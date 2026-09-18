"""
Webhook de MercadoPago (Incremento 2): recibe notificaciones de cambio de
estado de un pago y actualiza la orden correspondiente.
"""
import hashlib
import hmac

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models.database_models import Order
from utils.email_service import send_order_confirmation_email, send_order_rejected_email
from utils.error_handling import log_db_error
from utils.mercadopago_service import MercadoPagoError, obtener_pago
from utils.order_stock import descontar_stock, restaurar_stock

# Mapea los estados reales de un pago de MercadoPago al estado de Order.
# cancelled/refunded/charged_back se tratan como 'rejected': en los tres
# casos el dinero no queda cobrado a favor de la tienda.
ESTADOS_MP_A_ORDEN = {
    'approved': 'approved',
    'pending': 'pending',
    'in_process': 'pending',
    'in_mediation': 'pending',
    'rejected': 'rejected',
    'cancelled': 'rejected',
    'refunded': 'rejected',
    'charged_back': 'rejected',
}

webhooks_bp = Blueprint('webhooks', __name__, url_prefix='/webhooks')


@webhooks_bp.route('/mercadopago', methods=['POST'])
def mercadopago_webhook():
    """Recibe la notificación, valida su firma, y sincroniza Order.status
    con el estado real del pago (consultado a la API, nunca confiado desde
    el cuerpo de la notificación)."""
    if not _firma_valida(request):
        current_app.logger.warning('Webhook de MercadoPago con firma inválida o ausente, rechazado')
        return jsonify({'error': 'firma inválida'}), 401

    body = request.get_json(silent=True) or {}
    tipo = body.get('type') or request.args.get('type')
    # El data.id de la query string es el que efectivamente está firmado
    # (ver _firma_valida) -- se prioriza sobre el del body para no procesar
    # un payment_id distinto del que la firma realmente autenticó.
    payment_id = request.args.get('data.id') or request.args.get('id') or (body.get('data') or {}).get('id')

    # MercadoPago manda notificaciones de otros tipos (ej. merchant_order);
    # solo nos interesan las de pago. Responder 200 igual para que no reintente.
    if tipo != 'payment' or not payment_id:
        return jsonify({'success': True}), 200

    try:
        pago = obtener_pago(payment_id)
    except MercadoPagoError as e:
        current_app.logger.error(f'Error consultando el pago {payment_id} en MercadoPago: {e}')
        return jsonify({'error': 'no se pudo verificar el pago'}), 502

    order_id = pago.get('external_reference')
    order = Order.query.get(order_id) if order_id else None
    if not order:
        current_app.logger.warning(f'Webhook de MercadoPago: orden {order_id!r} no encontrada (payment {payment_id})')
        return jsonify({'success': True}), 200

    nuevo_estado = ESTADOS_MP_A_ORDEN.get(pago.get('status'), 'pending')

    # Idempotencia: MercadoPago puede reenviar la misma notificación varias
    # veces. Si el estado ya está sincronizado, no repetir el correo ni
    # restaurar stock dos veces.
    if order.status == nuevo_estado:
        return jsonify({'success': True}), 200

    # 'approved' es un estado terminal: una notificación tardía o de un
    # intento de pago distinto (external_reference compartido) no debe
    # poder revertir una orden que ya se cobró -- si no, se le devolvería
    # al inventario stock que en realidad sigue vendido.
    if order.status == 'approved':
        current_app.logger.info(
            f'Webhook de MercadoPago: orden {order.id} ya está approved, '
            f'se ignora notificación de {payment_id} (estado {nuevo_estado})'
        )
        return jsonify({'success': True}), 200

    try:
        if nuevo_estado == 'rejected':
            restaurar_stock(order)
        elif nuevo_estado == 'approved' and order.status == 'rejected':
            # Reintento de pago exitoso tras un rechazo previo: el stock se
            # había restaurado, hay que volver a descontarlo.
            descontar_stock(order)

        order.status = nuevo_estado
        order.payment_id = str(payment_id)
        order.payment_method = pago.get('payment_method_id') or order.payment_method
        db.session.commit()
    except SQLAlchemyError as e:
        log_db_error('mercadopago_webhook', e)
        return jsonify({'error': 'error al actualizar la orden'}), 500

    _enviar_correo_estado(order, nuevo_estado)

    return jsonify({'success': True}), 200


def _enviar_correo_estado(order, nuevo_estado):
    """Envía el correo final de estado. Un fallo de SMTP no debe volver a
    fallar el webhook: la orden ya quedó actualizada, que es lo que importa
    para la integridad de los datos."""
    try:
        if nuevo_estado == 'approved':
            send_order_confirmation_email(order.user.email, order.user.username, order)
        elif nuevo_estado == 'rejected':
            send_order_rejected_email(order.user.email, order.user.username, order)
        # 'pending' no dispara correo aquí: ya se envió al crear la orden en checkout().
    except Exception as e:
        current_app.logger.error(f'Error enviando correo de estado de pago para orden {order.id}: {e}')


def _firma_valida(req):
    """Valida el header x-signature siguiendo el algoritmo documentado por
    MercadoPago: HMAC-SHA256 sobre un manifest con el id del recurso, el
    x-request-id, y el timestamp, usando el webhook secret de la cuenta
    (distinto del access_token)."""
    secret = current_app.config.get('MERCADOPAGO_WEBHOOK_SECRET')
    if not secret:
        current_app.logger.error('MERCADOPAGO_WEBHOOK_SECRET no configurado -- no se puede validar el webhook')
        return False

    x_signature = req.headers.get('x-signature', '')
    x_request_id = req.headers.get('x-request-id', '')
    data_id = req.args.get('data.id', '') or req.args.get('id', '')

    partes = {}
    for parte in x_signature.split(','):
        if '=' in parte:
            clave, valor = parte.split('=', 1)
            partes[clave.strip()] = valor.strip()

    ts = partes.get('ts', '')
    v1 = partes.get('v1', '')
    if not ts or not v1:
        return False

    manifest = f'id:{data_id.lower()};request-id:{x_request_id};ts:{ts};'
    hash_calculado = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()

    return hmac.compare_digest(hash_calculado, v1)
