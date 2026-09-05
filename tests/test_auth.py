"""
Tests de autenticación
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from flask import url_for
from extensions import db
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


def test_recuperar_password_no_falla_si_smtp_falla(client, test_user, monkeypatch):
    """Antes del fix, `mail.send()` estaba dentro del mismo try que el commit de BD
    y se atrapaba con `except Exception` genérico junto con errores de BD reales.
    El token de recuperación debe guardarse aunque el envío del correo falle."""
    def fallar_envio(*args, **kwargs):
        raise RuntimeError('SMTP no configurado')

    monkeypatch.setattr('controllers.auth.mail.send', fallar_envio)

    response = client.post('/recuperar-password', data={
        'email': test_user.email
    }, follow_redirects=False)

    # No debe ser un 500: el fallo de correo se registra pero no interrumpe el flujo
    assert response.status_code == 302

    db.session.refresh(test_user)
    assert test_user.reset_token is not None


def test_token_expirado_compara_bien_naive_contra_aware(client, test_user):
    """Regresión real: reset_token_expiry se guarda en una columna DateTime
    sin tz. Se escribe con datetime.now(timezone.utc) pero SQLAlchemy la
    devuelve naive al releerla de la BD (SQLite y Postgres igual, la columna
    no tiene timezone=True). token_expirado() comparaba esa fecha naive
    directo contra datetime.now(timezone.utc) (aware) -> TypeError 'can't
    compare offset-naive and offset-aware datetimes', atrapado por el except
    Exception genérico de reset_password() y mostrado como 'token inválido'.
    En la práctica, CUALQUIER link de recuperación de contraseña fallaba
    siempre, el 100% de las veces, sin importar qué tan rápido se usara. El
    mismo archivo ya tenía el fix correcto en verify_login() con
    login_verification_expiry -- solo faltaba aplicarlo aquí."""
    test_user.reset_token = str(uuid.uuid4())
    test_user.reset_token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    db.session.commit()

    pagina = client.get(f'/reset-password/{test_user.reset_token}')

    assert pagina.status_code == 200
    assert b'token inv\xc3\xa1lido' not in pagina.data.lower()
    assert b'ha expirado' not in pagina.data.lower()

    nueva = client.post(f'/reset-password/{test_user.reset_token}', data={
        'password': 'NuevaPass123',
        'confirm_password': 'NuevaPass123',
    }, follow_redirects=False)
    assert nueva.status_code == 302
    assert '/login' in nueva.headers['Location']
