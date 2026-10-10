"""
utils/file_validation.py importaba `imghdr`, módulo eliminado en Python 3.13:
en cualquier entorno >= 3.13 el import fallaba y subir una imagen desde el
admin nunca funcionaba (el `except Exception` del controlador lo disfrazaba
de "Error al procesar la solicitud"). La validación del formato real usa ahora
el que detecta Pillow.
"""
import io

import pytest
from PIL import Image
from werkzeug.datastructures import FileStorage

from utils.file_validation import validate_file_upload


def _archivo(formato, nombre):
    buffer = io.BytesIO()
    Image.new('RGB', (4, 4), (200, 30, 30)).save(buffer, format=formato)
    buffer.seek(0)
    return FileStorage(stream=buffer, filename=nombre)


@pytest.mark.parametrize('formato, nombre', [
    ('PNG', 'foto.png'),
    ('JPEG', 'foto.jpg'),
    ('JPEG', 'foto.jpeg'),
    ('WEBP', 'foto.webp'),
])
def test_imagenes_reales_validas_se_aceptan(formato, nombre):
    assert validate_file_upload(_archivo(formato, nombre)) == (True, None)


def test_el_archivo_queda_listo_para_guardarse_despues_de_validar():
    archivo = _archivo('PNG', 'foto.png')
    validate_file_upload(archivo)
    assert archivo.stream.tell() == 0


def test_texto_con_extension_png_se_rechaza():
    archivo = FileStorage(stream=io.BytesIO(b'esto no es una imagen'), filename='falso.png')
    valido, mensaje = validate_file_upload(archivo)
    assert valido is False
    assert 'inválido' in mensaje.lower()


def test_formato_real_no_permitido_con_extension_permitida_se_rechaza():
    """Un GIF renombrado a .png: la extensión engaña, el formato real no."""
    valido, mensaje = validate_file_upload(_archivo('GIF', 'animacion.png'))
    assert valido is False
    assert 'formato' in mensaje.lower()


def test_extension_no_permitida_se_rechaza():
    valido, mensaje = validate_file_upload(_archivo('PNG', 'foto.gif'))
    assert valido is False
    assert 'extensión' in mensaje.lower()


def test_archivo_demasiado_grande_se_rechaza(monkeypatch):
    monkeypatch.setattr('utils.file_validation.MAX_FILE_SIZE', 10)
    valido, mensaje = validate_file_upload(_archivo('PNG', 'foto.png'))
    assert valido is False
    assert 'tamaño' in mensaje.lower()


def test_sin_archivo_se_rechaza():
    assert validate_file_upload(None) == (False, 'No se proporcionó ningún archivo')
