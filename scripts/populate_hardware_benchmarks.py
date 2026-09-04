"""
Script para poblar datos de benchmark en hardware existente
Compatible con PostgreSQL (Neon Tech)
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models.database_models import Hardware

# Datos de benchmark reales (aproximados basados en PassMark y 3DMark)
BENCHMARK_DATA = {
    # CPUs - Basado en PassMark CPU Mark
    'CPU': {
        'i9-13900K': {'score': 18000, 'cores': 24, 'threads': 32, 'freq': 3.0, 'tdp': 125},
        'i9-12900K': {'score': 16500, 'cores': 16, 'threads': 24, 'freq': 3.2, 'tdp': 125},
        'i7-13700K': {'score': 15000, 'cores': 16, 'threads': 24, 'freq': 3.4, 'tdp': 125},
        'i7-12700K': {'score': 13500, 'cores': 12, 'threads': 20, 'freq': 3.6, 'tdp': 125},
        'i5-13600K': {'score': 12000, 'cores': 14, 'threads': 20, 'freq': 3.5, 'tdp': 125},
        'i5-12600K': {'score': 10500, 'cores': 10, 'threads': 16, 'freq': 3.7, 'tdp': 125},
        'i5-12400F': {'score': 9000, 'cores': 6, 'threads': 12, 'freq': 2.5, 'tdp': 65},
        'i5-12400': {'score': 9000, 'cores': 6, 'threads': 12, 'freq': 2.5, 'tdp': 65},
        
        'Ryzen 9 7950X': {'score': 17500, 'cores': 16, 'threads': 32, 'freq': 4.5, 'tdp': 170},
        'Ryzen 9 7900X': {'score': 16000, 'cores': 12, 'threads': 24, 'freq': 4.7, 'tdp': 170},
        'Ryzen 7 7700X': {'score': 14000, 'cores': 8, 'threads': 16, 'freq': 4.5, 'tdp': 105},
        'Ryzen 7 5800X3D': {'score': 13000, 'cores': 8, 'threads': 16, 'freq': 3.4, 'tdp': 105},
        'Ryzen 5 7600X': {'score': 10500, 'cores': 6, 'threads': 12, 'freq': 4.7, 'tdp': 105},
        'Ryzen 5 5600X': {'score': 9500, 'cores': 6, 'threads': 12, 'freq': 3.7, 'tdp': 65},
        'Ryzen 5 5600': {'score': 9000, 'cores': 6, 'threads': 12, 'freq': 3.5, 'tdp': 65},
    },
    
    # GPUs - Basado en 3DMark Time Spy Graphics Score
    'GPU': {
        'RTX 4090': {'score': 25000, 'vram': 24, 'tdp': 450},
        'RTX 4080': {'score': 22000, 'vram': 16, 'tdp': 320},
        'RTX 4070 Ti': {'score': 18000, 'vram': 12, 'tdp': 285},
        'RTX 4070': {'score': 16000, 'vram': 12, 'tdp': 200},
        'RTX 4060 Ti': {'score': 14000, 'vram': 8, 'tdp': 160},
        'RTX 4060': {'score': 12000, 'vram': 8, 'tdp': 115},
        
        'RTX 3090': {'score': 19000, 'vram': 24, 'tdp': 350},
        'RTX 3080': {'score': 17000, 'vram': 10, 'tdp': 320},
        'RTX 3070': {'score': 14000, 'vram': 8, 'tdp': 220},
        'RTX 3060 Ti': {'score': 12000, 'vram': 8, 'tdp': 200},
        'RTX 3060': {'score': 10000, 'vram': 12, 'tdp': 170},
        'RTX 3050': {'score': 7500, 'vram': 8, 'tdp': 130},
        
        'RX 7900 XTX': {'score': 21000, 'vram': 24, 'tdp': 355},
        'RX 7900 XT': {'score': 19000, 'vram': 20, 'tdp': 300},
        'RX 7800 XT': {'score': 16000, 'vram': 16, 'tdp': 263},
        'RX 7700 XT': {'score': 14000, 'vram': 12, 'tdp': 245},
        'RX 6800 XT': {'score': 16000, 'vram': 16, 'tdp': 300},
        'RX 6700 XT': {'score': 12000, 'vram': 12, 'tdp': 230},
        'RX 6600 XT': {'score': 9000, 'vram': 8, 'tdp': 160},
        
        'GTX 1660 Super': {'score': 7000, 'vram': 6, 'tdp': 125},
        'GTX 1660': {'score': 6500, 'vram': 6, 'tdp': 120},
        'GTX 1650': {'score': 5000, 'vram': 4, 'tdp': 75},
    }
}

def update_hardware_benchmarks():
    """Actualizar benchmarks de hardware existente"""
    with app.app_context():
        updated_count = 0
        not_found = []

        def update_hardware_properties(hardware, specs, tipo):
            # (columna del modelo, clave en BENCHMARK_DATA, valor por defecto)
            props_map = {
                'CPU': [
                    ('cores', 'cores', 0), ('threads', 'threads', 0),
                    ('frequency_ghz', 'freq', 0.0), ('tdp_watts', 'tdp', 0)
                ],
                'GPU': [
                    ('vram_gb', 'vram', 0), ('tdp_watts', 'tdp', 0)
                ]
            }
            for columna, clave, default in props_map.get(tipo, []):
                setattr(hardware, columna, specs.get(clave, default))

        def process_component(tipo, model_name, specs):
            hardware_items = Hardware.query.filter(
                Hardware.tipo == tipo,
                Hardware.modelo.ilike(f'%{model_name}%')
            ).all()
            if not hardware_items:
                not_found.append(f"{tipo}: {model_name}")
                print(f"  ⚠️  No encontrado: {model_name}")
                return 0
            for hardware in hardware_items:
                hardware.benchmark_score = specs['score']
                update_hardware_properties(hardware, specs, tipo)
                print(f"  ✅ {hardware.marca} {hardware.modelo} - Score: {specs['score']}")
            return len(hardware_items)

        print("=" * 60)
        print("POBLACIÓN DE BENCHMARKS DE HARDWARE")
        print("=" * 60)
        print()

        for tipo, components in BENCHMARK_DATA.items():
            print(f"\n🔧 Procesando {tipo}s...")
            for model_name, specs in components.items():
                updated_count += process_component(tipo, model_name, specs)

        try:
            db.session.commit()
            print("\n" + "=" * 60)
            print(f"✅ Total actualizado: {updated_count} componentes")
            print("=" * 60)

            show_not_found(not_found)

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error al guardar cambios: {e}")
            raise

def show_not_found(not_found):
    if not_found:
        print(f"\n⚠️  No se encontraron {len(not_found)} componentes:")
        for item in not_found[:10]:
            print(f"  - {item}")
        if len(not_found) > 10:
            print(f"  ... y {len(not_found) - 10} más")
        print("\n💡 Estos componentes no están en la base de datos.")
        print("   Agrégalos primero si deseas incluir sus benchmarks.")

if __name__ == '__main__':
    try:
        update_hardware_benchmarks()
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
