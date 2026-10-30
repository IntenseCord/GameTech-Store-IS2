"""
Controlador del panel de administración
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError
from extensions import db
from models.database_models import User, Game, Hardware, Order, CartItem, Wishlist
from utils.error_handling import log_db_error
from utils.order_stock import TRANSICIONES, cambiar_estado_orden, estados_destino
import os
from datetime import datetime

UPLOAD = 'static/uploads'
ADMIN_JUEGOS = 'admin.juegos'
ADMIN_HARDWARE = 'admin.hardware'


def url_publica_de_imagen(filename):
    """URL guardada en la base de datos: siempre con '/', sin el separador del sistema."""
    return f'/{UPLOAD}/{filename}'

def borrar_imagen_subida(url):
    """Borra del disco una imagen subida por este panel; ignora URLs externas y cualquier otra ruta."""
    if not url or url != url_publica_de_imagen(os.path.basename(url)):
        return
    try:
        os.remove(os.path.join(UPLOAD, os.path.basename(url)))
    except FileNotFoundError:
        pass
    except OSError as e:
        log_db_error('borrar_imagen_subida', e)


def commit_con_imagen(imagen_subida=None, imagen_reemplazada=None):
    """Confirma la transacción sin dejar archivos huérfanos en disco.

    Si el commit falla se descarta la imagen recién subida; si tiene éxito se borra la que fue reemplazada.
    """
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        borrar_imagen_subida(imagen_subida)
        raise
    borrar_imagen_subida(imagen_reemplazada)


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
    try:
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
    except SQLAlchemyError as e:
        log_db_error('dashboard', e)
        flash('Error al cargar el dashboard', 'danger')
        return redirect(url_for('index'))

@admin_bp.route('/admin/usuarios')
@login_required
@admin_required
def usuarios():
    """Gestión de usuarios"""
    try:
        users = User.query.all()
        return render_template('admin/usuarios.html', users=users)
    except SQLAlchemyError as e:
        log_db_error('usuarios', e)
        flash('Error al cargar usuarios', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/usuario/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    """Alternar rol de administrador"""
    try:
        user = db.get_or_404(User, user_id)
        if user == current_user:
            flash('No puedes cambiar tu propio rol de administrador', 'danger')
        else:
            user.is_admin = not user.is_admin
            db.session.commit()
            flash(f'Rol de administrador actualizado para {user.username}', 'success')
        return redirect(url_for('admin.usuarios'))
    except SQLAlchemyError as e:
        log_db_error('toggle_admin', e)
        flash('Error al actualizar rol de administrador', 'danger')
        return redirect(url_for('admin.usuarios'))

@admin_bp.route('/admin/juegos')
@login_required
@admin_required
def juegos():
    """Gestión de juegos"""
    try:
        games = Game.query.all()
        return render_template('admin/juegos.html', games=games)
    except SQLAlchemyError as e:
        log_db_error('juegos', e)
        flash('Error al cargar juegos', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/juego/nuevo', methods=['GET', 'POST'])
@login_required
@admin_required
def nuevo_juego():
    """Crear nuevo juego"""
    try:
        if request.method == 'POST':
            try:
                # Validar campos requeridos
                nombre = request.form.get('nombre', '').strip()
                descripcion = request.form.get('descripcion', '').strip()
                genero = request.form.get('genero', '').strip()
                desarrollador = request.form.get('desarrollador', '').strip()
                
                if not nombre or not descripcion or not genero or not desarrollador:
                    flash('Todos los campos son requeridos', 'danger')
                    return render_template('admin/juego_form.html')
                
                # Validar precio (debe ser positivo)
                try:
                    precio = float(request.form.get('precio', 0))
                    if precio < 0:
                        flash('El precio debe ser positivo', 'danger')
                        return render_template('admin/juego_form.html')
                except (ValueError, TypeError):
                    flash('Precio inválido', 'danger')
                    return render_template('admin/juego_form.html')
                
                # Validar stock (debe ser entero positivo)
                try:
                    stock = int(request.form.get('stock', 0))
                    if stock < 0:
                        flash('El stock debe ser positivo', 'danger')
                        return render_template('admin/juego_form.html')
                except (ValueError, TypeError):
                    flash('Stock inválido', 'danger')
                    return render_template('admin/juego_form.html')
                
                # Validar fecha de lanzamiento
                try:
                    fecha_lanzamiento = datetime.strptime(request.form.get('fecha_lanzamiento', ''), '%Y-%m-%d')
                except (ValueError, TypeError):
                    flash('Fecha de lanzamiento inválida (formato: YYYY-MM-DD)', 'danger')
                    return render_template('admin/juego_form.html')
                
                # Procesar imagen - archivo o URL
                imagen_path = imagen_subida = None
                imagen = request.files.get('imagen')
                imagen_url = request.form.get('imagen_url', '').strip()
                
                if imagen and imagen.filename:
                    # Validar archivo de manera segura
                    from utils.file_validation import validate_file_upload, generate_unique_filename
                    is_valid, error_msg = validate_file_upload(imagen)
                    if not is_valid:
                        flash(f'Error en imagen: {error_msg}', 'danger')
                        return render_template('admin/juego_form.html')
                    
                    # Generar nombre único y guardar
                    filename = generate_unique_filename(imagen.filename)
                    imagen.save(os.path.join(UPLOAD, filename))
                    imagen_path = imagen_subida = url_publica_de_imagen(filename)
                elif imagen_url:
                    # Validar URL de manera segura
                    from utils.file_validation import validate_image_url
                    is_valid, error_msg = validate_image_url(imagen_url)
                    if not is_valid:
                        flash(f'Error en URL de imagen: {error_msg}', 'danger')
                        return render_template('admin/juego_form.html')
                    imagen_path = imagen_url

                # Crear juego
                juego = Game(
                    nombre=nombre,
                    descripcion=descripcion,
                    precio=precio,
                    genero=genero,
                    desarrollador=desarrollador,
                    fecha_lanzamiento=fecha_lanzamiento,
                    requisitos_minimos=request.form.get('requisitos_minimos', ''),
                    requisitos_recomendados=request.form.get('requisitos_recomendados', ''),
                    stock=stock,
                    imagen=imagen_path
                )
                db.session.add(juego)
                commit_con_imagen(imagen_subida)
                flash('Juego creado exitosamente', 'success')
                return redirect(url_for(ADMIN_JUEGOS))
            except SQLAlchemyError as e:
                log_db_error('nuevo_juego', e)
                flash('Error al crear juego', 'danger')
            except OSError as e:
                log_db_error('nuevo_juego (guardar imagen)', e)
                flash('No se pudo guardar la imagen', 'danger')

        return render_template('admin/juego_form.html')
    except SQLAlchemyError as e:
        log_db_error('nuevo_juego', e)
        flash('Error al procesar la solicitud', 'danger')
        return redirect(url_for(ADMIN_JUEGOS))

@admin_bp.route('/admin/juego/<int:game_id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_juego(game_id):
    """Editar juego existente"""
    try:
        game = db.get_or_404(Game, game_id)
        
        if request.method == 'POST':
            try:
                # Validar campos requeridos (misma validación que nuevo_juego)
                nombre = request.form.get('nombre', '').strip()
                descripcion = request.form.get('descripcion', '').strip()
                genero = request.form.get('genero', '').strip()
                desarrollador = request.form.get('desarrollador', '').strip()

                if not nombre or not descripcion or not genero or not desarrollador:
                    flash('Todos los campos son requeridos', 'danger')
                    return render_template('admin/juego_form.html', game=game)

                try:
                    precio = float(request.form.get('precio', 0))
                    if precio < 0:
                        flash('El precio debe ser positivo', 'danger')
                        return render_template('admin/juego_form.html', game=game)
                except (ValueError, TypeError):
                    flash('Precio inválido', 'danger')
                    return render_template('admin/juego_form.html', game=game)

                try:
                    stock = int(request.form.get('stock', 0))
                    if stock < 0:
                        flash('El stock debe ser positivo', 'danger')
                        return render_template('admin/juego_form.html', game=game)
                except (ValueError, TypeError):
                    flash('Stock inválido', 'danger')
                    return render_template('admin/juego_form.html', game=game)

                try:
                    fecha_lanzamiento = datetime.strptime(request.form.get('fecha_lanzamiento', ''), '%Y-%m-%d')
                except (ValueError, TypeError):
                    flash('Fecha de lanzamiento inválida (formato: YYYY-MM-DD)', 'danger')
                    return render_template('admin/juego_form.html', game=game)

                # Actualizar imagen si se proporciona una nueva - archivo o URL
                imagen_subida = imagen_reemplazada = None
                imagen = request.files.get('imagen')
                imagen_url = request.form.get('imagen_url', '').strip()

                if imagen and imagen.filename:
                    # Validar archivo de manera segura
                    from utils.file_validation import validate_file_upload, generate_unique_filename
                    is_valid, error_msg = validate_file_upload(imagen)
                    if not is_valid:
                        flash(f'Error en imagen: {error_msg}', 'danger')
                        return render_template('admin/juego_form.html', game=game)

                    # Generar nombre único y guardar
                    filename = generate_unique_filename(imagen.filename)
                    imagen.save(os.path.join(UPLOAD, filename))
                    imagen_reemplazada, imagen_subida = game.imagen, url_publica_de_imagen(filename)
                    game.imagen = imagen_subida
                elif imagen_url:
                    # Validar URL de manera segura
                    from utils.file_validation import validate_image_url
                    is_valid, error_msg = validate_image_url(imagen_url)
                    if not is_valid:
                        flash(f'Error en URL de imagen: {error_msg}', 'danger')
                        return render_template('admin/juego_form.html', game=game)
                    imagen_reemplazada = game.imagen
                    game.imagen = imagen_url

                # Actualizar datos
                game.nombre = nombre
                game.descripcion = descripcion
                game.precio = precio
                game.genero = genero
                game.desarrollador = desarrollador
                game.fecha_lanzamiento = fecha_lanzamiento
                game.requisitos_minimos = request.form.get('requisitos_minimos', '')
                game.requisitos_recomendados = request.form.get('requisitos_recomendados', '')
                game.stock = stock

                commit_con_imagen(imagen_subida, imagen_reemplazada)
                flash('Juego actualizado exitosamente', 'success')
                return redirect(url_for(ADMIN_JUEGOS))
            except SQLAlchemyError as e:
                log_db_error('editar_juego', e)
                flash('Error al actualizar juego', 'danger')
            except OSError as e:
                log_db_error('editar_juego (guardar imagen)', e)
                flash('No se pudo guardar la imagen', 'danger')

        return render_template('admin/juego_form.html', game=game)
    except SQLAlchemyError as e:
        log_db_error('editar_juego', e)
        flash('Error al procesar la solicitud', 'danger')
        return redirect(url_for(ADMIN_JUEGOS))

@admin_bp.route('/admin/hardware')
@login_required
@admin_required
def hardware():
    """Gestión de hardware"""
    try:
        components = Hardware.query.all()
        return render_template('admin/hardware.html', components=components)
    except SQLAlchemyError as e:
        log_db_error('hardware', e)
        flash('Error al cargar hardware', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/hardware/nuevo', methods=['GET', 'POST'])
@login_required
@admin_required
def nuevo_hardware():
    """Crear nuevo componente de hardware"""
    try:
        if request.method == 'POST':
            try:
                # Validar campos requeridos
                tipo = request.form.get('tipo', '').strip()
                marca = request.form.get('marca', '').strip()
                modelo = request.form.get('modelo', '').strip()
                especificaciones = request.form.get('especificaciones', '').strip()
                
                if not tipo or not marca or not modelo or not especificaciones:
                    flash('Todos los campos son requeridos', 'danger')
                    return render_template('admin/hardware_form.html')
                
                # Validar tipo de hardware
                tipos_validos = ['CPU', 'GPU', 'RAM', 'Motherboard', 'Almacenamiento', 'Fuente de poder', 'Refrigeración', 'Gabinete', 'Otro']
                if tipo not in tipos_validos:
                    flash('Tipo de hardware inválido', 'danger')
                    return render_template('admin/hardware_form.html')
                
                # Validar precio (debe ser positivo)
                try:
                    precio = float(request.form.get('precio', 0))
                    if precio < 0:
                        flash('El precio debe ser positivo', 'danger')
                        return render_template('admin/hardware_form.html')
                except (ValueError, TypeError):
                    flash('Precio inválido', 'danger')
                    return render_template('admin/hardware_form.html')
                
                # Validar stock (debe ser entero positivo)
                try:
                    stock = int(request.form.get('stock', 0))
                    if stock < 0:
                        flash('El stock debe ser positivo', 'danger')
                        return render_template('admin/hardware_form.html')
                except (ValueError, TypeError):
                    flash('Stock inválido', 'danger')
                    return render_template('admin/hardware_form.html')
                
                # Procesar imagen - archivo o URL
                imagen_path = imagen_subida = None
                imagen = request.files.get('imagen')
                imagen_url = request.form.get('imagen_url', '').strip()
                
                if imagen and imagen.filename:
                    # Validar archivo de manera segura
                    from utils.file_validation import validate_file_upload, generate_unique_filename
                    is_valid, error_msg = validate_file_upload(imagen)
                    if not is_valid:
                        flash(f'Error en imagen: {error_msg}', 'danger')
                        return render_template('admin/hardware_form.html')
                    
                    # Generar nombre único y guardar
                    filename = generate_unique_filename(imagen.filename)
                    imagen.save(os.path.join(UPLOAD, filename))
                    imagen_path = imagen_subida = url_publica_de_imagen(filename)
                elif imagen_url:
                    # Validar URL de manera segura
                    from utils.file_validation import validate_image_url
                    is_valid, error_msg = validate_image_url(imagen_url)
                    if not is_valid:
                        flash(f'Error en URL de imagen: {error_msg}', 'danger')
                        return render_template('admin/hardware_form.html')
                    imagen_path = imagen_url

                # Crear componente de hardware
                componente = Hardware(
                    tipo=tipo,
                    marca=marca,
                    modelo=modelo,
                    precio=precio,
                    descripcion=request.form.get('descripcion', ''),
                    especificaciones=especificaciones,
                    stock=stock,
                    imagen=imagen_path
                )
                db.session.add(componente)
                commit_con_imagen(imagen_subida)
                flash('Componente creado exitosamente', 'success')
                return redirect(url_for(ADMIN_HARDWARE))
            except SQLAlchemyError as e:
                log_db_error('nuevo_hardware', e)
                flash('Error al crear componente', 'danger')
            except OSError as e:
                log_db_error('nuevo_hardware (guardar imagen)', e)
                flash('No se pudo guardar la imagen', 'danger')

        return render_template('admin/hardware_form.html')
    except SQLAlchemyError as e:
        log_db_error('nuevo_hardware', e)
        flash('Error al procesar la solicitud', 'danger')
        return redirect(url_for(ADMIN_HARDWARE))

@admin_bp.route('/admin/hardware/<int:hardware_id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_hardware(hardware_id):
    """Editar componente de hardware existente"""
    try:
        component = db.get_or_404(Hardware, hardware_id)
        
        if request.method == 'POST':
            try:
                # Validar campos requeridos (misma validación que nuevo_hardware)
                tipo = request.form.get('tipo', '').strip()
                marca = request.form.get('marca', '').strip()
                modelo = request.form.get('modelo', '').strip()
                especificaciones = request.form.get('especificaciones', '').strip()

                if not tipo or not marca or not modelo or not especificaciones:
                    flash('Todos los campos son requeridos', 'danger')
                    return render_template('admin/hardware_form.html', hardware=component)

                tipos_validos = ['CPU', 'GPU', 'RAM', 'Motherboard', 'Almacenamiento', 'Fuente de poder', 'Refrigeración', 'Gabinete', 'Otro']
                if tipo not in tipos_validos:
                    flash('Tipo de hardware inválido', 'danger')
                    return render_template('admin/hardware_form.html', hardware=component)

                try:
                    precio = float(request.form.get('precio', 0))
                    if precio < 0:
                        flash('El precio debe ser positivo', 'danger')
                        return render_template('admin/hardware_form.html', hardware=component)
                except (ValueError, TypeError):
                    flash('Precio inválido', 'danger')
                    return render_template('admin/hardware_form.html', hardware=component)

                try:
                    stock = int(request.form.get('stock', 0))
                    if stock < 0:
                        flash('El stock debe ser positivo', 'danger')
                        return render_template('admin/hardware_form.html', hardware=component)
                except (ValueError, TypeError):
                    flash('Stock inválido', 'danger')
                    return render_template('admin/hardware_form.html', hardware=component)

                # Actualizar imagen si se proporciona una nueva - archivo o URL
                imagen_subida = imagen_reemplazada = None
                imagen = request.files.get('imagen')
                imagen_url = request.form.get('imagen_url', '').strip()

                if imagen and imagen.filename:
                    # Validar archivo de manera segura
                    from utils.file_validation import validate_file_upload, generate_unique_filename
                    is_valid, error_msg = validate_file_upload(imagen)
                    if not is_valid:
                        flash(f'Error en imagen: {error_msg}', 'danger')
                        return render_template('admin/hardware_form.html', hardware=component)

                    # Generar nombre único y guardar
                    filename = generate_unique_filename(imagen.filename)
                    imagen.save(os.path.join(UPLOAD, filename))
                    imagen_reemplazada, imagen_subida = component.imagen, url_publica_de_imagen(filename)
                    component.imagen = imagen_subida
                elif imagen_url:
                    # Validar URL de manera segura
                    from utils.file_validation import validate_image_url
                    is_valid, error_msg = validate_image_url(imagen_url)
                    if not is_valid:
                        flash(f'Error en URL de imagen: {error_msg}', 'danger')
                        return render_template('admin/hardware_form.html', hardware=component)
                    imagen_reemplazada = component.imagen
                    component.imagen = imagen_url

                # Actualizar datos
                component.tipo = tipo
                component.marca = marca
                component.modelo = modelo
                component.precio = precio
                component.descripcion = request.form.get('descripcion', '')
                component.especificaciones = especificaciones
                component.stock = stock

                commit_con_imagen(imagen_subida, imagen_reemplazada)
                flash('Componente actualizado exitosamente', 'success')
                return redirect(url_for(ADMIN_HARDWARE))
            except SQLAlchemyError as e:
                log_db_error('editar_hardware', e)
                flash('Error al actualizar componente', 'danger')
            except OSError as e:
                log_db_error('editar_hardware (guardar imagen)', e)
                flash('No se pudo guardar la imagen', 'danger')

        return render_template('admin/hardware_form.html', hardware=component)
    except SQLAlchemyError as e:
        log_db_error('editar_hardware', e)
        flash('Error al procesar la solicitud', 'danger')
        return redirect(url_for(ADMIN_HARDWARE))

@admin_bp.route('/admin/ordenes')
@login_required
@admin_required
def ordenes():
    """Gestión de órdenes"""
    try:
        orders = Order.query.order_by(Order.created_at.desc()).all()
        return render_template('admin/ordenes.html', orders=orders)
    except SQLAlchemyError as e:
        log_db_error('ordenes', e)
        flash('Error al cargar órdenes', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/orden/<int:order_id>')
@login_required
@admin_required
def ver_orden(order_id):
    """Ver detalles de una orden"""
    try:
        order = db.get_or_404(Order, order_id)
        return render_template('admin/orden_detalle.html', order=order, estados_destino=estados_destino(order.status))
    except SQLAlchemyError as e:
        log_db_error('ver_orden', e)
        flash('Error al cargar la orden', 'danger')
        return redirect(url_for('admin.ordenes'))

@admin_bp.route('/admin/orden/<int:order_id>/estado', methods=['POST'])
@login_required
@admin_required
def actualizar_estado_orden(order_id):
    """Actualizar estado de una orden"""
    try:
        order = db.get_or_404(Order, order_id)
        nuevo_estado = request.form.get('status')
        # Misma regla de transiciones y de stock que el webhook de MercadoPago
        # (utils/order_stock.py): rejected y cancelled son finales, así que una
        # corrección manual no puede desincronizar el inventario.
        if nuevo_estado not in TRANSICIONES:
            flash('Estado inválido', 'danger')
        elif cambiar_estado_orden(order, nuevo_estado):
            db.session.commit()
            flash('Estado de la orden actualizado', 'success')
        else:
            flash(f'Cambio de estado no está permitido: la orden está "{order.status}" y no puede pasar a "{nuevo_estado}"', 'danger')
        return redirect(url_for('admin.ver_orden', order_id=order_id))
    except SQLAlchemyError as e:
        log_db_error('actualizar_estado_orden', e)
        flash('Error al actualizar estado de la orden', 'danger')
        return redirect(url_for('admin.ver_orden', order_id=order_id))

def retirar_de_carritos_y_wishlists(product_type, product_id):
    """CartItem y Wishlist guardan product_id sin clave foránea: hay que limpiarlos
    a mano, dentro de la misma transacción que borra el producto."""
    CartItem.query.filter_by(product_type=product_type, product_id=product_id).delete()
    Wishlist.query.filter_by(product_type=product_type, product_id=product_id).delete()

@admin_bp.route('/admin/juego/<int:game_id>/eliminar', methods=['POST'])
@login_required
@admin_required
def eliminar_juego(game_id):
    """Eliminar juego existente"""
    try:
        game = db.get_or_404(Game, game_id)
        # game.imagen se guarda como "/static/uploads/<archivo>" (con slash
        # inicial, para usarlo directo en <img src>); compararlo contra UPLOAD
        # ("static/uploads", sin slash) nunca coincidía, así que esta limpieza
        # nunca se ejecutaba -- las imágenes subidas quedaban huérfanas en disco.
        if game.imagen and game.imagen.startswith('/' + UPLOAD):
            try:
                os.remove(game.imagen.lstrip('/'))
            except OSError:
                pass  # Si la imagen no existe, continuamos
        
        retirar_de_carritos_y_wishlists('game', game.id)
        db.session.delete(game)
        db.session.commit()
        flash('Juego eliminado exitosamente', 'success')
        return redirect(url_for(ADMIN_JUEGOS))
    except SQLAlchemyError as e:
        log_db_error('eliminar_juego', e)
        flash('Error al eliminar juego', 'danger')
        return redirect(url_for(ADMIN_JUEGOS))

@admin_bp.route('/admin/hardware/<int:hardware_id>/eliminar', methods=['POST'])
@login_required
@admin_required
def eliminar_hardware(hardware_id):
    """Eliminar componente de hardware existente"""
    try:
        component = db.get_or_404(Hardware, hardware_id)
        # Ver comentario equivalente en eliminar_juego(): la comparación original
        # nunca coincidía por el slash inicial, la limpieza nunca se ejecutaba.
        if component.imagen and component.imagen.startswith('/' + UPLOAD):
            try:
                os.remove(component.imagen.lstrip('/'))
            except OSError:
                pass  # Si la imagen no existe, continuamos
        
        retirar_de_carritos_y_wishlists('hardware', component.id)
        db.session.delete(component)
        db.session.commit()
        flash('Componente eliminado exitosamente', 'success')
        return redirect(url_for(ADMIN_HARDWARE))
    except SQLAlchemyError as e:
        log_db_error('eliminar_hardware', e)
        flash('Error al eliminar componente', 'danger')
        return redirect(url_for(ADMIN_HARDWARE))