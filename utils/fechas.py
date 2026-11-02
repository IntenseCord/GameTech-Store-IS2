"""
Fechas de la aplicación: se GUARDAN en UTC y se MUESTRAN en hora de Bogotá.

Una sola convención (hallazgo 31): las columnas DateTime guardan UTC sin zona (`ahora_utc`) y toda pantalla, correo y PDF convierte a la
hora de Colombia al mostrar (`formatear_local`, y el filtro `fecha_local` en las plantillas). Nadie usa la hora local del servidor.
"""
from datetime import datetime, timedelta, timezone

# Colombia está en UTC-5 todo el año (no usa horario de verano), por eso un desfase fijo equivale a America/Bogota
# y no hace falta la base de zonas horarias (tzdata), que en Windows no viene instalada.
ZONA_LOCAL = timezone(timedelta(hours=-5), 'America/Bogota')


def ahora_utc():
    """Hora UTC actual como datetime *sin* zona horaria (naive).

    Sustituye a la función utcnow de datetime (en desuso desde Python 3.12) con el mismo resultado: las columnas
    db.DateTime no guardan zona horaria, y el resto del código compara con .replace(tzinfo=timezone.utc).
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def a_hora_local(momento):
    """Convierte un instante guardado en UTC (sin zona, como sale de la base, o con zona) a la hora de Bogotá."""
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(ZONA_LOCAL)


def formatear_local(momento, formato='%d/%m/%Y %H:%M'):
    """El instante en hora de Bogotá con el formato dado; '' si no hay valor (una columna vacía no rompe la página)."""
    if momento is None:
        return ''
    return a_hora_local(momento).strftime(formato)
