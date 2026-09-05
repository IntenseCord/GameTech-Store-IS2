"""
Migración: Adaptar sistema de facturación de México a Colombia
"""
from app import app, db
from sqlalchemy import text

def migrate_invoices_to_colombia():
    """Migrar tabla de facturas a formato colombiano"""
    
    with app.app_context():
        print("🇨🇴 Iniciando migración a sistema colombiano...")
        
        try:
            # Agregar nuevas columnas colombianas
            migrations = [
                # Datos del receptor (Colombia)
                "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS nit_receptor VARCHAR(20)",
                "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS tipo_documento_receptor VARCHAR(10) DEFAULT '31'",
                "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS ciudad VARCHAR(100)",
                "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS departamento VARCHAR(100)",
                "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS telefono VARCHAR(20)",
                "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS email_receptor VARCHAR(200)",
                
                # Datos del emisor (Colombia)
                "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS nit_emisor VARCHAR(20) DEFAULT '900123456-7'",
                "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS regimen_emisor VARCHAR(50) DEFAULT 'Responsable de IVA'",
                
                # CUFE y QR (Colombia)
                "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS cufe TEXT",
                "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS qr_code TEXT",
                "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS fecha_validacion_dian TIMESTAMP",
            ]
            
            for migration in migrations:
                try:
                    db.session.execute(text(migration))
                    print(f"  ✅ {migration[:50]}...")
                except Exception as e:
                    if "already exists" in str(e) or "duplicate column" in str(e).lower():
                        print("  ⏭️  Columna ya existe, continuando...")
                    else:
                        print(f"  ⚠️  Error: {str(e)}")
            
            # Migrar datos existentes
            print("\n📦 Migrando datos existentes...")
            
            # Copiar RFC a NIT
            db.session.execute(text("""
                UPDATE invoices 
                SET nit_receptor = rfc_receptor 
                WHERE nit_receptor IS NULL AND rfc_receptor IS NOT NULL
            """))
            
            # Copiar email de usuarios
            db.session.execute(text("""
                UPDATE invoices 
                SET email_receptor = (
                    SELECT email FROM users WHERE users.id = invoices.user_id
                )
                WHERE email_receptor IS NULL
            """))
            
            # Actualizar razón social del emisor
            db.session.execute(text("""
                UPDATE invoices 
                SET razon_social_emisor = 'GameTech Store SAS'
                WHERE razon_social_emisor = 'GameTech Store SA de CV'
            """))
            
            # Actualizar fecha_validacion_dian
            db.session.execute(text("""
                UPDATE invoices 
                SET fecha_validacion_dian = fecha_timbrado
                WHERE fecha_validacion_dian IS NULL
            """))
            
            db.session.commit()
            print("✅ Migración completada exitosamente!")
            
            # Mostrar resumen
            result = db.session.execute(text("SELECT COUNT(*) FROM invoices"))
            total = result.scalar()
            print(f"\n📊 Total de facturas migradas: {total}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error en migración: {str(e)}")
            raise

if __name__ == '__main__':
    migrate_invoices_to_colombia()
