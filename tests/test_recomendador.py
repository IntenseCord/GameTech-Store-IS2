"""
Recomendador de mejoras (utils/recomendador.py) y su integración en el analizador (/api/analizar-hardware -> `upgrades`).

Antes el analizador decía "💡 Un GPU con puntuación de ~6247 o más equilibraría tu sistema" sin nombrar ninguna pieza. Ahora
propone piezas REALES del catálogo, ordenadas por mejor relación precio/rendimiento (puntaje por dólar).

Reglas:
  - Solo se recomienda lo que hace falta: un equipo equilibrado, con RAM suficiente y sin límite de VRAM no recibe nada.
  - Si hay cuello de botella, se mejora el componente débil con piezas que dejan el equipo SIN cuello de botella (se comprueba
    simulando el reemplazo con el motor); si ninguna lo logra, se muestran las que mejoran y se avisa.
  - Si un juego queda limitado por la VRAM, se proponen GPU con la VRAM que pide ese juego.
  - Solo piezas con stock, nunca la misma que ya tienes ni peores, máximo 3 por recomendación.
  - Cada opción avisa de lo que obliga a cambiar (placa por otro socket, otro tipo de memoria, fuente, largo de la GPU).
"""
import pytest

from database import agregar_juegos_faltantes, hardware_inicial, sincronizar_hardware
from models.database_models import Hardware
from scripts.populate_game_requirements import populate_game_requirements
from utils.hardware_engine import Sistema, evaluar_juego
from utils.recomendador import recomendar_mejoras

_CATALOGO = {h.modelo: h for h in hardware_inicial()}


def pieza(modelo, stock=None, benchmark_score=None, **specs):
    """Copia de una pieza del catálogo (sin tocar el original) con campos reemplazados."""
    import json
    base = _CATALOGO[modelo]
    copia = Hardware(tipo=base.tipo, marca=base.marca, modelo=base.modelo, precio=base.precio, socket=base.socket,
                     tdp_watts=base.tdp_watts, vram_gb=base.vram_gb, benchmark_score=base.benchmark_score,
                     stock=base.stock if stock is None else stock, especificaciones=base.especificaciones)
    if benchmark_score is not None:
        copia.benchmark_score = benchmark_score
    if specs:
        datos = json.loads(copia.especificaciones)
        datos.update(specs)
        copia.especificaciones = json.dumps(datos)
    return copia


def catalogo(**sin_stock):
    return [pieza(h.modelo, stock=0 if h.modelo in sin_stock else None) for h in hardware_inicial()]


def mejoras(cpu, gpu, ram, piezas=None, vram=None, maximo=3):
    return recomendar_mejoras(pieza(cpu), pieza(gpu), pieza(ram) if isinstance(ram, str) else ram,
                              piezas if piezas is not None else catalogo(), vram_necesaria=vram, maximo=maximo)


def modelos(entrada):
    return [o['pieza'].modelo for o in entrada['opciones']]


def entrada_de(recomendaciones, tipo):
    return next(r for r in recomendaciones if r['tipo'] == tipo)


# ------------------------------------------------------------------ cuándo no recomendar
def test_un_equipo_equilibrado_no_recibe_recomendaciones():
    assert mejoras('Core i5-12400F', 'RTX 4060', 'Vengeance LPX 16GB DDR4') == []


def test_sin_datos_de_benchmark_no_se_inventa_nada():
    sin_puntaje = pieza('RTX 4060', benchmark_score=0)
    assert recomendar_mejoras(pieza('Core i5-12400F'), sin_puntaje, pieza('Vengeance LPX 16GB DDR4'), catalogo()) == []


# ------------------------------------------------------------------ GPU limitante
def test_gpu_limitante_se_mejora_con_piezas_que_equilibran_ordenadas_por_precio_rendimiento():
    r = mejoras('Ryzen 5 5600', 'GTX 1650', 'Vengeance LPX 16GB DDR4')
    gpu = entrada_de(r, 'GPU')
    assert modelos(gpu) == ['RX 7600', 'RTX 4060']                 # la RTX 4070 dejaría a la CPU como cuello de botella
    assert all(o['equilibra'] for o in gpu['opciones'])
    assert [o['mejor_relacion'] for o in gpu['opciones']] == [True, False]


def test_el_criterio_de_orden_es_puntaje_por_dolar():
    gpu = entrada_de(mejoras('Ryzen 5 5600', 'GTX 1650', 'Vengeance LPX 16GB DDR4'), 'GPU')
    for o in gpu['opciones']:
        assert o['puntos_por_dolar'] == round(o['puntaje'] / float(o['precio']), 2)
    valores = [o['puntos_por_dolar'] for o in gpu['opciones']]
    assert valores == sorted(valores, reverse=True)


def test_cada_opcion_dice_cuanto_mejora_respecto_de_lo_que_tienes():
    gpu = entrada_de(mejoras('Ryzen 5 5600', 'GTX 1650', 'Vengeance LPX 16GB DDR4'), 'GPU')
    rx = next(o for o in gpu['opciones'] if o['pieza'].modelo == 'RX 7600')
    assert rx['mejora_pct'] == (11400 - 4840) * 100 // 4840 == 135


def test_las_gpu_avisan_de_la_fuente_y_del_largo():
    gpu = entrada_de(mejoras('Ryzen 5 5600', 'GTX 1650', 'Vengeance LPX 16GB DDR4'), 'GPU')
    avisos = ' '.join(gpu['opciones'][0]['avisos'])
    assert 'fuente' in avisos and '550' in avisos               # la RX 7600 recomienda 550 W
    assert 'mm' in avisos                                        # largo para el gabinete


def test_no_recomienda_la_pieza_que_ya_tienes_ni_peores():
    gpu = entrada_de(mejoras('Ryzen 5 5600', 'GTX 1650', 'Vengeance LPX 16GB DDR4'), 'GPU')
    assert 'GTX 1650' not in modelos(gpu)
    # con una RX 7600 el equipo ya no tiene cuello: no hay nada que recomendar
    assert mejoras('Ryzen 5 5600', 'RX 7600', 'Vengeance LPX 16GB DDR4') == []


def test_una_pieza_sin_stock_no_se_recomienda():
    gpu = entrada_de(mejoras('Ryzen 5 5600', 'GTX 1650', 'Vengeance LPX 16GB DDR4', piezas=catalogo(**{'RX 7600': 0})), 'GPU')
    assert modelos(gpu) == ['RTX 4060']


def test_se_puede_limitar_la_cantidad_de_opciones():
    gpu = entrada_de(mejoras('Core i7-13700K', 'GTX 1650', 'Vengeance LPX 16GB DDR4'), 'GPU')
    assert len(gpu['opciones']) == 3
    uno = entrada_de(mejoras('Core i7-13700K', 'GTX 1650', 'Vengeance LPX 16GB DDR4', maximo=1), 'GPU')
    assert len(uno['opciones']) == 1


# ------------------------------------------------------------------ CPU limitante
def test_cpu_limitante_misma_plataforma():
    cpu = entrada_de(mejoras('Core i5-12400F', 'RTX 4070', 'Vengeance LPX 16GB DDR4'), 'CPU')
    assert modelos(cpu) == ['Core i7-13700K']                     # el Ryzen 5 7600X mejora pero no elimina el cuello
    assert not any('placa' in a for a in cpu['opciones'][0]['avisos'])      # mismo socket LGA1700 y acepta DDR4


def test_una_cpu_de_otro_socket_avisa_que_hay_que_cambiar_la_placa():
    cpu = entrada_de(mejoras('Ryzen 5 5600', 'RTX 4070', 'Vengeance LPX 16GB DDR4'), 'CPU')
    assert modelos(cpu) == ['Core i7-13700K']
    avisos = ' '.join(cpu['opciones'][0]['avisos'])
    assert 'placa base' in avisos and 'AM4' in avisos and 'LGA1700' in avisos


def test_una_cpu_que_solo_acepta_ddr5_avisa_de_la_memoria():
    potente = pieza('Ryzen 5 7600X', benchmark_score=11500)
    piezas = [p for p in catalogo() if p.modelo != 'Ryzen 5 7600X'] + [potente]
    cpu = entrada_de(mejoras('Ryzen 5 5600', 'RTX 4070', 'Vengeance LPX 16GB DDR4', piezas=piezas), 'CPU')
    primera = cpu['opciones'][0]
    assert primera['pieza'].modelo == 'Ryzen 5 7600X'               # 11500 por $299.99 supera la relación del i7-13700K
    avisos = ' '.join(primera['avisos'])
    assert 'DDR5' in avisos and 'DDR4' in avisos and 'placa base' in avisos


def test_si_ninguna_pieza_equilibra_se_muestran_las_que_mejoran_y_se_avisa():
    sin_13700k = catalogo(**{'Core i7-13700K': 0})
    cpu = entrada_de(mejoras('Core i5-12400F', 'RTX 4070', 'Vengeance LPX 16GB DDR4', piezas=sin_13700k), 'CPU')
    assert modelos(cpu) == ['Ryzen 5 7600X'] and cpu['opciones'][0]['equilibra'] is False
    assert any('no elimina' in a for a in cpu['opciones'][0]['avisos'])


# ------------------------------------------------------------------ RAM
def test_poca_ram_recibe_opciones_de_memoria_por_gigabyte_por_dolar():
    poca = pieza('Vengeance LPX 16GB DDR4', capacidad='8 GB')
    ram = entrada_de(mejoras('Core i5-12400F', 'RTX 4060', poca), 'RAM')
    assert modelos(ram) == ['Trident Z RGB 32GB DDR4', 'Vengeance LPX 16GB DDR4', 'Vengeance 32GB DDR5']
    assert ram['opciones'][0]['puntos_por_dolar'] == round(3200 / 159.99, 2)
    assert 'DDR4' in ' '.join(ram['opciones'][0]['avisos']) and 'placa' in ' '.join(ram['opciones'][0]['avisos'])


def test_la_ram_de_16_gb_no_se_recomienda_cambiar():
    assert not [r for r in mejoras('Core i5-12400F', 'RTX 4060', 'Vengeance LPX 16GB DDR4') if r['tipo'] == 'RAM']


# ------------------------------------------------------------------ VRAM
def test_un_juego_limitado_por_vram_recomienda_gpu_con_esa_vram():
    r = mejoras('Core i5-12400F', 'RTX 4060', 'Vengeance LPX 16GB DDR4', vram=11)
    gpu = entrada_de(r, 'GPU')
    assert modelos(gpu) == ['RTX 4070'] and '11' in gpu['motivo'] and 'VRAM' in gpu['motivo']
    o = gpu['opciones'][0]
    assert o['equilibra'] is False and any('cuello de botella' in a for a in o['avisos'])   # la CPU quedaría corta


def test_la_vram_y_el_cuello_de_botella_se_combinan_en_una_sola_recomendacion_de_gpu():
    r = mejoras('Ryzen 5 5600', 'GTX 1650', 'Vengeance LPX 16GB DDR4', vram=8)
    assert [x['tipo'] for x in r].count('GPU') == 1
    gpu = entrada_de(r, 'GPU')
    assert modelos(gpu) == ['RX 7600', 'RTX 4060']
    assert 'VRAM' in gpu['motivo'] and 'cuello' in gpu['motivo']


def test_la_vram_pedida_descarta_las_gpu_que_no_la_tienen_aunque_equilibren():
    """RX 7600 y RTX 4060 equilibran con la CPU pero tienen 8 GB: si el juego pide 11 GB solo sirve la RTX 4070."""
    gpu = entrada_de(mejoras('Ryzen 5 5600', 'GTX 1650', 'Vengeance LPX 16GB DDR4', vram=11), 'GPU')
    assert modelos(gpu) == ['RTX 4070'] and gpu['opciones'][0]['equilibra'] is False


def test_se_toma_la_mayor_vram_que_piden_los_juegos_limitados():
    from controllers.hardware_analyzer import _vram_que_piden
    juegos = {'can_run_high': [{'vram_needed': 8}, {'vram_needed': None}], 'cannot_run': [{'vram_needed': 11}], 'sin_datos': []}
    assert _vram_que_piden(juegos) == 11
    assert _vram_que_piden({'can_run_ultra': [{'vram_needed': None}]}) is None


def test_sin_juegos_limitados_por_vram_no_se_menciona_la_vram():
    gpu = entrada_de(mejoras('Ryzen 5 5600', 'GTX 1650', 'Vengeance LPX 16GB DDR4'), 'GPU')
    assert 'VRAM' not in gpu['motivo']


# ------------------------------------------------------------------ el motor entrega la VRAM que falta
def test_evaluar_juego_informa_cuanta_vram_necesita_el_siguiente_nivel():
    from types import SimpleNamespace
    req = SimpleNamespace(min_cpu_score=8000, min_gpu_score=7000, min_ram_gb=8, min_vram_gb=4,
                          rec_cpu_score=12000, rec_gpu_score=14000, rec_ram_gb=12, rec_vram_gb=8,
                          ultra_cpu_score=15000, ultra_gpu_score=20000, ultra_ram_gb=20, ultra_vram_gb=12)
    limitado = evaluar_juego(Sistema(cpu=16000, gpu=21000, ram_gb=24, vram_gb=8), req)
    assert limitado['vram_necesaria'] == 12
    bajo_el_minimo = evaluar_juego(Sistema(cpu=16000, gpu=21000, ram_gb=24, vram_gb=3), req)
    assert bajo_el_minimo['vram_necesaria'] == 4
    suficiente = evaluar_juego(Sistema(cpu=16000, gpu=21000, ram_gb=24, vram_gb=12), req)
    assert suficiente['vram_necesaria'] is None
    assert evaluar_juego(Sistema(cpu=16000, gpu=21000, ram_gb=24), req)['vram_necesaria'] is None


# ------------------------------------------------------------------ API del analizador
@pytest.fixture
def base(app_context):
    sincronizar_hardware()
    agregar_juegos_faltantes()
    populate_game_requirements()
    return {h.modelo: h.id for h in Hardware.query.all()}


def _analizar(client, ids, cpu, gpu, ram):
    return client.post('/api/analizar-hardware', json={'cpu_id': ids[cpu], 'gpu_id': ids[gpu], 'ram_id': ids[ram]}).get_json()


def test_el_analizador_devuelve_las_mejoras_con_ids_y_precios_reales(client, base):
    d = _analizar(client, base, 'Ryzen 5 5600', 'GTX 1650', 'Vengeance LPX 16GB DDR4')
    gpu = next(u for u in d['upgrades'] if u['tipo'] == 'GPU')
    assert [o['modelo'] for o in gpu['opciones']] == ['RX 7600', 'RTX 4060']
    primera = gpu['opciones'][0]
    assert primera['id'] == base['RX 7600'] and primera['mejor_relacion'] is True
    assert primera['precio'] == 349.99 and primera['puntos_por_dolar'] == round(11400 / 349.99, 2)
    assert 'pieza' not in primera                                 # JSON serializable: sin objetos del modelo


def test_el_analizador_no_devuelve_mejoras_para_un_equipo_equilibrado_y_sin_limite_de_vram(client, base):
    d = _analizar(client, base, 'Core i7-13700K', 'RTX 4070', 'Vengeance 32GB DDR5')
    assert d['upgrades'] == []


def test_el_analizador_recomienda_mas_vram_cuando_un_juego_la_pide(client, base):
    """Con la RTX 4060 de 8 GB, Red Dead Redemption 2 y Baldur's Gate 3 (11 GB) quedan limitados por la VRAM."""
    d = _analizar(client, base, 'Core i5-12400F', 'RTX 4060', 'Vengeance LPX 16GB DDR4')
    gpu = next(u for u in d['upgrades'] if u['tipo'] == 'GPU')
    assert [o['modelo'] for o in gpu['opciones']] == ['RTX 4070'] and 'VRAM' in gpu['motivo']


def test_los_textos_antiguos_ya_no_son_la_unica_recomendacion(client, base):
    """Los textos genéricos se conservan, pero ahora hay además piezas concretas."""
    d = _analizar(client, base, 'Ryzen 5 5600', 'GTX 1650', 'Vengeance LPX 16GB DDR4')
    assert d['recommendations'] and d['upgrades']
