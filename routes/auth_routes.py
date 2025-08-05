"""
Authentication and User Management Routes
Handles login, logout, user management, and profile operations
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from sqlalchemy.orm import joinedload

from app import app, db
from models import User, UserRole, Sede, WorkSchedule, PasswordResetToken, italian_now
from forms import LoginForm, UserForm, UserProfileForm, ForgotPasswordForm, ResetPasswordForm
from utils import get_team_statistics
from .shared_utils import is_safe_url

# Create blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect('/dashboard')  # Temporary direct URL until dashboard is moved
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.password_hash and check_password_hash(user.password_hash, form.password.data):
            if user.active:
                login_user(user, remember=form.remember_me.data)
                next_page = request.args.get('next')
                if not next_page or not is_safe_url(next_page):
                    next_page = '/dashboard'  # Temporary direct URL
                return redirect(next_page)
            else:
                flash('Account disattivato. Contatta l\'amministratore.', 'warning')
        else:
            flash('Nome utente o password non validi', 'danger')
    
    return render_template('login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout effettuato con successo', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/user_management')
@login_required
def user_management():
    if not (current_user.can_manage_users() or current_user.can_view_users()):
        flash('Non hai i permessi per accedere alla gestione utenti', 'danger')
        return redirect('/dashboard')
    
    # Applica filtro automatico per sede usando il metodo helper
    users_query = User.get_visible_users_query(current_user).options(joinedload(User.sede_obj))
    users = users_query.order_by(User.created_at.desc()).all()
    
    # Determina il nome della sede per il titolo
    sede_name = None if current_user.all_sedi else (current_user.sede_obj.name if current_user.sede_obj else None)
    form = UserForm(is_edit=False)
    
    # Aggiungi statistiche team per le statistiche utenti dinamiche
    team_stats = None
    if current_user.can_view_team_stats_widget():
        team_stats = get_team_statistics()
    
    return render_template('user_management.html', users=users, form=form, 
                         sede_name=sede_name, is_multi_sede=current_user.all_sedi,
                         team_stats=team_stats)

@auth_bp.route('/user_profile', methods=['GET', 'POST'])
@login_required
def user_profile():
    """Route per la gestione del profilo personale dell'utente"""
    form = UserProfileForm(original_email=current_user.email, obj=current_user)
    
    if request.method == 'GET':
        # Popola i campi con i dati attuali dell'utente
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.email.data = current_user.email
        form.username.data = current_user.username
    
    if form.validate_on_submit():
        # Aggiorna i dati del profilo
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.email = form.email.data
        
        # Aggiorna la password solo se fornita
        if form.password.data:
            current_user.password_hash = generate_password_hash(form.password.data)
            flash('Password aggiornata con successo', 'success')
        
        try:
            db.session.commit()
            flash('Profilo aggiornato con successo', 'success')
            return redirect(url_for('auth.user_profile'))
        except Exception as e:
            db.session.rollback()
            flash('Errore durante l\'aggiornamento del profilo', 'danger')
    
    return render_template('user_profile.html', form=form, user=current_user)

@auth_bp.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if not current_user.can_manage_users():
        flash('Non hai i permessi per modificare utenti', 'danger')
        return redirect(url_for('auth.user_management'))
    
    user = User.query.get_or_404(user_id)
    
    # Verifica che l'utente corrente possa vedere questo utente
    visible_users = User.get_visible_users_query(current_user).all()
    if user not in visible_users:
        flash('Non hai i permessi per modificare questo utente', 'danger')
        return redirect(url_for('auth.user_management'))
    
    form = UserForm(is_edit=True, obj=user)
    
    if form.validate_on_submit():
        # Aggiorna i dati dell'utente
        user.username = form.username.data
        user.email = form.email.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.role = form.role.data
        user.all_sedi = form.all_sedi.data
        user.sede_id = form.sede.data if not form.all_sedi.data else None
        user.work_schedule_id = form.work_schedule.data
        user.aci_vehicle_id = form.aci_vehicle.data if form.aci_vehicle.data and form.aci_vehicle.data != -1 else None
        user.part_time_percentage = form.get_part_time_percentage_as_float()
        user.active = form.active.data
        
        # Aggiorna la password solo se fornita
        if form.password.data:
            user.password_hash = generate_password_hash(form.password.data)
        
        try:
            db.session.commit()
            flash('Utente aggiornato con successo', 'success')
            return redirect(url_for('auth.user_management'))
        except Exception as e:
            db.session.rollback()
            flash('Errore durante l\'aggiornamento dell\'utente', 'danger')
    
    return render_template('edit_user.html', form=form, user=user)

@auth_bp.route('/toggle_user/<int:user_id>', methods=['POST'])
@login_required
def toggle_user(user_id):
    if not current_user.can_manage_users():
        flash('Non hai i permessi per modificare utenti', 'danger')
        return redirect(url_for('auth.user_management'))
    
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('Non puoi disattivare il tuo account', 'warning')
        return redirect(url_for('auth.user_management'))
    
    if user.role == 'Amministratore':
        flash('Non è possibile disattivare un amministratore', 'warning')
        return redirect(url_for('auth.user_management'))
    
    user.active = not user.active
    db.session.commit()
    
    status = "attivato" if user.active else "disattivato"
    flash(f'Utente {user.get_full_name()} {status} con successo', 'success')
    
    return redirect(url_for('auth.user_management'))

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.password_hash and check_password_hash(user.password_hash, form.current_password.data):
            # Generate reset token
            token = PasswordResetToken(
                user_id=user.id,
                email=user.email,
                expires_at=italian_now() + timedelta(hours=1)
            )
            db.session.add(token)
            
            # Update password
            user.password_hash = generate_password_hash(form.new_password.data)
            db.session.commit()
            
            flash('Password aggiornata con successo', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Email o password corrente non validi', 'danger')
    
    return render_template('forgot_password.html', form=form)

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    # Verify token
    reset_token = PasswordResetToken.query.filter_by(token=token, used=False).first()
    if not reset_token or reset_token.expires_at < italian_now():
        flash('Token di reset non valido o scaduto', 'danger')
        return redirect(url_for('auth.login'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.get(reset_token.user_id)
        user.password_hash = generate_password_hash(form.password.data)
        
        # Mark token as used
        reset_token.used = True
        
        db.session.commit()
        flash('Password resettata con successo', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('reset_password.html', form=form)