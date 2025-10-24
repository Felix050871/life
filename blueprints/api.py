# =============================================================================
# API BLUEPRINT - Endpoints API centrali per frontend/AJAX
# =============================================================================
#
# ROUTES INCLUSE:
# 1. /api/sede/<sede_id>/users (GET) - API utenti di sede specifica
# 2. /api/sede/<sede_id>/work_schedules (GET) - API orari lavoro di sede
# 3. /api/roles (GET) - API lista ruoli disponibili
# 4. /api/presidio_coverage/<template_id> (GET) - API dettagli copertura presidio
#
# Total routes: 4 API endpoint routes
# =============================================================================

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from models import Sede, User, WorkSchedule, UserRole, PresidioCoverageTemplate
from utils_tenant import filter_by_company, set_company_on_create

# Create blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# =============================================================================
# SEDE API ROUTES
# =============================================================================

@api_bp.route('/sede/<int:sede_id>/users')
@login_required
def sede_users(sede_id):
    """API per ottenere gli utenti di una sede specifica"""
    if not current_user.can_access_turni():
        return jsonify({'error': 'Non autorizzato'}), 403
    
    sede = filter_by_company(Sede.query).filter(Sede.id == sede_id).first_or_404()
    
    # Verifica che l'utente possa accedere a questa sede
    if current_user.role != 'Amministratore' and not current_user.all_sedi and (not current_user.sede_obj or current_user.sede_obj.id != sede_id):
        return jsonify({'error': 'Non autorizzato'}), 403
    
    # Ottieni utenti attivi della sede (esclusi Amministratore)
    users = filter_by_company(User.query).filter_by(
        sede_id=sede_id, 
        active=True
    ).filter(
        User.role != 'Amministratore'
    ).order_by(User.first_name, User.last_name).all()
    
    users_data = []
    for user in users:
        users_data.append({
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role
        })
    
    return jsonify(users_data)

@api_bp.route('/work_schedules')
@login_required
def all_work_schedules():
    """API per ottenere tutti gli orari di lavoro disponibili per l'azienda"""
    try:
        # Ottieni tutti gli orari attivi dell'azienda (globali e sede-specifici)
        work_schedules = filter_by_company(WorkSchedule.query).filter_by(active=True).order_by(
            WorkSchedule.sede_id.is_(None).desc(),  # Globali per primi
            WorkSchedule.name
        ).all()
        
        schedules_data = []
        for schedule in work_schedules:
            if schedule.is_turni_schedule():
                # Visualizzazione speciale per orario "Turni"
                sede_name = schedule.sede_obj.name if schedule.sede_obj else ''
                schedules_data.append({
                    'id': schedule.id,
                    'name': f"{schedule.name} ({sede_name})" if sede_name else schedule.name,
                    'start_time': 'Flessibile',
                    'end_time': 'Flessibile',
                    'days_count': 7,
                    'is_global': False,
                    'sede_name': sede_name
                })
            else:
                # Orari standard
                if schedule.sede_id is None:
                    display_name = f"{schedule.name} (Globale)"
                else:
                    sede_name = schedule.sede_obj.name if schedule.sede_obj else 'Sede sconosciuta'
                    display_name = f"{schedule.name} ({sede_name})"
                
                schedules_data.append({
                    'id': schedule.id,
                    'name': display_name,
                    'start_time': schedule.start_time.strftime('%H:%M') if schedule.start_time else '',
                    'end_time': schedule.end_time.strftime('%H:%M') if schedule.end_time else '',
                    'days_count': len(schedule.days_of_week) if schedule.days_of_week else 0,
                    'is_global': schedule.sede_id is None,
                    'sede_name': schedule.sede_obj.name if schedule.sede_obj else None
                })
        
        return jsonify({
            'success': True,
            'work_schedules': schedules_data,
            'has_schedules': len(schedules_data) > 0
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/sede/<int:sede_id>/work_schedules')
@login_required
def sede_work_schedules(sede_id):
    """API per ottenere gli orari di lavoro globali e di una sede specifica"""
    try:
        sede = filter_by_company(Sede.query).filter(Sede.id == sede_id).first_or_404()
        
        # Ottieni orari globali (sede_id=NULL) - disponibili per tutti
        global_schedules = filter_by_company(WorkSchedule.query).filter_by(sede_id=None, active=True).all()
        
        # Ottieni orari specifici della sede
        sede_schedules = filter_by_company(WorkSchedule.query).filter_by(sede_id=sede_id, active=True).all()
        
        # Combina gli orari
        work_schedules = list(global_schedules) + list(sede_schedules)
        
        # Se la sede supporta modalità turni e non ha ancora l'orario 'Turni', crealo
        if sede.is_turni_mode() and not sede.has_turni_schedule():
            turni_schedule = sede.get_or_create_turni_schedule()
            work_schedules.append(turni_schedule)
        
        schedules_data = []
        for schedule in work_schedules:
            # Visualizzazione speciale per orario "Turni"
            if schedule.is_turni_schedule():
                schedules_data.append({
                    'id': schedule.id,
                    'name': schedule.name,
                    'start_time': 'Flessibile',
                    'end_time': 'Flessibile',
                    'days_count': 7,
                    'is_global': False
                })
            else:
                schedules_data.append({
                    'id': schedule.id,
                    'name': schedule.name + (' (Globale)' if schedule.sede_id is None else ''),
                    'start_time': schedule.start_time.strftime('%H:%M') if schedule.start_time else '',
                    'end_time': schedule.end_time.strftime('%H:%M') if schedule.end_time else '',
                    'days_count': len(schedule.days_of_week) if schedule.days_of_week else 0,
                    'is_global': schedule.sede_id is None
                })
        
        return jsonify({
            'success': True,
            'work_schedules': schedules_data,
            'sede_name': sede.name,
            'has_schedules': len(schedules_data) > 0,
            'is_turni_mode': sede.is_turni_mode()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =============================================================================
# ROLE API ROUTES
# =============================================================================

@api_bp.route('/roles')
@login_required  
def roles():
    """API endpoint per ottenere la lista dei ruoli disponibili"""
    try:
        roles = filter_by_company(UserRole.query).filter(
            UserRole.active == True,
            UserRole.name != 'Amministratore'
        ).all()
        role_names = [role.name for role in roles] if roles else ['Responsabile', 'Supervisore', 'Operatore', 'Ospite']
        return jsonify(role_names)
    except Exception as e:
        return jsonify(['Responsabile', 'Supervisore', 'Operatore', 'Ospite'])

# =============================================================================
# PRESIDIO API ROUTES
# =============================================================================

@api_bp.route('/presidio_coverage/<int:template_id>')
@login_required
def presidio_coverage(template_id):
    """API per ottenere dettagli copertura presidio"""
    template = filter_by_company(PresidioCoverageTemplate.query).filter(PresidioCoverageTemplate.id == template_id).first_or_404()
    
    coverages = []
    for coverage in template.coverages.filter_by(active=True):
        coverages.append({
            'id': coverage.id,
            'day_of_week': coverage.day_of_week,
            'start_time': coverage.start_time.strftime('%H:%M'),
            'end_time': coverage.end_time.strftime('%H:%M'),
            'required_roles': coverage.get_required_roles(),
            'role_count': coverage.role_count
        })
    
    return jsonify({
        'success': True,
        'template_name': template.name,
        'start_date': template.start_date.strftime('%Y-%m-%d'),
        'end_date': template.end_date.strftime('%Y-%m-%d'),
        'period': template.get_period_display(),
        'coverages': coverages
    })