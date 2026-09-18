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


"""
Explorador GraphiQL de /graphql: carga sus scripts y estilos desde unpkg.com,
que la CSP bloqueaba (la página se quedaba en "Loading..."). Solo se vio en el
navegador real: los tests no ejecutan JavaScript. El permiso debe quedar
limitado a esa ruta y a fuera de producción.
"""
def _directiva(response, nombre):
    csp = response.headers['Content-Security-Policy']
    return next(d for d in csp.split('; ') if d.startswith(nombre + ' '))


def test_csp_permite_unpkg_solo_en_graphql_en_desarrollo(client):
    graphql = client.get('/graphql', headers={'Accept': 'text/html'})

    assert 'https://unpkg.com' in _directiva(graphql, 'script-src')
    assert 'https://unpkg.com' in _directiva(graphql, 'style-src')
    assert 'data:' in _directiva(graphql, 'font-src'), 'GraphiQL incrusta sus fuentes como data: URIs'


def test_csp_no_permite_unpkg_ni_fuentes_data_en_el_resto_de_la_aplicacion(client):
    for ruta in ('/', '/tienda', '/hardware', '/login'):
        respuesta = client.get(ruta)
        assert 'unpkg.com' not in respuesta.headers['Content-Security-Policy'], ruta
        assert 'data:' not in _directiva(respuesta, 'font-src'), ruta


def test_csp_no_relaja_nada_en_graphql_en_produccion(client, app_context):
    app_context.config['ENV'] = 'production'
    try:
        respuesta = client.post('/graphql', json={'query': '{ juegos { id } }'})
        assert 'unpkg.com' not in respuesta.headers['Content-Security-Policy']
        assert 'data:' not in _directiva(respuesta, 'font-src')
    finally:
        app_context.config['ENV'] = 'testing'
