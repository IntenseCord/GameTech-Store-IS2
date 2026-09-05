# Migraciones de Base de Datos

## Sistema de Análisis de Hardware

Esta migración agrega las tablas y campos necesarios para el sistema de análisis de hardware y compatibilidad de juegos.

**Base de datos:** PostgreSQL (Neon Tech)

## Cambios Incluidos

### 1. Nueva Tabla: `game_requirements`
Almacena los requisitos de sistema para cada juego:
- Requisitos mínimos (1080p Low, 30 FPS)
- Requisitos recomendados (1080p High, 60 FPS)
- Requisitos ultra (1440p/4K Ultra, 60+ FPS)

### 2. Nuevas Columnas en `hardware`
- `benchmark_score`: Puntuación de rendimiento del componente
- `vram_gb`: VRAM para GPUs
- `cores`: Número de núcleos (CPUs)
- `threads`: Número de hilos (CPUs)
- `frequency_ghz`: Frecuencia en GHz (CPUs)
- `tdp_watts`: Consumo energético en watts
- `socket`: Socket del componente
- `generation`: Generación del componente
- `architecture`: Arquitectura del componente

### 3. Índices de Rendimiento
- Índice en `game_requirements.game_id`
- Índice en `hardware.benchmark_score`
- Índice compuesto en `hardware(tipo, benchmark_score)`

## Cómo Ejecutar la Migración

**Importante:** Asegúrate de tener configurada la variable `DATABASE_URL` en tu archivo `.env` con la URL de Neon Tech.

```bash
python run_migration.py
```

El script detectará automáticamente que estás usando PostgreSQL y ejecutará la migración correcta.

## Verificación

Después de ejecutar la migración, verifica que:
1. La tabla `game_requirements` existe
2. La tabla `hardware` tiene las nuevas columnas
3. No hay errores en la consola

## Próximos Pasos

Después de ejecutar esta migración:

1. **Poblar datos de benchmark:**
   ```bash
   python scripts/populate_hardware_benchmarks.py
   ```

2. **Poblar requisitos de juegos:**
   ```bash
   python scripts/populate_game_requirements.py
   ```

## Rollback

Si necesitas revertir los cambios en PostgreSQL:
```sql
-- Eliminar tabla
DROP TABLE IF EXISTS game_requirements;

-- Eliminar columnas de hardware (si es necesario)
ALTER TABLE hardware DROP COLUMN IF EXISTS benchmark_score;
ALTER TABLE hardware DROP COLUMN IF EXISTS vram_gb;
-- ... etc
```

**Recomendación:** Haz un backup de tu base de datos en Neon Tech antes de ejecutar la migración.

## Notas Importantes

- ⚠️ **Haz un backup** de tu base de datos antes de ejecutar la migración
- La migración es segura y no elimina datos existentes
- Solo agrega nuevas tablas y columnas
- Las columnas nuevas tienen valores por defecto
