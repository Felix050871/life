"""
Routes package initialization
Registers all blueprint modules for the Workly application
"""

from flask import Blueprint

def register_blueprints(app):
    """Register all application blueprints"""
    
    # Import blueprints
    from .auth_routes import auth_bp
    from .api_routes import api_bp
    from .dashboard_routes import dashboard_bp
    from .attendance_routes import attendance_bp
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(attendance_bp)