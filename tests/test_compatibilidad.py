"""
Compatibilidad entre componentes (utils/compatibilidad.py) y su API (/api/verificar-configuracion).

Parte del motor único: hardware_engine opina sobre RENDIMIENTO y este módulo sobre ENCAJE FÍSICO Y ELÉCTRICO
(socket, memoria, fuente, enfriador, gabinete). Las piezas de los tests salen del catálogo real (utils/catalogo_hardware.py).
Regla de la fuente (aprobada): potencia >= max(fuente recomendada de la GPU, consumo máximo de CPU + consumo de GPU + 100 W);
si no hay un 20 % de holgura sobre esa potencia, la verificación es "justa".
"""
import json

import pytest

from database import hardware_inicial, sincronizar_hardware
from models.database_models import Hardware
from utils.compatibilidad import (
    CAMPOS_POR_TIPO, INCOMPATIBLE, JUSTA, OK, SIN_DATOS, estado_general, verificar_configuracion,
)

_CATALOGO = {h.modelo: h for h in hardware_inicial()}


def p(modelo, **cambios):
    """Pieza del catálogo; `cambios` reemplaza claves de `especificaciones` (copia: no toca el catálogo)."""
    base = _CATALOGO[modelo]
    pieza = Hardware(tipo=base.tipo, marca=base.marca, modelo=base.modelo, socket=base.socket, tdp_watts=base.tdp_watts,
                     especificaciones=base.especificaciones)
    if cambios:
        specs = json.loads(pieza.especificaciones)
        specs.update(cambios)
        pieza.especificaciones = json.dumps(specs)
    return pieza


def estados(**piezas):
    return {v['par']: v['estado'] for v in verificar_configuracion(**piezas)}


def mensaje(par, **piezas):
    return next(v['mensaje'] for v in verificar_configuracion(**piezas) if v['par'] == par)


# --------------------------------------------------------------------- CPU y placa
@pytest.mark.parametrize('cpu, placa, esperado', [
    ('Core i5-12400F', 'MAG B660M Mortar WiFi DDR4', OK),
    ('Ryzen 5 7600X', 'MAG B650 Tomahawk WiFi', OK),
    ('Ryzen 5 5600', 'ROG Strix B450-F Gaming', OK),
    ('Core i7-13700K', 'MAG Z790 Tomahawk WiFi', OK),
    ('Core i5-12400F', 'ROG Strix B450-F Gaming', INCOMPATIBLE),
    ('Ryzen 5 5600', 'MAG B650 Tomahawk WiFi', INCOMPATIBLE),
    ('Ryzen 5 7600X', 'MAG Z790 Tomahawk WiFi', INCOMPATIBLE),
])
def test_cpu_y_placa_deben_tener_el_mismo_socket(cpu, placa, esperado):
    assert estados(cpu=p(cpu), placa=p(placa))['cpu_placa'] == esperado


def test_el_mensaje_de_socket_dice_cuales_son():
    m = mensaje('cpu_placa', cpu=p('Core i5-12400F'), placa=p('ROG Strix B450-F Gaming'))
    assert 'LGA1700' in m and 'AM4' in m


# ------------------------------------------------------------------------- memoria
@pytest.mark.parametrize('ram, placa, esperado', [
    ('Vengeance LPX 16GB DDR4', 'MAG B660M Mortar WiFi DDR4', OK),
    ('Vengeance 16GB DDR5', 'MAG B650 Tomahawk WiFi', OK),
    ('Vengeance 32GB DDR5', 'MAG Z790 Tomahawk WiFi', OK),
    ('Vengeance 16GB DDR5', 'MAG B660M Mortar WiFi DDR4', INCOMPATIBLE),
    ('Trident Z RGB 32GB DDR4', 'MAG B650 Tomahawk WiFi', INCOMPATIBLE),
])
def test_la_ram_debe_ser_del_tipo_de_memoria_de_la_placa(ram, placa, esperado):
    assert estados(ram=p(ram), placa=p(placa))['ram_placa'] == esperado


@pytest.mark.parametrize('cpu, ram, esperado', [
    ('Ryzen 5 7600X', 'Vengeance 16GB DDR5', OK),
    ('Core i7-13700K', 'Vengeance LPX 16GB DDR4', OK),       # el i7-13700K acepta DDR4 y DDR5
    ('Core i7-13700K', 'Vengeance 32GB DDR5', OK),
    ('Ryzen 5 7600X', 'Vengeance LPX 16GB DDR4', INCOMPATIBLE),
    ('Ryzen 5 5600', 'Vengeance 16GB DDR5', INCOMPATIBLE),
])
def test_la_cpu_debe_aceptar_el_tipo_de_memoria(cpu, ram, esperado):
    assert estados(cpu=p(cpu), ram=p(ram))['cpu_ram'] == esperado


# ------------------------------------------------------------------- fuente de poder
@pytest.mark.parametrize('cpu, gpu, fuente, esperado', [
    ('Core i7-13700K', 'RTX 4070', 'CX550 550W', INCOMPATIBLE),     # pide 650 W (recomendada de la GPU)
    ('Core i7-13700K', 'RTX 4070', 'RM650e 650W', JUSTA),
    ('Core i7-13700K', 'RTX 4070', 'RM750e 750W', JUSTA),           # 750 < 650 x 1,2 = 780
    ('Core i7-13700K', 'RTX 4070', 'RM850e 850W', OK),
    ('Core i5-12400F', 'RTX 4060', 'CX550 550W', JUSTA),            # pide 550 W
    ('Core i5-12400F', 'RTX 4060', 'RM750e 750W', OK),
    ('Ryzen 5 5600', 'GTX 1650', 'CX550 550W', OK),                 # pide 300 W
])
def test_regla_de_la_fuente_de_poder(cpu, gpu, fuente, esperado):
    assert estados(cpu=p(cpu), gpu=p(gpu), fuente=p(fuente))['fuente'] == esperado


def test_la_fuente_usa_el_consumo_real_cuando_supera_la_recomendacion_de_la_gpu():
    """Una GPU con recomendación baja pero CPU muy exigente: manda CPU + GPU + 100 W."""
    gpu = p('RTX 4060', psu_recomendada_w=300)
    cpu = p('Core i7-13700K')                                        # 253 + 115 + 100 = 468 W
    assert estados(cpu=cpu, gpu=gpu, fuente=p('CX550 550W'))['fuente'] == JUSTA   # 550 < 468 x 1,2 = 561,6
    cpu_debil = p('Ryzen 5 5600')                                    # 76 + 115 + 100 = 291 -> se impone la recomendada (300)
    assert estados(cpu=cpu_debil, gpu=gpu, fuente=p('CX550 550W'))['fuente'] == OK


def test_el_mensaje_de_la_fuente_dice_la_potencia_pedida():
    m = mensaje('fuente', cpu=p('Core i7-13700K'), gpu=p('RTX 4070'), fuente=p('CX550 550W'))
    assert '650' in m and '550' in m


def test_sin_gpu_o_sin_cpu_no_se_evalua_la_fuente():
    assert 'fuente' not in estados(cpu=p('Core i7-13700K'), fuente=p('CX550 550W'))
    assert 'fuente' not in estados(gpu=p('RTX 4070'), fuente=p('CX550 550W'))


# ------------------------------------------------------------------------ enfriador
@pytest.mark.parametrize('cpu, enfriador, esperado', [
    ('Core i7-13700K', 'AK400', JUSTA),        # 220 W: aguanta el TDP base (125 W) pero no el máximo (253 W)
    ('Core i7-13700K', 'AK620', OK),
    ('Core i7-13700K', 'LS720', OK),
    ('Core i5-12400F', 'AK400', OK),
    ('Ryzen 5 7600X', 'AK400', OK),
])
def test_el_enfriador_debe_aguantar_el_consumo_de_la_cpu(cpu, enfriador, esperado):
    assert estados(cpu=p(cpu), enfriador=p(enfriador))['enfriador_cpu'] == esperado


def test_un_enfriador_sin_el_socket_de_la_cpu_es_incompatible():
    solo_am4 = p('AK620', sockets=['AM4'])
    assert estados(cpu=p('Core i5-12400F'), enfriador=solo_am4)['enfriador_cpu'] == INCOMPATIBLE
    assert estados(cpu=p('Ryzen 5 5600'), enfriador=solo_am4)['enfriador_cpu'] == OK


def test_un_enfriador_que_no_llega_ni_al_tdp_base_es_incompatible():
    debil = p('AK400', tdp_max_w=100)
    assert estados(cpu=p('Core i7-13700K'), enfriador=debil)['enfriador_cpu'] == INCOMPATIBLE


# ------------------------------------------------------------------------- gabinete
@pytest.mark.parametrize('gabinete, placa, esperado', [
    ('MasterBox Q300L', 'MAG B660M Mortar WiFi DDR4', OK),       # micro-ATX en gabinete micro-ATX
    ('MasterBox Q300L', 'MAG B650 Tomahawk WiFi', INCOMPATIBLE),  # ATX no cabe
    ('H5 Flow', 'MAG Z790 Tomahawk WiFi', OK),
    ('4000D Airflow', 'MAG B660M Mortar WiFi DDR4', OK),         # un gabinete ATX acepta micro-ATX
])
def test_la_placa_debe_caber_en_el_gabinete(gabinete, placa, esperado):
    assert estados(gabinete=p(gabinete), placa=p(placa))['gabinete_placa'] == esperado


@pytest.mark.parametrize('gabinete, gpu_largo, esperado', [
    ('MasterBox Q300L', 244, OK),
    ('4000D Airflow', 360, OK),              # justo en el límite
    ('4000D Airflow', 361, INCOMPATIBLE),
    ('5000D Airflow', 400, OK),
])
def test_la_gpu_debe_caber_en_el_gabinete(gabinete, gpu_largo, esperado):
    gpu = p('RTX 4070', largo_mm=gpu_largo)
    assert estados(gabinete=p(gabinete), gpu=gpu)['gabinete_gpu'] == esperado


@pytest.mark.parametrize('gabinete, enfriador, esperado', [
    ('MasterBox Q300L', 'AK400', OK),           # 155 <= 159
    ('MasterBox Q300L', 'AK620', INCOMPATIBLE),  # 160 > 159: por 1 mm
    ('4000D Airflow', 'AK620', OK),
    ('4000D Airflow', 'LS720', OK),              # radiador 360 en gabinete que acepta 360
    ('H5 Flow', 'LS520', OK),                    # 240 <= 280
    ('H5 Flow', 'LS720', INCOMPATIBLE),          # 360 > 280
    ('MasterBox Q300L', 'LS520', INCOMPATIBLE),  # sin soporte de radiador declarado
])
def test_el_enfriador_debe_caber_en_el_gabinete(gabinete, enfriador, esperado):
    assert estados(gabinete=p(gabinete), enfriador=p(enfriador))['gabinete_enfriador'] == esperado


def test_el_mensaje_del_radiador_sin_soporte_lo_dice():
    assert 'soporte' in mensaje('gabinete_enfriador', gabinete=p('MasterBox Q300L'), enfriador=p('LS520'))


# ------------------------------------------------------------- datos que faltan
def test_una_pieza_sin_dato_da_sin_datos_y_no_incompatible():
    sin_socket = Hardware(tipo='Motherboard', marca='X', modelo='Placa sin socket', especificaciones='{}')
    r = estados(cpu=p('Core i5-12400F'), placa=sin_socket)
    assert r['cpu_placa'] == SIN_DATOS
    sin_largo = Hardware(tipo='GPU', marca='X', modelo='GPU sin largo', especificaciones='{}')
    assert estados(gabinete=p('4000D Airflow'), gpu=sin_largo)['gabinete_gpu'] == SIN_DATOS


# ------------------------------------------------------------- configuración completa
def test_una_configuracion_completa_y_coherente_da_ok():
    piezas = dict(cpu=p('Core i5-12400F'), gpu=p('RTX 4060'), ram=p('Vengeance LPX 16GB DDR4'),
                  placa=p('MAG B660M Mortar WiFi DDR4'), fuente=p('RM750e 750W'), enfriador=p('AK400'),
                  gabinete=p('MasterBox Q300L'))
    verificaciones = verificar_configuracion(**piezas)
    assert {v['par'] for v in verificaciones} == {'cpu_placa', 'ram_placa', 'cpu_ram', 'fuente', 'enfriador_cpu',
                                                   'gabinete_placa', 'gabinete_gpu', 'gabinete_enfriador'}
    assert all(v['estado'] == OK for v in verificaciones), verificaciones
    assert estado_general(verificaciones) == OK


def test_el_estado_general_toma_lo_peor():
    ok = {'estado': OK}
    assert estado_general([ok, {'estado': JUSTA}]) == JUSTA
    assert estado_general([ok, {'estado': JUSTA}, {'estado': INCOMPATIBLE}]) == INCOMPATIBLE
    assert estado_general([ok, {'estado': SIN_DATOS}]) == OK
    assert estado_general([{'estado': SIN_DATOS}]) == SIN_DATOS
    assert estado_general([]) == SIN_DATOS


def test_sin_pares_no_hay_verificaciones():
    assert verificar_configuracion(cpu=p('Core i5-12400F')) == []
    assert verificar_configuracion() == []


def test_cada_verificacion_indica_los_tipos_que_involucra():
    v = verificar_configuracion(cpu=p('Core i5-12400F'), placa=p('ROG Strix B450-F Gaming'))[0]
    assert v['piezas'] == ['CPU', 'Motherboard']


def test_los_campos_de_la_api_cubren_los_siete_tipos():
    assert set(CAMPOS_POR_TIPO) == {'CPU', 'GPU', 'RAM', 'Motherboard', 'Fuente de poder', 'Refrigeración', 'Gabinete'}


# --------------------------------------------------------------------------- la API
@pytest.fixture
def ids(app_context):
    sincronizar_hardware()
    return {h.modelo: h.id for h in Hardware.query.all()}


def _post(client, **cuerpo):
    return client.post('/api/verificar-configuracion', json=cuerpo)


def test_la_api_devuelve_verificaciones_estado_y_rendimiento(client, ids):
    r = _post(client, cpu_id=ids['Core i5-12400F'], gpu_id=ids['RTX 4060'], ram_id=ids['Vengeance LPX 16GB DDR4'],
              placa_id=ids['MAG B660M Mortar WiFi DDR4'], fuente_id=ids['RM750e 750W'])
    assert r.status_code == 200
    datos = r.get_json()
    assert datos['success'] is True and datos['estado'] == OK
    assert {v['par'] for v in datos['verificaciones']} == {'cpu_placa', 'ram_placa', 'cpu_ram', 'fuente'}
    assert datos['rendimiento']['nivel'] == 'Mid-High (1080p Ultra)' and datos['rendimiento']['total'] == 9390


def test_la_api_detecta_una_configuracion_incompatible(client, ids):
    r = _post(client, cpu_id=ids['Core i5-12400F'], placa_id=ids['ROG Strix B450-F Gaming']).get_json()
    assert r['estado'] == INCOMPATIBLE and r['verificaciones'][0]['par'] == 'cpu_placa'


def test_el_rendimiento_coincide_con_el_del_analizador(client, ids):
    """Un solo motor: el nivel del configurador es el mismo que el del analizador para el mismo equipo."""
    cpu, gpu, ram = ids['Ryzen 5 7600X'], ids['RTX 4070'], ids['Vengeance 32GB DDR5']
    a = client.post('/api/analizar-hardware', json={'cpu_id': cpu, 'gpu_id': gpu, 'ram_id': ram}).get_json()
    c = _post(client, cpu_id=cpu, gpu_id=gpu, ram_id=ram).get_json()
    assert c['rendimiento']['total'] == a['system_score']['total']
    assert c['rendimiento']['nivel'] == a['system_score']['tier']
    assert c['cuello']['has_bottleneck'] == a['bottlenecks']['has_bottleneck']


def test_la_api_sin_cpu_y_gpu_no_inventa_rendimiento(client, ids):
    datos = _post(client, placa_id=ids['MAG B650 Tomahawk WiFi']).get_json()
    assert datos['rendimiento']['total'] is None and datos['rendimiento']['nivel'] == 'Sin datos suficientes'
    assert datos['verificaciones'] == [] and datos['estado'] == SIN_DATOS


def test_la_api_rechaza_ids_de_otro_tipo_o_inexistentes(client, ids):
    assert _post(client, cpu_id=ids['RTX 4060']).status_code == 400          # una GPU en el campo de CPU
    assert _post(client, cpu_id=999999).status_code == 404
    assert _post(client).status_code == 400                                   # nada que verificar
    assert client.post('/api/verificar-configuracion', data='no es json', content_type='text/plain').status_code in (400, 415)


def test_la_api_no_revela_detalles_internos_si_falla(client, ids, monkeypatch):
    import controllers.hardware as hw

    def falla(**_):
        raise RuntimeError('detalle interno secreto')
    monkeypatch.setattr(hw, 'verificar_configuracion', falla)
    r = _post(client, cpu_id=ids['Core i5-12400F'])
    assert r.status_code == 500 and 'secreto' not in r.get_data(as_text=True)
