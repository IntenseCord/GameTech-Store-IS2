RAM_16_GB = "16 GB"
STORAGE_70_GB = "70 GB"
STORAGE_85_GB = "85 GB"

class Game:
    """Modelo para juegos"""

    def __init__(self, id, nombre, descripcion, precio, imagen, genero, desarrollador,
                 fecha_lanzamiento, requisitos_minimos, requisitos_recomendados):
        self.id = id
        self.nombre = nombre
        self.descripcion = descripcion
        self.precio = precio
        self.imagen = imagen
        self.genero = genero
        self.desarrollador = desarrollador
        self.fecha_lanzamiento = fecha_lanzamiento
        self.requisitos_minimos = requisitos_minimos  # dict con CPU, RAM, GPU, etc.
        self.requisitos_recomendados = requisitos_recomendados  # dict con CPU, RAM, GPU, etc.

    @classmethod
    def get_all_games(cls):
        """Obtener todos los juegos disponibles"""
        # Datos de ejemplo - en producción esto vendría de una base de datos
        juegos = [
            Game(
                id=1,
                nombre="Cyberpunk 2077",
                descripcion="Un RPG de mundo abierto en Night City",
                precio=59.99,
                imagen="/static/images/cyberpunk.jpg",
                genero="RPG",
                desarrollador="CD Projekt Red",
                fecha_lanzamiento="2020-12-10",
                requisitos_minimos={
                    "CPU": "Intel Core i5-3570K",
                    "RAM": "8 GB",
                    "GPU": "NVIDIA GeForce GTX 780",
                    "Almacenamiento": STORAGE_70_GB
                },
                requisitos_recomendados={
                    "CPU": "Intel Core i7-4790",
                    "RAM": RAM_16_GB,
                    "GPU": "NVIDIA GeForce GTX 1060",
                    "Almacenamiento": STORAGE_70_GB
                }
            ),
            Game(
                id=2,
                nombre="The Witcher 3: Wild Hunt",
                descripcion="La aventura de Geralt de Rivia continúa",
                precio=39.99,
                imagen="/static/images/witcher3.jpg",
                genero="RPG",
                desarrollador="CD Projekt Red",
                fecha_lanzamiento="2015-05-19",
                requisitos_minimos={
                    "CPU": "Intel Core i5-2500K",
                    "RAM": "6 GB",
                    "GPU": "NVIDIA GeForce GTX 660",
                    "Almacenamiento": "35 GB"
                },
                requisitos_recomendados={
                    "CPU": "Intel Core i7-3770",
                    "RAM": "8 GB",
                    "GPU": "NVIDIA GeForce GTX 770",
                    "Almacenamiento": "35 GB"
                }
            ),
            Game(
                id=3,
                nombre="Grand Theft Auto V",
                descripcion="Mundo abierto en Los Santos",
                precio=29.99,
                imagen="/static/images/gtav.jpg",
                genero="Acción",
                desarrollador="Rockstar Games",
                fecha_lanzamiento="2013-09-17",
                requisitos_minimos={
                    "CPU": "Intel Core 2 Quad Q6600",
                    "RAM": "4 GB",
                    "GPU": "NVIDIA GeForce 9800 GT",
                    "Almacenamiento": "65 GB"
                },
                requisitos_recomendados={
                    "CPU": "Intel Core i5-3470",
                    "RAM": "8 GB",
                    "GPU": "NVIDIA GeForce GTX 660",
                    "Almacenamiento": "65 GB"
                }
            ),
            Game(
                id=4,
                nombre="Counter-Strike 2",
                descripcion="El shooter táctico definitivo",
                precio=0.00,  # Free to play
                imagen="/static/images/cs2.jpg",
                genero="FPS",
                desarrollador="Valve",
                fecha_lanzamiento="2023-09-27",
                requisitos_minimos={
                    "CPU": "Intel Core i5-750",
                    "RAM": "8 GB",
                    "GPU": "NVIDIA GeForce GT 730",
                    "Almacenamiento": STORAGE_85_GB
                },
                requisitos_recomendados={
                    "CPU": "Intel Core i7-7700K",
                    "RAM": RAM_16_GB,
                    "GPU": "NVIDIA GeForce RTX 2070",
                    "Almacenamiento": STORAGE_85_GB
                }
            ),
            Game(
                id=5,
                nombre="Elden Ring",
                descripcion="Un souls-like de mundo abierto",
                precio=59.99,
                imagen="/static/images/eldenring.jpg",
                genero="RPG",
                desarrollador="FromSoftware",
                fecha_lanzamiento="2022-02-25",
                requisitos_minimos={
                    "CPU": "Intel Core i5-8400",
                    "RAM": "12 GB",
                    "GPU": "NVIDIA GeForce GTX 1060",
                    "Almacenamiento": "60 GB"
                },
                requisitos_recomendados={
                    "CPU": "Intel Core i7-8700K",
                    "RAM": RAM_16_GB,
                    "GPU": "NVIDIA GeForce GTX 1070",
                    "Almacenamiento": "60 GB"
                }
            )
        ]
        return juegos

    @classmethod
    def get_game_by_id(cls, game_id):
        """Obtener un juego por su ID"""
        juegos = cls.get_all_games()
        return next((juego for juego in juegos if juego.id == game_id), None)

    @classmethod
    def search_games(cls, query):
        """Buscar juegos por nombre, descripción o desarrollador"""
        if not query:
            return []
        
        query_lower = query.lower()
        juegos = cls.get_all_games()
        resultados = []
        
        for juego in juegos:
            # Buscar en nombre, descripción o desarrollador
            if (query_lower in juego.nombre.lower() or 
                query_lower in juego.descripcion.lower() or 
                query_lower in juego.desarrollador.lower()):
                resultados.append(juego)
        
        return resultados

    @classmethod
    def get_games_by_hardware(cls, hardware_specs):
        """Obtener juegos compatibles con el hardware especificado"""
        juegos = cls.get_all_games()
        juegos_compatibles = []

        for juego in juegos:
            if cls._es_compatible(juego.requisitos_minimos, hardware_specs):
                juegos_compatibles.append(juego)

        return juegos_compatibles

    @classmethod
    def _es_compatible(cls, requisitos_juego, hardware_usuario):
        """Verificar si el hardware del usuario cumple con los requisitos mínimos"""
        # Esta es una comparación simplificada - en producción sería más sofisticada
        # Comparar CPU (simplificado)
        if not cls._comparar_componente(hardware_usuario.get('cpu'), requisitos_juego.get('CPU')):
            return False

        # Comparar RAM
        ram_usuario = cls._extraer_numero(hardware_usuario.get('ram', '0 GB'))
        ram_requerida = cls._extraer_numero(requisitos_juego.get('RAM', '0 GB'))
        if ram_usuario < ram_requerida:
            return False

        # Comparar GPU (simplificado)
        if not cls._comparar_componente(hardware_usuario.get('gpu'), requisitos_juego.get('GPU')):
            return False

        return True

    @classmethod
    def _comparar_componente(cls, componente_usuario, componente_requerido):
        """Comparar componentes de hardware (simplificado)"""
        if not componente_usuario or not componente_requerido:
            return True  # Si falta información, asumir compatible

        # Esta es una comparación muy básica - en producción sería más avanzada
        return componente_usuario.lower() in componente_requerido.lower()

    @classmethod
    def _extraer_numero(cls, texto):
        """Extraer número de texto como '8 GB'"""
        import re
        numeros = re.findall(r'\d+', str(texto))
        return int(numeros[0]) if numeros else 0
