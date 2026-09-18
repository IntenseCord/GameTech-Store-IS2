"""
Tests de la API GraphQL del catálogo (controllers/graphql_api.py).

Cubren: solo se devuelven los campos pedidos, filtros, consulta por id, varias
colecciones en una sola petición, tope de tamaño de las listas, y que la API
es pública pero de solo lectura y sin datos de usuarios/órdenes.

Regresiones que se vigilan a propósito (ya nos pasaron en este proyecto):
- Decimal serializado como texto en JSON: `precio` debe llegar como número.
- `LIMIT` negativo: en SQLite devuelve todas las filas, no ninguna.
- Consultas repetidas por elemento (N+1): una lista debe costar 1 sentencia SQL
  sin importar cuántos elementos tenga.
"""
from sqlalchemy import event

from extensions import db
from models.database_models import Game, Hardware
from controllers.graphql_api import LIMITE_MAXIMO


def crear_juegos(cantidad, genero='Acción'):
    juegos = [
        Game(nombre=f'Juego {i}', descripcion='d', precio=49.99, genero=genero,
             desarrollador='dev', stock=5)
        for i in range(cantidad)
    ]
    db.session.add_all(juegos)
    db.session.commit()
    return juegos


def crear_hardware(tipo, cantidad=1):
    lista = [
        Hardware(tipo=tipo, marca='Marca', modelo=f'{tipo} {i}', precio=199.99,
                 especificaciones='{}', stock=3)
        for i in range(cantidad)
    ]
    db.session.add_all(lista)
    db.session.commit()
    return lista


def consultar(client, consulta):
    return client.post('/graphql', json={'query': consulta})


def contar_sentencias(accion):
    sentencias = []

    def registrar(conn, cursor, statement, params, context, executemany):
        sentencias.append(statement)

    event.listen(db.engine, 'before_cursor_execute', registrar)
    try:
        accion()
    finally:
        event.remove(db.engine, 'before_cursor_execute', registrar)
    return len(sentencias)


def test_devuelve_solo_los_campos_pedidos(client):
    crear_juegos(2)

    datos = consultar(client, '{ juegos { nombre precio } }').get_json()['data']

    assert len(datos['juegos']) == 2
    for juego in datos['juegos']:
        assert set(juego.keys()) == {'nombre', 'precio'}


def test_filtra_juegos_por_genero(client):
    crear_juegos(2, genero='Acción')
    crear_juegos(1, genero='Aventura')

    datos = consultar(client, '{ juegos(genero: "Aventura") { genero } }').get_json()['data']

    assert [j['genero'] for j in datos['juegos']] == ['Aventura']


def test_juego_por_id_existente_e_inexistente(client):
    juego = crear_juegos(1)[0]

    existente = consultar(client, f'{{ juego(id: {juego.id}) {{ nombre stock }} }}').get_json()['data']
    inexistente = consultar(client, '{ juego(id: 9999) { nombre } }').get_json()['data']

    assert existente['juego'] == {'nombre': 'Juego 0', 'stock': 5}
    assert inexistente['juego'] is None


def test_hardware_por_tipo_y_componente_por_id(client):
    crear_hardware('GPU', 2)
    cpu = crear_hardware('CPU')[0]

    por_tipo = consultar(client, '{ hardware(tipo: "GPU") { tipo } }').get_json()['data']
    por_id = consultar(client, f'{{ componente(id: {cpu.id}) {{ tipo marca }} }}').get_json()['data']

    assert [c['tipo'] for c in por_tipo['hardware']] == ['GPU', 'GPU']
    assert por_id['componente'] == {'tipo': 'CPU', 'marca': 'Marca'}


def test_dos_colecciones_en_una_sola_peticion(client):
    crear_juegos(1)
    crear_hardware('RAM')

    datos = consultar(client, '{ juegos { nombre } hardware { modelo } }').get_json()['data']

    assert len(datos['juegos']) == 1
    assert len(datos['hardware']) == 1


def test_precio_llega_como_numero_no_como_texto(client):
    """Regresión: Flask serializaba Decimal como string y rompía la aritmética de JS."""
    crear_juegos(1)

    precio = consultar(client, '{ juegos { precio } }').get_json()['data']['juegos'][0]['precio']

    assert isinstance(precio, float)
    assert precio == 49.99


def test_tope_de_tamano_de_las_listas(client):
    crear_juegos(LIMITE_MAXIMO + 5)

    datos = consultar(client, '{ juegos(limite: 1000) { id } }').get_json()['data']

    assert len(datos['juegos']) == LIMITE_MAXIMO


def test_limite_negativo_no_devuelve_todas_las_filas(client):
    """Regresión: en SQLite `LIMIT -1` significa "sin límite"."""
    crear_juegos(3)

    datos = consultar(client, '{ juegos(limite: -1) { id } }').get_json()['data']

    assert datos['juegos'] == []


def test_campo_inexistente_da_error_claro(client):
    respuesta = consultar(client, '{ juegos { nombre inexistente } }').get_json()

    assert 'inexistente' in respuesta['errors'][0]['message']


def test_una_lista_cuesta_una_sentencia_sin_importar_su_tamano(client):
    """Regresión de N+1: 20 juegos con varios campos no deben generar 20 consultas."""
    crear_juegos(20)

    sentencias = contar_sentencias(
        lambda: consultar(client, '{ juegos(limite: 20) { nombre precio genero stock } }')
    )

    assert sentencias <= 2


def test_es_de_solo_lectura_no_hay_mutaciones(client):
    respuesta = consultar(client, 'mutation { borrarTodo }').get_json()

    assert 'errors' in respuesta
    assert not respuesta.get('data')


def test_no_expone_usuarios_ordenes_ni_pagos(client):
    datos = consultar(client, '{ __schema { types { name } } }').get_json()['data']
    nombres = {t['name'] for t in datos['__schema']['types']}

    assert {'Query', 'Juego', 'Componente'} <= nombres
    for prohibido in ('User', 'Order', 'OrderItem', 'Invoice', 'CartItem', 'Wishlist'):
        assert prohibido not in nombres


def test_funciona_con_csrf_activo_porque_es_de_solo_lectura(client_csrf):
    """La ruta está exenta de CSRF: sin token, un POST debe ser aceptado."""
    respuesta = client_csrf.post('/graphql', json={'query': '{ juegos { nombre } }'})

    assert respuesta.status_code == 200
    assert 'data' in respuesta.get_json()


def test_rechaza_post_que_no_es_json(client):
    """Un formulario de otro sitio no puede enviar JSON: el tipo de contenido debe rechazarse."""
    respuesta = client.post('/graphql', data='{"query": "{ juegos { nombre } }"}',
                            content_type='text/plain')

    assert respuesta.status_code == 400
