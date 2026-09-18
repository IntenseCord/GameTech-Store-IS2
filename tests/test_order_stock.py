"""
Tests de utils/order_stock.py.

Regresión de rendimiento (2026-09-18): restaurar_stock/descontar_stock hacían
un SELECT y un UPDATE por cada ítem de la orden (1 + 2 por ítem). Medido
contra Neon, cada sentencia costaba ~150 ms de viaje de red, así que una orden
de 5 ítems tardaba ~1,3 s solo en restaurar stock. Ahora el ajuste se hace con
un UPDATE por tabla (juegos y hardware), sin importar cuántos ítems tenga la
orden. Además, `stock = stock + n` se calcula dentro de la base de datos, en
vez de leer el valor, sumarlo en Python y escribirlo de vuelta.
"""
from datetime import datetime

from sqlalchemy import event

from extensions import db
from models.database_models import Game, Hardware, Order, OrderItem
from utils.order_stock import descontar_stock, restaurar_stock


def crear_hardware(stock, cantidad=1):
    lista = [
        Hardware(tipo='CPU', marca='Marca', modelo=f'Modelo {i}', precio=10,
                 especificaciones='{}', stock=stock)
        for i in range(cantidad)
    ]
    db.session.add_all(lista)
    db.session.commit()
    return lista


def crear_juegos(stock, cantidad=1):
    lista = [
        Game(nombre=f'Juego {i}', descripcion='d', precio=10, genero='Acción',
             desarrollador='dev', stock=stock)
        for i in range(cantidad)
    ]
    db.session.add_all(lista)
    db.session.commit()
    return lista


def crear_orden(usuario, items):
    """items: lista de (tipo, producto, cantidad)."""
    order = Order(user_id=usuario.id, total=1, status='pending')
    db.session.add(order)
    db.session.flush()
    for tipo, producto, cantidad in items:
        db.session.add(OrderItem(
            order_id=order.id, product_type=tipo, product_id=producto.id,
            product_name='x', quantity=cantidad, price=1
        ))
    db.session.commit()
    db.session.refresh(order)
    return order


def stock_en_bd(modelo, producto_id):
    db.session.expire_all()
    return db.session.get(modelo, producto_id).stock


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


def test_restaurar_stock_devuelve_cantidades_a_juegos_y_hardware(app_context, test_user):
    juego = crear_juegos(stock=10)[0]
    hw = crear_hardware(stock=5)[0]
    order = crear_orden(test_user, [('game', juego, 2), ('hardware', hw, 3)])

    restaurar_stock(order)
    db.session.flush()

    assert stock_en_bd(Game, juego.id) == 12
    assert stock_en_bd(Hardware, hw.id) == 8


def test_restaurar_stock_suma_lineas_repetidas_del_mismo_producto(app_context, test_user):
    hw = crear_hardware(stock=5)[0]
    order = crear_orden(test_user, [('hardware', hw, 1), ('hardware', hw, 2)])

    restaurar_stock(order)
    db.session.flush()

    assert stock_en_bd(Hardware, hw.id) == 8


def test_descontar_stock_resta_cantidades(app_context, test_user):
    juego = crear_juegos(stock=10)[0]
    hw = crear_hardware(stock=5)[0]
    order = crear_orden(test_user, [('game', juego, 2), ('hardware', hw, 3)])

    descontar_stock(order)
    db.session.flush()

    assert stock_en_bd(Game, juego.id) == 8
    assert stock_en_bd(Hardware, hw.id) == 2


def test_no_toca_productos_que_no_estan_en_la_orden(app_context, test_user):
    en_orden, ajeno = crear_hardware(stock=5, cantidad=2)
    order = crear_orden(test_user, [('hardware', en_orden, 3)])

    restaurar_stock(order)
    db.session.flush()

    assert stock_en_bd(Hardware, en_orden.id) == 8
    assert stock_en_bd(Hardware, ajeno.id) == 5


def test_no_confunde_ids_iguales_entre_juegos_y_hardware(app_context, test_user):
    """Un juego y un hardware pueden tener el mismo id numérico (cada tabla
    numera por su cuenta); el ajuste debe respetar product_type."""
    juego = crear_juegos(stock=10)[0]
    hw = crear_hardware(stock=5)[0]
    assert juego.id == hw.id
    order = crear_orden(test_user, [('hardware', hw, 3)])

    restaurar_stock(order)
    db.session.flush()

    assert stock_en_bd(Hardware, hw.id) == 8
    assert stock_en_bd(Game, juego.id) == 10


def test_ignora_productos_inexistentes_sin_fallar(app_context, test_user):
    """Un producto borrado después de la compra no debe romper el ajuste del resto."""
    hw = crear_hardware(stock=5)[0]
    fantasma = Hardware(tipo='CPU', marca='M', modelo='Fantasma', precio=1,
                        especificaciones='{}', stock=0)
    fantasma.id = 9999
    order = crear_orden(test_user, [('hardware', hw, 3), ('hardware', fantasma, 1)])

    restaurar_stock(order)
    db.session.flush()

    assert stock_en_bd(Hardware, hw.id) == 8


def test_actualiza_updated_at_como_antes(app_context, test_user):
    hw = crear_hardware(stock=5)[0]
    antes = datetime(2020, 1, 1)
    hw.updated_at = antes
    db.session.commit()
    order = crear_orden(test_user, [('hardware', hw, 1)])

    restaurar_stock(order)
    db.session.flush()

    db.session.expire_all()
    assert db.session.get(Hardware, hw.id).updated_at > antes


def test_objetos_ya_cargados_en_sesion_ven_el_stock_nuevo(app_context, test_user):
    hw = crear_hardware(stock=5)[0]
    order = crear_orden(test_user, [('hardware', hw, 3)])
    assert hw.stock == 5

    restaurar_stock(order)

    assert hw.stock == 8


def test_restaurar_stock_usa_numero_constante_de_sentencias(app_context, test_user):
    hardware = crear_hardware(stock=5, cantidad=5)
    juegos = crear_juegos(stock=5, cantidad=2)
    items = [('hardware', h, 1) for h in hardware] + [('game', j, 1) for j in juegos]
    order = crear_orden(test_user, items)

    def accion():
        restaurar_stock(order)
        db.session.flush()

    assert contar_sentencias(accion) <= 2, 'debe ser un UPDATE por tabla, no uno por ítem'


def test_descontar_stock_usa_numero_constante_de_sentencias(app_context, test_user):
    hardware = crear_hardware(stock=5, cantidad=5)
    juegos = crear_juegos(stock=5, cantidad=2)
    items = [('hardware', h, 1) for h in hardware] + [('game', j, 1) for j in juegos]
    order = crear_orden(test_user, items)

    def accion():
        descontar_stock(order)
        db.session.flush()

    assert contar_sentencias(accion) <= 2, 'debe ser un UPDATE por tabla, no uno por ítem'
