# LIFE - WORKFORCE MANAGEMENT CORE
# Essential utilities and configuration for Flask application
# All feature routes migrated to respective blueprint modules
# Flask Core Imports
from flask import render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required
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
    """Main entry point - redirect to appropriate dashboard or login"""
    if current_user.is_authenticated:
        # SUPERADMIN sees company dashboard
        if current_user.is_system_admin:
            from models import Company, User
            companies = Company.query.order_by(Company.created_at.desc()).all()
            
            # Calculate statistics for each company
            company_stats = []
            for company in companies:
                # Get active users count
                active_users = company.users.filter_by(active=True).count()
                
                # Get company admin
                admin = company.users.filter_by(role='Amministratore').first()
                
                stats = {
                    'company': company,
                    'active_users': active_users,
                    'total_users': company.users.count(),
                    'admin': admin,
                    'sedi_count': company.sedi.count(),
                    'usage_percent': round((active_users / company.max_licenses * 100) if company.max_licenses > 0 else 0)
                }
                company_stats.append(stats)
            
            return render_template('dashboard_superadmin.html', company_stats=company_stats)
        
        # Regular users see home page with FLOW and CIRCLE buttons
        return redirect(url_for('home'))
    return redirect(url_for('auth.login'))

@app.route('/home')
@login_required
def home():
    """Home page with FLOW and CIRCLE sections"""
    from models import PlatformNews
    # Get active news ordered by priority
    news_list = PlatformNews.get_active_news()
    return render_template('home.html', news_list=news_list)
