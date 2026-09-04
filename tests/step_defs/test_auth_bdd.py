"""
Step definitions BDD para autenticación.

Ver test_models_bdd.py para el contexto del hallazgo original. Reescrito
con matching real (`parsers.parse`) y aserciones reales; de paso se
corrige que este archivo usaba `db.session.add(...)` sin haber importado
`db` (hubiera lanzado NameError si alguna vez se hubiera ejecutado).
"""
from pytest_bdd import given, when, then, scenario, parsers
from extensions import db
from models.database_models import User

FEATURE = '../features/auth.feature'


@scenario(FEATURE, 'Registro exitoso de usuario')
def test_registro_exitoso():
    pass


@scenario(FEATURE, 'Registro con contraseñas que no coinciden')
def test_registro_contrasenas_no_coinciden():
    pass


@scenario(FEATURE, 'Registro con contraseña inválida')
def test_registro_contrasena_invalida():
    pass


@scenario(FEATURE, 'Login exitoso')
def test_login_exitoso():
    pass


@scenario(FEATURE, 'Login fallido con contraseña incorrecta')
def test_login_fallido():
    pass


@scenario(FEATURE, 'Logout exitoso')
def test_logout_exitoso():
    pass


@given('estoy en la página de registro', target_fixture='formulario')
def pagina_registro(client):
    return {}


@when(parsers.parse('ingreso un nombre de usuario válido "{username}"'))
def ingresar_username(formulario, username):
    formulario['username'] = username


@when(parsers.parse('ingreso un email válido "{email}"'))
def ingresar_email(formulario, email):
    formulario['email'] = email


@when(parsers.parse('ingreso una contraseña válida "{password}"'))
def ingresar_password(formulario, password):
    formulario['password'] = password


@when(parsers.parse('ingreso una contraseña sin mayúscula "{password}"'))
def ingresar_password_sin_mayuscula(formulario, password):
    formulario['password'] = password


@when(parsers.parse('confirmo la contraseña "{password}"'))
def confirmar_password(formulario, password):
    formulario['confirm_password'] = password


@when('envío el formulario de registro', target_fixture='response')
def enviar_registro(client, formulario):
    return client.post('/registro', data=formulario)


@then('el usuario debería ser creado en la base de datos')
def verificar_usuario_creado(formulario):
    assert User.query.filter_by(username=formulario['username']).first() is not None


@then('debería ser redirigido a la página de login')
def verificar_redireccion_login(response):
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


@then('el usuario no debería ser creado')
def verificar_usuario_no_creado(formulario):
    assert User.query.filter_by(username=formulario['username']).first() is None


@then('debería ver un mensaje de error')
def verificar_mensaje_error(response):
    # En un error de validación, el formulario se re-renderiza (200), no se redirige
    assert response.status_code == 200


@given(parsers.parse('existe un usuario con nombre "{username}" y contraseña "{password}"'), target_fixture='formulario')
def usuario_existente(app_context, username, password):
    user = User(username=username, email=f'{username}@example.com')
    user.set_password(password)
    user.email_verified = True
    db.session.add(user)
    db.session.commit()
    return {}


@when('voy a la página de login')
def pagina_login(client):
    assert client.get('/login').status_code == 200


@when(parsers.parse('ingreso el nombre de usuario "{username}"'))
def ingresar_username_login(formulario, username):
    formulario['username'] = username


@when(parsers.parse('ingreso la contraseña "{password}"'))
def ingresar_password_login(formulario, password):
    formulario['password'] = password


@when('envío el formulario de login', target_fixture='response')
def enviar_login(client, formulario):
    return client.post('/login', data=formulario)


@then('debería ser redirigido a la página principal')
def verificar_redireccion_principal(response):
    assert response.status_code == 302


@when(parsers.parse('ingreso la contraseña incorrecta "{password}"'))
def ingresar_password_incorrecta(formulario, password):
    formulario['password'] = password


@then('debería permanecer en la página de login')
def verificar_permanecer_login(response):
    assert response.status_code == 200


@given(parsers.parse('estoy logueado como usuario "{username}"'))
def usuario_logueado(client, username):
    user = User(username=username, email=f'{username}@example.com')
    user.set_password('Test1234')
    user.email_verified = True
    db.session.add(user)
    db.session.commit()
    client.post('/login', data={'username': username, 'password': 'Test1234'})


@when('voy a la página de logout', target_fixture='response')
def pagina_logout(client):
    return client.get('/logout')


@then('no debería estar logueado')
def verificar_no_logueado(client):
    # Una ruta protegida debe redirigir a login si ya no hay sesión activa
    response = client.get('/carrito')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']
