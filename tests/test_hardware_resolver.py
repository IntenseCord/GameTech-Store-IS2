"""
Resolución de texto libre a un componente del catálogo (utils/hardware_resolver.py).

/consultar-compatibilidad recibe texto ("Intel Core i5-12400F", "RTX 4060", "16 GB") desde la tienda y desde la
ficha de un juego. El motor viejo adivinaba la potencia por palabras ("i5" valía 70) y daba 50 a cualquier
texto desconocido; ahora el texto se busca en el catálogo y, si no se reconoce, queda como "sin datos".
"""
import pytest

from extensions import db
from models.database_models import Hardware
from utils.hardware_resolver import ram_gb_de_texto, resolver_componente


def _crear(tipo, marca, modelo, score=0):
    h = Hardware(tipo=tipo, marca=marca, modelo=modelo, precio=10, especificaciones='{}', stock=1, benchmark_score=score)
    db.session.add(h)
    db.session.commit()
    return h


@pytest.fixture
def catalogo(app_context):
    return {
        'i5f': _crear('CPU', 'Intel', 'Core i5-12400F', 9000),
        'i5': _crear('CPU', 'Intel', 'Core i5-12400', 9000),
        'r5': _crear('CPU', 'AMD', 'Ryzen 5 7600X', 10500),
        'g4060': _crear('GPU', 'NVIDIA', 'RTX 4060', 12000),
        'g7600': _crear('GPU', 'AMD', 'RX 7600', 11000),
    }


@pytest.mark.parametrize('texto', [
    'Ryzen 5 7600X', 'AMD Ryzen 5 7600X', 'ryzen 5 7600x', 'RYZEN 5 7600X', 'AMD  Ryzen-5  7600X',
])
def test_resuelve_el_mismo_componente_con_distinta_escritura(catalogo, texto):
    assert resolver_componente('CPU', texto) == catalogo['r5']


@pytest.mark.parametrize('texto', ['Intel Core i5-12400F', 'Core i5-12400F', 'i5-12400F', 'i5 12400f'])
def test_resuelve_por_modelo_o_marca_y_modelo(catalogo, texto):
    assert resolver_componente('CPU', texto) == catalogo['i5f']


def test_el_nombre_exacto_gana_sobre_el_parcial(catalogo):
    # "Core i5-12400" es el modelo exacto aunque "Core i5-12400F" lo contenga
    assert resolver_componente('CPU', 'Core i5-12400') == catalogo['i5']


def test_un_texto_ambiguo_no_se_adivina(catalogo):
    assert resolver_componente('CPU', 'i5-12400') is None   # coincide con el 12400 y con el 12400F, sin ser ninguno exacto


@pytest.mark.parametrize('texto', ['Intel Core i5-3570K', 'GTX 780', 'i5', 'intel', '', '   ', None])
def test_texto_desconocido_o_demasiado_corto_no_se_resuelve(catalogo, texto):
    assert resolver_componente('CPU', texto) is None


def test_no_cruza_tipos(catalogo):
    assert resolver_componente('GPU', 'Ryzen 5 7600X') is None
    assert resolver_componente('GPU', 'RTX 4060') == catalogo['g4060']
    assert resolver_componente('GPU', 'RX 7600') == catalogo['g7600']


@pytest.mark.parametrize('texto, gb', [
    ('16 GB', 16), ('16GB', 16), ('32 gb', 32), ('Vengeance LPX 16GB DDR4', 16), ('8', 8), (' 64 ', 64),
])
def test_ram_en_gb(texto, gb):
    assert ram_gb_de_texto(texto) == gb


@pytest.mark.parametrize('texto', ['', None, 'mucha', '0 GB', 'DDR4'])
def test_ram_desconocida(texto):
    assert ram_gb_de_texto(texto) is None
