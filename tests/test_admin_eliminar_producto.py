"""
Al eliminar un juego o un componente desde el admin deben desaparecer los
items de carrito y de lista de deseos que lo referencian.

CartItem y Wishlist guardan product_id + product_type sin clave foránea, así
que la base de datos no los limpia sola: quedaban huérfanos y el contador del
carrito los seguía contando hasta que el usuario abría el carrito.
"""
import pytest
from flask import g
from sqlalchemy.exc import OperationalError

from extensions import db
from models.database_models import CartItem, Game, Hardware, User, Wishlist


def _crear_usuario(username, admin=False):
    usuario = User(username=username, email=f'{username}@example.com', is_admin=admin, email_verified=True)
    usuario.set_password('Test1234')
    db.session.add(usuario)
    db.session.commit()
    return usuario


def _olvidar_usuario_en_cache():
    """El fixture app_context mantiene un único contexto abierto y Flask-Login
    cachea al usuario en `g`: sin esto, un segundo cliente heredaría al primero."""
    g.pop('_login_user', None)


def _login(client, username):
    _olvidar_usuario_en_cache()
    return client.post('/login', data={'username': username, 'password': 'Test1234'})


def _contador(cliente):
    _olvidar_usuario_en_cache()
    return cliente.get('/api/carrito/count').get_json()['count']


@pytest.fixture
def escenario(app_context, test_game, test_hardware):
    """Dos usuarios con el juego y el hardware en carrito y wishlist, un admin,
    y un segundo juego que no debe tocarse."""
    admin = _crear_usuario('admintest', admin=True)
    ana = _crear_usuario('ana')
    beto = _crear_usuario('beto')
    otro_juego = Game(nombre='Otro', descripcion='d', precio=10, genero='x', desarrollador='d',
                      requisitos_minimos='{}', requisitos_recomendados='{}', stock=3)
    db.session.add(otro_juego)
    db.session.commit()

    for usuario in (ana, beto):
        db.session.add_all([
            CartItem(user_id=usuario.id, product_type='game', product_id=test_game.id, quantity=1),
            CartItem(user_id=usuario.id, product_type='hardware', product_id=test_hardware.id, quantity=1),
            CartItem(user_id=usuario.id, product_type='game', product_id=otro_juego.id, quantity=1),
            Wishlist(user_id=usuario.id, product_type='game', product_id=test_game.id),
            Wishlist(user_id=usuario.id, product_type='hardware', product_id=test_hardware.id),
        ])
    db.session.commit()
    return {'admin': admin, 'ana': ana, 'beto': beto, 'otro_juego': otro_juego}


def _tipos_en_carritos():
    return sorted((i.product_type, i.product_id) for i in CartItem.query.all())


def test_eliminar_juego_retira_sus_items_de_todos_los_carritos_y_wishlists(
        client, escenario, test_game, test_hardware):
    _login(client, 'admintest')

    respuesta = client.post(f'/admin/juego/{test_game.id}/eliminar')

    assert respuesta.status_code == 302
    assert db.session.get(Game, test_game.id) is None
    assert CartItem.query.filter_by(product_type='game', product_id=test_game.id).count() == 0
    assert Wishlist.query.filter_by(product_type='game', product_id=test_game.id).count() == 0


def test_eliminar_juego_no_toca_items_de_hardware_con_el_mismo_id(
        client, escenario, test_game, test_hardware):
    """Game y Hardware tienen ids independientes: borrar el juego N no puede
    afectar al componente N."""
    assert test_game.id == test_hardware.id  # ambos son el primer registro de su tabla
    _login(client, 'admintest')

    client.post(f'/admin/juego/{test_game.id}/eliminar')

    assert CartItem.query.filter_by(product_type='hardware', product_id=test_hardware.id).count() == 2
    assert Wishlist.query.filter_by(product_type='hardware', product_id=test_hardware.id).count() == 2


def test_eliminar_juego_conserva_items_de_otros_productos(client, escenario, test_game):
    _login(client, 'admintest')

    client.post(f'/admin/juego/{test_game.id}/eliminar')

    otro = escenario['otro_juego']
    assert CartItem.query.filter_by(product_type='game', product_id=otro.id).count() == 2


def test_eliminar_hardware_retira_sus_items_y_no_toca_los_del_juego_con_el_mismo_id(
        client, escenario, test_game, test_hardware):
    _login(client, 'admintest')

    respuesta = client.post(f'/admin/hardware/{test_hardware.id}/eliminar')

    assert respuesta.status_code == 302
    assert db.session.get(Hardware, test_hardware.id) is None
    assert CartItem.query.filter_by(product_type='hardware', product_id=test_hardware.id).count() == 0
    assert Wishlist.query.filter_by(product_type='hardware', product_id=test_hardware.id).count() == 0
    assert CartItem.query.filter_by(product_type='game', product_id=test_game.id).count() == 2
    assert Wishlist.query.filter_by(product_type='game', product_id=test_game.id).count() == 2


def test_contador_del_carrito_del_usuario_baja_al_instante(client, app_context, escenario, test_game):
    """Antes el contador seguía contando el item huérfano hasta abrir el carrito."""
    cliente_ana = app_context.test_client()
    _login(cliente_ana, 'ana')
    assert _contador(cliente_ana) == 3

    _login(client, 'admintest')
    _olvidar_usuario_en_cache()
    client.post(f'/admin/juego/{test_game.id}/eliminar')

    assert _contador(cliente_ana) == 2


def test_si_falla_el_commit_no_queda_un_borrado_a_medias(client, escenario, test_game, monkeypatch):
    """El borrado de los items y el del producto van en la misma transacción."""
    _login(client, 'admintest')
    antes = _tipos_en_carritos()

    def commit_falla(self):
        raise OperationalError('COMMIT', {}, Exception('falla simulada'))

    monkeypatch.setattr('sqlalchemy.orm.Session.commit', commit_falla)
    respuesta = client.post(f'/admin/juego/{test_game.id}/eliminar')
    monkeypatch.undo()

    assert respuesta.status_code == 302
    assert db.session.get(Game, test_game.id) is not None
    assert _tipos_en_carritos() == antes
    assert Wishlist.query.filter_by(product_type='game', product_id=test_game.id).count() == 2


def test_eliminar_producto_inexistente_devuelve_404(client, escenario):
    _login(client, 'admintest')
    assert client.post('/admin/juego/99999/eliminar').status_code == 404
    assert client.post('/admin/hardware/99999/eliminar').status_code == 404
