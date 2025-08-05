from datetime import datetime, timedelta
from flask import jsonify, request
from flask_login import login_required, current_user
from app import app, db, csrf
from models import User, Shift, PresidioCoverageTemplate, PresidioCoverage, UserRole
import json
import logging
from utils import split_coverage_into_segments_by_user_capacity
from new_shift_generation import calculate_shift_duration
from datetime import datetime, date, time

# Setup logging for API routes
logger = logging.getLogger(__name__)

@app.route('/api/get_shifts_for_template/<int:template_id>')
@login_required  
def api_get_shifts_for_template(template_id):
    """API RISCRITTA COMPLETAMENTE - CALCOLO MISSING_ROLES SEMPLICE E FUNZIONANTE"""
    
    try:
        template = PresidioCoverageTemplate.query.get_or_404(template_id)
        
        # STEP 1: Organizza turni per settimana - USA FRESH DATA DAL DATABASE
        weeks_data = {}
        # Forza refresh completo sessione database
        db.session.expire_all()
        db.session.commit()
        
        # Query SEMPLICE senza doppi join che possono causare problemi
        fresh_shifts = Shift.query.filter(
            Shift.date >= template.start_date,
            Shift.date <= template.end_date
        ).all()
        
        # DEBUG: Log tutti i turni trovati
        logger.info(f"FOUND {len(fresh_shifts)} shifts for template {template_id} from {template.start_date} to {template.end_date}")
        for shift in fresh_shifts:
            logger.info(f"SHIFT {shift.id}: {shift.date} {shift.start_time}-{shift.end_time} user_id={shift.user_id}")
            if shift.user:
                logger.info(f"  USER: {shift.user.first_name} {shift.user.last_name} role={shift.user.role}")
        
        # STEP 2: Crea struttura settimane PRIMA di processare i turni
        # Crea settimane per tutto il periodo del template
        current_date = template.start_date
        while current_date <= template.end_date:
            week_start = current_date - timedelta(days=current_date.weekday())
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
                    week_date = week_start + timedelta(days=i)
                    weeks_data[week_key]['days'].append({
                        'date': week_date.strftime('%d/%m'),
                        'shifts': [],
                        'missing_roles': []
                    })
            current_date += timedelta(days=7)
        
        # STEP 3: Processa i turni nella struttura già creata
        for shift in fresh_shifts:
            week_start = shift.date - timedelta(days=shift.date.weekday())
            week_key = week_start.strftime('%Y-%m-%d')
            day_index = shift.date.weekday()
            
            # DEBUG: Log per capire dove vanno i turni
            shift_date_str = shift.date.strftime('%d/%m')
            logger.info(f"PROCESSING shift {shift.id} for date {shift_date_str} (weekday {day_index}) in week {week_key}")
            
            if week_key in weeks_data and day_index < len(weeks_data[week_key]['days']):
                # Usa il nome completo invece del username
                user_name = f"{shift.user.first_name} {shift.user.last_name}" if shift.user else "Utente sconosciuto"
                user_role = shift.user.role if shift.user and isinstance(shift.user.role, str) else (shift.user.role.name if shift.user and shift.user.role else 'Senza ruolo')
                
                shift_data = {
                    'id': shift.id,
                    'user': user_name,
                    'user_id': shift.user.id if shift.user else None,
                    'role': user_role,
                    'time': f"{shift.start_time.strftime('%H:%M')}-{shift.end_time.strftime('%H:%M')}"
                }
                weeks_data[week_key]['days'][day_index]['shifts'].append(shift_data)
                weeks_data[week_key]['shift_count'] += 1
                weeks_data[week_key]['unique_users'].add(shift.user.username if shift.user else "unknown")
                
                logger.info(f"ADDED shift to week {week_key} day {day_index}: {shift_data}")
            else:
                logger.error(f"Could not find week {week_key} or invalid day index {day_index}")
        
        # STEP 4: Converti set in count
        for week_data in weeks_data.values():
            week_data['unique_users'] = len(week_data['unique_users'])
        
        # STEP 5: CALCOLA MISSING_ROLES - LOGICA SEMPLIFICATA
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

@app.route('/api/get_users_by_role/<role_name>')
@login_required
def api_get_users_by_role(role_name):
    """API per ottenere utenti attivi per un ruolo specifico"""
    try:
        users = User.query.filter_by(active=True).all()
        
        # Filtra utenti che hanno il ruolo richiesto
        filtered_users = []
        for user in users:
            if user.role and user.role == role_name:
                filtered_users.append({
                    'id': user.id,
                    'username': user.username,
                    'full_name': user.get_full_name(),
                    'role': user.role
                })
        
        return jsonify({
            'success': True,
            'users': filtered_users
        })
        
    except Exception as e:
        logger.error(f"Error in get_users_by_role: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/update_shift/<int:shift_id>', methods=['PUT'])
@csrf.exempt
@login_required
def api_update_shift(shift_id):
    """API per aggiornare l'assegnazione di un turno esistente"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID richiesto'}), 400
        
        # Verifica che l'utente esista ed sia attivo
        user = User.query.filter_by(id=user_id, active=True).first()
        if not user:
            return jsonify({'success': False, 'message': 'Utente non trovato o non attivo'}), 404
        
        # Trova il turno
        shift = Shift.query.get_or_404(shift_id)
        
        # Aggiorna l'assegnazione
        old_user_id = shift.user_id
        shift.user_id = user_id
        
        # Log dell'aggiornamento
        logger.info(f"Updating shift {shift_id}: user_id {old_user_id} -> {user_id}")
        
        try:
            db.session.commit()
            logger.info(f"Successfully updated shift {shift_id}")
        except Exception as commit_error:
            db.session.rollback()
            logger.error(f"Error committing shift update: {str(commit_error)}")
            raise
        
        return jsonify({
            'success': True,
            'message': f'Turno assegnato a {user.get_full_name()}',
            'shift': {
                'id': shift.id,
                'user': user.get_full_name(),
                'user_id': user.id,
                'date': shift.date.strftime('%d/%m/%Y'),
                'start_time': shift.start_time.strftime('%H:%M'),
                'end_time': shift.end_time.strftime('%H:%M')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in update_shift: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/create_shift', methods=['POST'])
@csrf.exempt
@login_required
def api_create_shift():
    """API per creare un nuovo turno per uno slot scoperto"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        shift_date = data.get('date')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        if not all([user_id, shift_date, start_time, end_time]):
            return jsonify({'success': False, 'message': 'Tutti i campi sono richiesti'}), 400
        
        # Verifica che l'utente esista ed sia attivo
        user = User.query.filter_by(id=user_id, active=True).first()
        if not user:
            return jsonify({'success': False, 'message': 'Utente non trovato o non attivo'}), 404
        
        # Converti stringhe in oggetti datetime
        shift_date_obj = datetime.strptime(shift_date, '%Y-%m-%d').date()
        start_time_obj = datetime.strptime(start_time, '%H:%M').time()
        end_time_obj = datetime.strptime(end_time, '%H:%M').time()
        
        # Verifica che non esista già un turno per questo utente nello stesso orario
        existing_shift = Shift.query.filter_by(
            user_id=user_id,
            date=shift_date_obj,
            start_time=start_time_obj,
            end_time=end_time_obj
        ).first()
        
        if existing_shift:
            return jsonify({'success': False, 'message': 'Esiste già un turno per questo utente nello stesso orario'}), 409
        
        # Crea il nuovo turno
        new_shift = Shift(
            user_id=user_id,
            date=shift_date_obj,
            start_time=start_time_obj,
            end_time=end_time_obj
        )
        
        db.session.add(new_shift)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Nuovo turno creato per {user.get_full_name()}',
            'shift': {
                'id': new_shift.id,
                'user': user.get_full_name(),
                'user_id': user.id,
                'date': new_shift.date.strftime('%d/%m/%Y'),
                'start_time': new_shift.start_time.strftime('%H:%M'),
                'end_time': new_shift.end_time.strftime('%H:%M')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in create_shift: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
