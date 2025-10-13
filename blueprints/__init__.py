# =============================================================================
# ROUTES PACKAGE - FLASK BLUEPRINTS
# Modular organization of Life routes using Flask Blueprints
# =============================================================================

from flask import Flask

def register_blueprints(app: Flask):
    """Register all blueprints with the Flask application"""
    
    # Import and register authentication blueprint
    from .auth import auth_bp
    app.register_blueprint(auth_bp)
    
    # Import and register holidays blueprint  
    from .holidays import holidays_bp
    app.register_blueprint(holidays_bp)
    
    print(f"✓ Registered {len(app.blueprints)} blueprints")