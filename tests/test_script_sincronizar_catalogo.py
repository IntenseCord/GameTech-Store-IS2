"""
scripts/sincronizar_catalogo.py: deja una base ya existente con el catálogo completo (juegos, hardware y requisitos).

`seed_database` solo corre con la base vacía; este comando es el camino para una base que ya tiene datos (por ejemplo, la de
Neon). Es idempotente: repetirlo no duplica ni cambia nada.

También cierra el hallazgo 44: los `print` de los scripts de carga llevaban emojis y lanzaban `UnicodeEncodeError` en la consola de
Windows (codificación cp1252), cortando la carga a mitad y dejando juegos agregados sin requisitos.
"""
import io
import re
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from database import hardware_inicial, juegos_iniciales
from extensions import db
from models.database_models import Game, GameRequirements, Hardware
from scripts.populate_game_requirements import populate_game_requirements
from scripts.populate_hardware_benchmarks import update_hardware_benchmarks
from scripts.sincronizar_catalogo import sincronizar_catalogo

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = ('populate_game_requirements.py', 'populate_hardware_benchmarks.py', 'sincronizar_catalogo.py')
EMOJIS = re.compile('[\U0001F000-\U0001FFFF☀-➿️]')

ORIGINALES = {'Cyberpunk 2077', 'The Witcher 3: Wild Hunt', 'Grand Theft Auto V', 'Counter-Strike 2', 'Elden Ring'}
HARDWARE_ORIGINAL = {'Core i5-12400F', 'Ryzen 5 7600X', 'RTX 4060', 'RX 7600', 'Vengeance LPX 16GB DDR4',
                     'Trident Z RGB 32GB DDR4', 'ROG Strix B450-F Gaming', 'MAG B660M Mortar WiFi DDR4'}


def consola_de_windows():
    """Una consola cp1252 estricta, como la de Windows sin UTF-8: un carácter que no entre lanza UnicodeEncodeError."""
    return io.TextIOWrapper(io.BytesIO(), encoding='cp1252', errors='strict', write_through=True)


# ------------------------------------------------------- hallazgo 44: nada que la consola no pueda imprimir
@pytest.mark.parametrize('nombre', SCRIPTS)
def test_los_scripts_no_contienen_emojis(nombre):
    texto = (RAIZ / 'scripts' / nombre).read_text(encoding='utf-8')
    assert not EMOJIS.search(texto), [m.group() for m in EMOJIS.finditer(texto)]


def test_los_scripts_imprimen_sin_error_en_la_consola_de_windows_con_la_base_vacia(app_context):
    """Rama de 'no encontrado': antes imprimía ⚠️ y 💡."""
    for funcion in (update_hardware_benchmarks, populate_game_requirements, sincronizar_catalogo):
        with redirect_stdout(consola_de_windows()):
            funcion()


def test_los_scripts_imprimen_sin_error_en_la_consola_de_windows_con_datos(app_context):
    db.session.add_all(hardware_inicial() + juegos_iniciales())
    db.session.commit()
    for funcion in (update_hardware_benchmarks, populate_game_requirements, sincronizar_catalogo):
        with redirect_stdout(consola_de_windows()):
            funcion()


# ----------------------------------------------------------- el comando de sincronización
def _base_antigua():
    """Lo que tenía la base de Neon antes de ampliar el catálogo: 5 juegos y 8 componentes."""
    db.session.add_all([j for j in juegos_iniciales() if j.nombre in ORIGINALES]
                       + [h for h in hardware_inicial() if h.modelo in HARDWARE_ORIGINAL])
    db.session.commit()


def test_deja_una_base_antigua_con_el_catalogo_completo(app_context):
    _base_antigua()
    assert (Game.query.count(), Hardware.query.count(), GameRequirements.query.count()) == (5, 8, 0)

    r = sincronizar_catalogo()

    assert (Game.query.count(), Hardware.query.count(), GameRequirements.query.count()) == (8, 28, 8)
    assert set(r['juegos_agregados']) == {'Red Dead Redemption 2', "Baldur's Gate 3", 'Apex Legends'}
    assert len(r['hardware_agregado']) == 20 and r['requisitos'] == 8


def test_es_idempotente(app_context):
    _base_antigua()
    sincronizar_catalogo()
    r = sincronizar_catalogo()
    assert r['juegos_agregados'] == [] and r['hardware_agregado'] == [] and r['hardware_actualizado'] == []
    assert (Game.query.count(), Hardware.query.count(), GameRequirements.query.count()) == (8, 28, 8)


def test_en_una_base_vacia_la_crea_completa(app_context):
    sincronizar_catalogo()
    assert (Game.query.count(), Hardware.query.count(), GameRequirements.query.count()) == (8, 28, 8)


def test_no_pisa_el_precio_ni_el_stock_que_el_administrador_cambio(app_context):
    _base_antigua()
    gpu = Hardware.query.filter_by(modelo='RTX 4060').one()
    gpu.precio, gpu.stock = 123.45, 7
    db.session.commit()

    sincronizar_catalogo()

    gpu = Hardware.query.filter_by(modelo='RTX 4060').one()
    assert (float(gpu.precio), gpu.stock) == (123.45, 7)


def test_resume_lo_que_hizo_en_texto_plano(app_context, capsys):
    _base_antigua()
    sincronizar_catalogo()
    salida = capsys.readouterr().out
    assert 'Juegos agregados: 3' in salida and 'Hardware agregado: 20' in salida and 'Requisitos cargados: 8' in salida
