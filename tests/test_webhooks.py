"""
Tests del webhook de MercadoPago (Incremento 2).

Cubren: validación de firma (rechaza sin firma / firma inválida), que el
estado real se sincroniza consultando la API (nunca se confía en el cuerpo
de la notificación), idempotencia ante reintentos, restauración de stock
cuando un pago termina rechazado, y que un fallo de envío de correo no
rompe la respuesta del webhook.

Regresión (revisión de código 2026-09-15):
- `test_webhook_no_revierte_orden_ya_aprobada` -- la idempotencia solo
  comparaba contra `order.status`, así que una notificación tardía o de un
  pago distinto para la misma orden podía revertir una orden ya 'approved'
  de vuelta a 'rejected' y restaurar stock que en realidad seguía vendido.
  Fix: 'approved' es ahora un estado terminal (controllers/webhooks.py).
- `test_webhook_reintento_exitoso_tras_rechazo_vuelve_a_descontar_stock` --
  faltante, no bug: una orden rechazada que se aprueba en un reintento
  posterior no volvía a descontar el stock que se había restaurado.
- `test_webhook_usa_payment_id_de_query_string_no_del_body` -- la firma
  x-signature solo cubre el data.id de la query string, pero el
  payment_id procesado priorizaba el del body -- un body modificado podía
  hacer que se procesara un pago distinto del que realmente autenticó la
  firma. Fix: se prioriza el data.id de la query (el firmado).
"""
import hashlib
import hmac

from extensions import db
from models.database_models import Order, OrderItem, Hardware


WEBHOOK_SECRET = 'test-webhook-secret'


def firmar(data_id, request_id='req-123', ts='1700000000', secret=WEBHOOK_SECRET):
    manifest = f'id:{data_id.lower()};request-id:{request_id};ts:{ts};'
    v1 = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return {'x-signature': f'ts={ts},v1={v1}', 'x-request-id': request_id}


def crear_orden_con_hardware(test_user, test_hardware, status='pending'):
    order = Order(user_id=test_user.id, total=59.99, status=status)
    db.session.add(order)
    db.session.flush()
    db.session.add(OrderItem(
        order_id=order.id, product_type='hardware', product_id=test_hardware.id,
        product_name='Test Hardware', quantity=2, price=29.99
    ))
    db.session.commit()
    return order


def enviar_webhook(client, payment_id, headers=None, tipo='payment'):
    return client.post(
        f'/webhooks/mercadopago?type={tipo}&data.id={payment_id}',
        json={'type': tipo, 'data': {'id': payment_id}},
        headers=headers or {},
    )


def test_webhook_sin_firma_es_rechazado(client, app_context):
    app_context.config['MERCADOPAGO_WEBHOOK_SECRET'] = WEBHOOK_SECRET
    response = enviar_webhook(client, '123456')
    assert response.status_code == 401


def test_webhook_firma_invalida_es_rechazada(client, app_context):
    app_context.config['MERCADOPAGO_WEBHOOK_SECRET'] = WEBHOOK_SECRET
    headers = firmar('123456', secret='otro-secreto-distinto')
    response = enviar_webhook(client, '123456', headers=headers)
    assert response.status_code == 401


def test_webhook_sin_secreto_configurado_rechaza_todo(client, app_context):
    app_context.config['MERCADOPAGO_WEBHOOK_SECRET'] = None
    headers = firmar('123456')
    response = enviar_webhook(client, '123456', headers=headers)
    assert response.status_code == 401


def test_webhook_pago_aprobado_actualiza_orden_y_envia_correo(client, app_context, test_user, test_hardware, monkeypatch):
    app_context.config['MERCADOPAGO_WEBHOOK_SECRET'] = WEBHOOK_SECRET
    order = crear_orden_con_hardware(test_user, test_hardware, status='pending')

    monkeypatch.setattr(
        'controllers.webhooks.obtener_pago',
        lambda payment_id: {'status': 'approved', 'external_reference': str(order.id), 'payment_method_id': 'visa'}
    )
    enviados = []
    monkeypatch.setattr(
        'controllers.webhooks.send_order_confirmation_email',
        lambda email, username, o: enviados.append((email, o.id)) or True
    )

    headers = firmar('987654')
    response = enviar_webhook(client, '987654', headers=headers)

    assert response.status_code == 200
    db.session.refresh(order)
    assert order.status == 'approved'
    assert order.payment_id == '987654'
    assert order.payment_method == 'visa'
    assert len(enviados) == 1
    assert enviados[0] == (test_user.email, order.id)


def test_webhook_pago_rechazado_restaura_stock_y_envia_correo(client, app_context, test_user, test_hardware, monkeypatch):
    app_context.config['MERCADOPAGO_WEBHOOK_SECRET'] = WEBHOOK_SECRET
    stock_original = test_hardware.stock
    order = crear_orden_con_hardware(test_user, test_hardware, status='pending')

    monkeypatch.setattr(
        'controllers.webhooks.obtener_pago',
        lambda payment_id: {'status': 'rejected', 'external_reference': str(order.id), 'payment_method_id': None}
    )
    enviados = []
    monkeypatch.setattr(
        'controllers.webhooks.send_order_rejected_email',
        lambda email, username, o: enviados.append((email, o.id)) or True
    )

    headers = firmar('555')
    response = enviar_webhook(client, '555', headers=headers)

    assert response.status_code == 200
    db.session.refresh(order)
    assert order.status == 'rejected'

    hardware = Hardware.query.get(test_hardware.id)
    assert hardware.stock == stock_original + 2  # se restauró la cantidad de la orden

    assert len(enviados) == 1


def test_webhook_es_idempotente_no_reprocesa_si_el_estado_no_cambio(client, app_context, test_user, test_hardware, monkeypatch):
    app_context.config['MERCADOPAGO_WEBHOOK_SECRET'] = WEBHOOK_SECRET
    order = crear_orden_con_hardware(test_user, test_hardware, status='approved')

    monkeypatch.setattr(
        'controllers.webhooks.obtener_pago',
        lambda payment_id: {'status': 'approved', 'external_reference': str(order.id), 'payment_method_id': 'visa'}
    )
    enviados = []
    monkeypatch.setattr(
        'controllers.webhooks.send_order_confirmation_email',
        lambda email, username, o: enviados.append(1) or True
    )

    headers = firmar('999')
    response = enviar_webhook(client, '999', headers=headers)

    assert response.status_code == 200
    assert len(enviados) == 0, 'no debe reenviar el correo si el estado ya estaba sincronizado'


def test_webhook_orden_inexistente_no_crashea(client, app_context, monkeypatch):
    app_context.config['MERCADOPAGO_WEBHOOK_SECRET'] = WEBHOOK_SECRET
    monkeypatch.setattr(
        'controllers.webhooks.obtener_pago',
        lambda payment_id: {'status': 'approved', 'external_reference': '999999'}
    )
    headers = firmar('111')
    response = enviar_webhook(client, '111', headers=headers)
    assert response.status_code == 200


def test_webhook_tipo_no_payment_se_ignora(client, app_context):
    app_context.config['MERCADOPAGO_WEBHOOK_SECRET'] = WEBHOOK_SECRET
    headers = firmar('222')
    response = enviar_webhook(client, '222', headers=headers, tipo='merchant_order')
    assert response.status_code == 200


def test_webhook_no_revierte_orden_ya_aprobada(client, app_context, test_user, test_hardware, monkeypatch):
    """Una notificación tardía de un pago distinto (misma orden) no debe
    poder revertir una orden que ya está 'approved' ni devolverle stock que
    en realidad sigue vendido."""
    app_context.config['MERCADOPAGO_WEBHOOK_SECRET'] = WEBHOOK_SECRET
    stock_tras_venta = test_hardware.stock
    order = crear_orden_con_hardware(test_user, test_hardware, status='approved')

    monkeypatch.setattr(
        'controllers.webhooks.obtener_pago',
        lambda payment_id: {'status': 'rejected', 'external_reference': str(order.id), 'payment_method_id': None}
    )
    enviados = []
    monkeypatch.setattr(
        'controllers.webhooks.send_order_rejected_email',
        lambda email, username, o: enviados.append(1) or True
    )

    headers = firmar('777')
    response = enviar_webhook(client, '777', headers=headers)

    assert response.status_code == 200
    db.session.refresh(order)
    assert order.status == 'approved', 'una orden ya aprobada no debe revertirse'

    hardware = Hardware.query.get(test_hardware.id)
    assert hardware.stock == stock_tras_venta, 'no debe restaurarse stock de una orden ya aprobada'
    assert len(enviados) == 0, 'no debe enviarse correo de rechazo para una orden ya aprobada'


def test_webhook_reintento_exitoso_tras_rechazo_vuelve_a_descontar_stock(client, app_context, test_user, test_hardware, monkeypatch):
    """Si una orden rechazada (con su stock ya restaurado) se aprueba en un
    reintento de pago posterior, el stock debe volver a descontarse."""
    app_context.config['MERCADOPAGO_WEBHOOK_SECRET'] = WEBHOOK_SECRET
    stock_restaurado = test_hardware.stock
    order = crear_orden_con_hardware(test_user, test_hardware, status='rejected')

    monkeypatch.setattr(
        'controllers.webhooks.obtener_pago',
        lambda payment_id: {'status': 'approved', 'external_reference': str(order.id), 'payment_method_id': 'visa'}
    )
    monkeypatch.setattr(
        'controllers.webhooks.send_order_confirmation_email',
        lambda email, username, o: True
    )

    headers = firmar('888')
    response = enviar_webhook(client, '888', headers=headers)

    assert response.status_code == 200
    db.session.refresh(order)
    assert order.status == 'approved'

    hardware = Hardware.query.get(test_hardware.id)
    assert hardware.stock == stock_restaurado - 2, 'debe volver a descontarse el stock de la orden que ahora se aprobó'


def test_webhook_usa_payment_id_de_query_string_no_del_body(client, app_context, test_user, test_hardware, monkeypatch):
    """El payment_id procesado debe ser el que realmente está cubierto por
    la firma (el de la query string), no el que venga en el body -- si no,
    la firma no protege lo que el webhook termina ejecutando."""
    app_context.config['MERCADOPAGO_WEBHOOK_SECRET'] = WEBHOOK_SECRET
    order = crear_orden_con_hardware(test_user, test_hardware, status='pending')

    payment_ids_consultados = []
    monkeypatch.setattr(
        'controllers.webhooks.obtener_pago',
        lambda payment_id: payment_ids_consultados.append(payment_id) or {
            'status': 'approved', 'external_reference': str(order.id), 'payment_method_id': 'visa'
        }
    )
    monkeypatch.setattr('controllers.webhooks.send_order_confirmation_email', lambda *a: True)

    # Firma calculada sobre data.id=123 (query string), pero el body dice 999.
    headers = firmar('123')
    response = client.post(
        '/webhooks/mercadopago?type=payment&data.id=123',
        json={'type': 'payment', 'data': {'id': '999'}},
        headers=headers,
    )

    assert response.status_code == 200
    assert payment_ids_consultados == ['123'], 'debe procesarse el payment_id firmado (query), no el del body'
