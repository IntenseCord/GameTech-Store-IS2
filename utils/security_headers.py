"""
Middleware para agregar headers de seguridad HTTP
"""
from flask import request

# GraphiQL (el explorador de la API GraphQL, activo solo fuera de producción)
# carga sus scripts y estilos desde unpkg.com. Se permite ese origen ÚNICAMENTE
# en la ruta /graphql y fuera de producción: el resto de la aplicación conserva
# la política original. Ojo: esos scripts de terceros comparten el origen de la
# aplicación mientras el explorador esté abierto.
CDN_EXPLORADOR_GRAPHQL = 'https://unpkg.com'
RUTA_GRAPHQL = '/graphql'


def add_security_headers(app):
    """Agregar headers de seguridad a todas las respuestas"""
    
    @app.after_request
    def set_security_headers(response):
        """Configurar headers de seguridad en cada respuesta"""
        
        # Prevenir clickjacking
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        
        # Prevenir MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # XSS Protection (legacy pero útil para navegadores antiguos)
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Content Security Policy
        es_explorador_graphql = request.path == RUTA_GRAPHQL and app.config.get('ENV') != 'production'
        cdn_extra = f' {CDN_EXPLORADOR_GRAPHQL}' if es_explorador_graphql else ''
        # GraphiQL trae sus fuentes incrustadas en el CSS como data: URIs.
        fuentes_extra = ' data:' if es_explorador_graphql else ''
        csp = (
            "default-src 'self'; "
            f"script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com{cdn_extra}; "
            f"style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com{cdn_extra}; "
            f"font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net{fuentes_extra}; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
        )
        response.headers['Content-Security-Policy'] = csp
        
        # HSTS (solo en producción con HTTPS)
        # app.config nunca tiene una clave 'FLASK_ENV': app.config.from_object()
        # copia los atributos de clase de Config (ENV, no FLASK_ENV) -- esa
        # comparación era siempre False, HSTS nunca se enviaba ni en produccion.
        if app.config.get('ENV') == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy (antes Feature-Policy)
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        return response
    
    app.logger.info('✅ Headers de seguridad configurados')
