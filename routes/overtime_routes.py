"""
Overtime Management Routes
Handles all overtime-related operations including requests, types, and management
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from routes.shared_utils import require_login
from models import User, db

overtime_bp = Blueprint('overtime', __name__, url_prefix='/overtime')

@overtime_bp.route('/requests')
@login_required
@require_login
def overtime_requests():
    """Overtime requests page"""
    if not (current_user.can_manage_overtime_requests() or current_user.can_view_overtime_requests()):
        flash('Non hai i permessi per accedere alle richieste di straordinario.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('overtime_requests.html')

@overtime_bp.route('/create', methods=['GET', 'POST'])
@login_required
@require_login
def create_overtime():
    """Create overtime request"""
    if not current_user.can_manage_overtime_requests():
        flash('Non hai i permessi per creare richieste di straordinario.', 'danger')
        return redirect(url_for('overtime.overtime_requests'))
    
    return render_template('create_overtime_request.html')

@overtime_bp.route('/types')
@login_required
@require_login
def overtime_types():
    """Overtime types management"""
    if not (current_user.can_manage_overtime_types() or current_user.can_view_overtime_types()):
        flash('Non hai i permessi per accedere ai tipi di straordinario.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('overtime_types.html')

@overtime_bp.route('/manage')
@login_required
@require_login
def manage_overtime():
    """Manage overtime requests"""
    if not current_user.can_manage_overtime_requests():
        flash('Non hai i permessi per gestire le richieste di straordinario.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('overtime_requests.html')