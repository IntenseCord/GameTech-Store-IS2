"""
Catálogo ampliado de juegos: Red Dead Redemption 2, Baldur's Gate 3 y Apex Legends.

Sus requisitos mínimo y recomendado son los de la ficha de Steam (consultada el 2026-10-30) y se calculan, como los demás,
con piezas de referencia en la escala única del proyecto (utils/benchmark_escala.py). El nivel ultra es criterio del
proyecto. Los productos se agregan a bases ya sembradas con `agregar_juegos_faltantes`, que no duplica si se repite.
"""
import json
from types import SimpleNamespace

import pytest

from database import agregar_juegos_faltantes, juegos_iniciales
from extensions import db
from models.database_models import Game, GameRequirements, Hardware
from scripts.populate_game_requirements import GAME_REQUIREMENTS_DATA, REFERENCIAS_POR_JUEGO, populate_game_requirements
from scripts.populate_hardware_benchmarks import update_hardware_benchmarks
from utils.benchmark_escala import CPU_SINGLE_THREAD, GPU_G3D, puntaje_cpu, puntaje_gpu
from utils.hardware_engine import Sistema, evaluar_juego

RDR2, BG3, APEX = 'Red Dead Redemption 2', "Baldur's Gate 3", 'Apex Legends'
NUEVOS = {RDR2, BG3, APEX}
ORIGINALES = {'Cyberpunk 2077', 'The Witcher 3: Wild Hunt', 'Grand Theft Auto V', 'Counter-Strike 2', 'Elden Ring'}


# ------------------------------------------------------- piezas de referencia nuevas
@pytest.mark.parametrize('nombre, esperado', [
    ('Core i5-4690', 5600), ('Core i7-4770K', 5530), ('Core i3-6300', 5780), ('Ryzen 5 3600', 6550),
])
def test_cpu_nuevas_en_la_escala(nombre, esperado):
    assert puntaje_cpu(nombre) == esperado


@pytest.mark.parametrize('nombre, esperado', [
    ('GeForce GTX 950', 3290), ('GeForce GTX 970', 5930), ('GeForce RTX 2060 Super', 10130),
])
def test_gpu_nuevas_en_la_escala(nombre, esperado):
    assert puntaje_gpu(nombre) == esperado


def test_el_orden_con_las_piezas_nuevas_respeta_el_rendimiento_real():
    cpus = ['Core i7-3770', 'Core i7-4770K', 'Core i5-4690', 'Core i7-4790', 'Core i3-6300', 'Core i5-8400',
            'Ryzen 5 3600', 'Core i7-8700K']
    gpus = ['GeForce GTX 950', 'GeForce GTX 770', 'GeForce GTX 780', 'Radeon RX 580', 'GeForce GTX 970',
            'GeForce GTX 1060', 'GeForce GTX 1070', 'GeForce RTX 2060', 'GeForce RTX 2060 Super',
            'GeForce GTX 1080 Ti']
    for lista, puntaje in ((cpus, puntaje_cpu), (gpus, puntaje_gpu)):
        valores = [puntaje(n) for n in lista]
        assert valores == sorted(valores) and len(set(valores)) == len(valores), lista


# ------------------------------------------------------------------ requisitos
def _req(juego):
    return next(g['requirements'] for g in GAME_REQUIREMENTS_DATA if g['game_name'] == juego)


def test_los_requisitos_cubren_los_ocho_juegos():
    assert len(GAME_REQUIREMENTS_DATA) == 8 and NUEVOS <= {g['game_name'] for g in GAME_REQUIREMENTS_DATA}


@pytest.mark.parametrize('juego', sorted(NUEVOS))
def test_minimo_y_recomendado_son_los_publicados_y_el_ultra_es_criterio_del_proyecto(juego):
    niveles = REFERENCIAS_POR_JUEGO[juego]
    assert niveles['min']['origen'] == 'publicado' and niveles['rec']['origen'] == 'publicado'
    assert niveles['ultra']['origen'] == 'proyecto'
    assert all(n['fuente'] for n in niveles.values())


@pytest.mark.parametrize('juego', sorted(NUEVOS))
def test_los_requisitos_nuevos_crecen_de_minimo_a_recomendado_a_ultra(juego):
    r = _req(juego)
    for campo in ('cpu_score', 'gpu_score', 'ram_gb', 'vram_gb'):
        assert r[f'min_{campo}'] <= r[f'rec_{campo}'] <= r[f'ultra_{campo}'], (juego, campo)
    assert r['min_cpu_score'] > 0 and r['min_gpu_score'] > 0


@pytest.mark.parametrize('juego, ram_min, ram_rec, cpu_min, gpu_min, cpu_rec, gpu_rec', [
    (RDR2, 8, 12, 'Core i5-2500K', 'GeForce GTX 770', 'Core i7-4770K', 'GeForce GTX 1060'),
    (BG3, 8, 16, 'Core i5-4690', 'GeForce GTX 970', 'Ryzen 5 3600', 'GeForce RTX 2060 Super'),
    (APEX, 6, 8, 'Core i3-6300', 'GeForce GTX 950', 'Ryzen 5 3600', 'GeForce GTX 970'),
])
def test_los_requisitos_nuevos_coinciden_con_la_ficha_de_steam(juego, ram_min, ram_rec, cpu_min, gpu_min, cpu_rec, gpu_rec):
    r = _req(juego)
    assert (r['min_ram_gb'], r['rec_ram_gb']) == (ram_min, ram_rec)
    assert (r['min_cpu_score'], r['min_gpu_score']) == (puntaje_cpu(cpu_min), puntaje_gpu(gpu_min))
    assert (r['rec_cpu_score'], r['rec_gpu_score']) == (puntaje_cpu(cpu_rec), puntaje_gpu(gpu_rec))


def test_almacenamiento_y_ssd_de_steam():
    assert (_req(RDR2)['storage_gb'], _req(BG3)['storage_gb'], _req(APEX)['storage_gb']) == (150, 150, 75)
    assert _req(BG3)['requires_ssd'] is True and _req(RDR2)['requires_ssd'] is False


def test_las_piezas_de_referencia_nuevas_existen_en_la_escala():
    for juego in NUEVOS:
        for ref in REFERENCIAS_POR_JUEGO[juego].values():
            assert ref['cpu'] in CPU_SINGLE_THREAD and ref['gpu'] in GPU_G3D


# ------------------------------------------------- el motor con los juegos nuevos
def _ns(juego):
    return SimpleNamespace(**_req(juego))


def test_un_equipo_actual_corre_los_tres_en_ultra():
    s = Sistema(cpu=9000, gpu=12000, ram_gb=16)                       # i5-12400F + RTX 4060
    assert {j: evaluar_juego(s, _ns(j))['calidad'] for j in NUEVOS} == {RDR2: 'ultra', BG3: 'ultra', APEX: 'ultra'}


def test_un_equipo_de_2012_no_corre_ninguno_de_los_tres():
    s = Sistema(cpu=puntaje_cpu('Core i5-2500K'), gpu=puntaje_gpu('GeForce GTX 660'), ram_gb=8)
    assert [evaluar_juego(s, _ns(j))['puede_correr'] for j in (RDR2, BG3, APEX)] == [False, False, False]


def test_un_equipo_de_gama_baja_corre_rdr2_y_apex_pero_no_baldurs_gate_3():
    """i5-8400 + GTX 1650: la GTX 1650 queda por debajo de la GTX 970 que pide BG3 como mínimo."""
    s = Sistema(cpu=puntaje_cpu('Core i5-8400'), gpu=puntaje_gpu('GeForce GTX 1650'), ram_gb=16)
    assert evaluar_juego(s, _ns(RDR2))['puede_correr'] is True
    assert evaluar_juego(s, _ns(APEX))['puede_correr'] is True
    assert evaluar_juego(s, _ns(BG3))['puede_correr'] is False


# ----------------------------------------------------------- los productos de la tienda
def test_juegos_iniciales_incluye_los_ocho_sin_repetir():
    nombres = [j.nombre for j in juegos_iniciales()]
    assert len(nombres) == len(set(nombres)) == 8 and NUEVOS <= set(nombres) and ORIGINALES <= set(nombres)


def test_agregar_juegos_faltantes_completa_una_base_ya_sembrada(app_context):
    db.session.add_all([j for j in juegos_iniciales() if j.nombre in ORIGINALES])
    db.session.commit()

    agregados = agregar_juegos_faltantes()

    assert set(agregados) == NUEVOS
    assert Game.query.count() == 8


def test_agregar_juegos_faltantes_no_duplica_si_se_repite(app_context):
    agregar_juegos_faltantes()
    assert agregar_juegos_faltantes() == []
    assert Game.query.count() == 8


def test_los_juegos_nuevos_usan_los_datos_de_steam(app_context):
    agregar_juegos_faltantes()
    por_nombre = {g.nombre: g for g in Game.query.all()}
    assert (por_nombre[RDR2].desarrollador, float(por_nombre[RDR2].precio)) == ('Rockstar Games', 59.99)
    assert (por_nombre[BG3].desarrollador, float(por_nombre[BG3].precio)) == ('Larian Studios', 59.99)
    assert (por_nombre[APEX].desarrollador, float(por_nombre[APEX].precio)) == ('Respawn', 0.0)   # gratuito, como Counter-Strike 2
    for nombre in NUEVOS:
        g = por_nombre[nombre]
        assert g.stock > 0 and g.imagen and g.descripcion and g.fecha_lanzamiento
        assert json.loads(g.requisitos_minimos)['RAM'] and json.loads(g.requisitos_recomendados)['GPU']


# ------------------------------------------------------- de punta a punta con la base
def test_el_analizador_incluye_los_ocho_juegos_sin_datos_faltantes(client, app_context):
    hw = [
        Hardware(tipo='CPU', marca='Intel', modelo='Core i5-12400F', precio=1, especificaciones='{}', stock=1),
        Hardware(tipo='GPU', marca='NVIDIA', modelo='RTX 4060', precio=1, especificaciones='{}', stock=1),
        Hardware(tipo='RAM', marca='Corsair', modelo='Kit 16GB', precio=1, especificaciones='{"capacidad": "16 GB"}', stock=1),
    ]
    db.session.add_all(hw)
    agregar_juegos_faltantes()
    db.session.commit()
    update_hardware_benchmarks()
    populate_game_requirements()
    ids = {h.modelo: h.id for h in Hardware.query.all()}

    r = client.post('/api/analizar-hardware', json={'cpu_id': ids['Core i5-12400F'], 'gpu_id': ids['RTX 4060'],
                                                    'ram_id': ids['Kit 16GB']}).get_json()

    todos = [j['nombre'] for lista in r['games'].values() for j in lista]
    assert len(todos) == 8 and r['games']['sin_datos'] == [] and r['games']['cannot_run'] == []
    assert NUEVOS <= set(todos)
    # la RTX 4060 tiene 8 GB de VRAM: Cyberpunk (10 GB), RDR2 y Baldur's Gate 3 (11 GB) no llegan a ultra
    assert {j['nombre'] for j in r['games']['can_run_high']} == {'Cyberpunk 2077', 'Red Dead Redemption 2', "Baldur's Gate 3"}
    assert GameRequirements.query.count() == 8
