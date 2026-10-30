"""
Estados de una orden y ajuste de stock asociado. Se comparte entre el webhook
de MercadoPago (controllers/webhooks.py) y la edición manual de estado del
admin (controllers/admin.py) para que ambos caminos apliquen la misma regla.

Regla: el stock se reserva al crear la orden `pending` (checkout). Al pasar a
`rejected` o `cancelled` se devuelve, una sola vez, y esos dos estados son
FINALES: la orden no vuelve a ningún otro estado (si el usuario quiere comprar
de nuevo, crea otra orden), así que nunca hay que volver a descontar.

Una orden `approved` solo puede pasar a `rejected` o `cancelled` por una
decisión manual del admin (devolución o reembolso); el webhook de MercadoPago
nunca la modifica. Ese camino supone que la mercancía no salió: el sistema no
tiene un estado de "enviado".

El ajuste se hace con un UPDATE por tabla (juegos y hardware) en vez de un
SELECT + UPDATE por cada ítem: cada sentencia es un viaje a la base de datos,
y el costo crecía con el tamaño de la orden. `stock = stock + n` se calcula
dentro de la base, así que además es atómico (no se lee, suma y escribe
desde Python).
"""
from sqlalchemy import func, select, update

from extensions import db
from models.database_models import Game, Hardware, Order, OrderItem

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
    """Devuelve al inventario el stock reservado en checkout() cuando la orden
    termina rechazada o cancelada -- el stock se descuenta al crear la orden
    'pending' (antes de saber si el pago se confirma), así que si no se
    confirma hay que revertirlo."""
    _ajustar_stock(order, +1)


# estado actual -> estados a los que puede pasar. `rejected` y `cancelled` no tienen salida.
TRANSICIONES = {
    'pending': {'approved', 'rejected', 'cancelled'},
    # approved -> rejected/cancelled: solo a mano desde el admin (devolución o reembolso), nunca por el webhook.
    'approved': {'rejected', 'cancelled'},
    # 'completed' es un valor heredado de antes del Incremento 1 (pagos): existe como origen para poder
    # cancelar órdenes viejas, pero ya no se ofrece como destino.
    'completed': {'rejected', 'cancelled'},
    'rejected': set(),
    'cancelled': set(),
}
ESTADOS_QUE_LIBERAN_STOCK = ('rejected', 'cancelled')


def estados_destino(estado_actual):
    """Estados a los que puede pasar una orden, en el orden en que se ofrecen al admin."""
    return [e for e in TRANSICIONES if e in TRANSICIONES.get(estado_actual, ())]


def cambiar_estado_orden(order, nuevo_estado):
    """Aplica la transición y el ajuste de stock que le corresponde. Devuelve
    True si la orden cambió y False si la transición no está permitida o si
    otra petición la cambió primero (en ambos casos no toca nada). No hace
    commit: lo hace quien llama, en su misma transacción.

    El cambio es una actualización condicional (`WHERE status = <estado que
    leímos>`): si dos notificaciones iguales llegan a la vez, solo una afecta
    la fila, y solo esa devuelve el stock. A diferencia de un bloqueo de fila,
    funciona igual en SQLite (tests) y en PostgreSQL."""
    estado_actual = order.status
    if nuevo_estado not in TRANSICIONES.get(estado_actual, ()):
        return False
    filas = db.session.execute(
        update(Order)
        .where(Order.id == order.id, Order.status == estado_actual)
        .values(status=nuevo_estado)
        .execution_options(synchronize_session=False)
    ).rowcount
    # El objeto en memoria puede estar desactualizado: que vuelva a leer el estado real.
    db.session.expire(order, ['status'])
    if filas != 1:
        return False
    if nuevo_estado in ESTADOS_QUE_LIBERAN_STOCK:
        restaurar_stock(order)
    return True
