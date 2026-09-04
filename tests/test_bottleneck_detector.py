"""
Tests de BottleneckDetector.

Regresión del bug encontrado en revisión general del proyecto (2026-09-04):
`_update_result()` recibía los parámetros en un orden distinto al que
`_apply_thresholds()` los pasaba, así que `detect()` crasheaba con
`ValueError` cada vez que detectaba un desequilibrio real entre CPU y GPU.
El bug estaba oculto porque `controllers/hardware_analyzer.py` atrapa la
excepción con un `except Exception` genérico y cae a "sin cuello de
botella" en silencio.
"""
from utils.bottleneck_detector import BottleneckDetector


class FakeHardware:
    def __init__(self, benchmark_score, ram_gb=16):
        self.benchmark_score = benchmark_score
        self._ram_gb = ram_gb

    def get_ram_capacity_gb(self):
        return self._ram_gb


def test_detecta_cuello_de_botella_de_cpu_sin_crashear():
    """GPU muy superior al CPU: antes del fix, esto lanzaba ValueError."""
    cpu = FakeHardware(benchmark_score=9000)
    gpu = FakeHardware(benchmark_score=20000)
    ram = FakeHardware(benchmark_score=0)

    resultado = BottleneckDetector.detect(cpu, gpu, ram)

    assert resultado['has_bottleneck'] is True
    assert resultado['type'] == 'cpu'
    assert isinstance(resultado['description'], str) and resultado['description']
    assert resultado['recommendations']
    assert '{score}' not in resultado['recommendations'][0]


def test_detecta_cuello_de_botella_de_gpu_sin_crashear():
    """CPU muy superior a la GPU: mismo bug, dirección contraria."""
    cpu = FakeHardware(benchmark_score=20000)
    gpu = FakeHardware(benchmark_score=9000)
    ram = FakeHardware(benchmark_score=0)

    resultado = BottleneckDetector.detect(cpu, gpu, ram)

    assert resultado['has_bottleneck'] is True
    assert resultado['type'] == 'gpu'
    assert isinstance(resultado['description'], str) and resultado['description']


def test_sistema_balanceado_no_reporta_cuello_de_botella():
    cpu = FakeHardware(benchmark_score=10000)
    gpu = FakeHardware(benchmark_score=10500)
    ram = FakeHardware(benchmark_score=0, ram_gb=16)

    resultado = BottleneckDetector.detect(cpu, gpu, ram)

    assert resultado['has_bottleneck'] is False
    assert 'Balanceado' in resultado['description']


def test_ram_insuficiente_se_reporta_como_bottleneck():
    cpu = FakeHardware(benchmark_score=10000)
    gpu = FakeHardware(benchmark_score=10500)
    ram = FakeHardware(benchmark_score=0, ram_gb=8)

    resultado = BottleneckDetector.detect(cpu, gpu, ram)

    assert resultado['has_bottleneck'] is True
    assert 'RAM' in resultado['description']
