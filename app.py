import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from config import get_config

# Get configuration based on environment
config_class = get_config()

# Configure logging with centralized configuration
logging.basicConfig(level=getattr(logging, config_class.LOG_LEVEL), 
                   format=config_class.LOG_FORMAT)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.config.from_object(config_class)
app.secret_key = app.config['SECRET_KEY']
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Configure the database using centralized configuration
app.config["SQLALCHEMY_DATABASE_URI"] = app.config['DATABASE_URL']
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": app.config['DATABASE_POOL_RECYCLE'],
    "pool_pre_ping": app.config['DATABASE_POOL_PRE_PING'],
}

# Initialize the app with the extension
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Effettua il login per accedere a questa pagina.'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()

# Import routes after app context is set up (must be at module level for gunicorn)
import routes

# Import routes to register them with the app
import routes
import api_routes

# Registra funzioni di utility per i template
@app.template_global()
def format_hours(hours_decimal):
    """Formato ore decimali in ore:minuti per i template"""
    from utils import format_hours as utils_format_hours
    return utils_format_hours(hours_decimal)

@app.template_filter('to_italian_time')
def to_italian_time(timestamp):
    """Converte timestamp UTC a orario italiano per i template"""
    if not timestamp:
        return None
    
    from zoneinfo import ZoneInfo
    utc_tz = ZoneInfo('UTC')
    italy_tz = ZoneInfo('Europe/Rome')
    
    # Se il timestamp non ha timezone, assumiamo sia UTC
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=utc_tz)
    
    # Converte all'orario italiano
    return timestamp.astimezone(italy_tz)

@app.template_filter('users_with_role_count')
def users_with_role_count(role_name):
    """Conta il numero di utenti con un determinato ruolo"""
    from models import User
    return User.query.filter_by(role=role_name).count()

@app.template_filter('format_time_italian')
def format_time_italian(timestamp):
    """Formatta timestamp in formato HH:MM per orario italiano"""
    if not timestamp:
        return "--:--"
    
    try:
        # Converti a orario italiano
        italian_time = to_italian_time(timestamp)
        if not italian_time:
            return "--:--"
        return italian_time.strftime('%H:%M')
    except Exception as e:
        pass  # Silent error handling
        return "--:--"

@app.template_filter('get_permission_display')
def get_permission_display(permission_name):
    """Traduce i nomi dei permessi usando la mappatura del modello UserRole"""
    from models import UserRole
    permissions_map = UserRole.get_available_permissions()
    return permissions_map.get(permission_name, permission_name)

# Context processor per conteggio messaggi non letti
@app.context_processor
def inject_unread_messages_count():
    """Rende disponibile il conteggio dei messaggi non letti in tutti i template"""
    from flask_login import current_user
    
    if current_user.is_authenticated and (current_user.can_send_messages() or current_user.can_view_messages()):
        from models import InternalMessage
        unread_count = InternalMessage.query.filter_by(
            recipient_id=current_user.id,
            is_read=False
        ).count()
        return dict(unread_messages_count=unread_count)
    
    return dict(unread_messages_count=0)
