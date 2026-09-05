"""
Configuración de Rate Limiting para protección contra ataques
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Inicializar limiter
limiter = None

def init_limiter(app):
    """Inicializar rate limiter con la aplicación Flask"""
    global limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://",
        strategy="fixed-window"
    )
    app.logger.info('✅ Rate Limiter inicializado')
    return limiter

# Límites personalizados para diferentes endpoints
def rate_limit_login():
    """Límite para intentos de login - 5 por minuto"""
    return "5 per minute"

def rate_limit_register():
    """Límite para registro - 3 por hora"""
    return "3 per hour"

def rate_limit_api():
    """Límite general para APIs - 100 por hora"""
    return "100 per hour"

def rate_limit_cart():
    """Límite para operaciones de carrito - 30 por minuto"""
    return "30 per minute"

def rate_limit_search():
    """Límite para búsquedas - 20 por minuto"""
    return "20 per minute"

def rate_limit_email_sensible():
    """Límite para rutas que envían correo a partir de un email arbitrario del
    formulario (recuperar contraseña, reenviar verificación) - 3 por hora.
    Sin esto, alguien puede bombardear el buzón de otra persona con correos
    repetidos: el límite global (50/hora) es demasiado permisivo para esto."""
    return "3 per hour"
