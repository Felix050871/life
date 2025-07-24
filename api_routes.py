from flask import jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import app, db
from models import User, Shift, PresidioCoverageTemplate, PresidioCoverage
import json

@app.route('/api/get_shifts_for_template/<int:template_id>')
@login_required
def api_get_shifts_for_template(template_id):
    print(f"*** ROUTE CHIAMATA: /api/get_shifts_for_template/{template_id} ***", flush=True)
    print(f"=== API get_shifts_for_template called with template_id={template_id} ===", flush=True)
    
    # Trova il template
    template = PresidioCoverageTemplate.query.get_or_404(template_id)
    print(f"Template found: {template.name}, period: {template.start_date} to {template.end_date}", flush=True)
    
    # Ottieni tutti i turni nel periodo del template
    shifts = Shift.query.filter(
        Shift.date >= template.start_date,
        Shift.date <= template.end_date
    ).all()
    
    print(f"API Debug: Found {len(shifts)} shifts for template {template_id}")
    
    # Ottieni le coperture richieste per il template per identificare ruoli mancanti
    coverages = PresidioCoverage.query.filter_by(
        template_id=template_id,
        is_active=True
    ).all()
    
    # Mappa i ruoli richiesti per ogni giorno della settimana e fascia oraria
    required_roles_map = {}
    print(f"Processing {len(coverages)} coverages for required roles mapping")
    for coverage in coverages:
        try:
            # Usa il metodo del modello per ottenere i ruoli
            required_roles = coverage.get_required_roles_list() if hasattr(coverage, 'get_required_roles_list') else []
            if not required_roles:
                # Fallback al parsing JSON diretto
                required_roles = json.loads(coverage.required_roles) if coverage.required_roles else []
            
            # Se è un dict (formato {"Operatore": 2}), estrai solo le chiavi (nomi ruoli)  
            if isinstance(required_roles, dict):
                required_roles = list(required_roles.keys())
            
            day = coverage.day_of_week  # Usa solo il giorno specifico della copertura
            
            print(f"Coverage ID {coverage.id}: day_of_week={day}, time={coverage.start_time}-{coverage.end_time}")
            print(f"  Raw required_roles field: {coverage.required_roles}")
            print(f"  Parsed required_roles: {required_roles}")
            
            if day not in required_roles_map:
                required_roles_map[day] = {}
            time_key = f"{coverage.start_time.strftime('%H:%M')}-{coverage.end_time.strftime('%H:%M')}"
            if time_key not in required_roles_map[day]:
                required_roles_map[day][time_key] = []
            required_roles_map[day][time_key].extend(required_roles)
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Error processing coverage {coverage.id}: {e}")
            continue
    
    print(f"Final required_roles_map: {required_roles_map}")
    
    if len(shifts) == 0:
        print(f"No shifts found in period {template.start_date} to {template.end_date}")
        # Anche senza turni, crea le settimane con informazioni sui ruoli mancanti
        weeks_data = {}
        current_date = template.start_date
        while current_date <= template.end_date:
            week_start = current_date - timedelta(days=current_date.weekday())
            week_key = week_start.strftime('%Y-%m-%d')
            
            if week_key not in weeks_data:
                weeks_data[week_key] = {
                    'start': week_start.strftime('%d/%m/%Y'),
                    'end': (week_start + timedelta(days=6)).strftime('%d/%m/%Y'),
                    'days': {i: {'date': (week_start + timedelta(days=i)).strftime('%d/%m'), 'shifts': [], 'missing_roles': []} for i in range(7)},
                    'shift_count': 0,
                    'unique_users': 0,
                    'total_hours': 0
                }
                
                # Aggiungi ruoli mancanti per ogni giorno
                for day_index in range(7):
                    day_data = weeks_data[week_key]['days'][day_index]
                    if day_index in required_roles_map:
                        for time_slot, required_roles in required_roles_map[day_index].items():
                            for required_role in required_roles:
                                day_data['missing_roles'].append({
                                    'role': required_role,
                                    'time_slot': time_slot
                                })
            
            current_date += timedelta(days=1)
        
        sorted_weeks = sorted(weeks_data.items(), key=lambda x: x[0])
        return jsonify({
            'success': True,
            'weeks': [week_data for _, week_data in sorted_weeks],
            'template_name': template.name
        })
    


    # Organizza i turni per settimana
    weeks_data = {}
    
    for shift in shifts:
        # Calcola la settimana di appartenenza
        week_start = shift.date - timedelta(days=shift.date.weekday())
        week_key = week_start.strftime('%Y-%m-%d')
        
        if week_key not in weeks_data:
            weeks_data[week_key] = {
                'start': week_start.strftime('%d/%m/%Y'),
                'end': (week_start + timedelta(days=6)).strftime('%d/%m/%Y'),
                'days': {i: {'date': (week_start + timedelta(days=i)).strftime('%d/%m'), 'shifts': []} for i in range(7)},
                'shift_count': 0,
                'unique_users': set(),
                'total_hours': 0
            }
        
        day_index = shift.date.weekday()
        shift_data = {
            'id': shift.id,
            'user': shift.user.username,
            'user_id': shift.user.id,
            'role': shift.user.role if isinstance(shift.user.role, str) else (shift.user.role.name if shift.user.role else 'Senza ruolo'),
            'time': f"{shift.start_time.strftime('%H:%M')}-{shift.end_time.strftime('%H:%M')}"
        }
        print(f"API Debug - Shift {shift.id}: user={shift.user.username}, role={shift.user.role if isinstance(shift.user.role, str) else (shift.user.role.name if shift.user.role else 'None')}")
        print(f"API Debug - Full shift data: {shift_data}")  # Debug temporaneo
        weeks_data[week_key]['days'][day_index]['shifts'].append(shift_data)
        
        weeks_data[week_key]['shift_count'] += 1
        weeks_data[week_key]['unique_users'].add(shift.user.username)
        
        # Calcola le ore del turno
        start_datetime = datetime.combine(shift.date, shift.start_time)
        end_datetime = datetime.combine(shift.date, shift.end_time)
        if end_datetime < start_datetime:  # Turno notturno
            end_datetime += timedelta(days=1)
        hours = (end_datetime - start_datetime).total_seconds() / 3600
        weeks_data[week_key]['total_hours'] += hours
    
    # Converti i set in count e aggiungi informazioni sui ruoli mancanti
    for week_data in weeks_data.values():
        week_data['unique_users'] = len(week_data['unique_users'])
        
        # Per ogni giorno della settimana, verifica se ci sono ruoli richiesti ma non coperti
        for day_index in range(7):
            day_data = week_data['days'][day_index]
            day_data['missing_roles'] = []
            
            if day_index in required_roles_map:
                for time_slot, required_roles in required_roles_map[day_index].items():
                    # Ottieni i ruoli presenti nei turni esistenti per questa fascia oraria
                    existing_roles = []
                    for shift in day_data['shifts']:
                        if shift['time'] == time_slot:
                            existing_roles.append(shift['role'])
                    
                    print(f"Time slot {time_slot} on day {day_index}: required={required_roles}, existing={existing_roles}")
                    
                    # Identifica ruoli richiesti ma mancanti
                    for required_role in required_roles:
                        # Conta quanti turni ci sono per questo ruolo nella fascia oraria
                        role_count = existing_roles.count(required_role)
                        print(f"Role {required_role} in time slot {time_slot}: count={role_count}")
                        
                        if role_count == 0:
                            print(f"Missing role: {required_role} for time slot {time_slot}")
                            day_data['missing_roles'].append({
                                'role': required_role,
                                'time_slot': time_slot
                            })
                        # Se servono più persone dello stesso ruolo, potrebbero essere necessari controlli aggiuntivi qui
    
    # Ordina le settimane per data
    sorted_weeks = sorted(weeks_data.items(), key=lambda x: x[0])
    
    response_data = {
        'success': True,
        'weeks': [week_data for _, week_data in sorted_weeks],
        'template_name': template.name,
        'period': template.get_period_display()
    }
    
    # Debug dei missing_roles per verificare se vengono popolati
    total_missing_roles = 0
    for i, week in enumerate(response_data['weeks']):
        for day_idx, day in week['days'].items():
            if day.get('missing_roles'):
                total_missing_roles += len(day['missing_roles'])
                print(f"Week {i}, Day {day_idx} has missing roles: {day['missing_roles']}")
    
    print(f"=== TOTAL MISSING ROLES FOUND: {total_missing_roles} ===")
    
    # Debug della prima settimana per verificare i campi
    if response_data['weeks'] and response_data['weeks'][0]['days'][0]['shifts']:
        first_shift = response_data['weeks'][0]['days'][0]['shifts'][0]
        print(f"=== First shift in response: {first_shift} ===")
    
    return jsonify(response_data)

@app.route('/api/get_users_by_role')
@login_required
def api_get_users_by_role():
    role = request.args.get('role')
    template_id = request.args.get('template_id')
    shift_date = request.args.get('shift_date')  # Data del turno da modificare
    
    print(f"API Debug: role='{role}', template_id='{template_id}', shift_date='{shift_date}'")
    
    # Debug aggiuntivo per verificare il filtro
    if not role or role == 'undefined':
        print(f"Role undefined! Restituisco lista vuota.")
        return jsonify([])
    
    if not role or not template_id:
        return jsonify({'error': 'Role e Template ID richiesti'}), 400
    
    # Trova il template per ottenere la sede
    template = PresidioCoverageTemplate.query.get_or_404(template_id)
    
    # Trova tutti gli utenti con il ruolo specificato e attivi
    users = User.query.filter_by(role=role, active=True).all()
    
    print(f"API Debug: Found {len(users)} users with role '{role}' and active=True")
    
    # Filtra gli utenti abilitati per la sede del template
    available_users = []
    for user in users:
        # Controlla se user ha sede_id o relazione sede
        user_sede_name = "None"
        if hasattr(user, 'sede_id') and user.sede_id:
            user_sede_name = f"sede_id_{user.sede_id}"
        elif hasattr(user, 'sede') and user.sede:
            user_sede_name = user.sede.name
            
        template_sede_name = template.sede.name if template.sede else "None"
        print(f"API Debug: User {user.username} - sede: {user_sede_name}, template sede: {template_sede_name}, all_sedi: {user.all_sedi}")
        
        # Utente abilitato se: ha all_sedi=True OR sede_id coincide OR entrambi hanno sede=None
        user_sede_id = getattr(user, 'sede_id', None)
        template_sede_id = template.sede.id if template.sede else None
        
        if user.all_sedi or user_sede_id == template_sede_id or (user_sede_id is None and template_sede_id is None):
            available_users.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.get_full_name()
            })
            print(f"API Debug: User {user.username} ADDED to available list")
        else:
            print(f"API Debug: User {user.username} EXCLUDED (sede mismatch)")
    
    print(f"API Debug: Returning {len(available_users)} available users")
    
    # Se è specificata una data, filtra gli utenti già impegnati quel giorno
    if shift_date:
        try:
            from datetime import datetime
            date_obj = datetime.strptime(shift_date, '%Y-%m-%d').date()
            
            # Trova tutti i turni per quella data
            busy_users = db.session.query(Shift.user_id).filter(
                Shift.date == date_obj
            ).distinct().all()
            busy_user_ids = [user_id[0] for user_id in busy_users]
            
            print(f"API Debug: Users busy on {shift_date}: {busy_user_ids}")
            
            # Filtra gli utenti già impegnati
            final_users = [user for user in available_users if user['id'] not in busy_user_ids]
            
            print(f"API Debug: After filtering busy users: {len(final_users)} available")
            return jsonify(final_users)
            
        except Exception as e:
            print(f"API Debug: Error filtering by date: {e}")
    
    return jsonify(available_users)
    
    if not role or not template_id:
        return jsonify({'error': 'Parametri mancanti'}), 400
    
    # Trova il template per ottenere la sede
    template = PresidioCoverageTemplate.query.get_or_404(template_id)
    sede_id = template.sede_id
    
    # Trova utenti con lo stesso ruolo abilitati alla sede
    users = User.query.filter(
        User.role == role,
        User.is_active == True,
        db.or_(User.sede_id == sede_id, User.all_sedi == True)
    ).all()
    
    return jsonify([{
        'id': user.id,
        'username': user.username
    } for user in users])

@app.route('/api/update_shift_user', methods=['POST'])
@login_required
def api_update_shift_user():
    if not current_user.can_manage_shifts():
        return jsonify({'error': 'Non autorizzato'}), 403
    
    shift_id = request.form.get('shift_id') 
    new_user_id = request.form.get('user_id')
    
    print(f"API Debug: update_shift_user called - shift_id={shift_id}, user_id={new_user_id}")
    
    if not shift_id or not new_user_id:
        return jsonify({'error': 'Parametri mancanti'}), 400
    
    # Trova il turno
    shift = Shift.query.get_or_404(shift_id)
    
    # Trova il nuovo utente
    new_user = User.query.get_or_404(new_user_id)
    
    # Verifica che il nuovo utente abbia lo stesso ruolo
    if new_user.role != shift.user.role:
        return jsonify({
            'success': False,
            'message': 'Il nuovo utente deve avere lo stesso ruolo dell\'utente originale'
        })
    
    # Per ora non verifichiamo la sede specifica, solo che sia attivo
    # TODO: aggiungere logica di verifica sede quando disponibile
    
    # Aggiorna il turno
    shift.user_id = new_user_id
    db.session.commit()
    
    return jsonify({
        'success': True,
        'user': {
            'id': new_user.id,
            'username': new_user.username,
            'full_name': new_user.get_full_name()
        }
    })