from flask import Blueprint, render_template, request, jsonify, current_app
from extensions import db
from models.database_models import Hardware
from utils.compatibilidad import CAMPOS_POR_TIPO, estado_general, verificar_configuracion
from utils.hardware_engine import detectar_cuello, nivel_del_sistema, puntuacion_total, recomendaciones, sistema_de

hardware_bp = Blueprint('hardware', __name__)

@hardware_bp.route('/hardware')
def lista_hardware():
    """Página que muestra todo el hardware disponible"""
    try:
        hardware = Hardware.get_all_hardware()
        current_app.logger.info(f'Hardware encontrado: {len(hardware)} componentes')
        
        # Organizar por categorías
        categorias = {}
        for componente in hardware:
            if componente.tipo not in categorias:
                categorias[componente.tipo] = []
            categorias[componente.tipo].append(componente)
        
        current_app.logger.info(f'Categorías: {list(categorias.keys())}')
        return render_template('hardware.html', hardware=hardware, categorias=categorias)
    except Exception as e:
        current_app.logger.error(f'Error en lista_hardware: {str(e)}')
        raise

@hardware_bp.route('/hardware/categoria/<categoria>')
def hardware_por_categoria(categoria):
    """Página que muestra hardware por categoría específica"""
    componentes = Hardware.get_hardware_by_tipo(categoria)

    if not componentes:
        return render_template('404.html'), 404

    return render_template('hardware_category.html', componentes=componentes, categoria=categoria)

# Espacios del Configurador de PC: el orden, el ícono y el texto vacío de cada tipo (el campo sale de CAMPOS_POR_TIPO).
_ESPACIOS = (
    ('CPU', 'Procesador', 'microchip', 'Selecciona un procesador'),
    ('GPU', 'Tarjeta Gráfica', 'video', 'Selecciona una tarjeta gráfica'),
    ('RAM', 'Memoria RAM', 'memory', 'Selecciona memoria RAM'),
    ('Motherboard', 'Placa Base', 'server', 'Selecciona una placa base'),
    ('Fuente de poder', 'Fuente de Poder', 'plug', 'Selecciona una fuente de poder'),
    ('Refrigeración', 'Refrigeración', 'fan', 'Selecciona un enfriador'),
    ('Gabinete', 'Gabinete', 'box', 'Selecciona un gabinete'),
)


def espacios_del_configurador():
    return [{'tipo': tipo, 'campo': CAMPOS_POR_TIPO[tipo], 'etiqueta': etiqueta, 'icono': icono, 'texto': texto}
            for tipo, etiqueta, icono, texto in _ESPACIOS]


@hardware_bp.route('/configurador-pc')
def configurador_pc():
    """Página del configurador de PC interactivo"""
    return render_template('pc_builder.html', slots=espacios_del_configurador())


@hardware_bp.route('/api/verificar-configuracion', methods=['POST'])
def api_verificar_configuracion():
    """Compatibilidad de las piezas elegidas más el rendimiento del equipo (ambos salen del motor único).

    Recibe cualquier subconjunto de los campos de CAMPOS_POR_TIPO (cpu_id, gpu_id, ram_id, placa_id, fuente_id,
    enfriador_id, gabinete_id) y verifica cada par de piezas que se pueda evaluar.
    """
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify({'error': 'No se recibieron datos'}), 400

    piezas = {}
    for tipo, campo in CAMPOS_POR_TIPO.items():
        valor = datos.get(campo)
        if valor in (None, ''):
            continue
        try:
            identificador = int(valor)
        except (TypeError, ValueError):
            return jsonify({'error': f'Identificador inválido en {campo}'}), 400
        componente = db.session.get(Hardware, identificador)
        if componente is None:
            return jsonify({'error': f'Componente no encontrado en {campo}'}), 404
        if componente.tipo != tipo:
            return jsonify({'error': f'El componente de {campo} no es del tipo {tipo}'}), 400
        piezas[campo] = componente
    if not piezas:
        return jsonify({'error': 'Elige al menos un componente'}), 400

    try:
        verificaciones = verificar_configuracion(
            cpu=piezas.get('cpu_id'), gpu=piezas.get('gpu_id'), ram=piezas.get('ram_id'), placa=piezas.get('placa_id'),
            fuente=piezas.get('fuente_id'), enfriador=piezas.get('enfriador_id'), gabinete=piezas.get('gabinete_id'))
        sistema = sistema_de(piezas.get('cpu_id'), piezas.get('gpu_id'), piezas.get('ram_id'))
        cuello = detectar_cuello(sistema)
        total = puntuacion_total(sistema)
        return jsonify({
            'success': True,
            'estado': estado_general(verificaciones),
            'verificaciones': verificaciones,
            'rendimiento': {'total': total, 'nivel': nivel_del_sistema(total), 'faltantes': sistema.faltantes},
            'cuello': cuello,
            'recomendaciones': recomendaciones(sistema, cuello),
        })
    except Exception:
        current_app.logger.exception('Error en api_verificar_configuracion')
        return jsonify({'error': 'Error del servidor al verificar la configuración'}), 500


@hardware_bp.route('/api/hardware/tipos')
def api_tipos_hardware():
    """API para obtener tipos de hardware disponibles"""
    hardware = Hardware.get_all_hardware()
    tipos = {componente.tipo for componente in hardware}

    return jsonify({'tipos': sorted(tipos)})

@hardware_bp.route('/api/hardware/por-tipo/<tipo>')
def api_hardware_por_tipo(tipo):
    """API para obtener hardware filtrado estrictamente por tipo"""
    try:
        componentes = Hardware.query.filter(Hardware.tipo.ilike(tipo)).all()
        resultados = []
        for c in componentes:
            try:
                resultados.append({
                    'id': c.id,
                    'tipo': c.tipo,
                    'marca': c.marca,
                    'modelo': c.modelo,
                    'precio': float(c.precio),
                    'descripcion': c.descripcion,
                    'imagen': c.imagen,
                    'especificaciones': c.get_especificaciones(),
                    'stock': c.stock,
                    'benchmark_score': c.benchmark_score or 0,
                    'socket': c.socket or '',
                    'vram_gb': c.vram_gb or 0,
                    'cores': c.cores or 0,
                    'threads': c.threads or 0,
                })
            except Exception as e:
                current_app.logger.error(f'Error procesando componente {c.id}: {str(e)}')
                continue
        return jsonify({'resultados': resultados})
    except Exception as e:
        current_app.logger.error(f'Error en api_hardware_por_tipo: {str(e)}')
        return jsonify({'error': str(e), 'resultados': []}), 500

@hardware_bp.route('/api/hardware/buscar')
def api_buscar_hardware():
    """API para buscar hardware"""
    try:
        query = request.args.get('q', '')
        current_app.logger.info('API buscar hardware llamado')
        
        resultados = Hardware.buscar_hardware(query)
        current_app.logger.info(f'Resultados encontrados: {len(resultados)}')

        hardware_data = []
        for componente in resultados:
            try:
                hardware_data.append({
                    'id': componente.id,
                    'tipo': componente.tipo,
                    'marca': componente.marca,
                    'modelo': componente.modelo,
                    'precio': float(componente.precio),
                    'descripcion': componente.descripcion,
                    'imagen': componente.imagen,
                    'especificaciones': componente.get_especificaciones(),
                    'stock': componente.stock
                })
            except Exception as e:
                current_app.logger.error(f'Error procesando componente {componente.id}: {str(e)}')
                continue

        current_app.logger.info(f'Hardware data serializado: {len(hardware_data)} items')
        return jsonify({'resultados': hardware_data})
    except Exception as e:
        current_app.logger.error(f'Error en api_buscar_hardware: {str(e)}')
        return jsonify({'error': str(e), 'resultados': []}), 500

@hardware_bp.route('/comparar-hardware', methods=['POST'])
def comparar_hardware():
    """Comparar componentes de hardware seleccionados"""
    data = request.get_json()
    componentes_ids = data.get('componentes', [])

    componentes = []
    for cid in componentes_ids:
        componente = Hardware.get_hardware_by_id(cid)
        if componente:
            componentes.append(componente)

    if not componentes:
        return jsonify({'error': 'No se encontraron componentes para comparar'}), 400

    # Crear tabla de comparación
    comparacion = {
        'componentes': [],
        'caracteristicas': {}
    }

    caracteristicas_comunes = set()
    for componente in componentes:
        comp_data = {
            'id': componente.id,
            'tipo': componente.tipo,
            'marca': componente.marca,
            'modelo': componente.modelo,
            'precio': float(componente.precio),
            'imagen': componente.imagen
        }
        comparacion['componentes'].append(comp_data)

        # Agregar especificaciones
        caracteristicas_comunes.update(componente.get_especificaciones().keys())

    caracteristicas_comunes = sorted(caracteristicas_comunes)

    # Crear matriz de comparación
    for caracteristica in caracteristicas_comunes:
        comparacion['caracteristicas'][caracteristica] = {}
        for componente in componentes:
            valor = componente.get_especificaciones().get(caracteristica, 'N/A')
            comparacion['caracteristicas'][caracteristica][componente.id] = valor

    return jsonify(comparacion)
