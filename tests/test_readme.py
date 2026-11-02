"""
README.md: que describa lo que el proyecto realmente tiene y que sus cifras no se desfasen en silencio.

El README anterior mencionaba modelos que ya no existen (models/game.py, models/compatibility.py), instrucciones de Heroku que no
aplican, funciones "planificadas" que ya estaban hechas y un enlace a un LICENSE inexistente. Estas pruebas fallan si:
  - falta documentar una variable de `.env.example`;
  - se nombra un comando, un archivo o una ruta que no existe;
  - la demostración cita cifras que el motor ya no calcula (por ejemplo, tras cambiar un precio del catálogo).
"""
import re
from pathlib import Path

import pytest

from app import app
from tests.test_asesor import juegos, piezas
from tests.test_recomendador import entrada_de, mejoras
from utils.asesor import armar_pc
from utils.compatibilidad import verificar_configuracion

RAIZ = Path(__file__).resolve().parent.parent
README = (RAIZ / 'README.md').read_text(encoding='utf-8')


def _por_modelo(modelo):
    return next(p for p in piezas() if p.modelo == modelo)


def test_documenta_cada_variable_de_env_example():
    variables = re.findall(r'^([A-Z][A-Z0-9_]+)=', (RAIZ / '.env.example').read_text(encoding='utf-8'), re.MULTILINE)
    assert variables
    faltan = [v for v in variables if v not in README]
    assert not faltan, faltan


def test_los_comandos_de_scripts_que_menciona_existen():
    comandos = re.findall(r'python (scripts/[\w]+\.py)', README)
    assert 'scripts/sincronizar_catalogo.py' in comandos
    assert all((RAIZ / c).is_file() for c in comandos), comandos


def test_los_archivos_y_carpetas_que_menciona_existen():
    rutas = set(re.findall(r'`((?:app|config|database|extensions|forms|pytest)\.(?:py|ini)|(?:controllers|models|utils|scripts|templates|static|tests|migrations)/[\w./-]*)`', README))
    assert len(rutas) >= 15
    inexistentes = [r for r in rutas if not (RAIZ / r).exists()]
    assert not inexistentes, inexistentes


def test_las_rutas_http_que_menciona_existen_en_la_aplicacion():
    reglas = {re.sub(r'<[^>]+>', '*', r.rule) for r in app.url_map.iter_rules()}
    citadas = {p for p in re.findall(r'`(/[\w/*-]*)`', README) if len(p) > 1}
    assert {'/tienda', '/hardware', '/configurador-pc', '/analizador-hardware', '/graphql', '/admin',
            '/api/analizar-hardware', '/api/verificar-configuracion', '/api/armar-pc'} <= citadas
    inexistentes = [p for p in citadas if p not in reglas]
    assert not inexistentes, inexistentes


def test_no_afirma_lo_que_no_existe():
    assert 'Heroku' not in README and 'Railway' not in README
    assert 'models/compatibility.py' not in README and 'models/game.py' not in README
    if not (RAIZ / 'LICENSE').exists():
        assert 'LICENSE' not in README
    assert 'twitter.com' not in README and 'tuusuario' not in README


def test_no_incluye_secretos_ni_urls_de_base_de_datos():
    marcador = 'postgresql://usuario:clave@host/base?sslmode=require'          # texto de ejemplo, no una credencial
    assert marcador in README
    assert not re.search(r'postgres(ql)?://[^\s`]+:[^\s`@]+@', README.replace(marcador, ''))
    assert not re.search(r'APP_USR-|TEST-[0-9a-f]{8}', README)


# ----------------------------------------------------- las cifras de la demostración salen del motor
def test_cifras_del_asesor():
    mil = armar_pc(piezas(), juegos(), 1000, 'gaming')
    assert f"${mil['precio_total']:.2f}" in README
    assert f"${mil['siguiente']['precio_extra']:.2f}" in README and f"${mil['siguiente']['precio_total']:.2f}" in README
    for pieza in mil['piezas'].values():
        assert pieza.modelo in README
    esports = armar_pc(piezas(), juegos(), 2000, 'esports')
    assert f"${esports['precio_total']:.2f}" in README and f"${esports['desde']:.2f}" in README
    assert f"${armar_pc(piezas(), juegos(), 1, 'gaming')['precio_minimo']:.2f}" in README


def test_cifras_del_recomendador():
    gpu = entrada_de(mejoras('Ryzen 5 5600', 'GTX 1650', 'Vengeance LPX 16GB DDR4'), 'GPU')
    mejor = gpu['opciones'][0]
    assert mejor['pieza'].modelo == 'RX 7600'
    assert f"${mejor['precio']:.2f}" in README and f"+{mejor['mejora_pct']}%" in README
    assert f"{mejor['puntos_por_dolar']:.2f}" in README
    vram = entrada_de(mejoras('Core i5-12400F', 'RTX 4060', 'Vengeance LPX 16GB DDR4', vram=11), 'GPU')
    assert vram['opciones'][0]['pieza'].modelo == 'RTX 4070' and '11 GB' in README and '8 GB' in README


def test_cifras_de_compatibilidad():
    v = verificar_configuracion(cpu=_por_modelo('Core i7-13700K'), gpu=_por_modelo('RTX 4070'), fuente=_por_modelo('CX550 550W'))
    fuente = next(x for x in v if x['par'] == 'fuente')
    assert fuente['estado'] == 'incompatible' and '650 W' in fuente['mensaje'] and '650 W' in README
    g = verificar_configuracion(gabinete=_por_modelo('MasterBox Q300L'), enfriador=_por_modelo('AK620'))
    gab = next(x for x in g if x['par'] == 'gabinete_enfriador')
    assert gab['estado'] == 'incompatible' and '160 mm' in gab['mensaje'] and '159 mm' in gab['mensaje']
    assert '160 mm' in README and '159 mm' in README


@pytest.mark.parametrize('seccion', ['Motor único', 'Instalación', 'Pruebas', 'Demostración', 'Limitaciones'])
def test_tiene_las_secciones_clave(seccion):
    assert re.search(rf'^##+ .*{seccion}', README, re.MULTILINE), seccion
