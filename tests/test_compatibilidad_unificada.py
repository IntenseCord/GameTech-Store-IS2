"""
Las pantallas de hardware son vistas del mismo motor (utils/hardware_engine.py).

Regresión del bug crítico del plan: para la misma CPU/GPU/RAM y el mismo juego, la tienda
(/consultar-compatibilidad, /verificar-setup-completo) y el analizador (/api/analizar-hardware) podían dar
respuestas distintas, porque la tienda usaba un motor que adivinaba la potencia por palabras del texto
(models/compatibility.py, "i5" valía 70 y un texto desconocido valía 50) y el analizador usaba benchmark_score.
Además el analizador descartaba el FPS, el limitante y el motivo que el cálculo sí producía (FPS fijo en 60).
"""
import importlib
from pathlib import Path

import pytest

from extensions import db
from models.database_models import Game, GameRequirements, Hardware

RAIZ = Path(__file__).resolve().parent.parent


def _hw(tipo, marca, modelo, score=0, capacidad=None):
    specs = f'{{"capacidad": "{capacidad}"}}' if capacidad else '{}'
    h = Hardware(tipo=tipo, marca=marca, modelo=modelo, precio=100, especificaciones=specs, stock=3, benchmark_score=score)
    db.session.add(h)
    db.session.commit()
    return h


@pytest.fixture
def equipos(app_context):
    return {
        'cpu_fuerte': _hw('CPU', 'Intel', 'Core i9-FUERTE', 16000),
        'gpu_fuerte': _hw('GPU', 'NVIDIA', 'RTX FUERTE', 22000),
        'ram_32': _hw('RAM', 'Corsair', 'Kit 32GB', 0, '32 GB'),
        'cpu_medio': _hw('CPU', 'Intel', 'Core i7-MEDIO', 12500),
        'gpu_medio': _hw('GPU', 'NVIDIA', 'RTX MEDIA', 14500),
        'ram_16': _hw('RAM', 'Corsair', 'Kit 16GB', 0, '16 GB'),
        'cpu_debil': _hw('CPU', 'Intel', 'Core i3-DEBIL', 7000),
        'gpu_debil': _hw('GPU', 'NVIDIA', 'GTX DEBIL', 5000),
        'ram_4': _hw('RAM', 'Corsair', 'Kit 4GB', 0, '4 GB'),
        'gpu_sin_puntaje': _hw('GPU', 'AMD', 'RX SINDATO', 0),
    }


@pytest.fixture
def juego(test_game):
    db.session.add(GameRequirements(
        game_id=test_game.id, min_cpu_score=8000, min_gpu_score=7000, min_ram_gb=8,
        rec_cpu_score=12000, rec_gpu_score=14000, rec_ram_gb=12,
        ultra_cpu_score=15000, ultra_gpu_score=20000, ultra_ram_gb=20))
    db.session.commit()
    return test_game


def _consultar(client, **componentes):
    return client.post('/consultar-compatibilidad', json=componentes)


def _analizar(client, cpu, gpu, ram):
    return client.post('/api/analizar-hardware', json={'cpu_id': cpu.id, 'gpu_id': gpu.id, 'ram_id': ram.id})


def _categoria(analisis, juego_id):
    for categoria, lista in analisis['games'].items():
        if any(j['id'] == juego_id for j in lista):
            return categoria
    return None


# --------------------------------------------------- /consultar-compatibilidad
def test_consultar_con_nombres_del_catalogo_usa_los_puntajes_reales(client, equipos, juego):
    r = _consultar(client, cpu='Core i9-FUERTE', gpu='RTX FUERTE', ram='32 GB').get_json()

    assert r['success'] is True and r['componentes_sin_datos'] == []
    [j] = r['juegos']
    assert j['id'] == juego.id and j['calidad'] == 'ultra' and j['fps_estimado'] == 96


def test_consultar_con_hardware_insuficiente_no_lista_el_juego_pero_tampoco_lo_oculta_como_sin_datos(client, equipos, juego):
    r = _consultar(client, cpu='Core i3-DEBIL', gpu='GTX DEBIL', ram='4 GB').get_json()

    assert r['juegos'] == [] and r['sin_datos'] == []


def test_texto_desconocido_es_sin_datos_no_un_50_inventado(client, equipos, juego):
    """Antes cualquier texto que no estuviera en las tablas de palabras valía 50 y el juego salía 'compatible'."""
    r = _consultar(client, cpu='Intel Core i5-3570K', gpu='NVIDIA GeForce GTX 780', ram='8 GB').get_json()

    assert r['success'] is True
    assert r['juegos'] == []           # la RAM (8 GB) cumple, pero con CPU y GPU desconocidas no se confirma nada
    assert r['componentes_sin_datos'] == ['cpu', 'gpu']
    assert r['sin_datos'] == [juego.id]


def test_texto_desconocido_en_todo_deja_el_juego_en_sin_datos(client, equipos, juego):
    r = _consultar(client, cpu='procesador raro', gpu='tarjeta rara', ram='mucha').get_json()

    assert r['componentes_sin_datos'] == ['cpu', 'gpu', 'ram']
    assert r['sin_datos'] == [juego.id]


def test_un_componente_del_catalogo_sin_puntaje_cuenta_como_sin_datos(client, equipos, juego):
    r = _consultar(client, gpu='RX SINDATO').get_json()

    assert r['componentes_sin_datos'] == ['gpu'] and r['sin_datos'] == [juego.id] and r['juegos'] == []


def test_se_puede_consultar_con_un_solo_componente(client, equipos, juego):
    r = _consultar(client, gpu='RTX FUERTE').get_json()

    assert [j['id'] for j in r['juegos']] == [juego.id]
    assert _consultar(client, gpu='GTX DEBIL').get_json()['juegos'] == []


def test_un_juego_sin_requisitos_cargados_va_a_sin_datos_y_no_a_compatibles(client, equipos, test_game):
    r = _consultar(client, cpu='Core i9-FUERTE', gpu='RTX FUERTE', ram='32 GB').get_json()

    assert r['juegos'] == [] and r['sin_datos'] == [test_game.id]


def test_consultar_sin_ningun_componente_es_un_error_del_cliente(client, equipos, juego):
    r = _consultar(client, cpu='', gpu='', ram='')

    assert r.status_code == 400 and r.get_json()['success'] is False


# ----------------------------------------------------- /verificar-setup-completo
def test_setup_completo_compatible(client, equipos, juego):
    r = client.post('/verificar-setup-completo', json={
        'juegos': [juego.id], 'componentes': [equipos['cpu_fuerte'].id, equipos['gpu_fuerte'].id, equipos['ram_32'].id]}).get_json()

    assert r['success'] is True and r['compatible'] is True and r['sin_datos'] == []
    [d] = r['detalles']
    assert (d['juego_id'], d['calidad'], d['fps']) == (juego.id, 'ultra', 96)
    assert r['precio_total'] == pytest.approx(300 + float(juego.precio))


def test_setup_completo_incompatible_explica_el_motivo(client, equipos, juego):
    r = client.post('/verificar-setup-completo', json={
        'juegos': [juego.id], 'componentes': [equipos['cpu_debil'].id, equipos['gpu_debil'].id, equipos['ram_4'].id]}).get_json()

    assert r['compatible'] is False
    assert 'insuficiente' in r['detalles'][0]['motivo']


def test_setup_completo_con_componente_sin_puntaje_no_se_declara_compatible(client, equipos, juego):
    r = client.post('/verificar-setup-completo', json={
        'juegos': [juego.id], 'componentes': [equipos['cpu_fuerte'].id, equipos['gpu_sin_puntaje'].id, equipos['ram_32'].id]}).get_json()

    assert r['compatible'] is False and r['sin_datos'] == [juego.id]
    assert r['detalles'][0]['estado'] == 'sin_datos' and 'GPU' in r['detalles'][0]['motivo']


# -------------------------------------------------- /api/analizar-hardware
def test_el_analizador_ya_no_descarta_fps_limitante_ni_motivo(client, equipos, juego):
    fuerte = _analizar(client, equipos['cpu_fuerte'], equipos['gpu_fuerte'], equipos['ram_32']).get_json()
    debil = _analizar(client, equipos['cpu_debil'], equipos['gpu_debil'], equipos['ram_4']).get_json()

    [g_fuerte] = fuerte['games']['can_run_ultra']
    assert g_fuerte['expected_fps'] == 96 and g_fuerte['quality'] == 'ultra'
    [g_debil] = debil['games']['cannot_run']
    assert g_debil['expected_fps'] == 0 and g_debil['bottleneck'] in ('cpu', 'gpu', 'ram')
    assert 'insuficiente' in g_debil['reason']


def test_el_fps_del_analizador_varia_entre_equipos(client, equipos, juego):
    a = _analizar(client, equipos['cpu_fuerte'], equipos['gpu_fuerte'], equipos['ram_32']).get_json()
    b = _analizar(client, equipos['cpu_medio'], equipos['gpu_medio'], equipos['ram_16']).get_json()

    fps_a = a['games']['can_run_ultra'][0]['expected_fps']
    fps_b = b['games']['can_run_high'][0]['expected_fps']
    assert fps_a != fps_b


def test_juego_sin_requisitos_va_al_grupo_sin_datos_no_a_ultra(client, equipos, test_game):
    r = _analizar(client, equipos['cpu_fuerte'], equipos['gpu_fuerte'], equipos['ram_32']).get_json()

    assert [j['id'] for j in r['games']['sin_datos']] == [test_game.id]
    assert r['games']['can_run_ultra'] == [] and r['games']['cannot_run'] == []


def test_componente_sin_puntaje_no_inventa_un_nivel_ni_dice_balanceado(client, equipos, juego):
    r = _analizar(client, equipos['cpu_fuerte'], equipos['gpu_sin_puntaje'], equipos['ram_32']).get_json()

    assert r['success'] is True
    assert r['system_score']['total'] is None and r['system_score']['tier'] == 'Sin datos suficientes'
    assert r['system_score']['faltantes'] == ['gpu']
    assert r['bottlenecks']['type'] == 'sin_datos' and 'Balanceado' not in r['bottlenecks']['description']
    assert r['recommendations'] == []
    assert [j['id'] for j in r['games']['sin_datos']] == [juego.id]


def test_contrato_json_del_analizador(client, equipos, juego):
    r = _analizar(client, equipos['cpu_fuerte'], equipos['gpu_fuerte'], equipos['ram_32']).get_json()

    assert set(r) == {'success', 'system_score', 'bottlenecks', 'games', 'recommendations'}
    assert set(r['games']) == {'can_run_ultra', 'can_run_high', 'can_run_medium', 'can_run_low', 'cannot_run', 'sin_datos'}
    assert {'total', 'cpu_score', 'gpu_score', 'ram_score', 'ram_gb', 'tier', 'components', 'faltantes'} <= set(r['system_score'])
    assert r['system_score']['total'] == 17080 and r['system_score']['tier'] == 'Ultra High-End (4K Ultra)'
    assert set(r['games']['can_run_ultra'][0]) == {'id', 'nombre', 'imagen', 'precio', 'expected_fps', 'quality', 'bottleneck', 'reason'}


def test_un_error_interno_ya_no_se_traga_en_silencio_ni_se_filtra_al_cliente(client, equipos, juego, monkeypatch):
    def falla(*a, **k):
        raise RuntimeError('detalle-interno-xyz')
    monkeypatch.setattr('controllers.hardware_analyzer.detectar_cuello', falla)

    r = _analizar(client, equipos['cpu_fuerte'], equipos['gpu_fuerte'], equipos['ram_32'])

    assert r.status_code == 500
    assert 'detalle-interno-xyz' not in r.get_data(as_text=True)


# ------------------------------------------- las dos pantallas dan la misma respuesta
@pytest.mark.parametrize('cpu, gpu, ram, texto', [
    ('cpu_fuerte', 'gpu_fuerte', 'ram_32', ('Core i9-FUERTE', 'RTX FUERTE', '32 GB')),
    ('cpu_medio', 'gpu_medio', 'ram_16', ('Core i7-MEDIO', 'RTX MEDIA', '16 GB')),
    ('cpu_debil', 'gpu_debil', 'ram_4', ('Core i3-DEBIL', 'GTX DEBIL', '4 GB')),
    ('cpu_fuerte', 'gpu_debil', 'ram_16', ('Core i9-FUERTE', 'GTX DEBIL', '16 GB')),
])
def test_tienda_y_analizador_coinciden_para_el_mismo_equipo(client, equipos, juego, cpu, gpu, ram, texto):
    analisis = _analizar(client, equipos[cpu], equipos[gpu], equipos[ram]).get_json()
    tienda = _consultar(client, cpu=texto[0], gpu=texto[1], ram=texto[2]).get_json()

    corre_en_el_analizador = _categoria(analisis, juego.id) != 'cannot_run'
    corre_en_la_tienda = juego.id in [j['id'] for j in tienda['juegos']]
    assert corre_en_la_tienda == corre_en_el_analizador

    if corre_en_el_analizador:       # y con la misma calidad y el mismo FPS
        calidad = _categoria(analisis, juego.id).replace('can_run_', '')
        en_tienda = next(j for j in tienda['juegos'] if j['id'] == juego.id)
        assert en_tienda['calidad'] == calidad
        assert en_tienda['fps_estimado'] == next(j for j in analisis['games'][f'can_run_{calidad}'] if j['id'] == juego.id)['expected_fps']


# --------------------------------------------------------- el motor viejo ya no existe
def test_el_motor_viejo_por_palabras_fue_eliminado():
    assert not (RAIZ / 'models' / 'compatibility.py').exists()
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module('models.compatibility')
    assert not hasattr(Game, 'get_games_by_hardware')
    assert not (RAIZ / 'utils' / 'bottleneck_detector.py').exists()
    assert not (RAIZ / 'utils' / 'performance_calculator.py').exists()
