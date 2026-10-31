"""
SmartBuildAdvisor: arma la mejor PC del catálogo para un presupuesto y un uso.

Es parte del motor único, no de la pantalla: usa `utils/hardware_engine.py` para el rendimiento y `utils/compatibilidad.py` para el
encaje, y es pura (sin Flask ni base de datos). La pantalla solo muestra lo que devuelve `armar_pc`.

Qué elige, en este orden:
  1. Solo PC completas (los 7 tipos), con stock, dentro del presupuesto y con TODAS las verificaciones en "ok". Una verificación
     "incompatible" descarta la combinación y una "sin_datos" también (no se recomienda lo que no se puede verificar).
  2. Si no existe ninguna así, acepta combinaciones con piezas "justa" (y lo advierte).
  3. Entre las candidatas, la que mejor corre los juegos del perfil: más puntos por calidad (ultra 4, alto 3, medio 2, bajo 1,
     no corre 0), luego más FPS, luego mayor puntuación del sistema y, a igualdad, la más barata.
Además dice cuánto más habría que gastar para subir de nivel y, si el presupuesto no alcanza, cuál es el mínimo.
"""
from utils.compatibilidad import INCOMPATIBLE, JUSTA, OK, SIN_DATOS, estado_general, verificar_configuracion
from utils.hardware_engine import evaluar_juego, nivel_del_sistema, puntuacion_total, sistema_de

TIPOS = ('CPU', 'Motherboard', 'RAM', 'GPU', 'Fuente de poder', 'Refrigeración', 'Gabinete')
PUNTOS_POR_CALIDAD = {'ultra': 4, 'high': 3, 'medium': 2, 'low': 1, 'none': 0}
_NOMBRE_CALIDAD = {'ultra': 'Ultra', 'high': 'Alto', 'medium': 'Medio', 'low': 'Bajo', 'none': 'no corren'}

PERFILES = {
    'gaming': {'etiqueta': 'Gaming (todos los juegos)', 'filtro': lambda juego: True},
    'esports': {'etiqueta': 'eSports (juegos FPS competitivos)', 'filtro': lambda juego: juego.genero == 'FPS'},
    'aaa': {'etiqueta': 'AAA y mundo abierto', 'filtro': lambda juego: juego.genero != 'FPS'},
}

_TOLERANCIA = 1e-9           # los precios son sumas de decimales: se compara el presupuesto con un margen mínimo


def _estado(verificaciones):
    """Peor estado de la lista; un `sin_datos` NO se toma como ok (no se recomienda lo que no se puede verificar)."""
    estados = {v['estado'] for v in verificaciones}
    if INCOMPATIBLE in estados:
        return INCOMPATIBLE
    if SIN_DATOS in estados:
        return SIN_DATOS
    return estado_general(verificaciones)


def _evaluar_perfil(sistema, perfil):
    """(puntos, fps, juegos) del equipo en los juegos del perfil; un juego sin requisitos no suma ni resta."""
    puntos, fps, detalle = 0, 0, []
    for juego in perfil:
        e = evaluar_juego(sistema, juego.requisitos)
        detalle.append({'nombre': juego.nombre, 'calidad': e['calidad'], 'fps': e['fps'], 'limitante': e['limitante'],
                        'motivo': e['motivo']})
        if e['estado'] != 'sin_datos':
            puntos += PUNTOS_POR_CALIDAD[e['calidad']]
            fps += e['fps']
    return puntos, fps, detalle


def _mas_baratas_por_estado(cpu, placa, gpu, fuentes, enfriadores, gabinetes):
    """Para una base (CPU, placa, GPU) la fuente, el enfriador y el gabinete más baratos de cada estado posible (ok / justa)."""
    por_fuente = []
    for f in fuentes:
        v = verificar_configuracion(cpu=cpu, gpu=gpu, fuente=f)
        if _estado(v) in (OK, JUSTA):
            por_fuente.append((float(f.precio), f, v))
    por_enfriador = []
    for e in enfriadores:
        v = verificar_configuracion(cpu=cpu, enfriador=e)
        if _estado(v) in (OK, JUSTA):
            por_enfriador.append((float(e.precio), e, v))
    mejores = {}
    for precio_e, e, v_e in por_enfriador:
        for g in gabinetes:
            v_g = verificar_configuracion(gabinete=g, placa=placa, gpu=gpu, enfriador=e)
            if _estado(v_g) not in (OK, JUSTA):
                continue
            for precio_f, f, v_f in por_fuente:
                v = v_f + v_e + v_g
                estado = _estado(v)
                precio = precio_f + precio_e + float(g.precio)
                if estado not in mejores or precio < mejores[estado][0]:
                    mejores[estado] = (precio, f, e, g, v)
    return mejores


def _candidatas(por_tipo, perfil):
    """Todas las PC completas aceptables (ok o justa): para cada base, la variante más barata de cada estado."""
    for cpu in por_tipo['CPU']:
        for placa in por_tipo['Motherboard']:
            if _estado(verificar_configuracion(cpu=cpu, placa=placa)) != OK:
                continue
            for ram in por_tipo['RAM']:
                v_ram = verificar_configuracion(cpu=cpu, ram=ram, placa=placa)
                if _estado(v_ram) != OK:
                    continue
                for gpu in por_tipo['GPU']:
                    sistema = sistema_de(cpu, gpu, ram)
                    puntos, fps, juegos = _evaluar_perfil(sistema, perfil)
                    total = puntuacion_total(sistema) or 0
                    resto = _mas_baratas_por_estado(cpu, placa, gpu, por_tipo['Fuente de poder'], por_tipo['Refrigeración'],
                                                    por_tipo['Gabinete'])
                    for estado, (precio_resto, fuente, enfriador, gabinete, v_resto) in resto.items():
                        precio = round(float(cpu.precio) + float(placa.precio) + float(ram.precio) + float(gpu.precio) + precio_resto, 2)
                        yield {
                            'piezas': dict(zip(TIPOS, (cpu, placa, ram, gpu, fuente, enfriador, gabinete))),
                            'precio_total': precio, 'estado': estado,
                            'verificaciones': _unir(v_ram, v_resto),
                            'objetivo': {'puntos': puntos, 'fps': fps, 'total': total},
                            'sistema': sistema, 'juegos': juegos,
                        }


def _unir(*listas):
    """Une las verificaciones parciales sin repetir un par."""
    vistas, unidas = set(), []
    for lista in listas:
        for v in lista:
            if v['par'] not in vistas:
                vistas.add(v['par'])
                unidas.append(v)
    return unidas


def _clave(candidata):
    o = candidata['objetivo']
    return (o['puntos'], o['fps'], o['total'], -candidata['precio_total'])


def _resumen(c, presupuesto, perfil_etiqueta, desde):
    conteo = {}
    for j in c['juegos']:
        if j['calidad'] is not None:
            conteo[j['calidad']] = conteo.get(j['calidad'], 0) + 1
    partes = [f'{conteo[q]} en {_NOMBRE_CALIDAD[q]}' if q != 'none' else f'{conteo[q]} no corren'
              for q in ('ultra', 'high', 'medium', 'low', 'none') if q in conteo]
    texto = (f'Con ${presupuesto:.2f} armé una PC compatible de ${c["precio_total"]:.2f} para {perfil_etiqueta}: '
             f'{len(c["juegos"])} juegos, {", ".join(partes) or "sin datos de juegos"}. '
             f'Nivel del sistema: {nivel_del_sistema(c["objetivo"]["total"])}.')
    if desde < c['precio_total']:
        texto += f' La misma calidad en estos juegos se consigue desde ${desde:.2f}.'
    if c['estado'] == JUSTA:
        texto += ' Ojo: alguna pieza queda justa (sin holgura); revisa las verificaciones.'
    return texto


def armar_pc(piezas, juegos, presupuesto, uso='gaming'):
    """La mejor PC compatible del catálogo para `presupuesto` y `uso` (ver el docstring del módulo).

    `piezas`: objetos Hardware; `juegos`: objetos con `nombre`, `genero` y `requisitos` (GameRequirements o None).
    Devuelve un diccionario con `ok`; si `ok` es False trae `motivo` (y `precio_minimo` si el problema es el presupuesto).
    """
    if uso not in PERFILES:
        raise ValueError(f'Uso desconocido: {uso}')
    perfil = [j for j in juegos if PERFILES[uso]['filtro'](j)]
    base = {'uso': uso, 'presupuesto': presupuesto}

    por_tipo = {t: [p for p in piezas if p.tipo == t and (p.stock or 0) > 0] for t in TIPOS}
    faltan = [t for t, lista in por_tipo.items() if not lista]
    if faltan:
        return {**base, 'ok': False, 'motivo': f'No hay piezas con stock de: {", ".join(faltan)}.'}

    candidatas = list(_candidatas(por_tipo, perfil))
    if not candidatas:
        return {**base, 'ok': False, 'motivo': 'Ninguna combinación del catálogo es compatible entre sí.'}

    for aceptables in ({OK}, {OK, JUSTA}):
        dentro = [c for c in candidatas if c['estado'] in aceptables and c['precio_total'] <= presupuesto + _TOLERANCIA]
        if dentro:
            elegida = max(dentro, key=_clave)
            conjunto = [c for c in candidatas if c['estado'] in aceptables]
            break
    else:
        minimo = min(c['precio_total'] for c in candidatas)
        return {**base, 'ok': False, 'precio_minimo': minimo,
                'motivo': f'El presupuesto no alcanza: la PC compatible más barata del catálogo cuesta ${minimo:.2f}.'}

    desde = min(c['precio_total'] for c in conjunto if c['objetivo']['puntos'] >= elegida['objetivo']['puntos'])
    mejores = [c for c in conjunto if c['objetivo']['puntos'] > elegida['objetivo']['puntos']]
    siguiente = None
    if mejores:
        c = min(mejores, key=lambda x: (x['precio_total'], -x['objetivo']['puntos']))
        extra = round(c['precio_total'] - elegida['precio_total'], 2)
        siguiente = {'precio_extra': extra, 'precio_total': c['precio_total'], 'puntos': c['objetivo']['puntos'],
                     'texto': f'Con ${extra:.2f} más (${c["precio_total"]:.2f} en total) subirías de '
                              f'{elegida["objetivo"]["puntos"]} a {c["objetivo"]["puntos"]} puntos en los juegos del perfil.'}

    total = elegida['objetivo']['total']
    return {
        **base, 'ok': True, 'estado': elegida['estado'], 'piezas': elegida['piezas'],
        'precio_total': elegida['precio_total'], 'sobrante': round(presupuesto - elegida['precio_total'], 2),
        'verificaciones': elegida['verificaciones'], 'objetivo': elegida['objetivo'],
        'rendimiento': {'total': total, 'nivel': nivel_del_sistema(total)},
        'juegos': elegida['juegos'], 'siguiente': siguiente, 'desde': desde,
        'resumen': _resumen(elegida, presupuesto, PERFILES[uso]['etiqueta'], desde),
    }
