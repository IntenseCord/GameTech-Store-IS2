"""
Escala única de benchmark (utils/benchmark_escala.py) y requisitos de juegos derivados de ella.

Regresión (hallazgo 42): las puntuaciones de los componentes y los requisitos de los juegos estaban en escalas
distintas. Cyberpunk pedía `rec_cpu_score = 12000` ("i7-4790 / Ryzen 5 3600") mientras un i5-12400F, mucho más
potente, valía 9000: con el motor único, i5-12400F + RTX 4060 salía "bajo" (33 FPS) en Cyberpunk. Ahora los requisitos
se calculan a partir de piezas de referencia con puntaje en la misma tabla, así que las dos escalas coinciden por
construcción.
"""
from types import SimpleNamespace

import pytest

from extensions import db
from models.database_models import Game, GameRequirements, Hardware
from scripts.populate_game_requirements import (
    GAME_REQUIREMENTS_DATA, REFERENCIAS_POR_JUEGO, populate_game_requirements,
)
from scripts.populate_hardware_benchmarks import BENCHMARK_DATA, update_hardware_benchmarks
from utils.benchmark_escala import (
    CPU_SINGLE_THREAD, GPU_G3D, PUNTAJE_RX_7600, puntaje_cpu, puntaje_gpu,
)
from utils.hardware_engine import Sistema, evaluar_juego


# ------------------------------------------------------------------- la escala
def test_la_escala_coincide_con_los_componentes_del_catalogo():
    """Los dos CPU y la RTX 4060 del catálogo son las anclas: la regla debe reproducir sus puntajes curados."""
    assert puntaje_cpu('Core i5-12400F') == pytest.approx(BENCHMARK_DATA['CPU']['i5-12400F']['score'], rel=0.02)
    assert puntaje_cpu('Ryzen 5 7600X') == pytest.approx(BENCHMARK_DATA['CPU']['Ryzen 5 7600X']['score'], rel=0.02)
    assert puntaje_gpu('GeForce RTX 4060') == pytest.approx(BENCHMARK_DATA['GPU']['RTX 4060']['score'], rel=0.01)


def test_el_orden_de_los_componentes_respeta_el_rendimiento_real():
    cpus = ['Core 2 Quad Q6600', 'Core i5-750', 'Core i5-2500K', 'Core i5-3470', 'Core i5-3570K', 'Core i7-3770',
            'Core i7-4790', 'Core i5-8400', 'Core i7-8700K', 'Core i5-12400F', 'Ryzen 5 7600X']
    gpus = ['GeForce 9800 GT', 'Radeon HD 4870', 'GeForce GT 730', 'GeForce GTX 660', 'Radeon HD 7870',
            'GeForce GTX 770', 'GeForce GTX 780', 'Radeon RX 580', 'GeForce GTX 1060', 'GeForce GTX 1070',
            'GeForce RTX 2060', 'GeForce GTX 1080 Ti', 'GeForce RTX 4060', 'GeForce RTX 3080']
    for lista, puntaje in ((cpus, puntaje_cpu), (gpus, puntaje_gpu)):
        valores = [puntaje(n) for n in lista if n != 'GeForce GT 730']
        assert valores == sorted(valores) and len(set(valores)) == len(valores), lista


def test_todas_las_piezas_de_referencia_existen_en_la_escala():
    for juego, niveles in REFERENCIAS_POR_JUEGO.items():
        for nivel, ref in niveles.items():
            assert ref['cpu'] in CPU_SINGLE_THREAD, (juego, nivel, ref['cpu'])
            assert ref['gpu'] in GPU_G3D, (juego, nivel, ref['gpu'])
            assert ref['origen'] in ('publicado', 'proyecto'), (juego, nivel)


def test_la_rx_7600_queda_un_poco_por_debajo_de_la_rtx_4060():
    """Reseñas a 1080p: la RTX 4060 es entre 3 % y 8 % más rápida que la RX 7600."""
    razon = PUNTAJE_RX_7600 / puntaje_gpu('GeForce RTX 4060')
    assert 0.92 <= razon <= 0.97
    assert BENCHMARK_DATA['GPU']['RX 7600']['score'] == PUNTAJE_RX_7600


# ------------------------------------------------------------ requisitos de juegos
NOMBRES = {'Cyberpunk 2077', 'Elden Ring', 'The Witcher 3', 'Grand Theft Auto V', 'Counter-Strike 2'}


def test_los_requisitos_cubren_los_cinco_juegos_originales_del_catalogo():
    assert NOMBRES <= {g['game_name'] for g in GAME_REQUIREMENTS_DATA}


@pytest.mark.parametrize('juego', sorted(NOMBRES))
def test_los_requisitos_crecen_de_minimo_a_recomendado_a_ultra(juego):
    r = next(g['requirements'] for g in GAME_REQUIREMENTS_DATA if g['game_name'] == juego)
    for campo in ('cpu_score', 'gpu_score', 'ram_gb', 'vram_gb'):
        assert r[f'min_{campo}'] <= r[f'rec_{campo}'] <= r[f'ultra_{campo}'], (juego, campo)
    assert r['min_cpu_score'] > 0 and r['min_gpu_score'] > 0


def test_los_requisitos_usan_los_puntajes_de_las_piezas_de_referencia():
    r = next(g['requirements'] for g in GAME_REQUIREMENTS_DATA if g['game_name'] == 'Cyberpunk 2077')
    assert r['min_cpu_score'] == puntaje_cpu('Core i5-3570K') and r['min_gpu_score'] == puntaje_gpu('GeForce GTX 780')
    assert r['rec_cpu_score'] == puntaje_cpu('Core i7-4790') and r['rec_gpu_score'] == puntaje_gpu('GeForce GTX 1060')


def test_ningun_requisito_exige_mas_que_un_equipo_de_gama_media_actual_salvo_el_ultra_de_cyberpunk():
    """El mínimo y el recomendado de cada juego deben estar al alcance del catálogo (RTX 4060 = 12000)."""
    for g in GAME_REQUIREMENTS_DATA:
        r = g['requirements']
        assert r['rec_gpu_score'] < BENCHMARK_DATA['GPU']['RTX 4060']['score'], g['game_name']
        assert r['rec_cpu_score'] < BENCHMARK_DATA['CPU']['i5-12400F']['score'], g['game_name']


# ----------------------- el motor con estos requisitos da resultados coherentes
def _requisitos(juego):
    return SimpleNamespace(**next(g['requirements'] for g in GAME_REQUIREMENTS_DATA if g['game_name'] == juego))


@pytest.mark.parametrize('cpu, gpu, esperado', [
    (9000, 12000, {'Cyberpunk 2077': 'high', 'Elden Ring': 'ultra', 'The Witcher 3': 'ultra',
                   'Grand Theft Auto V': 'ultra', 'Counter-Strike 2': 'ultra'}),                  # i5-12400F + RTX 4060
    (10500, PUNTAJE_RX_7600, {'Cyberpunk 2077': 'high', 'Elden Ring': 'ultra', 'The Witcher 3': 'ultra',
                              'Grand Theft Auto V': 'ultra', 'Counter-Strike 2': 'ultra'}),      # Ryzen 5 7600X + RX 7600
    (6050, 5000, {'Cyberpunk 2077': 'low', 'Elden Ring': 'none', 'The Witcher 3': 'high',   # el mínimo oficial de Elden Ring es una GTX 1060
                  'Grand Theft Auto V': 'high', 'Counter-Strike 2': 'medium'}),                  # i5-8400 + GTX 1650
])
def test_calidad_por_juego_para_equipos_conocidos(cpu, gpu, esperado):
    sistema = Sistema(cpu=cpu, gpu=gpu, ram_gb=16)
    obtenido = {j: evaluar_juego(sistema, _requisitos(j))['calidad'] for j in NOMBRES}
    assert obtenido == esperado


def test_un_equipo_muy_antiguo_no_corre_cyberpunk_pero_si_los_juegos_ligeros():
    sistema = Sistema(cpu=puntaje_cpu('Core i5-2500K'), gpu=puntaje_gpu('GeForce GTX 660'), ram_gb=8)
    assert evaluar_juego(sistema, _requisitos('Cyberpunk 2077'))['puede_correr'] is False
    assert evaluar_juego(sistema, _requisitos('Counter-Strike 2'))['puede_correr'] is True
    assert evaluar_juego(sistema, _requisitos('The Witcher 3'))['puede_correr'] is True


def test_ya_no_ocurre_el_caso_del_hallazgo_42():
    """i5-12400F + RTX 4060 + 16 GB en Cyberpunk: antes 'bajo', 33 FPS y limitado por CPU."""
    r = evaluar_juego(Sistema(cpu=9000, gpu=12000, ram_gb=16), _requisitos('Cyberpunk 2077'))
    assert r['calidad'] == 'high' and r['fps'] >= 60 and r['limitante'] is None


# ------------------------------------- los scripts escriben esos datos en la base
@pytest.fixture
def catalogo(app_context):
    hw = [
        Hardware(tipo='CPU', marca='Intel', modelo='Core i5-12400F', precio=1, especificaciones='{}', stock=1),
        Hardware(tipo='CPU', marca='AMD', modelo='Ryzen 5 7600X', precio=1, especificaciones='{}', stock=1),
        Hardware(tipo='GPU', marca='NVIDIA', modelo='RTX 4060', precio=1, especificaciones='{}', stock=1),
        Hardware(tipo='GPU', marca='AMD', modelo='RX 7600', precio=1, especificaciones='{}', stock=1),
    ]
    juegos = [Game(nombre=n, descripcion='d', precio=10, genero='x', desarrollador='d', stock=1) for n in sorted(NOMBRES)]
    db.session.add_all(hw + juegos)
    db.session.commit()
    return hw, juegos


def test_el_script_de_benchmarks_carga_la_rx_7600(catalogo):
    update_hardware_benchmarks()
    rx = Hardware.query.filter_by(modelo='RX 7600').one()
    assert rx.benchmark_score == PUNTAJE_RX_7600 and rx.vram_gb == 8


def test_el_script_de_requisitos_carga_los_cinco_juegos_incluidos_gta_v_y_counter_strike_2(catalogo):
    populate_game_requirements()
    cargados = {g.nombre: GameRequirements.get_by_game_id(g.id) for g in Game.query.all()}
    assert all(r is not None for r in cargados.values()), [n for n, r in cargados.items() if r is None]
    assert cargados['Counter-Strike 2'].min_cpu_score == puntaje_cpu('Core i5-750')


def test_el_analizador_con_los_datos_cargados_ya_no_tiene_juegos_sin_datos(client, catalogo):
    update_hardware_benchmarks()
    populate_game_requirements()
    ram = Hardware(tipo='RAM', marca='Corsair', modelo='Kit 16GB', precio=1, especificaciones='{"capacidad": "16 GB"}', stock=1)
    db.session.add(ram)
    db.session.commit()
    ids = {h.modelo: h.id for h in Hardware.query.all()}

    r = client.post('/api/analizar-hardware', json={'cpu_id': ids['Core i5-12400F'], 'gpu_id': ids['RTX 4060'],
                                                    'ram_id': ids['Kit 16GB']}).get_json()

    assert r['games']['sin_datos'] == [] and r['games']['cannot_run'] == []
    assert [j['nombre'] for j in r['games']['can_run_high']] == ['Cyberpunk 2077']
    assert all(j['expected_fps'] > 0 for lista in r['games'].values() for j in lista)
