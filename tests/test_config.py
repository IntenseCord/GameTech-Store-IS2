"""Tests de Config.get_database_url() y de la declaración del driver de PostgreSQL"""
from importlib.metadata import version
from pathlib import Path

import pytest
from config import Config


def _lineas_requirements():
    ruta = Path(__file__).parent.parent / 'requirements.txt'
    return [l.strip().lower() for l in ruta.read_text(encoding='utf-8').splitlines()]


@pytest.fixture
def entorno(monkeypatch):
    def fijar(database_url=None, flask_env=None):
        for clave, valor in (('DATABASE_URL', database_url), ('FLASK_ENV', flask_env)):
            if valor is None:
                monkeypatch.delenv(clave, raising=False)
            else:
                monkeypatch.setenv(clave, valor)
    return fijar


def test_esquema_postgres_se_convierte_a_postgresql(entorno):
    """SQLAlchemy 2.0 no acepta 'postgres://' (NoSuchModuleError)."""
    entorno(database_url='postgres://u:p@host/db?sslmode=require')
    assert Config.get_database_url() == 'postgresql://u:p@host/db?sslmode=require'


def test_postgres_convertido_es_aceptado_por_sqlalchemy(entorno):
    from sqlalchemy import create_engine
    entorno(database_url='postgres://u:p@host/db')
    motor = create_engine(Config.get_database_url())
    assert (motor.dialect.name, motor.dialect.driver) == ('postgresql', 'psycopg2')


def test_postgresql_usa_psycopg2(entorno):
    """El driver efectivo es psycopg2, el mismo que declara requirements.txt."""
    from sqlalchemy import create_engine
    entorno(database_url='postgresql://u:p@host/db')
    assert Config.get_database_url() == 'postgresql://u:p@host/db'
    motor = create_engine(Config.get_database_url())
    assert motor.dialect.driver == 'psycopg2'


def test_requirements_declara_psycopg2_y_no_psycopg3():
    lineas = _lineas_requirements()
    assert any(l.startswith('psycopg2-binary==') for l in lineas)
    assert not any(l.startswith(('psycopg==', 'psycopg[', 'psycopg-binary')) for l in lineas)


def test_version_instalada_de_psycopg2_coincide_con_requirements():
    """Detecta el desajuste entre lo declarado y lo instalado."""
    declarada = next(l for l in _lineas_requirements() if l.startswith('psycopg2-binary=='))
    assert version('psycopg2-binary') == declarada.split('==')[1]


def test_url_con_driver_explicito_no_se_modifica(entorno):
    entorno(database_url='postgresql+psycopg2://u:p@host/db')
    assert Config.get_database_url() == 'postgresql+psycopg2://u:p@host/db'


def test_sqlite_explicito_no_se_modifica(entorno):
    entorno(database_url='sqlite:///:memory:')
    assert Config.get_database_url() == 'sqlite:///:memory:'


def test_sin_database_url_en_desarrollo_usa_sqlite_local(entorno):
    entorno(flask_env='development')
    assert Config.get_database_url().startswith('sqlite:///')


def test_sin_database_url_en_produccion_falla_explicitamente(entorno):
    entorno(flask_env='production')
    with pytest.raises(RuntimeError, match='DATABASE_URL'):
        Config.get_database_url()


def test_sin_driver_postgres_no_cae_a_sqlite_en_silencio(entorno, monkeypatch):
    """Si falta el driver, la URL de Postgres se conserva (SQLAlchemy fallará
    con un error claro al crear el engine) en vez de redirigir a SQLite."""
    import builtins
    original = builtins.__import__

    def sin_psycopg(nombre, *args, **kwargs):
        if nombre.startswith('psycopg'):
            raise ImportError(nombre)
        return original(nombre, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', sin_psycopg)
    entorno(database_url='postgresql://u:p@host/db')
    assert Config.get_database_url() == 'postgresql://u:p@host/db'
