"""
Controlador del panel de administración
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from database import db
from models.database_models import User, Game, Hardware, Order, OrderItem
from werkzeug.utils import secure_filename
import os
from datetime import datetime

UPLOAD = 'static/uploads'
ADMIN_JUEGOS = 'admin.juegos'
ADMIN_HARDWARE = 'admin.hardware'

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    """Decorador para proteger rutas de administración"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Acceso denegado. Se requieren permisos de administrador.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/admin')
@login_required
@admin_required
def dashboard():
    """Panel principal de administración"""
    # Estadísticas básicas
    stats = {
        'usuarios': User.query.count(),
        'juegos': Game.query.count(),
        'hardware': Hardware.query.count(),
        'ordenes': Order.query.count(),
        'ordenes_recientes': Order.query.order_by(Order.created_at.desc()).limit(5).all(),
        'usuarios_recientes': User.query.order_by(User.created_at.desc()).limit(5).all()
    }
    return render_template('admin/dashboard.html', stats=stats)

@admin_bp.route('/admin/usuarios')
@login_required
@admin_required
def usuarios():
    """Gestión de usuarios"""
    users = User.query.all()
    return render_template('admin/usuarios.html', users=users)

@admin_bp.route('/admin/usuario/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    """Alternar rol de administrador"""
    user = User.query.get_or_404(user_id)
    if user == current_user:
        flash('No puedes cambiar tu propio rol de administrador', 'danger')
    else:
        user.is_admin = not user.is_admin
        db.session.commit()
        flash(f'Rol de administrador actualizado para {user.username}', 'success')
    return redirect(url_for('admin.usuarios'))

@admin_bp.route('/admin/juegos')
@login_required
@admin_required
def juegos():
    """Gestión de juegos"""
    games = Game.query.all()
    return render_template('admin/juegos.html', games=games)

@admin_bp.route('/admin/juego/nuevo', methods=['GET', 'POST'])
@login_required
@admin_required
def nuevo_juego():
    """Crear nuevo juego"""
    if request.method == 'POST':
        try:
            # Procesar imagen - archivo o URL
            imagen_path = None
            imagen = request.files.get('imagen')
            imagen_url = request.form.get('imagen_url', '').strip()
            
            if imagen and imagen.filename:
                # Procesar archivo subido
                filename = secure_filename(imagen.filename)
                imagen.save(os.path.join(UPLOAD, filename))
                imagen_path = os.path.join('/' + UPLOAD, filename)
            elif imagen_url:
                # Usar URL proporcionada
                imagen_path = imagen_url

            # Crear juego
            juego = Game(
                nombre=request.form['nombre'],
                descripcion=request.form['descripcion'],
                precio=float(request.form['precio']),
                genero=request.form['genero'],
                desarrollador=request.form['desarrollador'],
                fecha_lanzamiento=datetime.strptime(request.form['fecha_lanzamiento'], '%Y-%m-%d'),
                requisitos_minimos=request.form['requisitos_minimos'],
                requisitos_recomendados=request.form['requisitos_recomendados'],
                stock=int(request.form['stock']),
                imagen=imagen_path
            )
            db.session.add(juego)
            db.session.commit()
            flash('Juego creado exitosamente', 'success')
            return redirect(url_for(ADMIN_JUEGOS))
        except Exception as e:
            flash(f'Error al crear juego: {str(e)}', 'danger')
    
    return render_template('admin/juego_form.html')

@admin_bp.route('/admin/juego/<int:game_id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_juego(game_id):
    """Editar juego existente"""
    game = Game.query.get_or_404(game_id)
    
    if request.method == 'POST':
        try:
            # Actualizar imagen si se proporciona una nueva - archivo o URL
            imagen = request.files.get('imagen')
            imagen_url = request.form.get('imagen_url', '').strip()
            
            if imagen and imagen.filename:
                # Procesar archivo subido
                filename = secure_filename(imagen.filename)
                imagen.save(os.path.join(UPLOAD, filename))
                game.imagen = os.path.join('/' + UPLOAD, filename)
            elif imagen_url:
                # Usar URL proporcionada
                game.imagen = imagen_url

            # Actualizar datos
            game.nombre = request.form['nombre']
            game.descripcion = request.form['descripcion']
            game.precio = float(request.form['precio'])
            game.genero = request.form['genero']
            game.desarrollador = request.form['desarrollador']
            game.fecha_lanzamiento = datetime.strptime(request.form['fecha_lanzamiento'], '%Y-%m-%d')
            game.requisitos_minimos = request.form['requisitos_minimos']
            game.requisitos_recomendados = request.form['requisitos_recomendados']
            game.stock = int(request.form['stock'])
            
            db.session.commit()
            flash('Juego actualizado exitosamente', 'success')
            return redirect(url_for(ADMIN_JUEGOS))
        except Exception as e:
            flash(f'Error al actualizar juego: {str(e)}', 'danger')
    
    return render_template('admin/juego_form.html', game=game)

@admin_bp.route('/admin/hardware')
@login_required
@admin_required
def hardware():
    """Gestión de hardware"""
    components = Hardware.query.all()
    return render_template('admin/hardware.html', components=components)

@admin_bp.route('/admin/hardware/nuevo', methods=['GET', 'POST'])
@login_required
@admin_required
def nuevo_hardware():
    """Crear nuevo componente de hardware"""
    if request.method == 'POST':
        try:
            # Procesar imagen - archivo o URL
            imagen_path = None
            imagen = request.files.get('imagen')
            imagen_url = request.form.get('imagen_url', '').strip()
            
            if imagen and imagen.filename:
                # Procesar archivo subido
                filename = secure_filename(imagen.filename)
                imagen.save(os.path.join(UPLOAD, filename))
                imagen_path = os.path.join('/' + UPLOAD, filename)
            elif imagen_url:
                # Usar URL proporcionada
                imagen_path = imagen_url

            # Crear hardware
            hardware = Hardware(
                tipo=request.form['tipo'],
                marca=request.form['marca'],
                modelo=request.form['modelo'],
                precio=float(request.form['precio']),
                descripcion=request.form['descripcion'],
                especificaciones=request.form['especificaciones'],
                stock=int(request.form['stock']),
                imagen=imagen_path
            )
            db.session.add(hardware)
            db.session.commit()
            flash('Componente creado exitosamente', 'success')
            return redirect(url_for(ADMIN_HARDWARE))
        except Exception as e:
            flash(f'Error al crear componente: {str(e)}', 'danger')
    
    return render_template('admin/hardware_form.html')

@admin_bp.route('/admin/hardware/<int:hardware_id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_hardware(hardware_id):
    """Editar componente de hardware existente"""
    component = Hardware.query.get_or_404(hardware_id)
    
    if request.method == 'POST':
        try:
            # Actualizar imagen si se proporciona una nueva - archivo o URL
            imagen = request.files.get('imagen')
            imagen_url = request.form.get('imagen_url', '').strip()
            
            if imagen and imagen.filename:
                # Procesar archivo subido
                filename = secure_filename(imagen.filename)
                imagen.save(os.path.join(UPLOAD, filename))
                component.imagen = os.path.join('/' + UPLOAD, filename)
            elif imagen_url:
                # Usar URL proporcionada
                component.imagen = imagen_url

            # Actualizar datos
            component.tipo = request.form['tipo']
            component.marca = request.form['marca']
            component.modelo = request.form['modelo']
            component.precio = float(request.form['precio'])
            component.descripcion = request.form['descripcion']
            component.especificaciones = request.form['especificaciones']
            component.stock = int(request.form['stock'])
            
            db.session.commit()
            flash('Componente actualizado exitosamente', 'success')
            return redirect(url_for(ADMIN_HARDWARE))
        except Exception as e:
            flash(f'Error al actualizar componente: {str(e)}', 'danger')
    
    return render_template('admin/hardware_form.html', hardware=component)

@admin_bp.route('/admin/ordenes')
@login_required
@admin_required
def ordenes():
    """Gestión de órdenes"""
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/ordenes.html', orders=orders)

@admin_bp.route('/admin/orden/<int:order_id>')
@login_required
@admin_required
def ver_orden(order_id):
    """Ver detalles de una orden"""
    order = Order.query.get_or_404(order_id)
    return render_template('admin/orden_detalle.html', order=order)

@admin_bp.route('/admin/orden/<int:order_id>/estado', methods=['POST'])
@login_required
@admin_required
def actualizar_estado_orden(order_id):
    """Actualizar estado de una orden"""
    order = Order.query.get_or_404(order_id)
    nuevo_estado = request.form.get('status')
    if nuevo_estado in ['pending', 'completed', 'cancelled']:
        order.status = nuevo_estado
        db.session.commit()
        flash('Estado de la orden actualizado', 'success')
    else:
        flash('Estado inválido', 'danger')
    return redirect(url_for('admin.ver_orden', order_id=order_id))

@admin_bp.route('/admin/juego/<int:game_id>/eliminar', methods=['POST'])
@login_required
@admin_required
def eliminar_juego(game_id):
    """Eliminar juego existente"""
    game = Game.query.get_or_404(game_id)
    try:
        # Si el juego tiene una imagen, podríamos eliminarla del sistema de archivos aquí
        if game.imagen and game.imagen.startswith(UPLOAD):
            try:
                os.remove(os.path.join('static', game.imagen.lstrip('/static/')))
            except OSError:
                pass  # Si la imagen no existe, continuamos
        
        db.session.delete(game)
        db.session.commit()
        flash('Juego eliminado exitosamente', 'success')
    except Exception as e:
        flash(f'Error al eliminar juego: {str(e)}', 'danger')
    return redirect(url_for(ADMIN_JUEGOS))

@admin_bp.route('/admin/hardware/<int:hardware_id>/eliminar', methods=['POST'])
@login_required
@admin_required
def eliminar_hardware(hardware_id):
    """Eliminar componente de hardware existente"""
    component = Hardware.query.get_or_404(hardware_id)
    try:
        # Si el componente tiene una imagen, podríamos eliminarla del sistema de archivos aquí
        if component.imagen and component.imagen.startswith(UPLOAD):
            try:
                os.remove(os.path.join('static', component.imagen.lstrip('/static/')))
            except OSError:
                pass  # Si la imagen no existe, continuamos
        
        db.session.delete(component)
        db.session.commit()
        flash('Componente eliminado exitosamente', 'success')
    except Exception as e:
        flash(f'Error al eliminar componente: {str(e)}', 'danger')
    return redirect(url_for(ADMIN_HARDWARE))