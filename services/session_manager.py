"""
Session Manager Service - User Session Management
Gestisce il ciclo di vita delle sessioni utente con timeout inattività, multi-tenant isolation, e audit trail.

Features:
- Create/update/invalidate sessions
- Inactivity timeout enforcement (30 min default)
- Multi-tenant session isolation
- Audit trail (user_agent, IP, timestamps)
- Automatic cleanup of expired sessions
"""

import secrets
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Dict, List
from flask import request, session as flask_session
from app import db
from models import UserSession, User, Company
from config import get_config


def generate_session_id() -> str:
    """
    Generate a cryptographically secure session ID.
    Uses secrets.token_urlsafe for ~43 chars (future-proof to 96).
    
    Returns:
        str: Secure random session ID
    """
    return secrets.token_urlsafe(32)


def create_session(
    user: User, 
    company_id: Optional[int] = None,
    tenant_slug: Optional[str] = None,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None
) -> UserSession:
    """
    Create a new user session in the database and Flask session.
    Enforces MAX_CONCURRENT_SESSIONS limit with atomic transaction + row locking.
    
    Args:
        user: User object
        company_id: Company ID (None for super-admin)
        tenant_slug: Tenant slug for URL path
        user_agent: Browser user agent string
        ip_address: Client IP address
        
    Returns:
        UserSession: Created session object
    """
    config = get_config()
    
    # Generate unique session ID
    session_id = generate_session_id()
    
    # Calculate expiration time
    now = datetime.now(ZoneInfo('UTC'))
    expires_at = now + config.INACTIVITY_TIMEOUT
    
    # Extract from request if not provided
    if user_agent is None:
        user_agent = request.headers.get('User-Agent', '')
    if ip_address is None:
        ip_address = request.remote_addr
    
    # ATOMIC TRANSACTION: Create session + enforce concurrent limit
    # Lock active sessions to prevent race conditions on concurrent logins
    active_sessions = UserSession.query.filter_by(
        user_id=user.id,
        is_active=True
    ).order_by(UserSession.created_at.asc()).with_for_update().all()
    
    # Enforce concurrent session limit (FIFO invalidation)
    max_sessions = config.MAX_CONCURRENT_SESSIONS
    if len(active_sessions) >= max_sessions:
        # Invalidate oldest sessions to make room for new one
        excess_count = len(active_sessions) - max_sessions + 1
        sessions_to_invalidate = active_sessions[:excess_count]
        
        for old_session in sessions_to_invalidate:
            old_session.is_active = False
            old_session.terminated_at = now
            old_session.invalidation_reason = 'concurrent_limit'
    
    # Create new session record
    user_session = UserSession(
        session_id=session_id,
        user_id=user.id,
        company_id=company_id,
        tenant_slug=tenant_slug,
        created_at=now,
        last_activity=now,
        expires_at=expires_at,
        is_active=True,
        user_agent=user_agent,
        ip_address=ip_address
    )
    
    db.session.add(user_session)
    db.session.commit()
    
    # Store session_id in Flask session for tracking
    flask_session['session_uuid'] = session_id
    flask_session.permanent = True  # Enable PERMANENT_SESSION_LIFETIME
    
    return user_session


def update_activity(session_id: str) -> bool:
    """
    Update the last_activity timestamp for a session (heartbeat).
    
    Args:
        session_id: Session ID to update
        
    Returns:
        bool: True if updated successfully, False if session not found
    """
    user_session = UserSession.query.filter_by(
        session_id=session_id,
        is_active=True
    ).first()
    
    if not user_session:
        return False
    
    config = get_config()
    now = datetime.now(ZoneInfo('UTC'))
    
    user_session.last_activity = now
    user_session.expires_at = now + config.INACTIVITY_TIMEOUT
    
    db.session.commit()
    return True


def invalidate_session(session_id: str, reason: str = 'manual') -> bool:
    """
    Invalidate a specific session (logout, timeout, etc.).
    
    Args:
        session_id: Session ID to invalidate
        reason: Reason for invalidation (for audit logs)
        
    Returns:
        bool: True if invalidated successfully, False if not found
    """
    user_session = UserSession.query.filter_by(session_id=session_id).first()
    
    if not user_session:
        return False
    
    user_session.is_active = False
    user_session.terminated_at = datetime.now(ZoneInfo('UTC'))
    
    db.session.commit()
    return True


def invalidate_current_session() -> bool:
    """
    Invalidate the current user's session from Flask session.
    
    Returns:
        bool: True if invalidated, False if no session found
    """
    session_id = flask_session.get('session_uuid')
    if not session_id:
        return False
    
    result = invalidate_session(session_id)
    
    # Clear Flask session
    flask_session.pop('session_uuid', None)
    
    return result


def get_active_sessions(user_id: int, company_id: Optional[int] = None) -> List[UserSession]:
    """
    Get all active sessions for a user (optionally filtered by company).
    
    Args:
        user_id: User ID
        company_id: Company ID filter (None for all companies)
        
    Returns:
        List[UserSession]: Active sessions
    """
    query = UserSession.query.filter_by(
        user_id=user_id,
        is_active=True
    )
    
    if company_id is not None:
        query = query.filter_by(company_id=company_id)
    
    return query.order_by(UserSession.last_activity.desc()).all()


def get_current_session() -> Optional[UserSession]:
    """
    Get the current user's session from Flask session.
    
    Returns:
        UserSession or None if not found/invalid
    """
    session_id = flask_session.get('session_uuid')
    if not session_id:
        return None
    
    return UserSession.query.filter_by(
        session_id=session_id,
        is_active=True
    ).first()


def is_session_expired(session_id: str) -> bool:
    """
    Check if a session has expired based on inactivity timeout.
    
    Args:
        session_id: Session ID to check
        
    Returns:
        bool: True if expired, False otherwise
    """
    user_session = UserSession.query.filter_by(session_id=session_id).first()
    
    if not user_session or not user_session.is_active:
        return True
    
    config = get_config()
    return user_session.is_expired(timeout_minutes=int(config.INACTIVITY_TIMEOUT.total_seconds() / 60))


def get_session_time_remaining(session_id: str) -> int:
    """
    Get seconds remaining before session expires.
    
    Args:
        session_id: Session ID
        
    Returns:
        int: Seconds until expiry (0 if expired/not found)
    """
    user_session = UserSession.query.filter_by(session_id=session_id).first()
    
    if not user_session or not user_session.is_active:
        return 0
    
    config = get_config()
    return user_session.time_until_expiry(timeout_minutes=int(config.INACTIVITY_TIMEOUT.total_seconds() / 60))


def cleanup_expired_sessions(batch_size: int = 1000) -> int:
    """
    Cleanup expired sessions (background job / cron).
    Marks inactive sessions as terminated.
    
    Args:
        batch_size: Maximum number of sessions to process per run
        
    Returns:
        int: Number of sessions cleaned up
    """
    config = get_config()
    now = datetime.now(ZoneInfo('UTC'))
    cutoff_time = now - config.INACTIVITY_TIMEOUT
    
    # Find expired active sessions
    expired_sessions = UserSession.query.filter(
        UserSession.is_active == True,
        UserSession.last_activity < cutoff_time
    ).limit(batch_size).all()
    
    count = 0
    for user_session in expired_sessions:
        user_session.is_active = False
        user_session.terminated_at = now
        count += 1
    
    db.session.commit()
    return count


def get_session_warning_threshold() -> int:
    """
    Get the warning threshold in seconds (when to show warning modal).
    
    Returns:
        int: Seconds before expiry to show warning
    """
    config = get_config()
    return int(config.SESSION_WARNING_TIME.total_seconds())


def cleanup_old_sessions(user_id: int, max_sessions: Optional[int] = None) -> int:
    """
    Cleanup old sessions when user exceeds max concurrent sessions limit.
    Invalidates oldest sessions (FIFO) keeping only the most recent ones.
    
    Args:
        user_id: User ID
        max_sessions: Maximum concurrent sessions allowed (default from config)
        
    Returns:
        int: Number of sessions invalidated
    """
    # Resolve max_sessions from config if not provided
    session_limit = max_sessions
    if session_limit is None:
        config = get_config()
        session_limit = config.MAX_CONCURRENT_SESSIONS
    
    # Get all active sessions for user, ordered by creation time (oldest first)
    active_sessions = UserSession.query.filter_by(
        user_id=user_id,
        is_active=True
    ).order_by(UserSession.created_at.asc()).all()
    
    # If within limit, no cleanup needed
    if len(active_sessions) <= session_limit:
        return 0
    
    # Calculate how many sessions to invalidate
    excess_count = len(active_sessions) - session_limit
    sessions_to_invalidate = active_sessions[:excess_count]
    
    # Invalidate oldest sessions
    now = datetime.now(ZoneInfo('UTC'))
    count = 0
    for user_session in sessions_to_invalidate:
        user_session.is_active = False
        user_session.terminated_at = now
        user_session.invalidation_reason = 'concurrent_limit'
        count += 1
    
    db.session.commit()
    return count
