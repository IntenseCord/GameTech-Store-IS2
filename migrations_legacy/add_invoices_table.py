"""
Migración para agregar tabla de facturas y campos fiscales
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from sqlalchemy import text

def migrate():
    """Ejecutar migración"""
    with app.app_context():
        try:
            print("="*60)
            print("MIGRACIÓN: Sistema de Facturación")
            print("="*60)
            print()
            
            # 1. Agregar campos fiscales a users
            print("📝 Agregando campos fiscales a tabla users...")
            fiscal_fields = {
                'rfc': 'VARCHAR(13)',
                'razon_social': 'VARCHAR(200)',
                'direccion_fiscal': 'VARCHAR(300)',
                'codigo_postal': 'VARCHAR(10)',
                'regimen_fiscal': 'VARCHAR(100)'
            }
            
            for field_name, field_type in fiscal_fields.items():
                try:
                    db.session.execute(text(
                        f'ALTER TABLE users ADD COLUMN {field_name} {field_type}'
                    ))
                    db.session.commit()
                    print(f"  ✅ Campo '{field_name}' agregado")
                except Exception as e:
                    db.session.rollback()
                    if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                        print(f"  ℹ️  Campo '{field_name}' ya existe")
                    else:
                        print(f"  ⚠️  Error: {e}")
            
            # 2. Crear tabla invoices
            print("\n📋 Creando tabla invoices...")
            db.session.execute(text('''
                CREATE TABLE IF NOT EXISTS invoices (
                    id SERIAL PRIMARY KEY,
                    uuid VARCHAR(36) UNIQUE NOT NULL,
                    folio VARCHAR(50) NOT NULL,
                    
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    order_id INTEGER NOT NULL REFERENCES orders(id),
                    
                    rfc_receptor VARCHAR(13) NOT NULL,
                    razon_social_receptor VARCHAR(200) NOT NULL,
                    direccion_fiscal VARCHAR(300),
                    codigo_postal VARCHAR(10),
                    regimen_fiscal VARCHAR(100),
                    uso_cfdi VARCHAR(10) DEFAULT 'G03',
                    
                    rfc_emisor VARCHAR(13) DEFAULT 'GTS123456789',
                    razon_social_emisor VARCHAR(200) DEFAULT 'GameTech Store SA de CV',
                    
                    subtotal REAL NOT NULL,
                    iva REAL NOT NULL,
                    total REAL NOT NULL,
                    
                    metodo_pago VARCHAR(10) DEFAULT 'PUE',
                    forma_pago VARCHAR(10) DEFAULT '03',
                    
                    status VARCHAR(20) DEFAULT 'active',
                    fecha_emision TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fecha_timbrado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fecha_cancelacion TIMESTAMP,
                    
                    pdf_path VARCHAR(300),
                    xml_path VARCHAR(300),
                    
                    sello_digital TEXT,
                    cadena_original TEXT,
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''))
            db.session.commit()
            print("✅ Tabla invoices creada")
            
            # 3. Crear índices
            print("\n🔧 Creando índices...")
            indices = [
                ('idx_invoices_uuid', 'invoices', 'uuid'),
                ('idx_invoices_user_id', 'invoices', 'user_id'),
                ('idx_invoices_order_id', 'invoices', 'order_id'),
                ('idx_invoices_status', 'invoices', 'status')
            ]
            
            for index_name, table_name, columns in indices:
                try:
                    db.session.execute(text(
                        f'CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns})'
                    ))
                    db.session.commit()
                    print(f"  ✅ Índice '{index_name}' creado")
                except Exception as e:
                    db.session.rollback()
                    print(f"  ⚠️  Error: {e}")
            
            # 4. Crear directorio para PDFs
            print("\n📁 Creando directorios para archivos...")
            os.makedirs('static/invoices/pdf', exist_ok=True)
            os.makedirs('static/invoices/xml', exist_ok=True)
            print("✅ Directorios creados")
            
            print("\n" + "="*60)
            print("✅ ¡Migración completada exitosamente!")
            print("="*60)
            print("\n📌 Sistema de facturación listo para usar")
            
        except Exception as e:
            print(f"\n❌ Error en la migración: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            raise

if __name__ == '__main__':
    migrate()
