"""
Tests de controladores
"""
import pytest
from flask import url_for


def test_index_page(client):
    """Test de página principal"""
    response = client.get('/')
    assert response.status_code == 200


def test_tienda_page(client):
    """Test de página de tienda"""
    response = client.get('/tienda')
    assert response.status_code == 200


def test_registro_page(client):
    """Test de página de registro"""
    response = client.get('/registro')
    assert response.status_code == 200


def test_login_page(client):
    """Test de página de login"""
    response = client.get('/login')
    assert response.status_code == 200


def test_buscar_sin_query(client):
    """Test de búsqueda sin query"""
    response = client.get('/buscar')
    assert response.status_code == 200


def test_buscar_con_query(client, test_game):
    """Test de búsqueda con query"""
    response = client.get('/buscar?q=Test')
    assert response.status_code == 200


def test_juego_detalle(client, test_game):
    """Test de detalle de juego"""
    response = client.get(f'/juego/{test_game.id}')
    assert response.status_code == 200


def test_consultar_compatibilidad_no_crashea(client, test_game):
    """Regresión: Game.get_games_by_hardware() esperaba que cada valor de
    hardware_specs fuera un dict (specs.get('marca', '')), pero esta ruta le
    pasa texto libre — crasheaba con AttributeError en cada llamada, sin
    excepción, oculto por el except genérico de la ruta."""
    response = client.post('/consultar-compatibilidad', json={
        'cpu': 'Intel Core i5-3570K', 'gpu': 'NVIDIA GeForce GTX 780', 'ram': '8 GB', 'storage': ''
    })
    assert response.status_code == 200
    assert response.get_json()['success'] is True


def test_hardware_detalle(client, test_hardware):
    """Test de detalle de hardware"""
    response = client.get(f'/hardware/{test_hardware.id}')
    assert response.status_code == 200


def test_carrito_requiere_login(client):
    """Test de que el carrito requiere login"""
    response = client.get('/carrito')
    assert response.status_code == 302  # Redirect a login


def test_admin_requiere_login(client):
    """Test de que el admin requiere login"""
    response = client.get('/admin')
    assert response.status_code == 302  # Redirect a login


def test_admin_requiere_admin_role(client, test_user):
    """Test de que el admin requiere rol de administrador"""
    # Login como usuario normal
    client.post('/login', data={
        'username': 'testuser',
        'password': 'Test1234'
    })
    
    response = client.get('/admin')
    assert response.status_code == 302  # Redirect a index (no es admin)
