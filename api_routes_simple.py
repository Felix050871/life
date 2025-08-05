from flask import jsonify, request
from flask_login import login_required
from app import app, db
from models import Shift, PresidioCoverageTemplate, PresidioCoverage, User
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@app.route('/api/get_shifts_simple/<int:template_id>')
@login_required  
def api_get_shifts_simple(template_id):
    """API COMPLETAMENTE NUOVA - APPROCCIO SEMPLICE E DIRETTO"""
    
    try:
        template = PresidioCoverageTemplate.query.get_or_404(template_id)
        
        # STEP 1: Prendi TUTTI i turni del template - QUERY SEMPLICE
        all_shifts = db.session.query(Shift, User).join(User, Shift.user_id == User.id).filter(
            Shift.date >= template.start_date,
            Shift.date <= template.end_date
        ).all()
        
        print(f"SIMPLE API: Found {len(all_shifts)} shifts", flush=True)
        
        # STEP 2: Organizza per date - DIZIONARIO SEMPLICE
        shifts_by_date = {}
        for shift, user in all_shifts:
            date_key = shift.date.strftime('%d/%m')
            if date_key not in shifts_by_date:
                shifts_by_date[date_key] = []
            
            shift_info = {
                'id': shift.id,
                'user': f"{user.first_name} {user.last_name}",
                'user_id': user.id,
                'role': user.role,
                'time': f"{shift.start_time.strftime('%H:%M')}-{shift.end_time.strftime('%H:%M')}"
            }
            shifts_by_date[date_key].append(shift_info)
            print(f"ADDED: {date_key} -> {shift_info}", flush=True)
        
        # STEP 3: Crea struttura settimane SEMPLICE
        current_date = template.start_date
        weeks = []
        
        while current_date <= template.end_date:
            # Trova inizio settimana (lunedì)
            week_start = current_date - timedelta(days=current_date.weekday())
            
            # Crea 7 giorni della settimana
            week_days = []
            for i in range(7):
                day_date = week_start + timedelta(days=i)
                day_key = day_date.strftime('%d/%m')
                
                day_shifts = shifts_by_date.get(day_key, [])
                
                week_days.append({
                    'date': day_key,
                    'shifts': day_shifts,
                    'missing_roles': []  # Calcolato dopo
                })
            
            weeks.append({
                'start': week_start.strftime('%d/%m/%Y'),
                'end': (week_start + timedelta(days=6)).strftime('%d/%m/%Y'),
                'days': week_days,
                'shift_count': sum(len(day['shifts']) for day in week_days),
                'unique_users': 0,
                'total_hours': 0
            })
            
            # Vai alla prossima settimana
            current_date = week_start + timedelta(days=7)
        
        # STEP 4: Calcola missing roles SEMPLICE
        coverages = PresidioCoverage.query.filter_by(template_id=template_id, active=True).all()
        
        for week in weeks:
            for day in week['days']:
                # Per ogni coverage richiesta
                for coverage in coverages:
                    time_slot = f"{coverage.start_time.strftime('%H:%M')}-{coverage.end_time.strftime('%H:%M')}"
                    
                    # Verifica se c'è già un turno per questo slot
                    has_coverage = any(
                        shift['time'] == time_slot and str(coverage.role).lower() in str(shift['role']).lower()
                        for shift in day['shifts']
                    )
                    
                    if not has_coverage:
                        day['missing_roles'].append(f"{coverage.role} mancante ({time_slot})")
        
        return jsonify({
            'success': True,
            'period': f"{template.start_date.strftime('%d/%m/%Y')} - {template.end_date.strftime('%d/%m/%Y')}",
            'weeks': weeks
        })
        
    except Exception as e:
        logger.error(f"Error in simple API: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500