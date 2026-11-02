"""
Los avisos (flash) se muestran UNA vez (hallazgo 48, detectado en la prueba e2e del 1 de noviembre).

`base.html` ya recorre `get_flashed_messages`, pero 12 plantillas que la extienden (login, registro, perfil, carrito y el panel de
administración) lo recorrían otra vez: en una misma petición ambas llamadas devuelven la misma lista, así que cada aviso salía
dos veces ("¡Registro exitoso!..." duplicado al registrarse). Debe haber un único lugar que los pinte.
"""
from pathlib import Path

import pytest

from extensions import db
from models.database_models import User

PLANTILLAS = Path(__file__).resolve().parent.parent / 'templates'
AVISO = 'AVISO-UNICO-48'


def _encolar_aviso(client, categoria='success'):
    with client.session_transaction() as sesion:
        sesion['_flashes'] = [(categoria, AVISO)]


def test_solo_base_html_recorre_los_avisos():
    quienes = sorted(str(p.relative_to(PLANTILLAS)).replace('\\', '/') for p in PLANTILLAS.rglob('*.html')
                     if 'get_flashed_messages' in p.read_text(encoding='utf-8'))
    assert quienes == ['base.html'], quienes


@pytest.mark.parametrize('ruta', ['/login', '/registro'])
def test_un_aviso_aparece_una_sola_vez_en_las_paginas_publicas(client, ruta):
    _encolar_aviso(client)
    html = client.get(ruta).get_data(as_text=True)
    assert html.count(AVISO) == 1


@pytest.mark.parametrize('categoria', ['success', 'danger', 'warning', 'info'])
def test_cada_categoria_se_pinta_con_su_estilo_y_una_sola_vez(client, categoria):
    _encolar_aviso(client, categoria)
    html = client.get('/login').get_data(as_text=True)
    assert html.count(AVISO) == 1 and f'alert alert-{categoria}' in html


@pytest.mark.parametrize('ruta', ['/carrito', '/perfil/editar'])
def test_un_aviso_aparece_una_sola_vez_en_las_paginas_del_cliente(client, test_user, ruta):
    client.post('/login', data={'username': 'testuser', 'password': 'Test1234'})
    _encolar_aviso(client)
    html = client.get(ruta).get_data(as_text=True)
    assert html.count(AVISO) == 1


@pytest.mark.parametrize('ruta', ['/admin', '/admin/hardware', '/admin/juegos', '/admin/ordenes', '/admin/usuarios',
                                  '/admin/hardware/nuevo', '/admin/juego/nuevo'])
def test_un_aviso_aparece_una_sola_vez_en_el_panel_de_administracion(client, ruta):
    admin = User(username='admintest', email='admintest@example.com', is_admin=True, email_verified=True)
    admin.set_password('Test1234')
    db.session.add(admin)
    db.session.commit()
    client.post('/login', data={'username': 'admintest', 'password': 'Test1234'})
    _encolar_aviso(client)
    html = client.get(ruta).get_data(as_text=True)
    assert html.count(AVISO) == 1


def test_un_aviso_real_del_registro_sale_una_sola_vez(client):
    """El caso que se vio: registrarse y llegar al login con "¡Registro exitoso!"."""
    r = client.post('/registro', data={'username': 'nuevo48', 'email': 'nuevo48@example.com', 'password': 'Test1234',
                                       'confirm_password': 'Test1234'}, follow_redirects=True)
    assert r.get_data(as_text=True).count('Registro exitoso') == 1
