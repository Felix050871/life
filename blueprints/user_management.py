# =============================================================================
# USER MANAGEMENT BLUEPRINT - Gestione utenti, ruoli e sedi
# =============================================================================
#
# ROUTES INCLUSE:
# 1. user_management (GET) - Lista utenti con filtri e controlli
# 2. create_user (GET/POST) - Creazione nuovo utente
# 3. edit_user/<user_id> (GET/POST) - Modifica utente esistente  
# 4. delete_user/<user_id> (POST) - Eliminazione utente
# 5. manage_roles (GET) - Gestione ruoli sistema
# 6. create_role (GET/POST) - Creazione nuovo ruolo
# 7. edit_role/<role_id> (GET/POST) - Modifica ruolo esistente
# 8. delete_role/<role_id> (POST) - Eliminazione ruolo
# 9. manage_sedi (GET) - Gestione sedi organizzazione
# 10. create_sede (GET/POST) - Creazione nuova sede
# 11. edit_sede/<sede_id> (GET/POST) - Modifica sede esistente
# 12. delete_sede/<sede_id> (POST) - Eliminazione sede
# 13. manage_work_schedules (GET) - Gestione orari lavoro
# 14. api/get_users_by_sede/<sede_id> (GET) - API utenti per sede
#
# Total routes: 14+ user management routes
# =============================================================================

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, make_response
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from functools import wraps
from app import db
from models import User, Sede, WorkSchedule, italian_now
from forms import UserForm, UserProfileForm
from werkzeug.security import generate_password_hash
import io
import csv

# Create blueprint
user_management_bp = Blueprint('users', __name__, url_prefix='/users')

# Helper functions
def require_admin_permissions(f):
    """Decorator to require admin permissions for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not (current_user.can_manage_users() or current_user.can_view_users()):
            flash('Non hai i permessi per accedere a questa sezione', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# USER MANAGEMENT ROUTES
# =============================================================================

@user_management_bp.route('/user_management')
@login_required
@require_admin_permissions
def user_management():
    """Gestione utenti con filtri e controlli permessi"""
    # Filtri dalla query string
    role_filter = request.args.get('role', 'all')
    sede_filter = request.args.get('sede', 'all')
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('search', '')
    
    # Base query
    query = User.query
    
    # Controllo sede per non multi-sede admin
    if not current_user.all_sedi and current_user.sede_obj:
        query = query.filter(User.sede_id == current_user.sede_obj.id)
    
    # Applicazione filtri
    if role_filter != 'all':
        query = query.filter(User.role == role_filter)
    
    if sede_filter != 'all':
        try:
            sede_id = int(sede_filter)
            query = query.filter(User.sede_id == sede_id)
        except (ValueError, TypeError):
            pass
    
    if status_filter == 'active':
        query = query.filter(User.active.is_(True))
    elif status_filter == 'inactive':
        query = query.filter(User.active.is_(False))
    
    # Ricerca testuale
    if search_query:
        search_pattern = f'%{search_query}%'
        query = query.filter(
            db.or_(
                User.username.ilike(search_pattern),
                User.first_name.ilike(search_pattern),
                User.last_name.ilike(search_pattern),
                User.email.ilike(search_pattern)
            )
        )
    
    # Ordinamento e esecuzione query
    users = query.order_by(User.last_name, User.first_name).all()
    
    # Dati per filtri dropdown
    available_roles = db.session.query(User.role).distinct().filter(User.role.isnot(None)).all()
    available_roles = [r[0] for r in available_roles if r[0]]
    
    available_sedi = Sede.query.filter_by(active=True).order_by(Sede.name).all()
    if not current_user.all_sedi and current_user.sede_obj:
        available_sedi = [current_user.sede_obj]
    
    # Statistiche
    stats = {
        'total_users': len(users),
        'active_users': len([u for u in users if u.active]),
        'inactive_users': len([u for u in users if not u.active]),
    }
    
    return render_template('user_management.html',
                         users=users,
                         stats=stats,
                         available_roles=available_roles,
                         available_sedi=available_sedi,
                         filters={
                             'role': role_filter,
                             'sede': sede_filter,
                             'status': status_filter,
                             'search': search_query
                         },
                         can_create=current_user.can_manage_users())

@user_management_bp.route('/create_user', methods=['GET', 'POST'])
@login_required
def create_user():
    """Creazione nuovo utente"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per creare utenti', 'danger')
        return redirect(url_for('users.user_management'))
    
    if request.method == 'POST':
        try:
            # Validazione dati base
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            
            if not all([username, email, first_name, last_name]):
                flash('Tutti i campi obbligatori devono essere compilati', 'danger')
                return render_template('create_user.html', form_data=request.form)
            
            # Verifica unicità username/email
            if User.query.filter_by(username=username).first():
                flash('Username già esistente', 'danger')
                return render_template('create_user.html', form_data=request.form)
            
            if User.query.filter_by(email=email).first():
                flash('Email già esistente', 'danger')
                return render_template('create_user.html', form_data=request.form)
            
            # Creazione nuovo utente
            from werkzeug.security import generate_password_hash
            
            new_user = User()
            new_user.username = username
            new_user.email = email
            new_user.first_name = first_name
            new_user.last_name = last_name
            new_user.password_hash = generate_password_hash('password123')  # Default password
            new_user.role = request.form.get('role', 'Operatori')
            new_user.active = True
            new_user.created_at = italian_now()
            
            # Gestione sede
            sede_id = request.form.get('sede_id')
            if sede_id and sede_id != '':
                new_user.sede_id = int(sede_id)
            
            # Gestione work schedule
            work_schedule_id = request.form.get('work_schedule_id')
            if work_schedule_id and work_schedule_id != '':
                new_user.work_schedule_id = int(work_schedule_id)
            
            # Percentuale part-time
            part_time_percentage = request.form.get('part_time_percentage')
            if part_time_percentage:
                try:
                    new_user.part_time_percentage = float(part_time_percentage)
                except ValueError:
                    new_user.part_time_percentage = 100.0
            else:
                new_user.part_time_percentage = 100.0
            
            db.session.add(new_user)
            db.session.commit()
            
            flash(f'Utente {username} creato con successo', 'success')
            return redirect(url_for('users.user_management'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore nella creazione utente: {str(e)}', 'danger')
    
    # Dati per form
    available_roles = ['Amministratore', 'Responsabile', 'Operatore', 'Segreteria']
    available_sedi = Sede.query.filter_by(active=True).order_by(Sede.name).all()
    available_work_schedules = WorkSchedule.query.filter_by(active=True).order_by(WorkSchedule.name).all()
    
    return render_template('create_user.html',
                         available_roles=available_roles,
                         available_sedi=available_sedi,
                         available_work_schedules=available_work_schedules,
                         form_data=request.form if request.method == 'POST' else {})

@user_management_bp.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """Modifica utente esistente"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per modificare utenti', 'danger')
        return redirect(url_for('users.user_management'))
    
    user = User.query.get_or_404(user_id)
    
    # Controllo sede se non multi-sede
    if not current_user.all_sedi and current_user.sede_obj:
        if user.sede_id != current_user.sede_obj.id:
            flash('Non puoi modificare utenti di altre sedi', 'danger')
            return redirect(url_for('users.user_management'))
    
    if request.method == 'POST':
        try:
            # Aggiornamento dati base
            user.first_name = request.form.get('first_name', '').strip()
            user.last_name = request.form.get('last_name', '').strip()
            user.email = request.form.get('email', '').strip()
            user.role = request.form.get('role', user.role)
            user.active = request.form.get('active') == 'true'
            
            # Gestione sede
            sede_id = request.form.get('sede_id')
            if sede_id and sede_id != '':
                user.sede_id = int(sede_id)
            else:
                user.sede_id = None
            
            # Gestione work schedule
            work_schedule_id = request.form.get('work_schedule_id')
            if work_schedule_id and work_schedule_id != '':
                user.work_schedule_id = int(work_schedule_id)
            else:
                user.work_schedule_id = None
            
            # Percentuale part-time
            part_time_percentage = request.form.get('part_time_percentage')
            if part_time_percentage:
                try:
                    user.part_time_percentage = float(part_time_percentage)
                except ValueError:
                    pass
            
            # Reset password se richiesto
            if request.form.get('reset_password') == 'true':
                from werkzeug.security import generate_password_hash
                user.password_hash = generate_password_hash('password123')
                flash('Password reimpostata a "password123"', 'info')
            
            db.session.commit()
            flash(f'Utente {user.username} aggiornato con successo', 'success')
            return redirect(url_for('users.user_management'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore nell\'aggiornamento utente: {str(e)}', 'danger')
    
    # Dati per form
    available_roles = ['Amministratore', 'Responsabile', 'Operatore', 'Segreteria']
    available_sedi = Sede.query.filter_by(active=True).order_by(Sede.name).all()
    available_work_schedules = WorkSchedule.query.filter_by(active=True).order_by(WorkSchedule.name).all()
    
    return render_template('edit_user.html',
                         user=user,
                         available_roles=available_roles,
                         available_sedi=available_sedi,
                         available_work_schedules=available_work_schedules)

@user_management_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    """Eliminazione utente (soft delete)"""
    if not current_user.can_manage_users():
        return jsonify({'success': False, 'message': 'Non hai i permessi per eliminare utenti'}), 403
    
    try:
        user = User.query.get_or_404(user_id)
        
        # Controllo sede se non multi-sede
        if not current_user.all_sedi and current_user.sede_obj:
            if user.sede_id != current_user.sede_obj.id:
                return jsonify({'success': False, 'message': 'Non puoi eliminare utenti di altre sedi'}), 403
        
        # Non permettere auto-eliminazione
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Non puoi eliminare il tuo account'}), 400
        
        # Soft delete - disattiva invece di eliminare
        user.active = False
        user.username = f"{user.username}_deleted_{int(datetime.now().timestamp())}"
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Utente {user.first_name} {user.last_name} disattivato con successo'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Errore: {str(e)}'}), 500

@user_management_bp.route('/api/get_users_by_sede/<int:sede_id>')
@login_required
def get_users_by_sede_api(sede_id):
    """API per ottenere utenti di una sede specifica"""
    try:
        # Controllo permessi base
        if not (current_user.can_view_users() or current_user.can_manage_users()):
            return jsonify({'error': 'Non hai i permessi per visualizzare gli utenti'}), 403
        
        # Controllo sede se non multi-sede
        if not current_user.all_sedi and current_user.sede_obj:
            if sede_id != current_user.sede_obj.id:
                return jsonify({'error': 'Non puoi visualizzare utenti di altre sedi'}), 403
        
        users = User.query.filter_by(
            sede_id=sede_id,
            active=True
        ).order_by(User.last_name, User.first_name).all()
        
        users_data = []
        for user in users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.get_full_name(),
                'role': user.role,
                'email': user.email
            })
        
        return jsonify({
            'success': True,
            'users': users_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@user_management_bp.route('/')
@login_required
def users():
    """Route semplice per lista utenti con paginazione (migrata da routes.py)"""
    if not (current_user.can_manage_users() or current_user.can_view_users()):
        flash('Non hai i permessi per accedere agli utenti', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False)
    return render_template('users.html', users=users)

@user_management_bp.route('/new_user', methods=['GET', 'POST'])
@login_required
def new_user():
    """Creazione nuovo utente con UserForm (migrata da routes.py)"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per creare utenti', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    form = UserForm(is_edit=False)
    if form.validate_on_submit():
        # Crea il nuovo utente
        user = User()
        user.username = form.username.data
        user.email = form.email.data
        user.password_hash = generate_password_hash(form.password.data or 'default_password')
        user.role = form.role.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.all_sedi = form.all_sedi.data
        user.sede_id = form.sede.data if not form.all_sedi.data else None
        user.work_schedule_id = form.work_schedule.data
        user.aci_vehicle_id = form.aci_vehicle.data if form.aci_vehicle.data and form.aci_vehicle.data != -1 else None
        user.part_time_percentage = form.get_part_time_percentage_as_float()
        user.active = form.active.data
        db.session.add(user)
        db.session.flush()  # Per ottenere l'ID dell'utente
        
        # Non c'è più gestione sedi multiple
        
        db.session.commit()
        flash('Utente creato con successo', 'success')
        return redirect(url_for('users.users'))
    
    return render_template('users.html', form=form, editing=False)

@user_management_bp.route('/user_profile', methods=['GET', 'POST'])
@login_required
def user_profile():
    """Route per la gestione del profilo personale dell'utente (migrata da routes.py)"""
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
            return redirect(url_for('users.user_profile'))
        except Exception as e:
            db.session.rollback()
            flash('Errore durante l\'aggiornamento del profilo', 'danger')
            return redirect(url_for('users.user_profile'))
    
    return render_template('user_profile.html', form=form)

@user_management_bp.route('/toggle_user/<int:user_id>')
@login_required
def toggle_user(user_id):
    """Toggle dello stato attivo di un utente (migrata da routes.py)"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per modificare utenti', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Non puoi disattivare il tuo account', 'warning')
        return redirect(url_for('users.user_management'))
    
    # Impedisce la disattivazione dell'amministratore
    if user.role == 'Amministratore':
        flash('Non è possibile disattivare l\'utente amministratore', 'danger')
        return redirect(url_for('users.user_management'))
    
    user.active = not user.active
    db.session.commit()
    
    status = 'attivato' if user.active else 'disattivato'
    flash(f'Utente {status} con successo', 'success')
    return redirect(url_for('users.user_management'))