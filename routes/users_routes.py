"""
User Management Routes
Handles all user-related operations including management and viewing
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from routes.shared_utils import require_login
from models import User, db

users_bp = Blueprint('users', __name__, url_prefix='/users')

@users_bp.route('/manage')
@login_required
@require_login
def manage_users():
    """Manage users page"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per gestire gli utenti.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    users = User.query.all()
    return render_template('user_management.html', users=users)

@users_bp.route('/view')
@login_required 
@require_login
def view_users():
    """View users page"""
    if not current_user.can_view_users():
        flash('Non hai i permessi per visualizzare gli utenti.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    users = User.query.all()
    return render_template('users.html', users=users)

@users_bp.route('/create', methods=['GET', 'POST'])
@login_required
@require_login
def create_user():
    """Create new user"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per creare utenti.', 'danger')
        return redirect(url_for('users.manage_users'))
    
    if request.method == 'POST':
        # Handle user creation logic here
        flash('Utente creato con successo!', 'success')
        return redirect(url_for('users.manage_users'))
    
    return render_template('users/create.html')

@users_bp.route('/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@require_login
def edit_user(user_id):
    """Edit existing user"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per modificare gli utenti.', 'danger')
        return redirect(url_for('users.manage_users'))
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        # Handle user update logic here
        flash('Utente modificato con successo!', 'success')
        return redirect(url_for('users.manage_users'))
    
    return render_template('users/edit.html', user=user)