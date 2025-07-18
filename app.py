import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Configure the database - Workly usa un database separato
workly_db_url = os.environ.get("WORKLY_DATABASE_URL")
if not workly_db_url:
    # Fallback a SQLite locale per sviluppo Workly
    workly_db_url = "sqlite:///workly.db"
    
app.config["SQLALCHEMY_DATABASE_URI"] = workly_db_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
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

# Import routes to register them with the app
import routes

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

@app.template_filter('format_time_italian')
def format_time_italian(timestamp):
    """Formatta timestamp in formato HH:MM per orario italiano"""
    if not timestamp:
        return "--:--"
    
    # Converti a orario italiano
    italian_time = to_italian_time(timestamp)
    return italian_time.strftime('%H:%M')
