"""
Tests de facturación.

Cubren la conexión de utils/email_sender.py::enviar_factura_por_email()
al flujo real de solicitar_factura (antes, esa función existía pero nadie
la llamaba — ver hallazgo de la revisión general del proyecto, 2026-09-04).
"""
from extensions import db
from models.database_models import Order, OrderItem, Invoice


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
