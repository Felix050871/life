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
    from .users_routes import users_bp
    from .roles_routes import roles_bp
    from .sedi_routes import sedi_bp
    from .schedules_routes import schedules_bp
    from .shifts_routes import shifts_bp
    from .leave_routes import leave_bp
    from .overtime_routes import overtime_bp
    from .reperibilita_routes import reperibilita_bp
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(roles_bp)
    app.register_blueprint(sedi_bp)
    app.register_blueprint(schedules_bp)
    app.register_blueprint(shifts_bp)
    app.register_blueprint(leave_bp)
    app.register_blueprint(overtime_bp)
    app.register_blueprint(reperibilita_bp)