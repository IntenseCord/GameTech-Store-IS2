"""
Test de scripts/populate_game_requirements.py.

Regresión: el script buscaba el juego "Grand Theft Auto V" con el apodo
'GTA V', pero Game.nombre.ilike('%GTA V%') no coincide con el nombre real
sembrado en database.py ("Grand Theft Auto V" no contiene la subcadena
"GTA V") -- el juego quedaba siempre sin requisitos de sistema, cayendo
al cálculo de emergencia estimate_quality_without_requirements().
"""
from extensions import db
from models.database_models import Game, GameRequirements
from scripts.populate_game_requirements import populate_game_requirements


def test_puebla_requisitos_de_grand_theft_auto_v(app_context):
    game = Game(
        nombre='Grand Theft Auto V',
        descripcion='Test', precio=59.99, genero='Acción',
        desarrollador='Rockstar', stock=10
    )
    db.session.add(game)
    db.session.commit()

    populate_game_requirements()

    requisitos = GameRequirements.get_by_game_id(game.id)
    assert requisitos is not None, 'Grand Theft Auto V debería tener requisitos poblados por el script'
    assert requisitos.min_cpu_score == 6500
