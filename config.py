"""
Configuration settings for Workly Workforce Management Platform

This file centralizes all configuration values to eliminate hardcoded constants
and improve maintainability. Load values from environment variables with fallbacks.
"""

import os
from datetime import timedelta

class Config:
    """Base configuration class with all application settings"""
    
    # Flask Application Settings
    SECRET_KEY = os.environ.get('SESSION_SECRET') or 'dev-secret-key-please-change-in-production'
    FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Database Configuration - Solo PostgreSQL
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is required for PostgreSQL connection")
    DATABASE_POOL_RECYCLE = int(os.environ.get('DATABASE_POOL_RECYCLE', '300'))  # 5 minutes
    DATABASE_POOL_PRE_PING = os.environ.get('DATABASE_POOL_PRE_PING', 'True').lower() == 'true'
    
    # Server Configuration
    SERVER_HOST = os.environ.get('SERVER_HOST', '0.0.0.0')
    SERVER_PORT = int(os.environ.get('SERVER_PORT', '5000'))
    
    # URLs and External Services
    BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')
    QR_CODE_API_URL = os.environ.get('QR_CODE_API_URL', 'https://api.qrserver.com/v1/create-qr-code/')
    QR_CODE_SIZE = os.environ.get('QR_CODE_SIZE', '200x200')
    
    # File Paths and Static Resources
    STATIC_QR_DIR = os.path.join('static', 'qr')
    STATIC_UPLOADS_DIR = os.path.join('static', 'uploads')
    
    # Notification and Alert Settings
    TOAST_DURATION_SUCCESS = int(os.environ.get('TOAST_DURATION_SUCCESS', '3000'))  # 3 seconds
    TOAST_DURATION_ERROR = int(os.environ.get('TOAST_DURATION_ERROR', '5000'))     # 5 seconds
    
    # Security Settings
    SESSION_TIMEOUT = timedelta(hours=int(os.environ.get('SESSION_TIMEOUT_HOURS', '8')))
    PASSWORD_RESET_TIMEOUT = timedelta(hours=int(os.environ.get('PASSWORD_RESET_TIMEOUT_HOURS', '1')))
    
    # Application Limits and Constraints
    MAX_UPLOAD_SIZE = int(os.environ.get('MAX_UPLOAD_SIZE', '16777216'))  # 16MB
    PAGINATION_DEFAULT_SIZE = int(os.environ.get('PAGINATION_DEFAULT_SIZE', '20'))
    
    # Role-based Access Control
    PROTECTED_ROLES = ['Amministratore']  # Roles that cannot be deleted/disabled
    EXCLUDED_ROLES_FROM_REPORTS = ['Admin', 'Ente', 'Staff']  # Legacy roles excluded from reports
    
    # QR Code Settings
    QR_CODE_VERSION = int(os.environ.get('QR_CODE_VERSION', '1'))
    QR_CODE_BOX_SIZE = int(os.environ.get('QR_CODE_BOX_SIZE', '10'))
    QR_CODE_BORDER = int(os.environ.get('QR_CODE_BORDER', '4'))
    
    # Date and Time Formatting
    DEFAULT_DATE_FORMAT = os.environ.get('DEFAULT_DATE_FORMAT', '%d/%m/%Y')
    DEFAULT_TIME_FORMAT = os.environ.get('DEFAULT_TIME_FORMAT', '%H:%M')
    DEFAULT_DATETIME_FORMAT = os.environ.get('DEFAULT_DATETIME_FORMAT', '%d/%m/%Y %H:%M')
    
    # Bootstrap and UI Theme
    BOOTSTRAP_THEME = os.environ.get('BOOTSTRAP_THEME', 'light')
    BOOTSTRAP_CSS_URL = os.environ.get('BOOTSTRAP_CSS_URL', 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css')
    FONTAWESOME_CSS_URL = os.environ.get('FONTAWESOME_CSS_URL', 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css')
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = os.environ.get('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Email Configuration (for future use)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')

class DevelopmentConfig(Config):
    """Development environment configuration"""
    FLASK_DEBUG = True
    # Development uses PostgreSQL too
    pass

class ProductionConfig(Config):
    """Production environment configuration"""
    FLASK_DEBUG = False
    # Production uses PostgreSQL (inherited from Config)

class TestingConfig(Config):
    """Testing environment configuration"""
    TESTING = True
    # For testing, still require PostgreSQL or override DATABASE_URL explicitly
    WTF_CSRF_ENABLED = False

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get the current configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])