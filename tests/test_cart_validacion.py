"""
Validación de entrada y manejo de errores en controllers/cart.py.

- agregar_al_carrito no debe responder 500 ante datos mal formados.
- Los errores de base de datos muestran un mensaje amable; los errores
  inesperados (bugs) no se esconden: llegan al handler 500 y al log.
- Un item cuyo producto ya no existe (CartItem no tiene clave foránea) se
  retira al mostrar el carrito o el checkout, con aviso al usuario.
"""
from decimal import Decimal

import pytest
from sqlalchemy.exc import OperationalError

import controllers.cart as cart_module
from extensions import db
from models.database_models import CartItem, Order, User

DETALLE_INTERNO = 'detalle-interno-xyz'
PRODUCTO_INEXISTENTE = 99999


def login(client, username='testuser', password='Test1234'):
    return client.post('/login', data={'username': username, 'password': password})


def _falla_de_base_de_datos(*args, **kwargs):
    raise OperationalError('SELECT 1', {}, Exception(DETALLE_INTERNO))


def _bug_inesperado(*args, **kwargs):
    raise RuntimeError(DETALLE_INTERNO)


def _sembrar(user, game):
    """Un item válido en el carrito y una orden propia."""
    db.session.add(CartItem(user_id=user.id, product_type='game', product_id=game.id, quantity=1))
    orden = Order(user_id=user.id, total=10, status='pending')
    db.session.add(orden)
    db.session.commit()
    return orden


# ---------------------------------------------------------------- agregar

@pytest.mark.parametrize('payload', [
    {'product_type': 'game'},
    {'product_type': 'game', 'product_id': None},
    {'product_type': 'game', 'product_id': 'abc'},
    {'product_type': 'game', 'product_id': '1', 'quantity': 'x'},
    {'product_type': 'game', 'product_id': '1', 'quantity': None},
    {'product_type': 'game', 'product_id': '1', 'quantity': ''},
])
def test_agregar_con_numeros_invalidos_devuelve_400(client, test_user, test_game, payload):
    login(client)
    respuesta = client.post('/carrito/agregar', json=payload)
    assert respuesta.status_code == 400
    assert respuesta.get_json()['success'] is False
    assert CartItem.query.count() == 0


@pytest.mark.parametrize('cuerpo', [[1, 2, 3], 'texto', 5])
def test_agregar_con_json_que_no_es_objeto_devuelve_400(client, test_user, cuerpo):
    login(client)
    respuesta = client.post('/carrito/agregar', json=cuerpo)
    assert respuesta.status_code == 400
    assert respuesta.get_json()['success'] is False


def test_agregar_con_json_malformado_devuelve_400(client, test_user):
    login(client)
    respuesta = client.post('/carrito/agregar', data='{no es json', content_type='application/json')
    assert respuesta.status_code == 400


def test_agregar_desde_formulario_sin_product_id_no_da_500(client, test_user):
    login(client)
    respuesta = client.post('/carrito/agregar', data={'product_type': 'game'})
    assert respuesta.status_code == 302
    assert CartItem.query.count() == 0


def test_agregar_con_numeros_como_texto_sigue_funcionando(client, test_user, test_game):
    login(client)
    respuesta = client.post('/carrito/agregar', json={
        'product_type': 'game', 'product_id': str(test_game.id), 'quantity': '2'
    })
    assert respuesta.status_code == 200
    assert CartItem.query.one().quantity == 2


# ------------------------------------------------- errores de base de datos

@pytest.mark.parametrize('ruta, mensaje', [
    ('/carrito', 'Error al cargar el carrito'),
    ('/carrito/checkout', 'Error al procesar el checkout'),
    ('/mis-ordenes', 'No se pudieron cargar tus órdenes'),
    ('/orden/{order_id}', 'Error al cargar la orden'),
])
def test_error_de_base_de_datos_muestra_mensaje_amable_sin_detalles(
        client, test_user, test_game, monkeypatch, ruta, mensaje):
    login(client)
    orden = _sembrar(test_user, test_game)
    monkeypatch.setattr(cart_module, 'render_template', _falla_de_base_de_datos)

    respuesta = client.get(ruta.format(order_id=orden.id), follow_redirects=True)

    assert respuesta.status_code == 200
    assert mensaje.encode() in respuesta.data
    assert DETALLE_INTERNO.encode() not in respuesta.data


# ------------------------------------------------------ errores inesperados

@pytest.mark.parametrize('ruta', ['/carrito', '/carrito/checkout', '/mis-ordenes', '/orden/{order_id}'])
def test_error_inesperado_no_se_esconde_responde_500(
        client, test_user, test_game, monkeypatch, ruta):
    """Un bug (no un fallo de base de datos) no debe disfrazarse de mensaje amable."""
    login(client)
    orden = _sembrar(test_user, test_game)
    monkeypatch.setattr(cart_module, 'render_template', _bug_inesperado)
    monkeypatch.setitem(client.application.config, 'PROPAGATE_EXCEPTIONS', False)

    respuesta = client.get(ruta.format(order_id=orden.id))

    assert respuesta.status_code == 500
    assert DETALLE_INTERNO.encode() not in respuesta.data


# ----------------------------------------------------------- orden_confirmada

def test_orden_inexistente_devuelve_404(client, test_user):
    login(client)
    assert client.get(f'/orden/{PRODUCTO_INEXISTENTE}').status_code == 404


def test_orden_de_otro_usuario_redirige_con_aviso(client, test_user, test_game):
    otro = User(username='otro', email='otro@example.com')
    otro.set_password('Test1234')
    otro.email_verified = True
    db.session.add(otro)
    db.session.commit()
    orden_ajena = _sembrar(otro, test_game)
    login(client)

    respuesta = client.get(f'/orden/{orden_ajena.id}')

    assert respuesta.status_code == 302
    assert 'No tienes permiso'.encode() in client.get('/').data


def test_orden_propia_se_muestra(client, test_user, test_game):
    login(client)
    orden = _sembrar(test_user, test_game)
    assert client.get(f'/orden/{orden.id}').status_code == 200


# -------------------------------------------------------- items huérfanos

def test_subtotal_de_item_huerfano_es_decimal_y_se_puede_sumar(test_user, test_game):
    """get_subtotal devolvía 0.0 (float) para un producto borrado y Decimal para
    uno vigente: sumarlos lanzaba TypeError (Decimal + float)."""
    vigente = CartItem(user_id=test_user.id, product_type='game', product_id=test_game.id, quantity=2)
    huerfano = CartItem(user_id=test_user.id, product_type='hardware',
                        product_id=PRODUCTO_INEXISTENTE, quantity=1)

    assert isinstance(huerfano.get_subtotal(), Decimal)
    assert sum([vigente.get_subtotal(), huerfano.get_subtotal()]) == vigente.get_subtotal()


def _sembrar_con_huerfano(user, game):
    _sembrar(user, game)
    db.session.add(CartItem(user_id=user.id, product_type='hardware',
                            product_id=PRODUCTO_INEXISTENTE, quantity=1))
    db.session.commit()


def test_ver_carrito_retira_items_huerfanos_y_avisa(client, test_user, test_game):
    login(client)
    _sembrar_con_huerfano(test_user, test_game)

    respuesta = client.get('/carrito')

    assert respuesta.status_code == 200
    assert 'ya no están disponibles'.encode() in respuesta.data
    assert [i.product_type for i in CartItem.query.all()] == ['game']


def test_checkout_get_retira_items_huerfanos_y_se_muestra(client, test_user, test_game):
    """Antes: checkout.html revienta con un hardware inexistente y el except
    genérico lo disfrazaba de 'Error al procesar el checkout' (redirect)."""
    login(client)
    _sembrar_con_huerfano(test_user, test_game)

    respuesta = client.get('/carrito/checkout')

    assert respuesta.status_code == 200
    assert 'ya no están disponibles'.encode() in respuesta.data
    assert [i.product_type for i in CartItem.query.all()] == ['game']


def test_checkout_get_con_solo_huerfanos_dice_que_el_carrito_esta_vacio(client, test_user):
    login(client)
    db.session.add(CartItem(user_id=test_user.id, product_type='hardware',
                            product_id=PRODUCTO_INEXISTENTE, quantity=1))
    db.session.commit()

    respuesta = client.get('/carrito/checkout', follow_redirects=True)

    assert 'Tu carrito está vacío'.encode() in respuesta.data
    assert CartItem.query.count() == 0
