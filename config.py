"""
Configuración de la aplicación por ambiente
"""
import os
from pathlib import Path


class Config:
    """Configuración base"""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuración de base de datos
    @staticmethod
    def get_database_url():
        """Obtener URL de base de datos desde variables de entorno"""
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            instance_path = Path(__file__).parent / 'instance'
            instance_path.mkdir(exist_ok=True)
            db_file = instance_path / 'gametech_store.db'
            db_url = f'sqlite:///{db_file}'
        
        # Fallback a SQLite si PostgreSQL no está disponible
        if db_url and ('postgres' in db_url or db_url.startswith('postgresql')):
            try:
                import psycopg
            except Exception:
                try:
                    import psycopg2
                except Exception:
                    print("⚠️  PostgreSQL driver no disponible. Usando SQLite local como fallback.")
                    instance_path = Path(__file__).parent / 'instance'
                    db_file = instance_path / 'gametech_store.db'
                    db_url = f'sqlite:///{db_file}'
        
        return db_url
    
    @staticmethod
    def get_engine_options(db_url):
        """Obtener opciones del engine según tipo de base de datos"""
        if db_url.startswith('sqlite'):
            return {'connect_args': {'check_same_thread': False}}
        else:
            return {
                'pool_pre_ping': True,
                'pool_recycle': 300,
                'pool_timeout': 30,
                'pool_size': 10,
                'max_overflow': 5
            }
    
    # Configuración de uploads
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # Configuración de correo electrónico
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_USERNAME'))
    
    # Configuración de sesiones
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hora


class DevelopmentConfig(Config):
    """Configuración de desarrollo"""
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    @staticmethod
    def init_app(app):
        # Generar SECRET_KEY si no existe para desarrollo
        import secrets
        if not app.config.get('SECRET_KEY') or app.config['SECRET_KEY'] == 'dev-secret-key-change-in-production':
            app.config['SECRET_KEY'] = secrets.token_hex(32)
            print("⚠️  SECRET_KEY generada para desarrollo")


class ProductionConfig(Config):
    """Configuración de producción"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True  # Solo HTTPS en producción
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    @staticmethod
    def init_app(app):
        # Exigir SECRET_KEY en producción
        if not app.config.get('SECRET_KEY') or app.config['SECRET_KEY'] == 'dev-secret-key-change-in-production':
            raise ValueError('SECRET_KEY es requerido en producción')


class TestingConfig(Config):
    """Configuración de testing"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
