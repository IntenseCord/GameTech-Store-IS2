"""
Comportamiento real de static/js/hardware_analyzer.js (se ejecuta con Node, sin navegador).

Regresión: el commit 127ca54 quitó el flag `g` de las expresiones de formatMarkdown(); String.replaceAll
con una RegExp sin `g` lanza TypeError, así que en cuanto el análisis detectaba un cuello de botella
displayBottlenecks() abortaba y la pantalla no pintaba ningún resultado (el servidor respondía 200).
"""
import json
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
JS = RAIZ / 'static' / 'js'
ANALIZADOR = JS / 'hardware_analyzer.js'

necesita_node = pytest.mark.skipif(shutil.which('node') is None, reason='Node.js no está instalado')

GUION_NODE = textwrap.dedent(r"""
    const fs = require('fs');
    const vm = require('vm');
    const [rutaJs, casosJson] = process.argv.slice(1);
    const casos = JSON.parse(casosJson);

    const contenedor = { innerHTML: '', classList: { add() {}, remove() {} } };
    const documento = {
      getElementById: () => contenedor,
      addEventListener: () => {},
      createElement: () => ({
        _t: '',
        set textContent(v) { this._t = String(v); },
        get innerHTML() { return this._t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); },
      }),
    };
    const contexto = vm.createContext({ document: documento, console, window: {} });
    vm.runInContext(fs.readFileSync(rutaJs, 'utf8'), contexto);

    const salida = casos.map((caso) => {
      contenedor.innerHTML = '';
      try {
        vm.runInContext(caso.fn + '(' + JSON.stringify(caso.arg) + ')', contexto);
        return { error: null, html: contenedor.innerHTML };
      } catch (e) {
        return { error: String(e), html: contenedor.innerHTML };
      }
    });
    process.stdout.write(JSON.stringify(salida));
""")


def _renderizar(*casos, fn='displayBottlenecks'):
    pedidos = [{'fn': fn, 'arg': caso} for caso in casos]
    resultado = subprocess.run(
        ['node', '-e', GUION_NODE, str(ANALIZADOR), json.dumps(pedidos)],
        capture_output=True, text=True, encoding='utf-8', timeout=30,
    )
    assert resultado.returncode == 0, resultado.stderr
    return json.loads(resultado.stdout)


def _con_cuello(**extra):
    base = {'has_bottleneck': True, 'type': 'gpu', 'severity': 'moderate', 'percentage_loss': 13,
            'description': 'Tu CPU es ligeramente más potente...', 'recommendations': []}
    base.update(extra)
    return base


@necesita_node
def test_con_cuello_de_botella_se_pinta_sin_lanzar_error():
    [r] = _renderizar(_con_cuello())
    assert r['error'] is None, r['error']
    assert 'Tu CPU es ligeramente más potente' in r['html']
    assert '-13% rendimiento' in r['html']


@necesita_node
def test_descripcion_con_markdown_se_convierte_a_html():
    [r] = _renderizar(_con_cuello(description='Línea **importante**\n\nSegundo párrafo\ncon salto'))
    assert r['error'] is None, r['error']
    assert '<strong>importante</strong>' in r['html']
    assert '</p><p>' in r['html']
    assert '<br>' in r['html']
    assert '**' not in r['html']


@necesita_node
def test_caso_balanceado_no_muestra_markdown_crudo_ni_titulo_duplicado():
    descripcion = '✅ **¡Sistema Balanceado!**\n\nTu configuración está bien equilibrada.'
    [r] = _renderizar({'has_bottleneck': False, 'type': 'balanced', 'severity': 'none',
                       'percentage_loss': 0, 'description': descripcion, 'recommendations': []})
    assert r['error'] is None, r['error']
    assert '**' not in r['html']
    assert '<strong>¡Sistema Balanceado!</strong>' in r['html']
    assert r['html'].count('¡Sistema Balanceado!') == 1


@necesita_node
def test_sin_datos_de_benchmark_no_afirma_que_el_sistema_esta_balanceado():
    """El detector devuelve has_bottleneck=False con este texto cuando no hay scores:
    la pantalla no debe titularlo "¡Sistema Balanceado!"."""
    [r] = _renderizar({'has_bottleneck': False, 'type': 'balanced', 'severity': 'none', 'percentage_loss': 0,
                       'description': 'No hay datos de benchmark suficientes para analizar.',
                       'recommendations': []})
    assert r['error'] is None, r['error']
    assert 'No hay datos de benchmark suficientes' in r['html']
    assert 'Sistema Balanceado' not in r['html']


@necesita_node
def test_la_descripcion_del_servidor_se_escapa_antes_de_insertarla():
    malicioso = '<img src=x onerror=alert(1)>'
    sano, balanceado = _renderizar(
        _con_cuello(description=malicioso),
        {'has_bottleneck': False, 'type': 'balanced', 'severity': 'none', 'percentage_loss': 0,
         'description': malicioso, 'recommendations': []},
    )
    for r in (sano, balanceado):
        assert r['error'] is None, r['error']
        assert '<img' not in r['html']
        assert '&lt;img' in r['html']


@necesita_node
def test_las_recomendaciones_se_escapan():
    [r] = _renderizar(_con_cuello(recommendations=['<script>alert(1)</script>']))
    assert r['error'] is None, r['error']
    assert '<script>' not in r['html']


@necesita_node
def test_las_recomendaciones_generales_se_escapan():
    [r] = _renderizar(['<img src=x onerror=alert(1)>', 'Sube la RAM a 16GB'], fn='displayRecommendations')
    assert r['error'] is None, r['error']
    assert '<img' not in r['html']
    assert '&lt;img' in r['html']
    assert 'Sube la RAM a 16GB' in r['html']


def test_ningun_replaceall_con_regex_sin_flag_g():
    """Guardia estático: replaceAll con una RegExp sin `g` siempre lanza TypeError."""
    patron = re.compile(r'\.replaceAll\(\s*/((?:\\.|[^/\\\n])+)/([a-z]*)')
    ofensores = []
    for archivo in JS.rglob('*.js'):
        for numero, linea in enumerate(archivo.read_text(encoding='utf-8', errors='ignore').splitlines(), 1):
            for m in patron.finditer(linea):
                if 'g' not in m.group(2):
                    ofensores.append(f'{archivo.relative_to(RAIZ)}:{numero}: {linea.strip()}')
    assert not ofensores, 'replaceAll con RegExp sin flag g:\n' + '\n'.join(ofensores)
