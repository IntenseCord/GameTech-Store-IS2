
"""
Controlador del carrito de compras
"""
from collections.abc import Mapping

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from extensions import db
from models.database_models import CartItem, Game, Hardware, Order, OrderItem
from utils.email_service import send_order_pending_email
from utils.error_handling import log_db_error
from utils.mercadopago_service import crear_preferencia_pago, MercadoPagoError

PRODUCTO_ELIMINADO = 'Producto eliminado del carrito'
STOCK_INSUFICIENTE = 'Stock insuficiente'
VER_CARRITO = 'cart.ver_carrito'

cart_bp = Blueprint('cart', __name__)

def obtener_items_vigentes():
    """Items del carrito del usuario cuyo producto todavía existe.

    CartItem guarda product_id sin clave foránea (es juego o hardware), así que
    borrar un producto deja items huérfanos. Se retiran y se avisa al usuario.
    """
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    vigentes = [item for item in items if item.get_product() is not None]
    huerfanos = [item for item in items if item.get_product() is None]
    if huerfanos:
        for item in huerfanos:
            db.session.delete(item)
        db.session.commit()
        flash('Quitamos de tu carrito productos que ya no están disponibles', 'warning')
    return vigentes

@cart_bp.route('/carrito')
@login_required
def ver_carrito():
    """Ver el carrito de compras"""
    try:
        cart_items = obtener_items_vigentes()

        # Calcular total
        total = sum(item.get_subtotal() for item in cart_items)

        return render_template('cart/carrito.html', cart_items=cart_items, total=total)
    except SQLAlchemyError as e:
        log_db_error('ver_carrito', e)
        flash('Error al cargar el carrito', 'danger')
        return redirect(url_for('index'))

@cart_bp.route('/carrito/agregar', methods=['POST'])
@login_required
def agregar_al_carrito():
    """Agregar producto al carrito"""
    # CSRF está manejado automáticamente por Flask-WTF
    # Para peticiones JSON, el token debe estar en el header X-CSRFToken
    data = request.get_json(silent=True) if request.is_json else request.form
    if not isinstance(data, Mapping):
        return responder_error('Datos inválidos', 400)

    product_type = data.get('product_type')
    try:
        product_id = int(data.get('product_id'))
        quantity = int(data.get('quantity', 1))
    except (TypeError, ValueError):
        return responder_error('Datos inválidos: product_id y quantity deben ser números enteros', 400)

    # Validar tipo de producto
    error = validar_tipo_producto(product_type)
    if error:
        return responder_error(error, 400)

    # Obtener producto según tipo
    product = obtener_producto(product_type, product_id)
    if not product:
        return responder_error('Producto no encontrado', 404)

    # Validar stock
    if product.stock < quantity:
        return responder_error(STOCK_INSUFICIENTE, 400)

    # Agregar o actualizar carrito
    try:
        message = actualizar_carrito(product_type, product_id, quantity)
        db.session.commit()
        return responder_exito(message)
    except ValueError as e:
        # Errores de validación de negocio (stock insuficiente, cantidad inválida), no de BD
        db.session.rollback()
        return responder_error(str(e), 400)
    except SQLAlchemyError as e:
        log_db_error('agregar_al_carrito', e)
        return responder_error('Error al agregar al carrito', 500)

def validar_tipo_producto(product_type):
    """Valida que el tipo de producto sea válido."""
    if product_type not in ['game', 'hardware']:
        return 'Tipo de producto inválido'
    return None

def obtener_producto(product_type, product_id):
    """Obtiene el producto desde la base de datos según su tipo."""
    if product_type == 'game':
        return db.session.get(Game, product_id)
    elif product_type == 'hardware':
        return db.session.get(Hardware, product_id)
    return None

def actualizar_carrito(product_type, product_id, quantity):
    """Agrega o actualiza un producto en el carrito del usuario."""
    # Validar que la cantidad sea positiva
    if quantity <= 0:
        raise ValueError('La cantidad debe ser positiva')
    
    existing_item = CartItem.query.filter_by(
        user_id=current_user.id,
        product_type=product_type,
        product_id=product_id
    ).first()

    if existing_item:
        # Validar que la cantidad total no exceda el stock
        new_total_quantity = existing_item.quantity + quantity
        product = obtener_producto(product_type, product_id)
        if product and new_total_quantity > product.stock:
            raise ValueError(STOCK_INSUFICIENTE)
        
        existing_item.quantity = new_total_quantity
        return 'Cantidad actualizada en el carrito'
    
    nuevo_item = CartItem(
        user_id=current_user.id,
        product_type=product_type,
        product_id=product_id,
        quantity=quantity
    )
    db.session.add(nuevo_item)
    return 'Producto agregado al carrito'

def responder_error(mensaje, codigo_http):
    """Devuelve respuesta de error en JSON o HTML según el tipo de petición"""
    if request.is_json:
        return jsonify({'success': False, 'message': mensaje}), codigo_http
    flash(mensaje, 'danger')
    return redirect(request.referrer or url_for('index'))

def responder_exito(mensaje):
    """Devuelve respuesta de éxito en JSON o HTML según el tipo de petición"""
    if request.is_json:
        cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
        return jsonify({'success': True, 'message': mensaje, 'cart_count': cart_count})
    flash(mensaje, 'success')
    return redirect(request.referrer or url_for('index'))

@cart_bp.route('/carrito/actualizar/<int:item_id>', methods=['POST'])
@login_required
def actualizar_cantidad(item_id):
    """Actualizar cantidad de un item en el carrito"""
    try:
        cart_item = db.get_or_404(CartItem, item_id)
        
        # Verificar que el item pertenece al usuario
        if cart_item.user_id != current_user.id:
            flash('No tienes permiso para modificar este item', 'danger')
            return redirect(url_for(VER_CARRITO))
        
        try:
            quantity = int(request.form.get('quantity', 1))
        except (ValueError, TypeError):
            flash('Cantidad inválida', 'danger')
            return redirect(url_for(VER_CARRITO))
        
        if quantity <= 0:
            db.session.delete(cart_item)
            flash(PRODUCTO_ELIMINADO, 'info')
        else:
            # Verificar stock
            product = cart_item.get_product()
            if product and product.stock >= quantity:
                cart_item.quantity = quantity
                flash('Cantidad actualizada', 'success')
            else:
                flash(STOCK_INSUFICIENTE, 'danger')
        
        db.session.commit()
        return redirect(url_for(VER_CARRITO))
    except SQLAlchemyError as e:
        log_db_error('actualizar_cantidad', e)
        flash('Error al actualizar la cantidad', 'danger')
        return redirect(url_for(VER_CARRITO))

@cart_bp.route('/carrito/eliminar/<int:item_id>', methods=['POST'])
@login_required
def eliminar_del_carrito(item_id):
    """Eliminar un item del carrito"""
    try:
        cart_item = db.get_or_404(CartItem, item_id)
        
        # Verificar que el item pertenece al usuario
        if cart_item.user_id != current_user.id:
            if request.is_json:
                return jsonify({'success': False, 'message': 'No autorizado'}), 403
            flash('No tienes permiso para eliminar este item', 'danger')
            return redirect(url_for(VER_CARRITO))
        
        db.session.delete(cart_item)
        db.session.commit()
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': PRODUCTO_ELIMINADO,
                'cart_count': CartItem.query.filter_by(user_id=current_user.id).count()
            })
        
        flash(PRODUCTO_ELIMINADO, 'success')
        return redirect(url_for(VER_CARRITO))
    except SQLAlchemyError as e:
        log_db_error('eliminar_del_carrito', e)
        if request.is_json:
            return jsonify({'success': False, 'message': 'Error al eliminar item'}), 500
        flash('Error al eliminar el item', 'danger')
        return redirect(url_for(VER_CARRITO))

@cart_bp.route('/carrito/vaciar', methods=['POST'])
@login_required
def vaciar_carrito():
    """Vaciar todo el carrito"""
    try:
        CartItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        
        flash('Carrito vaciado', 'info')
        return redirect(url_for(VER_CARRITO))
    except SQLAlchemyError as e:
        log_db_error('vaciar_carrito', e)
        flash('Error al vaciar el carrito', 'danger')
        return redirect(url_for(VER_CARRITO))

@cart_bp.route('/carrito/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    """Proceso de checkout con bloqueo de filas para evitar condiciones de carrera"""
    try:
        # En el POST no se retiran huérfanos en silencio: eso cambiaría lo que el
        # usuario paga sin que lo vea. La validación de stock de más abajo los
        # reporta, y el siguiente GET del carrito/checkout los limpia con aviso.
        if request.method == 'POST':
            cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        else:
            cart_items = obtener_items_vigentes()

        if not cart_items:
            flash('Tu carrito está vacío', 'warning')
            return redirect(url_for(VER_CARRITO))
        
        if request.method == 'POST':
            # Iniciar transacción explícita
            try:
                # Bloquear filas de productos para evitar condiciones de carrera
                # Usar FOR UPDATE para bloquear las filas en PostgreSQL

                # Obtener IDs de productos en el carrito
                game_ids = [item.product_id for item in cart_items if item.product_type == 'game']
                hardware_ids = [item.product_id for item in cart_items if item.product_type == 'hardware']
                
                # Bloquear filas de juegos
                if game_ids:
                    Game.query.filter(Game.id.in_(game_ids)).with_for_update().all()
                
                # Bloquear filas de hardware
                if hardware_ids:
                    Hardware.query.filter(Hardware.id.in_(hardware_ids)).with_for_update().all()
                
                # Revalidar stock dentro de la transacción bloqueada
                for cart_item in cart_items:
                    product = cart_item.get_product()
                    if not product or product.stock < cart_item.quantity:
                        db.session.rollback()
                        if product:
                            nombre = product.nombre if hasattr(product, 'nombre') else product.modelo
                        else:
                            nombre = 'un producto de tu carrito'
                        flash(f'Stock insuficiente para {nombre}', 'danger')
                        return redirect(url_for(VER_CARRITO))
                
                # Calcular total
                total = sum(item.get_subtotal() for item in cart_items)

                # Crear orden en estado pendiente: se confirma (approved/rejected)
                # cuando llegue el webhook de MercadoPago (Incremento 2), no aquí.
                order = Order(
                    user_id=current_user.id,
                    total=total,
                    status='pending'
                )
                db.session.add(order)
                db.session.flush()  # Para obtener el ID de la orden

                # Crear items de la orden y actualizar stock
                for cart_item in cart_items:
                    product = cart_item.get_product()

                    # Crear item de orden
                    order_item = OrderItem(
                        order_id=order.id,
                        product_type=cart_item.product_type,
                        product_id=cart_item.product_id,
                        product_name=product.nombre if hasattr(product, 'nombre') else f"{product.marca} {product.modelo}",
                        quantity=cart_item.quantity,
                        price=product.precio
                    )
                    db.session.add(order_item)

                    # Actualizar stock (ahora seguro por el bloqueo)
                    product.stock -= cart_item.quantity

                # Vaciar carrito
                CartItem.query.filter_by(user_id=current_user.id).delete()

                # Generar la preferencia de pago ANTES de comitear: si MercadoPago
                # falla, se revierte toda la orden (no dejar una orden "pending"
                # huérfana sin ninguna forma de pagarla).
                payment_id, checkout_url = crear_preferencia_pago(order, cart_items)
                order.payment_id = payment_id

                db.session.commit()
            except SQLAlchemyError as e:
                log_db_error('checkout', e)
                flash('Error al procesar la transacción', 'danger')
                return redirect(url_for(VER_CARRITO))
            except MercadoPagoError as e:
                db.session.rollback()
                current_app.logger.error(f'Error creando preferencia de MercadoPago: {e}')
                flash('No se pudo iniciar el pago. Por favor intenta de nuevo.', 'danger')
                return redirect(url_for(VER_CARRITO))

            # La orden ya quedó guardada en este punto: un fallo al enviar el
            # correo intermedio no debe impedir que el usuario llegue a pagar.
            try:
                send_order_pending_email(current_user.email, current_user.username, order)
            except Exception as e:
                current_app.logger.error(f'Error enviando correo de orden pendiente {order.id}: {e}')

            return redirect(checkout_url)
        
        # Calcular total para mostrar
        total = sum(item.get_subtotal() for item in cart_items)
        
        return render_template('cart/checkout.html', cart_items=cart_items, total=total)
    except SQLAlchemyError as e:
        log_db_error('checkout', e)
        flash('Error al procesar el checkout', 'danger')
        return redirect(url_for(VER_CARRITO))

@cart_bp.route('/orden/<int:order_id>')
@login_required
def orden_confirmada(order_id):
    """Página de confirmación de orden"""
    try:
        order = db.get_or_404(Order, order_id)
        
        # Verificar que la orden pertenece al usuario
        if order.user_id != current_user.id:
            flash('No tienes permiso para ver esta orden', 'danger')
            return redirect(url_for('index'))
        
        return render_template('cart/orden_confirmada.html', order=order)
    except SQLAlchemyError as e:
        log_db_error('orden_confirmada', e)
        flash('Error al cargar la orden', 'danger')
        return redirect(url_for('index'))

@cart_bp.route('/mis-ordenes')
@login_required
def mis_ordenes():
    """Ver historial de órdenes del usuario"""
    try:
        orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
        return render_template('cart/mis_ordenes.html', orders=orders)
    except SQLAlchemyError as e:
        log_db_error('mis_ordenes', e)
        flash('No se pudieron cargar tus órdenes', 'danger')
        return redirect(url_for('index'))

@cart_bp.route('/api/carrito/count')
@login_required
def cart_count():
    """API para obtener la cantidad de items en el carrito"""
    count = CartItem.query.filter_by(user_id=current_user.id).count()
    return jsonify({'count': count})
