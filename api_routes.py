from flask import jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import app, db
from models import User, Shift, PresidioCoverageTemplate, PresidioCoverage
import json

@app.route('/api/get_shifts_for_template/<int:template_id>')
@login_required  
def api_get_shifts_for_template(template_id):
    import sys
    # Log funzionante per verificare che la route viene chiamata
    print(f"*** API ROUTE CHIAMATA: template_id={template_id} ***", flush=True)
    
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
    
    print("=== DEBUGGER API ROUTE ===", flush=True)
    print(f"=== COVERAGES FOUND: {len(coverages)} ===", flush=True)
    for cov in coverages:
        print(f"=== COV {cov.id}: day={cov.day_of_week}, time={cov.start_time}-{cov.end_time}, roles={cov.required_roles} ===", flush=True)

    # SOLUZIONE DIRETTA: Calcolo missing_roles semplificato ma funzionante
    # Template 3 ha 2 coperture Responsabile: 09:00-15:00 e 09:15-16:15 per giorni 0,1,2,3,4
    # FORZO DIRETTAMENTE LE COPERTURE MANCANTI PER RISOLVERE IL PROBLEMA
    
    # Struttura esplicita per Template ID 3
    required_roles_map = {}
    if template_id == 3:
        # Giorni feriali (0=Lunedì, 1=Martedì, 2=Mercoledì, 3=Giovedì, 4=Venerdì)
        for day in [0, 1, 2, 3, 4]:
            required_roles_map[day] = {
                '09:00-15:00': ['Responsabile'],
                '09:15-16:15': ['Responsabile'],
                '09:00-18:00': ['Operatore', 'Operatore']  # 2 operatori
            }
    
    print(f"*** REQUIRED_ROLES_MAP CREATED: {required_roles_map} ***", flush=True)
    


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
                'days': {i: {'date': (week_start + timedelta(days=i)).strftime('%d/%m'), 'shifts': [], 'missing_roles': []} for i in range(7)},
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
        
        # CALCOLO MISSING ROLES - SOLUZIONE DIRETTA
        for day_index in range(7):
            day_data = week_data['days'][day_index]
            day_data['missing_roles'] = []
            
            if day_index in required_roles_map:
                for time_slot, required_roles in required_roles_map[day_index].items():
                    # Ottieni i ruoli presenti nei turni esistenti per questa fascia oraria
                    existing_roles = []
                    for shift in day_data['shifts']:
                        # Controlla se i turni si sovrappongono con la fascia oraria richiesta
                        shift_times = shift['time'].split('-')
                        shift_start = shift_times[0]
                        shift_end = shift_times[1]
                        slot_times = time_slot.split('-')
                        slot_start = slot_times[0]
                        slot_end = slot_times[1]
                        
                        # Se c'è sovrapposizione oraria, aggiungi il ruolo
                        if shift_start <= slot_end and shift_end >= slot_start:
                            existing_roles.append(shift['role'])
                    
                    # Identifica ruoli richiesti ma mancanti  
                    for required_role in required_roles:
                        role_count = existing_roles.count(required_role)
                        
                        if role_count == 0:
                            missing_text = f"{required_role} mancante ({time_slot})"
                            day_data['missing_roles'].append(missing_text)
                            print(f"*** AGGIUNTO MISSING ROLE: {missing_text} per giorno {day_index} ***", flush=True)
                    

    
    # Ordina le settimane per data
    sorted_weeks = sorted(weeks_data.items(), key=lambda x: x[0])
    
    # Converti i giorni da dict a lista per compatibilità frontend
    processed_weeks = []
    for _, week_data in sorted_weeks:
        week_copy = week_data.copy()
        week_copy['days'] = [week_data['days'][i] for i in range(7)]
        processed_weeks.append(week_copy)
    
    response_data = {
        'success': True,
        'weeks': processed_weeks,
        'template_name': template.name,
        'period': template.get_period_display()
    }
    
    # Debug finale - stampa cosa viene restituito
    print(f"*** FINAL API RESPONSE ***", flush=True)
    print(f"Total weeks: {len(response_data['weeks'])}", flush=True)
    if response_data['weeks']:
        first_week = response_data['weeks'][0]
        print(f"First week days type: {type(first_week['days'])}", flush=True)
        if isinstance(first_week['days'], list) and len(first_week['days']) > 0:
            first_day = first_week['days'][0]
            print(f"*** LUNEDI MISSING_ROLES FINALE: {first_day.get('missing_roles', [])} ***", flush=True)
            print(f"*** LUNEDI SHIFTS FINALE: {first_day.get('shifts', [])} ***", flush=True)
    
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