# =============================================================================
# USER MANAGEMENT BLUEPRINT
# =============================================================================
# Blueprint for managing users, roles, sedi, admin functionality, 
# API endpoints and administrative operations
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from functools import wraps

# Local imports
from models import User, Sede, UserRole, WorkSchedule
from forms import UserForm, SedeForm, RoleForm, WorkScheduleForm
from app import db
from werkzeug.security import generate_password_hash
from sqlalchemy.orm import joinedload
from utils_tenant import filter_by_company, set_company_on_create

# =============================================================================
# BLUEPRINT CONFIGURATION
# =============================================================================

user_management_bp = Blueprint(
    'user_management', 
    __name__, 
    url_prefix='/admin',
    template_folder='../templates',
    static_folder='../static'
)

# =============================================================================
# PERMISSION DECORATORS
# =============================================================================

def require_admin_permission(f):
    """Decorator to check admin permission"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.can_manage_users():
            flash('Non hai i permessi per accedere a questa funzione amministrativa', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def require_turni_permission(f):
    """Decorator to check turni management permission"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.can_access_turni():
            flash('Non hai i permessi per accedere alla gestione turni', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# QR CODE ADMINISTRATION ROUTES
# =============================================================================

@user_management_bp.route('/qr_codes')
@login_required
def admin_qr_codes():
    """Gestione codici QR - Solo per chi può gestire"""
    if not current_user.can_manage_qr():
        flash('Non hai i permessi per gestire i codici QR', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    from utils import qr_codes_exist, get_qr_code_urls
    
    # Verifica se i QR code statici esistono
    qr_exist = qr_codes_exist()
    
    # Genera URL completi per i QR codes
    base_url = request.url_root.rstrip('/')
    qr_urls = {
        'entrata': f"{base_url}/qr_login/entrata",
        'uscita': f"{base_url}/qr_login/uscita"
    }
    
    # Se esistono, ottieni gli URL per visualizzarli
    static_qr_urls = get_qr_code_urls() if qr_exist else None
    
    from config import get_config
    config = get_config()
    
    return render_template('admin_qr_codes.html', 
                         qr_urls=qr_urls,
                         qr_exist=qr_exist,
                         static_qr_urls=static_qr_urls,
                         can_manage=True,
                         config=config)

@user_management_bp.route('/generate_static_qr')
@login_required
def admin_generate_static_qr():
    """Genera QR code statici e li salva su file"""
    if not current_user.can_manage_qr():
        flash('Non hai i permessi per generare codici QR', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    from utils import generate_static_qr_codes
    
    if generate_static_qr_codes():
        flash('QR code generati con successo e salvati come file statici', 'success')
    else:
        flash('Errore nella generazione dei QR code statici', 'danger')
    
    # Forza refresh della pagina per mostrare i nuovi QR code
    return redirect(url_for('user_management.admin_qr_codes') + '?refresh=1')

@user_management_bp.route('/view/qr_codes')
@login_required
def view_qr_codes():
    """Visualizzazione codici QR - Solo per chi può visualizzare"""
    if not current_user.can_view_qr():
        flash('Non hai i permessi per visualizzare i codici QR', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    from utils import qr_codes_exist, get_qr_code_urls
    
    # Verifica se i QR code statici esistono
    qr_exist = qr_codes_exist()
    
    # Genera URL completi per i QR codes
    base_url = request.url_root.rstrip('/')
    qr_urls = {
        'entrata': f"{base_url}/qr_login/entrata",
        'uscita': f"{base_url}/qr_login/uscita"
    }
    
    # Se esistono, ottieni gli URL per visualizzarli
    static_qr_urls = get_qr_code_urls() if qr_exist else None
    
    from config import get_config
    config = get_config()
    
    return render_template('view_qr_codes.html', 
                         qr_urls=qr_urls,
                         qr_exist=qr_exist,
                         static_qr_urls=static_qr_urls,
                         can_manage=False,
                         config=config)

# =============================================================================
# API ENDPOINTS  
# =============================================================================

@user_management_bp.route('/api/sede/<int:sede_id>/users')
@login_required
def api_sede_users(sede_id):
    """API per ottenere utenti di una sede specifica"""
    if not current_user.can_view_users():
        return jsonify({'error': 'Non autorizzato'}), 403
    
    sede = filter_by_company(Sede.query, Sede).get_or_404(sede_id)
    
    # Verifica permessi sede
    if not current_user.all_sedi and current_user.sede_id != sede_id:
        return jsonify({'error': 'Accesso negato a questa sede'}), 403
    
    users = filter_by_company(User.query, User).filter_by(sede_id=sede_id, active=True).order_by(
        User.last_name, User.first_name
    ).all()
    
    users_data = []
    for user in users:
        users_data.append({
            'id': user.id,
            'name': user.get_full_name(),
            'role': user.role,
            'username': user.username,
            'email': user.email
        })
    
    return jsonify({
        'success': True,
        'sede': sede.name,
        'users': users_data,
        'count': len(users_data)
    })

@user_management_bp.route('/api/sede/<int:sede_id>/work_schedules')
@login_required
def api_sede_work_schedules(sede_id):
    """API per ottenere orari di lavoro di una sede"""
    if not current_user.can_view_work_schedules():
        return jsonify({'error': 'Non autorizzato'}), 403
    
    sede = filter_by_company(Sede.query, Sede).get_or_404(sede_id)
    
    # Verifica permessi sede
    if not current_user.all_sedi and current_user.sede_id != sede_id:
        return jsonify({'error': 'Accesso negato a questa sede'}), 403
    
    schedules = filter_by_company(WorkSchedule.query, WorkSchedule).filter_by(sede_id=sede_id, active=True).order_by(
        WorkSchedule.name
    ).all()
    
    schedules_data = []
    for schedule in schedules:
        schedules_data.append({
            'id': schedule.id,
            'name': schedule.name,
            'description': schedule.description,
            'start_time': schedule.start_time.strftime('%H:%M') if schedule.start_time else None,
            'end_time': schedule.end_time.strftime('%H:%M') if schedule.end_time else None,
            'is_shift_based': schedule.is_shift_based
        })
    
    return jsonify({
        'success': True,
        'sede': sede.name,
        'work_schedules': schedules_data,
        'count': len(schedules_data)
    })

@user_management_bp.route('/api/roles')
@login_required
def api_roles():
    """API per ottenere lista dei ruoli disponibili"""
    if not current_user.can_view_roles():
        return jsonify({'error': 'Non autorizzato'}), 403
    
    roles = filter_by_company(UserRole.query, UserRole).filter_by(active=True).order_by(UserRole.name).all()
    
    roles_data = []
    for role in roles:
        roles_data.append({
            'id': role.id,
            'name': role.name,
            'description': role.description,
            'permissions_count': len([p for p in role.__dict__ if p.startswith('can_') and getattr(role, p)])
        })
    
    return jsonify({
        'success': True,
        'roles': roles_data,
        'count': len(roles_data)
    })

# =============================================================================
# USER PROFILE ROUTES
# =============================================================================

@user_management_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def user_profile():
    """User profile page"""
    from forms import UserProfileForm
    
    form = UserProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        # Update user profile
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.email = form.email.data
        
        # Update password if provided
        if form.password.data:
            from werkzeug.security import generate_password_hash
            current_user.password_hash = generate_password_hash(form.password.data)
        
        db.session.commit()
        flash('Profilo aggiornato con successo', 'success')
        return redirect(url_for('user_management.user_profile'))
    
    return render_template('user_profile.html', user=current_user, form=form)

# =============================================================================
# USER MANAGEMENT MAIN ROUTES
# =============================================================================

@user_management_bp.route('/users')
@login_required
def user_management():
    """Main user management page"""
    if not (current_user.can_manage_users() or current_user.can_view_users()):
        flash('Non hai i permessi per accedere alla gestione utenti', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    # Get users with their roles and sedi
    users = filter_by_company(User.query, User).options(
        joinedload(User.sede_obj)
    ).all()
    
    # Create user form (only for managers)
    form = UserForm() if current_user.can_manage_users() else None
    if form:
        # Populate form choices
        form.role.choices = [(role.name, role.name) for role in filter_by_company(UserRole.query, UserRole).filter_by(active=True).all()]
        form.sede.choices = [(-1, 'Seleziona una sede')] + [(sede.id, sede.name) for sede in filter_by_company(Sede.query, Sede).filter_by(active=True).all()]
    
    return render_template('user_management.html', 
                         users=users, 
                         form=form,
                         can_manage_users=current_user.can_manage_users())

# =============================================================================
# USER CRUD OPERATIONS
# =============================================================================

@user_management_bp.route('/users/new', methods=['POST'])
@login_required
def new_user():
    """Create a new user"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per creare utenti', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    form = UserForm(is_edit=False)
    if form.validate_on_submit():
        # Crea il nuovo utente
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data),
            role=form.role.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            all_sedi=form.all_sedi.data,
            sede_id=form.sede.data if not form.all_sedi.data else None,
            work_schedule_id=form.work_schedule.data,
            aci_vehicle_id=form.aci_vehicle.data if form.aci_vehicle.data and form.aci_vehicle.data != -1 else None,
            part_time_percentage=form.get_part_time_percentage_as_float(),
            banca_ore_enabled=form.banca_ore_enabled.data,
            banca_ore_limite_max=form.get_banca_ore_limite_max_as_float(),
            banca_ore_periodo_mesi=form.get_banca_ore_periodo_mesi_as_int(),
            active=form.active.data
        )
        set_company_on_create(user)
        db.session.add(user)
        db.session.flush()  # Per ottenere l'ID dell'utente
        
        db.session.commit()
        flash('Utente creato con successo', 'success')
        return redirect(url_for('user_management.user_management'))
    
    # Se ci sono errori di validazione, torna alla pagina principale con errori
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'{field}: {error}', 'danger')
    
    return redirect(url_for('user_management.user_management'))

@user_management_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """Edit an existing user"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per modificare gli utenti', 'danger')
        return redirect(url_for('user_management.user_management'))
    
    user = filter_by_company(User.query, User).get_or_404(user_id)
    form = UserForm(original_username=user.username, is_edit=True, obj=user)
    
    if request.method == 'GET':
        # Popola i campi sede e all_sedi con i valori attuali
        form.all_sedi.data = user.all_sedi
        if user.sede_id:
            form.sede.data = user.sede_id
        
        if user.work_schedule_id:
            # Aggiungi l'orario corrente alle scelte se non già presente
            if user.work_schedule:
                schedule_choice = (user.work_schedule.id, f"{user.work_schedule.name} ({user.work_schedule.start_time.strftime('%H:%M') if user.work_schedule.start_time else ''}-{user.work_schedule.end_time.strftime('%H:%M') if user.work_schedule.end_time else ''})")
                if schedule_choice not in form.work_schedule.choices:
                    form.work_schedule.choices.append(schedule_choice)
            form.work_schedule.data = user.work_schedule_id
        else:
            # Se non ha un orario, imposta il valore di default
            form.work_schedule.data = ''
        
        # Gestione del veicolo ACI con campi progressivi
        if user.aci_vehicle_id and user.aci_vehicle:
            # Popola i campi progressivi basati sul veicolo esistente
            form.aci_vehicle_tipo.data = user.aci_vehicle.tipologia
            form.aci_vehicle_marca.data = user.aci_vehicle.marca
            form.aci_vehicle.data = user.aci_vehicle_id
            
            # Aggiorna le scelte per rendere i dropdown funzionali
            from models import ACITable
            aci_vehicles = filter_by_company(ACITable.query, ACITable).order_by(ACITable.tipologia, ACITable.marca, ACITable.modello).all()
            
            # Aggiorna le scelte delle marche per il tipo selezionato
            marche = list(set([v.marca for v in aci_vehicles if v.tipologia == user.aci_vehicle.tipologia and v.marca]))
            form.aci_vehicle_marca.choices = [('', 'Seleziona marca')] + [(marca, marca) for marca in sorted(marche)]
            
            # Aggiorna le scelte dei modelli per tipo e marca selezionati
            modelli = filter_by_company(ACITable.query, ACITable).filter(
                ACITable.tipologia == user.aci_vehicle.tipologia,
                ACITable.marca == user.aci_vehicle.marca
            ).order_by(ACITable.modello).all()
            
            form.aci_vehicle.choices = [('', 'Seleziona modello')] + [(m.id, f"{m.modello} (€{m.costo_km:.4f}/km)") for m in modelli]
        
        return render_template('edit_user.html', form=form, user=user)
    
    if form.validate_on_submit():
        # Aggiorna i dati dell'utente
        user.username = form.username.data
        user.email = form.email.data
        if form.password.data:
            user.password_hash = generate_password_hash(form.password.data)
        user.role = form.role.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.all_sedi = form.all_sedi.data
        user.sede_id = form.sede.data if not form.all_sedi.data else None
        user.work_schedule_id = form.work_schedule.data
        user.aci_vehicle_id = form.aci_vehicle.data if form.aci_vehicle.data and form.aci_vehicle.data != -1 else None
        user.part_time_percentage = form.get_part_time_percentage_as_float()
        user.banca_ore_enabled = form.banca_ore_enabled.data
        user.banca_ore_limite_max = form.get_banca_ore_limite_max_as_float()
        user.banca_ore_periodo_mesi = form.get_banca_ore_periodo_mesi_as_int()
        user.active = form.active.data
        
        db.session.commit()
        flash('Utente modificato con successo', 'success')
        return redirect(url_for('user_management.user_management'))
    
    return render_template('edit_user.html', form=form, user=user)

@user_management_bp.route('/users/toggle/<int:user_id>')
@login_required
def toggle_user(user_id):
    """Toggle user active status"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per modificare utenti', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    user = filter_by_company(User.query, User).get_or_404(user_id)
    if user.id == current_user.id:
        flash('Non puoi disattivare il tuo account', 'warning')
        return redirect(url_for('user_management.user_management'))
    
    # Impedisce la disattivazione dell'amministratore
    if user.role == 'Amministratore':
        flash('Non è possibile disattivare l\'utente amministratore', 'danger')
        return redirect(url_for('user_management.user_management'))
    
    user.active = not user.active
    db.session.commit()
    
    status = 'attivato' if user.active else 'disattivato'
    flash(f'Utente {status} con successo', 'success')
    return redirect(url_for('user_management.user_management'))

# =============================================================================
# BLUEPRINT REGISTRATION READY
# =============================================================================
# This blueprint is ready to be registered in main.py:
# from blueprints.user_management import user_management_bp
# app.register_blueprint(user_management_bp)
# =============================================================================