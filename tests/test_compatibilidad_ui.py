"""
Interfaz de compatibilidad: static/js/compatibilidad.js (compartido), static/js/pc_builder.js y las páginas que los usan.

Regresiones:
  - hallazgo 45: la ficha de hardware lanzaba TypeError (buscaba por id botones que solo tenían clase) y su
    "verificación de compatibilidad" era un setTimeout que casi siempre respondía "compatible".
  - el Configurador de PC calculaba en JavaScript el nivel de rendimiento (50/35/15) y el desbalance CPU/GPU (ratio > 2) con una
    copia de las fórmulas del motor; ahora todo viene de /api/verificar-configuracion.
"""
import json
import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

from database import sincronizar_hardware
from models.database_models import Hardware

RAIZ = Path(__file__).resolve().parent.parent
JS = RAIZ / 'static' / 'js'
necesita_node = pytest.mark.skipif(shutil.which('node') is None, reason='Node.js no está instalado')

SLOTS = [{'tipo': 'CPU', 'campo': 'cpu_id', 'etiqueta': 'Procesador'},
         {'tipo': 'Motherboard', 'campo': 'placa_id', 'etiqueta': 'Placa Base'},
         {'tipo': 'Fuente de poder', 'campo': 'fuente_id', 'etiqueta': 'Fuente de Poder'}]

GUION_NODE = textwrap.dedent(r"""
    const fs = require('fs');
    const vm = require('vm');
    const [rutas, casosJson] = process.argv.slice(1);
    const casos = JSON.parse(casosJson);
    const elemento = () => ({ innerHTML: '', textContent: '', value: '', disabled: false, style: {}, classList: { add() {}, remove() {} },
                              addEventListener() {}, setAttribute() {} });
    const documento = {
      getElementById: () => elemento(), querySelector: () => null, querySelectorAll: () => [], addEventListener: () => {},
      createElement: () => ({
        _t: '',
        set textContent(v) { this._t = String(v); },
        get innerHTML() { return this._t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); },
      }),
    };
    const contexto = vm.createContext({ document: documento, console, window: { PC_SLOTS: JSON.parse(process.env.PC_SLOTS || '[]') } });
    for (const ruta of rutas.split(';')) vm.runInContext(fs.readFileSync(ruta, 'utf8'), contexto);
    const salida = casos.map((caso) => {
      try {
        return { error: null, valor: vm.runInContext(caso.expr, contexto) };
      } catch (e) {
        return { error: String(e) };
      }
    });
    process.stdout.write(JSON.stringify(salida));
""")


def _js(*expresiones, archivos=('compatibilidad.js',)):
    rutas = ';'.join(str(JS / a) for a in archivos)
    r = subprocess.run(['node', '-e', GUION_NODE, rutas, json.dumps([{'expr': e} for e in expresiones])],
                       capture_output=True, text=True, encoding='utf-8', timeout=30,
                       env={**os.environ, 'PC_SLOTS': json.dumps(SLOTS)})
    assert r.returncode == 0, r.stderr
    salida = json.loads(r.stdout)
    for s in salida:
        assert s['error'] is None, s['error']
    return [s['valor'] for s in salida]


def _v(par='cpu_placa', estado='ok', mensaje='msg', piezas=('CPU', 'Motherboard')):
    return {'par': par, 'estado': estado, 'mensaje': mensaje, 'piezas': list(piezas)}


# ---------------------------------------------------------------- compatibilidad.js
@necesita_node
def test_cada_estado_se_pinta_con_su_etiqueta():
    [html] = _js('htmlVerificaciones(%s)' % json.dumps([
        _v('a', 'ok'), _v('b', 'justa'), _v('c', 'incompatible'), _v('d', 'sin_datos')]))
    for etiqueta in ('Compatible', 'Justa', 'Incompatible', 'Sin datos'):
        assert etiqueta in html
    assert 'badge bg-danger' in html and 'badge bg-warning' in html and 'badge bg-success' in html


@necesita_node
def test_el_mensaje_del_servidor_se_escapa():
    [html] = _js('htmlVerificaciones(%s)' % json.dumps([_v(mensaje='<img src=x onerror=alert(1)> MSI "B650"')]))
    assert '<img' not in html and '&lt;img' in html


@necesita_node
def test_se_puede_filtrar_por_tipo_de_pieza():
    lista = json.dumps([_v('cpu_placa', piezas=('CPU', 'Motherboard'), mensaje='uno'),
                        _v('gabinete_gpu', piezas=('Gabinete', 'GPU'), mensaje='dos')])
    [con_cpu, con_gabinete, todas] = _js(f"htmlVerificaciones({lista}, 'CPU')", f"htmlVerificaciones({lista}, 'Gabinete')",
                                         f'htmlVerificaciones({lista})')
    assert 'uno' in con_cpu and 'dos' not in con_cpu
    assert 'dos' in con_gabinete and 'uno' not in con_gabinete
    assert 'uno' in todas and 'dos' in todas


@necesita_node
def test_sin_verificaciones_se_explica_que_faltan_piezas():
    [html] = _js('htmlVerificaciones([])')
    assert 'al menos dos' in html


@necesita_node
def test_el_resumen_nombra_el_estado_general():
    [ok, mal, nada] = _js("htmlResumen('ok')", "htmlResumen('incompatible')", "htmlResumen('sin_datos')")
    assert 'Compatible' in ok and 'alert-success' in ok
    assert 'Incompatible' in mal and 'alert-danger' in mal
    assert 'alert-secondary' in nada


@necesita_node
def test_el_cuerpo_de_la_peticion_usa_los_campos_de_la_api():
    [cuerpo] = _js("cuerpoDeConfiguracion({CPU: {id: 3}, Motherboard: {id: 8}, 'Fuente de poder': null}, window.PC_SLOTS)")
    assert cuerpo == {'cpu_id': 3, 'placa_id': 8}


# -------------------------------------------------------------------- pc_builder.js
@necesita_node
def test_el_precio_total_suma_solo_lo_elegido():
    [total, vacio] = _js("precioTotal({CPU: {precio: 199.99}, GPU: null, RAM: {precio: 89.99}})", 'precioTotal({})',
                         archivos=('compatibilidad.js', 'pc_builder.js'))
    assert round(total, 2) == 289.98 and vacio == 0


@necesita_node
def test_el_cuello_de_botella_y_las_recomendaciones_del_servidor_se_escapan():
    cuello = json.dumps({'has_bottleneck': True, 'description': '**Cuello** <b>GPU</b>\n\nSegunda línea'})
    [html, vacio, sin_cuello, recs] = _js(
        f'htmlCuello({cuello})', 'htmlCuello({has_bottleneck: false})', 'htmlCuello(null)',
        'htmlRecomendaciones(["💡 usa <script>x</script>"])', archivos=('compatibilidad.js', 'pc_builder.js'))
    assert '<b>' not in html and '&lt;b&gt;GPU' in html and '**' not in html and '<br>' in html
    assert vacio == '' and sin_cuello == ''
    assert '<script>' not in recs and '&lt;script&gt;' in recs


@necesita_node
def test_el_nivel_sale_de_la_respuesta_del_servidor():
    [con, sin] = _js("textoNivel({nivel: 'High-End (1440p Ultra)', total: 12633})", 'textoNivel(null)',
                     archivos=('compatibilidad.js', 'pc_builder.js'))
    assert con == 'High-End (1440p Ultra)' and sin == 'Sin componentes'


@necesita_node
def test_el_configurador_ya_no_calcula_rendimiento_ni_desbalance_por_su_cuenta():
    codigo = (JS / 'pc_builder.js').read_text(encoding='utf-8')
    for copia in ('0.35', '0.15', 'Ultra High-End', 'ratio >', 'updatePerformanceLevel', 'recommendGPU', 'autoRecommend'):
        assert copia not in codigo, copia


# ------------------------------------------------------------------------ las páginas
def test_el_configurador_tiene_los_siete_espacios_y_ya_no_el_autorecomendador(client, app_context):
    sincronizar_hardware()
    html = client.get('/configurador-pc').get_data(as_text=True)
    for campo in ('cpu_id', 'gpu_id', 'ram_id', 'placa_id', 'fuente_id', 'enfriador_id', 'gabinete_id'):
        assert f'id="slot-{campo}"' in html, campo
    for etiqueta in ('Procesador', 'Tarjeta Gráfica', 'Memoria RAM', 'Placa Base', 'Fuente de Poder', 'Refrigeración', 'Gabinete'):
        assert etiqueta in html, etiqueta
    assert 'auto-recommend-btn' not in html and 'budget-select' not in html
    assert 'js/compatibilidad.js' in html and 'js/pc_builder.js' in html


def test_la_ficha_ofrece_las_piezas_del_catalogo_en_vez_de_texto_libre(client, app_context):
    sincronizar_hardware()
    gpu = Hardware.query.filter_by(modelo='RTX 4070').one()
    html = client.get(f'/hardware/{gpu.id}').get_data(as_text=True)
    assert 'id="current-cpu"' not in html and 'Simular' not in html
    assert "getElementById('add-to-cart-btn')" not in html           # hallazgo 45: el id no existe
    for modelo in ('Core i7-13700K', 'MAG Z790 Tomahawk WiFi', 'RM850e 850W', '5000D Airflow'):
        assert modelo in html, modelo
    assert 'js/compatibilidad.js' in html and 'gpu_id' in html


def test_la_ficha_no_ofrece_piezas_del_mismo_tipo(client, app_context):
    sincronizar_hardware()
    gpu = Hardware.query.filter_by(modelo='RTX 4070').one()
    html = client.get(f'/hardware/{gpu.id}').get_data(as_text=True)
    assert 'id="otro-gpu_id"' not in html and 'id="otro-cpu_id"' in html


def test_la_ficha_le_pasa_a_su_script_el_tipo_y_el_campo_de_su_componente(client, app_context):
    sincronizar_hardware()
    for modelo, tipo, campo in (('RTX 4070', 'GPU', 'gpu_id'), ('5000D Airflow', 'Gabinete', 'gabinete_id'),
                                ('Core i7-13700K', 'CPU', 'cpu_id')):
        pieza = Hardware.query.filter_by(modelo=modelo).one()
        html = client.get(f'/hardware/{pieza.id}').get_data(as_text=True)
        assert f'const TIPO = "{tipo}"' in html and f'const CAMPO = "{campo}"' in html, modelo
        assert f'[CAMPO]: {pieza.id}' in html, modelo


def test_un_componente_sin_verificacion_no_muestra_un_boton_que_no_funciona(client, app_context):
    """Los tipos de la administración fuera de los 7 (Almacenamiento, Otro) no tienen evaluadores."""
    extra = Hardware(tipo='Almacenamiento', marca='WD', modelo='SSD 1TB', precio=60, especificaciones='{"capacidad": "1 TB"}', stock=3)
    from extensions import db
    db.session.add(extra)
    db.session.commit()
    html = client.get(f'/hardware/{extra.id}').get_data(as_text=True)
    assert 'check-compatibility-btn' not in html and 'todavía no tiene verificación' in html
