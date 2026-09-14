"""
Tests del webhook de MercadoPago (Incremento 2).

Cubren: validación de firma (rechaza sin firma / firma inválida), que el
estado real se sincroniza consultando la API (nunca se confía en el cuerpo
de la notificación), idempotencia ante reintentos, restauración de stock
cuando un pago termina rechazado, y que un fallo de envío de correo no
rompe la respuesta del webhook.
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
