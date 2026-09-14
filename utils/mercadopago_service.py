"""
Integración con MercadoPago (Checkout Pro + webhook de notificaciones).
"""
import mercadopago
from flask import current_app, url_for


class MercadoPagoError(Exception):
    """Error al comunicarse con la API de MercadoPago."""


def _get_sdk():
    access_token = current_app.config.get('MERCADOPAGO_ACCESS_TOKEN')
    if not access_token:
        raise MercadoPagoError('MERCADOPAGO_ACCESS_TOKEN no está configurado')
    return mercadopago.SDK(access_token)


def crear_preferencia_pago(order, cart_items):
    """
    Crea una preferencia de pago en MercadoPago para la orden dada.

    Args:
        order: Order ya con su id asignado (requiere al menos un
            db.session.flush() previo si todavía no se comiteó).
        cart_items: iterable de CartItem para armar los items de la preferencia.

    Returns:
        tuple (payment_id, checkout_url)

    Raises:
        MercadoPagoError: si la API de MercadoPago rechaza la petición o
            responde con un error.
    """
    sdk = _get_sdk()

    items = []
    for item in cart_items:
        product = item.get_product()
        nombre = product.nombre if hasattr(product, 'nombre') else f'{product.marca} {product.modelo}'
        items.append({
            'title': nombre,
            'quantity': item.quantity,
            'unit_price': float(product.precio),
            'currency_id': 'COP',
        })

    confirmacion_url = url_for('cart.orden_confirmada', order_id=order.id, _external=True)

    preference_data = {
        'items': items,
        'external_reference': str(order.id),
        'back_urls': {
            'success': confirmacion_url,
            'failure': confirmacion_url,
            'pending': confirmacion_url,
        },
        'auto_return': 'approved',
        'notification_url': url_for('webhooks.mercadopago_webhook', _external=True),
    }

    try:
        result = sdk.preference().create(preference_data)
    except Exception as e:
        raise MercadoPagoError(f'Error de comunicación con MercadoPago: {e}') from e

    if result.get('status') not in (200, 201):
        raise MercadoPagoError(f"MercadoPago rechazó la preferencia (status {result.get('status')}): {result.get('response')}")

    preference = result['response']
    access_token = current_app.config.get('MERCADOPAGO_ACCESS_TOKEN', '')
    es_sandbox = access_token.startswith('TEST-')
    checkout_url = preference.get('sandbox_init_point') if es_sandbox else preference.get('init_point')

    if not checkout_url:
        raise MercadoPagoError('MercadoPago no devolvió una URL de checkout válida')

    return preference['id'], checkout_url


def obtener_pago(payment_id):
    """
    Consulta el estado real de un pago en MercadoPago.

    El webhook solo notifica un payment_id -- nunca hay que confiar en el
    estado que venga en la propia notificación (puede ser vieja o falsificada
    si la firma no se validara), así que siempre se vuelve a consultar la API
    con el access_token propio antes de actuar.

    Args:
        payment_id: id del pago que llegó en la notificación del webhook.

    Returns:
        dict con la respuesta de MercadoPago (incluye 'status' y
        'external_reference').

    Raises:
        MercadoPagoError: si la API de MercadoPago no responde o rechaza la
            consulta.
    """
    sdk = _get_sdk()

    try:
        result = sdk.payment().get(payment_id)
    except Exception as e:
        raise MercadoPagoError(f'Error de comunicación con MercadoPago: {e}') from e

    if result.get('status') != 200:
        raise MercadoPagoError(f"MercadoPago rechazó la consulta del pago (status {result.get('status')}): {result.get('response')}")

    return result['response']
