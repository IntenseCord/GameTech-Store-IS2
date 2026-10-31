/*
 * Configurador de PC. Requiere static/js/compatibilidad.js y window.PC_SLOTS = [{tipo, campo, etiqueta, texto}, ...].
 * No calcula nada de hardware: el nivel de rendimiento, el cuello de botella y la compatibilidad vienen del servidor
 * (POST /api/verificar-configuracion, que usa el motor único).
 */
const currentBuild = {};
const componentsData = {};
let peticionVigente = 0;

function slotsDelConfigurador() {
    return window.PC_SLOTS || [];
}

function precioTotal(seleccion) {
    return Object.values(seleccion)
        .filter(componente => componente)
        .reduce((suma, componente) => suma + componente.precio, 0);
}

function htmlCuello(cuello) {
    if (!cuello || !cuello.has_bottleneck) {
        return '';
    }
    const texto = String(cuello.description || '').replaceAll('**', '').split('\n').filter(Boolean).map(escapeHtml).join('<br>');
    return `<div class="alert alert-warning mb-3"><i class="fas fa-exclamation-triangle me-2"></i>${texto}</div>`;
}

function htmlRecomendaciones(lista) {
    if (!lista || lista.length === 0) {
        return '';
    }
    return `<ul class="list-unstyled mb-0">${lista.map(t => `<li class="mb-1">${escapeHtml(t)}</li>`).join('')}</ul>`;
}

function textoNivel(rendimiento) {
    return rendimiento ? rendimiento.nivel : 'Sin componentes';
}

// ------------------------------------------------------------------ datos y elección
async function loadComponentsData() {
    try {
        for (const slot of slotsDelConfigurador()) {
            const respuesta = await fetch(`/api/hardware/por-tipo/${encodeURIComponent(slot.tipo)}`);
            const datos = await respuesta.json();
            componentsData[slot.tipo] = datos.resultados || [];
        }
    } catch (error) {
        console.error('Error cargando datos de componentes:', error);
    }
}

function selectComponent(tipo) {
    const modal = new bootstrap.Modal(document.getElementById('componentModal'));
    document.getElementById('componentModalLabel').textContent = `Seleccionar ${tipo}`;
    const contenedor = document.getElementById('component-options');
    contenedor.innerHTML = '';

    for (const componente of componentsData[tipo] || []) {
        const tarjeta = document.createElement('div');
        tarjeta.className = 'component-option card mb-2';
        tarjeta.innerHTML = `
            <div class="card-body">
                <div class="row align-items-center">
                    <div class="col-md-2">
                        <img src="${escapeHtml(componente.imagen)}" class="img-fluid rounded" alt="${escapeHtml(componente.modelo)}">
                    </div>
                    <div class="col-md-6">
                        <h6 class="mb-1">${escapeHtml(componente.marca)} ${escapeHtml(componente.modelo)}</h6>
                        <p class="text-muted small mb-0">${escapeHtml(componente.descripcion)}</p>
                    </div>
                    <div class="col-md-2">
                        <strong class="text-primary">$${componente.precio}</strong>
                    </div>
                    <div class="col-md-2">
                        <button class="btn btn-primary btn-sm w-100" data-elegir-tipo="${escapeHtml(tipo)}" data-elegir-id="${componente.id}">
                            Seleccionar
                        </button>
                    </div>
                </div>
            </div>`;
        contenedor.appendChild(tarjeta);
    }
    modal.show();
}

function chooseComponent(tipo, componenteId) {
    const componente = (componentsData[tipo] || []).find(c => c.id === componenteId);
    if (!componente) {
        return;
    }
    currentBuild[tipo] = componente;
    updateComponentSlot(tipo, componente);
    bootstrap.Modal.getInstance(document.getElementById('componentModal')).hide();
    actualizarConfiguracion();
}

function removeComponent(tipo) {
    currentBuild[tipo] = null;
    updateComponentSlot(tipo, null);
    actualizarConfiguracion();
}

function updateComponentSlot(tipo, componente) {
    const slot = slotsDelConfigurador().find(s => s.tipo === tipo);
    const contenido = document.getElementById(`content-${slot.campo}`);
    if (!componente) {
        contenido.innerHTML = `<p class="text-muted">${escapeHtml(slot.texto)}</p>`;
        return;
    }
    contenido.innerHTML = `
        <div class="d-flex align-items-center">
            <img src="${escapeHtml(componente.imagen || '/static/img/placeholder.png')}" class="img-thumbnail me-3" style="width: 50px; height: 50px;" alt="${escapeHtml(componente.modelo)}">
            <div class="flex-grow-1">
                <h6 class="mb-1">${escapeHtml(componente.marca)} ${escapeHtml(componente.modelo)}</h6>
                <p class="text-primary mb-0">$${componente.precio}</p>
            </div>
            <button class="btn btn-sm btn-outline-danger" data-quitar-tipo="${escapeHtml(tipo)}" aria-label="Quitar">
                <i class="fas fa-times"></i>
            </button>
        </div>`;
}

// ------------------------------------------------------------ verificación del servidor
async function actualizarConfiguracion() {
    document.getElementById('total-price').textContent = `$${precioTotal(currentBuild).toFixed(2)}`;
    document.getElementById('finalize-build-btn').disabled = Object.values(currentBuild).filter(c => c).length < 3;

    const cuerpo = cuerpoDeConfiguracion(currentBuild, slotsDelConfigurador());
    const verificaciones = document.getElementById('verificaciones');
    if (Object.keys(cuerpo).length === 0) {
        verificaciones.innerHTML = htmlResumen('sin_datos') + htmlVerificaciones([]);
        document.getElementById('performance-level').textContent = textoNivel(null);
        document.getElementById('recommendations-container').innerHTML = '';
        return;
    }

    const numero = ++peticionVigente;                      // descartar respuestas que llegan tarde
    try {
        const datos = await verificarConfiguracion(cuerpo);
        if (numero !== peticionVigente) {
            return;
        }
        window.estadoDeLaConfiguracion = datos.estado;
        verificaciones.innerHTML = htmlResumen(datos.estado) + htmlVerificaciones(datos.verificaciones);
        document.getElementById('performance-level').textContent = textoNivel(datos.rendimiento);
        document.getElementById('recommendations-container').innerHTML = htmlCuello(datos.cuello) + htmlRecomendaciones(datos.recomendaciones);
    } catch (error) {
        if (numero === peticionVigente) {
            verificaciones.innerHTML = '<div class="alert alert-danger mb-0">No se pudo verificar la configuración. Inténtalo de nuevo.</div>';
        }
    }
}

// ------------------------------------------------------------------------- compra
async function finalizeBuild() {
    if (window.estadoDeLaConfiguracion === 'incompatible'
        && !window.confirm('Hay piezas incompatibles entre sí. ¿Quieres agregarlas al carrito de todos modos?')) {
        return;
    }
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    const componentes = Object.values(currentBuild).filter(c => c);
    const boton = document.getElementById('finalize-build-btn');
    boton.disabled = true;
    boton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Agregando...';

    try {
        for (const componente of componentes) {
            const respuesta = await fetch('/carrito/agregar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ product_type: 'hardware', product_id: componente.id, quantity: 1 }),
            });
            if (!respuesta.ok && respuesta.status !== 400) {
                // 400 puede ser stock insuficiente o ya en carrito: no es fatal
                const error = await respuesta.json();
                showToast(`Error con ${componente.modelo}: ${error.message || respuesta.statusText}`, 'danger');
            }
        }
        window.location.href = '/carrito';
    } catch (error) {
        showToast('Error al agregar componentes al carrito', 'danger');
        boton.disabled = false;
        boton.innerHTML = '<i class="fas fa-shopping-cart me-2"></i>Finalizar Compra';
    }
}

document.addEventListener('DOMContentLoaded', function () {
    loadComponentsData();
    document.getElementById('finalize-build-btn').addEventListener('click', finalizeBuild);
    document.addEventListener('click', function (e) {
        const abrir = e.target.closest('[data-slot-tipo]');
        const elegir = e.target.closest('[data-elegir-id]');
        const quitar = e.target.closest('[data-quitar-tipo]');
        if (abrir) {
            selectComponent(abrir.dataset.slotTipo);
        } else if (elegir) {
            chooseComponent(elegir.dataset.elegirTipo, Number(elegir.dataset.elegirId));
        } else if (quitar) {
            removeComponent(quitar.dataset.quitarTipo);
        }
    });
});
