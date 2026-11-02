"""
Pantalla de resultado de una orden (/orden/<id>): lo que dice depende del estado (hallazgo 49).

Detectado en la prueba e2e del 1 de noviembre: con un pago RECHAZADO el bloque "¿Qué sigue?" prometía "Recibirás un email de confirmación
con los detalles de tu orden" y "Tu orden será procesada en las próximas 24 horas", cuando la orden es un estado final y el
correo que llega es el de "Tu pago no pudo procesarse". Al revisarla apareció además que una orden CANCELADA mostraba
"¡Compra Realizada con Éxito!", porque todo lo que no fuera pendiente o rechazada caía en el mensaje de éxito.
"""
import pytest

from extensions import db
from models.database_models import Order, OrderItem

PROMESAS_DE_UNA_COMPRA_EXITOSA = ('Tu orden será procesada en las próximas 24 horas', 'Recibirás un email de confirmación con los detalles')


def _orden(usuario, hardware, estado):
    order = Order(user_id=usuario.id, total=1, status=estado)
    db.session.add(order)
    db.session.flush()
    db.session.add(OrderItem(order_id=order.id, product_type='hardware', product_id=hardware.id, product_name='x', quantity=1, price=1))
    db.session.commit()
    return order


def _ver(client, usuario, hardware, estado):
    client.post('/login', data={'username': 'testuser', 'password': 'Test1234'})
    return client.get(f'/orden/{_orden(usuario, hardware, estado).id}').get_data(as_text=True)


@pytest.mark.parametrize('estado', ['approved', 'completed'])
def test_una_compra_exitosa_conserva_sus_promesas(client, test_user, test_hardware, estado):
    html = _ver(client, test_user, test_hardware, estado)
    assert '¡Compra Realizada con Éxito!' in html
    assert all(p in html for p in PROMESAS_DE_UNA_COMPRA_EXITOSA)
    assert html.count('¿Qué sigue?') == 1


def test_una_orden_pendiente_dice_que_se_esta_esperando_el_pago(client, test_user, test_hardware):
    html = _ver(client, test_user, test_hardware, 'pending')
    assert 'pendiente de confirmación' in html and 'notificaremos' in html
    assert not any(p in html for p in PROMESAS_DE_UNA_COMPRA_EXITOSA)
    assert '¡Compra Realizada con Éxito!' not in html


def test_una_orden_rechazada_no_promete_una_compra(client, test_user, test_hardware):
    html = _ver(client, test_user, test_hardware, 'rejected')
    assert 'Tu pago no pudo procesarse' in html
    # el checkout vacía el carrito al crear la orden (hallazgo 50): no se puede mandar al cliente "a su carrito"
    assert 'agregarlos de nuevo al carrito' in html and 'desde tu carrito' not in html
    assert not any(p in html for p in PROMESAS_DE_UNA_COMPRA_EXITOSA)
    assert '¡Compra Realizada con Éxito!' not in html and '24 horas' not in html
    assert html.count('¿Qué sigue?') == 1 and 'correo' in html.split('¿Qué sigue?')[1]


def test_una_orden_cancelada_no_se_presenta_como_exitosa(client, test_user, test_hardware):
    html = _ver(client, test_user, test_hardware, 'cancelled')
    assert 'Tu orden fue cancelada' in html and 'volvieron al inventario' in html
    assert '¡Compra Realizada con Éxito!' not in html and not any(p in html for p in PROMESAS_DE_UNA_COMPRA_EXITOSA)
    assert '24 horas' not in html


@pytest.mark.parametrize('estado', ['pending', 'approved', 'rejected', 'cancelled'])
def test_todas_las_ordenes_muestran_su_numero_total_y_productos(client, test_user, test_hardware, estado):
    html = _ver(client, test_user, test_hardware, estado)
    assert 'Número de Orden' in html and 'Total' in html and 'Ver Mis Órdenes' in html and 'Seguir Comprando' in html
