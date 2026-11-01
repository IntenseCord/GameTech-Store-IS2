"""
Recomendador de mejoras: qué piezas concretas del catálogo mejoran un equipo, ordenadas por mejor relación precio/rendimiento.

Parte del motor único (puro, sin Flask ni base de datos): usa `utils/hardware_engine.py` para decidir si hace falta mejorar algo
y para SIMULAR cada reemplazo, de modo que una recomendación nunca contradice al analizador.

Cuándo recomienda:
  - CPU o GPU es el cuello de botella  -> piezas del mismo tipo que mejoran el componente débil.
  - Un juego queda limitado por la VRAM -> GPU con la VRAM que ese juego pide (se combina con la anterior en una sola entrada).
  - La RAM es menor que la recomendada  -> módulos de 16 GB o más.
  Un equipo equilibrado, con RAM suficiente y sin límite de VRAM no recibe nada.

Cómo elige:
  - Solo piezas con stock que mejoren la que ya tienes (más puntaje, o 16 GB o más en la RAM).
  - Si alguna deja el equipo SIN cuello de botella (se simula con el motor), solo se muestran las que lo logran; si ninguna lo
    logra, se muestran las que mejoran y se avisa.
  - Se ordenan por puntaje por dólar (rendimiento / precio); la primera es la de "mejor relación".
  - Cada opción avisa de lo que obliga a cambiar: placa base por otro socket, otro tipo de memoria, fuente y largo de la GPU.
"""
from utils.hardware_engine import RAM_RECOMENDADA_GB, PUNTOS_POR_GB_RAM, detectar_cuello, sistema_de

MAXIMO_POR_DEFECTO = 3


def _disponibles(piezas, tipo):
    """Piezas del tipo con stock; las que no mejoran lo que ya tienes se descartan después por puntaje o capacidad."""
    return [p for p in piezas if p.tipo == tipo and (p.stock or 0) > 0]


def _cuello_cpu_gpu(cuello):
    return cuello['has_bottleneck'] and cuello['type'] in ('cpu', 'gpu')


def _aviso_de_equilibrio(cuello_actual, cuello_nuevo):
    if _cuello_cpu_gpu(cuello_actual):
        return 'Mejora, pero no elimina del todo el cuello de botella de tu equipo.'
    return f'Con esta pieza tu {cuello_nuevo["type"].upper()} pasaría a ser el cuello de botella.'


def _opcion(pieza, puntaje, puntaje_actual, avisos, equilibra=True):
    precio = float(pieza.precio)
    return {
        'pieza': pieza, 'precio': precio, 'puntaje': puntaje,
        'puntos_por_dolar': round(puntaje / precio, 2) if precio > 0 else 0.0,
        'mejora_pct': (puntaje - puntaje_actual) * 100 // puntaje_actual if puntaje_actual else 0,
        'equilibra': equilibra, 'mejor_relacion': False, 'avisos': avisos,
    }


def _ordenar(opciones, maximo):
    """Prefiere las que equilibran el equipo; ordena por puntaje por dólar (y precio) y marca la mejor relación."""
    equilibradas = [o for o in opciones if o['equilibra']]
    elegidas = sorted(equilibradas or opciones, key=lambda o: (-o['puntos_por_dolar'], o['precio'], o['pieza'].modelo))[:maximo]
    if elegidas:
        elegidas[0]['mejor_relacion'] = True
    return elegidas


# ------------------------------------------------------------------ avisos por tipo de pieza
def _avisos_gpu(gpu):
    specs, avisos = gpu.get_especificaciones(), []
    if specs.get('psu_recomendada_w'):
        avisos.append(f'Verifica tu fuente: se recomiendan {specs["psu_recomendada_w"]} W o más.')
    if specs.get('largo_mm'):
        avisos.append(f'Mide {specs["largo_mm"]} mm: confirma que cabe en tu gabinete.')
    return avisos


def _avisos_cpu(nueva, actual, ram):
    avisos = []
    if nueva.socket and actual.socket and nueva.socket != actual.socket:
        avisos.append(f'Requiere cambiar la placa base: tu CPU usa {actual.socket} y esta usa {nueva.socket}.')
    aceptadas, tipo_ram = nueva.get_especificaciones().get('tipos_memoria'), ram.get_especificaciones().get('tipo') if ram else None
    if aceptadas and tipo_ram and tipo_ram not in aceptadas:
        avisos.append(f'Requiere memoria {" o ".join(aceptadas)}: tu RAM es {tipo_ram}; cámbiala junto con la placa base.')
    return avisos


# ------------------------------------------------------------------ recomendaciones por tipo
def _recomendar_cpu(sistema, cpu, gpu, ram, cuello, piezas, maximo):
    opciones = []
    for candidata in _disponibles(piezas, 'CPU'):
        puntaje = candidata.benchmark_score or 0
        if puntaje <= sistema.cpu:
            continue
        cuello_nuevo = detectar_cuello(sistema_de(candidata, gpu, ram))
        equilibra = not _cuello_cpu_gpu(cuello_nuevo)
        avisos = _avisos_cpu(candidata, cpu, ram)
        if not equilibra:
            avisos.append(_aviso_de_equilibrio(cuello, cuello_nuevo))
        opciones.append(_opcion(candidata, puntaje, sistema.cpu, avisos, equilibra))
    if not opciones:
        return None
    return {'tipo': 'CPU', 'motivo': 'Tu CPU es el cuello de botella: no aprovecha todo el potencial de tu GPU.',
            'opciones': _ordenar(opciones, maximo)}


def _recomendar_gpu(sistema, cpu, gpu, ram, cuello, piezas, maximo, vram_necesaria):
    por_cuello = cuello['has_bottleneck'] and cuello['type'] == 'gpu'
    por_vram = bool(vram_necesaria) and sistema.vram_gb is not None and sistema.vram_gb < vram_necesaria
    if not (por_cuello or por_vram):
        return None
    motivos = []
    if por_cuello:
        motivos.append('Tu GPU es el cuello de botella: tu CPU rinde más de lo que ella aprovecha.')
    if por_vram:
        motivos.append(f'Hay juegos que piden {vram_necesaria} GB de VRAM y tu GPU tiene {sistema.vram_gb} GB.')
    opciones = []
    for candidata in _disponibles(piezas, 'GPU'):
        puntaje = candidata.benchmark_score or 0
        if puntaje <= sistema.gpu or (por_vram and (candidata.vram_gb or 0) < vram_necesaria):
            continue
        cuello_nuevo = detectar_cuello(sistema_de(cpu, candidata, ram))
        equilibra = not _cuello_cpu_gpu(cuello_nuevo)
        avisos = _avisos_gpu(candidata)
        if not equilibra:
            avisos.append(_aviso_de_equilibrio(cuello, cuello_nuevo))
        opciones.append(_opcion(candidata, puntaje, sistema.gpu, avisos, equilibra))
    if not opciones:
        return None
    return {'tipo': 'GPU', 'motivo': ' '.join(motivos), 'opciones': _ordenar(opciones, maximo)}


def _recomendar_ram(sistema, ram, piezas, maximo):
    if sistema.ram_gb is None or sistema.ram_gb >= RAM_RECOMENDADA_GB:
        return None
    opciones = []
    for candidata in _disponibles(piezas, 'RAM'):
        gb = candidata.get_ram_capacity_gb()
        if gb < RAM_RECOMENDADA_GB:
            continue
        tipo = candidata.get_especificaciones().get('tipo')
        avisos = [f'Es memoria {tipo}: tu placa base debe aceptar {tipo}.'] if tipo else []
        opciones.append(_opcion(candidata, gb * PUNTOS_POR_GB_RAM, sistema.ram_gb * PUNTOS_POR_GB_RAM, avisos))
    if not opciones:
        return None
    return {'tipo': 'RAM', 'motivo': f'Tienes {sistema.ram_gb} GB de RAM; los juegos modernos recomiendan {RAM_RECOMENDADA_GB} GB.',
            'opciones': _ordenar(opciones, maximo)}


def recomendar_mejoras(cpu, gpu, ram, piezas, vram_necesaria=None, maximo=MAXIMO_POR_DEFECTO):
    """Lista de {'tipo', 'motivo', 'opciones'} con las mejoras del catálogo para el equipo (vacía si no hace falta ninguna).

    `vram_necesaria`: GB de VRAM que pide el juego más exigente que el equipo no alcanza por falta de VRAM (o None).
    Con una CPU o GPU sin benchmark no se recomienda nada: no se inventa un diagnóstico sin datos.
    """
    sistema = sistema_de(cpu, gpu, ram)
    if sistema.cpu is None or sistema.gpu is None:
        return []
    cuello = detectar_cuello(sistema)
    recomendaciones = [
        _recomendar_cpu(sistema, cpu, gpu, ram, cuello, piezas, maximo) if cuello['has_bottleneck'] and cuello['type'] == 'cpu' else None,
        _recomendar_gpu(sistema, cpu, gpu, ram, cuello, piezas, maximo, vram_necesaria),
        _recomendar_ram(sistema, ram, piezas, maximo),
    ]
    return [r for r in recomendaciones if r]
