"""
Ajustes de stock asociados a cambios de estado de una orden. Se comparte
entre el webhook de MercadoPago (controllers/webhooks.py) y la edición
manual de estado del admin (controllers/admin.py) para que ambos caminos
mantengan el inventario sincronizado con el mismo criterio.
"""


def restaurar_stock(order):
    """Devuelve al inventario el stock descontado en checkout() cuando el
    pago termina rechazado -- el stock se descuenta al crear la orden
    'pending' (antes de saber si el pago se confirma), así que si no se
    confirma hay que revertirlo."""
    for item in order.items:
        product = item.get_product()
        if product:
            product.stock += item.quantity


def descontar_stock(order):
    """Vuelve a descontar el stock cuando una orden que había sido
    rechazada termina aprobada (reintento de pago exitoso) -- el stock se
    había restaurado en el rechazo anterior."""
    for item in order.items:
        product = item.get_product()
        if product:
            product.stock -= item.quantity
