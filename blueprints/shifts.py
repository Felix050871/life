# =============================================================================
# SHIFTS BLUEPRINT - Modulo gestione turni e scheduling
# =============================================================================
#
# ROUTES INCLUSE:
# 1. turni_automatici (GET) - Creazione automatica turni da template
# 2. api/get_shifts_for_template/<template_id> (GET) - API turni template
# 3. visualizza_turni (GET) - Visualizzazione turni
# 4. genera_turni_da_template (POST) - Generazione turni da template
# 5. create_shift (POST) - Creazione singolo turno
# 6. generate_shifts (POST) - Generazione multipla turni
# 7. regenerate_template/<template_id> (POST) - Rigenerazione template
# 8. delete_template/<template_id> (POST) - Eliminazione template
# 9. view_template/<template_id> (GET) - Visualizzazione template
#
# Total routes: 9+ shift management routes
# =============================================================================

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from functools import wraps
from app import db
from models import User, Shift, Sede, PresidioCoverageTemplate, italian_now
from collections import defaultdict
import json

# Create blueprint
shifts_bp = Blueprint('shifts', __name__, url_prefix='/shifts')

# Helper functions
def require_login(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# SHIFT MANAGEMENT ROUTES
# =============================================================================

@shifts_bp.route('/turni_automatici')
@login_required
def turni_automatici():
    """Sistema nuovo: Creazione automatica turni da template presidio"""
    if not (current_user.can_manage_shifts() or current_user.can_view_shifts()):
        flash('Non hai i permessi per accedere ai turni', 'danger')
        return redirect(url_for('dashboard'))
    
    # Ottieni template presidio attivi per creazione turni
    from models import PresidioCoverageTemplate
    presidio_templates = PresidioCoverageTemplate.query.filter_by(active=True).order_by(
        PresidioCoverageTemplate.start_date.desc()
    ).all()
    
    # Ottieni template selezionato se presente
    template_id = request.args.get('template_id')
    selected_template = None
    turni_per_settimana = {}
    settimane_stats = {}
    shifts = []
    
    if template_id:
        try:
            template_id = int(template_id)
            selected_template = PresidioCoverageTemplate.query.get(template_id)
            
            if selected_template:
                # Ottieni turni del template selezionato
                from collections import defaultdict
                from datetime import timedelta, date
                
                # Filtra turni per il periodo del template
                accessible_sedi = current_user.get_turni_sedi()
                if accessible_sedi:
                    shifts = Shift.query.join(User, Shift.user_id == User.id).filter(
                        User.sede_id.in_([sede.id for sede in accessible_sedi]),
                        Shift.date >= selected_template.start_date,
                        Shift.date <= selected_template.end_date,
                        Shift.shift_type == 'presidio'
                    ).order_by(Shift.date.asc(), Shift.start_time.asc()).all()
                else:
                    shifts = []
                
                # Raggruppa turni per settimana e calcola statistiche
                turni_per_settimana = defaultdict(list)
                settimane_stats = defaultdict(lambda: {
                    'inizio': None,
                    'fine': None,
                    'turni_count': 0,
                    'ore_totali': 0.0,
                    'unique_users': set(),
                    'giorni_coperti': set()
                })
                
                for shift in shifts:
                    # Calcola inizio settimana (lunedì)
                    settimana_inizio = shift.date - timedelta(days=shift.date.weekday())
                    settimana_key = settimana_inizio.strftime('%Y-%m-%d')
                    
                    turni_per_settimana[settimana_key].append(shift)
                    
                    # Aggiorna statistiche settimana
                    stats = settimane_stats[settimana_key]
                    if not stats['inizio']:
                        stats['inizio'] = settimana_inizio
                        stats['fine'] = settimana_inizio + timedelta(days=6)
                    
                    stats['turni_count'] = stats['turni_count'] + 1
                    if isinstance(stats['unique_users'], set):
                        stats['unique_users'].add(shift.user_id)
                    if isinstance(stats['giorni_coperti'], set):
                        stats['giorni_coperti'].add(shift.date.isoformat())
                    
                    # Calcola ore totali
                    if shift.start_time and shift.end_time:
                        start_dt = datetime.combine(shift.date, shift.start_time)
                        end_dt = datetime.combine(shift.date, shift.end_time)
                        if end_dt < start_dt:  # Turno notturno
                            end_dt += timedelta(days=1)
                        ore = (end_dt - start_dt).total_seconds() / 3600
                        if isinstance(stats['ore_totali'], (int, float)):
                            stats['ore_totali'] = stats['ore_totali'] + ore
                
                # Converti set in count per JSON serialization
                for settimana_key, stats in settimane_stats.items():
                    if isinstance(stats['unique_users'], set):
                        stats['unique_users'] = len(stats['unique_users'])
                
                # Ordina settimane per data crescente
                settimane_stats = dict(sorted(settimane_stats.items(), 
                                            key=lambda x: x[1]['inizio'] if x[1]['inizio'] else date.min))
                turni_per_settimana = dict(sorted(turni_per_settimana.items()))
        except (ValueError, TypeError):
            pass
    
    # Ottieni utenti disponibili per creazione turni raggruppati per ruolo
    from collections import defaultdict
    users_by_role = defaultdict(list)
    available_users = User.query.filter(
        User.active.is_(True)
    ).all()
    
    for user in available_users:
        if hasattr(user, 'role') and user.role:
            users_by_role[user.role].append(user)
    
    from datetime import date, timedelta
    return render_template('turni_automatici.html', 
                         presidio_templates=presidio_templates,
                         selected_template=selected_template,
                         turni_per_settimana=turni_per_settimana,
                         settimane_stats=settimane_stats,
                         users_by_role=dict(users_by_role),
                         shifts=shifts,
                         today=date.today(),
                         timedelta=timedelta,
                         can_manage_shifts=current_user.can_manage_shifts())

@shifts_bp.route('/api/get_shifts_for_template/<int:template_id>')
@login_required
def get_shifts_for_template_api(template_id):
    """API per ottenere turni di un template specifico"""
    try:
        from models import PresidioCoverageTemplate
        from collections import defaultdict
        from datetime import timedelta, date
        
        template = PresidioCoverageTemplate.query.get_or_404(template_id)
        
        # Ottieni turni del template
        accessible_sedi = current_user.get_turni_sedi()
        if accessible_sedi:
            shifts = Shift.query.join(User, Shift.user_id == User.id).filter(
                User.sede_id.in_([sede.id for sede in accessible_sedi]),
                Shift.date >= template.start_date,
                Shift.date <= template.end_date,
                Shift.shift_type == 'presidio'
            ).order_by(Shift.date.asc(), Shift.start_time.asc()).all()
        else:
            shifts = []
        
        # Raggruppa per settimana
        weeks_data = []
        turni_per_settimana = defaultdict(list)
        
        for shift in shifts:
            settimana_inizio = shift.date - timedelta(days=shift.date.weekday())
            settimana_key = settimana_inizio.strftime('%Y-%m-%d')
            turni_per_settimana[settimana_key].append(shift)
        
        # Converti in formato per frontend
        for settimana_key in sorted(turni_per_settimana.keys()):
            week_shifts = turni_per_settimana[settimana_key]
            settimana_inizio = datetime.strptime(settimana_key, '%Y-%m-%d').date()
            
            week_data = {
                'week_start': settimana_key,
                'week_end': (settimana_inizio + timedelta(days=6)).strftime('%Y-%m-%d'),
                'shifts_count': len(week_shifts),
                'shifts': []
            }
            
            for shift in week_shifts:
                shift_data = {
                    'id': shift.id,
                    'date': shift.date.strftime('%Y-%m-%d'),
                    'start_time': shift.start_time.strftime('%H:%M') if shift.start_time else '',
                    'end_time': shift.end_time.strftime('%H:%M') if shift.end_time else '',
                    'user_name': shift.user.nome + ' ' + shift.user.cognome if shift.user else '',
                    'role': shift.user.role if shift.user else ''
                }
                week_data['shifts'].append(shift_data)
            
            weeks_data.append(week_data)
        
        return jsonify({
            'success': True,
            'template_name': template.name,
            'weeks_data': weeks_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@shifts_bp.route('/visualizza_turni')
@login_required
def visualizza_turni():
    """Visualizzazione turni per mese/settimana"""
    if not (current_user.can_manage_shifts() or current_user.can_view_shifts()):
        flash('Non hai i permessi per visualizzare i turni', 'danger')
        return redirect(url_for('dashboard'))
    
    # Ottieni parametri filtro
    view_mode = request.args.get('view', 'month')  # month, week
    selected_date = request.args.get('date')
    sede_filter = request.args.get('sede')
    
    # Parse data selezionata
    if selected_date:
        try:
            target_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except:
            target_date = date.today()
    else:
        target_date = date.today()
    
    # Calcola range di date in base alla modalità
    if view_mode == 'week':
        # Vista settimanale: dal lunedì alla domenica
        start_date = target_date - timedelta(days=target_date.weekday())
        end_date = start_date + timedelta(days=6)
    else:
        # Vista mensile
        start_date = target_date.replace(day=1)
        if target_date.month == 12:
            end_date = date(target_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = target_date.replace(month=target_date.month + 1, day=1) - timedelta(days=1)
    
    # Query turni nel range
    query = Shift.query.filter(
        Shift.date >= start_date,
        Shift.date <= end_date
    )
    
    # Filtro per sede se specificato
    if sede_filter and sede_filter != 'all':
        try:
            sede_id = int(sede_filter)
            query = query.join(User, Shift.user_id == User.id).filter(User.sede_id == sede_id)
        except:
            pass
    
    # Controllo permessi sede
    accessible_sedi = current_user.get_turni_sedi()
    if accessible_sedi:
        sede_ids = [sede.id for sede in accessible_sedi]
        query = query.join(User, Shift.user_id == User.id).filter(User.sede_id.in_(sede_ids))
    
    shifts = query.order_by(Shift.date.asc(), Shift.start_time.asc()).all()
    
    # Ottieni sedi per filtro
    if accessible_sedi:
        available_sedi = accessible_sedi
    else:
        available_sedi = Sede.query.filter_by(active=True).all()
    
    # Raggruppa turni per giorno
    shifts_by_date = defaultdict(list)
    for shift in shifts:
        shifts_by_date[shift.date].append(shift)
    
    return render_template('shifts.html',
                         shifts=shifts,
                         shifts_by_date=dict(shifts_by_date),
                         view_mode=view_mode,
                         target_date=target_date,
                         start_date=start_date,
                         end_date=end_date,
                         available_sedi=available_sedi,
                         selected_sede=sede_filter,
                         can_manage_shifts=current_user.can_manage_shifts())

@shifts_bp.route('/genera_turni_da_template', methods=['POST'])
@login_required
def genera_turni_da_template():
    """Genera turni automaticamente da template presidio selezionato"""
    if not current_user.can_manage_shifts():
        return jsonify({'success': False, 'message': 'Non hai i permessi per generare turni'}), 403
    
    try:
        template_id = request.form.get('template_id')
        if not template_id:
            return jsonify({'success': False, 'message': 'Template ID richiesto'}), 400
        
        template = PresidioCoverageTemplate.query.get_or_404(int(template_id))
        
        # Import logica generazione turni da utils
        from utils import generate_shifts_from_template
        result = generate_shifts_from_template(template)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': f'Generati {result["generated_count"]} turni per {template.name}',
                'generated_count': result['generated_count']
            })
        else:
            return jsonify({'success': False, 'message': result.get('message', 'Errore nella generazione turni')}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Errore: {str(e)}'}), 500

@shifts_bp.route('/create_shift', methods=['POST'])
@login_required 
def create_shift():
    """Crea un singolo turno manualmente"""
    if not current_user.can_manage_shifts():
        return jsonify({'success': False, 'message': 'Non hai i permessi per creare turni'}), 403
        
    try:
        user_id = request.form.get('user_id')
        date_str = request.form.get('date')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        shift_type = request.form.get('shift_type', 'presidio')
        
        if not all([user_id, date_str, start_time_str, end_time_str]):
            return jsonify({'success': False, 'message': 'Tutti i campi sono richiesti'}), 400
        
        # Parse date e time
        shift_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        user = User.query.get(int(user_id))
        if not user or not user.active:
            return jsonify({'success': False, 'message': 'Utente non trovato o non attivo'}), 400
        
        # Controlla sovrapposizioni
        existing_shifts = Shift.query.filter(Shift.user_id == int(user_id), Shift.date == shift_date).all()
        for existing in existing_shifts:
            if existing.start_time and existing.end_time:
                if (start_time < existing.end_time and end_time > existing.start_time):
                    return jsonify({'success': False, 'message': f'Sovrapposizione con turno esistente'}), 400
        
        # Crea nuovo turno
        new_shift = Shift(
            user_id=int(user_id),
            date=shift_date,
            start_time=start_time,
            end_time=end_time,
            shift_type=shift_type,
            created_by_user_id=current_user.id
        )
        
        db.session.add(new_shift)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Turno creato per {user.nome} {user.cognome}',
            'shift_id': new_shift.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Errore nella creazione turno: {str(e)}'}), 500