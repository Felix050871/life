"""
Session API Blueprint - AJAX endpoints for session management
Provides heartbeat and status checking for inactivity timeout system.
"""

from flask import Blueprint, jsonify, session as flask_session
from flask_login import login_required, current_user
from services import session_manager
import logging

logger = logging.getLogger(__name__)

# Create blueprint
session_api_bp = Blueprint('session_api', __name__, url_prefix='/api/session')


@session_api_bp.route('/heartbeat', methods=['POST'])
@login_required
def heartbeat():
    """
    Update last_activity timestamp (heartbeat ping).
    Called by JavaScript on user activity (mouse/keyboard events).
    
    Returns:
        JSON: {success: bool, seconds_remaining: int}
    """
    session_id = flask_session.get('session_uuid')
    
    if not session_id:
        logger.warning(f"Heartbeat called with no session_uuid for user {current_user.id}")
        return jsonify({'success': False, 'error': 'No session found'}), 401
    
    # Update activity timestamp
    success = session_manager.update_activity(session_id)
    
    if not success:
        logger.warning(f"Failed to update activity for session {session_id[:8]}")
        return jsonify({'success': False, 'error': 'Session not found'}), 404
    
    # Return time remaining
    time_remaining = session_manager.get_session_time_remaining(session_id)
    
    return jsonify({
        'success': True,
        'seconds_remaining': time_remaining
    }), 200


@session_api_bp.route('/status', methods=['GET'])
@login_required
def status():
    """
    Get session status (time remaining, warning flag).
    Called by JavaScript to check if warning modal should be shown.
    
    Returns:
        JSON: {
            active: bool,
            seconds_remaining: int,
            warning: bool (true if within warning threshold),
            warning_threshold: int (seconds before expiry to show warning)
        }
    """
    session_id = flask_session.get('session_uuid')
    
    if not session_id:
        return jsonify({
            'active': False,
            'seconds_remaining': 0,
            'warning': False,
            'warning_threshold': 0
        }), 200
    
    # Check if session exists and is active
    user_session = session_manager.get_current_session()
    
    if not user_session:
        return jsonify({
            'active': False,
            'seconds_remaining': 0,
            'warning': False,
            'warning_threshold': 0
        }), 200
    
    # Get time remaining and warning threshold
    time_remaining = session_manager.get_session_time_remaining(session_id)
    warning_threshold = session_manager.get_session_warning_threshold()
    
    # Check if session has expired
    is_active = time_remaining > 0
    
    # Clamp seconds_remaining to 0 (never negative)
    seconds_remaining = max(0, time_remaining)
    
    # Determine if warning should be shown (only when still active)
    warning = time_remaining <= warning_threshold and time_remaining > 0
    
    return jsonify({
        'active': is_active,
        'seconds_remaining': seconds_remaining,
        'warning': warning,
        'warning_threshold': warning_threshold
    }), 200


@session_api_bp.route('/extend', methods=['POST'])
@login_required
def extend():
    """
    Extend session (same as heartbeat but explicit intent).
    Called when user clicks "Rimani connesso" in warning modal.
    
    Returns:
        JSON: {success: bool, seconds_remaining: int}
    """
    session_id = flask_session.get('session_uuid')
    
    if not session_id:
        return jsonify({'success': False, 'error': 'No session found'}), 401
    
    # Update activity timestamp (extends session)
    success = session_manager.update_activity(session_id)
    
    if not success:
        return jsonify({'success': False, 'error': 'Session not found'}), 404
    
    # Return new time remaining
    time_remaining = session_manager.get_session_time_remaining(session_id)
    
    logger.info(f"Session {session_id[:8]} extended by user {current_user.id}")
    
    return jsonify({
        'success': True,
        'seconds_remaining': time_remaining,
        'message': 'Sessione estesa con successo'
    }), 200
