"""
Tests de facturación.

Cubren la conexión de utils/email_sender.py::enviar_factura_por_email()
al flujo real de solicitar_factura (antes, esa función existía pero nadie
la llamaba — ver hallazgo de la revisión general del proyecto, 2026-09-04).

Regresión (revisión de código 2026-09-15): solicitar_factura() nunca
chequeaba order.status -- antes de Incremento 2 (pagos con MercadoPago)
todas las órdenes se creaban directamente como 'completed', así que "toda
orden del usuario" y "toda orden pagada" eran el mismo conjunto y la
falta de chequeo no se notaba. Al pasar a crear órdenes como 'pending'
(confirmadas después por el webhook), un usuario podía facturar una orden
'pending' o 'rejected' navegando directo a la URL -- el botón solo se
ocultaba en el template, la ruta no estaba protegida. Fix: solicitar_factura()
ahora exige status in ('completed', 'approved').
"""
import uuid

from extensions import db
from models.database_models import Order, OrderItem, Invoice, User


def login(client, username='testuser', password='Test1234'):
    return client.post('/login', data={'username': username, 'password': password})


def crear_orden(test_user):
    order = Order(user_id=test_user.id, total=59.99, status='completed')
    db.session.add(order)
    db.session.flush()
    db.session.add(OrderItem(
        order_id=order.id, product_type='game', product_id=1,
        product_name='Test Game', quantity=1, price=59.99
    ))
    db.session.commit()
    return order


def datos_factura_validos():
    return {
        'nit': '900123456',
        'razon_social': 'Cliente de Prueba',
        'forma_pago': 'Tarjeta de Crédito',
    }


def test_pagina_solicitar_factura_no_crashea_con_total_decimal(client, test_user):
    """Regresión: order.total es Decimal (columna NUMERIC) y el template hacía
    `order.total / 1.19` directo — Python no permite Decimal / float, así que
    la página crasheaba con 500 incluso antes de llegar a enviar el formulario."""
    login(client)
    order = crear_orden(test_user)

    response = client.get(f'/factura/solicitar/{order.id}')

    assert response.status_code == 200


def test_solicitar_factura_de_orden_no_aprobada_es_rechazada(client, test_user):
    """Regresión: solicitar_factura no chequeaba order.status -- una orden
    'pending' o 'rejected' (posibles desde el Incremento 2 de pagos) podía
    facturarse igual navegando directo a la URL, aunque nunca se haya
    cobrado nada."""
    login(client)
    order = Order(user_id=test_user.id, total=59.99, status='pending')
    db.session.add(order)
    db.session.flush()
    db.session.add(OrderItem(
        order_id=order.id, product_type='game', product_id=1,
        product_name='Test Game', quantity=1, price=59.99
    ))
    db.session.commit()

    response = client.post(f'/factura/solicitar/{order.id}', data=datos_factura_validos())

    assert response.status_code == 302
    assert Invoice.query.filter_by(order_id=order.id).first() is None, 'no debe crearse factura para una orden no aprobada'


def test_solicitar_factura_envia_email_con_la_factura(client, test_user, monkeypatch):
    login(client)
    order = crear_orden(test_user)

    llamadas = []
    monkeypatch.setattr(
        'controllers.invoice.enviar_factura_por_email',
        lambda invoice, user, pdf_path: llamadas.append((invoice.id, user.id, pdf_path)) or True
    )

    response = client.post(f'/factura/solicitar/{order.id}', data=datos_factura_validos())

    assert response.status_code == 302
    invoice = Invoice.query.filter_by(order_id=order.id).first()
    assert invoice is not None
    assert len(llamadas) == 1
    assert llamadas[0][0] == invoice.id
    assert llamadas[0][1] == test_user.id


def test_solicitar_factura_exitosa_aunque_falle_envio_de_email(client, test_user, monkeypatch):
    """Un fallo al enviar el correo no debe impedir que la factura quede generada."""
    login(client)
    order = crear_orden(test_user)

    monkeypatch.setattr('controllers.invoice.enviar_factura_por_email', lambda *a, **k: False)

    response = client.post(f'/factura/solicitar/{order.id}', data=datos_factura_validos(), follow_redirects=False)

    assert response.status_code == 302
    assert Invoice.query.filter_by(order_id=order.id).first() is not None


def crear_admin_logueado(client):
    admin = User(username='admintest', email='admintest@example.com', is_admin=True, email_verified=True)
    admin.set_password('Test1234')
    db.session.add(admin)
    db.session.commit()
    client.post('/login', data={'username': 'admintest', 'password': 'Test1234'})
    return admin


def crear_factura(user, order):
    invoice = Invoice(
        uuid=str(uuid.uuid4()), folio='FE-0001', user_id=user.id, order_id=order.id,
        nit_receptor='900123456', razon_social_receptor='Cliente de Prueba',
        subtotal=50.00, iva=9.50, total=59.50, status='active',
    )
    db.session.add(invoice)
    db.session.commit()
    return invoice


def test_cancelar_factura_ya_cancelada_no_devuelve_json_crudo(client, test_user):
    """Regresión: cancelar_factura() devolvía jsonify(...) en las rutas de
    error, pero se llama desde un <form method="POST"> normal (no fetch/AJAX)
    -- el navegador terminaba mostrando el JSON crudo en pantalla en vez de
    un mensaje. Debe comportarse como el resto de la app: flash + redirect."""
    admin = crear_admin_logueado(client)
    order = crear_orden(test_user)
    invoice = crear_factura(admin, order)
    invoice.status = 'cancelled'
    db.session.commit()

    response = client.post(f'/factura/cancelar/{invoice.id}', follow_redirects=False)

    assert response.status_code == 302
    assert response.content_type != 'application/json'


def test_cancelar_factura_sin_ser_admin_no_devuelve_json_crudo(client, test_user):
    login(client)
    order = crear_orden(test_user)
    invoice = crear_factura(test_user, order)

    response = client.post(f'/factura/cancelar/{invoice.id}', follow_redirects=False)

    assert response.status_code == 302
    assert response.content_type != 'application/json'

    db.session.refresh(invoice)
    assert invoice.status == 'active'


def test_cancelar_factura_exitosa(client, test_user):
    admin = crear_admin_logueado(client)
    order = crear_orden(test_user)
    invoice = crear_factura(admin, order)

    response = client.post(f'/factura/cancelar/{invoice.id}', follow_redirects=False)

    assert response.status_code == 302
    db.session.refresh(invoice)
    assert invoice.status == 'cancelled'
    assert invoice.fecha_cancelacion is not None


def test_ver_factura_no_crashea(client, test_user, monkeypatch):
    """Regresión: templates/invoice/ver_factura.html referenciaba campos de
    México inexistentes en el modelo (rfc_emisor, rfc_receptor, y sobre todo
    fecha_timbrado.strftime(...), que sí lanzaba UndefinedError porque se le
    llama un método sobre un valor indefinido) — el modelo real (Colombia)
    usa nit_emisor/nit_receptor/fecha_validacion_dian."""
    login(client)
    order = crear_orden(test_user)
    monkeypatch.setattr('controllers.invoice.enviar_factura_por_email', lambda *a, **k: True)
    client.post(f'/factura/solicitar/{order.id}', data=datos_factura_validos())

    invoice = Invoice.query.filter_by(order_id=order.id).first()
    response = client.get(f'/factura/{invoice.id}')

    assert response.status_code == 200
