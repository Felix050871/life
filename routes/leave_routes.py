"""
Leave Management Routes
Handles all leave-related operations including requests, types, and management
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from routes.shared_utils import require_login
from models import User, db

leave_bp = Blueprint('leave', __name__, url_prefix='/leave')

@leave_bp.route('/requests')
@login_required
@require_login
def leave_requests():
    """Leave requests page"""
    if not (current_user.can_manage_leave_requests() or current_user.can_view_leave_requests()):
        flash('Non hai i permessi per accedere alle richieste di congedo.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('leave_requests.html')

@leave_bp.route('/create', methods=['GET', 'POST'])
@login_required
@require_login
def create_leave():
    """Create leave request"""
    if not current_user.can_manage_leave_requests():
        flash('Non hai i permessi per creare richieste di congedo.', 'danger')
        return redirect(url_for('leave.leave_requests'))
    
    return render_template('create_leave_request.html')

@leave_bp.route('/types')
@login_required
@require_login
def leave_types():
    """Leave types management"""
    if not (current_user.can_manage_leave_types() or current_user.can_view_leave_types()):
        flash('Non hai i permessi per accedere ai tipi di congedo.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('leave_types.html')

@leave_bp.route('/approve')
@login_required
@require_login
def approve_leave():
    """Approve leave requests"""
    if not current_user.can_approve_leave_requests():
        flash('Non hai i permessi per approvare richieste di congedo.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('leave_requests.html')

@leave_bp.route('/view')
@login_required
@require_login
def view_leave():
    """View leave requests"""
    if not current_user.can_view_leave_requests():
        flash('Non hai i permessi per visualizzare le richieste di congedo.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('leave_requests.html')