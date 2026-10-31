"""
Escala única de puntajes de benchmark del proyecto.

`Hardware.benchmark_score` (componentes) y `GameRequirements.*_score` (requisitos de los juegos) deben estar en la
MISMA escala, porque el motor (utils/hardware_engine.py) los compara directamente. Antes cada uno tenía su propia
escala curada a mano y no coincidían (un i5-12400F, que vale 9000, quedaba por debajo del "i7-4790" que Cyberpunk
pedía como recomendado, a 12000).

Cómo se obtiene un puntaje de una pieza, a partir de PassMark (consultado el 2026-10-30):
  CPU: puntaje = Single Thread Rating (cpubenchmark.net) x FACTOR_CPU
  GPU: puntaje = G3D Mark (videocardbenchmark.net)       x FACTOR_GPU
Los factores se anclan en las piezas del catálogo que ya tenían puntaje curado: i5-12400F (9000) y Ryzen 5 7600X
(10500) para la CPU, y RTX 4060 (12000) para la GPU. La regla reproduce esos puntajes con menos del 2 % de diferencia
(la GTX 1650 tenía un puntaje curado a un 3 %; hoy se deriva de la regla como el resto de piezas nuevas).

Las cifras de PassMark se actualizan a diario y pueden variar unos pocos puntos porcentuales.
"""

FACTOR_CPU = 2.56
FACTOR_GPU = 0.615

# PassMark "Single Thread Rating", cpubenchmark.net (2026-10-30; Ryzen 5 5600 y Core i7-13700K, de páginas de comparación de jun-jul 2026)
CPU_SINGLE_THREAD = {
    'Core 2 Quad Q6600': 953,
    'Core i5-750': 1222,
    'Core i5-2500K': 1697,
    'Core i5-3470': 1932,
    'Core i5-3570K': 2043,
    'Core i7-3770': 2070,
    'Core i7-4770K': 2160,
    'Core i5-4690': 2189,
    'Core i7-4790': 2226,
    'Core i3-6300': 2259,
    'Core i5-8400': 2364,
    'Ryzen 5 3600': 2558,
    'Core i7-8700K': 2713,
    'Ryzen 5 5600': 3255,
    'Core i5-12400F': 3485,
    'Ryzen 5 7600X': 4128,
    'Core i7-13700K': 4327,
}

# PassMark "Average G3D Mark", videocardbenchmark.net (2026-10-30; RTX 4070, de una comparación de mayo 2026)
GPU_G3D = {
    'GeForce 9800 GT': 442,
    'Radeon HD 4870': 1376,
    'GeForce GT 730': 835,
    'GeForce GTX 660': 4043,
    'Radeon HD 7870': 4564,
    'GeForce GTX 950': 5350,
    'GeForce GTX 770': 5963,
    'GeForce GTX 780': 7970,
    'GeForce GTX 1650': 7869,
    'Radeon RX 580': 8782,
    'GeForce GTX 970': 9640,
    'GeForce GTX 1060': 10016,
    'GeForce GTX 1070': 13511,
    'GeForce RTX 2060': 14081,
    'GeForce RTX 2060 Super': 16464,
    'GeForce GTX 1080 Ti': 18598,
    'GeForce RTX 4060': 19508,
    'GeForce RTX 3080': 24971,
    'GeForce RTX 4070': 26905,
}


def _a_decenas(valor):
    return int(round(valor / 10.0)) * 10


def puntaje_cpu(nombre):
    """Puntaje en la escala del proyecto de una CPU de CPU_SINGLE_THREAD."""
    return _a_decenas(CPU_SINGLE_THREAD[nombre] * FACTOR_CPU)


def puntaje_gpu(nombre):
    """Puntaje en la escala del proyecto de una GPU de GPU_G3D."""
    return _a_decenas(GPU_G3D[nombre] * FACTOR_GPU)


# Radeon RX 7600: las reseñas a 1080p la ubican entre un 3 % y un 8 % por detrás de la RTX 4060 (punto medio ~5 %).
PUNTAJE_RX_7600 = _a_decenas(puntaje_gpu('GeForce RTX 4060') * 0.95)
