from flask import Blueprint, render_template, request, jsonify
from models.database_models import Game, GameRequirements, Hardware
from utils.hardware_engine import SIN_DATOS, Sistema, evaluar_juego, sistema_de
from utils.hardware_resolver import ram_gb_de_texto, resolver_componente

store_bp = Blueprint('store', __name__)

POR_PAGINA_DEFECTO = 12
POR_PAGINA_MAXIMO = 48

@store_bp.route('/tienda')
def tienda():
    """Página principal de la tienda con paginación"""
    try:
        # Obtener parámetros de paginación
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', POR_PAGINA_DEFECTO, type=int)
        per_page = max(1, min(per_page, POR_PAGINA_MAXIMO))
        
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
        if precio_min is not None:
            juegos_query = juegos_query.filter(Game.precio >= precio_min)
        if precio_max is not None:
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

        return render_template('game_detail.html', juego=juego, juegos_relacionados=juegos_relacionados,
                               cpus=Hardware.get_hardware_by_tipo('CPU'), gpus=Hardware.get_hardware_by_tipo('GPU'),
                               rams=Hardware.get_hardware_by_tipo('RAM'))
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

def _requisitos_por_juego(juegos):
    """Un solo SELECT con los requisitos de todos los juegos: {game_id: GameRequirements}."""
    if not juegos:
        return {}
    ids = [j.id for j in juegos]
    return {r.game_id: r for r in GameRequirements.query.filter(GameRequirements.game_id.in_(ids)).all()}


def _sistema_desde_texto(datos):
    """Convierte el texto de la tienda (nombres del catálogo o texto libre) en un Sistema del motor.

    Un componente que se escribió pero no se reconoce (o no tiene benchmark_score) queda como `desconocido`:
    no se inventa una potencia por palabras ("i5" = 70, desconocido = 50) como hacía el motor anterior.
    """
    desconocidos = []

    def puntos(clave, tipo):
        texto = str(datos.get(clave) or '').strip()
        if not texto:
            return None
        componente = resolver_componente(tipo, texto)
        puntuacion = componente.benchmark_score if componente else None
        if not puntuacion or puntuacion <= 0:
            desconocidos.append(clave)
            return None
        return puntuacion

    cpu = puntos('cpu', 'CPU')
    gpu = puntos('gpu', 'GPU')
    texto_ram = str(datos.get('ram') or '').strip()
    ram_gb = ram_gb_de_texto(texto_ram) if texto_ram else None
    if texto_ram and ram_gb is None:
        desconocidos.append('ram')
    indicados = [k for k in ('cpu', 'gpu', 'ram') if str(datos.get(k) or '').strip()]
    return Sistema(cpu=cpu, gpu=gpu, ram_gb=ram_gb, desconocidos=tuple(desconocidos)), indicados


@store_bp.route('/consultar-compatibilidad', methods=['POST'])
def consultar_compatibilidad():
    """Qué juegos puede correr el hardware indicado, evaluado con el mismo motor que el analizador."""
    try:
        datos = request.get_json(silent=True) or {}
        sistema, indicados = _sistema_desde_texto(datos)
        if not indicados:
            return jsonify({'success': False, 'error': 'Indica al menos un componente'}), 400

        juegos = Game.get_all_games()
        requisitos = _requisitos_por_juego(juegos)
        compatibles, sin_datos = [], []
        for juego in juegos:
            evaluacion = evaluar_juego(sistema, requisitos.get(juego.id))
            if evaluacion['estado'] == SIN_DATOS:
                sin_datos.append(juego.id)
            elif evaluacion['puede_correr']:
                compatibles.append({**juego.to_dict(), 'calidad': evaluacion['calidad'],
                                    'fps_estimado': evaluacion['fps'], 'limitante': evaluacion['limitante']})

        return jsonify({
            'success': True,
            'juegos': compatibles,
            'total': len(compatibles),
            'sin_datos': sin_datos,
            'componentes_sin_datos': list(sistema.desconocidos),
        })
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'Error en consultar_compatibilidad: {str(e)}')
        return jsonify({'success': False, 'error': 'Error al consultar compatibilidad'}), 500

@store_bp.route('/verificar-setup-completo', methods=['POST'])
def verificar_setup_completo():
    """Verificar un setup (CPU, GPU y RAM del catálogo) contra los juegos seleccionados, con el motor único."""
    try:
        data = request.get_json(silent=True) or {}

        juegos = [j for j in (Game.get_game_by_id(jid) for jid in data.get('juegos', [])) if j]
        componentes = [c for c in (Hardware.get_hardware_by_id(cid) for cid in data.get('componentes', [])) if c]

        def primero(tipo):
            return next((c for c in componentes if c.tipo == tipo), None)

        sistema = sistema_de(primero('CPU'), primero('GPU'), primero('RAM'))
        requisitos = _requisitos_por_juego(juegos)
        detalles = [{'juego': j.nombre, 'juego_id': j.id, **evaluar_juego(sistema, requisitos.get(j.id))} for j in juegos]
        precio_total = float(sum(c.precio for c in componentes) + sum(j.precio for j in juegos))

        return jsonify({
            'success': True,
            'compatible': bool(detalles) and all(d['puede_correr'] is True for d in detalles),
            'detalles': detalles,
            'sin_datos': [d['juego_id'] for d in detalles if d['estado'] == SIN_DATOS],
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
