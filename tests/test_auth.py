"""
Tests de autenticación
"""
import pytest
from flask import url_for
from models.database_models import User


def test_registro_exitoso(client):
    """Test de registro de usuario exitoso"""
    response = client.post('/registro', data={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'Test1234',
        'confirm_password': 'Test1234'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    user = User.query.filter_by(username='newuser').first()
    assert user is not None
    assert user.email == 'newuser@example.com'


def test_registro_contrasenas_no_coinciden(client):
    """Test de registro con contraseñas que no coinciden"""
    response = client.post('/registro', data={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'Test1234',
        'confirm_password': 'Test12345'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    user = User.query.filter_by(username='newuser').first()
    assert user is None


def test_registro_contrasena_invalida(client):
    """Test de registro con contraseña inválida (sin mayúscula)"""
    response = client.post('/registro', data={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'test1234',
        'confirm_password': 'test1234'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    user = User.query.filter_by(username='newuser').first()
    assert user is None


def test_login_exitoso(client, test_user):
    """Test de login exitoso"""
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'Test1234'
    }, follow_redirects=True)
    
    assert response.status_code == 200


def test_login_fallido(client, test_user):
    """Test de login con contraseña incorrecta"""
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'WrongPassword'
    }, follow_redirects=True)
    
    assert response.status_code == 200


def test_logout(client, test_user):
    """Test de logout"""
    # Login primero
    client.post('/login', data={
        'username': 'testuser',
        'password': 'Test1234'
    })
    
    # Logout
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
