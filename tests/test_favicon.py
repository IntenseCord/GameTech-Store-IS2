"""
Favicon (hallazgo 52, visto en la prueba e2e del 1 de noviembre).

Antes: no existía el archivo ni había `<link rel="icon">`, así que cada carga de página pedía `/favicon.ico` y el log
registraba un 404. Ahora `base.html` declara el ícono (un SVG propio en `static/`) y `/favicon.ico` redirige a él para los
clientes que lo piden igualmente (rastreadores, páginas que no heredan de la base).
"""
import re


def _href_del_icono(html):
    etiqueta = re.search(r'<link[^>]*rel="icon"[^>]*>', html)
    assert etiqueta, 'la página no declara <link rel="icon">'
    href = re.search(r'href="([^"]+)"', etiqueta.group(0))
    assert href, 'el <link rel="icon"> no tiene href'
    return href.group(1)


def test_la_portada_declara_el_icono(client):
    assert _href_del_icono(client.get('/').get_data(as_text=True)) == '/static/favicon.svg'


def test_una_pagina_de_error_tambien_declara_el_icono(client):
    respuesta = client.get('/ruta-que-no-existe')
    assert respuesta.status_code == 404
    assert _href_del_icono(respuesta.get_data(as_text=True)) == '/static/favicon.svg'


def test_el_archivo_del_icono_existe_y_es_un_svg(client):
    respuesta = client.get('/static/favicon.svg')
    assert respuesta.status_code == 200
    assert respuesta.mimetype == 'image/svg+xml'
    assert b'<svg' in respuesta.data


def test_favicon_ico_ya_no_responde_404(client):
    respuesta = client.get('/favicon.ico')
    assert respuesta.status_code in (301, 302, 308)
    assert respuesta.headers['Location'].endswith('/static/favicon.svg')
