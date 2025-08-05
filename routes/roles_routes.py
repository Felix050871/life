"""
Role Management Routes
Handles all role-related operations including management and viewing
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from routes.shared_utils import require_login
from models import User, db

roles_bp = Blueprint('roles', __name__, url_prefix='/roles')

@roles_bp.route('/manage')
@login_required
@require_login
def manage_roles():
    """Manage roles page"""
    if not current_user.can_manage_roles():
        flash('Non hai i permessi per gestire i ruoli.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('manage_roles.html')

@roles_bp.route('/view')
@login_required 
@require_login
def view_roles():
    """View roles page"""
    if not current_user.can_view_roles():
        flash('Non hai i permessi per visualizzare i ruoli.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('manage_roles.html')