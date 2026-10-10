"""Paginación y filtros de precio de /tienda"""
from contextlib import contextmanager

import pytest
from flask import template_rendered

from extensions import db
from models.database_models import Game

TOTAL_JUEGOS = 60


@contextmanager
def capturar_contexto(app):
    """Captura el contexto que la vista le pasa a store.html."""
    registros = []

    def registrar(sender, template, context, **extra):
        if template.name == 'store.html':
            registros.append(context)

    template_rendered.connect(registrar, app)
    try:
        yield registros
    finally:
        template_rendered.disconnect(registrar, app)


@pytest.fixture
def catalogo(app_context):
    """60 juegos con precios 1..60, más que el máximo permitido por página."""
    for n in range(1, TOTAL_JUEGOS + 1):
        db.session.add(Game(
            nombre=f'Juego {n:02d}', descripcion='d', precio=n, genero='Acción',
            desarrollador='Dev', requisitos_minimos='{}', requisitos_recomendados='{}', stock=5,
        ))
    db.session.commit()


def _consultar(app_context, client, query):
    with capturar_contexto(app_context) as registros:
        respuesta = client.get(f'/tienda{query}')
    assert respuesta.status_code == 200
    return registros[0]


def test_valores_por_defecto_no_cambian(app_context, client, catalogo):
    ctx = _consultar(app_context, client, '')
    assert ctx['pagination'].per_page == 12
    assert ctx['pagination'].page == 1
    assert len(ctx['juegos']) == 12


def test_per_page_enorme_se_limita_a_48(app_context, client, catalogo):
    ctx = _consultar(app_context, client, '?per_page=100000')
    assert ctx['pagination'].per_page == 48
    assert len(ctx['juegos']) == 48


@pytest.mark.parametrize('valor', ['0', '-5'])
def test_per_page_menor_a_1_se_ajusta_a_1(app_context, client, catalogo, valor):
    ctx = _consultar(app_context, client, f'?per_page={valor}')
    assert ctx['pagination'].per_page == 1
    assert len(ctx['juegos']) == 1


def test_per_page_no_numerico_usa_el_valor_por_defecto(app_context, client, catalogo):
    ctx = _consultar(app_context, client, '?per_page=abc')
    assert ctx['pagination'].per_page == 12


@pytest.mark.parametrize('valor', ['0', '-3'])
def test_page_menor_a_1_se_ajusta_a_1(app_context, client, catalogo, valor):
    ctx = _consultar(app_context, client, f'?page={valor}')
    assert ctx['pagination'].page == 1
    assert ctx['juegos'][0].nombre == 'Juego 01'


def test_page_mas_alla_del_final_devuelve_lista_vacia_sin_error(app_context, client, catalogo):
    ctx = _consultar(app_context, client, '?page=999')
    assert ctx['juegos'] == []


def test_precio_max_cero_filtra_en_vez_de_ignorarse(app_context, client, catalogo):
    """Todos los juegos cuestan >= 1, así que precio_max=0 no debe devolver ninguno."""
    ctx = _consultar(app_context, client, '?precio_max=0')
    assert ctx['juegos'] == []


def test_precio_min_cero_no_excluye_nada(app_context, client, catalogo):
    ctx = _consultar(app_context, client, '?precio_min=0&per_page=48')
    assert len(ctx['juegos']) == 48
    assert ctx['pagination'].total == TOTAL_JUEGOS


def test_precio_vacio_se_ignora(app_context, client, catalogo):
    """El formulario envía campos vacíos cuando el usuario no filtra."""
    ctx = _consultar(app_context, client, '?precio_min=&precio_max=')
    assert ctx['pagination'].total == TOTAL_JUEGOS


def test_rango_de_precios_filtra_correctamente(app_context, client, catalogo):
    ctx = _consultar(app_context, client, '?precio_min=10&precio_max=20&per_page=48')
    assert ctx['pagination'].total == 11
