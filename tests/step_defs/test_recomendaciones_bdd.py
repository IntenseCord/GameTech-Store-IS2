"""
Step definitions BDD de las recomendaciones del analizador (tests/features/recomendaciones.feature).

Cada escenario recorre la API real del analizador con el catálogo completo: lo que el cliente ve en pantalla sale de
`upgrades` en la respuesta de /api/analizar-hardware.
"""
from pytest_bdd import given, when, then, scenario, parsers

from database import agregar_juegos_faltantes, sincronizar_hardware
from models.database_models import Hardware
from extensions import db
from scripts.populate_game_requirements import populate_game_requirements

FEATURE = '../features/recomendaciones.feature'


@scenario(FEATURE, 'Un equipo equilibrado no recibe recomendaciones')
def test_equilibrado_sin_recomendaciones():
    pass


@scenario(FEATURE, 'Una GPU limitante recibe opciones ordenadas por precio y rendimiento')
def test_gpu_limitante_ordenada():
    pass


@scenario(FEATURE, 'Una CPU de otro socket avisa que hay que cambiar la placa base')
def test_cpu_otro_socket_avisa_placa():
    pass


@scenario(FEATURE, 'Un juego limitado por la VRAM recomienda una GPU con más VRAM')
def test_vram_recomienda_gpu():
    pass


@scenario(FEATURE, 'Una pieza sin stock no se recomienda')
def test_pieza_sin_stock():
    pass


@given('el catálogo de hardware y juegos está cargado', target_fixture='contexto')
def catalogo_cargado(client, app_context):
    sincronizar_hardware()
    agregar_juegos_faltantes()
    populate_game_requirements()
    return {'client': client}


@given(parsers.parse('la pieza "{modelo}" no tiene stock'))
def pieza_sin_stock(contexto, modelo):
    Hardware.query.filter_by(modelo=modelo).one().stock = 0
    db.session.commit()


@given(parsers.parse('tengo la CPU "{cpu}", la GPU "{gpu}" y la RAM "{ram}"'))
def mi_equipo(contexto, cpu, gpu, ram):
    ids = {h.modelo: h.id for h in Hardware.query.all()}
    contexto['cuerpo'] = {'cpu_id': ids[cpu], 'gpu_id': ids[gpu], 'ram_id': ids[ram]}


@when('analizo mi equipo')
def analizar(contexto):
    respuesta = contexto['client'].post('/api/analizar-hardware', json=contexto['cuerpo'])
    assert respuesta.status_code == 200
    contexto['upgrades'] = respuesta.get_json()['upgrades']


@then('no recibo recomendaciones')
def sin_recomendaciones(contexto):
    assert contexto['upgrades'] == []


@then(parsers.parse('recibo recomendaciones para "{tipo}"'))
def recomendaciones_para(contexto, tipo):
    entrada = next((u for u in contexto['upgrades'] if u['tipo'] == tipo), None)
    assert entrada is not None, [u['tipo'] for u in contexto['upgrades']]
    contexto['entrada'] = entrada


@then(parsers.parse('la primera opción es "{modelo}"'))
def primera_opcion(contexto, modelo):
    assert contexto['entrada']['opciones'][0]['modelo'] == modelo


@then('las opciones se ordenan de mayor a menor puntaje por dólar')
def ordenadas_por_valor(contexto):
    valores = [o['puntos_por_dolar'] for o in contexto['entrada']['opciones']]
    assert len(valores) >= 2 and valores == sorted(valores, reverse=True)


@then(parsers.parse('ninguna opción es "{modelo}"'))
def ninguna_opcion(contexto, modelo):
    assert modelo not in [o['modelo'] for o in contexto['entrada']['opciones']]


@then(parsers.parse('la primera opción avisa de "{texto}"'))
def primera_avisa(contexto, texto):
    assert any(texto in aviso for aviso in contexto['entrada']['opciones'][0]['avisos'])


@then(parsers.parse('el motivo menciona "{texto}"'))
def motivo_menciona(contexto, texto):
    assert texto in contexto['entrada']['motivo']
