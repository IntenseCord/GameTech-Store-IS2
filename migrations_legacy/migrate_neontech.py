"""
Script de migración para PostgreSQL (Neon Tech)
Agrega tablas y campos del sistema de análisis de hardware
"""
import sys
import os



# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from sqlalchemy import text

def migrate():
    """Ejecutar migración en PostgreSQL"""
    with app.app_context():
        try:
            print("="*60)
            print("MIGRACIÓN DE BASE DE DATOS - PostgreSQL (Neon Tech)")
            print("="*60)
            print()
            print("🔄 Iniciando migración...")
            
            # 1. Crear tabla game_requirements
            print("\n📋 Creando tabla game_requirements...")
            db.session.execute(text('''
                CREATE TABLE IF NOT EXISTS game_requirements (
                    id SERIAL PRIMARY KEY,
                    game_id INTEGER NOT NULL,
                    
                    -- Requisitos Mínimos (1080p Low, 30 FPS)
                    min_cpu_score INTEGER DEFAULT 0,
                    min_gpu_score INTEGER DEFAULT 0,
                    min_ram_gb INTEGER DEFAULT 8,
                    min_vram_gb INTEGER DEFAULT 2,
                    
                    -- Requisitos Recomendados (1080p High, 60 FPS)
                    rec_cpu_score INTEGER DEFAULT 0,
                    rec_gpu_score INTEGER DEFAULT 0,
                    rec_ram_gb INTEGER DEFAULT 16,
                    rec_vram_gb INTEGER DEFAULT 4,
                    
                    -- Requisitos Ultra (1440p/4K Ultra, 60+ FPS)
                    ultra_cpu_score INTEGER DEFAULT 0,
                    ultra_gpu_score INTEGER DEFAULT 0,
                    ultra_ram_gb INTEGER DEFAULT 32,
                    ultra_vram_gb INTEGER DEFAULT 8,
                    
                    -- Otros requisitos
                    storage_gb INTEGER DEFAULT 50,
                    directx_version VARCHAR(10) DEFAULT 'DX12',
                    requires_ssd BOOLEAN DEFAULT FALSE,
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
                )
            '''))
            db.session.commit()
            print("✅ Tabla game_requirements creada")
            
            # 2. Verificar si las columnas ya existen en hardware
            print("\n🔍 Verificando columnas en tabla hardware...")
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'hardware'
            """))
            existing_columns = [row[0] for row in result]
            
            # 3. Agregar nuevas columnas a hardware
            DEFAULT = 'INTEGER DEFAULT 0'
            columns_to_add = {
                'benchmark_score': DEFAULT,
                'vram_gb': DEFAULT,
                'cores': DEFAULT,
                'threads': DEFAULT,
                'frequency_ghz': 'REAL DEFAULT 0.0',
                'tdp_watts': DEFAULT,
                'socket': 'VARCHAR(50)',
                'generation': 'VARCHAR(50)',
                'architecture': 'VARCHAR(100)'
            }
            
            print("\n📝 Agregando columnas a tabla hardware...")
            for column_name, column_type in columns_to_add.items():
                if column_name not in existing_columns:
                    try:
                        db.session.execute(text(
                            f'ALTER TABLE hardware ADD COLUMN {column_name} {column_type}'
                        ))
                        db.session.commit()
                        print(f"  ✅ Columna '{column_name}' agregada")
                    except Exception as e:
                        db.session.rollback()
                        print(f"  ⚠️  Error al agregar '{column_name}': {e}")
                else:
                    print(f"  ℹ️  Columna '{column_name}' ya existe")
            
            # 4. Crear índices
            print("\n🔧 Creando índices...")
            indices = [
                ('idx_game_requirements_game_id', 'game_requirements', 'game_id'),
                ('idx_hardware_benchmark', 'hardware', 'benchmark_score'),
                ('idx_hardware_tipo_benchmark', 'hardware', 'tipo, benchmark_score')
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
                    print(f"  ⚠️  Error al crear índice '{index_name}': {e}")
            
            print("\n" + "="*60)
            print("✅ ¡Migración completada exitosamente!")
            print("="*60)
            print("\n📌 Próximos pasos:")
            print("  1. Ejecutar: python scripts/populate_hardware_benchmarks.py")
            print("  2. Ejecutar: python scripts/populate_game_requirements.py")
            
        except Exception as e:
            print(f"\n❌ Error en la migración: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            raise

if __name__ == '__main__':
    migrate()
