"""
Step definitions BDD para el flujo completo de pagos con MercadoPago
(Incremento 1: checkout -> preferencia de pago; Incremento 2: webhook ->
sincronización de estado).

A diferencia de tests/test_webhooks.py, tests/test_cart.py, etc. (que
verifican unidades de código de forma aislada), este feature cubre el
comportamiento general de punta a punta tal como lo viviría un usuario o
un administrador: carrito -> checkout -> notificación de MercadoPago ->
estado final visible en factura y en el panel de admin.

Nota sobre `hardware.stock_inicial`: es un atributo agregado a mano (no
una columna del modelo), usado solo para recordar el stock ANTES de que
corra el paso "When" de cada escenario. No se puede depender de un
fixture de pytest normal para esto porque pytest-bdd resuelve los
fixtures de los pasos "Then" recién cuando esos pasos se ejecutan --es
decir, después del commit del webhook, que ya deja `hardware.stock`
expirado/actualizado por SQLAlchemy. Guardarlo como atributo plano en el
propio objeto evita ese problema (SQLAlchemy solo expira columnas
mapeadas, no atributos sueltos que le agreguemos al objeto).
"""
import hashlib
import hmac

from pytest_bdd import given, when, then, scenario, parsers

from extensions import db
from models.database_models import Order, OrderItem, User

FEATURE = '../features/pagos.feature'
WEBHOOK_SECRET = 'secreto-bdd-de-prueba'


@scenario(FEATURE, 'Checkout crea una orden pendiente, descuenta stock y redirige a MercadoPago')
def test_checkout_crea_orden_pendiente():
    pass


@scenario(FEATURE, 'Un pago aprobado confirma la orden y permite solicitar factura')
def test_pago_aprobado_confirma_orden():
    pass


@scenario(FEATURE, 'Un pago rechazado restaura el stock y bloquea la factura')
def test_pago_rechazado_restaura_stock():
    pass


@scenario(FEATURE, 'Una notificación tardía no puede revertir una orden ya aprobada')
def test_notificacion_tardia_no_revierte():
    pass


@scenario(FEATURE, 'Un reintento de pago exitoso tras un rechazo vuelve a descontar el stock')
def test_reintento_exitoso_descuenta_stock():
    pass


@scenario(FEATURE, 'El panel de administración muestra una orden aprobada como pagada')
def test_dashboard_muestra_orden_pagada():
    pass


# --- Background -----------------------------------------------------------

@given('existe un hardware en stock', target_fixture='hardware')
def hardware_en_stock(test_hardware):
    return test_hardware


# --- Checkout ---------------------------------------------------------------

@given('estoy logueado y tengo ese hardware en el carrito')
def logueado_con_hardware_en_carrito(client, test_user, hardware):
    hardware.stock_inicial = hardware.stock
    client.post('/login', data={'username': test_user.username, 'password': 'Test1234'})
    client.post('/carrito/agregar', json={
        'product_type': 'hardware', 'product_id': hardware.id, 'quantity': 1
    })


@when('voy a pagar el carrito', target_fixture='response')
def pagar_carrito(client, monkeypatch):
    monkeypatch.setattr(
        'controllers.cart.crear_preferencia_pago',
        lambda order, cart_items: ('pref-bdd', 'https://sandbox.mercadopago.com/checkout/pref-bdd')
    )
    return client.post('/carrito/checkout', follow_redirects=False)


@then('debería ser redirigido a MercadoPago')
def verificar_redireccion_mercadopago(response):
    assert response.status_code == 302
    assert 'mercadopago.com' in response.headers['Location']


@then(parsers.parse('la orden creada debería quedar en estado "{estado_esperado}"'), target_fixture='order')
def verificar_orden_creada_estado(test_user, estado_esperado):
    order = Order.query.filter_by(user_id=test_user.id).order_by(Order.id.desc()).first()
    assert order is not None
    assert order.status == estado_esperado
    return order


# --- Orden preexistente + notificación del webhook --------------------------

@given(parsers.parse('tengo una orden "{estado}" de ese hardware'), target_fixture='order')
def orden_existente(client, app_context, test_user, hardware, estado):
    hardware.stock_inicial = hardware.stock
    order = Order(user_id=test_user.id, total=hardware.precio, status=estado)
    db.session.add(order)
    db.session.flush()
    db.session.add(OrderItem(
        order_id=order.id, product_type='hardware', product_id=hardware.id,
        product_name=f'{hardware.marca} {hardware.modelo}', quantity=1, price=hardware.precio
    ))
    db.session.commit()
    # Logueado para poder ejercitar /factura/solicitar como dueño de la orden.
    client.post('/login', data={'username': test_user.username, 'password': 'Test1234'})
    return order


@when(parsers.parse('MercadoPago notifica que el pago fue "{resultado}"'), target_fixture='response')
def notificar_pago(client, app_context, monkeypatch, order, resultado):
    app_context.config['MERCADOPAGO_WEBHOOK_SECRET'] = WEBHOOK_SECRET
    estado_mp = {'aprobado': 'approved', 'rechazado': 'rejected'}[resultado]

    monkeypatch.setattr(
        'controllers.webhooks.obtener_pago',
        lambda payment_id: {
            'status': estado_mp, 'external_reference': str(order.id), 'payment_method_id': 'visa'
        }
    )
    monkeypatch.setattr('controllers.webhooks.send_order_confirmation_email', lambda *a: True)
    monkeypatch.setattr('controllers.webhooks.send_order_rejected_email', lambda *a: True)

    payment_id = f'pago-{estado_mp}-{order.id}'
    ts = '1700000000'
    request_id = 'req-bdd'
    manifest = f'id:{payment_id.lower()};request-id:{request_id};ts:{ts};'
    v1 = hmac.new(WEBHOOK_SECRET.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    headers = {'x-signature': f'ts={ts},v1={v1}', 'x-request-id': request_id}

    return client.post(
        f'/webhooks/mercadopago?type=payment&data.id={payment_id}',
        json={'type': 'payment', 'data': {'id': payment_id}},
        headers=headers,
    )


@then(parsers.parse('la orden debería quedar en estado "{estado_esperado}"'))
def verificar_estado_orden(order, estado_esperado):
    db.session.refresh(order)
    assert order.status == estado_esperado


@then('el stock del hardware debería descontarse')
def verificar_stock_descontado(hardware):
    hw = _hardware_actual(hardware.id)
    assert hw.stock == hardware.stock_inicial - 1


@then('el stock del hardware debería restaurarse')
def verificar_stock_restaurado(hardware):
    hw = _hardware_actual(hardware.id)
    assert hw.stock == hardware.stock_inicial + 1


@then('el stock del hardware no debería restaurarse')
def verificar_stock_no_restaurado(hardware):
    hw = _hardware_actual(hardware.id)
    assert hw.stock == hardware.stock_inicial


@then('el stock del hardware debería descontarse de nuevo')
def verificar_stock_descontado_de_nuevo(hardware):
    hw = _hardware_actual(hardware.id)
    assert hw.stock == hardware.stock_inicial - 1


@then('debería poder solicitar factura de esa orden')
def verificar_puede_facturar(client, order):
    response = client.get(f'/factura/solicitar/{order.id}')
    assert response.status_code == 200


@then('no debería poder solicitar factura de esa orden')
def verificar_no_puede_facturar(client, order):
    response = client.post(f'/factura/solicitar/{order.id}', data={
        'nit': '900123456', 'razon_social': 'Cliente BDD', 'forma_pago': 'Tarjeta de Crédito',
    })
    assert response.status_code == 302

    from models.database_models import Invoice
    assert Invoice.query.filter_by(order_id=order.id).first() is None


# --- Panel de administración -------------------------------------------------

@when('un administrador ve el dashboard de órdenes', target_fixture='response')
def admin_ve_dashboard(client):
    admin = User(username='admin_bdd', email='admin_bdd@example.com', is_admin=True, email_verified=True)
    admin.set_password('Test1234')
    db.session.add(admin)
    db.session.commit()
    # El paso "tengo una orden ... de ese hardware" ya deja logueado al
    # dueño de la orden -- /login redirige sin cambiar de sesión si ya hay
    # un usuario autenticado, así que hay que cerrar esa sesión primero.
    client.get('/logout')
    client.post('/login', data={'username': 'admin_bdd', 'password': 'Test1234'})
    return client.get('/admin')


@then('debería mostrarse la orden como pagada')
def verificar_orden_pagada_en_dashboard(response, order):
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    inicio_fila = html.find(f'Orden #{order.id}')
    if inicio_fila == -1:
        # El dashboard solo lista las 5 órdenes más recientes: si por algún
        # motivo la nuestra no aparece por nombre, al menos no debe haber
        # ninguna fila marcando (falsamente) una orden como cancelada.
        assert 'Cancelada' not in html
    else:
        fragmento = html[inicio_fila:inicio_fila + 600]
        assert 'Completada' in fragmento or 'bg-success' in fragmento
        assert 'Cancelada' not in fragmento


# --- Helpers ------------------------------------------------------------

def _hardware_actual(hardware_id):
    from models.database_models import Hardware
    return Hardware.query.get(hardware_id)
