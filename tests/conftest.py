"""
Configuración de fixtures para pytest y pytest-bdd
"""
import os

# CRÍTICO: forzar SQLite en memoria ANTES de importar `app`. app.py calcula
# SQLALCHEMY_DATABASE_URI/SQLALCHEMY_ENGINE_OPTIONS a partir de DATABASE_URL
# al momento de importarse (Config.get_database_url() ignora FLASK_ENV/TestingConfig
# y siempre lee esa variable), y Flask-SQLAlchemy cachea el engine en ese instante.
# Sobrescribir app.config DESPUÉS de importar (como se hacía antes) no tiene ningún
# efecto sobre el engine ya construido: los tests terminaban corriendo db.create_all()/
# db.drop_all() contra la base de datos real de Neon en vez de SQLite. os.environ.setdefault
# respeta un DATABASE_URL que ya esté seteado en el proceso (no debería estarlo aquí,
# pero así load_dotenv() tampoco lo pisa al no usar override=True).
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['FLASK_ENV'] = 'testing'

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
def client_csrf(app_context):
    """Cliente de prueba con CSRF real activo.

    El resto de la suite corre con WTF_CSRF_ENABLED=False (ver app_context):
    eso es necesario para no tener que fabricar tokens en cada POST, pero como
    efecto secundario ningún test detecta un formulario al que le falte el
    campo csrf_token — ya pasó (checkout.html y otros 12 formularios más,
    todos dependían solo del parche JS de base.html) y solo se ve probando
    con esto activado. Usar este fixture para cubrir esos casos puntuales.
    """
    app_context.config['WTF_CSRF_ENABLED'] = True
    yield app_context.test_client()
    app_context.config['WTF_CSRF_ENABLED'] = False


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


# Fixtures adicionales para pytest-bdd
@pytest.fixture
def browser():
    """Fixture para navegador (opcional para pruebas con Selenium)"""
    pass
