/*
 * Interfaz de compatibilidad, compartida por el Configurador de PC y la ficha de hardware.
 * Todo lo que se muestra viene de POST /api/verificar-configuracion (utils/compatibilidad.py y el motor único): este archivo
 * solo arma la petición y pinta la respuesta, no decide nada.
 */
const ESTADOS_COMPATIBILIDAD = {
    ok: { etiqueta: 'Compatible', badge: 'bg-success', alerta: 'alert-success', icono: 'check-circle' },
    justa: { etiqueta: 'Justa', badge: 'bg-warning text-dark', alerta: 'alert-warning', icono: 'exclamation-triangle' },
    incompatible: { etiqueta: 'Incompatible', badge: 'bg-danger', alerta: 'alert-danger', icono: 'times-circle' },
    sin_datos: { etiqueta: 'Sin datos', badge: 'bg-secondary', alerta: 'alert-secondary', icono: 'question-circle' },
};

// Escapar HTML antes de insertar texto del servidor o del catálogo en innerHTML.
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text ?? '';
    return div.innerHTML;
}

// Lista de verificaciones; con `tipo` solo las que involucran a ese tipo de componente.
function htmlVerificaciones(verificaciones, tipo) {
    const lista = tipo ? verificaciones.filter(v => v.piezas.includes(tipo)) : verificaciones;
    if (lista.length === 0) {
        return tipo
            ? '<p class="text-muted mb-0">Elige otras piezas para ver si encajan con este componente.</p>'
            : '<p class="text-muted mb-0">Elige al menos dos componentes que se relacionen (por ejemplo, CPU y placa base) para verificar su compatibilidad.</p>';
    }
    const filas = lista.map(v => {
        const estado = ESTADOS_COMPATIBILIDAD[v.estado] || ESTADOS_COMPATIBILIDAD.sin_datos;
        return `<li class="list-group-item d-flex align-items-start gap-2">
            <span class="badge ${estado.badge} mt-1"><i class="fas fa-${estado.icono} me-1"></i>${estado.etiqueta}</span>
            <span>${escapeHtml(v.mensaje)}</span>
        </li>`;
    });
    return `<ul class="list-group">${filas.join('')}</ul>`;
}

// Estado general (el peor de la lista) como alerta.
function htmlResumen(estado) {
    const e = ESTADOS_COMPATIBILIDAD[estado] || ESTADOS_COMPATIBILIDAD.sin_datos;
    const texto = {
        ok: 'Todas las piezas elegidas son compatibles entre sí.',
        justa: 'Las piezas encajan, pero alguna queda justa: revisa los avisos.',
        incompatible: 'Hay piezas que no son compatibles entre sí.',
        sin_datos: 'Todavía no hay suficientes piezas para verificar.',
    }[estado] || '';
    return `<div class="alert ${e.alerta} mb-3"><i class="fas fa-${e.icono} me-2"></i><strong>${e.etiqueta}.</strong> ${texto}</div>`;
}

// {tipo: componente|null} + [{tipo, campo}] -> {campo: id} solo con lo elegido.
function cuerpoDeConfiguracion(seleccion, slots) {
    const cuerpo = {};
    for (const slot of slots) {
        const componente = seleccion[slot.tipo];
        if (componente) {
            cuerpo[slot.campo] = componente.id;
        }
    }
    return cuerpo;
}

async function verificarConfiguracion(cuerpo) {
    const csrf = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    const respuesta = await fetch('/api/verificar-configuracion', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify(cuerpo),
    });
    if (!respuesta.ok) {
        throw new Error('No se pudo verificar la configuración');
    }
    return respuesta.json();
}
