"""
Step definitions BDD para la API GraphQL del catálogo (controllers/graphql_api.py).

Complementa a tests/test_graphql_catalogo.py (que verifica cada regla de forma
aislada) con el comportamiento visto por quien consume la API, incluido un
escenario que conecta lo nuevo con lo antiguo: un cambio hecho desde el panel
de administración debe verse en GraphQL.
"""
from pytest_bdd import given, when, then, scenario, parsers

from extensions import db
from models.database_models import Game, Hardware, User

FEATURE = '../features/graphql.feature'


@scenario(FEATURE, 'Pedir solo algunos campos de los juegos')
def test_pedir_solo_algunos_campos():
    pass


@scenario(FEATURE, 'Consultar juegos y hardware en una sola petición')
def test_dos_colecciones_en_una_peticion():
    pass


@scenario(FEATURE, 'Un campo que no existe da un error claro')
def test_campo_inexistente():
    pass


@scenario(FEATURE, 'La API es de solo lectura y no expone datos sensibles')
def test_solo_lectura_sin_datos_sensibles():
    pass


@scenario(FEATURE, 'Un cambio del administrador se ve enseguida en la consulta')
def test_cambio_del_admin_se_ve_en_graphql():
    pass


def graphql(client, consulta):
    return client.post('/graphql', json={'query': consulta}).get_json()


# --- Background ---------------------------------------------------------------

@given('existe un catálogo con juegos y hardware', target_fixture='catalogo')
def catalogo(app_context):
    juegos = [
        Game(nombre='Cyberpunk 2077', descripcion='RPG', precio=59.99, genero='Acción',
             desarrollador='CDPR', stock=10),
        Game(nombre='Minecraft', descripcion='Construcción', precio=26.99, genero='Aventura',
             desarrollador='Mojang', stock=25),
    ]
    hardware = [
        Hardware(tipo='GPU', marca='NVIDIA', modelo='RTX 4060', precio=349.99,
                 especificaciones='{}', stock=6),
        Hardware(tipo='RAM', marca='Corsair', modelo='Vengeance 16GB', precio=89.99,
                 especificaciones='{}', stock=12),
    ]
    db.session.add_all(juegos + hardware)
    db.session.commit()
    return {'juegos': juegos, 'hardware': hardware}


# --- Escenarios de consulta ---------------------------------------------------------

@when(parsers.parse('consulto los juegos pidiendo los campos "{campos}"'), target_fixture='respuesta')
def consultar_juegos_con_campos(client, campos):
    return graphql(client, '{ juegos { ' + campos + ' } }')


@then(parsers.parse('cada juego devuelto tiene solo los campos "{campos}"'))
def verificar_solo_esos_campos(respuesta, campos):
    juegos = respuesta['data']['juegos']
    assert len(juegos) == 2
    for juego in juegos:
        assert set(juego.keys()) == set(campos.split())


@when('consulto juegos y hardware en una sola petición', target_fixture='respuesta')
def consultar_dos_colecciones(client):
    return graphql(client, '{ juegos { nombre } hardware { modelo } }')


@then('recibo ambas colecciones en la misma respuesta')
def verificar_ambas_colecciones(respuesta):
    assert len(respuesta['data']['juegos']) == 2
    assert len(respuesta['data']['hardware']) == 2


@when(parsers.parse('consulto el campo "{campo}" de los juegos'), target_fixture='respuesta')
def consultar_campo_inexistente(client, campo):
    return graphql(client, '{ juegos { ' + campo + ' } }')


@then(parsers.parse('recibo un error que menciona el campo "{campo}"'))
def verificar_error_menciona_campo(respuesta, campo):
    assert campo in respuesta['errors'][0]['message']


# --- Solo lectura y sin datos sensibles ------------------------------------------------

@when('consulto los tipos que expone el esquema', target_fixture='respuesta')
def consultar_tipos_del_esquema(client):
    return graphql(client, '{ __schema { types { name } } }')


@then('no aparecen usuarios, órdenes, facturas ni pagos')
def verificar_sin_datos_sensibles(respuesta):
    nombres = {t['name'] for t in respuesta['data']['__schema']['types']}
    for prohibido in ('User', 'Order', 'OrderItem', 'Invoice', 'CartItem', 'Wishlist'):
        assert prohibido not in nombres


@then('no se puede modificar nada con una mutación')
def verificar_sin_mutaciones(client):
    respuesta = graphql(client, 'mutation { borrarTodo }')
    assert 'errors' in respuesta


# --- Integración con el panel de administración -----------------------------------------------

@given('un administrador con la sesión iniciada')
def administrador_con_sesion(client, catalogo):
    admin = User(username='admin_bdd', email='admin_bdd@example.com', is_admin=True, email_verified=True)
    admin.set_password('Test1234')
    db.session.add(admin)
    db.session.commit()
    client.post('/login', data={'username': 'admin_bdd', 'password': 'Test1234'})


@when('el administrador cambia el stock del primer componente a 9')
def admin_cambia_stock(client, catalogo):
    componente = catalogo['hardware'][0]
    client.post(f'/admin/hardware/{componente.id}/editar', data={
        'tipo': componente.tipo, 'marca': componente.marca, 'modelo': componente.modelo,
        'precio': '349.99', 'stock': '9', 'especificaciones': '{}',
    })


@then('la consulta GraphQL muestra ese componente con stock 9')
def verificar_stock_en_graphql(client, catalogo):
    componente = catalogo['hardware'][0]
    respuesta = graphql(client, f'{{ componente(id: {componente.id}) {{ stock }} }}')
    assert respuesta['data']['componente']['stock'] == 9
