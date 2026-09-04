import os
import logging
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv

# Debe ejecutarse ANTES de importar `config`: sus clases leen SECRET_KEY/MAIL_*
# de os.environ como atributos de clase en el momento del import (no de forma
# perezosa), así que si .env se carga después esos valores quedan en None.
load_dotenv()

from flask import Flask, render_template, request
from flask_login import current_user
from flask_wtf.csrf import CSRFProtect

from config import config, Config
from extensions import db, mail, login_manager
from database import seed_database
from models.database_models import Game, Hardware, User, CartItem
from utils.rate_limiter import init_limiter
from utils.security_headers import add_security_headers
from utils.sentry_config import init_sentry

# Los blueprints NO se importan aquí arriba: controllers/auth.py usa
# @limiter.limit(...) como decorador en el momento de importarse, y
# `limiter` (utils/rate_limiter.py) es None hasta que init_limiter(app)
# corre más abajo. Importarlos antes rompe con AttributeError.

# Obtener configuración según ambiente
env = os.environ.get('FLASK_ENV', 'development')

# Crear la aplicación Flask
app = Flask(__name__)
app.config.from_object(config[env])

# Inicializar configuración específica del ambiente
config[env].init_app(app)

# Configurar base de datos usando métodos del config
db_url = Config.get_database_url()
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = Config.get_engine_options(db_url)

# Crear directorio de uploads si no existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Inicializar CSRF protection
csrf = CSRFProtect(app)
app.logger.info('✅ CSRF Protection habilitado')

# Inicializar extensiones
db.init_app(app)
mail.init_app(app)
login_manager.init_app(app)

# Inicializar seguridad y monitoreo
limiter = init_limiter(app)
add_security_headers(app)
init_sentry(app)

# Ejecutar migraciones automáticas (desactivado temporalmente por timeouts)
# from utils.auto_migrate import init_auto_migrations
# init_auto_migrations(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Importar y registrar blueprints (después de init_limiter, ver comentario arriba)
from controllers.store import store_bp
from controllers.hardware import hardware_bp
from controllers.auth import auth_bp
from controllers.cart import cart_bp
from controllers.admin import admin_bp
from controllers.hardware_analyzer import analyzer_bp
from controllers.invoice import invoice_bp
from controllers.wishlist import wishlist_bp

app.register_blueprint(store_bp)
app.register_blueprint(hardware_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(cart_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(analyzer_bp)
app.register_blueprint(invoice_bp)
app.register_blueprint(wishlist_bp)

# Configurar logging
if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/gametech_store.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('GameTech Store startup')

@app.route('/')
def index():
    """Página principal de la tienda"""
    juegos = Game.get_all_games()
    hardware = Hardware.get_all_hardware()

    # Obtener algunos productos destacados
    juegos_destacados = juegos[:3]
    hardware_destacado = hardware[:3]

    return render_template('index.html',
                         juegos_destacados=juegos_destacados,
                         hardware_destacado=hardware_destacado)

@app.route('/about')
def about():
    """Página acerca de"""
    return render_template('about.html')

@app.errorhandler(404)
def page_not_found(error):
    """Manejador de error 404"""
    app.logger.warning(f'404 error: {request.path}')
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Manejador de error 500"""
    db.session.rollback()
    app.logger.error(f'500 error: {error}')
    return render_template('500.html'), 500

@app.errorhandler(403)
def forbidden(error):
    """Manejador de error 403"""
    return render_template('403.html'), 403

# Context processor para hacer variables disponibles en todos los templates
@app.context_processor
def inject_user():
    """Inyectar información del usuario en todos los templates"""
    cart_count = 0
    if current_user.is_authenticated:
        cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
    return {"cart_count": cart_count}

if __name__ == '__main__':
    # Inicializar la base de datos
    with app.app_context():
        db.create_all()
        # Poblar con datos iniciales si está vacía
        if Game.query.count() == 0:
            seed_database()

    # Ejecutar la aplicación
    app.run(debug=True, host='0.0.0.0', port=5000)
