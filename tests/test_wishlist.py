"""
Tests de wishlist.

Regresión: templates/wishlist/index.html tenía dos url_for() rotos —
'hardware.hardware_detalle' (el endpoint real vive en el blueprint
store, no hardware) y 'hardware.hardware' (el endpoint real se llama
'lista_hardware') — ambos lanzaban werkzeug.routing.exceptions.BuildError
y tumbaban la página con un 500 en cuanto se renderizaba una fila de
hardware o el estado de lista vacía.
"""
from extensions import db
from models.database_models import Wishlist


def login(client, username='testuser', password='Test1234'):
    return client.post('/login', data={'username': username, 'password': password})


def test_wishlist_vacia_no_crashea(client, test_user):
    """Regresión del url_for('hardware.hardware') roto en el estado vacío."""
    login(client)
    response = client.get('/wishlist/')
    assert response.status_code == 200


def test_wishlist_con_hardware_no_crashea(client, test_user, test_hardware):
    """Regresión del url_for('hardware.hardware_detalle') roto (debía ser
    'store.hardware_detalle') al renderizar una fila de tipo hardware."""
    login(client)
    db.session.add(Wishlist(user_id=test_user.id, product_id=test_hardware.id, product_type='hardware'))
    db.session.commit()

    response = client.get('/wishlist/')
    assert response.status_code == 200


def test_wishlist_con_juego_no_crashea(client, test_user, test_game):
    login(client)
    db.session.add(Wishlist(user_id=test_user.id, product_id=test_game.id, product_type='game'))
    db.session.commit()

    response = client.get('/wishlist/')
    assert response.status_code == 200
