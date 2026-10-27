"""
Imágenes subidas desde el panel de administración: no deben quedar huérfanas en disco.

- Si el commit falla después de guardar el archivo, la imagen recién subida se borra.
- Al reemplazar la imagen de un producto, la anterior se borra del disco (solo si el commit tuvo éxito).
- validate_file_upload no expone el detalle interno de Pillow al administrador.
"""
import io
from pathlib import Path

import pytest
from flask import g
from PIL import Image
from sqlalchemy.exc import OperationalError
from werkzeug.datastructures import FileStorage

import controllers.admin as admin_module
from extensions import db
from models.database_models import Game, Hardware, User
from utils.file_validation import validate_file_upload

DATOS_JUEGO = {
    'nombre': 'Juego', 'descripcion': 'desc', 'genero': 'Acción', 'desarrollador': 'Dev',
    'precio': '10', 'stock': '2', 'fecha_lanzamiento': '2024-01-01',
}
DATOS_HARDWARE = {
    'tipo': 'CPU', 'marca': 'Marca', 'modelo': 'Modelo', 'precio': '10', 'stock': '2',
    'especificaciones': '{}',
}
CASOS = [
    ('/admin/juego/nuevo', DATOS_JUEGO),
    ('/admin/juego/{juego}/editar', DATOS_JUEGO),
    ('/admin/hardware/nuevo', DATOS_HARDWARE),
    ('/admin/hardware/{hardware}/editar', DATOS_HARDWARE),
]


def _png():
    buffer = io.BytesIO()
    Image.new('RGB', (4, 4), (10, 120, 200)).save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


@pytest.fixture
def panel(client, app_context, test_game, test_hardware, monkeypatch, tmp_path):
    g.pop('_login_user', None)
    admin = User(username='admintest', email='admintest@example.com', is_admin=True, email_verified=True)
    admin.set_password('Test1234')
    db.session.add(admin)
    db.session.commit()
    client.post('/login', data={'username': 'admintest', 'password': 'Test1234'})
    monkeypatch.setattr(admin_module, 'UPLOAD', str(tmp_path))
    return {'juego': test_game.id, 'hardware': test_hardware.id, 'carpeta': tmp_path}


def _archivos(carpeta):
    return sorted(p.name for p in Path(carpeta).iterdir())


def _publicar(client, panel, ruta, datos, **extra):
    url = ruta.format(juego=panel['juego'], hardware=panel['hardware'])
    return client.post(url, data=dict(datos, **extra), content_type='multipart/form-data')


@pytest.mark.parametrize('ruta, datos', CASOS)
def test_si_el_commit_falla_la_imagen_recien_subida_se_borra_del_disco(client, panel, monkeypatch, ruta, datos):
    def commit_falla(self):
        raise OperationalError('COMMIT', {}, Exception('boom'))

    monkeypatch.setattr('sqlalchemy.orm.Session.commit', commit_falla)

    respuesta = _publicar(client, panel, ruta, datos, imagen=(_png(), 'foto.png'))
    monkeypatch.undo()

    assert respuesta.status_code == 200
    assert _archivos(panel['carpeta']) == [], 'Quedó una imagen huérfana en disco'


@pytest.mark.parametrize('ruta, datos, modelo', [
    ('/admin/juego/{juego}/editar', DATOS_JUEGO, Game),
    ('/admin/hardware/{hardware}/editar', DATOS_HARDWARE, Hardware),
])
def test_si_el_commit_falla_al_editar_se_conserva_la_imagen_anterior(client, panel, monkeypatch, ruta, datos, modelo):
    anterior = panel['carpeta'] / 'anterior.png'
    anterior.write_bytes(b'x')
    producto = db.session.get(modelo, panel['juego'] if modelo is Game else panel['hardware'])
    producto.imagen = admin_module.url_publica_de_imagen('anterior.png')
    db.session.commit()

    def commit_falla(self):
        raise OperationalError('COMMIT', {}, Exception('boom'))

    monkeypatch.setattr('sqlalchemy.orm.Session.commit', commit_falla)
    _publicar(client, panel, ruta, datos, imagen=(_png(), 'nueva.png'))
    monkeypatch.undo()

    assert _archivos(panel['carpeta']) == ['anterior.png']


@pytest.mark.parametrize('ruta, datos, modelo', [
    ('/admin/juego/{juego}/editar', DATOS_JUEGO, Game),
    ('/admin/hardware/{hardware}/editar', DATOS_HARDWARE, Hardware),
])
def test_al_reemplazar_la_imagen_se_borra_la_anterior_del_disco(client, panel, ruta, datos, modelo):
    (panel['carpeta'] / 'anterior.png').write_bytes(b'x')
    producto = db.session.get(modelo, panel['juego'] if modelo is Game else panel['hardware'])
    producto.imagen = admin_module.url_publica_de_imagen('anterior.png')
    db.session.commit()

    respuesta = _publicar(client, panel, ruta, datos, imagen=(_png(), 'nueva.png'))

    assert respuesta.status_code == 302
    assert 'anterior.png' not in _archivos(panel['carpeta'])
    assert len(_archivos(panel['carpeta'])) == 1


@pytest.mark.parametrize('ruta, datos, modelo', [
    ('/admin/juego/{juego}/editar', DATOS_JUEGO, Game),
    ('/admin/hardware/{hardware}/editar', DATOS_HARDWARE, Hardware),
])
def test_al_reemplazar_por_una_url_externa_se_borra_la_imagen_subida_anterior(client, panel, ruta, datos, modelo):
    (panel['carpeta'] / 'anterior.png').write_bytes(b'x')
    producto = db.session.get(modelo, panel['juego'] if modelo is Game else panel['hardware'])
    producto.imagen = admin_module.url_publica_de_imagen('anterior.png')
    db.session.commit()

    respuesta = _publicar(client, panel, ruta, datos, imagen_url='https://ejemplo.com/portada.png')

    assert respuesta.status_code == 302
    assert _archivos(panel['carpeta']) == []


def test_borrar_imagen_subida_ignora_urls_externas_y_rutas_ajenas(panel):
    (panel['carpeta'] / 'segura.png').write_bytes(b'x')

    for url in (None, '', 'https://ejemplo.com/segura.png', '/otra/carpeta/segura.png',
                '/static/uploads/../segura.png'):
        admin_module.borrar_imagen_subida(url)

    assert _archivos(panel['carpeta']) == ['segura.png']


def test_imagen_corrupta_no_expone_el_detalle_interno_de_pillow():
    corrupto = FileStorage(stream=io.BytesIO(b'esto no es una imagen'), filename='falsa.png')

    es_valida, mensaje = validate_file_upload(corrupto)

    assert es_valida is False
    assert mensaje == 'Archivo de imagen inválido'
    assert 'BytesIO' not in mensaje and 'cannot identify' not in mensaje
