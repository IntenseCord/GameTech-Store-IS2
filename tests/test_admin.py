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
"""
from extensions import db
from models.database_models import User, Hardware


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
