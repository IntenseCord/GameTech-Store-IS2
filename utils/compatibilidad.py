"""
Compatibilidad entre componentes: socket, memoria, fuente de poder, enfriador y gabinete.

Es parte del motor único de hardware: utils/hardware_engine.py opina sobre el RENDIMIENTO (puntajes, juegos, cuellos de
botella) y este módulo sobre el ENCAJE FÍSICO Y ELÉCTRICO. Como el motor, es puro (sin Flask ni base de datos): recibe
objetos `Hardware` (cualquier objeto con `tipo`, `modelo`, `socket`, `tdp_watts` y `get_especificaciones()`) y devuelve
diccionarios.

Cada verificación tiene un estado:
  ok            encaja con holgura.
  justa         encaja, pero sin margen: funcionará con riesgo (fuente sin holgura, enfriador que no aguanta el turbo).
  incompatible  no encaja o no funcionará.
  sin_datos     a una de las piezas le falta el dato necesario; NO es "incompatible": se dice que no se puede saber.

Regla de la fuente de poder: potencia requerida = max(fuente recomendada de la GPU, consumo máximo de la CPU + consumo de la
GPU + 100 W). Si la fuente no llega a esa potencia es incompatible; si no tiene un 20 % de holgura sobre ella, es justa.
"""
from dataclasses import dataclass

OK, JUSTA, INCOMPATIBLE, SIN_DATOS = 'ok', 'justa', 'incompatible', 'sin_datos'

# Campo de la API de cada tipo de componente.
CAMPOS_POR_TIPO = {
    'CPU': 'cpu_id', 'GPU': 'gpu_id', 'RAM': 'ram_id', 'Motherboard': 'placa_id',
    'Fuente de poder': 'fuente_id', 'Refrigeración': 'enfriador_id', 'Gabinete': 'gabinete_id',
}

RESTO_DE_SISTEMA_W = 100                 # discos, ventiladores y demás, sumados al consumo de CPU y GPU
HOLGURA_NUM, HOLGURA_DEN = 6, 5          # la fuente necesita un 20 % sobre la potencia requerida para no ser "justa"

_ORDEN = {SIN_DATOS: 0, OK: 1, JUSTA: 2, INCOMPATIBLE: 3}


@dataclass(frozen=True)
class Verificacion:
    par: str
    piezas: tuple
    estado: str
    mensaje: str

    def a_dict(self):
        return {'par': self.par, 'piezas': list(self.piezas), 'estado': self.estado, 'mensaje': self.mensaje}


def _nombre(pieza):
    return f'{pieza.marca} {pieza.modelo}'.strip()


def _sin_datos(par, piezas, mensaje):
    return Verificacion(par, piezas, SIN_DATOS, mensaje)


def _numero(pieza, clave):
    valor = pieza.get_especificaciones().get(clave)
    return valor if isinstance(valor, (int, float)) and not isinstance(valor, bool) else None


# ------------------------------------------------------------------- CPU y placa
def _cpu_placa(cpu, placa):
    par, piezas = 'cpu_placa', ('CPU', 'Motherboard')
    if not cpu.socket or not placa.socket:
        return _sin_datos(par, piezas, 'No se conoce el socket de ' + (_nombre(cpu) if not cpu.socket else _nombre(placa)) + '.')
    if cpu.socket == placa.socket:
        return Verificacion(par, piezas, OK, f'{_nombre(cpu)} y {_nombre(placa)} comparten el socket {cpu.socket}.')
    return Verificacion(par, piezas, INCOMPATIBLE,
                        f'{_nombre(cpu)} usa el socket {cpu.socket} y {_nombre(placa)} es {placa.socket}: no encajan.')


# ---------------------------------------------------------------------- memoria
def _tipo_ram(ram):
    return ram.get_especificaciones().get('tipo')


def _ram_placa(ram, placa):
    par, piezas = 'ram_placa', ('RAM', 'Motherboard')
    tipo, de_la_placa = _tipo_ram(ram), placa.get_especificaciones().get('tipo_memoria')
    if not tipo or not de_la_placa:
        return _sin_datos(par, piezas, 'No se conoce el tipo de memoria de la RAM o de la placa.')
    if tipo == de_la_placa:
        return Verificacion(par, piezas, OK, f'La placa usa {de_la_placa} y la RAM es {tipo}.')
    return Verificacion(par, piezas, INCOMPATIBLE, f'La placa {_nombre(placa)} usa {de_la_placa} y la RAM es {tipo}: no son compatibles.')


def _cpu_ram(cpu, ram):
    par, piezas = 'cpu_ram', ('CPU', 'RAM')
    tipo, aceptadas = _tipo_ram(ram), cpu.get_especificaciones().get('tipos_memoria')
    if not tipo or not aceptadas:
        return _sin_datos(par, piezas, 'No se conoce la memoria que acepta la CPU o el tipo de la RAM.')
    if tipo in aceptadas:
        return Verificacion(par, piezas, OK, f'{_nombre(cpu)} acepta memoria {tipo}.')
    return Verificacion(par, piezas, INCOMPATIBLE,
                        f'{_nombre(cpu)} solo acepta {" o ".join(aceptadas)} y la RAM es {tipo}.')


# ----------------------------------------------------------------------- fuente
def potencia_requerida(cpu, gpu):
    """Vatios mínimos de la fuente para esta CPU y GPU, o None si falta algún dato de consumo."""
    maximo_cpu = _numero(cpu, 'potencia_maxima_w')
    consumo_gpu = gpu.tdp_watts
    if not maximo_cpu or not consumo_gpu:
        return None
    return max(_numero(gpu, 'psu_recomendada_w') or 0, maximo_cpu + consumo_gpu + RESTO_DE_SISTEMA_W)


def _fuente(fuente, cpu, gpu):
    par, piezas = 'fuente', ('Fuente de poder', 'CPU', 'GPU')
    potencia, requerida = _numero(fuente, 'potencia_w'), potencia_requerida(cpu, gpu)
    if potencia is None or requerida is None:
        return _sin_datos(par, piezas, 'No se conoce la potencia de la fuente o el consumo de la CPU o la GPU.')
    if potencia < requerida:
        return Verificacion(par, piezas, INCOMPATIBLE,
                            f'La configuración necesita al menos {requerida} W y la fuente es de {potencia:g} W.')
    if potencia * HOLGURA_DEN < requerida * HOLGURA_NUM:
        return Verificacion(par, piezas, JUSTA,
                            f'La fuente de {potencia:g} W alcanza los {requerida} W necesarios pero sin un 20 % de holgura.')
    return Verificacion(par, piezas, OK, f'La fuente de {potencia:g} W cubre con holgura los {requerida} W necesarios.')


# --------------------------------------------------------------------- enfriador
def _enfriador_cpu(enfriador, cpu):
    par, piezas = 'enfriador_cpu', ('Refrigeración', 'CPU')
    specs = enfriador.get_especificaciones()
    sockets, tdp_max = specs.get('sockets'), _numero(enfriador, 'tdp_max_w')
    maximo_cpu, tdp_cpu = _numero(cpu, 'potencia_maxima_w'), cpu.tdp_watts
    if not cpu.socket or not sockets or tdp_max is None or not maximo_cpu or not tdp_cpu:
        return _sin_datos(par, piezas, 'No se conoce el socket o el consumo de la CPU, o lo que soporta el enfriador.')
    if cpu.socket not in sockets:
        return Verificacion(par, piezas, INCOMPATIBLE,
                            f'{_nombre(enfriador)} no soporta el socket {cpu.socket} de la CPU (soporta {", ".join(sockets)}).')
    if tdp_max >= maximo_cpu:
        return Verificacion(par, piezas, OK, f'{_nombre(enfriador)} disipa hasta {tdp_max:g} W y la CPU consume hasta {maximo_cpu:g} W.')
    if tdp_max >= tdp_cpu:
        return Verificacion(par, piezas, JUSTA,
                            f'{_nombre(enfriador)} disipa {tdp_max:g} W: cubre el TDP base ({tdp_cpu} W) pero no el consumo '
                            f'máximo con turbo ({maximo_cpu:g} W).')
    return Verificacion(par, piezas, INCOMPATIBLE,
                        f'{_nombre(enfriador)} disipa {tdp_max:g} W y la CPU tiene un TDP de {tdp_cpu} W.')


# --------------------------------------------------------------------- gabinete
def _gabinete_placa(gabinete, placa):
    par, piezas = 'gabinete_placa', ('Gabinete', 'Motherboard')
    formatos, formato = gabinete.get_especificaciones().get('formatos_placa'), placa.get_especificaciones().get('formato')
    if not formatos or not formato:
        return _sin_datos(par, piezas, 'No se conoce el formato de la placa o los que acepta el gabinete.')
    if formato in formatos:
        return Verificacion(par, piezas, OK, f'El gabinete acepta placas {formato}.')
    return Verificacion(par, piezas, INCOMPATIBLE,
                        f'La placa es {formato} y {_nombre(gabinete)} solo acepta {", ".join(formatos)}.')


def _gabinete_gpu(gabinete, gpu):
    par, piezas = 'gabinete_gpu', ('Gabinete', 'GPU')
    maximo, largo = _numero(gabinete, 'largo_max_gpu_mm'), _numero(gpu, 'largo_mm')
    if maximo is None or largo is None:
        return _sin_datos(par, piezas, 'No se conoce el largo de la GPU o el máximo que acepta el gabinete.')
    if largo <= maximo:
        return Verificacion(par, piezas, OK, f'La GPU mide {largo:g} mm y el gabinete admite hasta {maximo:g} mm.')
    return Verificacion(par, piezas, INCOMPATIBLE, f'La GPU mide {largo:g} mm y el gabinete admite hasta {maximo:g} mm.')


def _gabinete_enfriador(gabinete, enfriador):
    par, piezas = 'gabinete_enfriador', ('Gabinete', 'Refrigeración')
    specs = enfriador.get_especificaciones()
    if specs.get('tipo') == 'Líquida':
        radiador, maximo = _numero(enfriador, 'radiador_mm'), _numero(gabinete, 'radiador_max_mm')
        if radiador is None or maximo is None:
            return _sin_datos(par, piezas, 'No se conoce el tamaño del radiador o lo que acepta el gabinete.')
        if maximo == 0:
            return Verificacion(par, piezas, INCOMPATIBLE, f'{_nombre(gabinete)} no declara soporte para radiadores de refrigeración líquida.')
        if radiador <= maximo:
            return Verificacion(par, piezas, OK, f'El radiador de {radiador:g} mm cabe (el gabinete admite hasta {maximo:g} mm).')
        return Verificacion(par, piezas, INCOMPATIBLE, f'El radiador de {radiador:g} mm no cabe: el gabinete admite hasta {maximo:g} mm.')
    altura, maximo = _numero(enfriador, 'altura_mm'), _numero(gabinete, 'altura_max_cooler_mm')
    if altura is None or maximo is None:
        return _sin_datos(par, piezas, 'No se conoce la altura del enfriador o la que acepta el gabinete.')
    if altura <= maximo:
        return Verificacion(par, piezas, OK, f'El enfriador mide {altura:g} mm y el gabinete admite hasta {maximo:g} mm.')
    return Verificacion(par, piezas, INCOMPATIBLE, f'El enfriador mide {altura:g} mm y el gabinete admite hasta {maximo:g} mm.')


# ------------------------------------------------------------------- conjunto
def verificar_configuracion(cpu=None, gpu=None, ram=None, placa=None, fuente=None, enfriador=None, gabinete=None):
    """Verifica cada par de piezas indicadas (`None` = no elegida; un par sin sus dos piezas no se evalúa)."""
    pares = (
        (_cpu_placa, cpu, placa), (_ram_placa, ram, placa), (_cpu_ram, cpu, ram),
        (_enfriador_cpu, enfriador, cpu),
        (_gabinete_placa, gabinete, placa), (_gabinete_gpu, gabinete, gpu), (_gabinete_enfriador, gabinete, enfriador),
    )
    verificaciones = []
    for funcion, a, b in pares:
        if a is not None and b is not None:
            verificaciones.append(funcion(a, b))
    if fuente is not None and cpu is not None and gpu is not None:
        verificaciones.append(_fuente(fuente, cpu, gpu))
    return [v.a_dict() for v in verificaciones]


def estado_general(verificaciones):
    """El peor estado de la lista (`sin_datos` solo si ninguna verificación pudo hacerse)."""
    if not verificaciones:
        return SIN_DATOS
    return max(verificaciones, key=lambda v: _ORDEN[v['estado']])['estado']
