"""
Extensiones de Flask compartidas
"""
from flask_mail import Mail
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Inicializar extensiones
mail = Mail()
login_manager = LoginManager()
db = SQLAlchemy()
migrate = Migrate()

# Configurar Flask-Login
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página'
login_manager.login_message_category = 'info'