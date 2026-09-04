"""
Step definitions BDD para controladores.

Ver test_models_bdd.py para el contexto del hallazgo (archivo nunca
descubierto por pytest + `then` vacíos). Reescrito con matching real
(`parsers.parse`) y aserciones sobre `response`.
"""
from pytest_bdd import given, when, then, scenario, parsers
from extensions import db
from models.database_models import Game, Hardware

FEATURE = '../features/controllers.feature'


@scenario(FEATURE, 'Ver página principal')
def test_pagina_principal():
    pass


@scenario(FEATURE, 'Ver página de tienda')
def test_pagina_tienda():
    pass


@scenario(FEATURE, 'Ver página de registro')
def test_pagina_registro():
    pass


@scenario(FEATURE, 'Ver página de login')
def test_pagina_login():
    pass


@scenario(FEATURE, 'Buscar sin query')
def test_buscar_sin_query():
    pass


@scenario(FEATURE, 'Buscar con query')
def test_buscar_con_query():
    pass


@scenario(FEATURE, 'Ver detalle de juego')
def test_detalle_juego():
    pass


@scenario(FEATURE, 'Ver detalle de hardware')
def test_detalle_hardware():
    pass


@scenario(FEATURE, 'Carrito requiere login')
def test_carrito_requiere_login():
    pass


@scenario(FEATURE, 'Admin requiere login')
def test_admin_requiere_login():
    pass


@scenario(FEATURE, 'Admin requiere rol de administrador')
def test_admin_requiere_rol():
    pass


@when('voy a la página principal', target_fixture='response')
def ir_pagina_principal(client):
    return client.get('/')


@then('la respuesta debería ser exitosa')
def verificar_respuesta_exitosa(response):
    assert response.status_code == 200


@when('voy a la página de tienda', target_fixture='response')
def ir_pagina_tienda(client):
    return client.get('/tienda')


@when('voy a la página de registro', target_fixture='response')
def ir_pagina_registro(client):
    return client.get('/registro')


@when('voy a la página de login', target_fixture='response')
def ir_pagina_login(client):
    return client.get('/login')


@when('voy a la página de búsqueda sin query', target_fixture='response')
def ir_buscar_sin_query(client):
    return client.get('/buscar')


@given(parsers.parse('existe un juego con nombre "{nombre}"'), target_fixture='juego')
def juego_existente(app_context, nombre):
    game = Game(
        nombre=nombre,
        descripcion='Test description',
        precio=49.99,
        genero='Acción',
        desarrollador='Test Dev',
        requisitos_minimos='{"cpu": "Intel i3"}',
        requisitos_recomendados='{"cpu": "Intel i5"}',
        stock=10
    )
    db.session.add(game)
    db.session.commit()
    return game


@when(parsers.parse('voy a la página de búsqueda con query "{query}"'), target_fixture='response')
def ir_buscar_con_query(client, query, juego):
    return client.get(f'/buscar?q={query}')


@given(parsers.parse('existe un juego con ID {id:d}'), target_fixture='juego')
def juego_con_id(app_context, id):
    game = Game(
        nombre='Test Game',
        descripcion='Test description',
        precio=49.99,
        genero='Acción',
        desarrollador='Test Dev',
        requisitos_minimos='{"cpu": "Intel i3"}',
        requisitos_recomendados='{"cpu": "Intel i5"}',
        stock=10
    )
    db.session.add(game)
    db.session.commit()
    assert game.id == id
    return game


@when(parsers.parse('voy al detalle del juego con ID {id:d}'), target_fixture='response')
def ir_detalle_juego(client, id, juego):
    return client.get(f'/juego/{id}')


@given(parsers.parse('existe un hardware con ID {id:d}'), target_fixture='hardware_item')
def hardware_con_id(app_context, id):
    hardware_item = Hardware(
        tipo='CPU',
        marca='Intel',
        modelo='Core i5-10400',
        precio=199.99,
        especificaciones='{"cores": 6}',
        stock=5
    )
    db.session.add(hardware_item)
    db.session.commit()
    assert hardware_item.id == id
    return hardware_item


@when(parsers.parse('voy al detalle del hardware con ID {id:d}'), target_fixture='response')
def ir_detalle_hardware(client, id, hardware_item):
    return client.get(f'/hardware/{id}')


@when('voy a la página del carrito sin estar logueado', target_fixture='response')
def ir_carrito_sin_login(client):
    return client.get('/carrito')


@then('debería ser redirigido al login')
def verificar_redireccion_login(response):
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


@when('voy a la página de admin sin estar logueado', target_fixture='response')
def ir_admin_sin_login(client):
    return client.get('/admin')


@given('estoy logueado como usuario normal')
def usuario_normal_logueado(client, test_user):
    client.post('/login', data={
        'username': 'testuser',
        'password': 'Test1234'
    })


@when('voy a la página de admin', target_fixture='response')
def ir_pagina_admin(client):
    return client.get('/admin')


@then('debería ser redirigido a la página principal')
def verificar_redireccion_principal(response):
    assert response.status_code == 302
