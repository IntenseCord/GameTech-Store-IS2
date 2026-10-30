"""
Resolución de texto libre a un componente del catálogo.

La tienda (`store.html`) y la ficha de un juego (`game_detail.html`) mandan texto a /consultar-compatibilidad.
El motor no adivina potencias por palabras: el texto se busca en el catálogo (que tiene `benchmark_score`) y, si
no se reconoce o es ambiguo, el componente queda "sin datos".
"""
import re

from models.database_models import Hardware

LARGO_MINIMO = 4       # "i5" o "intel" coinciden con demasiados componentes para fiarse
MAX_RAM_GB = 1024


def _normalizar(texto):
    return re.sub(r'[^a-z0-9]', '', str(texto or '').lower())


def resolver_componente(tipo, texto):
    """Devuelve el Hardware del catálogo que corresponde al texto, o None si no se reconoce o es ambiguo."""
    buscado = _normalizar(texto)
    if len(buscado) < LARGO_MINIMO:
        return None
    candidatos = Hardware.query.filter_by(tipo=tipo).all()

    # 1) coincidencia exacta con el modelo o con "marca modelo"
    for c in candidatos:
        if buscado in (_normalizar(c.modelo), _normalizar(f'{c.marca} {c.modelo}')):
            return c

    # 2) el texto contiene el nombre completo de un componente ("Intel Core i5-12400F de 12.ª gen"): gana el más largo
    contenidos = [c for c in candidatos if _normalizar(c.modelo) in buscado]
    if contenidos:
        return max(contenidos, key=lambda c: len(_normalizar(c.modelo)))

    # 3) el texto es parte del nombre de un componente: solo vale si hay uno solo
    parciales = [c for c in candidatos if buscado in _normalizar(f'{c.marca} {c.modelo}')]
    return parciales[0] if len(parciales) == 1 else None


def ram_gb_de_texto(texto):
    """'16 GB', '16GB', 'Vengeance LPX 16GB DDR4' o '8' -> GB; None si no hay una cantidad."""
    if texto is None:
        return None
    coincidencia = re.search(r'(\d+)\s*gb', str(texto), re.IGNORECASE) or re.fullmatch(r'\s*(\d+)\s*', str(texto))
    if not coincidencia:
        return None
    gb = int(coincidencia.group(1))
    return gb if 0 < gb <= MAX_RAM_GB else None
