# =============================================================================
# ATTENDANCE BLUEPRINT - Modulo gestione presenze e timbrature
# =============================================================================
#
# ROUTES INCLUSE:
# 1. check_shift_before_clock_in (POST) - Controllo pre-entrata
# 2. clock_in (POST) - Timbratura entrata  
# 3. check_shift_before_clock_out (POST) - Controllo pre-uscita
# 4. clock_out (POST) - Timbratura uscita
# 5. break_start (POST) - Inizio pausa
# 6. break_end (POST) - Fine pausa
# 7. attendance (GET/POST) - Pagina principale presenze
# 8. export_attendance_excel (GET) - Export dati presenze
# 9. api/work_hours/<user_id>/<date> (GET) - API ore lavorate
# 10. quick_attendance/<action> (GET/POST) - Timbratura rapida QR
#
# Total routes: 10
# =============================================================================

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, make_response
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from functools import wraps
from app import db
from models import User, AttendanceEvent, Shift, Sede, ReperibilitaShift, Intervention, italian_now
import io
import csv

# Create blueprint
attendance_bp = Blueprint('attendance', __name__, url_prefix='/attendance')

# Helper functions
def get_current_user_sede(user):
    """Get current user's sede - copy from routes.py"""
    if user.sedi:
        return user.sedi[0]  # Return first sede
    return None

def require_login(f):
    """Decorator to require login for routes - copy from routes.py"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# CLOCK IN/OUT PRE-CHECK ROUTES
# =============================================================================

@attendance_bp.route('/check_shift_before_clock_in', methods=['POST'])
@login_required  
def check_shift_before_clock_in():
    """Check if user can clock-in (no shift validation)"""
    # Check if can perform clock-in action
    if not AttendanceEvent.can_perform_action(current_user.id, 'clock_in'):
        status, last_event = AttendanceEvent.get_user_status(current_user.id)
        if status == 'in':
            return jsonify({
                'success': False,
                'message': 'Sei già presente. Devi prima registrare l\'uscita.',
                'already_clocked': True
            })
        elif status == 'break':
            return jsonify({
                'success': False,
                'message': 'Sei in pausa. Devi prima terminare la pausa.',
                'already_clocked': True
            })
    
    # No shift validation - always allow clock-in
    return jsonify({
        'success': True,
        'needs_confirmation': False
    })

@attendance_bp.route('/check_shift_before_clock_out', methods=['POST'])
@login_required  
def check_shift_before_clock_out():
    """Check if user can clock-out (no shift validation)"""
    # Check if user can perform clock-out
    if not AttendanceEvent.can_perform_action(current_user.id, 'clock_out'):
        return jsonify({
            'success': False,
            'message': 'Non puoi registrare l\'uscita in questo momento.'
        })
    
    # No shift validation - always allow clock-out if status permits
    return jsonify({
        'success': True,
        'needs_confirmation': False
    })

# =============================================================================
# CLOCK IN/OUT MAIN ROUTES
# =============================================================================

@attendance_bp.route('/clock_in', methods=['POST'])
@login_required  
def clock_in():
    if not current_user.can_access_attendance():
        return jsonify({
            'success': False,
            'message': 'Non hai i permessi per accedere alle presenze'
        }), 403

    try:
        # Verifica se l'utente può effettuare il clock-in
        if not AttendanceEvent.can_perform_action(current_user.id, 'clock_in'):
            status, last_event = AttendanceEvent.get_user_status(current_user.id)
            if status == 'in':
                return jsonify({
                    'success': False,
                    'message': 'Sei già presente. Devi prima registrare l\'uscita.'
                })
            elif status == 'break':
                return jsonify({
                    'success': False,
                    'message': 'Sei in pausa. Devi prima terminare la pausa.'
                })

        # Crea nuovo evento di entrata
        attendance_event = AttendanceEvent(
            user_id=current_user.id,
            event_type='clock_in',
            timestamp=italian_now(),
            sede_id=get_current_user_sede(current_user).id if get_current_user_sede(current_user) else None
        )
        db.session.add(attendance_event)
        db.session.commit()
        
        # Controlla se c'è un intervento attivo per questo utente
        active_intervention = Intervention.query.filter(
            Intervention.user_id == current_user.id,
            Intervention.end_datetime.is_(None)
        ).first()
        
        intervention_info = None
        if active_intervention:
            intervention_info = {
                'id': active_intervention.id,
                'description': active_intervention.description,
                'priority': active_intervention.priority,
                'start_datetime': active_intervention.start_datetime.strftime('%d/%m/%Y %H:%M') if active_intervention.start_datetime else None
            }

        return jsonify({
            'success': True,
            'message': f'Entrata registrata alle {attendance_event.timestamp.strftime("%H:%M")}',
            'timestamp': attendance_event.timestamp.strftime('%H:%M'),
            'active_intervention': intervention_info
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Errore nel salvare l\'entrata'
        }), 500

@attendance_bp.route('/clock_out', methods=['POST'])
@login_required
def clock_out():
    if not current_user.can_access_attendance():
        return jsonify({
            'success': False,
            'message': 'Non hai i permessi per accedere alle presenze'
        }), 403

    try:
        # Verifica se l'utente può effettuare il clock-out
        if not AttendanceEvent.can_perform_action(current_user.id, 'clock_out'):
            return jsonify({
                'success': False,
                'message': 'Non puoi registrare l\'uscita in questo momento.'
            })

        # Crea nuovo evento di uscita
        attendance_event = AttendanceEvent(
            user_id=current_user.id,
            event_type='clock_out',
            timestamp=italian_now(),
            sede_id=get_current_user_sede(current_user).id if get_current_user_sede(current_user) else None
        )
        db.session.add(attendance_event)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Uscita registrata alle {attendance_event.timestamp.strftime("%H:%M")}',
            'timestamp': attendance_event.timestamp.strftime('%H:%M')
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Errore nel salvare l\'uscita'
        }), 500

# =============================================================================
# BREAK START/END ROUTES
# =============================================================================

@attendance_bp.route('/break_start', methods=['POST'])
@login_required
def break_start():
    if not current_user.can_access_attendance():
        return jsonify({
            'success': False,
            'message': 'Non hai i permessi per accedere alle presenze'
        }), 403

    try:
        # Verifica se l'utente può iniziare la pausa
        if not AttendanceEvent.can_perform_action(current_user.id, 'break_start'):
            return jsonify({
                'success': False,
                'message': 'Non puoi iniziare la pausa in questo momento.'
            })

        # Crea nuovo evento di inizio pausa
        attendance_event = AttendanceEvent(
            user_id=current_user.id,
            event_type='break_start',
            timestamp=italian_now(),
            sede_id=get_current_user_sede(current_user).id if get_current_user_sede(current_user) else None
        )
        db.session.add(attendance_event)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Inizio pausa registrato alle {attendance_event.timestamp.strftime("%H:%M")}',
            'timestamp': attendance_event.timestamp.strftime('%H:%M')
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Errore nel salvare l\'inizio pausa'
        }), 500

@attendance_bp.route('/break_end', methods=['POST'])
@login_required
def break_end():
    if not current_user.can_access_attendance():
        return jsonify({
            'success': False,
            'message': 'Non hai i permessi per accedere alle presenze'
        }), 403

    try:
        # Verifica se l'utente può terminare la pausa
        if not AttendanceEvent.can_perform_action(current_user.id, 'break_end'):
            return jsonify({
                'success': False,
                'message': 'Non puoi terminare la pausa in questo momento.'
            })

        # Crea nuovo evento di fine pausa
        attendance_event = AttendanceEvent(
            user_id=current_user.id,
            event_type='break_end',
            timestamp=italian_now(),
            sede_id=get_current_user_sede(current_user).id if get_current_user_sede(current_user) else None
        )
        db.session.add(attendance_event)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Fine pausa registrata alle {attendance_event.timestamp.strftime("%H:%M")}',
            'timestamp': attendance_event.timestamp.strftime('%H:%M')
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Errore nel salvare la fine pausa'
        }), 500

# =============================================================================
# ATTENDANCE MAIN PAGE
# =============================================================================

@attendance_bp.route('/', methods=['GET', 'POST'])
@login_required
def attendance_main():
    # Controllo permessi di accesso alle presenze
    if not current_user.can_access_attendance():
        flash('Non hai i permessi per accedere alle presenze.', 'error')
        return redirect(url_for('dashboard.dashboard'))

    view_mode = request.args.get('view', 'personal')  # 'personal', 'team', 'sede'
    
    # Gestione vista
    if view_mode == 'team':
        if not current_user.can_view_attendance():
            flash('Non hai i permessi per visualizzare le presenze del team.', 'error')
            return redirect(url_for('attendance.attendance_main'))
    elif view_mode == 'sede':
        if not current_user.can_manage_attendance():
            flash('Non hai i permessi per visualizzare le presenze della sede.', 'error')
            return redirect(url_for('attendance.attendance_main'))

    # Data di riferimento (default: oggi)
    today = date.today()
    selected_date_str = request.args.get('date', today.strftime('%Y-%m-%d'))
    
    try:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except:
        selected_date = today
        selected_date_str = today.strftime('%Y-%m-%d')

    # Ottenimento dati presenze in base alla vista
    if view_mode == 'personal':
        users_data = [current_user]
        page_title = "Le Mie Presenze"
    elif view_mode == 'team':
        # Team users (same sede)
        current_sede = get_current_user_sede(current_user)
        if current_sede:
            users_data = User.query.filter(
                User.active == True,
                User.sedi.any(Sede.id == current_sede.id)
            ).all()
        else:
            users_data = [current_user]
        page_title = "Presenze Team"
    else:  # view_mode == 'sede'
        # All users in sede
        current_sede = get_current_user_sede(current_user)
        if current_sede:
            users_data = User.query.filter(
                User.active == True,
                User.sedi.any(Sede.id == current_sede.id)
            ).all()
        else:
            users_data = User.query.filter(User.active == True).all()
        page_title = "Presenze Sede"

    # Costruzione dati per ogni utente
    attendance_data = []
    for user in users_data:
        user_status, last_event = AttendanceEvent.get_user_status(user.id)
        events = AttendanceEvent.get_daily_events(user.id, selected_date)
        
        attendance_data.append({
            'user': user,
            'status': user_status,
            'last_event': last_event,
            'events': events,
            'work_hours': AttendanceEvent.get_daily_work_hours(user.id, selected_date),
            'break_time': AttendanceEvent.get_daily_break_time(user.id, selected_date)
        })

    return render_template('attendance.html',
                         attendance_data=attendance_data,
                         view_mode=view_mode,
                         selected_date=selected_date,
                         selected_date_str=selected_date_str,
                         page_title=page_title)

# =============================================================================
# ATTENDANCE EXPORT ROUTES
# =============================================================================

@attendance_bp.route('/export_excel')
@login_required  
def export_attendance_excel():
    """Export presenze in formato CSV"""
    if not current_user.can_view_attendance():
        flash('Non hai i permessi per esportare le presenze.', 'error')
        return redirect(url_for('attendance.attendance_main'))
    
    # Parametri per l'export
    start_date_str = request.args.get('start_date', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', date.today().strftime('%Y-%m-%d'))
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except:
        flash('Date non valide.', 'error')
        return redirect(url_for('attendance.attendance_main'))

    # Query per ottenere tutti gli eventi nel periodo
    events = AttendanceEvent.query.filter(
        AttendanceEvent.timestamp >= start_date,
        AttendanceEvent.timestamp <= end_date + timedelta(days=1)
    ).order_by(AttendanceEvent.timestamp).all()

    # Creazione file CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Data', 'Utente', 'Tipo Evento', 'Orario', 'Sede'])
    
    # Dati
    for event in events:
        writer.writerow([
            event.timestamp.strftime('%d/%m/%Y'),
            f"{event.user.first_name} {event.user.last_name}" if event.user else 'N/A',
            event.event_type,
            event.timestamp.strftime('%H:%M:%S'),
            event.sede.name if event.sede else 'N/A'
        ])

    # Preparazione response
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=presenze_{start_date_str}_{end_date_str}.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8"
    
    return response

# =============================================================================
# API ROUTES
# =============================================================================

@attendance_bp.route('/api/work_hours/<int:user_id>/<date_str>')
@login_required
def get_work_hours(user_id, date_str):
    """API endpoint per ottenere le ore lavorate aggiornate"""
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        work_hours = AttendanceEvent.get_daily_work_hours(user_id, target_date)
        return jsonify({'work_hours': round(work_hours, 1)})
    except Exception as e:
        return jsonify({'work_hours': 0})

# =============================================================================
# QUICK ATTENDANCE (QR) ROUTE
# =============================================================================

@attendance_bp.route('/quick/<action>', methods=['GET', 'POST'])
@require_login
def quick_attendance(action):
    """Gestisce la registrazione rapida di entrata/uscita tramite QR"""
    if action not in ['clock_in', 'clock_out', 'break_start', 'break_end']:
        flash('Azione non valida.', 'error')
        return redirect(url_for('attendance.attendance_main'))
    
    if not current_user.can_access_attendance():
        flash('Non hai i permessi per accedere alle presenze.', 'error')
        return redirect(url_for('dashboard.dashboard'))

    if request.method == 'POST':
        try:
            # Verifica se l'utente può effettuare l'azione
            if not AttendanceEvent.can_perform_action(current_user.id, action):
                status, last_event = AttendanceEvent.get_user_status(current_user.id)
                if action == 'clock_in' and status == 'in':
                    flash('Sei già presente. Devi prima registrare l\'uscita.', 'warning')
                elif action == 'clock_out' and status == 'out':
                    flash('Non sei ancora presente. Devi prima registrare l\'entrata.', 'warning')
                elif action == 'break_start' and status != 'in':
                    flash('Devi essere presente per iniziare una pausa.', 'warning')
                elif action == 'break_end' and status != 'break':
                    flash('Non sei in pausa.', 'warning')
                else:
                    flash('Non puoi effettuare questa azione al momento.', 'error')
                return redirect(url_for('attendance.attendance_main'))

            # Crea nuovo evento
            attendance_event = AttendanceEvent(
                user_id=current_user.id,
                event_type=action,
                timestamp=italian_now(),
                sede_id=get_current_user_sede(current_user).id if get_current_user_sede(current_user) else None
            )
            db.session.add(attendance_event)
            db.session.commit()
            
            # Messaggio di successo
            action_messages = {
                'clock_in': 'Entrata registrata',
                'clock_out': 'Uscita registrata', 
                'break_start': 'Inizio pausa registrato',
                'break_end': 'Fine pausa registrata'
            }
            
            flash(f'{action_messages[action]} alle {attendance_event.timestamp.strftime("%H:%M")}', 'success')
            return redirect(url_for('attendance.attendance_main'))

        except Exception as e:
            db.session.rollback()
            flash('Errore nel registrare l\'evento.', 'error')
            return redirect(url_for('attendance.attendance_main'))

    # GET request - mostra form di conferma
    action_titles = {
        'clock_in': 'Registra Entrata',
        'clock_out': 'Registra Uscita',
        'break_start': 'Inizia Pausa', 
        'break_end': 'Termina Pausa'
    }
    
    return render_template('quick_attendance.html',
                         action=action,
                         action_title=action_titles.get(action, 'Azione'),
                         current_time=italian_now())