"""
Configuración de la base de datos
"""
import json
from datetime import datetime
from extensions import db
from utils.catalogo_hardware import CATALOGO_HARDWARE, RENOMBRES


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


def _hardware_desde_item(item):
    from models.database_models import Hardware
    return Hardware(
        tipo=item['tipo'], marca=item['marca'], modelo=item['modelo'], precio=item['precio'],
        descripcion=item['descripcion'], imagen=item['imagen'], stock=item['stock'],
        especificaciones=json.dumps(item['especificaciones'], ensure_ascii=False), **item['columnas'],
    )


def hardware_inicial():
    """Componentes del catálogo (objetos sin agregar a la sesión)."""
    return [_hardware_desde_item(item) for item in CATALOGO_HARDWARE]


def _completar_hardware(hardware, item):
    """Completa un componente existente con los datos del catálogo sin tocar precio, stock ni descripción.

    El socket se normaliza siempre ("LGA 1700" -> "LGA1700"); el resto de columnas solo se llenan si están vacías, y a las
    especificaciones se les agregan las claves que falten (lo que el administrador ya editó se conserva).
    Devuelve True si cambió algo.
    """
    cambio = False
    for columna, valor in item['columnas'].items():
        if columna == 'socket' or not getattr(hardware, columna):
            if getattr(hardware, columna) != valor:
                setattr(hardware, columna, valor)
                cambio = True
    actuales = hardware.get_especificaciones()
    completas = {**item['especificaciones'], **{k: v for k, v in actuales.items() if k != 'socket'}}
    if completas != actuales:
        hardware.especificaciones = json.dumps(completas, ensure_ascii=False)
        cambio = True
    return cambio


def sincronizar_hardware():
    """Deja la base con el catálogo completo: agrega lo que falta y completa los datos de compatibilidad de lo existente.

    `seed_database` solo corre con la base vacía. Esta función es idempotente y devuelve
    {'agregados': [modelos nuevos], 'actualizados': [modelos existentes que cambiaron]}.
    """
    from models.database_models import Hardware
    for anterior, nuevo in RENOMBRES.items():
        existente = Hardware.query.filter_by(modelo=anterior).first()
        if existente and not Hardware.query.filter_by(tipo=existente.tipo, modelo=nuevo).first():
            existente.modelo = nuevo
    db.session.flush()

    actuales = {(h.tipo, h.modelo): h for h in Hardware.query.all()}
    agregados, actualizados = [], []
    for item in CATALOGO_HARDWARE:
        existente = actuales.get((item['tipo'], item['modelo']))
        if existente is None:
            db.session.add(_hardware_desde_item(item))
            agregados.append(item['modelo'])
        elif _completar_hardware(existente, item):
            actualizados.append(item['modelo'])
    db.session.commit()
    return {'agregados': agregados, 'actualizados': actualizados}


def seed_database():
    """Poblar la base de datos con datos iniciales"""
    from models.database_models import Game, User
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
    hardware_items = hardware_inicial()
    
    for hardware in hardware_items:
        db.session.add(hardware)
    
    db.session.commit()
    print("Base de datos poblada con éxito!")
