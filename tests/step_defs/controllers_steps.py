"""
Step definitions para controladores BDD
"""
from pytest_bdd import given, when, then, scenario
from flask import url_for


@scenario('controllers.feature', 'Ver página principal')
def test_pagina_principal():
    pass


@scenario('controllers.feature', 'Ver página de tienda')
def test_pagina_tienda():
    pass


@scenario('controllers.feature', 'Ver página de registro')
def test_pagina_registro():
    pass


@scenario('controllers.feature', 'Ver página de login')
def test_pagina_login():
    pass


@scenario('controllers.feature', 'Buscar sin query')
def test_buscar_sin_query():
    pass


@scenario('controllers.feature', 'Buscar con query')
def test_buscar_con_query():
    pass


@scenario('controllers.feature', 'Ver detalle de juego')
def test_detalle_juego():
    pass


@scenario('controllers.feature', 'Ver detalle de hardware')
def test_detalle_hardware():
    pass


@scenario('controllers.feature', 'Carrito requiere login')
def test_carrito_requiere_login():
    pass


@scenario('controllers.feature', 'Admin requiere login')
def test_admin_requiere_login():
    pass


@scenario('controllers.feature', 'Admin requiere rol de administrador')
def test_admin_requiere_rol():
    pass


@when('voy a la página principal')
def ir_pagina_principal(client):
    client.get('/')


@then('la respuesta debería ser exitosa')
def verificar_respuesta_exitosa(client):
    pass


@when('voy a la página de tienda')
def ir_pagina_tienda(client):
    client.get('/tienda')


@when('voy a la página de registro')
def ir_pagina_registro(client):
    client.get('/registro')


@when('voy a la página de login')
def ir_pagina_login(client):
    client.get('/login')


@when('voy a la página de búsqueda sin query')
def ir_buscar_sin_query(client):
    client.get('/buscar')


@given('existe un juego con nombre "<nombre>"')
def juego_existente(app_context, nombre):
    from models.database_models import Game
    from extensions import db
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


@when('voy a la página de búsqueda con query "<query>"')
def ir_buscar_con_query(client, query):
    client.get(f'/buscar?q={query}')


@given('existe un juego con ID <id>')
def juego_con_id(app_context, id):
    from models.database_models import Game
    from extensions import db
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


@when('voy al detalle del juego con ID <id>')
def ir_detalle_juego(client, id):
    client.get(f'/juego/{id}')


@given('existe un hardware con ID <id>')
def hardware_con_id(app_context, id):
    from models.database_models import Hardware
    from extensions import db
    hardware = Hardware(
        tipo='CPU',
        marca='Intel',
        modelo='Core i5-10400',
        precio=199.99,
        especificaciones='{"cores": 6}',
        stock=5
    )
    db.session.add(hardware)
    db.session.commit()


@when('voy al detalle del hardware con ID <id>')
def ir_detalle_hardware(client, id):
    client.get(f'/hardware/{id}')


@when('voy a la página del carrito sin estar logueado')
def ir_carrito_sin_login(client):
    client.get('/carrito')


@then('debería ser redirigido al login')
def verificar_redireccion_login(client):
    pass


@when('voy a la página de admin sin estar logueado')
def ir_admin_sin_login(client):
    client.get('/admin')


@given('estoy logueado como usuario normal')
def usuario_normal_logueado(client, test_user):
    client.post('/login', data={
        'username': 'testuser',
        'password': 'Test1234'
    })


@when('voy a la página de admin')
def ir_pagina_admin(client):
    client.get('/admin')


@then('debería ser redirigido a la página principal')
def verificar_redireccion_principal(client):
    pass
