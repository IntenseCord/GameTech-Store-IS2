"""
Configuración de Sentry para monitoreo de errores en producción
"""
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
import os

def init_sentry(app):
    """Inicializar Sentry para tracking de errores"""
    sentry_dsn = os.environ.get('SENTRY_DSN')

    # app.config nunca tiene una clave 'FLASK_ENV': app.config.from_object()
    # copia los atributos de clase de Config (ENV, no FLASK_ENV) -- comparar
    # contra 'FLASK_ENV' aqui hacia que Sentry nunca se inicializara, ni en
    # produccion real (mismo bug que tenia utils/security_headers.py con HSTS).
    if sentry_dsn and app.config.get('ENV') == 'production':
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[FlaskIntegration()],
            
            # Performance Monitoring
            traces_sample_rate=1.0,
            
            # Configuración de entorno
            environment=app.config.get('ENV', 'development'),
            release=os.environ.get('APP_VERSION', '1.0.0'),
            
            # Opciones adicionales
            send_default_pii=False,  # No enviar información personal
            attach_stacktrace=True,   # Incluir stack traces
            max_breadcrumbs=50,       # Máximo de breadcrumbs
        )
        
        app.logger.info('✅ Sentry inicializado correctamente')
        return True
    else:
        if app.config.get('ENV') != 'production':
            app.logger.info('ℹ️  Sentry no configurado (modo desarrollo)')
        else:
            app.logger.warning('⚠️  SENTRY_DSN no configurado en producción')
        return False
