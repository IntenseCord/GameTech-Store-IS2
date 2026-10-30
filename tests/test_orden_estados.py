"""
Estados de una orden y su efecto en el stock (utils/order_stock.py::cambiar_estado_orden).

Regla (decisión del usuario, 2026-10-27): `rejected` y `cancelled` son estados FINALES. El stock se
reserva al crear la orden `pending`, se devuelve una sola vez al rechazarla o cancelarla, y desde ahí
la orden no vuelve a ningún otro estado: si el usuario quiere comprar de nuevo, crea otra orden.

Regresión: antes, rechazada → pendiente → aprobada dejaba la orden aprobada con el stock ya devuelto
(sobreventa), y el admin podía cancelar sin devolver stock o rechazar una orden ya cancelada.
"""
import pytest
from sqlalchemy import text

from extensions import db
from models.database_models import Hardware, Order, OrderItem
from utils.order_stock import TRANSICIONES, cambiar_estado_orden


def _orden(usuario, hardware, estado, cantidad=2):
    order = Order(user_id=usuario.id, total=1, status=estado)
    db.session.add(order)
    db.session.flush()
    db.session.add(OrderItem(order_id=order.id, product_type='hardware', product_id=hardware.id,
                             product_name='x', quantity=cantidad, price=1))
    db.session.commit()
    return order


def _stock(hardware):
    db.session.expire_all()
    return db.session.get(Hardware, hardware.id).stock


# (estado actual, estado nuevo, ¿se permite?, ¿cuánto stock se devuelve? [orden de 2 unidades])
CASOS = [
    ('pending', 'approved', True, 0),
    ('pending', 'completed', False, 0),  # 'completed' es heredado: ya no se ofrece como destino
    ('pending', 'rejected', True, 2),
    ('pending', 'cancelled', True, 2),
    ('approved', 'rejected', True, 2),
    ('approved', 'cancelled', True, 2),
    ('completed', 'cancelled', True, 2),
    ('approved', 'pending', False, 0),
    ('approved', 'approved', False, 0),
    ('rejected', 'approved', False, 0),
    ('rejected', 'pending', False, 0),
    ('rejected', 'completed', False, 0),
    ('rejected', 'cancelled', False, 0),
    ('cancelled', 'approved', False, 0),
    ('cancelled', 'rejected', False, 0),
    ('cancelled', 'pending', False, 0),
]


@pytest.mark.parametrize('actual, nuevo, permitido, devuelto', CASOS)
def test_transiciones_y_ajuste_de_stock(app_context, test_user, test_hardware, actual, nuevo, permitido, devuelto):
    stock_inicial = test_hardware.stock
    order = _orden(test_user, test_hardware, actual)

    cambio = cambiar_estado_orden(order, nuevo)
    db.session.commit()

    assert cambio is permitido
    assert order.status == (nuevo if permitido else actual)
    assert _stock(test_hardware) == stock_inicial + devuelto


def test_los_estados_finales_no_tienen_salida():
    assert TRANSICIONES['rejected'] == set()
    assert TRANSICIONES['cancelled'] == set()


def test_rechazar_y_luego_cancelar_no_devuelve_el_stock_dos_veces(app_context, test_user, test_hardware):
    stock_inicial = test_hardware.stock
    order = _orden(test_user, test_hardware, 'pending')

    cambiar_estado_orden(order, 'rejected')
    cambiar_estado_orden(order, 'cancelled')
    db.session.commit()

    assert order.status == 'rejected'
    assert _stock(test_hardware) == stock_inicial + 2


def test_dos_cambios_simultaneos_devuelven_el_stock_una_sola_vez(app_context, test_user, test_hardware):
    """Carrera: MercadoPago entrega dos veces a la vez el mismo rechazo. Las dos peticiones leen la orden
    como `pending`; la otra petición (simulada con SQL directo, sin que esta sesión se entere) ya la rechazó
    y devolvió el stock. Esta copia desactualizada no debe devolverlo por segunda vez."""
    stock_inicial = test_hardware.stock
    order = _orden(test_user, test_hardware, 'pending')
    assert order.status == 'pending'  # copia en memoria que quedará desactualizada

    db.session.execute(text('UPDATE orders SET status = :e WHERE id = :i'), {'e': 'rejected', 'i': order.id})
    db.session.execute(text('UPDATE hardware SET stock = stock + 2 WHERE id = :i'), {'i': test_hardware.id})

    cambio = cambiar_estado_orden(order, 'rejected')
    db.session.commit()

    assert cambio is False
    assert order.status == 'rejected'
    assert _stock(test_hardware) == stock_inicial + 2, 'el stock no debe devolverse dos veces'


def test_una_orden_heredada_completed_todavia_puede_cancelarse(app_context, test_user, test_hardware):
    stock_inicial = test_hardware.stock
    order = _orden(test_user, test_hardware, 'completed')

    assert cambiar_estado_orden(order, 'cancelled') is True
    db.session.commit()

    assert order.status == 'cancelled'
    assert _stock(test_hardware) == stock_inicial + 2
