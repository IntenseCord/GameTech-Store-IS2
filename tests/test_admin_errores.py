"""
Manejo de errores del panel de administración.

- Los `except Exception` escondían bugs reales y tragaban el 404 de
  get_or_404 (un juego/orden inexistente redirigía en vez de dar 404).
- Los mensajes de error de base de datos mostraban str(e) al usuario.
- Un fallo de disco al guardar la imagen subida (OSError) es un error
  operativo esperado: mensaje claro, no un 500.
"""
import pytest
from flask import g
from sqlalchemy.exc import OperationalError
from werkzeug.datastructures import FileStorage

import controllers.admin as admin_module
from extensions import db
from models.database_models import Game, Hardware, Order, User

DETALLE_INTERNO = 'detalle-interno-xyz'


def _login_admin(client):
    g.pop('_login_user', None)
    admin = User(username='admintest', email='admintest@example.com', is_admin=True, email_verified=True)
    admin.set_password('Test1234')
    db.session.add(admin)
    db.session.commit()
    client.post('/login', data={'username': 'admintest', 'password': 'Test1234'})
    return admin


def _falla_de_base_de_datos(*args, **kwargs):
    raise OperationalError('SELECT 1', {}, Exception(DETALLE_INTERNO))


def _bug_inesperado(*args, **kwargs):
    raise RuntimeError(DETALLE_INTERNO)


DATOS_JUEGO = {
    'nombre': 'Juego', 'descripcion': 'desc', 'genero': 'Acción', 'desarrollador': 'Dev',
    'precio': '10', 'stock': '2', 'fecha_lanzamiento': '2024-01-01',
}
DATOS_HARDWARE = {
    'tipo': 'CPU', 'marca': 'Marca', 'modelo': 'Modelo', 'precio': '10', 'stock': '2',
    'especificaciones': '{}',
}


@pytest.fixture
def con_admin(client, app_context, test_game, test_hardware):
    admin = _login_admin(client)
    orden = Order(user_id=admin.id, total=10, status='pending')
    db.session.add(orden)
    db.session.commit()
    return {'orden': orden, 'juego': test_game, 'hardware': test_hardware}


# ------------------------------------------------- páginas de solo lectura

RUTAS_DE_LISTADO = [
    ('/admin', 'Error al cargar el dashboard'),
    ('/admin/usuarios', 'Error al cargar usuarios'),
    ('/admin/juegos', 'Error al cargar juegos'),
    ('/admin/hardware', 'Error al cargar hardware'),
    ('/admin/ordenes', 'Error al cargar órdenes'),
    ('/admin/orden/{orden}', 'Error al cargar la orden'),
]


@pytest.mark.parametrize('ruta, mensaje', RUTAS_DE_LISTADO)
def test_error_de_base_de_datos_muestra_mensaje_amable_sin_detalles(
        client, con_admin, monkeypatch, ruta, mensaje):
    monkeypatch.setattr(admin_module, 'render_template', _falla_de_base_de_datos)

    respuesta = client.get(ruta.format(orden=con_admin['orden'].id), follow_redirects=True)

    assert respuesta.status_code == 200
    assert mensaje.encode() in respuesta.data
    assert DETALLE_INTERNO.encode() not in respuesta.data


@pytest.mark.parametrize('ruta, _mensaje', RUTAS_DE_LISTADO)
def test_error_inesperado_en_listados_no_se_esconde_responde_500(
        client, con_admin, monkeypatch, ruta, _mensaje):
    monkeypatch.setattr(admin_module, 'render_template', _bug_inesperado)
    monkeypatch.setitem(client.application.config, 'PROPAGATE_EXCEPTIONS', False)

    respuesta = client.get(ruta.format(orden=con_admin['orden'].id))

    assert respuesta.status_code == 500
    assert DETALLE_INTERNO.encode() not in respuesta.data


# ------------------------------------------------------------ 404 tragado

@pytest.mark.parametrize('ruta', [
    '/admin/juego/99999/editar',
    '/admin/hardware/99999/editar',
    '/admin/orden/99999',
])
def test_recurso_inexistente_devuelve_404_no_redirect(client, con_admin, ruta):
    assert client.get(ruta).status_code == 404


# ------------------------------------------------------ str(e) al usuario

def _commit_falla(self):
    raise OperationalError('COMMIT', {}, Exception(DETALLE_INTERNO))


CASOS_ESCRITURA = [
    ('/admin/juego/nuevo', DATOS_JUEGO),
    ('/admin/juego/{juego}/editar', DATOS_JUEGO),
    ('/admin/hardware/nuevo', DATOS_HARDWARE),
    ('/admin/hardware/{hardware}/editar', DATOS_HARDWARE),
    ('/admin/juego/{juego}/eliminar', {}),
    ('/admin/hardware/{hardware}/eliminar', {}),
]


@pytest.mark.parametrize('ruta, datos', CASOS_ESCRITURA)
def test_fallo_de_commit_no_muestra_el_detalle_al_usuario(
        client, con_admin, monkeypatch, ruta, datos):
    url = ruta.format(juego=con_admin['juego'].id, hardware=con_admin['hardware'].id)
    monkeypatch.setattr('sqlalchemy.orm.Session.commit', _commit_falla)

    respuesta = client.post(url, data=datos, follow_redirects=True)
    monkeypatch.undo()

    assert respuesta.status_code == 200
    assert DETALLE_INTERNO.encode() not in respuesta.data
    assert b'alert' in respuesta.data  # sigue mostrando un aviso de error


# --------------------------------------------------- fallo de disco (OSError)

def _png_real():
    import io
    from PIL import Image
    buffer = io.BytesIO()
    Image.new('RGB', (4, 4), (10, 120, 200)).save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


@pytest.mark.parametrize('ruta, datos', [
    ('/admin/juego/nuevo', DATOS_JUEGO),
    ('/admin/juego/{juego}/editar', DATOS_JUEGO),
    ('/admin/hardware/nuevo', DATOS_HARDWARE),
    ('/admin/hardware/{hardware}/editar', DATOS_HARDWARE),
])
def test_fallo_de_disco_al_guardar_imagen_muestra_mensaje_no_500(
        client, con_admin, monkeypatch, ruta, datos):
    def disco_lleno(self, *args, **kwargs):
        raise OSError(28, 'No space left on device')

    monkeypatch.setattr(FileStorage, 'save', disco_lleno)
    url = ruta.format(juego=con_admin['juego'].id, hardware=con_admin['hardware'].id)
    cuerpo = dict(datos, imagen=(_png_real(), 'foto.png'))

    respuesta = client.post(url, data=cuerpo, content_type='multipart/form-data')

    assert respuesta.status_code == 200
    assert 'No se pudo guardar la imagen'.encode() in respuesta.data
    assert Game.query.filter_by(nombre='Juego').count() == 0
    assert Hardware.query.filter_by(modelo='Modelo').count() == 0


@pytest.mark.parametrize('ruta, datos, modelo', [
    ('/admin/juego/nuevo', DATOS_JUEGO, Game),
    ('/admin/juego/{juego}/editar', DATOS_JUEGO, Game),
    ('/admin/hardware/nuevo', DATOS_HARDWARE, Hardware),
    ('/admin/hardware/{hardware}/editar', DATOS_HARDWARE, Hardware),
])
def test_ruta_guardada_de_la_imagen_usa_barras_normales(client, con_admin, monkeypatch, ruta, datos, modelo):
    """os.path.join usa el separador del sistema: en Windows guardaba
    '/static/uploads\\<uuid>.png', una URL con barra invertida en la base de datos."""
    import re
    monkeypatch.setattr(FileStorage, 'save', lambda self, *args, **kwargs: None)
    url = ruta.format(juego=con_admin['juego'].id, hardware=con_admin['hardware'].id)

    client.post(url, data=dict(datos, imagen=(_png_real(), 'portada.png')),
                content_type='multipart/form-data')

    guardadas = [p.imagen for p in modelo.query.all() if p.imagen]
    assert guardadas, 'No se guardó ninguna ruta de imagen'
    assert all(re.fullmatch(r'/static/uploads/[0-9a-f-]{36}\.png', r) for r in guardadas), guardadas


def test_subir_imagen_real_crea_el_juego_y_guarda_el_archivo(client, con_admin, monkeypatch, tmp_path):
    """Antes (Python >= 3.13) la validación fallaba al importar imghdr y la
    subida de imágenes del admin nunca funcionaba."""
    monkeypatch.setattr(admin_module, 'UPLOAD', str(tmp_path))
    cuerpo = dict(DATOS_JUEGO, nombre='Con imagen', imagen=(_png_real(), 'portada.png'))

    respuesta = client.post('/admin/juego/nuevo', data=cuerpo, content_type='multipart/form-data')

    assert respuesta.status_code == 302
    juego = Game.query.filter_by(nombre='Con imagen').one()
    assert juego.imagen.endswith('.png')
    assert len(list(tmp_path.glob('*.png'))) == 1
