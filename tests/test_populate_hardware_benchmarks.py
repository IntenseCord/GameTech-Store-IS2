"""
Test de scripts/populate_hardware_benchmarks.py.

Regresión: `props_map` mapeaba columna->columna en vez de columna->clave
real de BENCHMARK_DATA (que usa 'freq'/'tdp'/'vram', no 'frequency_ghz'/
'tdp_watts'/'vram_gb'), así que `specs.get(prop, default)` siempre caía
en el default y frequency_ghz/tdp_watts/vram_gb quedaban en 0 para todo
el catálogo, sin importar los datos reales del script.
"""
from extensions import db
from models.database_models import Hardware
from scripts.populate_hardware_benchmarks import update_hardware_benchmarks


def test_actualiza_frequency_tdp_y_vram_no_solo_el_score(app_context):
    cpu = Hardware(
        tipo='CPU', marca='Intel', modelo='Core i5-12400F',
        precio=199.99, especificaciones='{}', stock=1
    )
    gpu = Hardware(
        tipo='GPU', marca='NVIDIA', modelo='RTX 4060',
        precio=399.99, especificaciones='{}', stock=1
    )
    db.session.add_all([cpu, gpu])
    db.session.commit()

    update_hardware_benchmarks()

    db.session.refresh(cpu)
    db.session.refresh(gpu)

    assert cpu.benchmark_score == 9000
    assert cpu.frequency_ghz == 2.5
    assert cpu.tdp_watts == 65
    assert cpu.cores == 6

    assert gpu.benchmark_score == 12000
    assert gpu.vram_gb == 8
    assert gpu.tdp_watts == 115
