"""
Attendance Routes
Employee attendance, breaks, and time tracking functionality
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import date, datetime, timedelta
from sqlalchemy.orm import joinedload

from app import db
from models import AttendanceEvent, User, Sede, italian_now
# Note: AttendanceFilterForm will be added when creating attendance-specific forms
from utils import format_hours, get_user_statistics

# Create blueprint
attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/attendance')
@login_required
def attendance():
    if not current_user.can_view_attendance():
        flash('Non hai i permessi per visualizzare le presenze', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    # Get filter parameters
    user_id = request.args.get('user_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Set default date range (last 30 days)
    if not start_date:
        start_date = (date.today() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = date.today().strftime('%Y-%m-%d')
    
    # Parse dates
    try:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        flash('Formato data non valido', 'danger')
        return redirect(url_for('attendance.attendance'))
    
    # Build query for attendance events
    query = AttendanceEvent.query.filter(
        AttendanceEvent.date >= start_date_obj,
        AttendanceEvent.date <= end_date_obj
    )
    
    # Apply user filter if specified and user has permissions
    if user_id:
        if current_user.can_view_all_attendance():
            query = query.filter(AttendanceEvent.user_id == user_id)
        elif user_id == current_user.id:
            query = query.filter(AttendanceEvent.user_id == current_user.id)
        else:
            flash('Non hai i permessi per visualizzare le presenze di altri utenti', 'danger')
            return redirect(url_for('attendance.attendance'))
    elif not current_user.can_view_all_attendance():
        # If user can't view all attendance, show only their own
        query = query.filter(AttendanceEvent.user_id == current_user.id)
    
    # Get attendance events with user data
    attendance_events = query.options(joinedload(AttendanceEvent.user)).order_by(
        AttendanceEvent.date.desc(),
        AttendanceEvent.timestamp.desc()
    ).all()
    
    # Get list of users for filter dropdown
    users = []
    if current_user.can_view_all_attendance():
        users = User.query.filter_by(active=True).order_by(User.first_name, User.last_name).all()
    
    # Calculate daily summaries
    daily_summaries = {}
    for event in attendance_events:
        date_key = event.date
        if date_key not in daily_summaries:
            daily_summaries[date_key] = {
                'user': event.user,
                'date': date_key,
                'events': [],
                'total_hours': 0,
                'status': 'Assente'
            }
        
        daily_summaries[date_key]['events'].append(event)
    
    # Calculate work hours for each day
    for date_key, summary in daily_summaries.items():
        work_hours = AttendanceEvent.get_daily_work_hours(summary['user'].id, date_key)
        summary['total_hours'] = work_hours
        
        # Determine status
        if work_hours > 0:
            user_status, _ = AttendanceEvent.get_user_status(summary['user'].id, date_key)
            summary['status'] = user_status if user_status != 'Assente' else 'Presente'
        else:
            summary['status'] = 'Assente'
    
    # Create basic form data for filters (will be improved later)
    form = None  # Placeholder until AttendanceFilterForm is created
    
    return render_template('attendance.html',
                         attendance_events=attendance_events,
                         daily_summaries=daily_summaries,
                         form=form,
                         start_date=start_date,
                         end_date=end_date,
                         selected_user_id=user_id)

@attendance_bp.route('/clock_in', methods=['POST'])
@login_required
def clock_in():
    if not current_user.can_manage_own_attendance():
        flash('Non hai i permessi per registrare presenze', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    # Check if user is already clocked in
    user_status, last_event = AttendanceEvent.get_user_status(current_user.id)
    
    if user_status in ['Presente', 'In pausa']:
        flash('Sei già presente. Effettua il clock-out prima di entrare nuovamente.', 'warning')
        return redirect(url_for('dashboard.dashboard'))
    
    # Create clock-in event
    event = AttendanceEvent(
        user_id=current_user.id,
        event_type='clock_in',
        timestamp=italian_now(),
        date=date.today()
    )
    
    try:
        db.session.add(event)
        db.session.commit()
        flash('Clock-in registrato con successo', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Errore durante la registrazione del clock-in', 'danger')
    
    return redirect(url_for('dashboard.dashboard'))

@attendance_bp.route('/clock_out', methods=['POST'])
@login_required
def clock_out():
    if not current_user.can_manage_own_attendance():
        flash('Non hai i permessi per registrare presenze', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    # Check if user is clocked in
    user_status, last_event = AttendanceEvent.get_user_status(current_user.id)
    
    if user_status == 'Assente':
        flash('Non sei presente. Effettua il clock-in prima di uscire.', 'warning')
        return redirect(url_for('dashboard.dashboard'))
    
    # If user is on break, end the break first
    if user_status == 'In pausa':
        end_break_event = AttendanceEvent(
            user_id=current_user.id,
            event_type='end_break',
            timestamp=italian_now(),
            date=date.today()
        )
        db.session.add(end_break_event)
    
    # Create clock-out event
    event = AttendanceEvent(
        user_id=current_user.id,
        event_type='clock_out',
        timestamp=italian_now(),
        date=date.today()
    )
    
    try:
        db.session.add(event)
        db.session.commit()
        flash('Clock-out registrato con successo', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Errore durante la registrazione del clock-out', 'danger')
    
    return redirect(url_for('dashboard.dashboard'))

@attendance_bp.route('/start_break', methods=['POST'])
@login_required
def start_break():
    if not current_user.can_manage_own_attendance():
        flash('Non hai i permessi per gestire le pause', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    # Check if user is present
    user_status, last_event = AttendanceEvent.get_user_status(current_user.id)
    
    if user_status != 'Presente':
        flash('Devi essere presente per iniziare una pausa', 'warning')
        return redirect(url_for('dashboard.dashboard'))
    
    # Create start break event
    event = AttendanceEvent(
        user_id=current_user.id,
        event_type='start_break',
        timestamp=italian_now(),
        date=date.today()
    )
    
    try:
        db.session.add(event)
        db.session.commit()
        flash('Pausa iniziata', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Errore durante l\'inizio della pausa', 'danger')
    
    return redirect(url_for('dashboard.dashboard'))

@attendance_bp.route('/end_break', methods=['POST'])
@login_required
def end_break():
    if not current_user.can_manage_own_attendance():
        flash('Non hai i permessi per gestire le pause', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    # Check if user is on break
    user_status, last_event = AttendanceEvent.get_user_status(current_user.id)
    
    if user_status != 'In pausa':
        flash('Non sei in pausa', 'warning')
        return redirect(url_for('dashboard.dashboard'))
    
    # Create end break event
    event = AttendanceEvent(
        user_id=current_user.id,
        event_type='end_break',
        timestamp=italian_now(),
        date=date.today()
    )
    
    try:
        db.session.add(event)
        db.session.commit()
        flash('Pausa terminata', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Errore durante la fine della pausa', 'danger')
    
    return redirect(url_for('dashboard.dashboard'))

@attendance_bp.route('/qr_attendance')
@login_required  
def qr_attendance():
    """Pagina per attendance tramite QR code"""
    if not current_user.can_manage_own_attendance():
        flash('Non hai i permessi per registrare presenze', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    # Get user status for display
    user_status, last_event = AttendanceEvent.get_user_status(current_user.id)
    work_hours_today = AttendanceEvent.get_daily_work_hours(current_user.id, date.today())
    
    return render_template('qr_attendance.html',
                         user_status=user_status,
                         last_event=last_event,
                         work_hours_today=work_hours_today)

@attendance_bp.route('/process_qr_action', methods=['POST'])
@login_required
def process_qr_action():
    """Processa azioni da QR code"""
    if not current_user.can_manage_own_attendance():
        return jsonify({'error': 'Non hai i permessi per registrare presenze'}), 403
    
    action = request.form.get('action')
    
    if action == 'clock_in':
        return redirect(url_for('attendance.clock_in'))
    elif action == 'clock_out':
        return redirect(url_for('attendance.clock_out'))
    elif action == 'start_break':
        return redirect(url_for('attendance.start_break'))
    elif action == 'end_break':
        return redirect(url_for('attendance.end_break'))
    else:
        flash('Azione non valida', 'danger')
        return redirect(url_for('attendance.qr_attendance'))

@attendance_bp.route('/attendance_summary/<int:user_id>')
@login_required
def attendance_summary(user_id):
    """Summary delle presenze per un utente specifico"""
    if not current_user.can_view_attendance():
        flash('Non hai i permessi per visualizzare le presenze', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    # Check permissions for viewing other users' attendance
    if user_id != current_user.id and not current_user.can_view_all_attendance():
        flash('Non hai i permessi per visualizzare le presenze di altri utenti', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    # Get date range (default last 30 days)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = date.today() - timedelta(days=30)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = date.today()
    
    # Get attendance statistics
    stats = get_user_statistics(user_id, start_date, end_date)
    
    # Get detailed daily records
    daily_records = []
    current_date = start_date
    while current_date <= end_date:
        work_hours = AttendanceEvent.get_daily_work_hours(user_id, current_date)
        user_status, _ = AttendanceEvent.get_user_status(user_id, current_date)
        
        daily_records.append({
            'date': current_date,
            'work_hours': work_hours,
            'status': user_status if work_hours > 0 else 'Assente',
            'formatted_hours': format_hours(work_hours)
        })
        current_date += timedelta(days=1)
    
    return render_template('attendance_summary.html',
                         user=user,
                         stats=stats,
                         daily_records=daily_records,
                         start_date=start_date,
                         end_date=end_date)