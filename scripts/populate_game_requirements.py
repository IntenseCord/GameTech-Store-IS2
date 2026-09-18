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

# Datos de requisitos reales de juegos populares
GAME_REQUIREMENTS_DATA = [
    {
        'game_name': 'Cyberpunk 2077',
        'requirements': {
            'min_cpu_score': 8000,    # i5-3570K / Ryzen 3 3200G
            'min_gpu_score': 7000,    # GTX 780 / RX 470
            'min_ram_gb': 8,
            'min_vram_gb': 3,
            
            'rec_cpu_score': 12000,   # i7-4790 / Ryzen 5 3600
            'rec_gpu_score': 14000,   # RTX 2060 / RX 5700 XT
            'rec_ram_gb': 12,
            'rec_vram_gb': 6,
            
            'ultra_cpu_score': 15000, # i7-12700K / Ryzen 7 7700X
            'ultra_gpu_score': 20000, # RTX 3080 / RX 7900 XT
            'ultra_ram_gb': 20,
            'ultra_vram_gb': 10,
            
            'storage_gb': 70,
            'directx_version': 'DX12',
            'requires_ssd': True
        }
    },
    {
        'game_name': 'Red Dead Redemption 2',
        'requirements': {
            'min_cpu_score': 7500,
            'min_gpu_score': 6000,
            'min_ram_gb': 8,
            'min_vram_gb': 2,
            
            'rec_cpu_score': 11000,
            'rec_gpu_score': 12000,
            'rec_ram_gb': 12,
            'rec_vram_gb': 6,
            
            'ultra_cpu_score': 14000,
            'ultra_gpu_score': 18000,
            'ultra_ram_gb': 16,
            'ultra_vram_gb': 8,
            
            'storage_gb': 150,
            'directx_version': 'DX12',
            'requires_ssd': False
        }
    },
    {
        'game_name': 'Elden Ring',
        'requirements': {
            'min_cpu_score': 8000,
            'min_gpu_score': 7000,
            'min_ram_gb': 12,
            'min_vram_gb': 3,
            
            'rec_cpu_score': 10000,
            'rec_gpu_score': 12000,
            'rec_ram_gb': 16,
            'rec_vram_gb': 6,
            
            'ultra_cpu_score': 13000,
            'ultra_gpu_score': 16000,
            'ultra_ram_gb': 16,
            'ultra_vram_gb': 8,
            
            'storage_gb': 60,
            'directx_version': 'DX12',
            'requires_ssd': False
        }
    },
    {
        'game_name': 'Call of Duty',
        'requirements': {
            'min_cpu_score': 9000,
            'min_gpu_score': 8000,
            'min_ram_gb': 8,
            'min_vram_gb': 3,
            
            'rec_cpu_score': 12000,
            'rec_gpu_score': 14000,
            'rec_ram_gb': 16,
            'rec_vram_gb': 6,
            
            'ultra_cpu_score': 15000,
            'ultra_gpu_score': 19000,
            'ultra_ram_gb': 16,
            'ultra_vram_gb': 8,
            
            'storage_gb': 125,
            'directx_version': 'DX12',
            'requires_ssd': True
        }
    },
    {
        'game_name': 'Fortnite',
        'requirements': {
            'min_cpu_score': 6000,
            'min_gpu_score': 5000,
            'min_ram_gb': 8,
            'min_vram_gb': 2,
            
            'rec_cpu_score': 9000,
            'rec_gpu_score': 10000,
            'rec_ram_gb': 16,
            'rec_vram_gb': 4,
            
            'ultra_cpu_score': 12000,
            'ultra_gpu_score': 14000,
            'ultra_ram_gb': 16,
            'ultra_vram_gb': 6,
            
            'storage_gb': 30,
            'directx_version': 'DX11',
            'requires_ssd': False
        }
    },
    {
        'game_name': 'The Witcher 3',
        'requirements': {
            'min_cpu_score': 7000,
            'min_gpu_score': 6000,
            'min_ram_gb': 6,
            'min_vram_gb': 2,
            
            'rec_cpu_score': 9500,
            'rec_gpu_score': 10000,
            'rec_ram_gb': 8,
            'rec_vram_gb': 3,
            
            'ultra_cpu_score': 12000,
            'ultra_gpu_score': 14000,
            'ultra_ram_gb': 16,
            'ultra_vram_gb': 6,
            
            'storage_gb': 50,
            'directx_version': 'DX11',
            'requires_ssd': False
        }
    },
    {
        'game_name': 'Valorant',
        'requirements': {
            'min_cpu_score': 5000,
            'min_gpu_score': 4000,
            'min_ram_gb': 4,
            'min_vram_gb': 1,
            
            'rec_cpu_score': 8000,
            'rec_gpu_score': 7000,
            'rec_ram_gb': 8,
            'rec_vram_gb': 2,
            
            'ultra_cpu_score': 10000,
            'ultra_gpu_score': 10000,
            'ultra_ram_gb': 16,
            'ultra_vram_gb': 4,
            
            'storage_gb': 20,
            'directx_version': 'DX11',
            'requires_ssd': False
        }
    },
    {
        'game_name': 'Minecraft',
        'requirements': {
            'min_cpu_score': 4000,
            'min_gpu_score': 3000,
            'min_ram_gb': 4,
            'min_vram_gb': 1,
            
            'rec_cpu_score': 7000,
            'rec_gpu_score': 6000,
            'rec_ram_gb': 8,
            'rec_vram_gb': 2,
            
            'ultra_cpu_score': 10000,
            'ultra_gpu_score': 10000,
            'ultra_ram_gb': 16,
            'ultra_vram_gb': 4,
            
            'storage_gb': 4,
            'directx_version': 'DX11',
            'requires_ssd': False
        }
    },
    {
        'game_name': 'Grand Theft Auto V',
        'requirements': {
            'min_cpu_score': 6500,
            'min_gpu_score': 5500,
            'min_ram_gb': 8,
            'min_vram_gb': 2,
            
            'rec_cpu_score': 9000,
            'rec_gpu_score': 10000,
            'rec_ram_gb': 8,
            'rec_vram_gb': 4,
            
            'ultra_cpu_score': 12000,
            'ultra_gpu_score': 14000,
            'ultra_ram_gb': 16,
            'ultra_vram_gb': 6,
            
            'storage_gb': 72,
            'directx_version': 'DX11',
            'requires_ssd': False
        }
    },
    {
        'game_name': 'Apex Legends',
        'requirements': {
            'min_cpu_score': 7000,
            'min_gpu_score': 6000,
            'min_ram_gb': 6,
            'min_vram_gb': 1,
            
            'rec_cpu_score': 9000,
            'rec_gpu_score': 10000,
            'rec_ram_gb': 8,
            'rec_vram_gb': 4,
            
            'ultra_cpu_score': 12000,
            'ultra_gpu_score': 14000,
            'ultra_ram_gb': 16,
            'ultra_vram_gb': 6,
            
            'storage_gb': 56,
            'directx_version': 'DX11',
            'requires_ssd': False
        }
    },
    {
        'game_name': 'Spider-Man',
        'requirements': {
            'min_cpu_score': 8500,
            'min_gpu_score': 7500,
            'min_ram_gb': 8,
            'min_vram_gb': 3,
            
            'rec_cpu_score': 11000,
            'rec_gpu_score': 12000,
            'rec_ram_gb': 16,
            'rec_vram_gb': 6,
            
            'ultra_cpu_score': 14000,
            'ultra_gpu_score': 18000,
            'ultra_ram_gb': 16,
            'ultra_vram_gb': 8,
            
            'storage_gb': 75,
            'directx_version': 'DX12',
            'requires_ssd': True
        }
    },
    {
        'game_name': 'God of War',
        'requirements': {
            'min_cpu_score': 8000,
            'min_gpu_score': 7000,
            'min_ram_gb': 8,
            'min_vram_gb': 3,
            
            'rec_cpu_score': 10500,
            'rec_gpu_score': 12000,
            'rec_ram_gb': 16,
            'rec_vram_gb': 6,
            
            'ultra_cpu_score': 13500,
            'ultra_gpu_score': 17000,
            'ultra_ram_gb': 16,
            'ultra_vram_gb': 8,
            
            'storage_gb': 70,
            'directx_version': 'DX11',
            'requires_ssd': True
        }
    }
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
