"""
Motor único de hardware: puntuación del sistema, rendimiento por juego y cuellos de botella.

Toda pantalla o API que opine sobre hardware (analizador, verificador de la tienda, setup completo) llama a
este módulo, de modo que dos pantallas nunca puedan contradecirse. Es puro: no usa Flask ni la base de datos,
recibe puntuaciones (`Hardware.benchmark_score`) y requisitos (`GameRequirements`) y devuelve diccionarios.

Principio central: un dato que falta NO es un cero. Un componente sin `benchmark_score` o un juego sin
requisitos cargados produce el estado `sin_datos`, nunca "no puede correr", "balanceado" ni "ultra".
"""
from dataclasses import dataclass

SIN_DATOS = 'sin_datos'

# --- puntuación total del sistema: GPU 50 %, CPU 35 %, RAM 15 % (100 puntos por GB) ---
PESO_GPU, PESO_CPU, PESO_RAM = 50, 35, 15          # en porcentaje: se calcula con enteros para no depender de decimales
PUNTOS_POR_GB_RAM = 100
NIVELES_DEL_SISTEMA = (
    (15000, 'Ultra High-End (4K Ultra)'),
    (10000, 'High-End (1440p Ultra)'),
    (7000, 'Mid-High (1080p Ultra)'),
    (4000, 'Mid-Range (1080p Medium-High)'),
)
NIVEL_BASE = 'Entry Level (1080p Low-Medium)'
NIVEL_SIN_DATOS = 'Sin datos suficientes'

# --- calidad por juego: FPS base de cada nivel (se escalan con la razón respecto del requisito) ---
FPS_BASE = {'ultra': 90, 'high': 60, 'medium': 45, 'low': 30}
FPS_MINIMO, FPS_MAXIMO = 15, 240
# "medium" exige un 20 % más que el mínimo (6/5), calculado con enteros
MEDIO_NUM, MEDIO_DEN = 6, 5
# un componente es el limitante si su razón con el requisito es menor al 70 % de la del otro
LIMITANTE_NUM, LIMITANTE_DEN = 7, 10

# --- cuello de botella: razón entre el componente más potente y el más débil ---
RAZON_LEVE, RAZON_MODERADA, RAZON_SEVERA = 3, 4, 6        # en medios: 1,5 / 2,0 / 3,0 (se compara mayor*2 >= menor*razón)
OBJETIVO_NUM, OBJETIVO_DEN = 3, 4                          # el débil debería llegar al 75 % del fuerte
RAM_RECOMENDADA_GB = 16
RAM_MINIMA_GB = 8
ORDEN_SEVERIDAD = {'none': 0, 'mild': 1, 'moderate': 2, 'severe': 3}


@dataclass(frozen=True)
class Sistema:
    """Puntuaciones del equipo. `None` significa "sin dato", no cero.

    `desconocidos` son los componentes que el usuario SÍ indicó pero de los que no hay dato (texto que no está
    en el catálogo, componente sin benchmark_score): con ellos no se puede confirmar que un juego corra, aunque
    los demás componentes lo cumplan. Un componente que no se indicó (por ejemplo, solo se eligió la GPU) no es
    desconocido: simplemente no se evalúa.
    """
    cpu: int | None = None
    gpu: int | None = None
    ram_gb: int | None = None
    desconocidos: tuple = ()

    @property
    def faltantes(self):
        return [n for n, v in (('cpu', self.cpu), ('gpu', self.gpu), ('ram', self.ram_gb)) if v is None]


def _puntuacion(componente):
    puntos = getattr(componente, 'benchmark_score', None)
    return puntos if puntos and puntos > 0 else None


def _ram_gb(componente):
    if componente is None:
        return None
    gb = componente.get_ram_capacity_gb() if hasattr(componente, 'get_ram_capacity_gb') else None
    return gb if gb and gb > 0 else None


def sistema_de(cpu=None, gpu=None, ram=None):
    """Construye el Sistema a partir de objetos Hardware (None = no indicado; sin benchmark = desconocido)."""
    sistema = Sistema(cpu=_puntuacion(cpu), gpu=_puntuacion(gpu), ram_gb=_ram_gb(ram))
    desconocidos = tuple(n for n, objeto, valor in (('cpu', cpu, sistema.cpu), ('gpu', gpu, sistema.gpu), ('ram', ram, sistema.ram_gb))
                         if objeto is not None and valor is None)
    return Sistema(sistema.cpu, sistema.gpu, sistema.ram_gb, desconocidos)


# ------------------------------------------------------------------ sistema
def puntuacion_total(sistema):
    """Puntuación general, o None si falta la CPU o la GPU."""
    if sistema.cpu is None or sistema.gpu is None:
        return None
    ram_puntos = (sistema.ram_gb or 0) * PUNTOS_POR_GB_RAM
    return (sistema.gpu * PESO_GPU + sistema.cpu * PESO_CPU + ram_puntos * PESO_RAM) // 100


def nivel_del_sistema(total):
    if total is None:
        return NIVEL_SIN_DATOS
    for umbral, nombre in NIVELES_DEL_SISTEMA:
        if total >= umbral:
            return nombre
    return NIVEL_BASE


# -------------------------------------------------------------------- juegos
def _sin_datos(motivo):
    return {'estado': SIN_DATOS, 'puede_correr': None, 'calidad': None, 'fps': 0,
            'limitante': None, 'motivo': motivo, 'parcial': False}


def _por_encima(sistema, nivel, req):
    """¿El equipo cumple, con los componentes que se conocen, los requisitos de ese nivel?"""
    pares = ((sistema.cpu, getattr(req, f'{nivel}_cpu_score')),
             (sistema.gpu, getattr(req, f'{nivel}_gpu_score')),
             (sistema.ram_gb, getattr(req, f'{nivel}_ram_gb')))
    return all(valor is None or valor >= exigido for valor, exigido in pares)


def _calidad(sistema, req):
    if _por_encima(sistema, 'ultra', req):
        return 'ultra'
    if _por_encima(sistema, 'rec', req):
        return 'high'
    cpu_ok = sistema.cpu is None or sistema.cpu * MEDIO_DEN >= req.min_cpu_score * MEDIO_NUM
    gpu_ok = sistema.gpu is None or sistema.gpu * MEDIO_DEN >= req.min_gpu_score * MEDIO_NUM
    return 'medium' if cpu_ok and gpu_ok else 'low'


def _requisitos_del_nivel(calidad, req):
    """(cpu, gpu, ram) exigidos al nivel de calidad alcanzado, para repartir el FPS y buscar el limitante."""
    if calidad == 'ultra':
        return req.ultra_cpu_score, req.ultra_gpu_score, req.ultra_ram_gb
    if calidad == 'high':
        return req.rec_cpu_score, req.rec_gpu_score, req.rec_ram_gb
    if calidad == 'medium':
        return (req.min_cpu_score * MEDIO_NUM // MEDIO_DEN, req.min_gpu_score * MEDIO_NUM // MEDIO_DEN, req.min_ram_gb)
    return req.min_cpu_score, req.min_gpu_score, req.min_ram_gb


def _fps(sistema, calidad, exigido_cpu, exigido_gpu):
    candidatos = [FPS_BASE[calidad] * valor // exigido
                  for valor, exigido in ((sistema.cpu, exigido_cpu), (sistema.gpu, exigido_gpu))
                  if valor is not None and exigido]
    if not candidatos:
        return 0
    return max(FPS_MINIMO, min(FPS_MAXIMO, min(candidatos)))


def _limitante_si_corre(sistema, exigido_cpu, exigido_gpu, exigido_ram):
    if sistema.ram_gb is not None and sistema.ram_gb < exigido_ram:
        return 'ram'
    if sistema.cpu is None or sistema.gpu is None or not exigido_cpu or not exigido_gpu:
        return None
    # razones en fracciones para comparar con enteros: cpu/ec < 0,7 * gpu/eg
    if sistema.cpu * exigido_gpu * LIMITANTE_DEN < sistema.gpu * exigido_cpu * LIMITANTE_NUM:
        return 'cpu'
    if sistema.gpu * exigido_cpu * LIMITANTE_DEN < sistema.cpu * exigido_gpu * LIMITANTE_NUM:
        return 'gpu'
    return None


def _fallos_del_minimo(sistema, req):
    """Lista de (componente, razón respecto del mínimo, texto) de lo que no llega al mínimo."""
    fallos = []
    if sistema.cpu is not None and sistema.cpu < req.min_cpu_score:
        deficit = (req.min_cpu_score - sistema.cpu) * 100 // req.min_cpu_score
        fallos.append(('cpu', sistema.cpu / req.min_cpu_score, f'CPU insuficiente ({deficit}% por debajo del mínimo)'))
    if sistema.gpu is not None and sistema.gpu < req.min_gpu_score:
        deficit = (req.min_gpu_score - sistema.gpu) * 100 // req.min_gpu_score
        fallos.append(('gpu', sistema.gpu / req.min_gpu_score, f'GPU insuficiente ({deficit}% por debajo del mínimo)'))
    if sistema.ram_gb is not None and sistema.ram_gb < req.min_ram_gb:
        fallos.append(('ram', sistema.ram_gb / req.min_ram_gb,
                       f'RAM insuficiente (requiere {req.min_ram_gb}GB, tienes {sistema.ram_gb}GB)'))
    return fallos


def evaluar_juego(sistema, req):
    """Qué calidad y FPS logra el equipo en un juego, qué lo limita y por qué.

    Evalúa solo los componentes que se conocen (`parcial=True` si falta alguno): la tienda permite elegir,
    por ejemplo, solo la GPU. Devuelve `estado='sin_datos'` si el juego no tiene requisitos cargados o si no
    se conoce ningún componente.
    """
    if req is None or not getattr(req, 'min_cpu_score', 0) or not getattr(req, 'min_gpu_score', 0):
        return _sin_datos('El juego no tiene requisitos cargados')
    if len(sistema.faltantes) == 3:
        return _sin_datos('No hay datos de ningún componente')

    parcial = bool(sistema.faltantes)
    fallos = _fallos_del_minimo(sistema, req)
    if fallos:
        limitante = min(fallos, key=lambda f: f[1])[0]
        return {'estado': 'ok', 'puede_correr': False, 'calidad': 'none', 'fps': 0, 'limitante': limitante,
                'motivo': ' | '.join(f[2] for f in fallos), 'parcial': parcial}

    if sistema.desconocidos:
        # Lo que se conoce cumple el mínimo, pero falta saber si el componente desconocido también: no se confirma.
        return _sin_datos(f'No hay datos de: {", ".join(n.upper() for n in sistema.desconocidos)}')

    calidad = _calidad(sistema, req)
    exigido_cpu, exigido_gpu, exigido_ram = _requisitos_del_nivel(calidad, req)
    return {'estado': 'ok', 'puede_correr': True, 'calidad': calidad,
            'fps': _fps(sistema, calidad, exigido_cpu, exigido_gpu),
            'limitante': _limitante_si_corre(sistema, exigido_cpu, exigido_gpu, exigido_ram),
            'motivo': '', 'parcial': parcial}


CATEGORIA_POR_CALIDAD = {'ultra': 'can_run_ultra', 'high': 'can_run_high', 'medium': 'can_run_medium',
                         'low': 'can_run_low', 'none': 'cannot_run'}


def categoria_de(evaluacion):
    """Clave del grupo en que se muestra un juego (can_run_ultra ... cannot_run, sin_datos)."""
    if evaluacion['estado'] == SIN_DATOS:
        return SIN_DATOS
    return CATEGORIA_POR_CALIDAD[evaluacion['calidad']]


# --------------------------------------------------------- cuello de botella
def _resultado_base():
    return {'has_bottleneck': False, 'type': 'balanced', 'severity': 'none',
            'description': '', 'recommendations': [], 'percentage_loss': 0}


def _severidad_por_razon(mayor, menor):
    """None si la diferencia no llega a cuello de botella; si no, 'mild' | 'moderate' | 'severe'."""
    if mayor * 2 >= menor * RAZON_SEVERA:
        return 'severe'
    if mayor * 2 >= menor * RAZON_MODERADA:
        return 'moderate'
    if mayor * 2 >= menor * RAZON_LEVE:
        return 'mild'
    return None


def _cuello_cpu_gpu(sistema, resultado):
    mayor, menor = max(sistema.cpu, sistema.gpu), min(sistema.cpu, sistema.gpu)
    severidad = _severidad_por_razon(mayor, menor)
    if severidad is None:
        return
    debil, fuerte = ('CPU', 'GPU') if sistema.cpu < sistema.gpu else ('GPU', 'CPU')
    perdida = (100 * (mayor - menor) + mayor // 2) // mayor     # % de la capacidad del componente fuerte que se desperdicia
    adverbio = {'mild': 'algo', 'moderate': 'bastante', 'severe': 'mucho'}[severidad]
    resultado.update(
        has_bottleneck=True, type=debil.lower(), severity=severidad, percentage_loss=perdida,
        description=f'Tu {fuerte} es {adverbio} más potente que tu {debil}: solo se aprovecha ~{100 - perdida}% de su capacidad.',
    )
    objetivo = mayor * OBJETIVO_NUM // OBJETIVO_DEN
    resultado['recommendations'].append(f'💡 Un {debil} con puntuación de ~{objetivo} o más equilibraría tu sistema.')


def _cuello_ram(sistema, resultado):
    if sistema.ram_gb is None or sistema.ram_gb >= RAM_RECOMENDADA_GB:
        return
    severidad = 'moderate' if sistema.ram_gb < RAM_MINIMA_GB else 'mild'
    if not resultado['has_bottleneck']:
        resultado['has_bottleneck'] = True
        resultado['type'] = 'ram'
    # la RAM nunca baja la severidad de un cuello CPU/GPU que ya es más grave
    if ORDEN_SEVERIDAD[severidad] > ORDEN_SEVERIDAD[resultado['severity']]:
        resultado['severity'] = severidad
    resultado['description'] += (
        ('\n\n' if resultado['description'] else '')
        + f'⚠️ **RAM Insuficiente**\nSolo tienes {sistema.ram_gb}GB de RAM. Los juegos modernos recomiendan {RAM_RECOMENDADA_GB}GB.'
    )
    resultado['recommendations'].append(f'💾 Actualizar a {RAM_RECOMENDADA_GB}GB o 32GB de RAM para mejor rendimiento.')


def detectar_cuello(sistema):
    """Cuello de botella CPU/GPU (tres niveles, simétricos) y de RAM. Sin CPU o GPU con dato: `sin_datos`."""
    resultado = _resultado_base()
    if sistema.cpu is None or sistema.gpu is None:
        resultado.update(type=SIN_DATOS, description='No hay datos de benchmark suficientes para analizar.')
        return resultado
    _cuello_cpu_gpu(sistema, resultado)
    _cuello_ram(sistema, resultado)
    if not resultado['has_bottleneck']:
        resultado['description'] = ('✅ **¡Sistema Balanceado!**\n\n'
                                    'Tu configuración está bien equilibrada. No hay cuellos de botella significativos.')
    return resultado


# ------------------------------------------------------------ recomendaciones
def recomendaciones(sistema, cuello):
    """Recomendaciones del cuello de botella más las del nivel del sistema (sin repetir la de RAM)."""
    textos = list(cuello['recommendations']) if cuello['has_bottleneck'] else []
    total = puntuacion_total(sistema)
    if total is None:
        return textos
    if total < 7000:
        textos.append('💡 Tu sistema es entry-level. Considera actualizar GPU y CPU para mejor experiencia.')
    elif total < 10000:
        textos.append('💡 Tu sistema es mid-range. Una GPU mejor te daría un salto significativo en rendimiento.')
    if sistema.ram_gb is not None and sistema.ram_gb < RAM_RECOMENDADA_GB and not any('RAM' in t for t in textos):
        textos.append(f'💾 {RAM_RECOMENDADA_GB}GB de RAM es el estándar actual para gaming. Considera expandir.')
    return textos
