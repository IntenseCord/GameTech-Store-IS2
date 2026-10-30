"""cart_items: una sola fila por usuario y producto

Hallazgo 30: un clic en "Agregar" mandaba dos peticiones y cart_items podía tener filas duplicadas del
mismo producto para el mismo usuario. Antes de crear la restricción única se fusionan las duplicadas
existentes: se conserva la fila más antigua y se le suma la cantidad de las demás.

Revision ID: a7c3e91b2d44
Revises: e4496e5d856a
Create Date: 2026-10-29 22:10:00.000000

"""
from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'a7c3e91b2d44'
down_revision = 'e4496e5d856a'
branch_labels = None
depends_on = None

NOMBRE_RESTRICCION = 'uq_cart_items_usuario_producto'
GRUPO = 'user_id, product_type, product_id'


def fusionar_duplicados(conexion):
    """Deja una sola fila por (usuario, tipo, producto) con la cantidad total."""
    conexion.execute(text(f"""
        UPDATE cart_items
        SET quantity = (
            SELECT SUM(COALESCE(c2.quantity, 1)) FROM cart_items c2
            WHERE c2.user_id = cart_items.user_id
              AND c2.product_type = cart_items.product_type
              AND c2.product_id = cart_items.product_id
        )
        WHERE id IN (SELECT MIN(id) FROM cart_items GROUP BY {GRUPO} HAVING COUNT(*) > 1)
    """))
    conexion.execute(text(f"""
        DELETE FROM cart_items
        WHERE id NOT IN (SELECT MIN(id) FROM cart_items GROUP BY {GRUPO})
    """))


def upgrade():
    fusionar_duplicados(op.get_bind())
    with op.batch_alter_table('cart_items', schema=None) as batch_op:
        batch_op.create_unique_constraint(NOMBRE_RESTRICCION, ['user_id', 'product_type', 'product_id'])


def downgrade():
    with op.batch_alter_table('cart_items', schema=None) as batch_op:
        batch_op.drop_constraint(NOMBRE_RESTRICCION, type_='unique')
