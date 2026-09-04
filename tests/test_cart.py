"""
Tests del carrito y checkout.

Cubren específicamente los dos bugs corregidos al reemplazar
`except Exception` por `except SQLAlchemyError` en controllers/cart.py
(ver Paso 3.6 del plan): validación de stock como error de negocio (400,
no 500) y que un fallo de envío de correo no revierta una compra ya
guardada en checkout.
"""
from extensions import db
from models.database_models import CartItem, Order


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


def test_checkout_exitoso_aunque_falle_envio_de_correo(client, test_user, test_game, monkeypatch):
    """Antes del fix, un fallo de SMTP durante el envío de confirmación (dentro del
    mismo try que la transacción de BD) hacía creer al usuario que la compra había
    fallado, aunque la orden ya estaba guardada. Ahora el envío de correo es un
    paso aparte, después del commit."""
    login(client)

    client.post('/carrito/agregar', json={
        'product_type': 'game', 'product_id': test_game.id, 'quantity': 1
    })

    def fallar_envio(*args, **kwargs):
        raise RuntimeError('SMTP no configurado')

    monkeypatch.setattr('controllers.cart.send_order_confirmation_email', fallar_envio)

    response = client.post('/carrito/checkout', follow_redirects=False)

    # Debe redirigir a la confirmación de orden (éxito), no de vuelta al carrito (error)
    assert response.status_code == 302
    assert '/orden/' in response.headers['Location']

    order = Order.query.filter_by(user_id=test_user.id).first()
    assert order is not None
    assert order.status == 'completed'

    # El carrito debe haber quedado vacío: la transacción sí se completó
    assert CartItem.query.filter_by(user_id=test_user.id).count() == 0
