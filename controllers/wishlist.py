"""
Controlador de Wishlist (Lista de Deseos)
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models.database_models import Wishlist, Game, Hardware

wishlist_bp = Blueprint('wishlist', __name__, url_prefix='/wishlist')

@wishlist_bp.route('/')
@login_required
def index():
    """Página de wishlist del usuario"""
    wishlist_items = Wishlist.get_user_wishlist(current_user.id)
    
    # Obtener detalles de los productos
    products = []
    for item in wishlist_items:
        if item.product_type == 'game':
            product = Game.query.get(item.product_id)
            if product:
                products.append({
                    'wishlist_id': item.id,
                    'type': 'game',
                    'product': product,
                    'added_at': item.created_at
                })
        elif item.product_type == 'hardware':
            product = Hardware.query.get(item.product_id)
            if product:
                products.append({
                    'wishlist_id': item.id,
                    'type': 'hardware',
                    'product': product,
                    'added_at': item.created_at
                })
    
    return render_template('wishlist/index.html', products=products)

@wishlist_bp.route('/agregar', methods=['POST'])
@login_required
def agregar():
    """Agregar producto a wishlist"""
    data = request.get_json()
    product_id = data.get('product_id')
    product_type = data.get('product_type')
    
    if not product_id or not product_type:
        return jsonify({
            'success': False,
            'message': 'Datos incompletos'
        }), 400
    
    success, message = Wishlist.add_to_wishlist(
        current_user.id,
        product_id,
        product_type
    )
    
    if success:
        wishlist_count = Wishlist.query.filter_by(user_id=current_user.id).count()
        return jsonify({
            'success': True,
            'message': message,
            'wishlist_count': wishlist_count
        })
    else:
        return jsonify({
            'success': False,
            'message': message
        }), 400

@wishlist_bp.route('/remover', methods=['POST'])
@login_required
def remover():
    """Remover producto de wishlist"""
    data = request.get_json()
    product_id = data.get('product_id')
    product_type = data.get('product_type')
    
    if not product_id or not product_type:
        return jsonify({
            'success': False,
            'message': 'Datos incompletos'
        }), 400
    
    success, message = Wishlist.remove_from_wishlist(
        current_user.id,
        product_id,
        product_type
    )
    
    wishlist_count = Wishlist.query.filter_by(user_id=current_user.id).count()
    
    return jsonify({
        'success': success,
        'message': message,
        'wishlist_count': wishlist_count
    })

@wishlist_bp.route('/check/<product_type>/<int:product_id>')
@login_required
def check(product_type, product_id):
    """Verificar si un producto está en wishlist"""
    item = Wishlist.query.filter_by(
        user_id=current_user.id,
        product_id=product_id,
        product_type=product_type
    ).first()
    
    return jsonify({
        'in_wishlist': item is not None
    })

@wishlist_bp.route('/count')
@login_required
def count():
    """Obtener cantidad de items en wishlist"""
    count = Wishlist.query.filter_by(user_id=current_user.id).count()
    return jsonify({'count': count})
