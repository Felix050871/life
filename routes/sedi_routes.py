"""
Sedi Management Routes  
Handles all sede-related operations including management and viewing
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from routes.shared_utils import require_login
from models import User, db

sedi_bp = Blueprint('sedi', __name__, url_prefix='/sedi')

@sedi_bp.route('/manage')
@login_required
@require_login
def manage_sedi():
    """Manage sedi page"""
    if not current_user.can_manage_sedi():
        flash('Non hai i permessi per gestire le sedi.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('sedi/manage.html')

@sedi_bp.route('/view')
@login_required 
@require_login
def view_sedi():
    """View sedi page"""
    if not current_user.can_view_sedi():
        flash('Non hai i permessi per visualizzare le sedi.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('sedi/view.html')