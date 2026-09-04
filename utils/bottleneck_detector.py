"""
Detector de cuellos de botella en configuraciones de hardware
Analiza el balance entre CPU, GPU y RAM
"""
import re

class BottleneckDetector:
    """Detecta y analiza cuellos de botella en hardware"""
    
    # Umbrales de desequilibrio
    SEVERE_RATIO = 3.0   # 3x diferencia = severo
    MODERATE_RATIO = 2.0 # 2x diferencia = moderado
    MILD_RATIO = 1.5     # 1.5x diferencia = leve
    
    @staticmethod
    def detect(cpu, gpu, ram):
        """
        Detectar cuellos de botella.
        Args:
            cpu: Objeto Hardware de tipo CPU
            gpu: Objeto Hardware de tipo GPU
            ram: Objeto Hardware de tipo RAM
        Returns:
            dict con información del cuello de botella
        """
        result = BottleneckDetector._init_result()
        cpu_score = cpu.benchmark_score or 0
        gpu_score = gpu.benchmark_score or 0
        ram_gb = BottleneckDetector._extract_ram_gb(ram)

        if not BottleneckDetector._has_valid_scores(cpu_score, gpu_score, result):
            return result

        BottleneckDetector._detect_main_bottleneck(cpu_score, gpu_score, result)
        BottleneckDetector._check_ram_bottleneck(result, ram_gb)
        BottleneckDetector._check_balanced(result)
        return result

    # Métodos auxiliares sugeridos dentro de BottleneckDetector:
    @staticmethod
    def _has_valid_scores(cpu_score, gpu_score, result):
        if cpu_score == 0 or gpu_score == 0:
            result['description'] = 'No hay datos de benchmark suficientes para analizar.'
            return False
        return True

    @staticmethod
    def _detect_main_bottleneck(cpu_score, gpu_score, result):
        gpu_cpu_ratio = gpu_score / cpu_score if cpu_score else 0
        cpu_gpu_ratio = cpu_score / gpu_score if gpu_score else 0

        if BottleneckDetector._is_cpu_bottleneck(gpu_score, cpu_score):
            if BottleneckDetector._apply_thresholds(gpu_cpu_ratio,
                    BottleneckDetector._cpu_thresholds(),
                    result, cpu_score, gpu_score, is_cpu=True):
                result['has_bottleneck'] = True
                result['type'] = 'cpu'
        elif BottleneckDetector._is_gpu_bottleneck(gpu_score, cpu_score):
            if BottleneckDetector._apply_thresholds(cpu_gpu_ratio,
                    BottleneckDetector._gpu_thresholds(),
                    result, cpu_score, gpu_score, is_cpu=False):
                result['has_bottleneck'] = True
                result['type'] = 'gpu'

    @staticmethod
    def _apply_thresholds(ratio, thresholds, result, cpu_score, gpu_score, is_cpu):
        """
        Aplica los umbrales al ratio y actualiza el resultado si corresponde.
        Devuelve True si algún umbral se cumple, False si ninguno.
        """
        kind = 'cpu' if is_cpu else 'gpu'
        for threshold_data in thresholds:
            threshold = threshold_data[0]
            if ratio < threshold:
                continue
            BottleneckDetector._update_result(
                result,
                threshold_data[1],       # severity
                threshold_data[2],       # percent
                threshold_data[3],       # multiplier
                threshold_data[4],       # desc
                threshold_data[5],       # rec
                cpu_score,
                gpu_score,
                kind
            )
            return True
        return False


    # Métodos auxiliares sugeridos como métodos estáticos:
    @staticmethod
    def _init_result():
        return {
            'has_bottleneck': False, 'type': 'balanced', 'severity': 'none',
            'description': '', 'recommendations': [], 'percentage_loss': 0
       }

    @staticmethod
    def _update_result(result, severity, percent, multiplier, desc, rec, cpu_score, gpu_score, kind):
        result['severity'] = severity
        result['percentage_loss'] = percent
        result['description'] = desc
        if kind == 'cpu':
            result['recommendations'].append(rec.format(score=int(gpu_score * multiplier)))
        else:
            result['recommendations'].append(rec.format(score=int(cpu_score * multiplier)))

    @staticmethod
    def _cpu_thresholds():
        return [
            (1.5, "severe", 25, 0.4, "Tu GPU es muy superior...", "💡 Un CPU con score ~{score}+..."),
            (1.15, "moderate", 12, 0.6, "Tu GPU es ligeramente más potente...", "💡 Un CPU con score ~{score}+...")
            # ...otros thresholds según tu lógica
        ]

    @staticmethod
    def _gpu_thresholds():
        return [
            (1.15, "moderate", 13, 0.5, "Tu CPU es ligeramente más potente...", "💡 Una GPU con score ~{score}+...")
            # ...otros thresholds según tu lógica
        ]

    @staticmethod
    def _is_cpu_bottleneck(gpu_score, cpu_score):
        return gpu_score / cpu_score >= BottleneckDetector.MILD_RATIO

    @staticmethod
    def _is_gpu_bottleneck(gpu_score, cpu_score):
        return cpu_score / gpu_score >= BottleneckDetector.MILD_RATIO

    @staticmethod
    def _check_ram_bottleneck(result, ram_gb):
        if ram_gb < 16:
            result['has_bottleneck'] = True
            if result['type'] == 'balanced':
                result['type'] = 'ram'
            result['severity'] = 'moderate' if ram_gb < 8 else 'mild'
            result['description'] += (
                f'\n\n⚠️ **RAM Insuficiente**\n'
                f'Solo tienes {ram_gb}GB de RAM. Los juegos modernos recomiendan 16GB.\n'
                '**Impacto:** Posibles stutters y limitaciones en juegos exigentes.'
            )
            result['recommendations'].append(
                '💾 Actualizar a 16GB o 32GB de RAM para mejor rendimiento.'
            )

    @staticmethod
    def _check_balanced(result):
        if not result['has_bottleneck']:
            result['description'] = (
                '✅ **¡Sistema Balanceado!**\n\n'
                'Tu configuración está bien equilibrada. '
                'No hay cuellos de botella significativos.'
            )

        
    @staticmethod
    def _extract_ram_gb(ram):
        """Extraer capacidad de RAM en GB"""
        if hasattr(ram, 'get_ram_capacity_gb'):
            return ram.get_ram_capacity_gb()
        
        # Fallback: extraer de especificaciones
        specs = ram.get_especificaciones() if hasattr(ram, 'get_especificaciones') else {}
        capacity_str = specs.get('capacidad', '8 GB')
       
        match = re.search(r'(\d+)\s*GB', str(capacity_str), re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 8  # Default
