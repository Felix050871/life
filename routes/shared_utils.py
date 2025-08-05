"""
Shared utilities for routes modules
Common functions and decorators used across multiple route blueprints
"""

from functools import wraps
from flask import redirect, url_for, request
from flask_login import current_user
from urllib.parse import urlparse, urljoin

def require_login(f):
    """Decorator to require login for routes"""
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
    
    # Check if the test URL is on the same domain
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc