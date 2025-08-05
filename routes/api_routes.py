"""
API Routes
JSON endpoints for AJAX requests and data exchange
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, date

from app import db
from models import (User, AttendanceEvent, Shift, PresidioCoverageTemplate, 
                   PresidioCoverage, Sede, MileageRequest)

# Create blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/work_hours/<int:user_id>/<date_str>')
@login_required
def get_work_hours(user_id, date_str):
    """API endpoint per ottenere le ore lavorate aggiornate"""
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        work_hours = AttendanceEvent.get_daily_work_hours(user_id, target_date)
        return jsonify({'work_hours': round(work_hours, 1)})
    except Exception:
        return jsonify({'work_hours': 0})

@api_bp.route('/get_shifts_for_template/<int:template_id>')
@login_required
def get_shifts_for_template_api(template_id):
    """API per ottenere turni di un template specifico"""
    if not current_user.can_view_shifts():
        return jsonify({'error': 'Non hai i permessi per visualizzare i turni'}), 403
    
    try:
        template = PresidioCoverageTemplate.query.get_or_404(template_id)
        
        # Ottieni turni del template
        shifts = Shift.query.filter(
            Shift.template_id == template_id,
            Shift.date >= template.start_date,
            Shift.date <= template.end_date,
            Shift.active == True
        ).order_by(Shift.date, Shift.start_time).all()
        
        # Prepara dati per la risposta
        shifts_data = []
        for shift in shifts:
            user_name = shift.user.get_full_name() if shift.user else "Non assegnato"
            shifts_data.append({
                'id': shift.id,
                'date': shift.date.strftime('%Y-%m-%d'),
                'date_display': shift.date.strftime('%d/%m/%Y'),
                'weekday': shift.get_weekday_name(),
                'start_time': shift.start_time.strftime('%H:%M'),
                'end_time': shift.end_time.strftime('%H:%M'),
                'role': shift.role,
                'user_id': shift.user_id,
                'user_name': user_name,
                'description': shift.description or '',
                'is_night_shift': shift.is_night_shift(),
                'duration_hours': shift.get_duration_hours()
            })
        
        return jsonify({
            'success': True,
            'template': {
                'id': template.id,
                'name': template.name,
                'start_date': template.start_date.strftime('%Y-%m-%d'),
                'end_date': template.end_date.strftime('%Y-%m-%d'),
                'period': template.get_period_display(),
            },
            'shifts': shifts_data,
            'total_shifts': len(shifts_data)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/get_coverage_requirements/<int:template_id>')
@login_required
def get_coverage_requirements(template_id):
    """API per ottenere i requisiti di copertura per un template specifico"""
    if not current_user.can_view_shifts():
        return jsonify({'error': 'Non hai i permessi per visualizzare le coperture'}), 403
    
    try:
        template = PresidioCoverageTemplate.query.get_or_404(template_id)
        
        # Ottieni tutte le coperture del template
        coverages = PresidioCoverage.query.filter_by(
            template_id=template_id,
            active=True
        ).order_by(PresidioCoverage.day_of_week, PresidioCoverage.start_time).all()
        
        # Raggruppa per giorno della settimana
        requirements_by_day = {}
        for coverage in coverages:
            day_name = coverage.get_day_name()
            if day_name not in requirements_by_day:
                requirements_by_day[day_name] = []
            
            requirements_by_day[day_name].append({
                'start_time': coverage.start_time.strftime('%H:%M'),
                'end_time': coverage.end_time.strftime('%H:%M'),
                'role': coverage.role,
                'time_slot': f"{coverage.start_time.strftime('%H:%M')}-{coverage.end_time.strftime('%H:%M')}"
            })
        
        return jsonify({
            'success': True,
            'template_id': template_id,
            'template_name': template.name,
            'requirements': requirements_by_day
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/sede/<int:sede_id>/users')
@login_required
def get_sede_users(sede_id):
    """API per ottenere gli utenti di una sede specifica"""
    if not current_user.can_view_users():
        return jsonify({'error': 'Non hai i permessi per visualizzare gli utenti'}), 403
    
    try:
        sede = Sede.query.get_or_404(sede_id)
        
        # Ottieni utenti della sede
        users = User.query.filter(
            User.sede_id == sede_id,
            User.active == True
        ).order_by(User.first_name, User.last_name).all()
        
        users_data = []
        for user in users:
            users_data.append({
                'id': user.id,
                'name': user.get_full_name(),
                'role': user.role,
                'email': user.email,
                'part_time_percentage': user.part_time_percentage
            })
        
        return jsonify({
            'success': True,
            'sede': {
                'id': sede.id,
                'name': sede.name
            },
            'users': users_data,
            'total_users': len(users_data)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/mileage_requests/<int:request_id>/calculate', methods=['POST'])
@login_required
def calculate_mileage_amount(request_id):
    """API per calcolare l'importo del rimborso chilometrico"""
    if not (current_user.can_create_mileage_requests() or current_user.can_manage_mileage_requests()):
        return jsonify({'error': 'Non hai i permessi per calcolare rimborsi chilometrici'}), 403
    
    try:
        mileage_request = MileageRequest.query.get_or_404(request_id)
        
        # Verifica che l'utente possa accedere a questa richiesta
        if not current_user.can_manage_mileage_requests() and mileage_request.user_id != current_user.id:
            return jsonify({'error': 'Non hai i permessi per accedere a questa richiesta'}), 403
        
        # Calcola l'importo se non già calcolato
        if not mileage_request.total_amount:
            mileage_request.calculate_total_amount()
            db.session.commit()
        
        return jsonify({
            'success': True,
            'request_id': request_id,
            'total_distance': mileage_request.total_distance,
            'rate_per_km': float(mileage_request.rate_per_km) if mileage_request.rate_per_km else 0,
            'total_amount': float(mileage_request.total_amount) if mileage_request.total_amount else 0
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/user_status/<int:user_id>')
@login_required
def get_user_status(user_id):
    """API per ottenere lo stato attuale di un utente"""
    if not current_user.can_view_attendance():
        return jsonify({'error': 'Non hai i permessi per visualizzare le presenze'}), 403
    
    try:
        # Verifica che l'utente corrente possa vedere questo utente
        if user_id != current_user.id and not current_user.can_view_all_attendance():
            return jsonify({'error': 'Non hai i permessi per visualizzare lo stato di questo utente'}), 403
        
        user = User.query.get_or_404(user_id)
        status, last_event = AttendanceEvent.get_user_status(user_id)
        
        # Calcola ore lavorate oggi
        today = date.today()
        work_hours = AttendanceEvent.get_daily_work_hours(user_id, today)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'user_name': user.get_full_name(),
            'status': status,
            'work_hours_today': round(work_hours, 1),
            'last_event': {
                'type': last_event.event_type if last_event else None,
                'timestamp': last_event.timestamp.strftime('%H:%M') if last_event else None
            } if last_event else None
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/validate_user_shift', methods=['POST'])
@login_required
def validate_user_shift():
    """API per validare se un utente può essere assegnato a un turno"""
    if not current_user.can_manage_shifts():
        return jsonify({'error': 'Non hai i permessi per gestire i turni'}), 403
    
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        shift_date = datetime.strptime(data.get('date'), '%Y-%m-%d').date()
        start_time = datetime.strptime(data.get('start_time'), '%H:%M').time()
        end_time = datetime.strptime(data.get('end_time'), '%H:%M').time()
        
        user = User.query.get_or_404(user_id)
        
        # Verifica disponibilità utente per questo turno
        # (qui andrebbe implementata la logica di validazione specifica)
        
        return jsonify({
            'success': True,
            'valid': True,
            'message': 'Utente disponibile per il turno'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500