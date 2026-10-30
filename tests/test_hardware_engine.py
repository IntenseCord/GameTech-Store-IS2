"""
Motor único de hardware (utils/hardware_engine.py).

Antes había dos motores que podían contradecirse (models/compatibility.py, que adivinaba la potencia por
palabras del texto, y PerformanceCalculator + BottleneckDetector, sobre benchmark_score) y el controlador
del analizador descartaba el FPS, el limitante y el motivo que el cálculo sí producía. Ahora todo sale de
este módulo, que no toca Flask ni la base de datos. Estos tests lo ejercitan con objetos simples.
"""
from types import SimpleNamespace

import pytest

from utils.hardware_engine import (
    Sistema, detectar_cuello, evaluar_juego, nivel_del_sistema, puntuacion_total, recomendaciones, sistema_de,
)


def hw(score, ram_gb=None):
    return SimpleNamespace(benchmark_score=score, get_ram_capacity_gb=lambda: ram_gb)


def requisitos(**extra):
    base = dict(min_cpu_score=8000, min_gpu_score=7000, min_ram_gb=8,
                rec_cpu_score=12000, rec_gpu_score=14000, rec_ram_gb=12,
                ultra_cpu_score=15000, ultra_gpu_score=20000, ultra_ram_gb=20)
    base.update(extra)
    return SimpleNamespace(**base)


# ------------------------------------------------------------------ sistema
def test_sistema_de_toma_scores_y_ram_de_los_componentes():
    s = sistema_de(cpu=hw(9000), gpu=hw(12000), ram=hw(0, ram_gb=32))
    assert (s.cpu, s.gpu, s.ram_gb) == (9000, 12000, 32)
    assert s.faltantes == []


@pytest.mark.parametrize('cpu, gpu, ram, faltantes', [
    (hw(0), hw(12000), hw(0, 16), ['cpu']),          # benchmark_score 0 = sin dato, no "puntaje cero"
    (hw(None), hw(12000), hw(0, 16), ['cpu']),
    (hw(9000), None, hw(0, 16), ['gpu']),
    (hw(9000), hw(12000), None, ['ram']),
    (None, None, None, ['cpu', 'gpu', 'ram']),
])
def test_los_componentes_sin_dato_se_reportan_como_faltantes(cpu, gpu, ram, faltantes):
    assert sistema_de(cpu, gpu, ram).faltantes == faltantes


# ---------------------------------------------------- puntuación y nivel total
def test_puntuacion_total_pondera_gpu_cpu_y_ram():
    # GPU 50 % + CPU 35 % + RAM 15 % (100 puntos por GB)
    assert puntuacion_total(Sistema(cpu=9000, gpu=12000, ram_gb=32)) == 9630


def test_puntuacion_total_no_existe_sin_cpu_o_gpu():
    assert puntuacion_total(Sistema(cpu=None, gpu=12000, ram_gb=16)) is None
    assert puntuacion_total(Sistema(cpu=9000, gpu=None, ram_gb=16)) is None


@pytest.mark.parametrize('sistema, nivel', [
    (Sistema(cpu=18000, gpu=25000, ram_gb=32), 'Ultra High-End (4K Ultra)'),       # clase RTX 4090
    (Sistema(cpu=10500, gpu=16000, ram_gb=32), 'High-End (1440p Ultra)'),          # clase RTX 4070
    (Sistema(cpu=9000, gpu=12000, ram_gb=32), 'Mid-High (1080p Ultra)'),           # i5-12400F + RTX 4060
    (Sistema(cpu=9000, gpu=5000, ram_gb=16), 'Mid-Range (1080p Medium-High)'),     # GTX 1650
    (Sistema(cpu=3000, gpu=2000, ram_gb=8), 'Entry Level (1080p Low-Medium)'),
])
def test_nivel_del_sistema_para_equipos_de_referencia(sistema, nivel):
    assert nivel_del_sistema(puntuacion_total(sistema)) == nivel


def test_nivel_del_sistema_sin_puntuacion():
    assert nivel_del_sistema(None) == 'Sin datos suficientes'


# ------------------------------------------------------------- juegos
@pytest.mark.parametrize('sistema, calidad, fps', [
    (Sistema(cpu=16000, gpu=22000, ram_gb=32), 'ultra', 96),    # 90 * min(16000/15000, 22000/20000)
    (Sistema(cpu=12500, gpu=14500, ram_gb=16), 'high', 62),     # 60 * min(12500/12000, 14500/14000)
    (Sistema(cpu=10000, gpu=9000, ram_gb=16), 'medium', 46),    # 45 * min(10000/9600, 9000/8400)
    (Sistema(cpu=8500, gpu=7500, ram_gb=8), 'low', 31),         # 30 * min(8500/8000, 7500/7000)
])
def test_calidad_y_fps_salen_de_la_razon_con_los_requisitos(sistema, calidad, fps):
    r = evaluar_juego(sistema, requisitos())
    assert r['estado'] == 'ok' and r['puede_correr'] is True
    assert (r['calidad'], r['fps']) == (calidad, fps)


def test_el_fps_ya_no_es_siempre_60():
    fuerte = evaluar_juego(Sistema(cpu=16000, gpu=22000, ram_gb=32), requisitos())['fps']
    justo = evaluar_juego(Sistema(cpu=8500, gpu=7500, ram_gb=8), requisitos())['fps']
    assert fuerte != justo and 60 not in (fuerte, justo)


def test_no_puede_correr_indica_limitante_y_motivo():
    r = evaluar_juego(Sistema(cpu=7000, gpu=9000, ram_gb=16), requisitos())
    assert r['puede_correr'] is False and r['calidad'] == 'none' and r['fps'] == 0
    assert r['limitante'] == 'cpu'
    assert 'CPU insuficiente' in r['motivo']


def test_ram_insuficiente_es_el_limitante():
    r = evaluar_juego(Sistema(cpu=16000, gpu=22000, ram_gb=4), requisitos())
    assert r['puede_correr'] is False and r['limitante'] == 'ram'
    assert 'RAM insuficiente' in r['motivo']


def test_un_componente_muy_inferior_al_otro_es_el_limitante_de_la_calidad():
    r = evaluar_juego(Sistema(cpu=9700, gpu=30000, ram_gb=16), requisitos())
    assert r['puede_correr'] is True and r['limitante'] == 'cpu'


@pytest.mark.parametrize('req', [None, requisitos(min_cpu_score=0), requisitos(min_gpu_score=0)])
def test_un_juego_sin_requisitos_cargados_es_sin_datos_no_ultra(req):
    r = evaluar_juego(Sistema(cpu=16000, gpu=22000, ram_gb=32), req)
    assert r['estado'] == 'sin_datos' and r['puede_correr'] is None and r['calidad'] is None
    assert r['motivo']


def test_sin_ningun_componente_con_dato_es_sin_datos():
    r = evaluar_juego(Sistema(cpu=None, gpu=None, ram_gb=None), requisitos())
    assert r['estado'] == 'sin_datos'


def test_con_un_solo_componente_se_evalua_solo_ese_componente():
    """/consultar-compatibilidad permite elegir solo la GPU."""
    r = evaluar_juego(Sistema(cpu=None, gpu=22000, ram_gb=None), requisitos())
    assert r['estado'] == 'ok' and r['puede_correr'] is True and r['parcial'] is True
    assert (r['calidad'], r['fps']) == ('ultra', 99)   # 90 * 22000/20000
    assert evaluar_juego(Sistema(cpu=None, gpu=5000, ram_gb=None), requisitos())['puede_correr'] is False


# ------------------------------------------------------- cuello de botella
@pytest.mark.parametrize('cpu, gpu, tipo, severidad, perdida', [
    (10000, 15000, 'cpu', 'mild', 33),        # razón 1,5
    (9000, 25000, 'cpu', 'moderate', 64),     # razón 2,78
    (5000, 20000, 'cpu', 'severe', 75),       # razón 4
    (15000, 10000, 'gpu', 'mild', 33),        # simétrico: la GPU también tiene los tres niveles
    (25000, 9000, 'gpu', 'moderate', 64),
    (20000, 5000, 'gpu', 'severe', 75),
])
def test_cuello_de_botella_simetrico_con_tres_niveles(cpu, gpu, tipo, severidad, perdida):
    r = detectar_cuello(Sistema(cpu=cpu, gpu=gpu, ram_gb=32))
    assert r['has_bottleneck'] is True
    assert (r['type'], r['severity'], r['percentage_loss']) == (tipo, severidad, perdida)
    assert r['recommendations'] and '{' not in r['recommendations'][0]


def test_la_recomendacion_apunta_a_un_componente_que_equilibre_el_sistema():
    r = detectar_cuello(Sistema(cpu=9000, gpu=25000, ram_gb=32))
    assert '18750' in r['recommendations'][0]       # 75 % del componente más potente


def test_sistema_balanceado():
    r = detectar_cuello(Sistema(cpu=10000, gpu=14000, ram_gb=32))   # razón 1,4
    assert r['has_bottleneck'] is False and r['type'] == 'balanced'
    assert 'Balanceado' in r['description']


def test_la_ram_no_reduce_la_severidad_de_un_cuello_cpu_gpu():
    r = detectar_cuello(Sistema(cpu=5000, gpu=20000, ram_gb=8))
    assert (r['type'], r['severity']) == ('cpu', 'severe')
    assert 'RAM' in r['description']


@pytest.mark.parametrize('ram_gb, severidad', [(12, 'mild'), (8, 'mild'), (4, 'moderate')])
def test_ram_insuficiente_sola_es_un_cuello_de_botella(ram_gb, severidad):
    r = detectar_cuello(Sistema(cpu=10000, gpu=11000, ram_gb=ram_gb))
    assert (r['has_bottleneck'], r['type'], r['severity']) == (True, 'ram', severidad)


def test_sin_datos_no_se_presenta_como_sistema_balanceado():
    r = detectar_cuello(Sistema(cpu=10000, gpu=None, ram_gb=16))
    assert r['has_bottleneck'] is False and r['type'] == 'sin_datos'
    assert 'No hay datos' in r['description'] and 'Balanceado' not in r['description']


# ----------------------------------------------------------- recomendaciones
def test_recomendaciones_incluyen_las_del_cuello_y_no_repiten_la_de_ram():
    sistema = Sistema(cpu=5000, gpu=20000, ram_gb=8)
    textos = recomendaciones(sistema, detectar_cuello(sistema))
    assert sum('RAM' in t for t in textos) == 1
    assert any('CPU' in t for t in textos)


def test_recomendaciones_sin_datos_no_inventan_nada():
    sistema = Sistema(cpu=None, gpu=12000, ram_gb=16)
    assert recomendaciones(sistema, detectar_cuello(sistema)) == []


def test_un_componente_indicado_sin_dato_es_desconocido_no_ausente():
    s = sistema_de(cpu=hw(16000), gpu=hw(0), ram=None)
    assert s.desconocidos == ('gpu',)         # la GPU se indicó pero no tiene benchmark
    assert s.faltantes == ['gpu', 'ram']      # la RAM simplemente no se indicó


def test_con_un_componente_desconocido_no_se_confirma_que_el_juego_corra():
    r = evaluar_juego(Sistema(cpu=16000, gpu=None, ram_gb=32, desconocidos=('gpu',)), requisitos())
    assert r['estado'] == 'sin_datos' and 'GPU' in r['motivo']


def test_con_un_componente_desconocido_si_se_confirma_que_no_corre_si_otro_ya_no_llega():
    r = evaluar_juego(Sistema(cpu=7000, gpu=None, ram_gb=32, desconocidos=('gpu',)), requisitos())
    assert r['estado'] == 'ok' and r['puede_correr'] is False and r['limitante'] == 'cpu'
