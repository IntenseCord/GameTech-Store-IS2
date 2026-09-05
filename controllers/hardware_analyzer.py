"""
Controlador para el analizador de hardware
Permite a los usuarios analizar su configuración y ver compatibilidad con juegos
"""
from flask import Blueprint, render_template, request, jsonify, current_app
from models.database_models import Hardware, Game, GameRequirements
from utils.bottleneck_detector import BottleneckDetector
from utils.performance_calculator import PerformanceCalculator

analyzer_bp = Blueprint('analyzer', __name__)

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
        cpu = Hardware.query.get(cpu_id)
        gpu = Hardware.query.get(gpu_id)
        ram = Hardware.query.get(ram_id)
        
        if not all([cpu, gpu, ram]):
            return jsonify({'error': 'Uno o más componentes no encontrados'}), 404
        
        # Validar tipos
        if cpu.tipo != 'CPU' or gpu.tipo != 'GPU' or ram.tipo != 'RAM':
            return jsonify({'error': 'Tipos de componentes incorrectos'}), 400
        
        # 1. Calcular puntuación del sistema
        system_score = calculate_system_score(cpu, gpu, ram)
        
        # 2. Detectar cuellos de botella
        try:
            bottlenecks = BottleneckDetector.detect(cpu, gpu, ram)
        except Exception as e:
            current_app.logger.error(f"Error detecting bottleneck: {str(e)}")
            bottlenecks = {'has_bottleneck': False, 'recommendations': []}
        
        # 3. Analizar compatibilidad con juegos
        try:
            games_analysis = analyze_game_compatibility(cpu, gpu, ram)
        except Exception as e:
            current_app.logger.error(f"Error analyzing games: {str(e)}")
            games_analysis = {
                'can_run_ultra': [],
                'can_run_high': [],
                'can_run_medium': [],
                'can_run_low': [],
                'cannot_run': []
            }
        
        # 4. Generar recomendaciones
        try:
            recommendations = generate_recommendations(bottlenecks, system_score)
        except Exception as e:
            current_app.logger.error(f"Error generating recommendations: {str(e)}")
            recommendations = []
        
        return jsonify({
            'success': True,
            'system_score': system_score,
            'bottlenecks': bottlenecks,
            'games': games_analysis,
            'recommendations': recommendations
        })
    
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error in analyze_hardware: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': f'Error del servidor: {str(e)}'}), 500

def calculate_system_score(cpu, gpu, ram):
    """Calcular puntuación general del sistema"""
    cpu_score = cpu.benchmark_score or 0
    gpu_score = gpu.benchmark_score or 0
    ram_gb = ram.get_ram_capacity_gb() if hasattr(ram, 'get_ram_capacity_gb') else 8
    ram_score = ram_gb * 100  # 16GB = 1600 puntos
    
    # Ponderación: GPU 50%, CPU 35%, RAM 15%
    total = (gpu_score * 0.5) + (cpu_score * 0.35) + (ram_score * 0.15)
    
    return {
        'total': int(total),
        'cpu_score': cpu_score,
        'gpu_score': gpu_score,
        'ram_score': ram_score,
        'ram_gb': ram_gb,
        'tier': get_performance_tier(total),
        'components': {
            'cpu': f'{cpu.marca} {cpu.modelo}',
            'gpu': f'{gpu.marca} {gpu.modelo}',
            'ram': f'{ram_gb}GB RAM'
        }
    }

def get_performance_tier(score):
    """Determinar el nivel de rendimiento"""
    if score >= 15000:
        return 'Ultra High-End (4K Ultra)'
    elif score >= 10000:
        return 'High-End (1440p Ultra)'
    elif score >= 7000:
        return 'Mid-High (1080p Ultra)'
    elif score >= 4000:
        return 'Mid-Range (1080p Medium-High)'
    else:
        return 'Entry Level (1080p Low-Medium)'

def analyze_game_compatibility(cpu, gpu, ram):
    """Analizar qué juegos puede correr el usuario"""
    games = Game.get_all_games()
    
    results = {
        'can_run_ultra': [],
        'can_run_high': [],
        'can_run_medium': [],
        'can_run_low': [],
        'cannot_run': []
    }
    
    if not games:
        return results
    
    for game in games:
        try:
            requirements = GameRequirements.get_by_game_id(game.id)
            
            if not requirements:
                # Si no hay requisitos, estimar basado en benchmark
                quality = estimate_quality_without_requirements(cpu, gpu, ram)
            else:
                # Calcular rendimiento
                performance = PerformanceCalculator.calculate_game_performance(
                    cpu, gpu, ram, requirements
                )
                quality = performance.get('quality', 'medium')
            
            game_data = {
                'id': game.id,
                'nombre': game.nombre,
                'imagen': game.imagen,
                'precio': float(game.precio),
                'expected_fps': 60,
                'quality': quality,
                'bottleneck': None,
                'reason': ''
            }
            
            # Clasificar por calidad
            if quality == 'ultra':
                results['can_run_ultra'].append(game_data)
            elif quality == 'high':
                results['can_run_high'].append(game_data)
            elif quality == 'medium':
                results['can_run_medium'].append(game_data)
            elif quality == 'low':
                results['can_run_low'].append(game_data)
            else:
                results['cannot_run'].append(game_data)
        except Exception as e:
            current_app.logger.error(f"Error analizando juego {game.id}: {e}")
            continue
    
    return results

def estimate_quality_without_requirements(cpu, gpu, ram):
    """Estimar calidad sin requisitos específicos"""
    cpu_score = cpu.benchmark_score or 0
    gpu_score = gpu.benchmark_score or 0
    ram_gb = ram.get_ram_capacity_gb() if hasattr(ram, 'get_ram_capacity_gb') else 8
    
    # Puntuación general
    total_score = (gpu_score * 0.5) + (cpu_score * 0.35) + (ram_gb * 100 * 0.15)
    
    if total_score >= 10000:
        return 'ultra'
    elif total_score >= 7000:
        return 'high'
    elif total_score >= 4000:
        return 'medium'
    elif total_score >= 2000:
        return 'low'
    else:
        return 'cannot_run'

def generate_recommendations(bottlenecks, system_score):
    """Generar recomendaciones de mejora"""
    recommendations = []
    
    # Recomendaciones de bottleneck
    if bottlenecks['has_bottleneck']:
        recommendations.extend(bottlenecks['recommendations'])
    
    # Recomendaciones por tier
    total_score = system_score['total']
    
    if total_score < 7000:
        recommendations.append(
            '💡 Tu sistema es entry-level. Considera actualizar GPU y CPU para mejor experiencia.'
        )
    elif total_score < 10000:
        recommendations.append(
            '💡 Tu sistema es mid-range. Una GPU mejor te daría un salto significativo en rendimiento.'
        )
    
    # Recomendación de RAM
    if system_score['ram_gb'] < 16:
        recommendations.append(
            '💾 16GB de RAM es el estándar actual para gaming. Considera expandir.'
        )
    
    return recommendations
