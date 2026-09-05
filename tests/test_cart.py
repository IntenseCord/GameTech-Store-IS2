"""
Tests del carrito y checkout.

Cubren los bugs corregidos al reemplazar `except Exception` por
`except SQLAlchemyError` en controllers/cart.py (validación de stock como
error de negocio, 400 no 500) y el flujo de checkout con MercadoPago
(Incremento 1): la orden queda `pending` y solo se confirma vía webhook
(Incremento 2), y un fallo al crear la preferencia de pago revierte toda
la transacción (orden, items y stock).
"""
import re

from extensions import db
from models.database_models import CartItem, Order, Hardware
from utils.mercadopago_service import MercadoPagoError


def login(client, username='testuser', password='Test1234'):
    return client.post('/login', data={'username': username, 'password': password})


def test_agregar_al_carrito_excede_stock_devuelve_400_no_500(client, test_user, test_hardware):
    """Antes del fix, esto se atrapaba con `except Exception` genérico y devolvía 500
    en vez de 400: no es un error de servidor, es una validación de negocio."""
    login(client)

    # Primera adición: dentro del stock (5 unidades disponibles)
    r1 = client.post('/carrito/agregar', json={
        'product_type': 'hardware', 'product_id': test_hardware.id, 'quantity': 3
    })
    assert r1.status_code == 200

    # Segunda adición: 3 + 3 = 6 > stock (5) -> ValueError de negocio dentro de actualizar_carrito
    r2 = client.post('/carrito/agregar', json={
        'product_type': 'hardware', 'product_id': test_hardware.id, 'quantity': 3
    })
    assert r2.status_code == 400
    assert r2.get_json()['success'] is False

    # La cantidad no debió cambiar: el ValueError se lanza antes del commit
    item = CartItem.query.filter_by(user_id=test_user.id, product_id=test_hardware.id).first()
    assert item.quantity == 3


def test_checkout_form_incluye_csrf_token_propio(client_csrf, test_user, test_game):
    """Regresión: el <form> de checkout.html no tenía su propio campo csrf_token
    (a diferencia de carrito.html). base.html tiene un <script> que lo auto-inyecta
    en cualquier form sin él, así que en un navegador normal con JS activo la compra
    sí funcionaba — pero el test client no ejecuta JS, y tampoco lo haría un usuario
    con JS deshabilitado: sin el campo propio en el HTML, ese POST se rechaza con
    400 'CSRF token missing'. La suite normal corre con WTF_CSRF_ENABLED=False y
    nunca lo detectó — solo se ve con client_csrf.

    Se hace login vía sesión directa (no vía POST /login) porque ese endpoint
    también exige CSRF y no es lo que este test está verificando."""
    with client_csrf.session_transaction() as sess:
        sess['_user_id'] = str(test_user.id)
        sess['_fresh'] = True

    CartItem.query.filter_by(user_id=test_user.id).delete()
    db.session.add(CartItem(user_id=test_user.id, product_type='game', product_id=test_game.id, quantity=1))
    db.session.commit()

    pagina = client_csrf.get('/carrito/checkout')

    # Extrae el token del <input> del propio form de checkout, no del <meta>
    # global de base.html (ese está en toda página y no prueba nada del form).
    match = re.search(
        rb'<form[^>]*carrito/checkout[^>]*>.*?name="csrf_token"\s+value="([^"]+)"',
        pagina.data,
        re.DOTALL,
    )
    assert match, 'El <form> de checkout no incluye su propio campo csrf_token'
    token = match.group(1).decode()

    con_token = client_csrf.post('/carrito/checkout', data={'csrf_token': token})
    assert con_token.status_code != 400


def test_pagina_checkout_no_crashea_con_total_decimal(client, test_user, test_game):
    """Regresión crítica: item.get_subtotal() devuelve Decimal (precio es NUMERIC),
    y el template hacía `total * 0.16` directo — Python no permite Decimal * float.
    El checkout.py::checkout() atrapa la excepción con un except genérico y
    redirige silenciosamente al carrito con un error confuso: nadie podía
    completar una compra, sin que se viera como un crash."""
    login(client)
    client.post('/carrito/agregar', json={
        'product_type': 'game', 'product_id': test_game.id, 'quantity': 1
    })

    response = client.get('/carrito/checkout')

    assert response.status_code == 200


def test_checkout_exitoso_crea_orden_pending_y_redirige_a_mercadopago(client, test_user, test_game, monkeypatch):
    """La orden no se marca 'completed' en checkout(): queda 'pending' hasta que
    el webhook de MercadoPago (Incremento 2) confirme el pago de verdad. El
    usuario es redirigido al checkout_url que devuelve la API, no a orden_confirmada
    directamente."""
    login(client)

    client.post('/carrito/agregar', json={
        'product_type': 'game', 'product_id': test_game.id, 'quantity': 1
    })

    def preferencia_falsa(order, cart_items):
        return 'pref-123', 'https://sandbox.mercadopago.com/checkout/pref-123'

    monkeypatch.setattr('controllers.cart.crear_preferencia_pago', preferencia_falsa)

    response = client.post('/carrito/checkout', follow_redirects=False)

    assert response.status_code == 302
    assert response.headers['Location'] == 'https://sandbox.mercadopago.com/checkout/pref-123'

    order = Order.query.filter_by(user_id=test_user.id).first()
    assert order is not None
    assert order.status == 'pending'
    assert order.payment_id == 'pref-123'

    # El carrito sí debe haber quedado vacío: la orden se comiteó
    assert CartItem.query.filter_by(user_id=test_user.id).count() == 0


def test_checkout_exitoso_aunque_falle_envio_de_correo_pendiente(client, test_user, test_game, monkeypatch):
    """Un fallo de SMTP al enviar el correo intermedio de 'orden pendiente' no debe
    impedir que el usuario llegue al checkout de MercadoPago: la orden y el pago
    ya se resolvieron antes de intentar el envío."""
    login(client)

    client.post('/carrito/agregar', json={
        'product_type': 'game', 'product_id': test_game.id, 'quantity': 1
    })

    def preferencia_falsa(order, cart_items):
        return 'pref-456', 'https://sandbox.mercadopago.com/checkout/pref-456'

    def fallar_envio(*args, **kwargs):
        raise RuntimeError('SMTP no configurado')

    monkeypatch.setattr('controllers.cart.crear_preferencia_pago', preferencia_falsa)
    monkeypatch.setattr('controllers.cart.send_order_pending_email', fallar_envio)

    response = client.post('/carrito/checkout', follow_redirects=False)

    assert response.status_code == 302
    assert response.headers['Location'] == 'https://sandbox.mercadopago.com/checkout/pref-456'

    order = Order.query.filter_by(user_id=test_user.id).first()
    assert order is not None
    assert order.status == 'pending'


def test_checkout_revierte_orden_y_stock_si_falla_mercadopago(client, test_user, test_hardware, monkeypatch):
    """Si crear_preferencia_pago() falla, no debe quedar una orden 'pending'
    huérfana sin ninguna forma de pagarla: toda la transacción (orden, items,
    descuento de stock, vaciado de carrito) debe revertirse."""
    login(client)

    stock_original = test_hardware.stock

    client.post('/carrito/agregar', json={
        'product_type': 'hardware', 'product_id': test_hardware.id, 'quantity': 1
    })

    def fallar_preferencia(order, cart_items):
        raise MercadoPagoError('sandbox no configurado')

    monkeypatch.setattr('controllers.cart.crear_preferencia_pago', fallar_preferencia)

    response = client.post('/carrito/checkout', follow_redirects=False)

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/carrito')

    assert Order.query.filter_by(user_id=test_user.id).count() == 0
    assert CartItem.query.filter_by(user_id=test_user.id).count() == 1

    hardware = Hardware.query.get(test_hardware.id)
    assert hardware.stock == stock_original
