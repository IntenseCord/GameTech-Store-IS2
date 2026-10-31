"""
Script para poblar requisitos de sistema de juegos populares
Compatible con PostgreSQL (Neon Tech)
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models.database_models import Game, GameRequirements
from utils.benchmark_escala import puntaje_cpu, puntaje_gpu

# Requisitos de los juegos del catálogo, CALCULADOS a partir de piezas de referencia con puntaje en la escala única
# del proyecto (utils/benchmark_escala.py): así los requisitos y `Hardware.benchmark_score` quedan en la misma escala.
#
# Niveles (ver GameRequirements): min = 1080p bajo (~30 FPS), rec = 1080p alto (~60 FPS), ultra = 1440p/4K máximo.
#   origen 'publicado': pieza que el desarrollador nombra en sus requisitos oficiales (CPU y GPU de Intel/NVIDIA, la
#                       primera alternativa de la lista; la AMD equivalente da un puntaje parecido).
#   origen 'proyecto' : nivel que el desarrollador no publica; es un criterio del proyecto y puede ajustarse.
# Solo están los juegos del catálogo: los requisitos de los otros 7 juegos que traía este script estaban en la escala
# anterior y no se pueden defender; se agregan de nuevo, con sus piezas de referencia, cuando el juego entre al catálogo.
REFERENCIAS_POR_JUEGO = {
    'Cyberpunk 2077': {
        'min': {'cpu': 'Core i5-3570K', 'gpu': 'GeForce GTX 780', 'ram_gb': 8, 'vram_gb': 3, 'origen': 'publicado',
                'fuente': 'CD Projekt RED, requisitos de lanzamiento (2020): i5-3570K, GTX 780 3 GB, 8 GB'},
        'rec': {'cpu': 'Core i7-4790', 'gpu': 'GeForce GTX 1060', 'ram_gb': 12, 'vram_gb': 6, 'origen': 'publicado',
                'fuente': 'CD Projekt RED, requisitos de lanzamiento (2020): i7-4790, GTX 1060, 12 GB'},
        'ultra': {'cpu': 'Core i7-8700K', 'gpu': 'GeForce RTX 3080', 'ram_gb': 16, 'vram_gb': 10, 'origen': 'proyecto',
                  'fuente': 'criterio del proyecto: 1440p en ultra (CD Projekt RED cita una RTX 3070-3080 para 1440p/4K)'},
    },
    'Elden Ring': {
        'min': {'cpu': 'Core i5-8400', 'gpu': 'GeForce GTX 1060', 'ram_gb': 12, 'vram_gb': 3, 'origen': 'publicado',
                'fuente': 'FromSoftware/Bandai Namco: i5-8400, GTX 1060 3 GB, 12 GB (se usa el puntaje de la GTX 1060 de 6 GB)'},
        'rec': {'cpu': 'Core i7-8700K', 'gpu': 'GeForce GTX 1070', 'ram_gb': 16, 'vram_gb': 8, 'origen': 'publicado',
                'fuente': 'FromSoftware/Bandai Namco: i7-8700K, GTX 1070, 16 GB'},
        'ultra': {'cpu': 'Core i7-8700K', 'gpu': 'GeForce RTX 2060', 'ram_gb': 16, 'vram_gb': 8, 'origen': 'proyecto',
                  'fuente': 'criterio del proyecto: 1440p máximo ~60 FPS; el juego está limitado por el motor, no pide más CPU'},
    },
    'The Witcher 3': {
        'min': {'cpu': 'Core i5-2500K', 'gpu': 'GeForce GTX 660', 'ram_gb': 6, 'vram_gb': 2, 'origen': 'publicado',
                'fuente': 'CD Projekt RED, requisitos originales (2015): i5-2500K, GTX 660, 6 GB'},
        'rec': {'cpu': 'Core i7-3770', 'gpu': 'GeForce GTX 770', 'ram_gb': 8, 'vram_gb': 2, 'origen': 'publicado',
                'fuente': 'CD Projekt RED, requisitos originales (2015): i7-3770, GTX 770, 8 GB'},
        'ultra': {'cpu': 'Core i7-4790', 'gpu': 'GeForce GTX 1070', 'ram_gb': 16, 'vram_gb': 6, 'origen': 'proyecto',
                  'fuente': 'criterio del proyecto: 1440p en ultra'},
    },
    'Grand Theft Auto V': {
        'min': {'cpu': 'Core 2 Quad Q6600', 'gpu': 'GeForce 9800 GT', 'ram_gb': 4, 'vram_gb': 1, 'origen': 'publicado',
                'fuente': 'Rockstar (versión Legacy): Core 2 Quad Q6600, GeForce 9800 GT 1 GB, 4 GB'},
        'rec': {'cpu': 'Core i5-3470', 'gpu': 'GeForce GTX 660', 'ram_gb': 8, 'vram_gb': 2, 'origen': 'publicado',
                'fuente': 'Rockstar (versión Legacy): i5-3470, GTX 660 2 GB, 8 GB'},
        'ultra': {'cpu': 'Core i7-4790', 'gpu': 'GeForce GTX 1060', 'ram_gb': 16, 'vram_gb': 6, 'origen': 'proyecto',
                  'fuente': 'criterio del proyecto: 1440p en muy alto'},
    },
    'Counter-Strike 2': {
        'min': {'cpu': 'Core i5-750', 'gpu': 'GeForce GT 730', 'ram_gb': 8, 'vram_gb': 1, 'origen': 'publicado',
                'fuente': 'Valve: Core i5-750 (4 hilos), 8 GB, GPU DirectX 11 con 1 GB (se usa la GT 730 que lista el catálogo)'},
        'rec': {'cpu': 'Core i7-4790', 'gpu': 'GeForce GTX 1060', 'ram_gb': 16, 'vram_gb': 4, 'origen': 'proyecto',
                'fuente': 'criterio del proyecto: Valve no publica requisitos recomendados'},
        'ultra': {'cpu': 'Core i5-8400', 'gpu': 'GeForce GTX 1070', 'ram_gb': 16, 'vram_gb': 6, 'origen': 'proyecto',
                  'fuente': 'criterio del proyecto: 1440p alto con muchos FPS'},
    },
    # Los tres siguientes: mínimo y recomendado de la ficha de Steam (consultada el 2026-10-30)
    'Red Dead Redemption 2': {
        'min': {'cpu': 'Core i5-2500K', 'gpu': 'GeForce GTX 770', 'ram_gb': 8, 'vram_gb': 2, 'origen': 'publicado',
                'fuente': 'Rockstar (Steam): i5-2500K, GTX 770 2 GB, 8 GB'},
        'rec': {'cpu': 'Core i7-4770K', 'gpu': 'GeForce GTX 1060', 'ram_gb': 12, 'vram_gb': 6, 'origen': 'publicado',
                'fuente': 'Rockstar (Steam): i7-4770K, GTX 1060 6 GB, 12 GB'},
        'ultra': {'cpu': 'Core i7-8700K', 'gpu': 'GeForce GTX 1080 Ti', 'ram_gb': 16, 'vram_gb': 11, 'origen': 'proyecto',
                  'fuente': 'criterio del proyecto: 1440p en ajustes altos con ~60 FPS'},
    },
    "Baldur's Gate 3": {
        'min': {'cpu': 'Core i5-4690', 'gpu': 'GeForce GTX 970', 'ram_gb': 8, 'vram_gb': 4, 'origen': 'publicado',
                'fuente': 'Larian (Steam): i5-4690, GTX 970 (4 GB o más de VRAM), 8 GB, SSD obligatorio'},
        'rec': {'cpu': 'Ryzen 5 3600', 'gpu': 'GeForce RTX 2060 Super', 'ram_gb': 16, 'vram_gb': 8, 'origen': 'publicado',
                'fuente': 'Larian (Steam): Ryzen 5 3600 (o i7-8700K), RTX 2060 Super (8 GB o más de VRAM), 16 GB'},
        'ultra': {'cpu': 'Core i7-8700K', 'gpu': 'GeForce GTX 1080 Ti', 'ram_gb': 16, 'vram_gb': 11, 'origen': 'proyecto',
                  'fuente': 'criterio del proyecto: 1440p en ultra; el acto 3 exige más CPU que GPU'},
    },
    'Apex Legends': {
        'min': {'cpu': 'Core i3-6300', 'gpu': 'GeForce GTX 950', 'ram_gb': 6, 'vram_gb': 2, 'origen': 'publicado',
                'fuente': 'Respawn (Steam): i3-6300, GTX 950 / HD 7790 2 GB, 6 GB'},
        'rec': {'cpu': 'Ryzen 5 3600', 'gpu': 'GeForce GTX 970', 'ram_gb': 8, 'vram_gb': 4, 'origen': 'publicado',
                'fuente': 'Respawn (Steam): "Ryzen 5 o equivalente" sin modelo (se usa el 3600, criterio del proyecto), GTX 970 / R9 290, 8 GB'},
        'ultra': {'cpu': 'Core i7-8700K', 'gpu': 'GeForce GTX 1070', 'ram_gb': 16, 'vram_gb': 8, 'origen': 'proyecto',
                  'fuente': 'criterio del proyecto: 1440p alto con FPS altos (juego competitivo)'},
    },
}

EXTRAS_POR_JUEGO = {
    'Cyberpunk 2077': {'storage_gb': 70, 'directx_version': 'DX12', 'requires_ssd': True},
    'Elden Ring': {'storage_gb': 60, 'directx_version': 'DX12', 'requires_ssd': False},
    'The Witcher 3': {'storage_gb': 50, 'directx_version': 'DX11', 'requires_ssd': False},
    'Grand Theft Auto V': {'storage_gb': 72, 'directx_version': 'DX11', 'requires_ssd': False},
    'Counter-Strike 2': {'storage_gb': 85, 'directx_version': 'DX11', 'requires_ssd': False},
    'Red Dead Redemption 2': {'storage_gb': 150, 'directx_version': 'DX12', 'requires_ssd': False},
    "Baldur's Gate 3": {'storage_gb': 150, 'directx_version': 'DX11', 'requires_ssd': True},
    'Apex Legends': {'storage_gb': 75, 'directx_version': 'DX12', 'requires_ssd': False},
}


def _requisitos_calculados(juego):
    """Arma el diccionario de GameRequirements con los puntajes de las piezas de referencia."""
    requisitos = {}
    for nivel, ref in REFERENCIAS_POR_JUEGO[juego].items():
        requisitos[f'{nivel}_cpu_score'] = puntaje_cpu(ref['cpu'])
        requisitos[f'{nivel}_gpu_score'] = puntaje_gpu(ref['gpu'])
        requisitos[f'{nivel}_ram_gb'] = ref['ram_gb']
        requisitos[f'{nivel}_vram_gb'] = ref['vram_gb']
    requisitos.update(EXTRAS_POR_JUEGO[juego])
    return requisitos


GAME_REQUIREMENTS_DATA = [
    {'game_name': nombre, 'requirements': _requisitos_calculados(nombre)} for nombre in REFERENCIAS_POR_JUEGO
]

def populate_game_requirements():
    """Poblar requisitos de juegos"""
    with app.app_context():
        created_count = 0
        updated_count = 0
        not_found = []
        
        print("="*60)
        print("POBLACIÓN DE REQUISITOS DE JUEGOS")
        print("="*60)
        print()
        
        for game_data in GAME_REQUIREMENTS_DATA:
            game_name = game_data['game_name']
            requirements_data = game_data['requirements']
            
            # Buscar el juego por nombre (búsqueda flexible)
            game = Game.query.filter(
                Game.nombre.ilike(f'%{game_name}%')
            ).first()
            
            if not game:
                not_found.append(game_name)
                print(f"⚠️  Juego no encontrado: {game_name}")
                continue
            
            # Verificar si ya existen requisitos
            existing_req = GameRequirements.get_by_game_id(game.id)
            
            if existing_req:
                # Actualizar requisitos existentes
                for key, value in requirements_data.items():
                    setattr(existing_req, key, value)
                updated_count += 1
                print(f"🔄 Actualizado: {game.nombre}")
            else:
                # Crear nuevos requisitos
                GameRequirements.create_requirements(
                    game_id=game.id,
                    **requirements_data
                )
                created_count += 1
                print(f"✅ Creado: {game.nombre}")
        
        print("\n" + "="*60)
        print(f"✅ Requisitos creados: {created_count}")
        print(f"🔄 Requisitos actualizados: {updated_count}")
        print("="*60)
        
        if not_found:
            print(f"\n⚠️  No se encontraron {len(not_found)} juegos:")
            for game in not_found:
                print(f"  - {game}")
            print("\n💡 Estos juegos no están en la base de datos.")
            print("   Agrégalos primero si deseas incluir sus requisitos.")

if __name__ == '__main__':
    try:
        populate_game_requirements()
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
