"""
Script de migración para agregar tablas y campos del sistema de análisis de hardware
Ejecutar: python migrations/add_hardware_analysis_tables.py
"""
import sqlite3
import os

DEFAULT = 'INTEGER DEFAULT 0'

def migrate():
    """Ejecutar migración de base de datos"""
    # Crear directorio instance si no existe
    if not os.path.exists('instance'):
        os.makedirs('instance')
        print("✅ Directorio 'instance' creado")
    
    db_path = os.path.join('instance', 'gametech_store.db')
    
    # Si la base de datos no existe, crearla
    if not os.path.exists(db_path):
        print("⚠️  La base de datos no existe. Se creará una nueva...")
        # Crear archivo de base de datos vacío
        conn = sqlite3.connect(db_path)
        conn.close()
        print("✅ Base de datos creada")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🔄 Iniciando migración...")
        
        # 1. Crear tabla game_requirements
        print("\n📋 Creando tabla game_requirements...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_requirements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                requires_ssd BOOLEAN DEFAULT 0,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
            )
        ''')
        print("✅ Tabla game_requirements creada")
        
        # 2. Verificar columnas existentes en hardware
        print("\n🔍 Verificando columnas en tabla hardware...")
        cursor.execute("PRAGMA table_info(hardware)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        
        # 3. Agregar nuevas columnas a hardware
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
                    cursor.execute(f'ALTER TABLE hardware ADD COLUMN {column_name} {column_type}')
                    print(f"  ✅ Columna '{column_name}' agregada")
                except sqlite3.Error as e:
                    print(f"  ⚠️  Error al agregar '{column_name}': {e}")
            else:
                print(f"  ℹ️  Columna '{column_name}' ya existe")
        
        # 4. Crear índices para mejorar rendimiento
        print("\n🔧 Creando índices...")
        indices = [
            ('idx_game_requirements_game_id', 'game_requirements', 'game_id'),
            ('idx_hardware_benchmark', 'hardware', 'benchmark_score'),
            ('idx_hardware_tipo_benchmark', 'hardware', 'tipo, benchmark_score')
        ]
        
        for index_name, table_name, columns in indices:
            try:
                cursor.execute(f'''
                    CREATE INDEX IF NOT EXISTS {index_name} 
                    ON {table_name}({columns})
                ''')
                print(f"  ✅ Índice '{index_name}' creado")
            except sqlite3.Error as e:
                print(f"  ⚠️  Error al crear índice '{index_name}': {e}")
        
        # 5. Commit de cambios
        conn.commit()
        print("\n" + "="*60)
        print("✅ ¡Migración completada exitosamente!")
        print("="*60)
        print("\n📌 Próximos pasos:")
        print("  1. Ejecutar: python scripts/populate_hardware_benchmarks.py")
        print("  2. Ejecutar: python scripts/populate_game_requirements.py")
        
    except sqlite3.Error as e:
        print(f"\n❌ Error en la migración: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
