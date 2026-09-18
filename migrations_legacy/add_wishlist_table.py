"""
Migración: Agregar tabla wishlist
"""
import os
import sys
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from sqlalchemy import text

def run_migration():
    """Ejecutar migración para crear tabla wishlist"""
    with app.app_context():
        try:
            print("="*60)
            print("MIGRACIÓN: Crear Tabla Wishlist")
            print("="*60)
            print()
            
            # Verificar si la tabla ya existe
            check_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name = 'wishlist'
            """)
            
            existing_table = db.session.execute(check_query).first()
            
            if existing_table:
                print("✓ La tabla 'wishlist' ya existe. No se requiere migración.")
                return
            
            print("📝 Creando tabla 'wishlist'...")
            
            # Crear tabla wishlist
            create_table_query = text("""
                CREATE TABLE wishlist (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    product_id INTEGER NOT NULL,
                    product_type VARCHAR(20) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, product_id, product_type)
                )
            """)
            
            db.session.execute(create_table_query)
            db.session.commit()
            print("  ✓ Tabla 'wishlist' creada")
            
            # Crear índices
            print("\n📝 Creando índices...")
            
            create_index_query = text("""
                CREATE INDEX idx_wishlist_user_id ON wishlist(user_id);
                CREATE INDEX idx_wishlist_product ON wishlist(product_id, product_type);
            """)
            
            db.session.execute(create_index_query)
            db.session.commit()
            print("  ✓ Índices creados")
            
            print("\n" + "="*60)
            print("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
            print("="*60)
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERROR durante la migración: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    run_migration()
