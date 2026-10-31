"""
Catálogo de hardware de la tienda: 7 tipos x 4 opciones (datos puros, sin Flask ni base de datos).

Cada componente trae, además de lo que muestra la tienda, los datos que usa el motor de compatibilidad:
  CPU          socket (columna), potencia_maxima_w (consumo con turbo) y tipos_memoria que acepta.
  GPU          consumo (tdp_watts), largo_mm y psu_recomendada_w (fabricante o reseñas, ver `largo_mm`).
  RAM          tipo (DDR4/DDR5) y capacidad.
  Motherboard  socket (columna), formato y tipo_memoria.
  Fuente       potencia_w.
  Refrigeración tipo (Aire/Líquida), tdp_max_w, sockets que soporta y altura_mm (aire) o radiador_mm (líquida).
  Gabinete     formatos_placa, largo_max_gpu_mm, altura_max_cooler_mm y radiador_max_mm (0 = sin soporte declarado).

Origen de los datos (consultados el 2026-10-30):
  - CPU/GPU: puntaje en la escala única (utils/benchmark_escala.py); consumo, memoria y sockets de AMD, Intel y NVIDIA.
  - largo_mm de las GPU: longitud del diseño de referencia (RTX 4060 240, RTX 4070 244, RX 7600 204); la GTX 1650 no tiene
    diseño de referencia y se usa 229 mm, el valor de un agregador, no de NVIDIA. Las versiones de los fabricantes varían.
  - Gabinetes y enfriadores de aire: especificaciones publicadas por el fabricante y tiendas.
  - TDP de los enfriadores líquidos: DeepCool no lo publica; LS520 = 260 W (agregador) y LS720 = 300 W es criterio del proyecto.
  - Precios: referencia del proyecto en USD (precio de lista de lanzamiento donde existe, si no un precio típico de tienda).
    No son precios de lista verificados: ajustar desde el panel de administración si hace falta.
"""
from utils.benchmark_escala import PUNTAJE_RX_7600, puntaje_cpu, puntaje_gpu

TIPOS = ('CPU', 'GPU', 'RAM', 'Motherboard', 'Fuente de poder', 'Refrigeración', 'Gabinete')

# Nombres anteriores de componentes que en realidad eran otra variante (ver sincronizar_hardware).
RENOMBRES = {'MAG B660M Mortar WiFi': 'MAG B660M Mortar WiFi DDR4'}

_SOCKETS_ENFRIADOR = ['LGA1700', 'AM4', 'AM5']


def _c(tipo, marca, modelo, precio, stock, descripcion, color, texto, especificaciones, **columnas):
    return {
        'tipo': tipo, 'marca': marca, 'modelo': modelo, 'precio': precio, 'stock': stock, 'descripcion': descripcion,
        'imagen': f'https://via.placeholder.com/400x300/{color}/ffffff?text={texto}',
        'especificaciones': especificaciones, 'columnas': columnas,
    }


CATALOGO_HARDWARE = [
    # ------------------------------------------------------------------ CPU
    _c('CPU', 'AMD', 'Ryzen 5 5600', 149.99, 28,
       'Procesador Zen 3 de 6 núcleos para la plataforma AM4. La opción más económica para jugar en 1080p.',
       'b22222', 'AMD+Ryzen+5+5600',
       {'nucleos': 6, 'hilos': 12, 'frecuencia_base': '3.5 GHz', 'frecuencia_boost': '4.4 GHz', 'socket': 'AM4', 'tdp': '65W',
        'potencia_maxima_w': 76, 'tipos_memoria': ['DDR4']},
       benchmark_score=puntaje_cpu('Ryzen 5 5600'), cores=6, threads=12, frequency_ghz=3.5, tdp_watts=65, socket='AM4'),
    _c('CPU', 'Intel', 'Core i5-12400F', 199.99, 30,
       'Procesador de 12ª generación para gaming con 6 núcleos y 12 hilos. Excelente rendimiento en juegos y multitarea.',
       '0066cc', 'Intel+i5-12400F',
       {'nucleos': 6, 'hilos': 12, 'frecuencia_base': '2.5 GHz', 'frecuencia_boost': '4.4 GHz', 'socket': 'LGA1700', 'tdp': '65W',
        'potencia_maxima_w': 117, 'tipos_memoria': ['DDR4', 'DDR5']},
       benchmark_score=9000, cores=6, threads=12, frequency_ghz=2.5, tdp_watts=65, socket='LGA1700'),
    _c('CPU', 'AMD', 'Ryzen 5 7600X', 299.99, 25,
       'Procesador Zen 4 para alto rendimiento con arquitectura de 5nm. Ideal para gaming y creación de contenido.',
       'ed1c24', 'AMD+Ryzen+5',
       {'nucleos': 6, 'hilos': 12, 'frecuencia_base': '4.7 GHz', 'frecuencia_boost': '5.3 GHz', 'socket': 'AM5', 'tdp': '105W',
        'potencia_maxima_w': 142, 'tipos_memoria': ['DDR5']},
       benchmark_score=10500, cores=6, threads=12, frequency_ghz=4.7, tdp_watts=105, socket='AM5'),
    _c('CPU', 'Intel', 'Core i7-13700K', 399.99, 15,
       'Procesador Raptor Lake de 16 núcleos (8 de rendimiento y 8 eficientes) para gaming extremo y creación de contenido.',
       '1e3a8a', 'Intel+i7-13700K',
       {'nucleos': 16, 'hilos': 24, 'frecuencia_base': '3.4 GHz', 'frecuencia_boost': '5.4 GHz', 'socket': 'LGA1700', 'tdp': '125W',
        'potencia_maxima_w': 253, 'tipos_memoria': ['DDR4', 'DDR5']},
       benchmark_score=puntaje_cpu('Core i7-13700K'), cores=16, threads=24, frequency_ghz=3.4, tdp_watts=125, socket='LGA1700'),

    # ------------------------------------------------------------------ GPU
    _c('GPU', 'NVIDIA', 'GTX 1650', 149.99, 25,
       'Tarjeta gráfica de entrada que no necesita conector de alimentación adicional. Para esports y juegos ligeros en 1080p.',
       '3f7d00', 'GTX+1650',
       {'memoria': '4 GB GDDR5', 'consumo': '75W', 'puertos': 'HDMI, DisplayPort, DVI', 'cuda_cores': 896,
        'largo_mm': 229, 'psu_recomendada_w': 300},
       benchmark_score=puntaje_gpu('GeForce GTX 1650'), vram_gb=4, tdp_watts=75),
    _c('GPU', 'AMD', 'RX 7600', 349.99, 18,
       'Radeon con arquitectura RDNA 3. Excelente rendimiento por precio para gaming en 1080p.',
       'ed1c24', 'RX+7600',
       {'memoria': '8 GB GDDR6', 'consumo': '165W', 'puertos': 'HDMI, DisplayPort x3', 'stream_processors': 2048,
        'largo_mm': 204, 'psu_recomendada_w': 550},
       benchmark_score=PUNTAJE_RX_7600, vram_gb=8, tdp_watts=165),
    _c('GPU', 'NVIDIA', 'RTX 4060', 399.99, 20,
       'Tarjeta gráfica con Ray Tracing y DLSS 3. Perfecta para gaming en 1080p y 1440p con alto rendimiento.',
       '76b900', 'RTX+4060',
       {'memoria': '8 GB GDDR6', 'consumo': '115W', 'puertos': 'HDMI, DisplayPort x3', 'cuda_cores': 3072,
        'largo_mm': 240, 'psu_recomendada_w': 550},
       benchmark_score=12000, vram_gb=8, tdp_watts=115),
    _c('GPU', 'NVIDIA', 'RTX 4070', 599.99, 12,
       'Tarjeta gráfica Ada Lovelace con 12 GB de memoria. Ray Tracing y DLSS 3 para jugar en 1440p con holgura.',
       '5a8f00', 'RTX+4070',
       {'memoria': '12 GB GDDR6X', 'consumo': '200W', 'puertos': 'HDMI, DisplayPort x3', 'cuda_cores': 5888,
        'largo_mm': 244, 'psu_recomendada_w': 650},
       benchmark_score=puntaje_gpu('GeForce RTX 4070'), vram_gb=12, tdp_watts=200),

    # ------------------------------------------------------------------ RAM
    _c('RAM', 'Corsair', 'Vengeance LPX 16GB DDR4', 89.99, 50,
       'Memoria de alto rendimiento para gaming con perfil bajo. Compatible con la mayoría de motherboards.',
       'ffcc00', 'Corsair+RAM+16GB',
       {'capacidad': '16 GB', 'tipo': 'DDR4', 'frecuencia': '3200 MHz', 'latencia': 'CL16', 'modulos': '2x8GB'}),
    _c('RAM', 'G.Skill', 'Trident Z RGB 32GB DDR4', 159.99, 35,
       'Memoria RGB premium para entusiastas con iluminación personalizable y alto rendimiento.',
       'ff0000', 'G.Skill+RAM+32GB',
       {'capacidad': '32 GB', 'tipo': 'DDR4', 'frecuencia': '3600 MHz', 'latencia': 'CL18', 'modulos': '2x16GB'}),
    _c('RAM', 'Corsair', 'Vengeance 16GB DDR5', 109.99, 40,
       'Memoria DDR5 de 16 GB (2x8GB) a 5600 MHz para las plataformas AM5 y Intel con DDR5.',
       'e6b800', 'Corsair+DDR5+16GB',
       {'capacidad': '16 GB', 'tipo': 'DDR5', 'frecuencia': '5600 MHz', 'latencia': 'CL36', 'modulos': '2x8GB'}),
    _c('RAM', 'Corsair', 'Vengeance 32GB DDR5', 199.99, 30,
       'Memoria DDR5 de 32 GB (2x16GB) a 6000 MHz con baja latencia para gaming y creación de contenido.',
       'd4a017', 'Corsair+DDR5+32GB',
       {'capacidad': '32 GB', 'tipo': 'DDR5', 'frecuencia': '6000 MHz', 'latencia': 'CL36', 'modulos': '2x16GB'}),

    # ----------------------------------------------------------- Motherboard
    _c('Motherboard', 'ASUS', 'ROG Strix B450-F Gaming', 129.99, 15,
       'Placa base ATX para AMD con soporte para Ryzen. Excelente para builds gaming de gama media.',
       'ff6600', 'ASUS+B450',
       {'socket': 'AM4', 'formato': 'ATX', 'slots_ram': 4, 'slots_pcie': '2 x PCIe 3.0 x16', 'chipset': 'B450',
        'tipo_memoria': 'DDR4'},
       socket='AM4'),
    _c('Motherboard', 'MSI', 'MAG B660M Mortar WiFi DDR4', 149.99, 20,
       'Placa base micro-ATX para Intel con WiFi integrado y memoria DDR4. Perfecta para builds compactas.',
       '000000', 'MSI+B660M',
       {'socket': 'LGA1700', 'formato': 'Micro-ATX', 'slots_ram': 4, 'slots_pcie': '1 x PCIe 4.0 x16', 'chipset': 'B660',
        'tipo_memoria': 'DDR4'},
       socket='LGA1700'),
    _c('Motherboard', 'MSI', 'MAG B650 Tomahawk WiFi', 219.99, 12,
       'Placa ATX para Ryzen serie 7000 con memoria DDR5, WiFi 6E y tres ranuras M.2.',
       'c0392b', 'MSI+B650',
       {'socket': 'AM5', 'formato': 'ATX', 'slots_ram': 4, 'slots_pcie': '1 x PCIe 4.0 x16', 'chipset': 'B650',
        'tipo_memoria': 'DDR5'},
       socket='AM5'),
    _c('Motherboard', 'MSI', 'MAG Z790 Tomahawk WiFi', 289.99, 10,
       'Placa ATX de gama alta para Intel de 12.ª a 14.ª generación, con DDR5 y WiFi 6E.',
       '2c3e50', 'MSI+Z790',
       {'socket': 'LGA1700', 'formato': 'ATX', 'slots_ram': 4, 'slots_pcie': '1 x PCIe 5.0 x16', 'chipset': 'Z790',
        'tipo_memoria': 'DDR5'},
       socket='LGA1700'),

    # -------------------------------------------------------- Fuente de poder
    _c('Fuente de poder', 'Corsair', 'CX550 550W', 59.99, 40,
       'Fuente de 550 W 80 PLUS Bronze, no modular. Suficiente para equipos de gama de entrada.',
       '444444', 'Corsair+CX550',
       {'potencia_w': 550, 'certificacion': '80 PLUS Bronze', 'modular': 'No modular', 'formato': 'ATX'}),
    _c('Fuente de poder', 'Corsair', 'RM650e 650W', 99.99, 30,
       'Fuente de 650 W 80 PLUS Gold totalmente modular, con modo de ventilador silencioso.',
       '555555', 'Corsair+RM650e',
       {'potencia_w': 650, 'certificacion': '80 PLUS Gold', 'modular': 'Totalmente modular', 'formato': 'ATX'}),
    _c('Fuente de poder', 'Corsair', 'RM750e 750W', 109.99, 25,
       'Fuente de 750 W 80 PLUS Gold totalmente modular para equipos de gama alta.',
       '666666', 'Corsair+RM750e',
       {'potencia_w': 750, 'certificacion': '80 PLUS Gold', 'modular': 'Totalmente modular', 'formato': 'ATX'}),
    _c('Fuente de poder', 'Corsair', 'RM850e 850W', 129.99, 20,
       'Fuente de 850 W 80 PLUS Gold totalmente modular, con holgura para GPU de alto consumo.',
       '777777', 'Corsair+RM850e',
       {'potencia_w': 850, 'certificacion': '80 PLUS Gold', 'modular': 'Totalmente modular', 'formato': 'ATX'}),

    # ----------------------------------------------------------- Refrigeración
    _c('Refrigeración', 'DeepCool', 'AK400', 29.99, 40,
       'Disipador de aire de torre simple con ventilador de 120 mm. Buena relación precio y temperatura.',
       '0e7490', 'DeepCool+AK400',
       {'tipo': 'Aire', 'tdp_max_w': 220, 'sockets': _SOCKETS_ENFRIADOR, 'altura_mm': 155, 'ventiladores': '1 x 120 mm'}),
    _c('Refrigeración', 'DeepCool', 'AK620', 64.99, 25,
       'Disipador de aire de doble torre con dos ventiladores de 120 mm para procesadores de alto consumo.',
       '0891b2', 'DeepCool+AK620',
       {'tipo': 'Aire', 'tdp_max_w': 260, 'sockets': _SOCKETS_ENFRIADOR, 'altura_mm': 160, 'ventiladores': '2 x 120 mm'}),
    _c('Refrigeración', 'DeepCool', 'LS520', 89.99, 18,
       'Refrigeración líquida todo en uno con radiador de 240 mm y dos ventiladores de 120 mm.',
       '0369a1', 'DeepCool+LS520',
       {'tipo': 'Líquida', 'tdp_max_w': 260, 'sockets': _SOCKETS_ENFRIADOR, 'radiador_mm': 240, 'ventiladores': '2 x 120 mm'}),
    _c('Refrigeración', 'DeepCool', 'LS720', 129.99, 12,
       'Refrigeración líquida todo en uno con radiador de 360 mm y tres ventiladores de 120 mm.',
       '075985', 'DeepCool+LS720',
       {'tipo': 'Líquida', 'tdp_max_w': 300, 'sockets': _SOCKETS_ENFRIADOR, 'radiador_mm': 360, 'ventiladores': '3 x 120 mm'}),

    # ---------------------------------------------------------------- Gabinete
    _c('Gabinete', 'Cooler Master', 'MasterBox Q300L', 49.99, 20,
       'Gabinete micro-ATX compacto con panel lateral acrílico. Ideal para equipos pequeños.',
       '7c3aed', 'Cooler+Master+Q300L',
       {'formatos_placa': ['Micro-ATX', 'Mini-ITX'], 'largo_max_gpu_mm': 360, 'altura_max_cooler_mm': 159,
        'radiador_max_mm': 0}),
    _c('Gabinete', 'NZXT', 'H5 Flow', 94.99, 18,
       'Gabinete ATX de torre media con frente perforado para un excelente flujo de aire.',
       '6d28d9', 'NZXT+H5+Flow',
       {'formatos_placa': ['ATX', 'Micro-ATX', 'Mini-ITX'], 'largo_max_gpu_mm': 365, 'altura_max_cooler_mm': 165,
        'radiador_max_mm': 280}),
    _c('Gabinete', 'Corsair', '4000D Airflow', 104.99, 22,
       'Gabinete ATX de torre media con panel frontal de alto flujo y espacio para radiador de 360 mm.',
       '5b21b6', 'Corsair+4000D',
       {'formatos_placa': ['ATX', 'Micro-ATX', 'Mini-ITX'], 'largo_max_gpu_mm': 360, 'altura_max_cooler_mm': 170,
        'radiador_max_mm': 360}),
    _c('Gabinete', 'Corsair', '5000D Airflow', 149.99, 10,
       'Gabinete ATX de torre media amplio, con espacio para tarjetas gráficas de hasta 420 mm.',
       '4c1d95', 'Corsair+5000D',
       {'formatos_placa': ['ATX', 'Micro-ATX', 'Mini-ITX'], 'largo_max_gpu_mm': 420, 'altura_max_cooler_mm': 170,
        'radiador_max_mm': 360}),
]
