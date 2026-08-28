"""
Configuración de fixtures para pytest
"""
import pytest
from app import app
from extensions import db
from models.database_models import User, Game, Hardware


@pytest.fixture
def app_context():
    """Crear contexto de aplicación para testing"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app_context):
    """Crear cliente de prueba"""
    return app_context.test_client()


@pytest.fixture
def test_user(app_context):
    """Crear usuario de prueba"""
    user = User(username='testuser', email='test@example.com')
    user.set_password('Test1234')
    user.email_verified = True
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def test_game(app_context):
    """Crear juego de prueba"""
    game = Game(
        nombre='Test Game',
        descripcion='Test game description',
        precio=49.99,
        genero='Acción',
        desarrollador='Test Dev',
        requisitos_minimos='{"cpu": "Intel i3", "ram": "8GB", "gpu": "GTX 1050"}',
        requisitos_recomendados='{"cpu": "Intel i5", "ram": "16GB", "gpu": "GTX 1060"}',
        stock=10
    )
    db.session.add(game)
    db.session.commit()
    return game


@pytest.fixture
def test_hardware(app_context):
    """Crear hardware de prueba"""
    hardware = Hardware(
        tipo='CPU',
        marca='Intel',
        modelo='Core i5-10400',
        precio=199.99,
        descripcion='Test CPU',
        especificaciones='{"cores": 6, "threads": 12, "frequency": "2.9GHz"}',
        stock=5
    )
    db.session.add(hardware)
    db.session.commit()
    return hardware
