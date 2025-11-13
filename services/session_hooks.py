"""
Session Hooks - Before Request Handler
Enforce inactivity timeout and session validation on every authenticated request.

Integrates with Flask-Login and session_manager to:
- Validate active sessions
- Check expiration
- Trigger warnings
- Auto-logout on timeout
"""

from flask import session as flask_session, redirect, url_for, request, g
from flask_login import current_user, logout_user
from services import session_manager
import logging

logger = logging.getLogger(__name__)


def check_session_validity():
    """
    Before request hook to validate and enforce session inactivity timeout.
    
    Flow:
    1. Skip for unauthenticated users and static assets
    2. Check if session_uuid exists in Flask session
    3. Validate session against database
    4. Check expiration
    5. Update activity (heartbeat)
    6. Set warning flag if near expiry
    """
    
    # Skip for unauthenticated users
    if not current_user.is_authenticated:
        return
    
    # Skip for static assets and session API endpoints
    if request.endpoint and (
        request.endpoint == 'static' or 
        request.endpoint.startswith('session_api.')
    ):
        return
    
    # Get session ID from Flask session
    session_id = flask_session.get('session_uuid')
    
    # No session UUID - create one (migration scenario) or logout
    if not session_id:
        logger.warning(f"No session_uuid for authenticated user {current_user.id}, logging out")
        logout_user()
        flask_session.clear()
        
        # Redirect to tenant-specific login if in tenant context
        from middleware_tenant import get_tenant_slug
        tenant_slug = get_tenant_slug()
        if tenant_slug:
            return redirect(url_for('auth.tenant_login', slug=tenant_slug))
        return redirect(url_for('auth.admin_login'))
    
    # Get session from database
    user_session = session_manager.get_current_session()
    
    # Session not found or inactive - logout
    if not user_session:
        logger.warning(f"Session {session_id[:8]}... not found or inactive, logging out user {current_user.id}")
        logout_user()
        flask_session.clear()
        
        # Redirect to tenant-specific login if in tenant context
        from middleware_tenant import get_tenant_slug
        tenant_slug = get_tenant_slug()
        if tenant_slug:
            return redirect(url_for('auth.tenant_login', slug=tenant_slug))
        return redirect(url_for('auth.admin_login'))
    
    # Check if session is expired
    if session_manager.is_session_expired(session_id):
        logger.info(f"Session {session_id[:8]}... expired for user {current_user.id}, logging out")
        session_manager.invalidate_session(session_id, reason='timeout')
        logout_user()
        flask_session.clear()
        
        # Redirect to tenant-specific login if in tenant context
        from middleware_tenant import get_tenant_slug
        tenant_slug = get_tenant_slug()
        if tenant_slug:
            return redirect(url_for('auth.tenant_login', slug=tenant_slug))
        return redirect(url_for('auth.admin_login'))
    
    # Update last_activity (heartbeat) - only for non-API requests
    # API heartbeat endpoint handles its own updates
    if not request.path.startswith('/api/session/'):
        session_manager.update_activity(session_id)
    
    # Check if warning should be shown
    time_remaining = session_manager.get_session_time_remaining(session_id)
    warning_threshold = session_manager.get_session_warning_threshold()
    
    # Set warning flag in g context for templates
    if time_remaining <= warning_threshold and time_remaining > 0:
        g.session_warning = True
        g.session_warning_seconds = time_remaining
    else:
        g.session_warning = False
        g.session_warning_seconds = time_remaining
    
    # No issues - continue with request
    return None
