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
    """API per ottenere tutti gli orari di lavoro globali disponibili per l'azienda"""
    try:
        # Ottieni tutti gli orari attivi dell'azienda (tutti globali ora)
        work_schedules = filter_by_company(WorkSchedule.query).filter_by(active=True).order_by(
            WorkSchedule.name
        ).all()
        
        schedules_data = []
        for schedule in work_schedules:
            schedules_data.append({
                'id': schedule.id,
                'name': schedule.name,
                'start_time': schedule.start_time.strftime('%H:%M') if schedule.start_time else '',
                'end_time': schedule.end_time.strftime('%H:%M') if schedule.end_time else '',
                'days_count': len(schedule.days_of_week) if schedule.days_of_week else 0
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
    """
    DEPRECATED: API per ottenere gli orari di lavoro.
    Gli orari ora sono globali a livello aziendale, non più per sede.
    Questo endpoint è mantenuto per retrocompatibilità e restituisce tutti gli orari globali.
    """
    # Reindirizza alla funzione all_work_schedules per evitare duplicazione
    return all_work_schedules()

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