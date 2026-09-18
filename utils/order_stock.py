"""
Ajustes de stock asociados a cambios de estado de una orden. Se comparte
entre el webhook de MercadoPago (controllers/webhooks.py) y la edición
manual de estado del admin (controllers/admin.py) para que ambos caminos
mantengan el inventario sincronizado con el mismo criterio.

El ajuste se hace con un UPDATE por tabla (juegos y hardware) en vez de un
SELECT + UPDATE por cada ítem: cada sentencia es un viaje a la base de datos,
y el costo crecía con el tamaño de la orden. `stock = stock + n` se calcula
dentro de la base, así que además es atómico (no se lee, suma y escribe
desde Python).
"""
from sqlalchemy import func, select, update

from extensions import db
from models.database_models import Game, Hardware, OrderItem

_MODELO_POR_TIPO = {'game': Game, 'hardware': Hardware}


def _ajustar_stock(order, signo):
    """Suma (signo=+1) o resta (signo=-1) a cada producto de la orden la
    cantidad total comprada. Productos que ya no existen o tipos desconocidos
    se ignoran, igual que antes."""
    for tipo, modelo in _MODELO_POR_TIPO.items():
        items_del_tipo = (
            OrderItem.order_id == order.id,
            OrderItem.product_type == tipo,
        )
        cantidad_por_producto = (
            select(func.sum(OrderItem.quantity))
            .where(*items_del_tipo, OrderItem.product_id == modelo.id)
            .scalar_subquery()
        )
        db.session.execute(
            update(modelo)
            .where(modelo.id.in_(select(OrderItem.product_id).where(*items_del_tipo)))
            .values(stock=func.coalesce(modelo.stock, 0) + signo * cantidad_por_producto)
            # 'fetch' deja al día los objetos que la sesión ya tenga cargados.
            .execution_options(synchronize_session='fetch')
        )


def restaurar_stock(order):
    """Devuelve al inventario el stock descontado en checkout() cuando el
    pago termina rechazado -- el stock se descuenta al crear la orden
    'pending' (antes de saber si el pago se confirma), así que si no se
    confirma hay que revertirlo."""
    _ajustar_stock(order, +1)


def descontar_stock(order):
    """Vuelve a descontar el stock cuando una orden que había sido
    rechazada termina aprobada (reintento de pago exitoso) -- el stock se
    había restaurado en el rechazo anterior."""
    _ajustar_stock(order, -1)
