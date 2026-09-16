"""
Regresión: add_security_headers() comparaba app.config.get('FLASK_ENV') ==
'production' para decidir si mandar el header HSTS. app.config nunca tiene
una clave 'FLASK_ENV' -- app.config.from_object() copia los atributos de
clase de Config (que define ENV, no FLASK_ENV) -- así que esa comparación
era siempre False y HSTS nunca se enviaba, ni en un despliegue real de
producción.
"""
def test_hsts_se_envia_en_produccion(client, app_context):
    app_context.config['ENV'] = 'production'
    try:
        response = client.get('/')
        assert 'Strict-Transport-Security' in response.headers
    finally:
        app_context.config['ENV'] = 'testing'


def test_hsts_no_se_envia_fuera_de_produccion(client, app_context):
    app_context.config['ENV'] = 'testing'
    response = client.get('/')
    assert 'Strict-Transport-Security' not in response.headers
