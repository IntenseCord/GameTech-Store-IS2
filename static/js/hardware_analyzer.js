/**
 * Hardware Analyzer - Frontend Logic
 * Maneja el análisis de hardware y visualización de resultados
 */

// Estado global
let currentAnalysis = null;

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    const analyzeBtn = document.getElementById('analyze-btn');
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', analyzeHardware);
    }
});

/**
 * Función principal de análisis
 */
async function analyzeHardware() {
    const cpuId = document.getElementById('cpu-select').value;
    const gpuId = document.getElementById('gpu-select').value;
    const ramId = document.getElementById('ram-select').value;
    
    // Validar selección
    if (!cpuId || !gpuId || !ramId) {
        showAlert('Por favor selecciona todos los componentes (CPU, GPU y RAM)', 'warning');
        return;
    }
    
    // Mostrar loading
    showLoading(true);
    hideResults();
    
    const selectedComponents = {
        cpu_id: Number.parseInt(cpuId),
        gpu_id: Number.parseInt(gpuId),
        ram_id: Number.parseInt(ramId)
    };
    
    // Validar que los IDs sean válidos
    if (!selectedComponents.cpu_id || !selectedComponents.gpu_id || !selectedComponents.ram_id) {
        showAlert('Componentes inválidos. Por favor intenta de nuevo.', 'danger');
        showLoading(false);
        return;
    }
    
    try {
        const response = await fetch('/api/analizar-hardware', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken() || ''
            },
            body: JSON.stringify(selectedComponents)
        });
        
        if (!response.ok) {
            try {
                const errorData = await response.json();
                throw new Error(errorData.error || `Error: ${response.status} ${response.statusText}`);
            } catch (e) {
                throw new Error(`Error en la respuesta del servidor: ${response.status}`);
            }
        }
        
        const data = await response.json();
        
        if (data.success) {
            currentAnalysis = data;
            displayResults(data);
        } else {
            showAlert(data.error || 'Error al analizar el hardware', 'danger');
        }
        
    } catch (error) {
        console.error('Error completo:', error);
        showAlert(`Error: ${error.message || 'Error al conectar con el servidor. Por favor intenta de nuevo.'}`, 'danger');
    } finally {
        showLoading(false);
    }
}

/**
 * Mostrar todos los resultados
 */
function displayResults(data) {
    displaySystemScore(data.system_score);
    displayBottlenecks(data.bottlenecks);
    displayRecommendations(data.recommendations);
    displayGameCompatibility(data.games);
    
    // Mostrar contenedor de resultados
    document.getElementById('results-container').classList.remove('d-none');
    
    // Scroll suave a resultados
    document.getElementById('results-container').scrollIntoView({ 
        behavior: 'smooth', 
        block: 'start' 
    });
}

/**
 * Mostrar puntuación del sistema
 */
function displaySystemScore(score) {
    const container = document.getElementById('system-score-card');
    
    const tierColor = getTierColor(score.total);
    
    container.innerHTML = `
        <div class="card-body text-center py-4" style="background: linear-gradient(135deg, ${tierColor}22 0%, ${tierColor}11 100%);">
            <div class="row align-items-center">
                <div class="col-md-4">
                    <div class="score-display">${score.total}</div>
                    <p class="text-muted mb-0">Puntuación Total</p>
                </div>
                <div class="col-md-4">
                    <h4 class="mb-2" style="color: ${tierColor};">
                        <i class="fas fa-trophy me-2"></i>${score.tier}
                    </h4>
                    <p class="text-muted mb-0">Nivel de Rendimiento</p>
                </div>
                <div class="col-md-4">
                    <div class="row g-2">
                        <div class="col-12">
                            <small class="text-muted">CPU:</small>
                            <strong class="ms-2">${score.cpu_score}</strong>
                        </div>
                        <div class="col-12">
                            <small class="text-muted">GPU:</small>
                            <strong class="ms-2">${score.gpu_score}</strong>
                        </div>
                        <div class="col-12">
                            <small class="text-muted">RAM:</small>
                            <strong class="ms-2">${score.ram_gb}GB</strong>
                        </div>
                    </div>
                </div>
            </div>
            <hr class="my-3">
            <div class="row text-start">
                <div class="col-md-4">
                    <small class="text-muted"><i class="fas fa-microchip me-1"></i>CPU:</small>
                    <p class="mb-0">${score.components.cpu}</p>
                </div>
                <div class="col-md-4">
                    <small class="text-muted"><i class="fas fa-video me-1"></i>GPU:</small>
                    <p class="mb-0">${score.components.gpu}</p>
                </div>
                <div class="col-md-4">
                    <small class="text-muted"><i class="fas fa-memory me-1"></i>RAM:</small>
                    <p class="mb-0">${score.components.ram}</p>
                </div>
            </div>
        </div>
    `;
}

/**
 * Mostrar cuellos de botella
 */
function displayBottlenecks(bottlenecks) {
    const container = document.getElementById('bottlenecks-container');
    
    if (!bottlenecks.has_bottleneck) {
        container.innerHTML = `
            <div class="alert alert-success mb-0">
                <h5><i class="fas fa-check-circle me-2"></i>¡Sistema Balanceado!</h5>
                <p class="mb-0">${bottlenecks.description}</p>
            </div>
        `;
        return;
    }
    
    const severityClass = {
        'severe': 'danger',
        'moderate': 'warning',
        'mild': 'info'
    }[bottlenecks.severity] || 'info';
    
    const severityIcon = {
        'severe': 'exclamation-triangle',
        'moderate': 'exclamation-circle',
        'mild': 'info-circle'
    }[bottlenecks.severity] || 'info-circle';
    
    let html = `
        <div class="alert alert-${severityClass}">
            <h5>
                <i class="fas fa-${severityIcon} me-2"></i>
                Cuello de Botella Detectado
                ${bottlenecks.percentage_loss > 0 ? `<span class="badge bg-${severityClass} ms-2">-${bottlenecks.percentage_loss}% rendimiento</span>` : ''}
            </h5>
            <div class="bottleneck-description">${formatMarkdown(bottlenecks.description)}</div>
    `;
    
    if (bottlenecks.recommendations && bottlenecks.recommendations.length > 0) {
        html += `
            <hr>
            <h6><i class="fas fa-tools me-2"></i>Recomendaciones:</h6>
            <ul class="mb-0">
                ${bottlenecks.recommendations.map(rec => `<li>${rec}</li>`).join('')}
            </ul>
        `;
    }
    
    html += `</div>`;
    container.innerHTML = html;
}

/**
 * Mostrar recomendaciones generales
 */
function displayRecommendations(recommendations) {
    const section = document.getElementById('recommendations-section');
    const container = document.getElementById('recommendations-container');
    
    if (!recommendations || recommendations.length === 0) {
        section.classList.add('d-none');
        return;
    }
    
    section.classList.remove('d-none');
    
    const html = `
        <ul class="list-group list-group-flush">
            ${recommendations.map(rec => `
                <li class="list-group-item">
                    <i class="fas fa-arrow-right text-info me-2"></i>${rec}
                </li>
            `).join('')}
        </ul>
    `;
    
    container.innerHTML = html;
}

/**
 * Mostrar compatibilidad con juegos
 */
function displayGameCompatibility(games) {
    // Actualizar contadores
    document.getElementById('ultra-count').textContent = games.can_run_ultra.length;
    document.getElementById('high-count').textContent = games.can_run_high.length;
    document.getElementById('medium-count').textContent = games.can_run_medium.length;
    document.getElementById('low-count').textContent = games.can_run_low.length;
    document.getElementById('cannot-count').textContent = games.cannot_run.length;
    
    // Renderizar cada categoría
    renderGameCategory('ultra-games', games.can_run_ultra, 'ultra', 'success');
    renderGameCategory('high-games', games.can_run_high, 'high', 'primary');
    renderGameCategory('medium-games', games.can_run_medium, 'medium', 'warning');
    renderGameCategory('low-games', games.can_run_low, 'low', 'secondary');
    renderGameCategory('cannot-games', games.cannot_run, 'cannot', 'danger');
}

/**
 * Renderizar categoría de juegos
 */
function renderGameCategory(containerId, games, quality, badgeColor) {
    const container = document.getElementById(containerId);
    
    if (games.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-inbox fa-3x mb-3"></i>
                <p>No hay juegos en esta categoría</p>
            </div>
        `;
        return;
    }
    
    const html = games.map(game => `
        <div class="card game-card ${quality} mb-3">
            <div class="card-body">
                <div class="row align-items-center">
                    <div class="col-md-2">
                        <img src="${game.imagen || '/static/images/game-placeholder.jpg'}" 
                             class="img-fluid rounded" 
                             alt="${game.nombre}"
                             onerror="this.src='/static/images/game-placeholder.jpg'">
                    </div>
                    <div class="col-md-6">
                        <h5 class="mb-1">${game.nombre}</h5>
                        ${game.reason ? `<small class="text-danger">${game.reason}</small>` : ''}
                        ${game.bottleneck ? `
                            <div class="mt-2">
                                <span class="badge bg-warning text-dark">
                                    <i class="fas fa-exclamation-triangle me-1"></i>
                                    Limitado por ${game.bottleneck.toUpperCase()}
                                </span>
                            </div>
                        ` : ''}
                    </div>
                    <div class="col-md-2 text-center">
                        ${game.expected_fps > 0 ? `
                            <div class="fps-indicator text-${badgeColor}">
                                ${game.expected_fps} FPS
                            </div>
                            <small class="text-muted">Estimado</small>
                        ` : '<small class="text-danger">No puede correr</small>'}
                    </div>
                    <div class="col-md-2 text-center">
                        <span class="badge bg-${badgeColor} quality-badge">
                            ${getQualityLabel(quality)}
                        </span>
                        <div class="mt-2">
                            <small class="text-muted">$${game.precio}</small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

/**
 * Utilidades
 */

function getTierColor(score) {
    if (score >= 15000) return '#9c27b0';
    if (score >= 10000) return '#2196f3';
    if (score >= 7000) return '#4caf50';
    if (score >= 4000) return '#ff9800';
    return '#f44336';
}

function getQualityLabel(quality) {
    const labels = {
        'ultra': 'Ultra (4K)',
        'high': 'Alto (1440p)',
        'medium': 'Medio (1080p)',
        'low': 'Bajo (720p)',
        'cannot': 'No Compatible'
    };
    return labels[quality] || quality;
}

function formatMarkdown(text) {
    // Convertir markdown simple a HTML
    return text
        .replaceAll(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replaceAll(/\n\n/, '</p><p>')
        .replaceAll(/\n/, '<br>');
}

function showLoading(show) {
    const loader = document.getElementById('loading-container');
    if (show) {
        loader.classList.remove('d-none');
    } else {
        loader.classList.add('d-none');
    }
}

function hideResults() {
    document.getElementById('results-container').classList.add('d-none');
}

function showAlert(message, type = 'info') {
    // Crear alert temporal
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3`;
    alertDiv.style.zIndex = '9999';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto-remover después de 5 segundos
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

/**
 * Obtener token CSRF del DOM
 */
function getCSRFToken() {
    // Buscar en meta tag
    const token = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (token) return token;
    
    // Buscar en input hidden
    const input = document.querySelector('input[name="csrf_token"]');
    if (input) return input.value;
    
    // Buscar en cookie
    const name = 'csrf_token=';
    const decodedCookie = decodeURIComponent(document.cookie);
    const cookieArray = decodedCookie.split(';');
    for (let cookie of cookieArray) {
        cookie = cookie.trim();
        if (cookie.indexOf(name) === 0) {
            return cookie.substring(name.length);
        }
    }
    
    return '';
}

