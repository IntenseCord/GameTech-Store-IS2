"""
Tests del panel de administración.

Regresión: templates/admin/hardware_form.html tenía valores de <option>
en inglés/mayúsculas ('STORAGE', 'MOTHERBOARD', 'PSU', 'CASE') que no
coincidían con la lista `tipos_validos` que valida
controllers/admin.py::nuevo_hardware() ('Almacenamiento', 'Motherboard',
'Fuente de poder', 'Gabinete') — el formulario de admin no podía crear
Motherboard/PSU/Almacenamiento/Gabinete, solo CPU/GPU/RAM (coincidencia).
Esto bloqueaba directamente el plan de sembrar PSU/Cooling/Gabinete vía
el panel de admin.

Regresión (revisión de código 2026-09-15): actualizar_estado_orden() dejaba
que un admin cambiara el status de una orden a mano sin tocar el stock --
a diferencia del webhook de MercadoPago (controllers/webhooks.py), que sí
restaura/descuenta stock según la transición. Corregir a mano una orden
aprobada a 'rejected' (o viceversa) desincronizaba el inventario real.
Fix: controllers/admin.py ahora usa el mismo utils/order_stock.py que el
webhook.
"""
from extensions import db
from models.database_models import User, Hardware, Order, OrderItem


def crear_admin_logueado(client):
    admin = User(username='admintest', email='admintest@example.com', is_admin=True, email_verified=True)
    admin.set_password('Test1234')
    db.session.add(admin)
    db.session.commit()
    client.post('/login', data={'username': 'admintest', 'password': 'Test1234'})


def test_crear_hardware_todos_los_tipos_del_select(client):
    """Cada value real del <select> de templates/admin/hardware_form.html
    debe poder crear un componente sin ser rechazado por 'Tipo de
    hardware inválido'."""
    crear_admin_logueado(client)

    tipos_del_select = ['CPU', 'GPU', 'RAM', 'Almacenamiento', 'Motherboard', 'Fuente de poder', 'Refrigeración', 'Gabinete', 'Otro']

    for tipo in tipos_del_select:
        modelo = f'Test {tipo}'
        client.post('/admin/hardware/nuevo', data={
            'tipo': tipo,
            'marca': 'Marca Test',
            'modelo': modelo,
            'precio': '99.99',
            'stock': '1',
            'especificaciones': '{}'
        })
        creado = Hardware.query.filter_by(modelo=modelo).first()
        assert creado is not None, f'El tipo "{tipo}" del <select> fue rechazado por el backend'
        assert creado.tipo == tipo


def test_actualizar_estado_orden_a_rechazada_restaura_stock(client, test_hardware):
    """Regresión: el cambio manual de estado del admin no tocaba stock, a
    diferencia del webhook de MercadoPago -- corregir a mano una orden
    aprobada a 'rejected' dejaba el inventario desincronizado."""
    crear_admin_logueado(client)
    admin = User.query.filter_by(username='admintest').first()
    stock_vendido = test_hardware.stock
    order = Order(user_id=admin.id, total=test_hardware.precio, status='approved')
    db.session.add(order)
    db.session.flush()
    db.session.add(OrderItem(
        order_id=order.id, product_type='hardware', product_id=test_hardware.id,
        product_name='Test Hardware', quantity=1, price=test_hardware.precio
    ))
    db.session.commit()

    client.post(f'/admin/orden/{order.id}/estado', data={'status': 'rejected'})

    hardware = Hardware.query.get(test_hardware.id)
    assert hardware.stock == stock_vendido + 1


def test_actualizar_estado_orden_a_aprobada_tras_rechazo_descuenta_stock(client, test_hardware):
    """Reintento de pago corregido a mano: si una orden rechazada (con
    stock ya restaurado) se marca 'approved', el stock debe descontarse
    de nuevo."""
    crear_admin_logueado(client)
    admin = User.query.filter_by(username='admintest').first()
    stock_restaurado = test_hardware.stock
    order = Order(user_id=admin.id, total=test_hardware.precio, status='rejected')
    db.session.add(order)
    db.session.flush()
    db.session.add(OrderItem(
        order_id=order.id, product_type='hardware', product_id=test_hardware.id,
        product_name='Test Hardware', quantity=1, price=test_hardware.precio
    ))
    db.session.commit()

    client.post(f'/admin/orden/{order.id}/estado', data={'status': 'approved'})

    hardware = Hardware.query.get(test_hardware.id)
    assert hardware.stock == stock_restaurado - 1
