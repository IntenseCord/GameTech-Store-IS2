"""
API GraphQL del catálogo (juegos y hardware): solo lectura y pública.

Expone los mismos datos que la tienda ya muestra sin iniciar sesión
(/tienda, /hardware). No hay usuarios, órdenes, facturas ni pagos en el
esquema, y tampoco mutaciones: por eso la ruta se exime de CSRF (no hay
ninguna acción que un tercero pueda forzar) y no requiere sesión.
"""
from typing import Optional

import strawberry
from strawberry.flask.views import GraphQLView

from extensions import db
from models.database_models import Game, Hardware
from utils.rate_limiter import limiter, rate_limit_graphql

LIMITE_MAXIMO = 50
LIMITE_POR_DEFECTO = 10


def _acotar(limite):
    """Nunca más de LIMITE_MAXIMO elementos. Un límite negativo se trata como
    0: en SQLite `LIMIT -1` devuelve todas las filas."""
    return max(0, min(limite, LIMITE_MAXIMO))


@strawberry.type
class Juego:
    id: int
    nombre: str
    descripcion: str
    precio: float
    genero: Optional[str]
    desarrollador: Optional[str]
    imagen: Optional[str]
    stock: Optional[int]


@strawberry.type
class Componente:
    id: int
    tipo: str
    marca: str
    modelo: str
    descripcion: Optional[str]
    precio: float
    imagen: Optional[str]
    stock: Optional[int]
    benchmark_score: Optional[int]
    tdp_watts: Optional[int]
    socket: Optional[str]


@strawberry.type
class Query:
    @strawberry.field
    def juegos(self, genero: Optional[str] = None, limite: int = LIMITE_POR_DEFECTO) -> list[Juego]:
        consulta = Game.query
        if genero is not None:
            consulta = consulta.filter(Game.genero == genero)
        return consulta.order_by(Game.id).limit(_acotar(limite)).all()

    @strawberry.field
    def juego(self, id: int) -> Optional[Juego]:
        return db.session.get(Game, id)

    @strawberry.field
    def hardware(self, tipo: Optional[str] = None, limite: int = LIMITE_POR_DEFECTO) -> list[Componente]:
        consulta = Hardware.query
        if tipo is not None:
            consulta = consulta.filter(Hardware.tipo == tipo)
        return consulta.order_by(Hardware.id).limit(_acotar(limite)).all()

    @strawberry.field
    def componente(self, id: int) -> Optional[Componente]:
        return db.session.get(Hardware, id)


schema = strawberry.Schema(query=Query)


def init_graphql(app, csrf):
    """Registra /graphql. Se llama desde app.py, después de init_limiter."""
    vista = GraphQLView.as_view('graphql', schema=schema, graphql_ide='graphiql')
    vista = limiter.limit(rate_limit_graphql)(vista)
    csrf.exempt(vista)
    app.add_url_rule('/graphql', view_func=vista, methods=['GET', 'POST'])
