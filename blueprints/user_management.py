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
from sqlalchemy.orm import joinedload

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
    
    sede = Sede.query.get_or_404(sede_id)
    
    # Verifica permessi sede
    if not current_user.all_sedi and current_user.sede_id != sede_id:
        return jsonify({'error': 'Accesso negato a questa sede'}), 403
    
    users = User.query.filter_by(sede_id=sede_id, active=True).order_by(
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
    
    sede = Sede.query.get_or_404(sede_id)
    
    # Verifica permessi sede
    if not current_user.all_sedi and current_user.sede_id != sede_id:
        return jsonify({'error': 'Accesso negato a questa sede'}), 403
    
    schedules = WorkSchedule.query.filter_by(sede_id=sede_id, active=True).order_by(
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
    
    roles = UserRole.query.filter_by(active=True).order_by(UserRole.name).all()
    
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

@user_management_bp.route('/profile')
@login_required
def user_profile():
    """User profile page"""
    # Basic profile functionality - can be expanded later
    return render_template('user_profile.html', user=current_user)

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
    users = User.query.options(
        joinedload(User.sede_obj)
    ).all()
    
    # Create user form (only for managers)
    form = UserForm() if current_user.can_manage_users() else None
    if form:
        # Populate form choices
        form.role.choices = [(role.name, role.name) for role in UserRole.query.filter_by(active=True).all()]
        form.sede.choices = [(-1, 'Seleziona una sede')] + [(sede.id, sede.name) for sede in Sede.query.filter_by(active=True).all()]
    
    return render_template('user_management.html', 
                         users=users, 
                         form=form,
                         can_manage_users=current_user.can_manage_users())

# =============================================================================
# BLUEPRINT REGISTRATION READY
# =============================================================================
# This blueprint is ready to be registered in main.py:
# from blueprints.user_management import user_management_bp
# app.register_blueprint(user_management_bp)
# =============================================================================