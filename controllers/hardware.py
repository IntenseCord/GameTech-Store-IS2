from flask import Blueprint, render_template, request, jsonify, current_app
from models.database_models import Hardware, Game

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

@hardware_bp.route('/configurador-pc')
def configurador_pc():
    """Página del configurador de PC interactivo"""
    hardware = Hardware.get_all_hardware()

    # Organizar por categorías para el configurador
    categorias = {
        'CPU': [h for h in hardware if h.tipo == 'CPU'],
        'GPU': [h for h in hardware if h.tipo == 'GPU'],
        'RAM': [h for h in hardware if h.tipo == 'RAM'],
        'Motherboard': [h for h in hardware if h.tipo == 'Motherboard']
    }

    return render_template('pc_builder.html', categorias=categorias)

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
                    'precio': c.precio,
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
                    'precio': componente.precio,
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
            'precio': componente.precio,
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
