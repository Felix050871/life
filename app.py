import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from config import get_config
from email_utils import init_mail

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

# Secure session cookie configuration
# SESSION_COOKIE_SECURE solo in produzione (HTTPS richiesto)
app.config['SESSION_COOKIE_SECURE'] = not app.config.get('FLASK_DEBUG', False)
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Previene accesso JavaScript ai cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Protezione CSRF

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

# Initialize Flask-Mail for email notifications
init_mail(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.admin_login'  # Default fallback
login_manager.login_message = 'Effettua il login per accedere a questa pagina.'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    """Custom unauthorized handler per tenant-aware login redirect"""
    from flask import g, redirect, url_for, request
    from middleware_tenant import get_tenant_slug
    
    # Check if we're in a tenant context
    tenant_slug = get_tenant_slug()
    
    if tenant_slug:
        # Redirect to tenant-specific login
        return redirect(url_for('auth.tenant_login', slug=tenant_slug, next=request.url))
    else:
        # Redirect to admin login
        return redirect(url_for('auth.admin_login', next=request.url))

with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()

# Register tenant context middleware
from middleware_tenant import load_tenant_context
app.before_request(load_tenant_context)

# Import routes after app context is set up (must be at module level for gunicorn)
# Routes imported in main.py to avoid circular imports with Gunicorn

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

@app.template_filter('safe_html')
def safe_html(text):
    """Sanitizza HTML permettendo solo tag sicuri"""
    if not text:
        return ""
    
    import bleach
    from markupsafe import Markup
    
    # Tag HTML permessi (solo formattazione di base)
    allowed_tags = [
        'p', 'br', 'b', 'i', 'strong', 'em', 'u', 's',
        'ul', 'ol', 'li', 'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'blockquote', 'pre', 'code', 'hr', 'div', 'span'
    ]
    
    # Attributi permessi
    allowed_attributes = {
        'a': ['href', 'title', 'target'],
        '*': ['class']
    }
    
    # Protocolli permessi per i link
    allowed_protocols = ['http', 'https', 'mailto']
    
    # Sanitizza il contenuto
    cleaned = bleach.clean(
        text,
        tags=allowed_tags,
        attributes=allowed_attributes,
        protocols=allowed_protocols,
        strip=True
    )
    
    # Converte newline in <br> se non ci sono già tag p o br
    if '<br' not in cleaned and '<p>' not in cleaned:
        cleaned = cleaned.replace('\n', '<br>')
    
    # Ritorna come Markup (safe HTML)
    return Markup(cleaned)

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
