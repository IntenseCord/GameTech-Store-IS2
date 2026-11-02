"""
Deja la base de datos con el catálogo completo: juegos, hardware y requisitos de los juegos.

`seed_database` (database.py) solo siembra una base VACÍA. Este comando es el camino para una base que ya tiene datos, por
ejemplo la de Neon: agrega los juegos y componentes que falten, completa los datos de compatibilidad de los existentes (sin tocar
precio, stock ni descripción) y carga los requisitos de cada juego. Es idempotente: repetirlo no duplica ni cambia nada.

Uso:
    python scripts/sincronizar_catalogo.py
"""
import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import agregar_juegos_faltantes, sincronizar_hardware
from models.database_models import GameRequirements
from scripts.populate_game_requirements import populate_game_requirements


def sincronizar_catalogo():
    """Sincroniza juegos, hardware y requisitos; devuelve un resumen de lo que hizo."""
    with app.app_context():
        juegos_agregados = agregar_juegos_faltantes()
        hardware = sincronizar_hardware()
        populate_game_requirements()
        resumen = {
            'juegos_agregados': juegos_agregados,
            'hardware_agregado': hardware['agregados'],
            'hardware_actualizado': hardware['actualizados'],
            'requisitos': GameRequirements.query.count(),
        }
    print('\nResumen de la sincronización del catálogo')
    print(f'Juegos agregados: {len(resumen["juegos_agregados"])}')
    print(f'Hardware agregado: {len(resumen["hardware_agregado"])}')
    print(f'Hardware actualizado: {len(resumen["hardware_actualizado"])}')
    print(f'Requisitos cargados: {resumen["requisitos"]}')
    return resumen


if __name__ == '__main__':
    sincronizar_catalogo()
