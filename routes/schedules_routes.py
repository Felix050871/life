"""
Schedules Management Routes
Handles all schedule-related operations including management and viewing  
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from routes.shared_utils import require_login
from models import User, db

schedules_bp = Blueprint('schedules', __name__, url_prefix='/schedules')

@schedules_bp.route('/manage')
@login_required
@require_login
def manage_schedules():
    """Manage schedules page"""
    if not current_user.can_manage_schedules():
        flash('Non hai i permessi per gestire gli orari.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('manage_work_schedules.html')

@schedules_bp.route('/view')
@login_required 
@require_login
def view_schedules():
    """View schedules page"""
    if not current_user.can_view_schedules():
        flash('Non hai i permessi per visualizzare gli orari.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('manage_work_schedules.html')