from datetime import datetime, timedelta
from flask import jsonify, request
from flask_login import login_required, current_user
from app import app, db
from models import User, Shift, PresidioCoverageTemplate, PresidioCoverage
import json

@app.route('/api/get_shifts_for_template/<int:template_id>')
@login_required  
def api_get_shifts_for_template(template_id):
    """API COMPLETAMENTE RISCRITTA - LOGICA SEMPLICE E FUNZIONANTE"""
    
    template = PresidioCoverageTemplate.query.get_or_404(template_id)
    shifts = Shift.query.filter(
        Shift.date >= template.start_date,
        Shift.date <= template.end_date
    ).all()
    
    # STEP 1: Organizza turni per settimana
    weeks_data = {}
    for shift in shifts:
        week_start = shift.date - timedelta(days=shift.date.weekday())
        week_key = week_start.strftime('%Y-%m-%d')
        
        if week_key not in weeks_data:
            weeks_data[week_key] = {
                'start': week_start.strftime('%d/%m/%Y'),
                'end': (week_start + timedelta(days=6)).strftime('%d/%m/%Y'),
                'days': [],
                'shift_count': 0,
                'unique_users': set(),
                'total_hours': 0
            }
            # Inizializza i 7 giorni della settimana
            for i in range(7):
                weeks_data[week_key]['days'].append({
                    'date': (week_start + timedelta(days=i)).strftime('%d/%m'),
                    'shifts': [],
                    'missing_roles': []
                })
        
        day_index = shift.date.weekday()
        shift_data = {
            'id': shift.id,
            'user': shift.user.username,
            'user_id': shift.user.id,
            'role': shift.user.role.name if shift.user.role else 'Senza ruolo',
            'time': f"{shift.start_time.strftime('%H:%M')}-{shift.end_time.strftime('%H:%M')}"
        }
        weeks_data[week_key]['days'][day_index]['shifts'].append(shift_data)
        weeks_data[week_key]['shift_count'] += 1
        weeks_data[week_key]['unique_users'].add(shift.user.username)
    
    # STEP 2: Converti set in count
    for week_data in weeks_data.values():
        week_data['unique_users'] = len(week_data['unique_users'])
    
    # STEP 3: CALCOLA MISSING_ROLES - LOGICA SEMPLICE E DIRETTA
    coverages = PresidioCoverage.query.filter_by(template_id=template_id, is_active=True).all()
    
    for week_data in weeks_data.values():
        for day_index in range(7):
            day_data = week_data['days'][day_index]
            
            # Trova coperture richieste per questo giorno
            for coverage in coverages:
                if coverage.day_of_week == day_index:
                    # Parse ruoli richiesti
                    try:
                        required_roles = json.loads(coverage.required_roles) if coverage.required_roles else []
                    except:
                        required_roles = []
                    
                    time_slot = f"{coverage.start_time.strftime('%H:%M')}-{coverage.end_time.strftime('%H:%M')}"
                    
                    # Verifica ogni ruolo richiesto
                    for required_role in required_roles:
                        # Conta ruoli esistenti che coprono questa fascia oraria
                        role_found = False
                        for shift in day_data['shifts']:
                            if shift['role'] == required_role:
                                shift_times = shift['time'].split('-')
                                shift_start = shift_times[0]
                                shift_end = shift_times[1]
                                
                                # Verifica sovrapposizione oraria
                                if shift_start <= coverage.end_time.strftime('%H:%M') and shift_end >= coverage.start_time.strftime('%H:%M'):
                                    role_found = True
                                    break
                        
                        # Se ruolo non trovato, aggiungi a missing_roles
                        if not role_found:
                            missing_text = f"{required_role} mancante ({time_slot})"
                            if missing_text not in day_data['missing_roles']:
                                day_data['missing_roles'].append(missing_text)
    
    # STEP 4: Ordina e restituisci
    sorted_weeks = sorted(weeks_data.items())
    processed_weeks = [week_data for _, week_data in sorted_weeks]
    
    return jsonify({
        'success': True,
        'weeks': processed_weeks,
        'template_name': template.name,
        'period': template.get_period_display()
    })