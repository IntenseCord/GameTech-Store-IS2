"""
SmartBuildAdvisor: `armar_pc` (utils/asesor.py) y su API (/api/armar-pc).

El asesor es una función del motor, no de la pantalla: dado un presupuesto y un uso busca, entre las piezas del catálogo, la PC
completa y compatible que mejor corre los juegos del perfil. La prueba central es un ORÁCULO de fuerza bruta: recorre las 16 384
combinaciones del catálogo (4 opciones x 7 tipos) con los mismos evaluadores y comprueba que el asesor encuentra el óptimo.
"""
import itertools
from types import SimpleNamespace

import pytest

from database import agregar_juegos_faltantes, hardware_inicial, juegos_iniciales, sincronizar_hardware
from extensions import db
from models.database_models import Hardware
from scripts.populate_game_requirements import GAME_REQUIREMENTS_DATA, populate_game_requirements
from utils.asesor import PERFILES, PUNTOS_POR_CALIDAD, armar_pc
from utils.compatibilidad import INCOMPATIBLE, JUSTA, OK, estado_general, verificar_configuracion
from utils.hardware_engine import evaluar_juego, puntuacion_total, sistema_de

TIPOS = ('CPU', 'Motherboard', 'RAM', 'GPU', 'Fuente de poder', 'Refrigeración', 'Gabinete')


def piezas():
    return hardware_inicial()


def juegos():
    """Los 8 juegos del catálogo con sus requisitos (como los entrega el controlador)."""
    resultado = []
    for g in juegos_iniciales():
        datos = next(d['requirements'] for d in GAME_REQUIREMENTS_DATA if d['game_name'] in g.nombre)
        resultado.append(SimpleNamespace(nombre=g.nombre, genero=g.genero, requisitos=SimpleNamespace(**datos)))
    return resultado


# ---------------------------------------------------------- oráculo de fuerza bruta
def _clave(piezas_elegidas, perfil_juegos):
    cpu, placa, ram, gpu, fuente, enfriador, gabinete = piezas_elegidas
    sistema = sistema_de(cpu, gpu, ram)
    evaluaciones = [evaluar_juego(sistema, j.requisitos) for j in perfil_juegos]
    puntos = sum(PUNTOS_POR_CALIDAD[e['calidad']] for e in evaluaciones if e['estado'] != 'sin_datos')
    fps = sum(e['fps'] for e in evaluaciones if e['estado'] != 'sin_datos')
    precio = round(sum(float(p.precio) for p in piezas_elegidas), 2)
    return (puntos, fps, puntuacion_total(sistema), -precio), precio


@pytest.fixture(scope='module')
def todas_las_combinaciones_ok():
    """[(piezas, estado)] de las combinaciones del catálogo en las que NINGUNA verificación es incompatible."""
    catalogo = piezas()
    por_tipo = [[p for p in catalogo if p.tipo == t] for t in TIPOS]
    validas = []
    for combo in itertools.product(*por_tipo):
        cpu, placa, ram, gpu, fuente, enfriador, gabinete = combo
        v = verificar_configuracion(cpu=cpu, gpu=gpu, ram=ram, placa=placa, fuente=fuente, enfriador=enfriador, gabinete=gabinete)
        estado = estado_general(v)
        if estado != INCOMPATIBLE:
            validas.append((combo, estado))
    return validas


@pytest.mark.parametrize('uso', ['gaming', 'esports', 'aaa'])
@pytest.mark.parametrize('presupuesto', [800, 1000, 1500, 2000])
def test_el_asesor_encuentra_el_optimo_que_halla_la_fuerza_bruta(todas_las_combinaciones_ok, presupuesto, uso):
    perfil = [j for j in juegos() if PERFILES[uso]['filtro'](j)]
    candidatas = [(combo, *_clave(combo, perfil)) for combo, estado in todas_las_combinaciones_ok
                  if estado == OK and _clave(combo, perfil)[1] <= presupuesto]
    mejor_clave = max(c[1] for c in candidatas)

    r = armar_pc(piezas(), juegos(), presupuesto, uso)

    assert r['ok'] is True and r['estado'] == OK
    o = r['objetivo']
    assert (o['puntos'], o['fps'], o['total'], -r['precio_total']) == mejor_clave


# ------------------------------------------------------------------ propiedades
def test_la_pc_armada_esta_completa_dentro_del_presupuesto_y_es_compatible():
    r = armar_pc(piezas(), juegos(), 1200, 'gaming')
    assert set(r['piezas']) == set(TIPOS)
    assert r['precio_total'] <= 1200 and r['sobrante'] == round(1200 - r['precio_total'], 2)
    assert all(v['estado'] == OK for v in r['verificaciones']) and len(r['verificaciones']) == 8


def test_con_mas_presupuesto_nunca_se_corre_peor():
    puntos = [armar_pc(piezas(), juegos(), p, 'gaming')['objetivo']['puntos'] for p in (800, 900, 1000, 1200, 1400, 1500, 2000)]
    assert puntos == sorted(puntos) and puntos[0] < puntos[-1]


def test_el_resultado_trae_el_rendimiento_y_los_juegos_del_perfil():
    r = armar_pc(piezas(), juegos(), 1500, 'gaming')
    assert r['rendimiento']['total'] and r['rendimiento']['nivel']
    assert len(r['juegos']) == 8 and {'nombre', 'calidad', 'fps', 'limitante'} <= set(r['juegos'][0])
    assert f"{r['precio_total']:.2f}" in r['resumen']


def test_cada_perfil_evalua_solo_sus_juegos():
    esports = armar_pc(piezas(), juegos(), 1000, 'esports')
    aaa = armar_pc(piezas(), juegos(), 1000, 'aaa')
    assert {j['nombre'] for j in esports['juegos']} == {'Counter-Strike 2', 'Apex Legends'}
    assert 'Counter-Strike 2' not in {j['nombre'] for j in aaa['juegos']} and len(aaa['juegos']) == 6


def test_un_uso_desconocido_es_un_error():
    with pytest.raises(ValueError):
        armar_pc(piezas(), juegos(), 1000, 'minería')


# ----------------------------------------------------- presupuesto insuficiente
def test_si_no_alcanza_el_presupuesto_dice_cual_es_el_minimo():
    r = armar_pc(piezas(), juegos(), 300, 'gaming')
    assert r['ok'] is False and 'piezas' not in r
    minimo = r['precio_minimo']
    assert minimo > 300 and f'{minimo:.2f}' in r['motivo']
    # con exactamente ese presupuesto sí se puede armar
    assert armar_pc(piezas(), juegos(), minimo, 'gaming')['ok'] is True
    assert armar_pc(piezas(), juegos(), minimo - 0.01, 'gaming')['ok'] is False


def test_el_precio_minimo_coincide_con_la_fuerza_bruta(todas_las_combinaciones_ok):
    """El mínimo es la combinación aceptable (ok o justa) más barata del catálogo."""
    barata = min(round(sum(float(p.precio) for p in combo), 2) for combo, _ in todas_las_combinaciones_ok)
    assert armar_pc(piezas(), juegos(), 1, 'gaming')['precio_minimo'] == barata


# ----------------------------------------------------------------------- stock
def test_una_pieza_sin_stock_no_se_usa():
    catalogo = piezas()
    for p in catalogo:
        if p.modelo == 'RTX 4070':
            p.stock = 0
    r = armar_pc(catalogo, juegos(), 5000, 'gaming')
    assert r['piezas']['GPU'].modelo != 'RTX 4070'


def test_si_falta_un_tipo_completo_no_se_puede_armar():
    sin_gabinetes = [p for p in piezas() if p.tipo != 'Gabinete']
    r = armar_pc(sin_gabinetes, juegos(), 5000, 'gaming')
    assert r['ok'] is False and 'Gabinete' in r['motivo']


# ------------------------------------------------------------------ desempates y datos que faltan
def test_a_igual_rendimiento_elige_la_combinacion_mas_barata():
    """Una GPU idéntica a la RTX 4060 pero $10 más cara no debe ganar: rinde igual y cuesta más."""
    catalogo = piezas()
    original = next(p for p in catalogo if p.modelo == 'RTX 4060')
    clon = type(original)(tipo='GPU', marca='Marca X', modelo='RTX 4060 edición cara', precio=float(original.precio) + 10,
                          especificaciones=original.especificaciones, stock=5, benchmark_score=original.benchmark_score,
                          vram_gb=original.vram_gb, tdp_watts=original.tdp_watts)
    r = armar_pc(catalogo + [clon], juegos(), 1200, 'gaming')
    assert r['piezas']['GPU'].modelo != 'RTX 4060 edición cara'
    sin_clon = armar_pc(catalogo, juegos(), 1200, 'gaming')
    assert r['precio_total'] == sin_clon['precio_total']


def test_un_juego_sin_requisitos_no_suma_ni_rompe_el_calculo():
    sin_datos = SimpleNamespace(nombre='Juego sin requisitos', genero='RPG', requisitos=None)
    base = armar_pc(piezas(), juegos(), 1200, 'gaming')
    con = armar_pc(piezas(), juegos() + [sin_datos], 1200, 'gaming')
    assert con['objetivo'] == base['objetivo'] and con['precio_total'] == base['precio_total']
    fila = next(j for j in con['juegos'] if j['nombre'] == 'Juego sin requisitos')
    assert fila['calidad'] is None


# ------------------------------------------------------------ "justa" como último recurso
def test_si_solo_hay_combinaciones_justas_las_acepta_y_lo_advierte():
    elegidas = {'Core i5-12400F', 'MAG B660M Mortar WiFi DDR4', 'Vengeance LPX 16GB DDR4', 'RTX 4060', 'CX550 550W', 'AK400', 'MasterBox Q300L'}
    r = armar_pc([p for p in piezas() if p.modelo in elegidas], juegos(), 5000, 'gaming')
    assert r['ok'] is True and r['estado'] == JUSTA
    assert 'justa' in r['resumen'].lower()


def test_prefiere_una_combinacion_ok_aunque_rinda_menos_que_una_justa():
    """Con una fuente de 550 W, la RTX 4060 + i5-12400F es 'justa' y la GTX 1650 es 'ok': elige la segunda."""
    elegidas = {'Core i5-12400F', 'MAG B660M Mortar WiFi DDR4', 'Vengeance LPX 16GB DDR4', 'RTX 4060', 'GTX 1650', 'CX550 550W', 'AK400', 'MasterBox Q300L'}
    r = armar_pc([p for p in piezas() if p.modelo in elegidas], juegos(), 5000, 'gaming')
    assert r['estado'] == OK and r['piezas']['GPU'].modelo == 'GTX 1650'


# ------------------------------------------------------------ cuánto más subirías
def test_dice_cuanto_mas_habria_que_gastar_para_subir_de_nivel():
    r = armar_pc(piezas(), juegos(), 800, 'gaming')
    s = r['siguiente']
    assert s is not None and s['precio_extra'] > 0 and s['puntos'] > r['objetivo']['puntos']
    assert round(r['precio_total'] + s['precio_extra'], 2) > 800                  # lo que no alcanzaba con el presupuesto
    mejorada = armar_pc(piezas(), juegos(), round(r['precio_total'] + s['precio_extra'], 2), 'gaming')
    assert mejorada['objetivo']['puntos'] >= s['puntos']


@pytest.mark.parametrize('presupuesto', [800, 1000, 1200])
def test_el_siguiente_nivel_es_la_combinacion_mas_barata_que_mejora_los_puntos(todas_las_combinaciones_ok, presupuesto):
    perfil = juegos()
    r = armar_pc(piezas(), juegos(), presupuesto, 'gaming')
    mejores = [clave_precio for combo, estado in todas_las_combinaciones_ok if estado == OK
               for (clave, clave_precio) in [_clave(combo, perfil)] if clave[0] > r['objetivo']['puntos']]
    assert r['siguiente']['precio_total'] == min(mejores)
    assert r['siguiente']['precio_extra'] == round(min(mejores) - r['precio_total'], 2)


@pytest.mark.parametrize('uso, presupuesto', [('esports', 2000), ('esports', 1000), ('gaming', 2000), ('gaming', 800), ('aaa', 1500)])
def test_dice_desde_cuanto_se_consigue_la_misma_calidad(todas_las_combinaciones_ok, uso, presupuesto):
    perfil = [j for j in juegos() if PERFILES[uso]['filtro'](j)]
    r = armar_pc(piezas(), juegos(), presupuesto, uso)
    igual_o_mejor = [precio for combo, estado in todas_las_combinaciones_ok if estado == OK
                     for (clave, precio) in [_clave(combo, perfil)] if clave[0] >= r['objetivo']['puntos']]
    assert r['desde'] == min(igual_o_mejor)
    assert r['desde'] <= r['precio_total']
    texto = f"desde ${r['desde']:.2f}"
    assert (texto in r['resumen']) == (r['desde'] < r['precio_total'])        # solo lo menciona si de verdad se podía gastar menos


def test_con_el_presupuesto_minimo_no_hay_nada_mas_barato_que_mencionar():
    minimo = armar_pc(piezas(), juegos(), 1, 'gaming')['precio_minimo']
    r = armar_pc(piezas(), juegos(), minimo, 'gaming')
    assert r['desde'] == r['precio_total'] == minimo and 'desde $' not in r['resumen']


def test_la_pc_maxima_no_tiene_siguiente_nivel():
    assert armar_pc(piezas(), juegos(), 100000, 'gaming')['siguiente'] is None


# --------------------------------------------------------------------------- API
@pytest.fixture
def base(app_context):
    sincronizar_hardware()
    agregar_juegos_faltantes()
    populate_game_requirements()


def _armar(client, **cuerpo):
    return client.post('/api/armar-pc', json=cuerpo)


def test_la_api_arma_una_pc_con_ids_y_precios_reales(client, base):
    r = _armar(client, presupuesto=1200, uso='gaming')
    assert r.status_code == 200
    d = r.get_json()
    assert d['success'] is True and d['ok'] is True and d['estado'] == OK
    assert set(d['piezas']) == set(TIPOS)
    for tipo, p in d['piezas'].items():
        h = db.session.get(Hardware, p['id'])
        assert h.tipo == tipo and float(h.precio) == p['precio'] and h.modelo == p['modelo']
    assert d['precio_total'] <= 1200


def test_lo_que_arma_la_api_lo_confirma_la_api_de_verificacion(client, base):
    """Un solo motor: la PC del asesor es 'ok' para el verificador y tiene el mismo rendimiento."""
    d = _armar(client, presupuesto=1500, uso='gaming').get_json()
    ids = {'cpu_id': d['piezas']['CPU']['id'], 'gpu_id': d['piezas']['GPU']['id'], 'ram_id': d['piezas']['RAM']['id'],
           'placa_id': d['piezas']['Motherboard']['id'], 'fuente_id': d['piezas']['Fuente de poder']['id'],
           'enfriador_id': d['piezas']['Refrigeración']['id'], 'gabinete_id': d['piezas']['Gabinete']['id']}
    v = client.post('/api/verificar-configuracion', json=ids).get_json()
    assert v['estado'] == OK and v['rendimiento']['total'] == d['rendimiento']['total']
    assert v['rendimiento']['nivel'] == d['rendimiento']['nivel']


def test_la_api_con_presupuesto_insuficiente_responde_200_con_el_minimo(client, base):
    d = _armar(client, presupuesto=100, uso='gaming').get_json()
    assert d['success'] is True and d['ok'] is False and d['precio_minimo'] > 100


@pytest.mark.parametrize('cuerpo', [
    {}, {'presupuesto': 'mucho', 'uso': 'gaming'}, {'presupuesto': -5, 'uso': 'gaming'}, {'presupuesto': 0, 'uso': 'gaming'},
    {'presupuesto': 1000, 'uso': 'minería'}, {'presupuesto': 1000},
])
def test_la_api_rechaza_entradas_invalidas(client, base, cuerpo):
    assert _armar(client, **cuerpo).status_code == 400


def test_la_api_no_revela_detalles_internos_si_falla(client, base, monkeypatch):
    import controllers.hardware as hw

    def falla(*_, **__):
        raise RuntimeError('detalle interno secreto')
    monkeypatch.setattr(hw, 'armar_pc', falla)
    r = _armar(client, presupuesto=1000, uso='gaming')
    assert r.status_code == 500 and 'secreto' not in r.get_data(as_text=True)
