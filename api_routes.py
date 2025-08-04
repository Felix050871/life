from datetime import datetime, timedelta
from flask import jsonify, request
from flask_login import login_required, current_user
from app import app, db
from models import User, Shift, PresidioCoverageTemplate, PresidioCoverage
import json
import logging
from utils import split_coverage_into_segments_by_user_capacity
from new_shift_generation import calculate_shift_duration

# Setup logging for API routes
logger = logging.getLogger(__name__)

@app.route('/api/get_shifts_for_template/<int:template_id>')
@login_required  
def api_get_shifts_for_template(template_id):
    """API COMPLETAMENTE RISCRITTA - LOGICA SEMPLICE E FUNZIONANTE"""
    
    # DEBUG: Aggiungo logging per verificare chiamate API
    import sys
    print(f"API DEBUG: get_shifts_for_template chiamata per template_id={template_id}", file=sys.stderr, flush=True)
    print(f"API DEBUG: Template {template.name}, periodo {template.start_date} - {template.end_date}", file=sys.stderr, flush=True)
    
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
    
    # STEP 3: CALCOLA MISSING_ROLES - CON DEBUG COMPLETO
    coverages = PresidioCoverage.query.filter_by(template_id=template_id, active=True).all()
    logger.debug(f" Found {len(coverages)} coverages for template {template_id}")
    
    for coverage in coverages:
        print(f"API DEBUG: Coverage {coverage.id}: day={coverage.day_of_week}, time={coverage.start_time}-{coverage.end_time}, roles={coverage.required_roles}", file=sys.stderr, flush=True)
    
    for week_data in weeks_data.values():
        for day_index in range(7):
            day_data = week_data['days'][day_index]
            print(f"API DEBUG: Processing day {day_index} with {len(day_data['shifts'])} shifts", file=sys.stderr, flush=True)
            
            # Trova coperture richieste per questo giorno
            day_coverages = [c for c in coverages if c.day_of_week == day_index]
            print(f"API DEBUG: Day {day_index} has {len(day_coverages)} coverages", file=sys.stderr, flush=True)
            
            for coverage in day_coverages:
                # Parse ruoli richiesti
                try:
                    required_roles = json.loads(coverage.required_roles) if coverage.required_roles else []
                    logger.debug(f" Coverage requires roles: {required_roles}")
                except Exception as e:
                    logger.debug(f" Error parsing roles: {e}")
                    required_roles = []
                
                # Verifica copertura (non spezzare, le coperture sono già definite correttamente)
                time_slot = f"{coverage.start_time.strftime('%H:%M')}-{coverage.end_time.strftime('%H:%M')}"
                
                # Verifica ogni ruolo richiesto per questa copertura
                for required_role in required_roles:
                    logger.debug(f" Looking for role '{required_role}' in time slot {time_slot}")
                    
                    # Conta ruoli esistenti che coprono questa fascia oraria ESATTA
                    role_found = False
                    for shift in day_data['shifts']:
                        if shift['role'] == required_role:
                            shift_times = shift['time'].split('-')
                            shift_start = shift_times[0]
                            shift_end = shift_times[1]
                            
                            # Verifica copertura ESATTA della fascia oraria (non sovrapposizione parziale)
                            if (shift_start <= coverage.start_time.strftime('%H:%M') and 
                                shift_end >= coverage.end_time.strftime('%H:%M')):
                                logger.debug(f" Role {required_role} found - exact coverage detected")
                                role_found = True
                                break
                    
                    # Se ruolo non trovato per questa copertura, aggiungi a missing_roles
                    if not role_found:
                        missing_text = f"{required_role} mancante ({time_slot})"
                        if missing_text not in day_data['missing_roles']:
                            day_data['missing_roles'].append(missing_text)
                            print(f"API: MISSING COVERAGE: {missing_text}", file=sys.stderr, flush=True)
    
    # STEP 4: Ordina e restituisci
    sorted_weeks = sorted(weeks_data.items())
    processed_weeks = [week_data for _, week_data in sorted_weeks]
    
    return jsonify({
        'success': True,
        'weeks': processed_weeks,
        'template_name': template.name,
        'period': template.get_period_display()
    })

@app.route('/api/get_coverage_requirements/<int:template_id>')
@login_required
def api_get_coverage_requirements(template_id):
    """API per ottenere i requisiti di copertura di un template"""
    
    coverages = PresidioCoverage.query.filter_by(template_id=template_id, active=True).all()
    
    coverage_data = []
    for coverage in coverages:
        try:
            required_roles = json.loads(coverage.required_roles) if coverage.required_roles else []
        except:
            required_roles = []
        
        coverage_data.append({
            'day_of_week': coverage.day_of_week,
            'start_time': coverage.start_time.strftime('%H:%M'),
            'end_time': coverage.end_time.strftime('%H:%M'),
            'required_roles': required_roles,
            'role_count': coverage.role_count
        })
    
    return jsonify({
        'success': True,
        'coverages': coverage_data
    })

@app.route('/api/aci/marche/<tipo>')
@login_required
def api_aci_marche_by_tipo(tipo):
    """API per ottenere le marche filtrate per tipo di veicolo"""
    try:
        from models import ACITable
        marche = db.session.query(ACITable.marca).filter(
            ACITable.tipologia == tipo,
            ACITable.marca.isnot(None)
        ).distinct().order_by(ACITable.marca).all()
        
        marche_list = [m[0] for m in marche if m[0]]
        return jsonify({
            'success': True,
            'marche': marche_list
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/aci/modelli/<tipo>/<marca>')
@login_required
def api_aci_modelli_by_tipo_marca(tipo, marca):
    """API per ottenere i modelli filtrati per tipo e marca di veicolo"""
    try:
        from models import ACITable
        vehicles = ACITable.query.filter(
            ACITable.tipologia == tipo,
            ACITable.marca == marca
        ).order_by(ACITable.modello).all()
        
        modelli_list = [(v.id, f"{v.modello} (€{v.costo_km:.4f}/km)") for v in vehicles]
        return jsonify({
            'success': True,
            'modelli': modelli_list
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })