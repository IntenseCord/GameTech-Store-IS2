"""
Regresión: init_sentry() comparaba app.config.get('FLASK_ENV') ==
'production' -- igual que el bug de HSTS en utils/security_headers.py.
app.config nunca tiene una clave 'FLASK_ENV' (solo 'ENV', vía Config.ENV),
así que Sentry nunca se inicializaba, ni en un despliegue real de
producción con SENTRY_DSN configurado.
"""
from utils.sentry_config import init_sentry


def test_sentry_se_inicializa_en_produccion_con_dsn(app_context, monkeypatch):
    monkeypatch.setenv('SENTRY_DSN', 'https://fake@sentry.example.com/1')
    monkeypatch.setattr('utils.sentry_config.sentry_sdk.init', lambda **kwargs: None)
    app_context.config['ENV'] = 'production'
    try:
        assert init_sentry(app_context) is True
    finally:
        app_context.config['ENV'] = 'testing'


def test_sentry_no_se_inicializa_fuera_de_produccion(app_context, monkeypatch):
    monkeypatch.setenv('SENTRY_DSN', 'https://fake@sentry.example.com/1')
    app_context.config['ENV'] = 'testing'
    assert init_sentry(app_context) is False
