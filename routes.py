# LIFE - WORKFORCE MANAGEMENT CORE
# Essential utilities and configuration for Flask application
# All feature routes migrated to respective blueprint modules
# Flask Core Imports
from flask import render_template, request, redirect, url_for, flash
from flask_login import current_user
# Standard Library Imports
from urllib.parse import urlparse, urljoin
# Application Imports
from app import app
from config import get_config
# No models needed for core utilities
# Blueprint registration will be handled at the end of this file
# GLOBAL CONFIGURATION AND UTILITY FUNCTIONS
@app.context_processor
def inject_config():
    """Inject configuration into all templates"""
    config = get_config()
    return dict(config=config)
def require_login(f):
    """Decorator to require login for routes"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function
def is_safe_url(target):
    """Check if a URL is safe for redirect (same domain only)"""
    if not target:
        return False
    # Parse the target URL
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    # Check if the scheme and netloc match (same domain)
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc
# CORE NAVIGATION ROUTES
@app.route('/')
def index():
    """Main entry point - show home page or redirect to login"""
    if current_user.is_authenticated:
        return render_template('home.html')
    return redirect(url_for('auth.login'))
