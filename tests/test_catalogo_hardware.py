"""
Catálogo de hardware ampliado: 7 tipos x 4 opciones (CPU, GPU, RAM, placa madre, fuente, refrigeración y gabinete).

Cada componente trae los datos que necesitará el motor de compatibilidad: socket y tipo de memoria, consumo y largo de las
GPU, vatios de las fuentes, TDP y sockets de los enfriadores, formatos y holguras de los gabinetes. Los puntajes de CPU y GPU
salen de la escala única (utils/benchmark_escala.py) y deben coincidir con los de scripts/populate_hardware_benchmarks.py.
`sincronizar_hardware` completa una base ya sembrada sin tocar precio ni stock y sin duplicar si se repite.
"""
import json

import pytest

from database import hardware_inicial, sincronizar_hardware
from extensions import db
from models.database_models import Hardware
from scripts.populate_hardware_benchmarks import BENCHMARK_DATA, update_hardware_benchmarks
from utils.benchmark_escala import puntaje_cpu, puntaje_gpu
from utils.catalogo_hardware import CATALOGO_HARDWARE, RENOMBRES, TIPOS

SOCKETS = {'AM4', 'AM5', 'LGA1700'}
MEMORIAS = {'DDR4', 'DDR5'}


def _por_tipo(tipo):
    return [i for i in CATALOGO_HARDWARE if i['tipo'] == tipo]


def _item(modelo):
    return next(i for i in CATALOGO_HARDWARE if i['modelo'] == modelo)


# ------------------------------------------------------------------ estructura
def test_siete_tipos_con_cuatro_opciones_cada_uno():
    assert set(TIPOS) == {'CPU', 'GPU', 'RAM', 'Motherboard', 'Fuente de poder', 'Refrigeración', 'Gabinete'}
    assert {t: len(_por_tipo(t)) for t in TIPOS} == {t: 4 for t in TIPOS}
    assert len(CATALOGO_HARDWARE) == 28


def test_no_hay_modelos_repetidos_y_los_datos_basicos_estan_completos():
    claves = [(i['tipo'], i['modelo']) for i in CATALOGO_HARDWARE]
    assert len(claves) == len(set(claves))
    for i in CATALOGO_HARDWARE:
        assert i['marca'] and i['descripcion'] and i['imagen'], i['modelo']
        assert i['precio'] > 0 and i['stock'] > 0, i['modelo']
        assert isinstance(i['especificaciones'], dict) and i['especificaciones'], i['modelo']


# ------------------------------------------------- CPU, placas y memoria (socket/DDR)
def test_cpu_y_placas_usan_sockets_normalizados():
    for i in _por_tipo('CPU') + _por_tipo('Motherboard'):
        assert i['columnas']['socket'] in SOCKETS, i['modelo']
        assert i['especificaciones']['socket'] == i['columnas']['socket'], i['modelo']


def test_todo_socket_de_cpu_tiene_placa_y_viceversa():
    cpus = {i['columnas']['socket'] for i in _por_tipo('CPU')}
    placas = {i['columnas']['socket'] for i in _por_tipo('Motherboard')}
    assert cpus == placas == SOCKETS


def test_las_placas_declaran_formato_y_tipo_de_memoria():
    for i in _por_tipo('Motherboard'):
        e = i['especificaciones']
        assert e['formato'] in {'ATX', 'Micro-ATX', 'Mini-ITX'} and e['tipo_memoria'] in MEMORIAS, i['modelo']


def test_las_cpu_declaran_la_memoria_que_aceptan_y_su_potencia_maxima():
    for i in _por_tipo('CPU'):
        e = i['especificaciones']
        assert e['tipos_memoria'] and set(e['tipos_memoria']) <= MEMORIAS, i['modelo']
        assert e['potencia_maxima_w'] >= i['columnas']['tdp_watts'] > 0, i['modelo']


def test_cada_cpu_tiene_una_placa_con_memoria_compatible():
    for cpu in _por_tipo('CPU'):
        validas = [p for p in _por_tipo('Motherboard') if p['columnas']['socket'] == cpu['columnas']['socket']
                   and p['especificaciones']['tipo_memoria'] in cpu['especificaciones']['tipos_memoria']]
        assert validas, cpu['modelo']


def test_hay_ram_de_cada_tipo_de_memoria_de_las_placas():
    rams = {i['especificaciones']['tipo'] for i in _por_tipo('RAM')}
    assert rams == {p['especificaciones']['tipo_memoria'] for p in _por_tipo('Motherboard')} == MEMORIAS
    assert sum(1 for i in _por_tipo('RAM') if i['especificaciones']['tipo'] == 'DDR5') == 2


# ------------------------------------------------------------------------- GPU
def test_las_gpu_declaran_consumo_largo_y_fuente_recomendada():
    for i in _por_tipo('GPU'):
        assert i['columnas']['tdp_watts'] > 0 and i['columnas']['vram_gb'] > 0, i['modelo']
        assert i['especificaciones']['largo_mm'] > 0 and i['especificaciones']['psu_recomendada_w'] >= 300, i['modelo']
        assert i['especificaciones']['psu_recomendada_w'] >= i['columnas']['tdp_watts'], i['modelo']


# --------------------------------------------------- fuentes, refrigeración, gabinetes
def test_las_fuentes_son_de_550_650_750_y_850_w():
    assert sorted(i['especificaciones']['potencia_w'] for i in _por_tipo('Fuente de poder')) == [550, 650, 750, 850]
    for i in _por_tipo('Fuente de poder'):
        assert i['especificaciones']['certificacion'].startswith('80 PLUS') and i['especificaciones']['formato'] == 'ATX'


def test_refrigeracion_dos_de_aire_y_dos_liquidas_con_sus_datos_de_ajuste():
    cool = _por_tipo('Refrigeración')
    assert sorted(i['especificaciones']['tipo'] for i in cool) == ['Aire', 'Aire', 'Líquida', 'Líquida']
    for i in cool:
        e = i['especificaciones']
        assert e['tdp_max_w'] > 0 and e['sockets'] and set(e['sockets']) <= SOCKETS, i['modelo']
        if e['tipo'] == 'Aire':
            assert e['altura_mm'] > 0, i['modelo']
        else:
            assert e['radiador_mm'] in (240, 360), i['modelo']


def test_los_enfriadores_cubren_todos_los_sockets_del_catalogo():
    cubiertos = set()
    for i in _por_tipo('Refrigeración'):
        cubiertos |= set(i['especificaciones']['sockets'])
    assert cubiertos == SOCKETS


def test_los_gabinetes_declaran_formatos_y_holguras():
    for i in _por_tipo('Gabinete'):
        e = i['especificaciones']
        assert e['formatos_placa'] and set(e['formatos_placa']) <= {'ATX', 'Micro-ATX', 'Mini-ITX'}, i['modelo']
        assert e['largo_max_gpu_mm'] > 0 and e['altura_max_cooler_mm'] > 0 and e['radiador_max_mm'] >= 0, i['modelo']


def test_toda_placa_y_toda_gpu_caben_en_algun_gabinete():
    gabinetes = [i['especificaciones'] for i in _por_tipo('Gabinete')]
    for p in _por_tipo('Motherboard'):
        assert any(p['especificaciones']['formato'] in g['formatos_placa'] for g in gabinetes), p['modelo']
    for gpu in _por_tipo('GPU'):
        assert any(gpu['especificaciones']['largo_mm'] <= g['largo_max_gpu_mm'] for g in gabinetes), gpu['modelo']


def test_hay_un_gabinete_compacto_y_uno_que_acepta_radiador_de_360():
    gabinetes = [i['especificaciones'] for i in _por_tipo('Gabinete')]
    assert any('ATX' not in g['formatos_placa'] for g in gabinetes)
    assert any(g['radiador_max_mm'] >= 360 for g in gabinetes)


# ------------------------------------------- puntajes en la escala única
def test_las_piezas_nuevas_usan_la_escala_unica():
    assert _item('Ryzen 5 5600')['columnas']['benchmark_score'] == puntaje_cpu('Ryzen 5 5600')
    assert _item('Core i7-13700K')['columnas']['benchmark_score'] == puntaje_cpu('Core i7-13700K')
    assert _item('GTX 1650')['columnas']['benchmark_score'] == puntaje_gpu('GeForce GTX 1650')
    assert _item('RTX 4070')['columnas']['benchmark_score'] == puntaje_gpu('GeForce RTX 4070')


@pytest.mark.parametrize('tipo', ['CPU', 'GPU'])
def test_el_catalogo_y_el_script_de_benchmarks_coinciden(tipo):
    """Si difieren, `update_hardware_benchmarks` pisaría los puntajes del catálogo con otros de otra escala."""
    for i in _por_tipo(tipo):
        coincidencias = [(k, v) for k, v in BENCHMARK_DATA[tipo].items() if k.lower() in i['modelo'].lower()]
        assert coincidencias, i['modelo']
        # `process_component` aplica las entradas en orden: la última coincidencia es la que queda en la base
        _, datos = coincidencias[-1]
        c = i['columnas']
        assert c['benchmark_score'] == datos['score'], i['modelo']
        assert c['tdp_watts'] == datos['tdp'], i['modelo']
        if tipo == 'GPU':
            assert c['vram_gb'] == datos['vram'], i['modelo']
        else:
            assert (c['cores'], c['threads'], c['frequency_ghz']) == (datos['cores'], datos['threads'], datos['freq']), i['modelo']


def test_el_orden_de_rendimiento_dentro_de_cpu_y_gpu():
    cpu = [_item(m)['columnas']['benchmark_score'] for m in ('Ryzen 5 5600', 'Core i5-12400F', 'Ryzen 5 7600X', 'Core i7-13700K')]
    gpu = [_item(m)['columnas']['benchmark_score'] for m in ('GTX 1650', 'RX 7600', 'RTX 4060', 'RTX 4070')]
    assert cpu == sorted(cpu) and gpu == sorted(gpu)


# ------------------------------------------------------------ objetos y base de datos
def test_hardware_inicial_crea_los_28_con_sus_columnas():
    items = hardware_inicial()
    assert len(items) == 28
    rtx = next(h for h in items if h.modelo == 'RTX 4070')
    assert (rtx.tipo, rtx.socket, rtx.vram_gb, rtx.tdp_watts) == ('GPU', None, 12, 200)
    ryzen = next(h for h in items if h.modelo == 'Ryzen 5 5600')
    assert (ryzen.socket, ryzen.cores, ryzen.benchmark_score) == ('AM4', 6, puntaje_cpu('Ryzen 5 5600'))
    assert json.loads(ryzen.especificaciones)['tipos_memoria'] == ['DDR4']


def _sembrar_catalogo_antiguo():
    """Los 8 componentes tal como estaban antes (sin datos de compatibilidad, sockets con espacio y placa sin 'DDR4')."""
    antiguos = [
        Hardware(tipo='CPU', marca='Intel', modelo='Core i5-12400F', precio=111, stock=7, socket='LGA 1700',
                 especificaciones='{"nucleos": 6, "socket": "LGA 1700", "tdp": "65W"}'),
        Hardware(tipo='CPU', marca='AMD', modelo='Ryzen 5 7600X', precio=222, stock=8,
                 especificaciones='{"nucleos": 6, "socket": "AM5", "tdp": "105W"}'),
        Hardware(tipo='GPU', marca='NVIDIA', modelo='RTX 4060', precio=333, stock=9,
                 especificaciones='{"memoria": "8 GB GDDR6", "consumo": "115W"}'),
        Hardware(tipo='GPU', marca='AMD', modelo='RX 7600', precio=344, stock=10,
                 especificaciones='{"memoria": "8 GB GDDR6", "consumo": "165W"}'),
        Hardware(tipo='RAM', marca='Corsair', modelo='Vengeance LPX 16GB DDR4', precio=55, stock=11,
                 especificaciones='{"capacidad": "16 GB", "tipo": "DDR4"}'),
        Hardware(tipo='RAM', marca='G.Skill', modelo='Trident Z RGB 32GB DDR4', precio=66, stock=12,
                 especificaciones='{"capacidad": "32 GB", "tipo": "DDR4"}'),
        Hardware(tipo='Motherboard', marca='ASUS', modelo='ROG Strix B450-F Gaming', precio=77, stock=13,
                 especificaciones='{"socket": "AM4", "formato": "ATX", "chipset": "B450"}'),
        Hardware(tipo='Motherboard', marca='MSI', modelo='MAG B660M Mortar WiFi', precio=88, stock=14, socket='LGA 1700',
                 especificaciones='{"socket": "LGA 1700", "formato": "Micro-ATX", "chipset": "B660"}'),
    ]
    db.session.add_all(antiguos)
    db.session.commit()


def test_sincronizar_en_una_base_vacia_agrega_los_28(app_context):
    r = sincronizar_hardware()
    assert len(r['agregados']) == 28 and r['actualizados'] == []
    assert Hardware.query.count() == 28


def test_sincronizar_no_duplica_ni_cambia_nada_si_se_repite(app_context):
    sincronizar_hardware()
    r = sincronizar_hardware()
    assert r == {'agregados': [], 'actualizados': []}
    assert Hardware.query.count() == 28


def test_sincronizar_completa_una_base_antigua_sin_tocar_precio_ni_stock(app_context):
    _sembrar_catalogo_antiguo()

    r = sincronizar_hardware()

    assert len(r['agregados']) == 20 and len(r['actualizados']) == 8
    assert Hardware.query.count() == 28
    cpu = Hardware.query.filter_by(modelo='Core i5-12400F').one()
    assert (float(cpu.precio), cpu.stock) == (111, 7)                       # lo editado por el admin se respeta
    assert cpu.socket == 'LGA1700' and cpu.tdp_watts == 65
    specs = json.loads(cpu.especificaciones)
    assert specs['socket'] == 'LGA1700' and specs['nucleos'] == 6           # normaliza el socket y conserva lo existente
    assert specs['tipos_memoria'] == ['DDR4', 'DDR5'] and specs['potencia_maxima_w'] == 117


def test_sincronizar_renombra_la_placa_que_en_realidad_es_la_version_ddr4(app_context):
    _sembrar_catalogo_antiguo()
    assert RENOMBRES == {'MAG B660M Mortar WiFi': 'MAG B660M Mortar WiFi DDR4'}

    sincronizar_hardware()

    assert Hardware.query.filter_by(modelo='MAG B660M Mortar WiFi').count() == 0
    placa = Hardware.query.filter_by(modelo='MAG B660M Mortar WiFi DDR4').one()
    assert json.loads(placa.especificaciones)['tipo_memoria'] == 'DDR4' and float(placa.precio) == 88
    assert placa.socket == 'LGA1700'
    assert Hardware.query.filter_by(tipo='Motherboard').count() == 4


def test_los_benchmarks_del_script_no_cambian_los_puntajes_del_catalogo(app_context):
    sincronizar_hardware()
    antes = {h.modelo: (h.benchmark_score, h.tdp_watts, h.vram_gb) for h in Hardware.query.filter(Hardware.tipo.in_(['CPU', 'GPU']))}

    update_hardware_benchmarks()
    db.session.expire_all()

    despues = {h.modelo: (h.benchmark_score, h.tdp_watts, h.vram_gb) for h in Hardware.query.filter(Hardware.tipo.in_(['CPU', 'GPU']))}
    assert antes == despues


# ------------------------------------------------------------- las páginas
def test_la_pagina_de_hardware_muestra_los_siete_tipos_y_sus_28_componentes(client, app_context):
    sincronizar_hardware()
    html = client.get('/hardware').get_data(as_text=True)
    for etiqueta in ('Procesadores', 'Tarjetas Gráficas', 'Memoria RAM', 'Placas Base', 'Fuentes de Poder', 'Refrigeración', 'Gabinetes'):
        assert etiqueta in html, etiqueta
    assert html.count('class="hardware-item"') == 28


@pytest.mark.parametrize('categoria', ['Fuente de poder', 'Refrigeración', 'Gabinete'])
def test_las_categorias_nuevas_listan_sus_cuatro_componentes(client, app_context, categoria):
    sincronizar_hardware()
    r = client.get(f'/hardware/categoria/{categoria}')
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    modelos = [i['modelo'] for i in _por_tipo(categoria)]
    assert len(modelos) == 4 and all(m in html for m in modelos)


def test_la_ficha_muestra_las_listas_y_las_etiquetas_legibles(client, app_context):
    sincronizar_hardware()
    cpu = Hardware.query.filter_by(modelo='Core i7-13700K').one()
    html = client.get(f'/hardware/{cpu.id}').get_data(as_text=True)
    assert 'DDR4, DDR5' in html and "['DDR4'" not in html           # antes se imprimía la lista de Python
    assert 'Consumo máximo (W)' in html and 'Potencia Maxima W' not in html

    gabinete = Hardware.query.filter_by(modelo='5000D Airflow').one()
    html = client.get(f'/hardware/{gabinete.id}').get_data(as_text=True)
    assert 'ATX, Micro-ATX, Mini-ITX' in html and 'Largo máximo de GPU (mm)' in html


def test_la_ficha_de_cada_componente_nuevo_carga(client, app_context):
    sincronizar_hardware()
    for h in Hardware.query.filter(Hardware.tipo.in_(['Fuente de poder', 'Refrigeración', 'Gabinete'])):
        r = client.get(f'/hardware/{h.id}')
        assert r.status_code == 200, h.modelo
        assert h.modelo in r.get_data(as_text=True)
