"""
Hallazgo 15: avisos de librerías en desuso que se acumulaban en la suite (2.605).

- datetime.utcnow() (Python 3.12+) se sustituye por utils.fechas.ahora_utc(), con el mismo resultado: hora UTC *naive*.
- Strawberry pide clases o fábricas, no instancias, en `extensions=[...]`.
"""
import re
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path

import strawberry
from strawberry.extensions import SchemaExtension

from controllers.graphql_api import extensiones_de_seguridad
from extensions import db
from models.database_models import User
from utils.fechas import ahora_utc

RAIZ = Path(__file__).resolve().parent.parent


def test_ahora_utc_es_la_hora_utc_sin_zona_horaria():
    ahora = ahora_utc()

    assert ahora.tzinfo is None
    assert abs(ahora - datetime.now(timezone.utc).replace(tzinfo=None)) < timedelta(seconds=5)


def test_las_columnas_de_fecha_siguen_guardandose_sin_zona_horaria(app_context):
    usuario = User(username='fechas', email='fechas@example.com')
    usuario.set_password('Test1234')
    db.session.add(usuario)
    db.session.commit()

    assert usuario.created_at.tzinfo is None
    assert abs(usuario.created_at - ahora_utc()) < timedelta(seconds=5)


def test_el_codigo_de_la_aplicacion_no_usa_datetime_utcnow():
    """datetime.utcnow() está en desuso: usar utils.fechas.ahora_utc()."""
    patron = re.compile(r'\butcnow\s*\(|\bdatetime\.utcnow\b')
    ofensores = []
    for archivo in RAIZ.rglob('*.py'):
        partes = archivo.relative_to(RAIZ).parts
        if partes[0] in ('venv', '.venv', 'env', 'node_modules', 'migrations') or archivo.name == Path(__file__).name:
            continue
        for numero, linea in enumerate(archivo.read_text(encoding='utf-8', errors='ignore').splitlines(), 1):
            if patron.search(linea):
                ofensores.append(f'{"/".join(partes)}:{numero}: {linea.strip()}')
    assert not ofensores, 'Usos de utcnow:\n' + '\n'.join(ofensores)


def test_las_extensiones_de_graphql_son_clases_o_fabricas_no_instancias():
    for produccion in (False, True):
        for extension in extensiones_de_seguridad(produccion):
            assert not isinstance(extension, SchemaExtension), extension


def test_construir_el_esquema_graphql_no_emite_avisos_de_desuso():
    @strawberry.type
    class Consulta:
        @strawberry.field
        def hola(self) -> str:
            return 'hola'

    with warnings.catch_warnings():
        warnings.simplefilter('error')
        for produccion in (False, True):
            strawberry.Schema(query=Consulta, extensions=extensiones_de_seguridad(produccion))
