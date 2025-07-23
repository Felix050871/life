from flask import jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import app, db
from models import User, Shift, PresidioCoverageTemplate

@app.route('/api/get_shifts_for_template')
@login_required
def api_get_shifts_for_template():
    template_id = request.args.get('template_id')
    if not template_id:
        return jsonify({'error': 'Template ID richiesto'}), 400
    
    # Trova il template
    template = PresidioCoverageTemplate.query.get_or_404(template_id)
    
    # Ottieni tutti i turni per questo template
    shifts = Shift.query.filter_by(presidio_coverage_template_id=template_id).all()
    
    # Organizza i turni per settimana
    weeks_data = {}
    
    for shift in shifts:
        # Calcola la settimana di appartenenza
        week_start = shift.shift_date - timedelta(days=shift.shift_date.weekday())
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
        
        day_index = shift.shift_date.weekday()
        shift_data = {
            'id': shift.id,
            'user': shift.user.username,
            'user_id': shift.user.id,
            'role': shift.user.role,
            'time': f"{shift.start_time.strftime('%H:%M')}-{shift.end_time.strftime('%H:%M')}"
        }
        print(f"API Debug - Shift data: {shift_data}")  # Debug temporaneo
        weeks_data[week_key]['days'][day_index]['shifts'].append(shift_data)
        
        weeks_data[week_key]['shift_count'] += 1
        weeks_data[week_key]['unique_users'].add(shift.user.username)
        
        # Calcola le ore del turno
        start_datetime = datetime.combine(shift.shift_date, shift.start_time)
        end_datetime = datetime.combine(shift.shift_date, shift.end_time)
        if end_datetime < start_datetime:  # Turno notturno
            end_datetime += timedelta(days=1)
        hours = (end_datetime - start_datetime).total_seconds() / 3600
        weeks_data[week_key]['total_hours'] += hours
    
    # Converti i set in count
    for week_data in weeks_data.values():
        week_data['unique_users'] = len(week_data['unique_users'])
    
    # Ordina le settimane per data
    sorted_weeks = sorted(weeks_data.items(), key=lambda x: x[0])
    
    return jsonify({
        'weeks': [week_data for _, week_data in sorted_weeks],
        'template_name': template.name
    })

@app.route('/api/get_users_by_role')
@login_required
def api_get_users_by_role():
    role = request.args.get('role')
    template_id = request.args.get('template_id')
    
    print(f"API Debug: role='{role}', template_id='{template_id}'")
    
    if not role or not template_id:
        return jsonify({'error': 'Role e Template ID richiesti'}), 400
    
    # Trova il template per ottenere la sede
    template = PresidioCoverageTemplate.query.get_or_404(template_id)
    
    # Trova tutti gli utenti con il ruolo specificato e abilitati per la sede del template
    users = User.query.filter_by(role=role, is_active=True).all()
    
    # Filtra gli utenti abilitati per la sede del template
    available_users = []
    for user in users:
        if user.all_sedi or user.sede == template.sede:
            available_users.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.get_full_name()
            })
    
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
    
    # Verifica che il nuovo utente sia abilitato alla sede
    template = shift.presidio_coverage_template
    if not new_user.all_sedi and new_user.sede_id != template.sede_id:
        return jsonify({
            'success': False,
            'message': 'Il nuovo utente non è abilitato a questa sede'
        })
    
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