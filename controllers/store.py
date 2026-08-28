from flask import Blueprint, render_template, request, jsonify
from models.database_models import Game, Hardware
from models.compatibility import Compatibility

store_bp = Blueprint('store', __name__)

@store_bp.route('/tienda')
def tienda():
    """Página principal de la tienda con paginación"""
    try:
        # Obtener parámetros de paginación
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 12, type=int)
        
        # Obtener filtros
        categoria = request.args.get('categoria', '')
        precio_min = request.args.get('precio_min', type=float)
        precio_max = request.args.get('precio_max', type=float)
        ordenar = request.args.get('ordenar', 'nombre')
        
        # Query de juegos
        juegos_query = Game.query
        
        # Aplicar filtros
        if categoria:
            juegos_query = juegos_query.filter_by(genero=categoria)
        if precio_min:
            juegos_query = juegos_query.filter(Game.precio >= precio_min)
        if precio_max:
            juegos_query = juegos_query.filter(Game.precio <= precio_max)
        
        # Aplicar ordenamiento
        if ordenar == 'precio_asc':
            juegos_query = juegos_query.order_by(Game.precio.asc())
        elif ordenar == 'precio_desc':
            juegos_query = juegos_query.order_by(Game.precio.desc())
        elif ordenar == 'nombre':
            juegos_query = juegos_query.order_by(Game.nombre.asc())
        
        # Paginar
        juegos_paginados = juegos_query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Hardware (sin paginación por ahora)
        hardware = Hardware.get_all_hardware()
        
        return render_template('store.html', 
                             juegos=juegos_paginados.items,
                             pagination=juegos_paginados,
                             hardware=hardware,
                             categoria=categoria,
                             precio_min=precio_min,
                             precio_max=precio_max,
                             ordenar=ordenar)
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'Error en tienda: {str(e)}')
        return render_template('500.html'), 500

@store_bp.route('/juego/<int:juego_id>')
def juego_detalle(juego_id):
    """Página de detalle de un juego específico"""
    try:
        juego = Game.get_game_by_id(juego_id)
        if not juego:
            return render_template('404.html'), 404

        # Obtener juegos relacionados (mismo género)
        juegos_relacionados = Game.query.filter_by(genero=juego.genero).filter(Game.id != juego.id).limit(3).all()

        return render_template('game_detail.html', juego=juego, juegos_relacionados=juegos_relacionados)
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'Error en juego_detalle: {str(e)}')
        return render_template('500.html'), 500

@store_bp.route('/hardware/<int:hardware_id>')
def hardware_detalle(hardware_id):
    """Página de detalle de un componente de hardware"""
    try:
        componente = Hardware.get_hardware_by_id(hardware_id)
        if not componente:
            return render_template('404.html'), 404

        # Obtener hardware relacionado (mismo tipo)
        hardware_relacionado = Hardware.query.filter_by(tipo=componente.tipo).filter(Hardware.id != hardware_id).limit(3).all()

        return render_template('hardware_detail.html', componente=componente, hardware_relacionado=hardware_relacionado)
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'Error en hardware_detalle: {str(e)}')
        return render_template('500.html'), 500

@store_bp.route('/consultar-compatibilidad', methods=['POST'])
def consultar_compatibilidad():
    """Consultar compatibilidad de juegos con hardware específico"""
    try:
        data = request.get_json()

        # Obtener especificaciones del hardware del usuario
        hardware_usuario = {
            'cpu': data.get('cpu', ''),
            'ram': data.get('ram', ''),
            'gpu': data.get('gpu', ''),
            'storage': data.get('storage', '')
        }

        # Obtener juegos compatibles
        juegos_compatibles = Game.get_games_by_hardware(hardware_usuario)

        # Crear lista de juegos para enviar al frontend
        juegos_data = [juego.to_dict() for juego in juegos_compatibles]

        return jsonify({
            'success': True,
            'juegos': juegos_data,
            'total': len(juegos_data)
        })
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'Error en consultar_compatibilidad: {str(e)}')
        return jsonify({'success': False, 'error': 'Error al consultar compatibilidad'}), 500

@store_bp.route('/verificar-setup-completo', methods=['POST'])
def verificar_setup_completo():
    """Verificar compatibilidad de un setup completo con juegos seleccionados"""
    try:
        data = request.get_json()

        juegos_seleccionados_ids = data.get('juegos', [])
        componentes_seleccionados_ids = data.get('componentes', [])

        # Obtener objetos de juegos y componentes
        juegos = [Game.get_game_by_id(jid) for jid in juegos_seleccionados_ids if Game.get_game_by_id(jid)]
        componentes = [Hardware.get_hardware_by_id(cid) for cid in componentes_seleccionados_ids if Hardware.get_hardware_by_id(cid)]

        # Verificar compatibilidad
        resultado = Compatibility.verificar_compatibility_completa(juegos, componentes)

        # Calcular precio total
        precio_total = sum(componente.precio for componente in componentes) + sum(juego.precio for juego in juegos)

        return jsonify({
            'success': True,
            'compatible': resultado['compatible'],
            'detalles': resultado['detalles'],
            'precio_total': precio_total,
            'componentes_count': len(componentes),
            'juegos_count': len(juegos)
        })
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'Error en verificar_setup_completo: {str(e)}')
        return jsonify({'success': False, 'error': 'Error al verificar setup completo'}), 500

@store_bp.route('/buscar')
def buscar():
    """Página de búsqueda de productos"""
    try:
        query = request.args.get('q', '')

        if not query:
            return render_template('search.html', resultados=[], query='')

        # Buscar en juegos usando el método de la base de datos
        juegos_resultados = Game.search_games(query)

        # Buscar en hardware
        hardware_resultados = Hardware.buscar_hardware(query)

        resultados = {
            'juegos': juegos_resultados,
            'hardware': hardware_resultados
        }

        return render_template('search.html', resultados=resultados, query=query)
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'Error en buscar: {str(e)}')
        return render_template('500.html'), 500
