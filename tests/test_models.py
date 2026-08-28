"""
Tests de modelos de base de datos
"""
import pytest
from models.database_models import User, Game, Hardware


def test_crear_usuario(app_context):
    """Test de creación de usuario"""
    user = User(username='testuser', email='test@example.com')
    user.set_password('Test1234')
    db.session.add(user)
    db.session.commit()
    
    assert user.id is not None
    assert user.username == 'testuser'
    assert user.email == 'test@example.com'
    assert user.check_password('Test1234')
    assert not user.check_password('WrongPassword')


def test_crear_juego(app_context):
    """Test de creación de juego"""
    game = Game(
        nombre='Test Game',
        descripcion='Test description',
        precio=49.99,
        genero='Acción',
        desarrollador='Test Dev',
        requisitos_minimos='{"cpu": "Intel i3"}',
        requisitos_recomendados='{"cpu": "Intel i5"}',
        stock=10
    )
    db.session.add(game)
    db.session.commit()
    
    assert game.id is not None
    assert game.nombre == 'Test Game'
    assert game.precio == 49.99
    assert game.stock == 10


def test_crear_hardware(app_context):
    """Test de creación de hardware"""
    hardware = Hardware(
        tipo='CPU',
        marca='Intel',
        modelo='Core i5-10400',
        precio=199.99,
        especificaciones='{"cores": 6}',
        stock=5
    )
    db.session.add(hardware)
    db.session.commit()
    
    assert hardware.id is not None
    assert hardware.tipo == 'CPU'
    assert hardware.marca == 'Intel'
    assert hardware.precio == 199.99


def test_usuario_admin(app_context):
    """Test de rol de administrador"""
    user = User(username='admin', email='admin@example.com', is_admin=True)
    user.set_password('Admin1234')
    db.session.add(user)
    db.session.commit()
    
    assert user.is_admin is True


def test_juego_get_requisitos(app_context):
    """Test de obtención de requisitos de juego"""
    game = Game(
        nombre='Test Game',
        descripcion='Test description',
        precio=49.99,
        genero='Acción',
        desarrollador='Test Dev',
        requisitos_minimos='{"cpu": "Intel i3", "ram": "8GB"}',
        requisitos_recomendados='{"cpu": "Intel i5", "ram": "16GB"}',
        stock=10
    )
    db.session.add(game)
    db.session.commit()
    
    requisitos_min = game.get_requisitos_minimos()
    assert requisitos_min['cpu'] == 'Intel i3'
    assert requisitos_min['ram'] == '8GB'


def test_hardware_get_especificaciones(app_context):
    """Test de obtención de especificaciones de hardware"""
    hardware = Hardware(
        tipo='CPU',
        marca='Intel',
        modelo='Core i5-10400',
        precio=199.99,
        especificaciones='{"cores": 6, "threads": 12}',
        stock=5
    )
    db.session.add(hardware)
    db.session.commit()
    
    especificaciones = hardware.get_especificaciones()
    assert especificaciones['cores'] == 6
    assert especificaciones['threads'] == 12
