"""
Configuración de la base de datos
"""
from datetime import datetime
from extensions import db


def juegos_iniciales():
    """Juegos del catálogo (objetos sin agregar a la sesión)."""
    from models.database_models import Game
    return [
        Game(
            nombre="Cyberpunk 2077",
            descripcion="Un RPG de mundo abierto en Night City donde asumes el rol de V, un mercenario en busca de un implante único que es la clave de la inmortalidad.",
            precio=59.99,
            imagen="https://via.placeholder.com/400x300/667eea/ffffff?text=Cyberpunk+2077",
            genero="RPG",
            desarrollador="CD Projekt Red",
            fecha_lanzamiento=datetime(2020, 12, 10),
            requisitos_minimos='{"CPU": "Intel Core i5-3570K", "RAM": "8 GB", "GPU": "NVIDIA GeForce GTX 780", "Almacenamiento": "70 GB"}',
            requisitos_recomendados='{"CPU": "Intel Core i7-4790", "RAM": "16 GB", "GPU": "NVIDIA GeForce GTX 1060", "Almacenamiento": "70 GB"}',
            stock=50
        ),
        Game(
            nombre="The Witcher 3: Wild Hunt",
            descripcion="La aventura de Geralt de Rivia continúa en este épico RPG de mundo abierto. Caza monstruos, toma decisiones morales y explora un mundo vasto.",
            precio=39.99,
            imagen="https://via.placeholder.com/400x300/764ba2/ffffff?text=The+Witcher+3",
            genero="RPG",
            desarrollador="CD Projekt Red",
            fecha_lanzamiento=datetime(2015, 5, 19),
            requisitos_minimos='{"CPU": "Intel Core i5-2500K", "RAM": "6 GB", "GPU": "NVIDIA GeForce GTX 660", "Almacenamiento": "35 GB"}',
            requisitos_recomendados='{"CPU": "Intel Core i7-3770", "RAM": "8 GB", "GPU": "NVIDIA GeForce GTX 770", "Almacenamiento": "35 GB"}',
            stock=100
        ),
        Game(
            nombre="Grand Theft Auto V",
            descripcion="Mundo abierto en Los Santos. Experimenta la vida criminal desde tres perspectivas diferentes en esta obra maestra de Rockstar.",
            precio=29.99,
            imagen="https://via.placeholder.com/400x300/28a745/ffffff?text=GTA+V",
            genero="Acción",
            desarrollador="Rockstar Games",
            fecha_lanzamiento=datetime(2013, 9, 17),
            requisitos_minimos='{"CPU": "Intel Core 2 Quad Q6600", "RAM": "4 GB", "GPU": "NVIDIA GeForce 9800 GT", "Almacenamiento": "65 GB"}',
            requisitos_recomendados='{"CPU": "Intel Core i5-3470", "RAM": "8 GB", "GPU": "NVIDIA GeForce GTX 660", "Almacenamiento": "65 GB"}',
            stock=75
        ),
        Game(
            nombre="Counter-Strike 2",
            descripcion="El shooter táctico definitivo. Juego competitivo 5v5 con mecánicas precisas y mapas icónicos.",
            precio=0.00,
            imagen="https://via.placeholder.com/400x300/17a2b8/ffffff?text=Counter-Strike+2",
            genero="FPS",
            desarrollador="Valve",
            fecha_lanzamiento=datetime(2023, 9, 27),
            requisitos_minimos='{"CPU": "Intel Core i5-750", "RAM": "8 GB", "GPU": "NVIDIA GeForce GT 730", "Almacenamiento": "85 GB"}',
            requisitos_recomendados='{"CPU": "Intel Core i7-7700K", "RAM": "16 GB", "GPU": "NVIDIA GeForce RTX 2070", "Almacenamiento": "85 GB"}',
            stock=999
        ),
        Game(
            nombre="Elden Ring",
            descripcion="Un souls-like de mundo abierto creado por FromSoftware y George R.R. Martin. Explora las Tierras Intermedias.",
            precio=59.99,
            imagen="https://via.placeholder.com/400x300/ffc107/333333?text=Elden+Ring",
            genero="RPG",
            desarrollador="FromSoftware",
            fecha_lanzamiento=datetime(2022, 2, 25),
            requisitos_minimos='{"CPU": "Intel Core i5-8400", "RAM": "12 GB", "GPU": "NVIDIA GeForce GTX 1060", "Almacenamiento": "60 GB"}',
            requisitos_recomendados='{"CPU": "Intel Core i7-8700K", "RAM": "16 GB", "GPU": "NVIDIA GeForce GTX 1070", "Almacenamiento": "60 GB"}',
            stock=60
        ),
        Game(
            nombre="Red Dead Redemption 2",
            descripcion="Épica del Viejo Oeste de Rockstar: sigue a Arthur Morgan y a la banda de Van der Linde en su huida por un mundo abierto lleno de vida.",
            precio=59.99,
            imagen="https://via.placeholder.com/400x300/8b0000/ffffff?text=Red+Dead+Redemption+2",
            genero="Acción",
            desarrollador="Rockstar Games",
            fecha_lanzamiento=datetime(2019, 12, 5),
            requisitos_minimos='{"CPU": "Intel Core i5-2500K", "RAM": "8 GB", "GPU": "NVIDIA GeForce GTX 770 2GB", "Almacenamiento": "150 GB"}',
            requisitos_recomendados='{"CPU": "Intel Core i7-4770K", "RAM": "12 GB", "GPU": "NVIDIA GeForce GTX 1060 6GB", "Almacenamiento": "150 GB"}',
            stock=80
        ),
        Game(
            nombre="Baldur's Gate 3",
            descripcion="RPG por turnos de Larian Studios basado en Dungeons & Dragons: reúne a tu grupo, toma decisiones con consecuencias y enfrenta al Azotamentes.",
            precio=59.99,
            imagen="https://via.placeholder.com/400x300/4b0082/ffffff?text=Baldur%27s+Gate+3",
            genero="RPG",
            desarrollador="Larian Studios",
            fecha_lanzamiento=datetime(2023, 8, 3),
            requisitos_minimos='{"CPU": "Intel Core i5-4690", "RAM": "8 GB", "GPU": "NVIDIA GeForce GTX 970", "Almacenamiento": "150 GB (SSD)"}',
            requisitos_recomendados='{"CPU": "AMD Ryzen 5 3600", "RAM": "16 GB", "GPU": "NVIDIA GeForce RTX 2060 Super", "Almacenamiento": "150 GB (SSD)"}',
            stock=70
        ),
        Game(
            nombre="Apex Legends",
            descripcion="Battle royale de héroes gratuito de Respawn: elige una leyenda con habilidades únicas y compite en escuadras de tres.",
            precio=0.00,
            imagen="https://via.placeholder.com/400x300/c0392b/ffffff?text=Apex+Legends",
            genero="FPS",
            desarrollador="Respawn",
            fecha_lanzamiento=datetime(2020, 11, 4),
            requisitos_minimos='{"CPU": "Intel Core i3-6300", "RAM": "6 GB", "GPU": "NVIDIA GeForce GTX 950", "Almacenamiento": "75 GB"}',
            requisitos_recomendados='{"CPU": "AMD Ryzen 5 3600", "RAM": "8 GB", "GPU": "NVIDIA GeForce GTX 970", "Almacenamiento": "75 GB"}',
            stock=999
        )
    ]


def agregar_juegos_faltantes():
    """Agrega los juegos del catálogo que no existan (por nombre) y devuelve sus nombres.

    `seed_database` solo corre con la base vacía; esta función completa una base ya sembrada y no duplica si se repite.
    """
    from models.database_models import Game
    existentes = {nombre for (nombre,) in db.session.query(Game.nombre).all()}
    faltantes = [j for j in juegos_iniciales() if j.nombre not in existentes]
    db.session.add_all(faltantes)
    db.session.commit()
    return [j.nombre for j in faltantes]


def seed_database():
    """Poblar la base de datos con datos iniciales"""
    from models.database_models import Game, Hardware, User
    from werkzeug.security import generate_password_hash
    from os import environ
    # Crear usuario admin por defecto si no existe
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_password = environ.get('ADMIN_PASSWORD')
        if not admin_password:
            raise ValueError('ADMIN_PASSWORD environment variable is not set')
            
        admin = User(
            username='admin',
            email='admin@gametechstore.com',
            password_hash=generate_password_hash(admin_password),
            is_admin=True,  # Aseguramos que el usuario admin tenga permisos de administrador
            email_verified=True  # Cuenta de sistema creada por el propio backend, no requiere verificación
        )
        db.session.add(admin)
    
    # Agregar juegos
    juegos = juegos_iniciales()
    
    for juego in juegos:
        db.session.add(juego)
    
    # Agregar hardware
    hardware_items = [
        Hardware(
            tipo="CPU",
            marca="Intel",
            modelo="Core i5-12400F",
            precio=199.99,
            descripcion="Procesador de 12ª generación para gaming con 6 núcleos y 12 hilos. Excelente rendimiento en juegos y multitarea.",
            imagen="https://via.placeholder.com/400x300/0066cc/ffffff?text=Intel+i5-12400F",
            especificaciones='{"nucleos": 6, "hilos": 12, "frecuencia_base": "2.5 GHz", "frecuencia_boost": "4.4 GHz", "socket": "LGA 1700", "tdp": "65W"}',
            stock=30
        ),
        Hardware(
            tipo="CPU",
            marca="AMD",
            modelo="Ryzen 5 7600X",
            precio=299.99,
            descripcion="Procesador Zen 4 para alto rendimiento con arquitectura de 5nm. Ideal para gaming y creación de contenido.",
            imagen="https://via.placeholder.com/400x300/ed1c24/ffffff?text=AMD+Ryzen+5",
            especificaciones='{"nucleos": 6, "hilos": 12, "frecuencia_base": "4.7 GHz", "frecuencia_boost": "5.3 GHz", "socket": "AM5", "tdp": "105W"}',
            stock=25
        ),
        Hardware(
            tipo="GPU",
            marca="NVIDIA",
            modelo="RTX 4060",
            precio=399.99,
            descripcion="Tarjeta gráfica con Ray Tracing y DLSS 3. Perfecta para gaming en 1080p y 1440p con alto rendimiento.",
            imagen="https://via.placeholder.com/400x300/76b900/ffffff?text=RTX+4060",
            especificaciones='{"memoria": "8 GB GDDR6", "consumo": "115W", "puertos": "HDMI, DisplayPort x3", "cuda_cores": 3072}',
            stock=20
        ),
        Hardware(
            tipo="GPU",
            marca="AMD",
            modelo="RX 7600",
            precio=349.99,
            descripcion="Radeon con arquitectura RDNA 3. Excelente rendimiento por precio para gaming en 1080p.",
            imagen="https://via.placeholder.com/400x300/ed1c24/ffffff?text=RX+7600",
            especificaciones='{"memoria": "8 GB GDDR6", "consumo": "165W", "puertos": "HDMI, DisplayPort x3", "stream_processors": 2048}',
            stock=18
        ),
        Hardware(
            tipo="RAM",
            marca="Corsair",
            modelo="Vengeance LPX 16GB DDR4",
            precio=89.99,
            descripcion="Memoria de alto rendimiento para gaming con perfil bajo. Compatible con la mayoría de motherboards.",
            imagen="https://via.placeholder.com/400x300/ffcc00/333333?text=Corsair+RAM+16GB",
            especificaciones='{"capacidad": "16 GB", "tipo": "DDR4", "frecuencia": "3200 MHz", "latencia": "CL16", "modulos": "2x8GB"}',
            stock=50
        ),
        Hardware(
            tipo="RAM",
            marca="G.Skill",
            modelo="Trident Z RGB 32GB DDR4",
            precio=159.99,
            descripcion="Memoria RGB premium para entusiastas con iluminación personalizable y alto rendimiento.",
            imagen="https://via.placeholder.com/400x300/ff0000/ffffff?text=G.Skill+RAM+32GB",
            especificaciones='{"capacidad": "32 GB", "tipo": "DDR4", "frecuencia": "3600 MHz", "latencia": "CL18", "modulos": "2x16GB"}',
            stock=35
        ),
        Hardware(
            tipo="Motherboard",
            marca="ASUS",
            modelo="ROG Strix B450-F Gaming",
            precio=129.99,
            descripcion="Placa base ATX para AMD con soporte para Ryzen. Excelente para builds gaming de gama media.",
            imagen="https://via.placeholder.com/400x300/ff6600/ffffff?text=ASUS+B450",
            especificaciones='{"socket": "AM4", "formato": "ATX", "slots_ram": 4, "slots_pcie": "2 x PCIe 3.0 x16", "chipset": "B450"}',
            stock=15
        ),
        Hardware(
            tipo="Motherboard",
            marca="MSI",
            modelo="MAG B660M Mortar WiFi",
            precio=149.99,
            descripcion="Placa base micro-ATX para Intel con WiFi integrado. Perfecta para builds compactas.",
            imagen="https://via.placeholder.com/400x300/000000/ffffff?text=MSI+B660M",
            especificaciones='{"socket": "LGA 1700", "formato": "Micro-ATX", "slots_ram": 4, "slots_pcie": "1 x PCIe 4.0 x16", "chipset": "B660"}',
            stock=20
        )
    ]
    
    for hardware in hardware_items:
        db.session.add(hardware)
    
    db.session.commit()
    print("Base de datos poblada con éxito!")
