"""
Migración: Aumentar el campo imagen a 5000 caracteres
para soportar URLs largas e imágenes codificadas en base64
"""

from app import app
from database import db
from sqlalchemy import text
import os

def migrate_up():
    """Aumentar el tamaño del campo imagen en games y hardware"""
    with app.app_context():
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        is_postgresql = 'postgresql' in db_uri
        is_sqlite = 'sqlite' in db_uri
        
        print(f"🔍 Base de datos detectada: {'PostgreSQL' if is_postgresql else 'SQLite' if is_sqlite else 'Desconocida'}")
        
        if is_sqlite:
            migrate_sqlite()
        elif is_postgresql:
            migrate_postgresql()
        else:
            print("❌ Base de datos no soportada")

def migrate_sqlite():
    """Migración para SQLite"""
    try:
        # SQLite: usar PRAGMA para modificar tabla
        db.session.execute(text('PRAGMA foreign_keys=OFF'))
        
        # Game
        db.session.execute(text('ALTER TABLE game RENAME TO game_old'))
        db.session.execute(text('''
            CREATE TABLE game (
                id INTEGER PRIMARY KEY,
                nombre VARCHAR(200) NOT NULL,
                descripcion TEXT NOT NULL,
                precio FLOAT NOT NULL,
                imagen VARCHAR(5000),
                genero VARCHAR(50),
                desarrollador VARCHAR(100),
                fecha_lanzamiento DATETIME,
                requisitos_minimos TEXT,
                requisitos_recomendados TEXT,
                stock INTEGER DEFAULT 0,
                created_at DATETIME,
                updated_at DATETIME
            )
        '''))
        db.session.execute(text('INSERT INTO game SELECT * FROM game_old'))
        db.session.execute(text('DROP TABLE game_old'))
        
        # Hardware
        db.session.execute(text('ALTER TABLE hardware RENAME TO hardware_old'))
        db.session.execute(text('''
            CREATE TABLE hardware (
                id INTEGER PRIMARY KEY,
                tipo VARCHAR(50) NOT NULL,
                marca VARCHAR(100) NOT NULL,
                modelo VARCHAR(200) NOT NULL,
                precio FLOAT NOT NULL,
                descripcion TEXT,
                imagen VARCHAR(5000),
                especificaciones TEXT,
                stock INTEGER DEFAULT 0,
                benchmark_score INTEGER DEFAULT 0,
                vram_gb INTEGER DEFAULT 0,
                cores INTEGER DEFAULT 0,
                threads INTEGER DEFAULT 0,
                frequency_ghz FLOAT DEFAULT 0.0,
                created_at DATETIME,
                updated_at DATETIME
            )
        '''))
        db.session.execute(text('INSERT INTO hardware SELECT * FROM hardware_old'))
        db.session.execute(text('DROP TABLE hardware_old'))
        
        db.session.execute(text('PRAGMA foreign_keys=ON'))
        db.session.commit()
        print("✅ Migración SQLite completada: campo imagen aumentado a 5000 caracteres")
        
    except Exception as e:
        print(f"❌ Error en migración SQLite: {e}")
        db.session.rollback()

def migrate_postgresql():
    """Migración para PostgreSQL"""
    try:
        # Crear columna temporal con el nuevo tipo
        db.session.execute(text('ALTER TABLE game ADD COLUMN imagen_new VARCHAR(5000)'))
        db.session.execute(text('UPDATE game SET imagen_new = imagen'))
        db.session.execute(text('ALTER TABLE game DROP COLUMN imagen'))
        db.session.execute(text('ALTER TABLE game RENAME COLUMN imagen_new TO imagen'))
        
        db.session.execute(text('ALTER TABLE hardware ADD COLUMN imagen_new VARCHAR(5000)'))
        db.session.execute(text('UPDATE hardware SET imagen_new = imagen'))
        db.session.execute(text('ALTER TABLE hardware DROP COLUMN imagen'))
        db.session.execute(text('ALTER TABLE hardware RENAME COLUMN imagen_new TO imagen'))
        
        db.session.commit()
        print("✅ Migración PostgreSQL completada: campo imagen aumentado a 5000 caracteres")
        
    except Exception as e:
        print(f"⚠️ Advertencia en migración PostgreSQL: {e}")
        db.session.rollback()
        print("💡 Esto es esperado si ya está ejecutada o las tablas no existen")
        print("📝 Asegúrate de que tu BD está actualizada con las tablas correctas")

if __name__ == '__main__':
    migrate_up()


