from flask import jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import app, db
from models import User, Shift, PresidioCoverageTemplate

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
    if len(shifts) == 0:
        print(f"No shifts found in period {template.start_date} to {template.end_date}")
        return jsonify({'weeks': [], 'template_name': template.name})
    
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
    
    # Converti i set in count
    for week_data in weeks_data.values():
        week_data['unique_users'] = len(week_data['unique_users'])
    
    # Ordina le settimane per data
    sorted_weeks = sorted(weeks_data.items(), key=lambda x: x[0])
    
    response_data = {
        'success': True,
        'weeks': [week_data for _, week_data in sorted_weeks],
        'template_name': template.name,
        'period': template.get_period_display()
    }
    
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
    
    print(f"API Debug: role='{role}', template_id='{template_id}'")
    
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
            'username': new_user.username
        }
    })