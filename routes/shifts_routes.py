"""
Shifts Management Routes  
Handles all shift-related operations including management and viewing
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from routes.shared_utils import require_login
from models import User, db

shifts_bp = Blueprint('shifts', __name__, url_prefix='/shifts')

@shifts_bp.route('/manage')
@login_required
@require_login
def manage_shifts():
    """Manage shifts page"""
    if not current_user.can_manage_shifts():
        flash('Non hai i permessi per gestire i turni.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('shifts/manage.html')

@shifts_bp.route('/view')
@login_required 
@require_login
def view_shifts():
    """View shifts page"""
    if not current_user.can_view_shifts():
        flash('Non hai i permessi per visualizzare i turni.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('shifts/view.html')

@shifts_bp.route('/coverage/manage')
@login_required
@require_login  
def manage_coverage():
    """Manage coverage page"""
    if not current_user.can_manage_shifts():
        flash('Non hai i permessi per gestire le coperture.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('shifts/coverage_manage.html')

@shifts_bp.route('/coverage/view')
@login_required
@require_login
def view_coverage():
    """View coverage page"""
    if not current_user.can_view_shifts():
        flash('Non hai i permessi per visualizzare le coperture.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('shifts/coverage_view.html')