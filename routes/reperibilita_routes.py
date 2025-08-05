"""
Reperibilita Management Routes
Handles all reperibilita-related operations including coverage, shifts, and interventions
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from routes.shared_utils import require_login
from models import User, db

reperibilita_bp = Blueprint('reperibilita', __name__, url_prefix='/reperibilita')

@reperibilita_bp.route('/generate')
@login_required
@require_login
def generate_shifts():
    """Generate reperibilita shifts"""
    if not current_user.can_manage_reperibilita():
        flash('Non hai i permessi per generare turni di reperibilità.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('generate_reperibilita_shifts.html')

@reperibilita_bp.route('/shifts')
@login_required
@require_login
def reperibilita_shifts():
    """Reperibilita shifts page"""
    if not (current_user.can_manage_reperibilita() or current_user.can_view_reperibilita()):
        flash('Non hai i permessi per accedere ai turni di reperibilità.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('reperibilita_shifts.html')

@reperibilita_bp.route('/coverage')
@login_required
@require_login
def coverage():
    """Reperibilita coverage page"""
    if not (current_user.can_manage_coverage() or current_user.can_view_coverage()):
        flash('Non hai i permessi per accedere alle coperture di reperibilità.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('reperibilita_coverage.html')

@reperibilita_bp.route('/interventions')
@login_required
@require_login
def interventions():
    """Reperibilita interventions page"""
    if not (current_user.can_manage_interventions() or current_user.can_view_interventions()):
        flash('Non hai i permessi per accedere agli interventi.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('my_interventions.html')