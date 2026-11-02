"""
Tarjeta de mejoras del analizador (static/js/hardware_analyzer.js: displayUpgrades), ejecutada con Node sin navegador.
Todo texto que llega del servidor (modelo, motivo, avisos) se escapa antes de entrar a innerHTML.
"""
from tests.test_analizador_js import _renderizar, necesita_node


def _opcion(**extra):
    base = {'id': 7, 'marca': 'AMD', 'modelo': 'RX 7600', 'precio': 349.99, 'puntaje': 11400, 'puntos_por_dolar': 32.57,
            'mejora_pct': 135, 'equilibra': True, 'mejor_relacion': True, 'avisos': ['Verifica tu fuente: 550 W o más.']}
    base.update(extra)
    return base


def _upgrades(*opciones, motivo='Tu GPU es el cuello de botella', tipo='GPU'):
    return [{'tipo': tipo, 'motivo': motivo, 'opciones': list(opciones)}]


def _pintar(upgrades):
    [r] = _renderizar(upgrades, fn='displayUpgrades')
    assert r['error'] is None, r['error']
    return r['html']


@necesita_node
def test_se_pinta_la_pieza_con_precio_mejora_valor_y_enlace_a_su_ficha():
    html = _pintar(_upgrades(_opcion()))
    assert 'AMD RX 7600' in html and '$349.99' in html and '+135%' in html and '32.57' in html
    assert 'href="/hardware/7"' in html and 'Tu GPU es el cuello de botella' in html
    assert 'Verifica tu fuente' in html


@necesita_node
def test_solo_la_primera_lleva_la_etiqueta_de_mejor_relacion():
    html = _pintar(_upgrades(_opcion(), _opcion(id=8, modelo='RTX 4060', mejor_relacion=False)))
    assert html.count('Mejor relación precio/rendimiento') == 1


@necesita_node
def test_con_una_sola_opcion_no_hay_nada_que_comparar_y_no_lleva_la_etiqueta_de_mejor_relacion():
    assert 'Mejor relación' not in _pintar(_upgrades(_opcion()))


@necesita_node
def test_una_opcion_que_no_equilibra_del_todo_se_marca():
    html = _pintar(_upgrades(_opcion(equilibra=False, mejor_relacion=False)))
    assert 'No equilibra del todo' in html
    assert 'No equilibra del todo' not in _pintar(_upgrades(_opcion()))


@necesita_node
def test_el_texto_del_servidor_se_escapa():
    html = _pintar(_upgrades(_opcion(modelo='<img src=x onerror=alert(1)>', avisos=['<script>x</script>']),
                             motivo='Motivo <b>peligroso</b>'))
    assert '<img' not in html and '<script>' not in html and '<b>' not in html
    assert '&lt;img' in html and '&lt;script&gt;' in html


@necesita_node
def test_sin_mejoras_se_dice_que_el_equipo_no_las_necesita():
    assert 'no necesita mejoras' in _pintar([])
