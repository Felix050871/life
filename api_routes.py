from datetime import datetime, timedelta
from flask import jsonify, request
from flask_login import login_required, current_user
from app import app, db
from sqlalchemy.orm import joinedload
from models import User, Shift, PresidioCoverageTemplate, PresidioCoverage
import json
import logging
from utils import split_coverage_into_segments_by_user_capacity
from new_shift_generation import calculate_shift_duration

# Setup logging for API routes  
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/api/get_shifts_for_template/<int:template_id>', methods=['GET'])
@login_required  
def api_get_shifts_for_template(template_id):
    """API RISCRITTA COMPLETAMENTE - CALCOLO MISSING_ROLES SEMPLICE E FUNZIONANTE"""
    
    # FORCE IMMEDIATE OUTPUT TO IDENTIFY EXECUTION
    import sys
    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    
    logger.info("=== API EXECUTION START ===")
    print("=== API CALLED ===", flush=True)
    print(f"Function called with template_id: {template_id}", flush=True)
    sys.stdout.flush()
    
    try:
        template = PresidioCoverageTemplate.query.get_or_404(template_id)
        print(f"Template {template_id}: {template.start_date} to {template.end_date}", flush=True)
        sys.stdout.flush()
        
        # Query diretta senza eager loading per test
        all_shifts = Shift.query.all()
        print(f"Total shifts in database: {len(all_shifts)}", flush=True)
        sys.stdout.flush()
        
        shifts = Shift.query.filter(
            Shift.date >= template.start_date,
            Shift.date <= template.end_date
        ).all()
        
        print(f"API DEBUG: Found {len(shifts)} shifts for template {template_id}", flush=True)
        sys.stdout.flush()
        for shift in shifts[:10]:  # Log primi 10 turni per debug
            print(f"Shift {shift.id}: {shift.date} {shift.start_time}-{shift.end_time} -> user_id={shift.user_id}", flush=True)
        sys.stdout.flush()
        
        # DEBUG AGGIUNTIVO: Controlla turni specifici 01/10
        oct_01_shifts = [s for s in shifts if s.date.strftime('%Y-%m-%d') == '2025-10-01']
        print(f"01/10 shifts found: {len(oct_01_shifts)}", flush=True)
        sys.stdout.flush()
        for shift in oct_01_shifts:
            print(f"01/10 - Shift {shift.id}: {shift.start_time}-{shift.end_time} -> user_id={shift.user_id}", flush=True)
        sys.stdout.flush()
        
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
            
            # Safe access to user data
            try:
                if shift.user:
                    user_display_name = f"{shift.user.first_name} {shift.user.last_name}".strip()
                    if not user_display_name:
                        user_display_name = shift.user.username
                    user_role = shift.user.role
                else:
                    user_display_name = "Utente eliminato"
                    user_role = "N/A"
            except Exception as e:
                print(f"Error accessing user for shift {shift.id}: {e}")
                user_display_name = f"Utente ID {shift.user_id}"
                user_role = "N/A"
            
            shift_data = {
                'id': shift.id,
                'user': user_display_name,
                'user_id': shift.user_id,
                'role': user_role,
                'time': f"{shift.start_time.strftime('%H:%M')}-{shift.end_time.strftime('%H:%M')}"
            }
            weeks_data[week_key]['days'][day_index]['shifts'].append(shift_data)
            print(f"Added shift {shift.id} to week {week_key}, day {day_index}: {user_display_name}", flush=True)
            sys.stdout.flush()
            weeks_data[week_key]['shift_count'] += 1
            weeks_data[week_key]['unique_users'].add(shift.user.username)
        
        # STEP 2: Converti set in count
        for week_data in weeks_data.values():
            week_data['unique_users'] = len(week_data['unique_users'])
        
        # STEP 3: CALCOLA MISSING_ROLES - LOGICA SEMPLIFICATA
        coverages = PresidioCoverage.query.filter_by(template_id=template_id, active=True).all()
        total_missing = 0
        
        for week_data in weeks_data.values():
            for day_index in range(7):
                day_data = week_data['days'][day_index]
                day_coverages = [c for c in coverages if c.day_of_week == day_index]
                
                for coverage in day_coverages:
                    try:
                        required_roles = json.loads(coverage.required_roles) if coverage.required_roles else []
                    except:
                        required_roles = []
                    
                    time_slot = f"{coverage.start_time.strftime('%H:%M')}-{coverage.end_time.strftime('%H:%M')}"
                    
                    for required_role in required_roles:
                        # Verifica se esiste un turno che copre ESATTAMENTE questa fascia oraria
                        role_found = False
                        for shift in day_data['shifts']:
                            if (shift['role'] == required_role and 
                                shift['time'] == time_slot):
                                role_found = True
                                break
                        
                        # Se non trovato, aggiungi ai missing
                        if not role_found:
                            missing_text = f"{required_role} mancante ({time_slot})"
                            if missing_text not in day_data['missing_roles']:
                                day_data['missing_roles'].append(missing_text)
                                total_missing += 1
        
        return jsonify({
            'success': True,
            'weeks': weeks_data,
            'template_name': template.name,
            'period': template.get_period_display(),
            'debug_missing_count': total_missing
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'debug_missing_count': -1
        }), 500

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

@app.route('/api/users_by_role/<role>')
@login_required
def api_users_by_role(role):
    """API per ottenere utenti con un ruolo specifico"""
    try:
        if not current_user.can_access_turni():
            return jsonify({'error': 'Non autorizzato'}), 403
        
        # Ottieni utenti attivi con il ruolo richiesto nella sede dell'utente corrente
        query = User.query.filter(
            User.role == role,
            User.active == True
        )
        
        # Se l'utente non è admin, filtra per sede
        if current_user.role != 'Amministratore' and current_user.sede_obj:
            query = query.filter(User.sede_id == current_user.sede_obj.id)
        
        users = query.order_by(User.first_name, User.last_name).all()
        
        users_data = []
        for user in users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.get_full_name(),
                'role': user.role
            })
        
        return jsonify({
            'success': True,
            'users': users_data
        })
        
    except Exception as e:
        print(f"Errore API users_by_role: {e}")
        return jsonify({'error': 'Errore interno del server'}), 500

@app.route('/api/update_shift/<int:shift_id>', methods=['POST'])
@login_required  
def api_update_shift(shift_id):
    """API per aggiornare l'assegnazione di un turno"""
    try:
        if not current_user.can_access_turni():
            return jsonify({'error': 'Non autorizzato'}), 403
        
        shift = Shift.query.get_or_404(shift_id)
        
        # Verifica che il turno non sia passato
        from datetime import date
        if shift.date < date.today():
            return jsonify({'error': 'Non è possibile modificare turni passati'}), 400
        
        # Verifica permessi sulla sede (se non admin)
        if current_user.role != 'Amministratore':
            if not current_user.sede_obj or current_user.sede_obj.id != shift.user.sede_id:
                return jsonify({'error': 'Non hai i permessi per modificare turni per questa sede'}), 403
        
        # Per chiamate AJAX, Flask-WTF non richiede CSRF per API routes
        data = request.get_json()
        new_user_id = data.get('new_user_id')
        
        if not new_user_id:
            return jsonify({'error': 'ID utente richiesto'}), 400
        
        new_user = User.query.get(new_user_id)
        if not new_user:
            return jsonify({'error': 'Utente non trovato'}), 404
        
        # Verifica che il nuovo utente abbia il ruolo appropriato
        # Il ruolo del turno è determinato dal ruolo dell'utente originale
        current_shift_role = shift.user.role if shift.user else None
        if current_shift_role and new_user.role != current_shift_role:
            return jsonify({'error': f'Il nuovo utente deve avere il ruolo {current_shift_role}'}), 400
        
        # Verifica sovrapposizioni
        overlapping_shift = Shift.query.filter(
            Shift.user_id == new_user_id,
            Shift.date == shift.date,
            Shift.id != shift.id,
            # Controlla sovrapposizione oraria
            db.or_(
                db.and_(Shift.start_time <= shift.start_time, Shift.end_time > shift.start_time),
                db.and_(Shift.start_time < shift.end_time, Shift.end_time >= shift.end_time),
                db.and_(Shift.start_time >= shift.start_time, Shift.end_time <= shift.end_time)
            )
        ).first()
        
        if overlapping_shift:
            return jsonify({
                'error': f'Sovrapposizione rilevata: l\'utente selezionato ha già un turno dalle {overlapping_shift.start_time.strftime("%H:%M")} alle {overlapping_shift.end_time.strftime("%H:%M")}'
            }), 400
        
        # Salva i valori originali per il log
        old_user = shift.user.get_full_name()
        
        # Aggiorna il turno
        shift.user_id = new_user_id
        db.session.commit()
        
        # Log dell'operazione
        print(f"Turno {shift_id} aggiornato: {old_user} -> {new_user.get_full_name()}")
        
        return jsonify({
            'success': True,
            'message': f'Turno aggiornato da {old_user} a {new_user.get_full_name()}'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Errore API update_shift: {e}")
        return jsonify({'error': 'Errore interno del server'}), 500

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