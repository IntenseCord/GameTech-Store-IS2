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
from models.database_models import User, Hardware, Game


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


def test_editar_hardware_rechaza_tipo_invalido(client):
    """Regresión: editar_hardware() no validaba `tipo` contra tipos_validos
    (a diferencia de nuevo_hardware) — se podía dejar un componente existente
    con un tipo que el resto de la app (filtros de tienda, compatibilidad)
    no reconoce."""
    crear_admin_logueado(client)
    hw = Hardware(tipo='CPU', marca='Intel', modelo='Core i5', precio=100, especificaciones='{}', stock=1)
    db.session.add(hw)
    db.session.commit()

    client.post(f'/admin/hardware/{hw.id}/editar', data={
        'tipo': 'TIPO_INVENTADO',
        'marca': 'Intel', 'modelo': 'Core i5', 'precio': '100', 'stock': '1', 'especificaciones': '{}'
    })

    hardware = Hardware.query.get(hw.id)
    assert hardware.tipo == 'CPU', 'editar_hardware aceptó un tipo fuera de tipos_validos'


def test_editar_hardware_rechaza_precio_negativo(client):
    """Regresión: editar_hardware() no validaba precio/stock negativos."""
    crear_admin_logueado(client)
    hw = Hardware(tipo='CPU', marca='Intel', modelo='Core i5', precio=100, especificaciones='{}', stock=1)
    db.session.add(hw)
    db.session.commit()

    client.post(f'/admin/hardware/{hw.id}/editar', data={
        'tipo': 'CPU', 'marca': 'Intel', 'modelo': 'Core i5',
        'precio': '-50', 'stock': '1', 'especificaciones': '{}'
    })

    hardware = Hardware.query.get(hw.id)
    assert hardware.precio == 100, 'editar_hardware aceptó un precio negativo'


def test_editar_juego_rechaza_stock_negativo(client):
    """Regresión: editar_juego() usaba request.form['stock'] directo (int())
    sin validar >= 0, a diferencia de nuevo_juego."""
    crear_admin_logueado(client)
    game = Game(nombre='Test', descripcion='d', precio=10, genero='Acción',
                desarrollador='dev', stock=5, fecha_lanzamiento=None)
    db.session.add(game)
    db.session.commit()

    client.post(f'/admin/juego/{game.id}/editar', data={
        'nombre': 'Test', 'descripcion': 'd', 'genero': 'Acción', 'desarrollador': 'dev',
        'precio': '10', 'stock': '-3', 'fecha_lanzamiento': '2024-01-01',
        'requisitos_minimos': '', 'requisitos_recomendados': ''
    })

    actualizado = Game.query.get(game.id)
    assert actualizado.stock == 5, 'editar_juego aceptó un stock negativo'


def test_editar_juego_con_campo_faltante_no_revienta_con_500(client):
    """Regresión: editar_juego() usaba request.form['campo'] (KeyError si
    falta), atrapado solo por el except Exception genérico externo, sin
    decirle al admin qué campo faltó."""
    crear_admin_logueado(client)
    game = Game(nombre='Test', descripcion='d', precio=10, genero='Acción',
                desarrollador='dev', stock=5, fecha_lanzamiento=None)
    db.session.add(game)
    db.session.commit()

    response = client.post(f'/admin/juego/{game.id}/editar', data={
        'nombre': 'Test', 'descripcion': 'd', 'genero': 'Acción',
        # falta 'desarrollador' a propósito
        'precio': '10', 'stock': '3', 'fecha_lanzamiento': '2024-01-01',
    }, follow_redirects=True)

    assert response.status_code == 200


def test_eliminar_juego_borra_la_imagen_subida_del_disco(client):
    """Regresión: game.imagen.startswith(UPLOAD) comparaba "/static/uploads/x"
    contra "static/uploads" (sin slash inicial) -- nunca coincidía, así que la
    limpieza de archivos nunca se ejecutaba y las imágenes subidas quedaban
    huérfanas en disco para siempre al borrar el juego."""
    import os
    import controllers.admin as admin_module

    filename = 'test_eliminar_juego_regresion.jpg'
    ruta_disco = os.path.join(admin_module.UPLOAD, filename)
    ruta_guardada = os.path.join('/' + admin_module.UPLOAD, filename)  # lo que guarda nuevo_juego()

    os.makedirs(admin_module.UPLOAD, exist_ok=True)
    with open(ruta_disco, 'wb') as f:
        f.write(b'fake image data')

    try:
        crear_admin_logueado(client)
        game = Game(nombre='Test', descripcion='d', precio=10, genero='Acción',
                    desarrollador='dev', stock=5, fecha_lanzamiento=None,
                    imagen=ruta_guardada)
        db.session.add(game)
        db.session.commit()

        client.post(f'/admin/juego/{game.id}/eliminar')

        assert not os.path.exists(ruta_disco), 'La imagen subida no se borró del disco al eliminar el juego'
    finally:
        if os.path.exists(ruta_disco):
            os.remove(ruta_disco)
