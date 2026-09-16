"""
Regresión: 13 formularios POST en toda la app no tenían su propio campo
csrf_token — dependían exclusivamente del <script> de base.html que lo
auto-inyecta por JS en cualquier <form method="POST"> que no lo tenga.
En un navegador normal con JS activo funcionaban igual, pero si el JS
falla o está deshabilitado, ese POST se rechaza con 400 "CSRF token
missing" sin ningún aviso claro. La suite normal corre con
WTF_CSRF_ENABLED=False y nunca lo detectó (ver conftest.py::client_csrf).

Estos tests activan CSRF real y verifican, por cada página, que el propio
<form> (no el <meta name="csrf-token"> global de base.html, que usa un
atributo distinto) trae el campo. Se busca literalmente `name="csrf_token"`
con comillas dobles: el script de base.html solo referencia ese nombre con
comillas simples (`input.name = 'csrf_token'`), así que no genera falsos
positivos.
"""
import uuid
from datetime import datetime, timedelta, timezone

from extensions import db
from models.database_models import User, Game, Hardware, Order, OrderItem, Invoice, CartItem

CSRF_INPUT = b'name="csrf_token"'


def login_directo(client_csrf, user):
    """Login vía sesión de Flask-Login directa: las rutas /login y /registro
    también exigen CSRF y no es lo que estos tests verifican."""
    with client_csrf.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True


def crear_usuario(admin=False):
    user = User(
        username='admintest' if admin else 'testuser',
        email='admintest@example.com' if admin else 'test@example.com',
        is_admin=admin,
        email_verified=True,
    )
    user.set_password('Test1234')
    db.session.add(user)
    db.session.commit()
    return user


def test_formularios_publicos_incluyen_csrf_token(client_csrf, test_user):
    """recuperar_password.html y resend_verification.html: sin login."""
    for ruta in ('/recuperar-password', '/resend-verification'):
        pagina = client_csrf.get(ruta)
        assert CSRF_INPUT in pagina.data, f'{ruta} no incluye su propio csrf_token'


def test_reset_password_incluye_csrf_token(client_csrf, test_user):
    test_user.reset_token = str(uuid.uuid4())
    test_user.reset_token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    db.session.commit()

    pagina = client_csrf.get(f'/reset-password/{test_user.reset_token}')
    assert pagina.status_code == 200
    assert CSRF_INPUT in pagina.data


def test_editar_perfil_incluye_csrf_token(client_csrf, test_user):
    login_directo(client_csrf, test_user)
    pagina = client_csrf.get('/perfil/editar')
    assert CSRF_INPUT in pagina.data


def test_checkout_incluye_csrf_token(client_csrf, test_user, test_game):
    login_directo(client_csrf, test_user)
    db.session.add(CartItem(user_id=test_user.id, product_type='game', product_id=test_game.id, quantity=1))
    db.session.commit()

    pagina = client_csrf.get('/carrito/checkout')
    assert CSRF_INPUT in pagina.data


def test_solicitar_factura_incluye_csrf_token(client_csrf, test_user):
    login_directo(client_csrf, test_user)
    order = Order(user_id=test_user.id, total=59.99, status='completed')
    db.session.add(order)
    db.session.commit()

    pagina = client_csrf.get(f'/factura/solicitar/{order.id}')
    assert CSRF_INPUT in pagina.data


def test_ver_factura_incluye_csrf_token_para_admin(client_csrf):
    admin = crear_usuario(admin=True)
    login_directo(client_csrf, admin)

    order = Order(user_id=admin.id, total=59.99, status='completed')
    db.session.add(order)
    db.session.flush()

    invoice = Invoice(
        uuid=str(uuid.uuid4()),
        folio='FE-0001',
        user_id=admin.id,
        order_id=order.id,
        nit_receptor='900123456',
        razon_social_receptor='Cliente de Prueba',
        subtotal=50.00,
        iva=9.50,
        total=59.50,
        status='active',
    )
    db.session.add(invoice)
    db.session.commit()

    pagina = client_csrf.get(f'/factura/{invoice.id}')
    assert CSRF_INPUT in pagina.data


def test_paneles_admin_incluyen_csrf_token(client_csrf, test_game, test_hardware):
    """usuarios.html, juegos.html, hardware.html, juego_form.html,
    hardware_form.html, orden_detalle.html: todos requieren admin."""
    admin = crear_usuario(admin=True)
    login_directo(client_csrf, admin)

    order = Order(user_id=admin.id, total=59.99, status='pending')
    db.session.add(order)
    db.session.commit()

    rutas = [
        '/admin/usuarios',
        '/admin/juegos',
        '/admin/hardware',
        '/admin/juego/nuevo',
        '/admin/hardware/nuevo',
        f'/admin/orden/{order.id}',
    ]
    for ruta in rutas:
        pagina = client_csrf.get(ruta)
        assert CSRF_INPUT in pagina.data, f'{ruta} no incluye su propio csrf_token'
