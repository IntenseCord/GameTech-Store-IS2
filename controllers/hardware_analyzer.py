"""
Controlador para el analizador de hardware
Permite a los usuarios analizar su configuración y ver compatibilidad con juegos.

Es una vista del motor único (utils/hardware_engine.py): no calcula nada por su cuenta.
"""
from flask import Blueprint, render_template, request, jsonify, current_app
from extensions import db
from models.database_models import Hardware, Game, GameRequirements
from utils.hardware_engine import (
    SIN_DATOS, categoria_de, detectar_cuello, evaluar_juego, nivel_del_sistema, puntuacion_total,
    recomendaciones, sistema_de,
)

analyzer_bp = Blueprint('analyzer', __name__)

PUNTOS_POR_GB_RAM = 100


@analyzer_bp.route('/analizador-hardware')
def hardware_analyzer_page():
    """Página principal del analizador de hardware"""
    # Cargar componentes para los selectores
    cpus = Hardware.get_hardware_by_tipo('CPU')
    gpus = Hardware.get_hardware_by_tipo('GPU')
    rams = Hardware.get_hardware_by_tipo('RAM')

    return render_template('hardware_checker.html',
                         cpus=cpus,
                         gpus=gpus,
                         rams=rams)


@analyzer_bp.route('/api/analizar-hardware', methods=['POST'])
def analyze_hardware():
    """API para analizar la configuración del usuario"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400

        cpu_id = data.get('cpu_id')
        gpu_id = data.get('gpu_id')
        ram_id = data.get('ram_id')

        # Validar datos
        if not all([cpu_id, gpu_id, ram_id]):
            return jsonify({'error': 'Faltan componentes'}), 400

        # Obtener componentes
        cpu = db.session.get(Hardware, cpu_id)
        gpu = db.session.get(Hardware, gpu_id)
        ram = db.session.get(Hardware, ram_id)

        if not all([cpu, gpu, ram]):
            return jsonify({'error': 'Uno o más componentes no encontrados'}), 404

        # Validar tipos
        if cpu.tipo != 'CPU' or gpu.tipo != 'GPU' or ram.tipo != 'RAM':
            return jsonify({'error': 'Tipos de componentes incorrectos'}), 400

        sistema = sistema_de(cpu, gpu, ram)
        cuello = detectar_cuello(sistema)

        return jsonify({
            'success': True,
            'system_score': _puntuacion_del_sistema(sistema, cpu, gpu, ram),
            'bottlenecks': cuello,
            'games': _clasificar_juegos(sistema),
            'recommendations': recomendaciones(sistema, cuello),
        })

    except Exception as e:
        import traceback
        # El detalle va al log; al cliente solo un mensaje genérico (el error no se muestra ni se oculta como "sin problemas")
        current_app.logger.error(f"Error in analyze_hardware: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': 'Error del servidor al analizar el hardware'}), 500


def _puntuacion_del_sistema(sistema, cpu, gpu, ram):
    total = puntuacion_total(sistema)
    return {
        'total': total,
        'cpu_score': sistema.cpu,
        'gpu_score': sistema.gpu,
        'ram_score': sistema.ram_gb * PUNTOS_POR_GB_RAM if sistema.ram_gb else None,
        'ram_gb': sistema.ram_gb,
        'tier': nivel_del_sistema(total),
        'faltantes': sistema.faltantes,
        'components': {
            'cpu': f'{cpu.marca} {cpu.modelo}',
            'gpu': f'{gpu.marca} {gpu.modelo}',
            'ram': f'{sistema.ram_gb}GB RAM' if sistema.ram_gb else f'{ram.marca} {ram.modelo}',
        }
    }


def _clasificar_juegos(sistema):
    """Agrupa los juegos por la calidad que alcanza el equipo (o `sin_datos` si no se puede saber)."""
    grupos = {'can_run_ultra': [], 'can_run_high': [], 'can_run_medium': [], 'can_run_low': [],
              'cannot_run': [], SIN_DATOS: []}
    juegos = Game.get_all_games()
    requisitos = {r.game_id: r for r in GameRequirements.query.all()}
    for juego in juegos:
        evaluacion = evaluar_juego(sistema, requisitos.get(juego.id))
        grupos[categoria_de(evaluacion)].append({
            'id': juego.id,
            'nombre': juego.nombre,
            'imagen': juego.imagen,
            'precio': float(juego.precio),
            'expected_fps': evaluacion['fps'],
            'quality': evaluacion['calidad'] or SIN_DATOS,
            'bottleneck': evaluacion['limitante'],
            'reason': evaluacion['motivo'],
        })
    return grupos
