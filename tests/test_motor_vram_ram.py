"""
VRAM y RAM en el motor único (hallazgo 47, descubierto por Alejandro).

Antes: `GameRequirements` guardaba la VRAM de cada nivel y `Hardware.vram_gb` la de cada GPU, pero el motor nunca las leía:
una GTX 1650 de 4 GB y una RTX 4060 de 8 GB se comparaban solo por velocidad. De la RAM solo contaba la capacidad y
`get_ram_capacity_gb` devolvía 8 GB cuando no podía leerla (un dato inventado).
Ahora la VRAM es un requisito por nivel y un límite del equipo (con su propio limitante), la velocidad de la RAM entra a la
puntuación con un factor acotado, y una capacidad ilegible es "sin datos".
"""
from types import SimpleNamespace

import pytest

from database import agregar_juegos_faltantes, sincronizar_hardware
from models.database_models import Hardware
from scripts.populate_game_requirements import populate_game_requirements
from utils.hardware_engine import Sistema, evaluar_juego, puntuacion_total, sistema_de


def req(**extra):
    base = dict(min_cpu_score=8000, min_gpu_score=7000, min_ram_gb=8, min_vram_gb=4,
                rec_cpu_score=12000, rec_gpu_score=14000, rec_ram_gb=12, rec_vram_gb=8,
                ultra_cpu_score=15000, ultra_gpu_score=20000, ultra_ram_gb=20, ultra_vram_gb=12)
    base.update(extra)
    return SimpleNamespace(**base)


POTENTE = dict(cpu=16000, gpu=21000, ram_gb=24)          # cumple el nivel ultra en CPU, GPU y RAM


# ---------------------------------------------------------------------- VRAM
def test_la_vram_corta_el_nivel_ultra_aunque_lo_demas_alcance():
    r = evaluar_juego(Sistema(**POTENTE, vram_gb=8), req())
    assert r['calidad'] == 'high' and r['limitante'] == 'vram'
    assert '12' in r['motivo'] and '8' in r['motivo']            # dice cuánta VRAM necesita y cuánta tiene


def test_con_la_vram_suficiente_llega_a_ultra_sin_limitante():
    r = evaluar_juego(Sistema(**POTENTE, vram_gb=12), req())
    assert r['calidad'] == 'ultra' and r['limitante'] is None and r['motivo'] == ''


def test_una_vram_sin_dato_no_bloquea_ni_se_toma_como_cero():
    r = evaluar_juego(Sistema(**POTENTE, vram_gb=None), req())
    assert r['calidad'] == 'ultra' and r['limitante'] is None


def test_la_vram_bajo_el_minimo_impide_correr_el_juego():
    r = evaluar_juego(Sistema(**POTENTE, vram_gb=3), req())
    assert r['puede_correr'] is False and r['calidad'] == 'none' and r['limitante'] == 'vram'
    assert 'VRAM insuficiente' in r['motivo']


def test_la_vram_tambien_corta_el_nivel_recomendado():
    r = evaluar_juego(Sistema(cpu=12500, gpu=14500, ram_gb=12, vram_gb=6), req())
    assert r['calidad'] == 'medium' and r['limitante'] == 'vram'


def test_si_otro_componente_tambien_impide_el_siguiente_nivel_el_limitante_no_es_la_vram():
    """Calidad alta: para llegar a ultra faltan CPU (13000 < 15000) y VRAM (8 < 12); culpar solo a la VRAM sería falso."""
    r = evaluar_juego(Sistema(cpu=13000, gpu=21000, ram_gb=24, vram_gb=8), req())
    assert r['calidad'] == 'high' and r['limitante'] != 'vram' and r['motivo'] == ''


def test_requisitos_sin_columnas_de_vram_no_rompen_el_motor():
    sin_vram = SimpleNamespace(min_cpu_score=8000, min_gpu_score=7000, min_ram_gb=8, rec_cpu_score=12000, rec_gpu_score=14000,
                               rec_ram_gb=12, ultra_cpu_score=15000, ultra_gpu_score=20000, ultra_ram_gb=20)
    assert evaluar_juego(Sistema(**POTENTE, vram_gb=2), sin_vram)['calidad'] == 'ultra'


def test_sistema_de_toma_la_vram_de_la_gpu():
    gpu = SimpleNamespace(benchmark_score=12000, vram_gb=8)
    assert sistema_de(gpu=gpu).vram_gb == 8
    assert sistema_de(gpu=SimpleNamespace(benchmark_score=12000, vram_gb=0)).vram_gb is None      # 0 = sin dato
    assert sistema_de(gpu=SimpleNamespace(benchmark_score=12000)).vram_gb is None


# ---------------------------------------------------------------------- RAM
def test_la_velocidad_estandar_no_cambia_la_puntuacion():
    base = puntuacion_total(Sistema(cpu=9000, gpu=12000, ram_gb=16))
    assert base == 9390
    assert puntuacion_total(Sistema(cpu=9000, gpu=12000, ram_gb=16, ram_mhz=3200)) == base


def test_una_ram_mas_rapida_sube_la_puntuacion_y_una_mas_lenta_la_baja():
    de = lambda mhz: puntuacion_total(Sistema(cpu=9000, gpu=12000, ram_gb=16, ram_mhz=mhz))
    assert de(1600) == de(2400)                        # ambas bajo el piso del 80 %
    assert de(2400) < de(2666) < de(3200) < de(3600) < de(5600)


def test_el_factor_de_velocidad_esta_acotado():
    de = lambda mhz: puntuacion_total(Sistema(cpu=9000, gpu=12000, ram_gb=16, ram_mhz=mhz))
    assert de(6400) == de(9999) == 9450                  # tope: 125 %
    assert de(1600) == de(800) == 9342                   # piso: 80 %


def test_sistema_de_toma_la_velocidad_de_la_ram():
    ram = SimpleNamespace(benchmark_score=0, get_ram_capacity_gb=lambda: 16, get_ram_speed_mhz=lambda: 5600)
    assert sistema_de(ram=ram).ram_mhz == 5600
    sin = SimpleNamespace(benchmark_score=0, get_ram_capacity_gb=lambda: 16, get_ram_speed_mhz=lambda: 0)
    assert sistema_de(ram=sin).ram_mhz is None


def test_la_velocidad_se_lee_de_las_especificaciones():
    leer = lambda specs: Hardware(tipo='RAM', marca='x', modelo='y', especificaciones=specs).get_ram_speed_mhz()
    assert leer('{"frecuencia": "3200 MHz"}') == 3200
    assert leer('{"frecuencia": "5600 MT/s"}') == 5600
    assert leer('{"frecuencia": 3600}') == 3600
    assert leer('{}') == 0 and leer('{"frecuencia": "rápida"}') == 0
    assert Hardware(tipo='GPU', marca='x', modelo='y', especificaciones='{"frecuencia": "3200 MHz"}').get_ram_speed_mhz() == 0


def test_una_capacidad_de_ram_ilegible_ya_no_vale_8_gb():
    ram = Hardware(tipo='RAM', marca='Kingston', modelo='Fury', especificaciones='{"capacidad": 16}')
    assert ram.get_ram_capacity_gb() == 0
    sin_capacidad = Hardware(tipo='RAM', marca='x', modelo='z', especificaciones='{}')
    assert sin_capacidad.get_ram_capacity_gb() == 0


def test_una_ram_ilegible_deja_los_juegos_en_sin_datos_en_vez_de_inventar_8_gb():
    cpu, gpu = SimpleNamespace(benchmark_score=16000), SimpleNamespace(benchmark_score=21000)
    ram = Hardware(tipo='RAM', marca='x', modelo='z', especificaciones='{}')
    s = sistema_de(cpu, gpu, ram)
    assert s.ram_gb is None and 'ram' in s.desconocidos
    assert evaluar_juego(s, req())['estado'] == 'sin_datos'


# --------------------------------------------------- con el catálogo real, por el analizador
@pytest.fixture
def todo(app_context):
    sincronizar_hardware()
    agregar_juegos_faltantes()
    populate_game_requirements()
    return {h.modelo: h.id for h in Hardware.query.all()}


def _juegos_por_calidad(client, ids, cpu, gpu, ram):
    r = client.post('/api/analizar-hardware', json={'cpu_id': ids[cpu], 'gpu_id': ids[gpu], 'ram_id': ids[ram]}).get_json()
    return {j['nombre']: (grupo, j['bottleneck']) for grupo, lista in r['games'].items() for j in lista}


def test_la_rtx_4060_de_8_gb_no_llega_a_ultra_en_los_juegos_que_piden_11_gb(client, todo):
    juegos = _juegos_por_calidad(client, todo, 'Core i7-13700K', 'RTX 4060', 'Vengeance LPX 16GB DDR4')
    assert juegos['Red Dead Redemption 2'] == ('can_run_high', 'vram')
    assert juegos["Baldur's Gate 3"] == ('can_run_high', 'vram')
    assert juegos['Cyberpunk 2077'][0] == 'can_run_high'
    assert juegos['The Witcher 3: Wild Hunt'][0] == 'can_run_ultra'          # pide 6 GB


def test_la_rtx_4070_de_12_gb_si_llega_a_ultra_en_todos(client, todo):
    juegos = _juegos_por_calidad(client, todo, 'Core i7-13700K', 'RTX 4070', 'Vengeance 32GB DDR5')
    assert {grupo for grupo, _ in juegos.values()} == {'can_run_ultra'} and len(juegos) == 8
