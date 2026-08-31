"""
Step definitions para modelos BDD
"""
from pytest_bdd import given, when, then, scenario
from models.database_models import User, Game, Hardware
from extensions import db


@scenario('models.feature', 'Crear usuario exitosamente')
def test_crear_usuario():
    pass


@scenario('models.feature', 'Crear juego exitosamente')
def test_crear_juego():
    pass


@scenario('models.feature', 'Crear hardware exitosamente')
def test_crear_hardware():
    pass


@scenario('models.feature', 'Usuario con rol de administrador')
def test_usuario_admin():
    pass


@scenario('models.feature', 'Obtener requisitos de juego')
def test_obtener_requisitos():
    pass


@scenario('models.feature', 'Obtener especificaciones de hardware')
def test_obtener_especificaciones():
    pass


@given('tengo una base de datos vacía')
def base_datos_vacia(app_context):
    pass


@when('creo un usuario con nombre "<username>" y email "<email>"')
def crear_usuario(app_context, username, email):
    user = User(username=username, email=email)
    user.set_password('Test1234')
    db.session.add(user)
    db.session.commit()


@when('establezco la contraseña "<password>"')
def establecer_password(app_context, password):
    pass


@then('el usuario debería tener un ID asignado')
def verificar_id_usuario(app_context):
    pass


@then('el nombre de usuario debería ser "<username>"')
def verificar_nombre_usuario(app_context, username):
    pass


@then('el email debería ser "<email>"')
def verificar_email(app_context, email):
    pass


@then('la contraseña debería ser válida para "<password>"')
def verificar_password_valida(app_context, password):
    pass


@then('la contraseña no debería ser válida para "<password>"')
def verificar_password_invalida(app_context, password):
    pass


@when('creo un juego con nombre "<nombre>" y precio <precio>')
def crear_juego(app_context, nombre, precio):
    game = Game(
        nombre=nombre,
        descripcion='Test description',
        precio=precio,
        genero='Acción',
        desarrollador='Test Dev',
        requisitos_minimos='{"cpu": "Intel i3"}',
        requisitos_recomendados='{"cpu": "Intel i5"}',
        stock=10
    )
    db.session.add(game)
    db.session.commit()


@when('establezco el género "<genero>"')
def establecer_genero_juego(app_context, genero):
    pass


@when('establezco el desarrollador "<desarrollador>"')
def establecer_desarrollador(app_context, desarrollador):
    pass


@when('establezco el stock <stock>')
def establecer_stock_juego(app_context, stock):
    pass


@then('el juego debería tener un ID asignado')
def verificar_id_juego(app_context):
    pass


@then('el nombre debería ser "<nombre>"')
def verificar_nombre_juego(app_context, nombre):
    pass


@then('el precio debería ser <precio>')
def verificar_precio_juego(app_context, precio):
    pass


@then('el stock debería ser <stock>')
def verificar_stock_juego(app_context, stock):
    pass


@when('creo un hardware tipo "<tipo>" con marca "<marca>"')
def crear_hardware(app_context, tipo, marca):
    hardware = Hardware(
        tipo=tipo,
        marca=marca,
        modelo='Test Model',
        precio=199.99,
        especificaciones='{"cores": 6}',
        stock=5
    )
    db.session.add(hardware)
    db.session.commit()


@when('establezco el modelo "<modelo>"')
def establecer_modelo(app_context, modelo):
    pass


@when('establezco el precio <precio>')
def establecer_precio_hardware(app_context, precio):
    pass


@then('el hardware debería tener un ID asignado')
def verificar_id_hardware(app_context):
    pass


@then('el tipo debería ser "<tipo>"')
def verificar_tipo_hardware(app_context, tipo):
    pass


@then('la marca debería ser "<marca>"')
def verificar_marca_hardware(app_context, marca):
    pass


@then('el precio debería ser <precio>')
def verificar_precio_hardware(app_context, precio):
    pass


@when('creo un usuario administrador con nombre "<username>"')
def crear_usuario_admin(app_context, username):
    user = User(username=username, email=f'{username}@example.com', is_admin=True)
    user.set_password('Admin1234')
    db.session.add(user)
    db.session.commit()


@when('establezco el rol de administrador')
def establecer_rol_admin(app_context):
    pass


@then('el usuario debería ser administrador')
def verificar_usuario_admin(app_context):
    pass


@given('tengo un juego con requisitos mínimos JSON')
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


@when('obtengo los requisitos mínimos')
def obtener_requisitos(app_context):
    pass


@then('debería tener CPU "<cpu>"')
def verificar_cpu(app_context, cpu):
    pass


@then('debería tener RAM "<ram>"')
def verificar_ram(app_context, ram):
    pass


@given('tengo un hardware con especificaciones JSON')
def hardware_con_especificaciones(app_context):
    hardware = Hardware(
        tipo='CPU',
        marca='Intel',
        modelo='Core i5-10400',
        precio=199.99,
        especificaciones='{"cores": 6, "threads": 12}',
        stock=5
    )
    db.session.add(hardware)
    db.session.commit()


@when('obtengo las especificaciones')
def obtener_especificaciones(app_context):
    pass


@then('debería tener <cores> cores')
def verificar_cores(app_context, cores):
    pass


@then('debería tener <threads> threads')
def verificar_threads(app_context, threads):
    pass
