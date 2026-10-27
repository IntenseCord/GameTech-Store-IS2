"""
Textos y botones de las plantillas del flujo de compra.

- checkout.html decía "compra simulada, no se procesará ningún pago real" aunque el pago
  real se hace en MercadoPago.
- mis_ordenes.html seguía ofreciendo "Solicitar Factura" después de facturar.
"""
from decimal import Decimal

from extensions import db
from models.database_models import CartItem, Invoice, Order, OrderItem
from utils.fechas import ahora_utc


def login(client, username='testuser', password='Test1234'):
    return client.post('/login', data={'username': username, 'password': password})


def _orden(user, status, product_id):
    orden = Order(user_id=user.id, total=Decimal('59.99'), status=status)
    db.session.add(orden)
    db.session.flush()
    db.session.add(OrderItem(order_id=orden.id, product_type='game', product_id=product_id,
                             product_name='Test Game', quantity=1, price=Decimal('59.99')))
    db.session.commit()
    return orden


def _factura(user, orden):
    factura = Invoice(
        uuid=f'uuid-{orden.id}', folio=f'FE-{orden.id:06d}', user_id=user.id, order_id=orden.id,
        nit_receptor='1234567890', razon_social_receptor='Cliente Prueba',
        subtotal=Decimal('50.41'), iva=Decimal('9.58'), total=Decimal('59.99'),
        fecha_emision=ahora_utc(),
    )
    db.session.add(factura)
    db.session.commit()
    return factura


def test_checkout_no_dice_que_el_pago_es_simulado(client, test_user, test_game):
    login(client)
    db.session.add(CartItem(user_id=test_user.id, product_type='game', product_id=test_game.id, quantity=1))
    db.session.commit()

    html = client.get('/carrito/checkout').get_data(as_text=True)

    assert 'compra simulada' not in html
    assert 'ningún pago real' not in html
    assert 'MercadoPago' in html


def test_orden_aprobada_sin_factura_ofrece_solicitarla(client, test_user, test_game):
    login(client)
    orden = _orden(test_user, 'approved', test_game.id)

    html = client.get('/mis-ordenes').get_data(as_text=True)

    assert f'/factura/solicitar/{orden.id}' in html
    assert 'Solicitar Factura' in html
    assert 'Ver Factura' not in html


def test_orden_ya_facturada_ofrece_ver_la_factura_y_no_solicitarla(client, test_user, test_game):
    login(client)
    orden = _orden(test_user, 'approved', test_game.id)
    factura = _factura(test_user, orden)

    html = client.get('/mis-ordenes').get_data(as_text=True)

    assert 'Ver Factura' in html
    assert f'/factura/{factura.id}"' in html
    assert 'Solicitar Factura' not in html
    assert f'/factura/solicitar/{orden.id}' not in html


def test_orden_pendiente_no_ofrece_factura(client, test_user, test_game):
    login(client)
    _orden(test_user, 'pending', test_game.id)

    html = client.get('/mis-ordenes').get_data(as_text=True)

    assert 'Solicitar Factura' not in html
    assert 'Ver Factura' not in html


def test_cada_orden_muestra_el_boton_que_le_corresponde(client, test_user, test_game):
    login(client)
    facturada = _orden(test_user, 'approved', test_game.id)
    factura = _factura(test_user, facturada)
    sin_facturar = _orden(test_user, 'approved', test_game.id)

    html = client.get('/mis-ordenes').get_data(as_text=True)

    assert f'/factura/{factura.id}"' in html
    assert f'/factura/solicitar/{sin_facturar.id}' in html
    assert f'/factura/solicitar/{facturada.id}' not in html
