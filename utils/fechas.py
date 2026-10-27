"""
Fecha y hora UTC para las columnas DateTime de la base de datos.
"""
from datetime import datetime, timezone


def ahora_utc():
    """Hora UTC actual como datetime *sin* zona horaria (naive).

    Sustituye a la función utcnow de datetime (en desuso desde Python 3.12) con el mismo resultado: las columnas
    db.DateTime no guardan zona horaria, y el resto del código compara con .replace(tzinfo=timezone.utc).
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
