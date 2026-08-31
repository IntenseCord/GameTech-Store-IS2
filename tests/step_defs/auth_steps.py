"""
Step definitions para autenticación BDD
"""
from pytest_bdd import given, when, then, scenario
from flask import url_for
from models.database_models import User


@scenario('auth.feature', 'Registro exitoso de usuario')
def test_registro_exitoso():
    pass


@scenario('auth.feature', 'Registro con contraseñas que no coinciden')
def test_registro_contrasenas_no_coinciden():
    pass


@scenario('auth.feature', 'Registro con contraseña inválida')
def test_registro_contrasena_invalida():
    pass


@scenario('auth.feature', 'Login exitoso')
def test_login_exitoso():
    pass


@scenario('auth.feature', 'Login fallido con contraseña incorrecta')
def test_login_fallido():
    pass


@given('estoy en la página de registro')
def pagina_registro(client):
    pass


@when('ingreso un nombre de usuario válido "<username>"')
def ingresar_username(client, username):
    pass


@when('ingreso un email válido "<email>"')
def ingresar_email(client, email):
    pass


@when('ingreso una contraseña válida "<password>"')
def ingresar_password(client, password):
    pass


@when('confirmo la contraseña "<password>"')
def confirmar_password(client, password):
    pass


@when('envío el formulario de registro')
def enviar_registro(client):
    pass


@then('el usuario debería ser creado en la base de datos')
def verificar_usuario_creado(app_context):
    pass


@then('debería ser redirigido a la página de login')
def verificar_redireccion_login(client):
    pass


@then('el usuario no debería ser creado')
def verificar_usuario_no_creado(app_context):
    pass


@then('debería ver un mensaje de error')
def verificar_mensaje_error(client):
    pass


@given('existe un usuario con nombre "<username>" y contraseña "<password>"')
def usuario_existente(app_context, username, password):
    user = User(username=username, email=f'{username}@example.com')
    user.set_password(password)
    user.email_verified = True
    db.session.add(user)
    db.session.commit()


@when('voy a la página de login')
def pagina_login(client):
    pass


@when('ingreso el nombre de usuario "<username>"')
def ingresar_username_login(client, username):
    pass


@when('ingreso la contraseña "<password>"')
def ingresar_password_login(client, password):
    pass


@when('envío el formulario de login')
def enviar_login(client):
    pass


@then('debería ser redirigido a la página principal')
def verificar_redireccion_principal(client):
    pass


@when('ingreso la contraseña incorrecta "<password>"')
def ingresar_password_incorrecta(client, password):
    pass


@then('debería permanecer en la página de login')
def verificar_permanecer_login(client):
    pass


@given('estoy logueado como usuario "<username>"')
def usuario_logueado(client, username):
    pass


@when('voy a la página de logout')
def pagina_logout(client):
    pass


@then('no debería estar logueado')
def verificar_no_logueado(client):
    pass
