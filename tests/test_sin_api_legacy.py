"""Guardia contra APIs legacy de SQLAlchemy / Flask-SQLAlchemy.

Query.get() y Query.get_or_404() están en desuso (SQLAlchemy 2.0, Flask-SQLAlchemy 3.1):
se reemplazan por db.session.get(Modelo, id) y db.get_or_404(Modelo, id).
pytest.ini convierte el aviso en error para el código que los tests ejecutan;
este test cubre además las rutas que ningún test recorre.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CARPETAS_IGNORADAS = {'.git', '.venv', 'venv', 'env', 'node_modules', 'instance', '__pycache__'}
PATRON = re.compile(r'\.query\.get(?:_or_404)?\(')


def _archivos_python():
    for ruta in RAIZ.rglob('*.py'):
        if CARPETAS_IGNORADAS.isdisjoint(ruta.relative_to(RAIZ).parts):
            yield ruta


def test_no_hay_usos_de_query_get_ni_get_or_404():
    ofensores = []
    for ruta in _archivos_python():
        for numero, linea in enumerate(ruta.read_text(encoding='utf-8', errors='ignore').splitlines(), 1):
            if PATRON.search(linea):
                ofensores.append(f'{ruta.relative_to(RAIZ)}:{numero}: {linea.strip()}')
    assert not ofensores, 'Usos de API legacy:\n' + '\n'.join(ofensores)
