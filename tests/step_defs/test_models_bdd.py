"""
Step definitions BDD para modelos de base de datos.

Antes de este archivo, todo `then` era `pass` (sin aserciones reales) y el
archivo se llamaba `models_steps.py` (pytest nunca lo descubría porque no
empieza con `test_`) — ver hallazgo de la revisión general del proyecto
(2026-09-04). Ahora cada `@scenario` corre de verdad y cada `@then` afirma
algo comprobable.
"""
from pytest_bdd import given, when, then, scenario, parsers
from extensions import db
from models.database_models import User, Game, Hardware

FEATURE = '../features/models.feature'


@scenario(FEATURE, 'Crear usuario exitosamente')
def test_crear_usuario():
    pass


@scenario(FEATURE, 'Crear juego exitosamente')
def test_crear_juego():
    pass


@scenario(FEATURE, 'Crear hardware exitosamente')
def test_crear_hardware():
    pass


@scenario(FEATURE, 'Usuario con rol de administrador')
def test_usuario_admin():
    pass


@scenario(FEATURE, 'Obtener requisitos de juego')
def test_obtener_requisitos():
    pass


@scenario(FEATURE, 'Obtener especificaciones de hardware')
def test_obtener_especificaciones():
    pass


@given('tengo una base de datos vacía')
def base_datos_vacia(app_context):
    assert Game.query.count() == 0
    assert User.query.count() == 0


@when(parsers.parse('creo un usuario con nombre "{username}" y email "{email}"'), target_fixture='usuario')
def crear_usuario(username, email):
    return User(username=username, email=email)


@when(parsers.parse('establezco la contraseña "{password}"'))
def establecer_password(usuario, password):
    usuario.set_password(password)
    db.session.add(usuario)
    db.session.commit()


@then('el usuario debería tener un ID asignado')
def verificar_id_usuario(usuario):
    assert usuario.id is not None


@then(parsers.parse('el nombre de usuario debería ser "{username}"'))
def verificar_nombre_usuario(usuario, username):
    assert usuario.username == username


@then(parsers.parse('el email debería ser "{email}"'))
def verificar_email(usuario, email):
    assert usuario.email == email


@then(parsers.parse('la contraseña debería ser válida para "{password}"'))
def verificar_password_valida(usuario, password):
    assert usuario.check_password(password) is True


@then(parsers.parse('la contraseña no debería ser válida para "{password}"'))
def verificar_password_invalida(usuario, password):
    assert usuario.check_password(password) is False


@when(parsers.parse('creo un juego con nombre "{nombre}" y precio {precio}'), target_fixture='juego')
def crear_juego(nombre, precio):
    return Game(
        nombre=nombre,
        descripcion='Test description',
        precio=float(precio),
        genero='Acción',
        desarrollador='Test Dev',
        requisitos_minimos='{"cpu": "Intel i3"}',
        requisitos_recomendados='{"cpu": "Intel i5"}',
        stock=0
    )


@when(parsers.parse('establezco el género "{genero}"'))
def establecer_genero_juego(juego, genero):
    juego.genero = genero


@when(parsers.parse('establezco el desarrollador "{desarrollador}"'))
def establecer_desarrollador(juego, desarrollador):
    juego.desarrollador = desarrollador


@when(parsers.parse('establezco el stock {stock:d}'))
def establecer_stock_juego(juego, stock):
    juego.stock = stock
    db.session.add(juego)
    db.session.commit()


@then('el juego debería tener un ID asignado')
def verificar_id_juego(juego):
    assert juego.id is not None


@then(parsers.parse('el nombre debería ser "{nombre}"'))
def verificar_nombre_juego(juego, nombre):
    assert juego.nombre == nombre


@then(parsers.parse('el precio del juego debería ser {precio}'))
def verificar_precio_juego(juego, precio):
    assert float(juego.precio) == float(precio)


@then(parsers.parse('el stock debería ser {stock:d}'))
def verificar_stock_juego(juego, stock):
    assert juego.stock == stock


@when(parsers.parse('creo un hardware tipo "{tipo}" con marca "{marca}"'), target_fixture='hardware_item')
def crear_hardware(tipo, marca):
    return Hardware(
        tipo=tipo,
        marca=marca,
        modelo='Test Model',
        precio=0.0,
        especificaciones='{"cores": 6}',
        stock=0
    )


@when(parsers.parse('establezco el modelo "{modelo}"'))
def establecer_modelo(hardware_item, modelo):
    hardware_item.modelo = modelo


@when(parsers.parse('establezco el precio {precio}'))
def establecer_precio_hardware(hardware_item, precio):
    hardware_item.precio = float(precio)


@when(parsers.parse('fijo el stock de hardware en {stock:d}'))
def fijar_stock_hardware(hardware_item, stock):
    hardware_item.stock = stock
    db.session.add(hardware_item)
    db.session.commit()


@then('el hardware debería tener un ID asignado')
def verificar_id_hardware(hardware_item):
    assert hardware_item.id is not None


@then(parsers.parse('el tipo debería ser "{tipo}"'))
def verificar_tipo_hardware(hardware_item, tipo):
    assert hardware_item.tipo == tipo


@then(parsers.parse('la marca debería ser "{marca}"'))
def verificar_marca_hardware(hardware_item, marca):
    assert hardware_item.marca == marca


@then(parsers.parse('el precio del hardware debería ser {precio}'))
def verificar_precio_hardware(hardware_item, precio):
    assert float(hardware_item.precio) == float(precio)


@when(parsers.parse('creo un usuario administrador con nombre "{username}"'), target_fixture='usuario')
def crear_usuario_admin(username):
    user = User(username=username, email=f'{username}@example.com', is_admin=True)
    user.set_password('Admin1234')
    return user


@when('establezco el rol de administrador')
def establecer_rol_admin(usuario):
    usuario.is_admin = True
    db.session.add(usuario)
    db.session.commit()


@then('el usuario debería ser administrador')
def verificar_usuario_admin(usuario):
    assert usuario.is_admin is True


@given('tengo un juego con requisitos mínimos JSON', target_fixture='juego')
def juego_con_requisitos(app_context):
    game = Game(
        nombre='Test Game',
        descripcion='Test description',
        precio=49.99,
        genero='Acción',
        desarrollador='Test Dev',
        requisitos_minimos='{"cpu": "Intel i3", "ram": "8GB"}',
        requisitos_recomendados='{"cpu": "Intel i5", "ram": "16GB"}',
        stock=10
    )
    db.session.add(game)
    db.session.commit()
    return game


@when('obtengo los requisitos mínimos', target_fixture='requisitos')
def obtener_requisitos(juego):
    return juego.get_requisitos_minimos()


@then(parsers.parse('debería tener CPU "{cpu}"'))
def verificar_cpu(requisitos, cpu):
    assert requisitos.get('cpu') == cpu


@then(parsers.parse('debería tener RAM "{ram}"'))
def verificar_ram(requisitos, ram):
    assert requisitos.get('ram') == ram


@given('tengo un hardware con especificaciones JSON', target_fixture='hardware_item')
def hardware_con_especificaciones(app_context):
    hardware_item = Hardware(
        tipo='CPU',
        marca='Intel',
        modelo='Core i5-10400',
        precio=199.99,
        especificaciones='{"cores": 6, "threads": 12}',
        stock=5
    )
    db.session.add(hardware_item)
    db.session.commit()
    return hardware_item


@when('obtengo las especificaciones', target_fixture='especificaciones')
def obtener_especificaciones(hardware_item):
    return hardware_item.get_especificaciones()


@then(parsers.parse('debería tener {cores:d} cores'))
def verificar_cores(especificaciones, cores):
    assert especificaciones.get('cores') == cores


@then(parsers.parse('debería tener {threads:d} threads'))
def verificar_threads(especificaciones, threads):
    assert especificaciones.get('threads') == threads
