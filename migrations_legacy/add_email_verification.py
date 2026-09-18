"""
Migración: Agregar columnas para verificación de correo electrónico
Agrega: email_verified, verification_token, token_expiry a la tabla users
"""
import os
import sys
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from sqlalchemy import text

def run_migration():
    """Ejecutar migración para agregar columnas de verificación de email"""
    with app.app_context():
        try:
            print("="*60)
            print("MIGRACIÓN: Agregar Verificación de Email")
            print("="*60)
            
            # Verificar si las columnas ya existen
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name IN ('email_verified', 'verification_token', 'token_expiry')
            """)
            
            existing_columns = [row[0] for row in db.session.execute(check_query)]
            
            if len(existing_columns) == 3:
                print("✓ Las columnas ya existen. No se requiere migración.")
                return
            
            print("\n📝 Agregando columnas a la tabla 'users'...")
            
            # Agregar columna email_verified
            if 'email_verified' not in existing_columns:
                db.session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN email_verified BOOLEAN DEFAULT FALSE
                """))
                print("  ✓ Columna 'email_verified' agregada")
            
            # Agregar columna verification_token
            if 'verification_token' not in existing_columns:
                db.session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN verification_token VARCHAR(255)
                """))
                print("  ✓ Columna 'verification_token' agregada")
            
            # Agregar columna token_expiry
            if 'token_expiry' not in existing_columns:
                db.session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN token_expiry TIMESTAMP
                """))
                print("  ✓ Columna 'token_expiry' agregada")
            
            # Commit de los cambios
            db.session.commit()
            
            # Marcar usuarios existentes como verificados (opcional)
            print("\n📧 Marcando usuarios existentes como verificados...")
            db.session.execute(text("""
                UPDATE users 
                SET email_verified = TRUE 
                WHERE email_verified IS NULL OR email_verified = FALSE
            """))
            db.session.commit()
            print("  ✓ Usuarios existentes marcados como verificados")
            
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
