"""
Utilidades para manejo centralizado de errores de base de datos en los controladores.
"""
from flask import current_app
from extensions import db


def log_db_error(context, error):
    """Revierte la transacción actual y registra el error con un contexto uniforme.

    Reemplaza el bloque repetido `db.session.rollback()` + `current_app.logger.error(...)`
    (y su import local de `current_app`) que aparecía en cada `except` de los controladores.
    """
    db.session.rollback()
    current_app.logger.error(f'Error en {context}: {error}')
