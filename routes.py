from flask import render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, date, timedelta
import qrcode
from io import BytesIO, StringIO
import base64
from defusedcsv import csv
from urllib.parse import urlparse, urljoin
from app import app, db, csrf
from sqlalchemy.orm import joinedload
from models import User, AttendanceEvent, LeaveRequest, Shift, ShiftTemplate, ReperibilitaShift, ReperibilitaTemplate, ReperibilitaIntervention, Intervention, Sede, WorkSchedule, UserRole, italian_now
from forms import LoginForm, UserForm, AttendanceForm, LeaveRequestForm, ShiftForm, ShiftTemplateForm, SedeForm, WorkScheduleForm, RoleForm
from utils import generate_shifts_for_period, get_user_statistics, get_team_statistics, format_hours, check_user_schedule_with_permissions

# Define require_login decorator
def require_login(f):
    """Decorator to require login for routes"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    
    return decorated_function

def is_safe_url(target):
    """Check if a URL is safe for redirect (same domain only)"""
    if not target:
        return False
    
    # Parse the target URL
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    
    # Check if the scheme and netloc match (same domain)
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.active and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if next_page and is_safe_url(next_page):
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        flash('Username o password non validi', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout effettuato con successo', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Management può visualizzare tutte le presenze di tutte le sedi
    if current_user.role == 'Management':
        return redirect(url_for('dashboard_team'))
    
    # Reindirizza l'utente Ente e PM alla home page con vista team per coerenza visiva
    if current_user.role in ['Ente', 'Project Manager']:
        return redirect(url_for('ente_home'))
    
    # Blocca l'accesso alla dashboard per altri utenti senza permessi
    if not current_user.can_access_dashboard():
        flash('Non hai i permessi per accedere alla dashboard.', 'danger')
        return redirect(url_for('shifts'))
    
    stats = get_user_statistics(current_user.id)
    
    if current_user.can_view_reports():
        team_stats = get_team_statistics()
    else:
        team_stats = None
    
    # Get today's attendance events
    today_events_check = AttendanceEvent.query.filter(
        AttendanceEvent.user_id == current_user.id,
        AttendanceEvent.date == date.today()
    ).first()
    today_attendance = today_events_check  # Per compatibilità con il template
    
    # Get daily status variables for the status section
    today_date = date.today()
    
    # Initialize variables for all users
    user_status = 'out'
    today_work_hours = 0
    today_events = []
    
    # Get current user's status and today's events (for regular users only, PM will be handled separately)
    if current_user.role not in ['Project Manager', 'Ente', 'Admin']:
        user_status, _ = AttendanceEvent.get_user_status(current_user.id, today_date)
        today_events = AttendanceEvent.get_daily_events(current_user.id, today_date)
        today_work_hours = AttendanceEvent.get_daily_work_hours(current_user.id, today_date)
    
    # Get upcoming shifts
    upcoming_shifts = Shift.query.filter(
        Shift.user_id == current_user.id,
        Shift.date >= date.today()
    ).order_by(Shift.date, Shift.start_time).limit(5).all()
    
    # Get upcoming reperibilità shifts for authorized users
    upcoming_reperibilita_shifts = []
    active_intervention = None
    recent_interventions = []
    current_time = italian_now().time()
    if current_user.role in ['Project Manager', 'Operatore', 'Redattore', 'Sviluppatore']:
        upcoming_reperibilita_shifts = ReperibilitaShift.query.filter(
            ReperibilitaShift.user_id == current_user.id,
            ReperibilitaShift.date >= date.today()
        ).order_by(ReperibilitaShift.date, ReperibilitaShift.start_time).limit(5).all()
        
        # Get active intervention for this user
        active_intervention = ReperibilitaIntervention.query.filter_by(
            user_id=current_user.id,
            end_datetime=None
        ).first()
        
        # Get recent interventions for timeline (last 7 days)
        seven_days_ago = italian_now() - timedelta(days=7)
        recent_interventions = ReperibilitaIntervention.query.filter(
            ReperibilitaIntervention.user_id == current_user.id,
            ReperibilitaIntervention.start_datetime >= seven_days_ago
        ).order_by(ReperibilitaIntervention.start_datetime.desc()).limit(10).all()
    
    # Get active general intervention for this user
    active_general_intervention = Intervention.query.filter_by(
        user_id=current_user.id,
        end_datetime=None
    ).first()
    
    # Get recent leave requests
    recent_leaves = LeaveRequest.query.filter_by(
        user_id=current_user.id
    ).order_by(LeaveRequest.created_at.desc()).limit(3).all()
    
    # Get weekly calendar data (Monday to Sunday)
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday
    weekdays = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
    
    weekly_calendar = []
    for i in range(7):
        day_date = week_start + timedelta(days=i)
        
        # Get shifts for this day (only show shifts, not attendance info)
        day_shifts = Shift.query.filter(
            Shift.user_id == current_user.id,
            Shift.date == day_date
        ).all()
        
        weekly_calendar.append({
            'date': day_date,
            'weekday': weekdays[i],
            'is_today': day_date == today,
            'shifts': day_shifts
        })
    
    # Get weekly team shifts and attendance data for PM role
    weekly_team_data = None
    shifts_by_day = {}
    attendance_by_date = {}
    week_dates = []
    
    if current_user.role == 'Project Manager':
        # Get all users except Ente users
        all_team_users = User.query.filter(
            User.active == True,
            User.role != 'Ente'
        ).all()
        
        # Get all shifts for the current week for all team members
        weekly_team_shifts = Shift.query.filter(
            Shift.date >= week_start,
            Shift.date < week_start + timedelta(days=7)
        ).order_by(Shift.date, Shift.start_time).all()
        
        # Group shifts by day for Ente-style view
        for i in range(7):
            day_date = week_start + timedelta(days=i)
            day_shifts = [s for s in weekly_team_shifts if s.date == day_date]
            shifts_by_day[day_date] = day_shifts
            
            # Initialize attendance dict for this day
            attendance_by_date[day_date] = {}
            
            # Add week date info
            week_dates.append({
                'date': day_date,
                'weekday': weekdays[i],
                'is_today': day_date == today
            })
        
        # Get attendance data for all team users for the week
        for user in all_team_users:
            for i in range(7):
                day_date = week_start + timedelta(days=i)
                
                # Get daily summary for this user and date
                try:
                    daily_summary = AttendanceEvent.get_daily_summary(user.id, day_date)
                    if daily_summary:
                        # Check for shifts on this date for this user
                        user_shifts = [s for s in weekly_team_shifts if s.user_id == user.id and s.date == day_date]
                        shift_status = 'normale'
                        
                        if user_shifts and daily_summary.clock_in:
                            shift = user_shifts[0]  # Take first shift if multiple
                            
                            from zoneinfo import ZoneInfo
                            italy_tz = ZoneInfo('Europe/Rome')
                            
                            # Create shift start time in Italian timezone
                            shift_start_datetime = datetime.combine(day_date, shift.start_time)
                            shift_start_datetime = shift_start_datetime.replace(tzinfo=italy_tz)
                            # Limiti più ragionevoli: anticipo oltre 30min, ritardo oltre 15min
                            early_limit = shift_start_datetime - timedelta(minutes=30)
                            late_limit = shift_start_datetime + timedelta(minutes=15)
                            
                            # Convert daily_summary.clock_in to Italian timezone if needed
                            clock_in_time = daily_summary.clock_in
                            if clock_in_time.tzinfo is None:
                                # Assume UTC and convert to Italian time
                                utc_tz = ZoneInfo('UTC')
                                clock_in_time = clock_in_time.replace(tzinfo=utc_tz).astimezone(italy_tz)
                            
                            if clock_in_time < early_limit:
                                shift_status = 'anticipo'
                            elif clock_in_time > late_limit:
                                shift_status = 'ritardo'
                            
                            # Calculate exit status if clock_out exists
                            exit_status = 'normale'
                            if daily_summary.clock_out:
                                shift_end_datetime = datetime.combine(day_date, shift.end_time)
                                shift_end_datetime = shift_end_datetime.replace(tzinfo=italy_tz)
                                # Exit limits: 5 minutes tolerance
                                exit_early_limit = shift_end_datetime - timedelta(minutes=5)
                                exit_late_limit = shift_end_datetime
                                
                                clock_out_time = daily_summary.clock_out
                                if clock_out_time.tzinfo is None:
                                    clock_out_time = clock_out_time.replace(tzinfo=utc_tz).astimezone(italy_tz)
                                
                                if clock_out_time < exit_early_limit:
                                    exit_status = 'anticipo'  # Early exit = yellow warning
                                elif clock_out_time > exit_late_limit:
                                    exit_status = 'ritardo'   # Late exit = blue thumbs up (overtime)
                        else:
                            exit_status = 'normale'
                        
                        attendance_by_date[day_date][user.id] = {
                            'user': user,
                            'clock_in': daily_summary.clock_in,
                            'clock_out': daily_summary.clock_out,
                            'status': 'Presente' if daily_summary.clock_in and not daily_summary.clock_out else 'Assente',
                            'work_hours': daily_summary.get_work_hours() if daily_summary.clock_in else 0,
                            'shift_status': shift_status,
                            'exit_status': exit_status if 'exit_status' in locals() else 'normale'
                        }
                except:
                    # Skip users with database issues
                    continue
    
    # Add personal attendance data for PM
    if current_user.role == 'Project Manager':
        # Get PM's personal attendance data (same as regular users)
        user_status = AttendanceEvent.get_user_status(current_user.id)
        today_events = AttendanceEvent.get_daily_events(current_user.id, today_date)
        today_work_hours = AttendanceEvent.get_daily_work_hours(current_user.id, today_date)


    return render_template('dashboard.html', 
                         stats=stats, 
                         team_stats=team_stats,
                         today_attendance=today_attendance,
                         upcoming_shifts=upcoming_shifts,
                         upcoming_reperibilita_shifts=upcoming_reperibilita_shifts,
                         active_intervention=active_intervention,
                         active_general_intervention=active_general_intervention,
                         recent_interventions=recent_interventions,
                         recent_leaves=recent_leaves,
                         weekly_calendar=weekly_calendar,
                         weekly_team_data=weekly_team_data,
                         shifts_by_day=shifts_by_day,
                         attendance_by_date=attendance_by_date,
                         week_dates=week_dates,
                         today=today,
                         today_date=today_date,
                         current_time=current_time,
                         user_status=user_status,
                         today_events=today_events,
                         today_work_hours=today_work_hours)

@app.route('/dashboard_team')
@login_required
def dashboard_team():
    """Dashboard per visualizzare le presenze di tutte le sedi - per Management"""
    if not current_user.can_view_all_attendance():
        flash('Non hai i permessi per visualizzare questo contenuto.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get all active users from all sedi
    all_users = User.query.filter(User.active == True).all()
    
    # Get all active sedi
    all_sedi = Sede.query.filter(Sede.active == True).all()
    
    # Get attendance data for today
    today = date.today()
    today_attendance = {}
    
    for user in all_users:
        status, last_event = AttendanceEvent.get_user_status(user.id, today)
        daily_summary = AttendanceEvent.get_daily_summary(user.id, today)
        
        # Check for approved leave requests
        leave_request = LeaveRequest.query.filter(
            LeaveRequest.user_id == user.id,
            LeaveRequest.status == 'Approved',
            LeaveRequest.start_date <= today,
            LeaveRequest.end_date >= today
        ).first()
        
        today_attendance[user.id] = {
            'user': user,
            'status': status,
            'last_event': last_event,
            'daily_summary': daily_summary,
            'leave_request': leave_request
        }
    
    return render_template('dashboard_team.html',
                         all_users=all_users,
                         all_sedi=all_sedi,
                         today_attendance=today_attendance,
                         today=today,
                         current_user=current_user)

@app.route('/ente-home')
@login_required
def ente_home():
    """Home page per utente Ente e PM con vista team e navigazione settimanale"""
    if current_user.role not in ['Ente', 'Project Manager']:
        flash('Accesso non autorizzato.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Usa l'orario italiano
    from zoneinfo import ZoneInfo
    italy_tz = ZoneInfo('Europe/Rome')
    today = datetime.now(italy_tz)
    
    # Get currently present users
    present_users = []
    
    # Get all active users (excluding Ente role but including current user if not Ente)
    try:
        users = User.query.filter(
            User.active == True,
            User.role != 'Ente'
        ).all()
        
        # Check who is currently present (simplified check)
        for user in users:
            try:
                # Get user's current status using today's date in Italian timezone
                today_date = today.date()
                status, last_event = AttendanceEvent.get_user_status(user.id, today_date)
                
                if status == 'in':
                    # Get all events for today to show complete timeline
                    today_events = db.session.query(AttendanceEvent).filter(
                        AttendanceEvent.user_id == user.id,
                        AttendanceEvent.date == today_date
                    ).order_by(AttendanceEvent.timestamp.asc()).all()
                    
                    # Find the last clock_in event (when they entered)
                    last_clock_in = None
                    for event in reversed(today_events):
                        if event.event_type == 'clock_in':
                            last_clock_in = event
                            break
                    
                    user.last_event = last_clock_in or last_event
                    user.today_events = today_events
                    present_users.append(user)
            except Exception as e:
                # Skip users with database issues but log the error
                app.logger.error(f"Error checking presence for user {user.id}: {e}")
                continue
    except:
        # Handle database errors gracefully
        present_users = []
    
    # Get week offset parameter (default to 0 for current week)
    week_offset = request.args.get('week_offset', 0, type=int)
    
    # Calculate week dates based on offset
    today_date = today.date()
    base_week_start = today_date - timedelta(days=today_date.weekday())
    week_start = base_week_start + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)
    
    # Get all shifts for the week
    weekly_shifts = Shift.query.filter(
        Shift.date >= week_start,
        Shift.date <= week_end
    ).order_by(Shift.date, Shift.start_time).all()
    
    # Get all reperibilità shifts for the week
    from models import ReperibilitaShift, ReperibilitaIntervention
    weekly_reperibilita = ReperibilitaShift.query.filter(
        ReperibilitaShift.date >= week_start,
        ReperibilitaShift.date <= week_end
    ).order_by(ReperibilitaShift.date, ReperibilitaShift.start_time).all()
    
    # Create a dictionary of reperibilità shifts by date
    reperibilita_by_date = {}
    for rep_shift in weekly_reperibilita:
        if rep_shift.date not in reperibilita_by_date:
            reperibilita_by_date[rep_shift.date] = []
        reperibilita_by_date[rep_shift.date].append(rep_shift)
    
    # Organize shifts by day and add leave request info
    shifts_by_day = {}
    for shift in weekly_shifts:
        if shift.date not in shifts_by_day:
            shifts_by_day[shift.date] = []
        
        # Check for overlapping leave requests
        overlapping_leave = LeaveRequest.query.filter(
            LeaveRequest.user_id == shift.user_id,
            LeaveRequest.start_date <= shift.date,
            LeaveRequest.end_date >= shift.date,
            LeaveRequest.status.in_(['Pending', 'Approved'])
        ).first()
        
        shift.has_leave_request = overlapping_leave is not None
        shift.leave_request = overlapping_leave
        
        shifts_by_day[shift.date].append(shift)
    
    # Get attendance data for the week
    attendance_by_date = {}
    all_users = User.query.filter(
        User.active == True,
        User.role != 'Ente'
    ).all()
    
    # Get all attendance events for the week
    events_by_date = {}
    all_events = AttendanceEvent.query.filter(
        AttendanceEvent.date >= week_start,
        AttendanceEvent.date <= week_end
    ).order_by(AttendanceEvent.date, AttendanceEvent.timestamp).all()
    
    for event in all_events:
        if event.date not in events_by_date:
            events_by_date[event.date] = {}
        if event.user_id not in events_by_date[event.date]:
            events_by_date[event.date][event.user_id] = []
        events_by_date[event.date][event.user_id].append(event)
    
    # Get all reperibilità interventions for the week
    interventions_by_date = {}
    week_start_datetime = italian_now().replace(year=week_start.year, month=week_start.month, day=week_start.day, hour=0, minute=0, second=0, microsecond=0)
    week_end_datetime = week_start_datetime + timedelta(days=7)
    
    all_interventions = ReperibilitaIntervention.query.filter(
        ReperibilitaIntervention.start_datetime >= week_start_datetime,
        ReperibilitaIntervention.start_datetime < week_end_datetime
    ).order_by(ReperibilitaIntervention.start_datetime.desc()).all()
    
    for intervention in all_interventions:
        intervention_date = intervention.start_datetime.date()
        if intervention_date not in interventions_by_date:
            interventions_by_date[intervention_date] = []
        interventions_by_date[intervention_date].append(intervention)
    
    for day_date in [week_start + timedelta(days=i) for i in range(7)]:
        attendance_by_date[day_date] = {}
        for user in all_users:
            # Get daily summary for this user and date
            try:
                daily_summary = AttendanceEvent.get_daily_summary(user.id, day_date)
                if daily_summary:
                    # Check for shifts on this date for this user
                    user_shifts = [s for s in weekly_shifts if s.user_id == user.id and s.date == day_date]
                    shift_status = 'normale'
                    
                    if user_shifts and daily_summary.clock_in:
                        shift = user_shifts[0]  # Take first shift if multiple
                        
                        from zoneinfo import ZoneInfo
                        italy_tz = ZoneInfo('Europe/Rome')
                        
                        # Create shift start time in Italian timezone
                        shift_start_datetime = datetime.combine(day_date, shift.start_time)
                        shift_start_datetime = shift_start_datetime.replace(tzinfo=italy_tz)
                        # Limiti più ragionevoli: anticipo oltre 30min, ritardo oltre 15min
                        early_limit = shift_start_datetime - timedelta(minutes=30)
                        late_limit = shift_start_datetime + timedelta(minutes=15)
                        
                        # Convert daily_summary.clock_in to Italian timezone if needed
                        clock_in_time = daily_summary.clock_in
                        if clock_in_time.tzinfo is None:
                            # Assume UTC and convert to Italian time
                            utc_tz = ZoneInfo('UTC')
                            clock_in_time = clock_in_time.replace(tzinfo=utc_tz).astimezone(italy_tz)
                        
                        if clock_in_time < early_limit:
                            shift_status = 'anticipo'
                        elif clock_in_time > late_limit:
                            shift_status = 'ritardo'
                    
                    attendance_by_date[day_date][user.id] = {
                        'user': user,
                        'clock_in': daily_summary.clock_in,
                        'clock_out': daily_summary.clock_out,
                        'status': 'Presente' if daily_summary.clock_in and not daily_summary.clock_out else 'Assente',
                        'work_hours': daily_summary.get_work_hours() if daily_summary.clock_in else 0,
                        'shift_status': shift_status
                    }
                else:
                    attendance_by_date[day_date][user.id] = {
                        'user': user,
                        'clock_in': None,
                        'clock_out': None,
                        'status': 'Assente',
                        'work_hours': 0
                    }
            except:
                attendance_by_date[day_date][user.id] = {
                    'user': user,
                    'clock_in': None,
                    'clock_out': None,
                    'status': 'Assente',
                    'work_hours': 0
                }
    
    # Add personal attendance data for PM (similar to dashboard logic)
    user_status = 'out'
    today_work_hours = 0
    today_events = []
    today_date = today.date()
    
    if current_user.role == 'Project Manager':
        user_status, last_event = AttendanceEvent.get_user_status(current_user.id)
        today_events = AttendanceEvent.get_daily_events(current_user.id, today_date)
        today_work_hours = AttendanceEvent.get_daily_work_hours(current_user.id, today_date)
    
    # Get shifts and intervention data for PM
    upcoming_reperibilita_shifts = []
    active_intervention = None
    recent_interventions = []
    
    if current_user.role == 'Project Manager':
        
        # Get upcoming reperibilità shifts for PM
        upcoming_reperibilita_shifts = ReperibilitaShift.query.filter(
            ReperibilitaShift.user_id == current_user.id,
            ReperibilitaShift.date >= today_date
        ).order_by(ReperibilitaShift.date, ReperibilitaShift.start_time).limit(5).all()
        
        # Get active intervention for PM
        active_intervention = ReperibilitaIntervention.query.filter_by(
            user_id=current_user.id,
            end_datetime=None
        ).first()
        
        # Get recent interventions for PM (last 7 days)
        seven_days_ago = italian_now() - timedelta(days=7)
        recent_interventions = ReperibilitaIntervention.query.filter(
            ReperibilitaIntervention.user_id == current_user.id,
            ReperibilitaIntervention.start_datetime >= seven_days_ago
        ).order_by(ReperibilitaIntervention.start_datetime.desc()).limit(10).all()
    
    # Create week dates info
    week_dates = []
    italian_weekdays = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
    
    for i in range(7):
        day_date = week_start + timedelta(days=i)
        week_dates.append({
            'date': day_date,
            'weekday': italian_weekdays[i],
            'is_today': day_date == today_date
        })
    
    return render_template('ente_home.html',
                         present_users=present_users,
                         today=today,
                         week_start=week_start,
                         week_end=week_end,
                         week_offset=week_offset,
                         shifts_by_day=shifts_by_day,
                         reperibilita_by_date=reperibilita_by_date,
                         week_dates=week_dates,
                         attendance_by_date=attendance_by_date,
                         events_by_date=events_by_date,
                         interventions_by_date=interventions_by_date,
                         user_status=user_status,
                         today_events=today_events,
                         today_work_hours=today_work_hours,
                         today_date=today_date,

                         upcoming_reperibilita_shifts=upcoming_reperibilita_shifts,
                         active_intervention=active_intervention,
                         recent_interventions=recent_interventions)

@app.route('/test_route', methods=['GET', 'POST'])
@login_required
def test_route():
    app.logger.error("TEST ROUTE CALLED!")
    flash('Test route funziona!', 'info')
    return redirect(url_for('attendance'))

@app.route('/api/work_hours/<int:user_id>/<date_str>')
@login_required
def get_work_hours(user_id, date_str):
    """API endpoint per ottenere le ore lavorate aggiornate"""
    from datetime import datetime
    from flask import jsonify
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        
        work_hours = AttendanceEvent.get_daily_work_hours(user_id, target_date)
        return jsonify({'work_hours': round(work_hours, 1)})
    except Exception as e:
        app.logger.error(f"Error in get_work_hours: {e}")
        return jsonify({'work_hours': 0})

@app.route('/check_shift_before_clock_in', methods=['POST'])
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

@app.route('/clock_in', methods=['POST'])
@login_required  
def clock_in():
    if not current_user.can_access_attendance():
        flash('Non hai i permessi per registrare presenze.', 'danger')
        return redirect(url_for('shifts'))
        
    app.logger.error(f"CLOCK_IN: User {current_user.id} attempting clock-in")
    
    # Verifica se può fare clock-in
    if not AttendanceEvent.can_perform_action(current_user.id, 'clock_in'):
        status, _ = AttendanceEvent.get_user_status(current_user.id)
        if status == 'in':
            flash('Sei già presente. Devi prima registrare l\'uscita.', 'warning')
        elif status == 'break':
            flash('Sei in pausa. Devi prima terminare la pausa.', 'warning')
        # Redirect PM to ente_home, altri utenti alla dashboard
        if current_user.role == 'Project Manager':
            return redirect(url_for('ente_home'))
        else:
            return redirect(url_for('dashboard'))
    
    # Verifica se ha già registrato una presenza completa (entrata+uscita) oggi
    from zoneinfo import ZoneInfo
    italy_tz = ZoneInfo('Europe/Rome')
    today = datetime.now(italy_tz).date()
    
    existing_events = AttendanceEvent.query.filter(
        AttendanceEvent.user_id == current_user.id,
        AttendanceEvent.date == today
    ).all()
    
    # Conta entrate e uscite complete
    clock_ins = [e for e in existing_events if e.event_type == 'clock_in']
    clock_outs = [e for e in existing_events if e.event_type == 'clock_out']
    
    # Blocca se ha già una presenza completa (entrata+uscita) oggi
    if len(clock_ins) > 0 and len(clock_outs) > 0 and len(clock_ins) == len(clock_outs):
        flash('Hai già registrato una presenza completa oggi. Non puoi registrare più entrate/uscite nella stessa giornata.', 'warning')
        if current_user.role == 'Project Manager':
            return redirect(url_for('ente_home'))
        else:
            return redirect(url_for('dashboard'))
    
    # Usa l'orario italiano invece di UTC
    from zoneinfo import ZoneInfo
    italy_tz = ZoneInfo('Europe/Rome')
    now = datetime.now(italy_tz)
    
    # Crea nuovo evento di entrata
    event = AttendanceEvent()
    event.user_id = current_user.id
    event.date = now.date()  # Usa la data italiana
    event.event_type = 'clock_in'
    event.timestamp = now
    
    # Controlla gli orari della sede e permessi per determinare lo stato
    try:
        schedule_check = check_user_schedule_with_permissions(current_user.id, now)
        if schedule_check['has_schedule']:
            event.shift_status = schedule_check['entry_status']
        else:
            event.shift_status = 'normale'
    except Exception as e:
        app.logger.error(f"Error checking schedule for entry: {e}")
        event.shift_status = 'normale'
    
    try:
        db.session.add(event)
        db.session.commit()
        app.logger.error(f"CLOCK_IN: Event created successfully at {now}")
        flash('Entrata registrata alle {}'.format(now.strftime('%H:%M')), 'success')
    except Exception as e:
        app.logger.error(f"CLOCK_IN: Database commit failed: {e}")
        db.session.rollback()
        flash('Errore nel salvare l\'entrata', 'danger')
    
    # Redirect PM to ente_home, altri utenti alla dashboard
    if current_user.role == 'Project Manager':
        return redirect(url_for('ente_home'))
    else:
        return redirect(url_for('dashboard'))

@app.route('/check_shift_before_clock_out', methods=['POST'])
@login_required  
def check_shift_before_clock_out():
    """Check if user can clock-out (no shift validation)"""
    # Check if can perform clock-out action
    if not AttendanceEvent.can_perform_action(current_user.id, 'clock_out'):
        status, last_event = AttendanceEvent.get_user_status(current_user.id)
        if status == 'out':
            return jsonify({
                'success': False,
                'message': 'Non sei presente. Devi prima registrare l\'entrata.',
                'already_clocked': True
            })
    
    # No shift validation - always allow clock-out
    return jsonify({
        'success': True,
        'needs_confirmation': False
    })

@app.route('/clock_out', methods=['POST'])
@login_required
def clock_out():
    if not current_user.can_access_attendance():
        flash('Non hai i permessi per registrare presenze.', 'danger')
        return redirect(url_for('shifts'))
        
    # Verifica se può fare clock-out
    if not AttendanceEvent.can_perform_action(current_user.id, 'clock_out'):
        status, _ = AttendanceEvent.get_user_status(current_user.id)
        if status == 'out':
            flash('Non sei presente. Devi prima registrare l\'entrata.', 'warning')
        # Redirect PM to ente_home, altri utenti alla dashboard
        if current_user.role == 'Project Manager':
            return redirect(url_for('ente_home'))
        else:
            return redirect(url_for('dashboard'))
    
    # Verifica se ha già registrato una presenza completa (entrata+uscita) oggi
    from zoneinfo import ZoneInfo
    italy_tz = ZoneInfo('Europe/Rome')
    today = datetime.now(italy_tz).date()
    
    existing_events = AttendanceEvent.query.filter(
        AttendanceEvent.user_id == current_user.id,
        AttendanceEvent.date == today
    ).all()
    
    # Conta entrate e uscite complete
    clock_ins = [e for e in existing_events if e.event_type == 'clock_in']
    clock_outs = [e for e in existing_events if e.event_type == 'clock_out']
    
    # Blocca se ha già una presenza completa (entrata+uscita) oggi
    if len(clock_ins) > 0 and len(clock_outs) > 0 and len(clock_ins) == len(clock_outs):
        flash('Hai già registrato una presenza completa oggi. Non puoi registrare più entrate/uscite nella stessa giornata.', 'warning')
        if current_user.role == 'Project Manager':
            return redirect(url_for('ente_home'))
        else:
            return redirect(url_for('dashboard'))
    
    # Usa l'orario italiano invece di UTC
    from zoneinfo import ZoneInfo
    italy_tz = ZoneInfo('Europe/Rome')
    now = datetime.now(italy_tz)
    
    # Crea nuovo evento di uscita
    event = AttendanceEvent()
    event.user_id = current_user.id
    event.date = now.date()  # Usa la data italiana
    event.event_type = 'clock_out'
    event.timestamp = now
    
    # Controlla gli orari della sede e permessi per determinare lo stato
    try:
        schedule_check = check_user_schedule_with_permissions(current_user.id, now)
        if schedule_check['has_schedule']:
            event.shift_status = schedule_check['exit_status']
        else:
            event.shift_status = 'normale'
    except Exception as e:
        app.logger.error(f"Error checking schedule for exit: {e}")
        event.shift_status = 'normale'
    
    try:
        db.session.add(event)
        db.session.commit()
        flash('Uscita registrata alle {}'.format(now.strftime('%H:%M')), 'success')
    except Exception as e:
        db.session.rollback()
        flash('Errore nel salvare l\'uscita', 'danger')
    
    # Redirect PM to ente_home, altri utenti alla dashboard
    if current_user.role == 'Project Manager':
        return redirect(url_for('ente_home'))
    else:
        return redirect(url_for('dashboard'))

@app.route('/break_start', methods=['POST'])
@login_required
def break_start():
    if not current_user.can_access_attendance():
        flash('Non hai i permessi per registrare presenze.', 'danger')
        return redirect(url_for('shifts'))
        
    # Verifica se può iniziare la pausa
    if not AttendanceEvent.can_perform_action(current_user.id, 'break_start'):
        status, _ = AttendanceEvent.get_user_status(current_user.id)
        if status == 'out':
            flash('Non sei presente. Devi prima registrare l\'entrata.', 'warning')
        elif status == 'break':
            flash('Sei già in pausa.', 'warning')
        # Redirect PM to ente_home, altri utenti alla dashboard
        if current_user.role == 'Project Manager':
            return redirect(url_for('ente_home'))
        else:
            return redirect(url_for('dashboard'))
    
    # Usa l'orario italiano invece di UTC
    from zoneinfo import ZoneInfo
    italy_tz = ZoneInfo('Europe/Rome')
    now = datetime.now(italy_tz)
    
    # Crea nuovo evento di inizio pausa
    event = AttendanceEvent()
    event.user_id = current_user.id
    event.date = now.date()  # Usa la data italiana
    event.event_type = 'break_start'
    event.timestamp = now
    
    try:
        db.session.add(event)
        db.session.commit()
        flash('Pausa iniziata alle {}'.format(now.strftime('%H:%M')), 'info')
    except Exception as e:
        db.session.rollback()
        flash('Errore nel salvare l\'inizio pausa', 'danger')
    
    # Redirect PM to ente_home, altri utenti alla dashboard
    if current_user.role == 'Project Manager':
        return redirect(url_for('ente_home'))
    else:
        return redirect(url_for('dashboard'))

@app.route('/break_end', methods=['POST'])
@login_required
def break_end():
    if not current_user.can_access_attendance():
        flash('Non hai i permessi per registrare presenze.', 'danger')
        return redirect(url_for('shifts'))
        
    # Verifica se può terminare la pausa
    if not AttendanceEvent.can_perform_action(current_user.id, 'break_end'):
        status, _ = AttendanceEvent.get_user_status(current_user.id)
        if status == 'out':
            flash('Non sei presente.', 'warning')
        elif status == 'in':
            flash('Non sei in pausa.', 'warning')
        # Redirect PM to ente_home, altri utenti alla dashboard
        if current_user.role == 'Project Manager':
            return redirect(url_for('ente_home'))
        else:
            return redirect(url_for('dashboard'))
    
    # Usa l'orario italiano invece di UTC
    from zoneinfo import ZoneInfo
    italy_tz = ZoneInfo('Europe/Rome')
    now = datetime.now(italy_tz)
    
    # Crea nuovo evento di fine pausa
    event = AttendanceEvent()
    event.user_id = current_user.id
    event.date = now.date()  # Usa la data italiana
    event.event_type = 'break_end'
    event.timestamp = now
    
    try:
        db.session.add(event)
        db.session.commit()
        flash('Pausa terminata alle {}'.format(now.strftime('%H:%M')), 'info')
    except Exception as e:
        db.session.rollback()
        flash('Errore nel salvare la fine pausa', 'danger')
    
    # Redirect PM to ente_home, altri utenti alla dashboard
    if current_user.role == 'Project Manager':
        return redirect(url_for('ente_home'))
    else:
        return redirect(url_for('dashboard'))

@app.route('/attendance', methods=['GET', 'POST'])
@login_required
def attendance():
    # Utente Ente può solo visualizzare dati team, non gestire presenze personali
    if not current_user.can_access_attendance() and current_user.role != 'Ente':
        flash('Non hai i permessi per accedere alla gestione presenze.', 'danger')
        return redirect(url_for('shifts'))
    
    form = AttendanceForm()
    
    # Ottieni stato attuale dell'utente e eventi di oggi (solo se non è Ente)
    if current_user.role != 'Ente':
        user_status, last_event = AttendanceEvent.get_user_status(current_user.id)
        today_events = AttendanceEvent.get_daily_events(current_user.id)
        today_work_hours = AttendanceEvent.get_daily_work_hours(current_user.id)
    else:
        # Ente non ha dati personali
        user_status, last_event = 'out', None
        today_events = []
        today_work_hours = 0
    
    # Blocca POST per utente Ente (solo visualizzazione)
    if request.method == 'POST' and form.validate_on_submit() and current_user.role != 'Ente':
        # Salva note nell'ultimo evento di oggi o crea un nuovo evento note
        if form.notes.data:
            if today_events and last_event:
                # Aggiorna note dell'ultimo evento
                last_event.notes = form.notes.data
                db.session.commit()
                flash('Note salvate', 'success')
            else:
                # Crea evento note se non ci sono eventi oggi
                from zoneinfo import ZoneInfo
                italy_tz = ZoneInfo('Europe/Rome')
                now = datetime.now(italy_tz)
                
                note_event = AttendanceEvent(
                    user_id=current_user.id,
                    date=now.date(),
                    event_type='clock_in',  # Evento fittizio per salvare le note
                    timestamp=now,
                    notes=form.notes.data
                )
                db.session.add(note_event)
                db.session.commit()
                flash('Note salvate', 'success')
        return redirect(url_for('attendance'))
    
    # Handle team/personal view toggle for PM, Management and Ente
    view_mode = request.args.get('view', 'personal')
    if current_user.role in ['Project Manager', 'Management']:
        # PM and Management can toggle between personal and team view
        show_team_data = (view_mode == 'team')
    elif current_user.role == 'Ente':
        # Ente vede sempre e solo dati team
        show_team_data = True
        view_mode = 'team'
    else:
        # Non-PM/Management/Ente users see only personal data
        show_team_data = False
        view_mode = 'personal'
    
    # Handle date filtering
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Default to last 30 days if no dates provided
    if not start_date_str or not end_date_str:
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
    else:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            # Fallback to default if invalid dates
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
    
    if show_team_data:
        # Get team attendance data for PM, Management and Ente
        if current_user.role == 'Management':
            # Management vede tutti gli utenti di tutte le sedi
            team_users = User.query.filter(User.active.is_(True)).all()
        else:
            # PM e Ente vedono solo utenti operativi
            team_users = User.query.filter(
                User.role.in_(['Redattore', 'Sviluppatore', 'Operatore', 'Project Manager']),
                User.active.is_(True)
            ).all()
        
        old_records = []
        event_records = []
        user_shifts = []
        
        for user in team_users:
            # Get event records for this user
            user_event_records = AttendanceEvent.get_events_as_records(user.id, start_date, end_date)
            event_records.extend(user_event_records)
            
            # Get shifts for this user
            user_user_shifts = Shift.query.filter(
                Shift.user_id == user.id,
                Shift.date >= start_date,
                Shift.date <= end_date
            ).all()
            user_shifts.extend(user_user_shifts)
    else:
        # Ottieni tutti gli eventi come record individuali
        event_records = AttendanceEvent.get_events_as_records(current_user.id, start_date, end_date)
        old_records = []  # Non più necessario
        
        # Get user shifts for shift comparison
        user_shifts = Shift.query.filter(
            Shift.user_id == current_user.id,
            Shift.date >= start_date,
            Shift.date <= end_date
        ).all()
    
    # Create a shift lookup by date and user
    if show_team_data:
        # Per i dati team, crea lookup per utente+data
        shifts_by_user_date = {}
        for shift in user_shifts:
            key = (shift.user_id, shift.date)
            shifts_by_user_date[key] = shift
    else:
        # Per i dati personali, usa la lookup per data
        shifts_by_date = {shift.date: shift for shift in user_shifts}
    
    # Add shift status to event records (both entry and exit indicators)
    for record in event_records:
        # Trova il turno corrispondente
        shift = None
        if show_team_data:
            # Per dati team, cerca per utente+data
            key = (record.user_id, record.date)
            shift = shifts_by_user_date.get(key)
        else:
            # Per dati personali, cerca per data
            shift = shifts_by_date.get(record.date)
        
        # Inizializza indicatori
        record.shift_status = 'normale'
        record.exit_status = 'normale'
        
        if shift:
            from zoneinfo import ZoneInfo
            italy_tz = ZoneInfo('Europe/Rome')
            utc_tz = ZoneInfo('UTC')
            
            # Calcola indicatori di ENTRATA
            if hasattr(record, 'clock_in') and record.clock_in:
                # Crea l'orario di inizio turno in timezone italiana
                shift_start_datetime = datetime.combine(record.date, shift.start_time)
                shift_start_datetime = shift_start_datetime.replace(tzinfo=italy_tz)
                # Limiti più ragionevoli: anticipo oltre 30min, ritardo oltre 15min
                early_limit = shift_start_datetime - timedelta(minutes=30)
                late_limit = shift_start_datetime + timedelta(minutes=15)
                
                # Converti il timestamp di clock_in da UTC a orario italiano
                clock_in_time = record.clock_in
                if clock_in_time.tzinfo is None:
                    clock_in_time = clock_in_time.replace(tzinfo=utc_tz)
                
                # Converte a orario italiano per il confronto
                clock_in_time_italy = clock_in_time.astimezone(italy_tz)
                
                if clock_in_time_italy < early_limit:
                    record.shift_status = 'anticipo'
                elif clock_in_time_italy > late_limit:
                    record.shift_status = 'ritardo'
                else:
                    record.shift_status = 'normale'
            
            # Calcola indicatori di USCITA
            if hasattr(record, 'clock_out') and record.clock_out:
                # Crea l'orario di fine turno in timezone italiana
                shift_end_datetime = datetime.combine(record.date, shift.end_time)
                shift_end_datetime = shift_end_datetime.replace(tzinfo=italy_tz)
                # Tolleranza uscita: 5 minuti prima per anticipata, 10 minuti dopo per straordinario
                early_exit_limit = shift_end_datetime - timedelta(minutes=5)
                late_exit_limit = shift_end_datetime + timedelta(minutes=10)
                
                # Converti il timestamp di clock_out da UTC a orario italiano
                clock_out_time = record.clock_out
                if clock_out_time.tzinfo is None:
                    clock_out_time = clock_out_time.replace(tzinfo=utc_tz)
                
                # Converte a orario italiano per il confronto
                clock_out_time_italy = clock_out_time.astimezone(italy_tz)
                
                if clock_out_time_italy < early_exit_limit:
                    record.exit_status = 'anticipo'  # Uscita anticipata
                elif clock_out_time_italy > late_exit_limit:
                    record.exit_status = 'straordinario'  # Straordinario (oltre 10 min)
                else:
                    record.exit_status = 'normale'
    
    # Non ci sono più turni da controllare - rimosso controllo assenze basato su turni
    
    # Aggiungi record per le giornate con ferie/permessi/malattie approvate
    leave_records = []
    
    # Determina l'utente per cui cercare le richieste di ferie
    target_user_id = current_user.id if not show_team_data else None
    
    if target_user_id:
        # Cerca richieste di ferie approvate nel periodo
        approved_leaves = LeaveRequest.query.filter(
            LeaveRequest.user_id == target_user_id,
            LeaveRequest.status == 'Approved',
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date
        ).all()
        
        for leave in approved_leaves:
            current_date = max(leave.start_date, start_date)
            while current_date <= min(leave.end_date, end_date):
                # Verifica se esiste già un record di presenza per questa data
                existing_record = any(r.date == current_date for r in event_records + old_records)
                
                if not existing_record:
                    # Crea un record per la giornata di ferie/permesso/malattia
                    class LeaveRecord:
                        def __init__(self, date, leave_type, reason, user_id):
                            self.date = date
                            self.clock_in = None
                            self.clock_out = None
                            self.break_start = None
                            self.break_end = None
                            self.notes = f"{leave_type}: {reason}" if reason else leave_type
                            self.user_id = user_id
                            self.user = User.query.get(user_id)
                            self.shift_status = leave_type.lower()  # 'ferie', 'permesso', 'malattia'
                            self.exit_status = 'normale'
                            self.leave_type = leave_type
                            self.leave_reason = reason
                        
                        def get_work_hours(self):
                            return 0  # Nessuna ora lavorata durante ferie/permessi
                        
                        def get_attendance_indicators(self):
                            return {'entry': None, 'exit': None}
                    
                    leave_records.append(LeaveRecord(
                        date=current_date,
                        leave_type=leave.leave_type,
                        reason=leave.reason,
                        user_id=target_user_id
                    ))
                
                current_date += timedelta(days=1)
    
    # Combina tutti i record
    records = []
    records.extend(event_records)
    records.extend(old_records)
    records.extend(leave_records)
    
    # Riordina per data e timestamp decrescente
    def sort_key(record):
        if hasattr(record, 'timestamp') and record.timestamp:
            return (record.date, record.timestamp)
        elif hasattr(record, 'created_at') and record.created_at:
            return (record.date, record.created_at)
        else:
            return (record.date, datetime.min)
    
    records.sort(key=sort_key, reverse=True)
    
    return render_template('attendance.html', 
                         form=form, 
                         records=records,
                         today_date=date.today(),
                         start_date=start_date.strftime('%Y-%m-%d'),
                         end_date=end_date.strftime('%Y-%m-%d'),
                         user_status=user_status,
                         today_events=today_events,
                         today_work_hours=today_work_hours,
                         view_mode=view_mode,
                         show_team_data=show_team_data)

@app.route('/shifts')
@login_required
def shifts():
    if current_user.can_manage_shifts():
        # Managers see template management interface
        shift_form = ShiftForm()
        template_form = ShiftTemplateForm()
        
        # Populate user choices for shift form
        workers = User.query.filter(
            User.role.in_(['Redattore', 'Sviluppatore', 'Operatore']),
            User.active.is_(True)
        ).all()
        shift_form.user_id.choices = [(u.id, u.get_full_name()) for u in workers]
        
        # Get existing shift templates
        shift_templates = ShiftTemplate.query.order_by(ShiftTemplate.created_at.desc()).all()
        
        return render_template('shifts.html', 
                             shift_form=shift_form,
                             template_form=template_form,
                             shift_templates=shift_templates,
                             can_manage=True,
                             selected_template=None,
                             shifts=None)
    else:
        # Parametri di visualizzazione per utenti normali
        if current_user.role in ['Admin', 'Project Manager']:
            view_mode = request.args.get('view', 'all')
        elif current_user.role == 'Ente':
            view_mode = 'all'  # Ente vede sempre tutti
        else:
            view_mode = 'personal'  # Utenti normali vedono solo i propri
        
        if view_mode == 'personal':
            # Show only personal shifts
            shifts = Shift.query.filter(Shift.user_id == current_user.id).order_by(
                Shift.date.desc(), Shift.start_time
            ).all()
            
            # Check for leave requests that overlap with each shift
            for shift in shifts:
                leave_request = LeaveRequest.query.filter(
                    LeaveRequest.user_id == shift.user_id,
                    LeaveRequest.start_date <= shift.date,
                    LeaveRequest.end_date >= shift.date,
                    LeaveRequest.status.in_(['Pending', 'Approved'])
                ).first()
                
                shift.has_leave_request = leave_request is not None
                shift.leave_request = leave_request
            
            total_hours = sum(shift.get_duration_hours() for shift in shifts)
            future_shifts = len([s for s in shifts if s.date >= date.today()])
            unique_users = 1
            
            # Helper per giorni della settimana in italiano
            def get_italian_weekday(date_obj):
                giorni = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
                return giorni[date_obj.weekday()]
            
            return render_template('shifts.html',
                                 shifts=shifts,
                                 today=date.today(),
                                 total_hours=round(total_hours, 1),
                                 future_shifts=future_shifts,
                                 unique_users=unique_users,
                                 can_manage=False,
                                 view_mode=view_mode,
                                 selected_template=None,
                                 shift_templates=[],
                                 get_italian_weekday=get_italian_weekday)
        else:
            # Show all templates in read-only mode (solo per Ente)
            shift_templates = ShiftTemplate.query.order_by(ShiftTemplate.created_at.desc()).all()
            
            # Helper per giorni della settimana in italiano
            def get_italian_weekday(date_obj):
                giorni = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
                return giorni[date_obj.weekday()]
            
            return render_template('shifts.html', 
                                 shift_templates=shift_templates,
                                 today=date.today(),
                                 can_manage=False,
                                 view_mode=view_mode,
                                 selected_template=None,
                                 shifts=None,
                                 get_italian_weekday=get_italian_weekday)

@app.route('/create_shift', methods=['POST'])
@login_required
def create_shift():
    if not current_user.can_manage_shifts():
        flash('Non hai i permessi per creare turni', 'danger')
        return redirect(url_for('shifts'))
    
    form = ShiftForm()
    workers = User.query.filter(
        User.role.in_(['Redattore', 'Sviluppatore', 'Operatore']),
        User.active.is_(True)
    ).all()
    form.user_id.choices = [(u.id, u.get_full_name()) for u in workers]
    
    if form.validate_on_submit():
        # Check for conflicts - more detailed validation
        existing_shifts = Shift.query.filter(
            Shift.user_id == form.user_id.data,
            Shift.date == form.date.data
        ).all()
        
        if existing_shifts:
            # Check for overlaps or consecutive shifts
            new_start = form.start_time.data
            new_end = form.end_time.data
            
            has_overlap = False
            for existing in existing_shifts:
                # Check overlap or consecutive shifts (no gap)
                if not (new_end < existing.start_time or new_start > existing.end_time):
                    has_overlap = True
                    break
            
            if has_overlap:
                flash('⚠️ ATTENZIONE: Questo turno si sovrappone o è consecutivo ad un turno esistente. I doppi turni sono sconsigliati salvo casi eccezionali.', 'warning')
                # Don't create the shift - require explicit confirmation
                return redirect(url_for('shifts'))
            else:
                # Multiple non-overlapping shifts on same day - allow with warning
                flash('⚠️ NOTA: L\'utente avrà multipli turni non consecutivi in questa data.', 'info')
        
        # Create the shift
        shift = Shift()
        shift.user_id = form.user_id.data
        shift.date = form.date.data
        shift.start_time = form.start_time.data
        shift.end_time = form.end_time.data
        shift.shift_type = form.shift_type.data
        shift.created_by = current_user.id
        db.session.add(shift)
        db.session.commit()
        flash('Turno creato con successo', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'danger')
    
    return redirect(url_for('shifts'))

@app.route('/generate_shifts', methods=['POST'])
@login_required
def generate_shifts():
    if not current_user.can_manage_shifts():
        flash('Non hai i permessi per generare turni', 'danger')
        return redirect(url_for('shifts'))
    
    form = ShiftTemplateForm()
    if form.validate_on_submit():
        # Create template record first
        template = ShiftTemplate()
        template.name = form.name.data
        template.start_date = form.start_date.data
        template.end_date = form.end_date.data
        template.description = form.description.data
        template.created_by = current_user.id
        db.session.add(template)
        db.session.commit()
        
        success, message = generate_shifts_for_period(
            form.start_date.data,
            form.end_date.data,
            current_user.id
        )
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'danger')
    
    return redirect(url_for('shifts'))

@app.route('/regenerate_template/<int:template_id>', methods=['POST'])
@login_required
def regenerate_template(template_id):
    if not current_user.can_manage_shifts():
        flash('Non hai i permessi per rigenerare turni', 'danger')
        return redirect(url_for('shifts'))
    
    template = ShiftTemplate.query.get_or_404(template_id)
    
    # Delete only FUTURE shifts for this period (preserve past shifts)
    from datetime import date
    today = date.today()
    future_start_date = max(template.start_date, today)
    
    shifts_deleted = Shift.query.filter(
        Shift.date >= future_start_date,
        Shift.date <= template.end_date
    ).delete()
    db.session.commit()
    
    # Update template creation timestamp to reflect regeneration
    from models import italian_now
    template.created_at = italian_now()
    template.created_by = current_user.id  # Update creator to current user
    db.session.commit()
    
    # Regenerate shifts
    success, message = generate_shifts_for_period(
        template.start_date,
        template.end_date,
        current_user.id
    )
    
    if success:
        preserved_msg = f" (preservati {(today - template.start_date).days} giorni già lavorati)" if today > template.start_date else ""
        flash(f'Template "{template.name}" rigenerato con successo{preserved_msg}. {message}', 'success')
    else:
        flash(f'Errore nella rigenerazione: {message}', 'danger')
    
    return redirect(url_for('shifts'))

@app.route('/delete_template/<int:template_id>', methods=['POST'])
@login_required
def delete_template(template_id):
    if not current_user.can_manage_shifts():
        flash('Non hai i permessi per eliminare template', 'danger')
        return redirect(url_for('shifts'))
    
    template = ShiftTemplate.query.get_or_404(template_id)
    
    # Delete associated shifts
    shifts_deleted = Shift.query.filter(
        Shift.date >= template.start_date,
        Shift.date <= template.end_date
    ).delete()
    
    # Delete template
    db.session.delete(template)
    db.session.commit()
    
    flash(f'Template "{template.name}" eliminato insieme a {shifts_deleted} turni associati', 'success')
    return redirect(url_for('shifts'))

@app.route('/view_template/<int:template_id>')
@login_required
def view_template(template_id):
    # All users can view templates, but only managers can manage them
    can_manage = current_user.can_manage_shifts()
    
    template = ShiftTemplate.query.get_or_404(template_id)
    
    # Get view mode from URL parameter
    view_mode = request.args.get('view', 'all')
    
    # Get shifts for this template period
    shifts_query = Shift.query.join(User, Shift.user_id == User.id).filter(
        Shift.date >= template.start_date,
        Shift.date <= template.end_date
    )
    
    # Apply view filter
    if view_mode == 'personal':
        shifts = shifts_query.filter(Shift.user_id == current_user.id).order_by(Shift.date.desc(), Shift.start_time).all()
    else:
        shifts = shifts_query.order_by(Shift.date.desc(), Shift.start_time).all()
    
    # Check for leave requests that overlap with each shift
    for shift in shifts:
        # Look for pending or approved leave requests that overlap with the shift date
        leave_request = LeaveRequest.query.filter(
            LeaveRequest.user_id == shift.user_id,
            LeaveRequest.start_date <= shift.date,
            LeaveRequest.end_date >= shift.date,
            LeaveRequest.status.in_(['Pending', 'Approved'])
        ).first()
        
        # Add leave request info to shift object
        shift.has_leave_request = leave_request is not None
        shift.leave_request = leave_request
    
    # Calculate statistics
    total_hours = sum(shift.get_duration_hours() for shift in shifts)
    future_shifts = len([s for s in shifts if s.date >= date.today()])
    unique_users = len(set(shift.user_id for shift in shifts))
    
    # Calculate hours per user
    user_hours = {}
    for shift in shifts:
        if shift.user_id not in user_hours:
            user_hours[shift.user_id] = {
                'user': shift.user,
                'total_hours': 0,
                'shift_count': 0,
                'shifts': []
            }
        hours = shift.get_duration_hours()
        user_hours[shift.user_id]['total_hours'] += hours
        user_hours[shift.user_id]['shift_count'] += 1
        user_hours[shift.user_id]['shifts'].append(shift)
    
    # Sort by total hours descending
    user_hours_list = sorted(user_hours.values(), key=lambda x: x['total_hours'], reverse=True)
    
    # Get forms only for managers
    if can_manage:
        shift_form = ShiftForm()
        template_form = ShiftTemplateForm()
        
        # Populate user choices for shift form
        workers = User.query.filter(
            User.role.in_(['Redattore', 'Sviluppatore', 'Operatore']),
            User.active.is_(True)
        ).all()
        shift_form.user_id.choices = [(u.id, u.get_full_name()) for u in workers]
        
        # Get all templates
        shift_templates = ShiftTemplate.query.order_by(ShiftTemplate.created_at.desc()).all()
    else:
        shift_form = None
        template_form = None
        shift_templates = []
    
    # Helper per giorni della settimana in italiano
    def get_italian_weekday(date_obj):
        giorni = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
        return giorni[date_obj.weekday()]
    
    return render_template('shifts.html', 
                         shifts=shifts, 
                         shift_form=shift_form,
                         template_form=template_form,
                         shift_templates=shift_templates,
                         selected_template=template,
                         today=date.today(),
                         total_hours=round(total_hours, 1),
                         future_shifts=future_shifts,
                         unique_users=unique_users,
                         user_hours_list=user_hours_list,
                         get_italian_weekday=get_italian_weekday,
                         can_manage=can_manage,
                         view_mode=view_mode)

@app.route('/leave_requests')
@login_required
def leave_requests():
    form = LeaveRequestForm()
    
    if current_user.can_approve_leave():
        # Project managers see all requests
        requests = LeaveRequest.query.join(User, LeaveRequest.user_id == User.id).order_by(
            LeaveRequest.created_at.desc()
        ).all()
        can_approve = True
    else:
        # Users see only their requests
        requests = LeaveRequest.query.filter_by(
            user_id=current_user.id
        ).order_by(LeaveRequest.created_at.desc()).all()
        can_approve = False
    
    return render_template('leave_requests.html', 
                         requests=requests, 
                         form=form,
                         can_approve=can_approve,
                         today=date.today())

@app.route('/create_leave_request', methods=['POST'])
@login_required
def create_leave_request():
    if not current_user.can_request_leave():
        flash('Non hai i permessi per richiedere ferie/permessi', 'danger')
        return redirect(url_for('leave_requests'))
    
    form = LeaveRequestForm()
    if form.validate_on_submit():
        # Per permessi, imposta automaticamente end_date = start_date
        end_date = form.start_date.data if form.leave_type.data == 'Permesso' else form.end_date.data
        
        # Check for overlapping requests
        overlapping = LeaveRequest.query.filter(
            LeaveRequest.user_id == current_user.id,
            LeaveRequest.status.in_(['Pending', 'Approved']),
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= form.start_date.data
        ).first()
        
        if overlapping:
            flash('Hai già una richiesta sovrapposta in questo periodo', 'warning')
        else:
            leave_request = LeaveRequest(
                user_id=current_user.id,
                start_date=form.start_date.data,
                end_date=end_date,
                leave_type=form.leave_type.data,
                reason=form.reason.data
            )
            
            # Auto-approve sick leave, set others as pending
            if form.leave_type.data == 'Malattia':
                leave_request.status = 'Approved'
                leave_request.approved_by = current_user.id  # Self-approved
                leave_request.approved_at = datetime.now()
            else:
                leave_request.status = 'Pending'
            
            # Aggiungi orari per i permessi
            if form.leave_type.data == 'Permesso':
                leave_request.start_time = form.start_time.data
                leave_request.end_time = form.end_time.data
            
            db.session.add(leave_request)
            db.session.commit()
            
            # Messaggio di successo personalizzato
            if form.leave_type.data == 'Malattia':
                flash('Richiesta di malattia approvata automaticamente', 'success')
            elif form.leave_type.data == 'Permesso':
                duration = leave_request.get_duration_display()
                flash(f'Richiesta di permesso inviata con successo ({duration})', 'success')
            else:
                flash('Richiesta inviata con successo', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'danger')
    
    return redirect(url_for('leave_requests'))

@app.route('/approve_leave/<int:request_id>')
@login_required
def approve_leave(request_id):
    if not current_user.can_approve_leave():
        flash('Non hai i permessi per approvare richieste', 'danger')
        return redirect(url_for('leave_requests'))
    
    leave_request = LeaveRequest.query.get_or_404(request_id)
    leave_request.status = 'Approved'
    leave_request.approved_by = current_user.id
    leave_request.approved_at = datetime.utcnow()
    
    db.session.commit()
    flash('Richiesta approvata', 'success')
    return redirect(url_for('leave_requests'))

@app.route('/reject_leave/<int:request_id>')
@login_required
def reject_leave(request_id):
    if not current_user.can_approve_leave():
        flash('Non hai i permessi per rifiutare richieste', 'danger')
        return redirect(url_for('leave_requests'))
    
    leave_request = LeaveRequest.query.get_or_404(request_id)
    leave_request.status = 'Rejected'
    leave_request.approved_by = current_user.id
    leave_request.approved_at = datetime.utcnow()
    
    db.session.commit()
    flash('Richiesta rifiutata', 'warning')
    return redirect(url_for('leave_requests'))

@app.route('/delete_leave/<int:request_id>')
@login_required
def delete_leave(request_id):
    leave_request = LeaveRequest.query.get_or_404(request_id)
    
    # Verifica che sia l'utente proprietario della richiesta
    if leave_request.user_id != current_user.id:
        flash('Non puoi cancellare richieste di altri utenti', 'danger')
        return redirect(url_for('leave_requests'))
    
    # Verifica che la richiesta non sia già approvata
    if leave_request.status == 'Approved':
        flash('Non puoi cancellare richieste già approvate', 'warning')
        return redirect(url_for('leave_requests'))
    
    # Cancella la richiesta
    db.session.delete(leave_request)
    db.session.commit()
    flash('Richiesta cancellata con successo', 'success')
    return redirect(url_for('leave_requests'))

@app.route('/users')
@login_required
def users():
    if not current_user.can_manage_users():
        flash('Non hai i permessi per gestire gli utenti', 'danger')
        return redirect(url_for('dashboard'))
    
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False)
    return render_template('users.html', users=users)

@app.route('/new_user', methods=['GET', 'POST'])
@login_required
def new_user():
    if not current_user.can_manage_users():
        flash('Non hai i permessi per creare utenti', 'danger')
        return redirect(url_for('dashboard'))
    
    form = UserForm(is_edit=False)
    if form.validate_on_submit():
        # Crea il nuovo utente
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data),
            role=form.role.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            sede_id=form.sede.data,
            part_time_percentage=form.get_part_time_percentage_as_float(),
            active=form.is_active.data
        )
        db.session.add(user)
        db.session.flush()  # Per ottenere l'ID dell'utente
        
        # Non c'è più gestione sedi multiple
        
        db.session.commit()
        flash('Utente creato con successo', 'success')
        return redirect(url_for('users'))
    
    return render_template('users.html', form=form, editing=False)

@app.route('/user_management')
@login_required
def user_management():
    if not current_user.can_manage_users():
        flash('Non hai i permessi per gestire gli utenti', 'danger')
        return redirect(url_for('dashboard'))
    
    users = User.query.options(joinedload(User.sede_obj)).order_by(User.created_at.desc()).all()
    form = UserForm(is_edit=False)
    return render_template('user_management.html', users=users, form=form)



@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if not current_user.can_manage_users():
        flash('Non hai i permessi per modificare gli utenti', 'danger')
        return redirect(url_for('user_management'))
    
    user = User.query.get_or_404(user_id)
    form = UserForm(original_username=user.username, is_edit=True, obj=user)
    
    if request.method == 'GET':
        # Popola il campo sede con la sede attualmente associata all'utente
        if user.sede_id:
            form.sede.data = user.sede_id
    
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.role = form.role.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.sede_id = form.sede.data
        user.part_time_percentage = form.get_part_time_percentage_as_float()
        user.active = form.is_active.data
        
        # Update password only if provided
        if form.password.data:
            user.password_hash = generate_password_hash(form.password.data)
        
        # Non c'è più gestione sedi multiple
        
        db.session.commit()
        flash(f'Utente {user.username} modificato con successo', 'success')
        return redirect(url_for('user_management'))
    else:
        # Populate the percentage field manually only on GET request
        form.part_time_percentage.data = str(user.part_time_percentage)
    
    return render_template('edit_user.html', form=form, user=user)

@app.route('/toggle_user/<int:user_id>')
@login_required
def toggle_user(user_id):
    if not current_user.can_manage_users():
        flash('Non hai i permessi per modificare utenti', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Non puoi disattivare il tuo account', 'warning')
        return redirect(url_for('user_management'))
    
    user.active = not user.active
    db.session.commit()
    
    status = 'attivato' if user.active else 'disattivato'
    flash(f'Utente {status} con successo', 'success')
    return redirect(url_for('user_management'))

@app.route('/reports')
@login_required
def reports():
    if not current_user.can_view_reports():
        flash('Non hai i permessi per visualizzare i report', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get date range from request
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
    
    # Get team statistics with error handling
    try:
        team_stats = get_team_statistics(start_date, end_date)
    except Exception as e:
        app.logger.error(f"Error loading team statistics: {e}")
        team_stats = {
            'active_users': 0,
            'total_hours': 0,
            'shifts_this_period': 0,
            'avg_hours_per_user': 0
        }
    
    # Get user statistics for all active users (excluding Admin and Ente)
    users = User.query.filter_by(active=True).filter(~User.role.in_(['Admin', 'Ente'])).all()
    app.logger.error(f"REPORTS: Found {len(users)} active users (excluding Admin and Ente)")
    
    user_stats = []
    chart_data = []  # Separate data for charts without User objects
    
    for user in users:
        try:
            stats = get_user_statistics(user.id, start_date, end_date)
            stats['user'] = user
            user_stats.append(stats)
            
            # Create chart-safe data
            chart_data.append({
                'user_id': user.id,
                'username': user.username,
                'full_name': user.get_full_name(),
                'role': user.role,
                'total_hours_worked': stats['total_hours_worked'],
                'days_worked': stats['days_worked'],
                'shifts_assigned': stats['shifts_assigned'],
                'shift_hours': stats['shift_hours'],
                'approved_leaves': stats['approved_leaves'],
                'pending_leaves': stats['pending_leaves']
            })
            
            app.logger.error(f"REPORTS: User {user.username} stats: {stats}")
        except Exception as e:
            app.logger.error(f"Error getting stats for user {user.username}: {e}")
            # Continue without this user's stats
            continue
    
    app.logger.error(f"REPORTS: Total user_stats: {len(user_stats)}")
    
    # Get interventions data for the table (entrambi i tipi)
    from models import Intervention, ReperibilitaIntervention
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    try:
        # Interventi generici
        interventions = Intervention.query.filter(
            Intervention.start_datetime >= start_datetime,
            Intervention.start_datetime <= end_datetime
        ).order_by(Intervention.start_datetime.desc()).all()
        
        # Interventi reperibilità  
        reperibilita_interventions = ReperibilitaIntervention.query.filter(
            ReperibilitaIntervention.start_datetime >= start_datetime,
            ReperibilitaIntervention.start_datetime <= end_datetime
        ).order_by(ReperibilitaIntervention.start_datetime.desc()).all()
    except Exception as e:
        app.logger.error(f"Errore nel caricamento interventi: {e}")
        interventions = []
        reperibilita_interventions = []
    
    # Get attendance data for charts - calculate real data
    attendance_data = []
    current_date = start_date
    active_user_ids = [user.id for user in User.query.filter(User.active.is_(True)).filter(~User.role.in_(['Admin', 'Ente'])).all()]
    
    while current_date <= end_date:
        # Calculate total hours and workers for this day
        daily_total_hours = 0
        workers_present = 0
        
        for user_id in active_user_ids:
            try:
                daily_hours = AttendanceEvent.get_daily_work_hours(user_id, current_date)
                if daily_hours and daily_hours > 0:
                    daily_total_hours += float(daily_hours)
                    workers_present += 1
            except Exception as e:
                app.logger.error(f"Error calculating daily hours for chart user {user_id} date {current_date}: {e}")
                # Continue to next user instead of stopping
                continue
        
        attendance_data.append({
            'date': current_date.strftime('%d/%m'),  # Format for display
            'hours': round(daily_total_hours, 1),
            'workers': workers_present
        })
        current_date += timedelta(days=1)
    
    return render_template('reports.html', 
                         team_stats=team_stats,
                         user_stats=user_stats,
                         chart_data=chart_data,
                         attendance_data=attendance_data,
                         interventions=interventions,
                         reperibilita_interventions=reperibilita_interventions,
                         start_date=start_date,
                         end_date=end_date)

@app.route('/holidays')
@login_required
def holidays():
    """Gestione festività (solo Admin)"""
    if current_user.role != 'Admin':
        flash('Solo gli amministratori possono gestire le festività', 'danger')
        return redirect(url_for('dashboard'))
    
    from models import Holiday
    holidays = Holiday.query.order_by(Holiday.month, Holiday.day).all()
    return render_template('holidays.html', holidays=holidays)

@app.route('/holidays/add', methods=['GET', 'POST'])
@login_required
def add_holiday():
    """Aggiunta nuova festività"""
    if current_user.role != 'Admin':
        flash('Solo gli amministratori possono gestire le festività', 'danger')
        return redirect(url_for('dashboard'))
    
    from forms import HolidayForm
    from models import Holiday
    
    form = HolidayForm()
    
    if form.validate_on_submit():
        # Gestisci il campo sede_id correttamente
        sede_id = form.sede_id.data if form.sede_id.data != '' else None
        
        # Controlla se esiste già una festività nello stesso giorno e stesso ambito
        existing = Holiday.query.filter_by(
            month=form.month.data,
            day=form.day.data,
            sede_id=sede_id,
            is_active=True
        ).first()
        
        if existing:
            scope = existing.scope_display
            flash(f'Esiste già una festività attiva il {form.day.data}/{form.month.data} per {scope}: {existing.name}', 'warning')
        else:
            holiday = Holiday(
                name=form.name.data,
                month=form.month.data,
                day=form.day.data,
                sede_id=sede_id,
                description=form.description.data,
                is_active=form.is_active.data,
                created_by=current_user.id
            )
            
            db.session.add(holiday)
            db.session.commit()
            
            scope = holiday.scope_display
            flash(f'Festività "{holiday.name}" aggiunta con successo per {scope}', 'success')
            return redirect(url_for('holidays'))
    
    return render_template('add_holiday.html', form=form)

@app.route('/holidays/edit/<int:holiday_id>', methods=['GET', 'POST'])
@login_required
def edit_holiday(holiday_id):
    """Modifica festività esistente"""
    if current_user.role != 'Admin':
        flash('Solo gli amministratori possono gestire le festività', 'danger')
        return redirect(url_for('dashboard'))
    
    from forms import HolidayForm
    from models import Holiday
    
    holiday = Holiday.query.get_or_404(holiday_id)
    form = HolidayForm(obj=holiday)
    
    # Precompila il campo sede_id correttamente
    if request.method == 'GET':
        form.sede_id.data = holiday.sede_id
    
    if form.validate_on_submit():
        # Gestisci il campo sede_id correttamente
        sede_id = form.sede_id.data if form.sede_id.data != '' else None
        
        # Controlla se esiste già un'altra festività nello stesso giorno e stesso ambito
        existing = Holiday.query.filter(
            Holiday.month == form.month.data,
            Holiday.day == form.day.data,
            Holiday.sede_id == sede_id,
            Holiday.is_active == True,
            Holiday.id != holiday_id
        ).first()
        
        if existing:
            scope = existing.scope_display
            flash(f'Esiste già una festività attiva il {form.day.data}/{form.month.data} per {scope}: {existing.name}', 'warning')
        else:
            holiday.name = form.name.data
            holiday.month = form.month.data
            holiday.day = form.day.data
            holiday.sede_id = sede_id
            holiday.description = form.description.data
            holiday.is_active = form.is_active.data
            
            db.session.commit()
            
            scope = holiday.scope_display
            flash(f'Festività "{holiday.name}" modificata con successo per {scope}', 'success')
            return redirect(url_for('holidays'))
    
    return render_template('edit_holiday.html', form=form, holiday=holiday)

@app.route('/holidays/delete/<int:holiday_id>')
@login_required
def delete_holiday(holiday_id):
    """Elimina festività"""
    if current_user.role != 'Admin':
        flash('Solo gli amministratori possono gestire le festività', 'danger')
        return redirect(url_for('dashboard'))
    
    from models import Holiday
    
    holiday = Holiday.query.get_or_404(holiday_id)
    holiday_name = holiday.name
    
    db.session.delete(holiday)
    db.session.commit()
    
    flash(f'Festività "{holiday_name}" eliminata con successo', 'success')
    return redirect(url_for('holidays'))

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Cambio password utente"""
    from forms import ChangePasswordForm
    from werkzeug.security import check_password_hash, generate_password_hash
    
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        # Verifica password attuale
        if not check_password_hash(current_user.password_hash, form.current_password.data):
            flash('Password attuale non corretta', 'danger')
            return render_template('change_password.html', form=form)
        
        # Aggiorna password
        current_user.password_hash = generate_password_hash(form.new_password.data)
        db.session.commit()
        
        flash('Password cambiata con successo', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('change_password.html', form=form)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """Richiesta reset password"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    from forms import ForgotPasswordForm
    from models import User, PasswordResetToken
    import secrets
    from datetime import timedelta
    
    form = ForgotPasswordForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            # Invalida token precedenti
            old_tokens = PasswordResetToken.query.filter_by(user_id=user.id, used=False).all()
            for token in old_tokens:
                token.used = True
            
            # Crea nuovo token - salva in UTC per evitare problemi timezone
            from datetime import datetime
            reset_token = PasswordResetToken(
                user_id=user.id,
                token=secrets.token_urlsafe(32),
                expires_at=datetime.utcnow() + timedelta(hours=1)  # Salva in UTC
            )
            
            db.session.add(reset_token)
            db.session.commit()
            
            # In una versione completa, qui invieresti l'email
            # Per ora mostriamo il link direttamente
            reset_url = url_for('reset_password', token=reset_token.token, _external=True)
            flash(f'Link per il reset della password: {reset_url}', 'info')
        else:
            # Per sicurezza, non rivelare se l'email esiste o meno
            flash('Se l\'email esiste nel sistema, riceverai un link per il reset della password', 'info')
        
        return redirect(url_for('login'))
    
    return render_template('forgot_password.html', form=form)

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password con token"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    from forms import ResetPasswordForm
    from models import PasswordResetToken
    from werkzeug.security import generate_password_hash
    
    # Trova il token
    reset_token = PasswordResetToken.query.filter_by(token=token).first()
    

    if not reset_token or not reset_token.is_valid:
        flash('Token non valido o scaduto', 'danger')
        return redirect(url_for('forgot_password'))
    
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        # Aggiorna password
        reset_token.user.password_hash = generate_password_hash(form.new_password.data)
        
        # Marca token come usato
        reset_token.used = True
        
        db.session.commit()
        
        flash('Password reimpostata con successo. Puoi ora accedere con la nuova password', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html', form=form, token=token)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.route('/edit_shift/<int:shift_id>', methods=['GET', 'POST'])
@login_required
def edit_shift(shift_id):
    if not current_user.can_manage_shifts():
        flash('Non hai i permessi per modificare turni', 'danger')
        return redirect(url_for('shifts'))
    
    shift = Shift.query.get_or_404(shift_id)
    
    # Check if shift is in the future or today
    if shift.date < date.today():
        flash('Non è possibile modificare turni passati', 'warning')
        return redirect(url_for('shifts'))
    
    from forms import EditShiftForm
    form = EditShiftForm()
    
    # Get available users for assignment
    users = User.query.filter(
        User.role.in_(['Project Manager', 'Redattore', 'Sviluppatore', 'Operatore']),
        User.active.is_(True)
    ).order_by(User.first_name, User.last_name).all()
    
    # Popola le scelte del form con gli utenti disponibili
    form.user_id.choices = [(user.id, f"{user.get_full_name()} - {user.role}") for user in users]
    
    if form.validate_on_submit():
        try:
            # Verifica sovrapposizioni con il nuovo orario e utente
            overlapping_shift = Shift.query.filter(
                Shift.user_id == form.user_id.data,
                Shift.date == shift.date,
                Shift.id != shift.id,
                # Controlla sovrapposizione oraria
                db.or_(
                    db.and_(Shift.start_time <= form.start_time.data, Shift.end_time > form.start_time.data),
                    db.and_(Shift.start_time < form.end_time.data, Shift.end_time >= form.end_time.data),
                    db.and_(Shift.start_time >= form.start_time.data, Shift.end_time <= form.end_time.data)
                )
            ).first()
            
            if overlapping_shift:
                flash(f'Sovrapposizione rilevata: l\'utente selezionato ha già un turno dalle {overlapping_shift.start_time.strftime("%H:%M")} alle {overlapping_shift.end_time.strftime("%H:%M")}', 'warning')
            else:
                # Salva i valori originali per il messaggio
                old_user = shift.user.get_full_name()
                old_time = f"{shift.start_time.strftime('%H:%M')} - {shift.end_time.strftime('%H:%M')}"
                old_type = shift.shift_type
                
                # Aggiorna il turno
                shift.user_id = form.user_id.data
                shift.start_time = form.start_time.data
                shift.end_time = form.end_time.data
                shift.shift_type = form.shift_type.data
                
                db.session.commit()
                
                new_user = User.query.get(form.user_id.data)
                new_time = f"{form.start_time.data.strftime('%H:%M')} - {form.end_time.data.strftime('%H:%M')}"
                
                flash(f'Turno modificato con successo: {old_user} ({old_time}, {old_type}) → {new_user.get_full_name()} ({new_time}, {form.shift_type.data})', 'success')
                
                # Redirect back to team shifts page 
                return redirect(url_for('team_shifts'))
                
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la modifica del turno: {str(e)}', 'danger')
    
    # Pre-popola il form con i dati esistenti
    if request.method == 'GET':
        form.user_id.data = shift.user_id
        form.start_time.data = shift.start_time
        form.end_time.data = shift.end_time
        form.shift_type.data = shift.shift_type
    
    return render_template('edit_shift.html', shift=shift, users=users, form=form)



def calculate_shift_presence(shift):
    """Calcola lo stato di presenza per un turno specifico"""
    from datetime import datetime, timedelta
    
    # Combina data e orari del turno per creare datetime completi
    shift_start = datetime.combine(shift.date, shift.start_time)
    shift_end = datetime.combine(shift.date, shift.end_time)
    
    # Prendi tutti gli eventi di presenza dell'utente per quella data
    events = AttendanceEvent.query.filter(
        AttendanceEvent.user_id == shift.user_id,
        AttendanceEvent.date == shift.date
    ).order_by(AttendanceEvent.timestamp).all()
    
    if not events:
        return {
            'status': 'absent',
            'color': 'danger',
            'actual_start': None,
            'actual_end': None,
            'message': 'Assente'
        }
    
    # Trova l'entrata e l'uscita più vicine al turno
    actual_start = None
    actual_end = None
    
    # Trova la prima entrata del giorno
    for event in events:
        if event.event_type == 'clock_in':
            actual_start = event.timestamp
            break
    
    # Trova l'ultima uscita del giorno
    for event in reversed(events):
        if event.event_type == 'clock_out':
            actual_end = event.timestamp
            break
    
    # Definisci tolleranze 
    tolerance_late = timedelta(minutes=14)   # 14 min dopo per ritardo di entrata
    tolerance_early_exit = timedelta(minutes=14)  # 14 min prima per uscita anticipata
    
    # Valuta lo stato di presenza
    if actual_start is None:
        return {
            'status': 'absent',
            'color': 'danger',
            'actual_start': None,
            'actual_end': actual_end,
            'message': 'Non entrato'
        }
    
    # Controlla se è in orario, in ritardo o in anticipo
    status = 'present'
    color = 'success'
    message = 'Presente'
    
    # Controlla entrata
    if actual_start > shift_start + tolerance_late:
        status = 'late'
        color = 'warning'
        message = 'Entrata in ritardo'
    
    # Controlla uscita se presente
    if actual_end and actual_end < shift_end - tolerance_early_exit:
        status = 'early_exit'
        color = 'warning'
        message = 'Uscita anticipata'
    elif actual_end is None and shift.date < date.today():
        # Turno passato senza uscita registrata
        status = 'no_exit'
        color = 'warning'
        message = 'Senza uscita'
    
    return {
        'status': status,
        'color': color,
        'actual_start': actual_start,
        'actual_end': actual_end,
        'message': message
    }

@app.route('/team-shifts')
@login_required
def team_shifts():
    # Solo PM può vedere i turni del team
    if current_user.role not in ['Project Manager']:
        flash('Non hai i permessi per accedere a questa funzionalità.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Gestisci navigazione settimanale
    date_param = request.args.get('date')
    if date_param:
        try:
            target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
        except:
            target_date = date.today()
    else:
        target_date = date.today()
    
    # Calcola l'inizio e la fine della settimana
    week_start = target_date - timedelta(days=target_date.weekday())
    week_end = week_start + timedelta(days=6)
    
    # Calcola settimana precedente e successiva per navigazione
    prev_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)
    
    # Prendi tutti i turni della settimana
    weekly_shifts = Shift.query.filter(
        Shift.date >= week_start,
        Shift.date <= week_end
    ).order_by(Shift.date, Shift.start_time).all()
    
    # Prendi tutti i turni di reperibilità della settimana
    from models import ReperibilitaShift
    weekly_reperibilita = ReperibilitaShift.query.filter(
        ReperibilitaShift.date >= week_start,
        ReperibilitaShift.date <= week_end
    ).order_by(ReperibilitaShift.date, ReperibilitaShift.start_time).all()
    
    # Crea un dizionario dei turni di reperibilità per data
    reperibilita_by_date = {}
    for rep_shift in weekly_reperibilita:
        if rep_shift.date not in reperibilita_by_date:
            reperibilita_by_date[rep_shift.date] = []
        reperibilita_by_date[rep_shift.date].append(rep_shift)
    
    # Raggruppa i turni per giorno e aggiungi informazioni di presenza
    shifts_by_day = {}
    for shift in weekly_shifts:
        if shift.date not in shifts_by_day:
            shifts_by_day[shift.date] = []
        
        # Calcola lo stato di presenza per questo turno
        presence_info = calculate_shift_presence(shift)
        shift.presence_info = presence_info
        
        # Check for leave requests that overlap with each shift
        leave_request = LeaveRequest.query.filter(
            LeaveRequest.user_id == shift.user_id,
            LeaveRequest.start_date <= shift.date,
            LeaveRequest.end_date >= shift.date,
            LeaveRequest.status.in_(['Pending', 'Approved'])
        ).first()
        
        shift.has_leave_request = leave_request is not None
        shift.leave_request = leave_request
        
        shifts_by_day[shift.date].append(shift)
    
    # Prendi tutti gli utenti per il dropdown di filtro
    users = User.query.filter_by(active=True).order_by(User.first_name, User.last_name).all()
    
    # Crea una lista delle date della settimana con nomi dei giorni
    today = date.today()
    weekdays = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
    week_dates = []
    for i in range(7):
        day_date = week_start + timedelta(days=i)
        week_dates.append({
            'date': day_date,
            'weekday': weekdays[i],
            'is_today': day_date == today
        })
    
    return render_template('team_shifts.html', 
                         shifts_by_day=shifts_by_day,
                         reperibilita_by_date=reperibilita_by_date,
                         week_start=week_start,
                         week_end=week_end,
                         prev_week=prev_week,
                         next_week=next_week,
                         target_date=target_date,
                         users=users,
                         today=today,
                         week_dates=week_dates)



@app.route('/team-shifts/change-user/<int:shift_id>', methods=['POST'])
@login_required
@csrf.exempt
def change_shift_user(shift_id):
    """Cambia l'utente assegnato a un turno (solo PM)"""
    if current_user.role not in ['Project Manager']:
        return jsonify({'success': False, 'message': 'Non hai i permessi per modificare i turni.'})
    
    try:
        new_user_id = request.json.get('user_id')
        if not new_user_id:
            return jsonify({'success': False, 'message': 'ID utente mancante.'})
        
        shift = Shift.query.get_or_404(shift_id)
        old_user = shift.user
        new_user = User.query.get_or_404(new_user_id)
        
        # Verifica che il nuovo utente sia attivo
        if not new_user.active:
            return jsonify({'success': False, 'message': 'L\'utente selezionato non è attivo.'})
        
        # Verifica sovrapposizioni per il nuovo utente
        overlapping_shift = Shift.query.filter(
            Shift.user_id == new_user_id,
            Shift.date == shift.date,
            Shift.id != shift_id,
            # Controlla sovrapposizione oraria
            db.or_(
                db.and_(Shift.start_time <= shift.start_time, Shift.end_time > shift.start_time),
                db.and_(Shift.start_time < shift.end_time, Shift.end_time >= shift.end_time),
                db.and_(Shift.start_time >= shift.start_time, Shift.end_time <= shift.end_time)
            )
        ).first()
        
        if overlapping_shift:
            return jsonify({
                'success': False, 
                'message': f'{new_user.get_full_name()} ha già un turno sovrapposto dalle {overlapping_shift.start_time.strftime("%H:%M")} alle {overlapping_shift.end_time.strftime("%H:%M")}.'
            })
        
        # Aggiorna il turno
        shift.user_id = new_user_id
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Turno trasferito da {old_user.get_full_name()} a {new_user.get_full_name()}.',
            'new_user_name': new_user.get_full_name(),
            'new_user_role': new_user.role
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Errore durante la modifica: {str(e)}'})


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500


# ============ REPERIBILITÀ ROUTES ============

@app.route('/reperibilita_coverage')
@require_login
def reperibilita_coverage():
    """Lista coperture reperibilità (solo PM e Admin)"""
    if not (current_user.role in ['Admin', 'Project Manager']):
        return redirect(url_for('not_found_error'))
    
    from models import ReperibilitaCoverage
    from collections import defaultdict
    
    # Raggruppa le coperture per periodo come i presidi
    coverages = ReperibilitaCoverage.query.order_by(ReperibilitaCoverage.start_date.desc()).all()
    groups = defaultdict(lambda: {'coverages': [], 'start_date': None, 'end_date': None, 'creator': None, 'created_at': None})
    
    for coverage in coverages:
        period_key = f"{coverage.start_date.strftime('%Y-%m-%d')}_{coverage.end_date.strftime('%Y-%m-%d')}"
        if not groups[period_key]['start_date']:
            groups[period_key]['start_date'] = coverage.start_date
            groups[period_key]['end_date'] = coverage.end_date
            groups[period_key]['creator'] = coverage.creator
            groups[period_key]['created_at'] = coverage.created_at
        groups[period_key]['coverages'].append(coverage)
    
    # Converte in oggetti simili ai presidi per il template
    reperibilita_groups = {}
    for period_key, data in groups.items():
        class ReperibilitaGroup:
            def __init__(self, coverages, start_date, end_date, creator, created_at):
                self.coverages = coverages
                self.start_date = start_date
                self.end_date = end_date
                self.creator = creator
                self.created_at = created_at
        
        reperibilita_groups[period_key] = ReperibilitaGroup(
            data['coverages'], data['start_date'], data['end_date'], 
            data['creator'], data['created_at']
        )
    
    return render_template('reperibilita_coverage.html', reperibilita_groups=reperibilita_groups)


@app.route('/reperibilita_coverage/create', methods=['GET', 'POST'])
@require_login
def create_reperibilita_coverage():
    """Crea nuova copertura reperibilità (solo PM e Admin)"""
    if not (current_user.role in ['Admin', 'Project Manager']):
        return redirect(url_for('not_found_error'))
    
    from forms import ReperibilitaCoverageForm
    from models import ReperibilitaCoverage
    
    form = ReperibilitaCoverageForm()
    
    if form.validate_on_submit():
        # Crea una copertura per ogni giorno selezionato
        import json
        success_count = 0
        
        for day_of_week in form.days_of_week.data:
            coverage = ReperibilitaCoverage()
            coverage.day_of_week = day_of_week
            coverage.start_time = form.start_time.data
            coverage.end_time = form.end_time.data
            coverage.set_required_roles_list(form.required_roles.data)
            coverage.description = form.description.data
            coverage.is_active = form.is_active.data
            coverage.start_date = form.start_date.data
            coverage.end_date = form.end_date.data
            coverage.created_by = current_user.id
            
            db.session.add(coverage)
            success_count += 1
        
        try:
            db.session.commit()
            flash(f'Copertura reperibilità creata con successo per {success_count} giorni!', 'success')
            return redirect(url_for('reperibilita_coverage'))
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la creazione: {str(e)}', 'error')
    
    return render_template('create_reperibilita_coverage.html', form=form)


@app.route('/reperibilita_coverage/edit/<int:coverage_id>', methods=['GET', 'POST'])
@require_login
def edit_reperibilita_coverage(coverage_id):
    """Modifica copertura reperibilità (solo PM e Admin)"""
    if not (current_user.role in ['Admin', 'Project Manager']):
        return redirect(url_for('not_found_error'))
    
    from forms import ReperibilitaCoverageForm
    from models import ReperibilitaCoverage
    
    coverage = ReperibilitaCoverage.query.get_or_404(coverage_id)
    form = ReperibilitaCoverageForm()
    
    if form.validate_on_submit():
        coverage.start_time = form.start_time.data
        coverage.end_time = form.end_time.data
        coverage.set_required_roles_list(form.required_roles.data)
        coverage.description = form.description.data
        coverage.is_active = form.is_active.data
        coverage.start_date = form.start_date.data
        coverage.end_date = form.end_date.data
        
        try:
            db.session.commit()
            flash('Copertura reperibilità aggiornata con successo!', 'success')
            return redirect(url_for('reperibilita_coverage'))
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante l\'aggiornamento: {str(e)}', 'error')
    
    # Pre-popola il form con i dati esistenti
    if request.method == 'GET':
        form.start_time.data = coverage.start_time
        form.end_time.data = coverage.end_time
        form.required_roles.data = coverage.get_required_roles_list()
        form.description.data = coverage.description
        form.is_active.data = coverage.is_active
        form.start_date.data = coverage.start_date
        form.end_date.data = coverage.end_date
        form.days_of_week.data = [coverage.day_of_week]  # Single day for edit
    
    return render_template('edit_reperibilita_coverage.html', form=form, coverage=coverage)


@app.route('/reperibilita_coverage/delete/<int:coverage_id>', methods=['GET'])
@require_login
def delete_reperibilita_coverage(coverage_id):
    """Elimina copertura reperibilità (solo PM e Admin)"""
    if not (current_user.role in ['Admin', 'Project Manager']):
        return redirect(url_for('not_found_error'))
    
    from models import ReperibilitaCoverage
    
    coverage = ReperibilitaCoverage.query.get_or_404(coverage_id)
    
    try:
        db.session.delete(coverage)
        db.session.commit()
        flash('Copertura reperibilità eliminata con successo!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante l\'eliminazione: {str(e)}', 'error')
    
    return redirect(url_for('reperibilita_coverage'))


@app.route('/reperibilita_coverage/view/<period_key>')
@require_login
def view_reperibilita_coverage(period_key):
    """Visualizza dettagli coperture reperibilità per un periodo (solo PM e Admin)"""
    if not (current_user.role in ['Admin', 'Project Manager']):
        return redirect(url_for('not_found_error'))
    
    from models import ReperibilitaCoverage
    
    # Decodifica period_key
    start_date_str, end_date_str = period_key.split('_')
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    # Trova tutte le coperture per questo periodo
    coverages = ReperibilitaCoverage.query.filter(
        ReperibilitaCoverage.start_date == start_date,
        ReperibilitaCoverage.end_date == end_date
    ).order_by(ReperibilitaCoverage.day_of_week, ReperibilitaCoverage.start_time).all()
    
    if not coverages:
        flash('Periodo di copertura reperibilità non trovato', 'error')
        return redirect(url_for('reperibilita_coverage'))
    
    return render_template('view_reperibilita_coverage.html', 
                         coverages=coverages, 
                         start_date=start_date, 
                         end_date=end_date,
                         period_key=period_key)


@app.route('/reperibilita_coverage/delete_period/<period_key>')
@require_login  
def delete_reperibilita_period(period_key):
    """Elimina tutte le coperture reperibilità di un periodo (solo PM e Admin)"""
    if not (current_user.role in ['Admin', 'Project Manager']):
        return redirect(url_for('not_found_error'))
    
    from models import ReperibilitaCoverage
    
    # Decodifica period_key
    start_date_str, end_date_str = period_key.split('_')
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    # Trova e elimina tutte le coperture per questo periodo
    coverages = ReperibilitaCoverage.query.filter(
        ReperibilitaCoverage.start_date == start_date,
        ReperibilitaCoverage.end_date == end_date
    ).all()
    
    try:
        count = len(coverages)
        for coverage in coverages:
            db.session.delete(coverage)
        db.session.commit()
        flash(f'Eliminate {count} coperture reperibilità del periodo {start_date.strftime("%d/%m/%Y")} - {end_date.strftime("%d/%m/%Y")}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante l\'eliminazione: {str(e)}', 'error')
    
    return redirect(url_for('reperibilita_coverage'))


@app.route('/reperibilita_shifts')
@require_login
def reperibilita_shifts():
    """Gestione turni reperibilità"""
    from models import ReperibilitaShift, ReperibilitaTemplate
    from datetime import datetime, timedelta
    from collections import defaultdict
    
    # Get current template list for generation
    templates = ReperibilitaTemplate.query.order_by(ReperibilitaTemplate.created_at.desc()).all()
    
    # Parametri di visualizzazione
    if current_user.role in ['Admin', 'Project Manager', 'Management']:
        view_mode = request.args.get('view', 'all')
    elif current_user.role == 'Ente':
        view_mode = 'all'  # Ente vede sempre tutti
    else:
        view_mode = 'personal'  # Utenti normali vedono solo i propri
    
    period_mode = request.args.get('period', 'week')
    display_mode = request.args.get('display', 'table')
    
    # Calcolo periodo di visualizzazione
    today = italian_now().date()
    if period_mode == 'month':
        start_date = today.replace(day=1)
        next_month = start_date.replace(month=start_date.month + 1) if start_date.month < 12 else start_date.replace(year=start_date.year + 1, month=1)
        end_date = next_month - timedelta(days=1)
    else:  # week
        days_until_monday = today.weekday()
        start_date = today - timedelta(days=days_until_monday)
        end_date = start_date + timedelta(days=6)
    
    # Get existing shifts filtrate per periodo
    shifts_query = ReperibilitaShift.query.filter(
        ReperibilitaShift.date >= start_date,
        ReperibilitaShift.date <= end_date
    )
    
    # Applica filtro utente se necessario
    if view_mode == 'personal':
        shifts = shifts_query.filter_by(user_id=current_user.id).order_by(ReperibilitaShift.date.asc()).all()
    else:
        shifts = shifts_query.order_by(ReperibilitaShift.date.asc()).all()
    
    # Organizza shifts per giorno (per vista calendario)
    shifts_by_day = defaultdict(list)
    for shift in shifts:
        shifts_by_day[shift.date].append(shift)
    
    # Genera calendario giorni
    calendar_days = []
    current_date = start_date
    weekdays = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
    
    while current_date <= end_date:
        calendar_days.append({
            'date': current_date,
            'weekday': weekdays[current_date.weekday()],
            'is_today': current_date == today
        })
        current_date += timedelta(days=1)
    
    # Get active intervention for current user
    active_intervention = None
    current_time = italian_now().time()
    if current_user.role in ['Project Manager', 'Operatore', 'Redattore', 'Sviluppatore']:
        active_intervention = ReperibilitaIntervention.query.filter_by(
            user_id=current_user.id,
            end_datetime=None
        ).first()
    
    return render_template('reperibilita_shifts.html', 
                         shifts=shifts, 
                         templates=templates,
                         shifts_by_day=shifts_by_day,
                         active_intervention=active_intervention,
                         calendar_days=calendar_days,
                         today_date=today,
                         current_time=current_time)


@app.route('/reperibilita_template/<start_date>/<end_date>')
@require_login
def reperibilita_template_detail(start_date, end_date):
    """Mostra dettaglio template reperibilità (come shift_template_detail)"""
    from models import ReperibilitaShift
    from datetime import datetime
    from collections import defaultdict
    
    # Parse delle date
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Trova tutti i turni di reperibilità per questo periodo
    shifts = ReperibilitaShift.query.filter(
        ReperibilitaShift.date >= start_date,
        ReperibilitaShift.date <= end_date
    ).order_by(ReperibilitaShift.date, ReperibilitaShift.start_time).all()
    
    # Organizza per giorno della settimana per la vista calendario
    shifts_by_day = defaultdict(list)
    for shift in shifts:
        shifts_by_day[shift.date].append(shift)
    
    # Genera calendario giorni
    calendar_days = []
    current_date = start_date
    weekdays = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
    
    while current_date <= end_date:
        calendar_days.append({
            'date': current_date,
            'weekday': weekdays[current_date.weekday()],
            'is_today': current_date == italian_now().date()
        })
        current_date += timedelta(days=1)
    
    period_key = f"{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}"
    
    return render_template('reperibilita_template_detail.html', 
                         shifts=shifts,
                         shifts_by_day=shifts_by_day,
                         calendar_days=calendar_days,
                         start_date=start_date,
                         end_date=end_date,
                         period_key=period_key)


@app.route('/reperibilita_replica/<period_key>', methods=['GET', 'POST'])
@require_login
def reperibilita_replica(period_key):
    """Replica template reperibilità (solo PM e Admin)"""
    if not (current_user.role in ['Admin', 'Project Manager']):
        flash('Non hai i permessi per replicare i template di reperibilità', 'danger')
        return redirect(url_for('dashboard'))
    
    from forms import ReperibilitaReplicaForm
    from models import ReperibilitaCoverage
    
    # Decodifica period_key
    start_date_str, end_date_str = period_key.split('_')
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    form = ReperibilitaReplicaForm()
    
    if form.validate_on_submit():
        
        # Ottieni mappatura ruoli dal form
        role_mapping = form.get_role_mapping_dict()
        
        # Trova le coperture originali
        original_coverages = ReperibilitaCoverage.query.filter(
            ReperibilitaCoverage.start_date == start_date,
            ReperibilitaCoverage.end_date == end_date
        ).all()
        
        if not original_coverages:
            flash('Template di copertura originale non trovato', 'error')
            return redirect(url_for('reperibilita_coverage'))
        
        # Verifica se esistono già coperture per informazione (non blocca la creazione)
        existing_coverages = ReperibilitaCoverage.query.filter(
            ReperibilitaCoverage.start_date == form.start_date.data,
            ReperibilitaCoverage.end_date == form.end_date.data
        ).all()
        
        # Replica le coperture con nuove date e ruoli modificati
        new_coverages_count = 0
        for original_coverage in original_coverages:
            new_coverage = ReperibilitaCoverage()
            new_coverage.day_of_week = original_coverage.day_of_week
            new_coverage.start_time = original_coverage.start_time
            new_coverage.end_time = original_coverage.end_time
            new_coverage.description = original_coverage.description
            new_coverage.is_active = original_coverage.is_active
            new_coverage.start_date = form.start_date.data
            new_coverage.end_date = form.end_date.data
            new_coverage.created_by = current_user.id
            
            # Applica mappatura ruoli se specificata
            original_roles = original_coverage.get_required_roles_list()
            if role_mapping:
                # Sostituisce i ruoli secondo la mappatura
                new_roles = []
                for role in original_roles:
                    if role in role_mapping:
                        new_roles.append(role_mapping[role])
                    else:
                        new_roles.append(role)  # Mantiene il ruolo originale se non mappato
                new_coverage.set_required_roles_list(new_roles)
            else:
                # Mantiene i ruoli originali
                new_coverage.set_required_roles_list(original_roles)
            
            db.session.add(new_coverage)
            new_coverages_count += 1
        
        try:
            db.session.commit()
            
            success_msg = f'Template reperibilità replicato con successo. Coperture create: {new_coverages_count}.'
            if role_mapping:
                success_msg += f' Ruoli sostituiti: {len(role_mapping)}.'
            if existing_coverages:
                success_msg += f' Aggiunte a {len(existing_coverages)} coperture esistenti.'
            
            flash(success_msg, 'success')
            return redirect(url_for('reperibilita_coverage'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la replica: {str(e)}', 'error')
    
    # Pre-popola le date originali come suggerimento
    if request.method == 'GET':
        form.start_date.data = start_date
        form.end_date.data = end_date
    
    # Trova le coperture originali per mostrare informazioni nel template
    original_coverages = ReperibilitaCoverage.query.filter(
        ReperibilitaCoverage.start_date == start_date,
        ReperibilitaCoverage.end_date == end_date
    ).order_by(ReperibilitaCoverage.day_of_week, ReperibilitaCoverage.start_time).all()
    
    return render_template('reperibilita_replica.html', 
                         form=form,
                         original_coverages=original_coverages,
                         start_date=start_date,
                         end_date=end_date)


@app.route('/reperibilita_shifts/generate', methods=['GET', 'POST'])
@require_login
def generate_reperibilita_shifts():
    """Genera turnazioni reperibilità (solo PM e Admin)"""
    if not (current_user.role in ['Admin', 'Project Manager']):
        return redirect(url_for('not_found_error'))
    
    from forms import ReperibilitaTemplateForm
    from models import ReperibilitaTemplate, ReperibilitaShift
    from utils import generate_reperibilita_shifts
    
    form = ReperibilitaTemplateForm()
    
    if form.validate_on_submit():
        # Elimina turni esistenti nel periodo
        existing_shifts = ReperibilitaShift.query.filter(
            ReperibilitaShift.date >= form.start_date.data,
            ReperibilitaShift.date <= form.end_date.data
        ).all()
        
        for shift in existing_shifts:
            db.session.delete(shift)
        
        # Crea template
        template = ReperibilitaTemplate()
        template.name = form.name.data
        template.start_date = form.start_date.data
        template.end_date = form.end_date.data
        template.description = form.description.data
        template.created_by = current_user.id
        db.session.add(template)
        
        try:
            # Genera turni reperibilità
            shifts_created, warnings = generate_reperibilita_shifts(
                form.start_date.data,
                form.end_date.data,
                current_user.id
            )
            
            db.session.commit()
            
            # Costruisci messaggio di successo
            success_msg = f'Template "{form.name.data}" creato con successo. Turni reperibilità generati: {shifts_created}.'
            
            if warnings:
                if len(warnings) <= 3:
                    warning_text = " Attenzione: " + "; ".join(warnings)
                else:
                    warning_text = f" Attenzione: {warnings[0]}; {warnings[1]}; {warnings[2]} e altri {len(warnings) - 3} avvisi."
                success_msg += warning_text
            
            flash(success_msg, 'success' if not warnings else 'warning')
            return redirect(url_for('reperibilita_shifts'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la generazione: {str(e)}', 'error')
    
    return render_template('generate_reperibilita_shifts.html', form=form)


@app.route('/reperibilita_shifts/regenerate/<int:template_id>', methods=['GET'])
@require_login
def regenerate_reperibilita_template(template_id):
    """Rigenera turni reperibilità da template esistente (solo PM e Admin)"""
    if not (current_user.role in ['Admin', 'Project Manager']):
        return redirect(url_for('not_found_error'))
    
    from models import ReperibilitaTemplate, ReperibilitaShift
    from utils import generate_reperibilita_shifts
    
    # Trova il template esistente
    template = ReperibilitaTemplate.query.get_or_404(template_id)
    
    try:
        # Elimina turni esistenti nel periodo del template
        existing_shifts = ReperibilitaShift.query.filter(
            ReperibilitaShift.date >= template.start_date,
            ReperibilitaShift.date <= template.end_date
        ).all()
        
        for shift in existing_shifts:
            db.session.delete(shift)
        
        # Rigenera turni con gli stessi parametri del template
        shifts_created, warnings = generate_reperibilita_shifts(
            template.start_date,
            template.end_date,
            current_user.id
        )
        
        # Aggiorna la data di creazione del template
        template.created_at = italian_now()
        
        db.session.commit()
        
        # Costruisci messaggio di successo
        success_msg = f'Template "{template.name}" rigenerato con successo. Turni reperibilità generati: {shifts_created}.'
        
        if warnings:
            if len(warnings) <= 3:
                warning_text = " Attenzione: " + "; ".join(warnings)
            else:
                warning_text = f" Attenzione: {warnings[0]}; {warnings[1]}; {warnings[2]} e altri {len(warnings) - 3} avvisi."
            success_msg += warning_text
        
        flash(success_msg, 'success' if not warnings else 'warning')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante la rigenerazione: {str(e)}', 'error')
    
    return redirect(url_for('reperibilita_shifts'))


@app.route('/start-intervention', methods=['POST'])
@login_required
def start_intervention():
    """Inizia un intervento di reperibilità"""
    if current_user.role not in ['Project Manager', 'Operatore', 'Redattore', 'Sviluppatore']:
        flash('Non hai i permessi per registrare interventi di reperibilità.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Controlla se c'è già un intervento attivo
    active_intervention = ReperibilitaIntervention.query.filter_by(
        user_id=current_user.id,
        end_datetime=None
    ).first()
    
    if active_intervention:
        flash('Hai già un intervento di reperibilità in corso.', 'warning')
        return redirect(url_for('dashboard'))
    
    # Ottieni shift_id dal form se presente
    shift_id = request.form.get('shift_id')
    if shift_id:
        shift_id = int(shift_id)
    
    # Ottieni is_remote dal form (default True = remoto)
    is_remote = request.form.get('is_remote', 'true').lower() == 'true'
    
    # Ottieni priorità dal form (default Media)
    priority = request.form.get('priority', 'Media')
    if priority not in ['Bassa', 'Media', 'Alta']:
        priority = 'Media'
    
    # Crea nuovo intervento
    intervention = ReperibilitaIntervention(
        user_id=current_user.id,
        shift_id=shift_id,
        start_datetime=italian_now(),
        description=request.form.get('description', ''),
        priority=priority,
        is_remote=is_remote
    )
    
    db.session.add(intervention)
    db.session.commit()
    
    flash('Intervento di reperibilità iniziato con successo.', 'success')
    return redirect(url_for('reperibilita_shifts'))


@app.route('/end-intervention', methods=['POST'])
@login_required
def end_intervention():
    """Termina un intervento di reperibilità"""
    if current_user.role not in ['Project Manager', 'Operatore', 'Redattore', 'Sviluppatore']:
        flash('Non hai i permessi per registrare interventi di reperibilità.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Trova l'intervento attivo
    active_intervention = ReperibilitaIntervention.query.filter_by(
        user_id=current_user.id,
        end_datetime=None
    ).first()
    
    if not active_intervention:
        flash('Nessun intervento di reperibilità attivo da terminare.', 'warning')
        return redirect(url_for('dashboard'))
    
    # Termina l'intervento
    active_intervention.end_datetime = italian_now()
    active_intervention.description = request.form.get('description', active_intervention.description)
    
    db.session.commit()
    
    flash('Intervento di reperibilità terminato con successo.', 'success')
    
    # Redirect PM to ente_home, others to reperibilita_shifts
    if current_user.role == 'Project Manager':
        return redirect(url_for('ente_home'))
    else:
        return redirect(url_for('reperibilita_shifts'))


@app.route('/reperibilita_template/delete/<template_id>')
@require_login
def delete_reperibilita_template(template_id):
    """Elimina un template reperibilità e tutti i suoi turni (solo PM e Admin)"""
    if not (current_user.role in ['Admin', 'Project Manager']):
        return redirect(url_for('not_found_error'))
    
    from models import ReperibilitaTemplate, ReperibilitaShift
    
    template = ReperibilitaTemplate.query.get_or_404(template_id)
    
    try:
        # Elimina tutti i turni del periodo del template
        shifts = ReperibilitaShift.query.filter(
            ReperibilitaShift.date >= template.start_date,
            ReperibilitaShift.date <= template.end_date
        ).all()
        
        for shift in shifts:
            db.session.delete(shift)
        
        # Elimina il template
        template_name = template.name
        db.session.delete(template)
        db.session.commit()
        
        flash(f'Template reperibilità "{template_name}" eliminato con successo', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante l\'eliminazione: {str(e)}', 'error')
    
    return redirect(url_for('reperibilita_shifts'))


# QR Code Authentication Routes
@app.route('/qr_login/<action>', methods=['GET', 'POST'])
def qr_login(action):
    """Pagina di login con QR code per entrata/uscita rapida"""
    if action not in ['entrata', 'uscita']:
        flash('Azione non valida', 'error')
        return redirect(url_for('login'))
    
    # Se l'utente è già autenticato, esegui l'azione direttamente
    if current_user.is_authenticated:
        return redirect(url_for('quick_attendance', action=action))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash(f'Accesso effettuato con successo!', 'success')
            return redirect(url_for('quick_attendance', action=action))
        else:
            flash('Username o password non validi', 'error')
    
    return render_template('qr_login.html', form=form, action=action)


@app.route('/quick_attendance/<action>', methods=['GET'])
@require_login
def quick_attendance(action):
    """Gestisce la registrazione rapida di entrata/uscita tramite QR"""
    if action not in ['entrata', 'uscita']:
        flash('Azione non valida', 'error')
        return redirect(url_for('index'))
    
    try:
        now = italian_now()
        today = now.date()
        
        # QR Code actions now use only AttendanceEvent
        
        if action == 'entrata':
            # Create entry event
            entry_event = AttendanceEvent(
                user_id=current_user.id,
                date=today,
                event_type='clock_in',
                timestamp=now,
                notes='Entrata tramite QR Code'
            )
            db.session.add(entry_event)
            message = f'Entrata registrata alle {now.strftime("%H:%M")}'
            
        else:  # uscita
            # Create exit event
            exit_event = AttendanceEvent(
                user_id=current_user.id,
                date=today,
                event_type='clock_out',
                timestamp=now,
                notes='Uscita tramite QR Code'
            )
            db.session.add(exit_event)
            message = f'Uscita registrata alle {now.strftime("%H:%M")}'
        
        db.session.commit()
        flash(message, 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante la registrazione: {str(e)}', 'error')
    
    return redirect(url_for('index'))


@app.route('/generate_qr_codes')
def generate_qr_codes():
    """Genera i codici QR per entrata e uscita"""
    try:
        base_url = request.url_root.rstrip('/')
        
        # URLs per entrata e uscita
        entry_url = f"{base_url}/qr_login/entrata"
        exit_url = f"{base_url}/qr_login/uscita"
        
        # Genera QR Code per entrata (semplificato)
        qr_entry = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr_entry.add_data(entry_url)
        qr_entry.make(fit=True)
        
        # Crea immagine con colori default
        entry_img = qr_entry.make_image(fill_color="black", back_color="white")
        entry_buffer = BytesIO()
        entry_img.save(entry_buffer, format='PNG')
        entry_buffer.seek(0)
        entry_qr_data = base64.b64encode(entry_buffer.getvalue()).decode()
        
        # Genera QR Code per uscita (semplificato)
        qr_exit = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr_exit.add_data(exit_url)
        qr_exit.make(fit=True)
        
        # Crea immagine con colori default
        exit_img = qr_exit.make_image(fill_color="black", back_color="white")
        exit_buffer = BytesIO()
        exit_img.save(exit_buffer, format='PNG')
        exit_buffer.seek(0)
        exit_qr_data = base64.b64encode(exit_buffer.getvalue()).decode()
        
        return render_template('qr_codes.html',
                             entry_qr=entry_qr_data,
                             exit_qr=exit_qr_data,
                             entry_url=entry_url,
                             exit_url=exit_url)
                             
    except Exception as e:
        flash(f'Errore nella generazione dei codici QR: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/shifts/export/csv')
@login_required
def export_shifts_csv():
    """Export turni in formato CSV"""
    # Parametri dalla query string
    view_mode = request.args.get('view', 'month')  # month, week, day
    show_my_shifts = request.args.get('my_shifts', 'false') == 'true'
    date_param = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    try:
        current_date = datetime.strptime(date_param, '%Y-%m-%d').date()
    except:
        current_date = date.today()
    
    # Calcola range di date in base alla vista
    if view_mode == 'day':
        start_date = current_date
        end_date = current_date
        filename = f"turni_{current_date.strftime('%Y-%m-%d')}.csv"
    elif view_mode == 'week':
        # Settimana (Lunedì - Domenica)
        days_since_monday = current_date.weekday()
        start_date = current_date - timedelta(days=days_since_monday)
        end_date = start_date + timedelta(days=6)
        filename = f"turni_settimana_{start_date.strftime('%Y-%m-%d')}.csv"
    else:  # month
        start_date = current_date.replace(day=1)
        if current_date.month == 12:
            end_date = date(current_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(current_date.year, current_date.month + 1, 1) - timedelta(days=1)
        filename = f"turni_{current_date.strftime('%Y-%m')}.csv"
    
    # Query dei turni
    shifts_query = Shift.query.filter(
        Shift.date >= start_date,
        Shift.date <= end_date
    )
    
    # Filtro per "I Miei Turni" se richiesto
    if show_my_shifts:
        shifts_query = shifts_query.filter(Shift.user_id == current_user.id)
        filename = f"miei_{filename}"
    
    shifts = shifts_query.order_by(Shift.date, Shift.start_time).all()
    
    # Crea CSV in memoria
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Data', 'Utente', 'Ruolo', 'Orario Inizio', 'Orario Fine', 
        'Tipo Turno', 'Durata (ore)'
    ])
    
    # Dati
    for shift in shifts:
        duration = (datetime.combine(date.today(), shift.end_time) - 
                   datetime.combine(date.today(), shift.start_time)).total_seconds() / 3600
        
        writer.writerow([
            shift.date.strftime('%d/%m/%Y'),
            shift.user.get_full_name(),
            shift.user.role,
            shift.start_time.strftime('%H:%M'),
            shift.end_time.strftime('%H:%M'),
            shift.shift_type,
            f"{duration:.1f}"
        ])
    
    # Crea response
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    
    return response

@app.route('/shifts/export/pdf')
@login_required  
def export_shifts_pdf():
    """Export calendario turni in formato PDF"""
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from io import BytesIO
    
    # Parametri dalla query string
    view_mode = request.args.get('view', 'month')
    show_my_shifts = request.args.get('my_shifts', 'false') == 'true'
    date_param = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    try:
        current_date = datetime.strptime(date_param, '%Y-%m-%d').date()
    except:
        current_date = date.today()
    
    # Calcola range di date in base alla vista
    if view_mode == 'day':
        start_date = current_date
        end_date = current_date
        title = f"Turni del {current_date.strftime('%d/%m/%Y')}"
        filename = f"turni_{current_date.strftime('%Y-%m-%d')}.pdf"
    elif view_mode == 'week':
        days_since_monday = current_date.weekday()
        start_date = current_date - timedelta(days=days_since_monday)
        end_date = start_date + timedelta(days=6)
        title = f"Turni settimana {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"
        filename = f"turni_settimana_{start_date.strftime('%Y-%m-%d')}.pdf"
    else:  # month
        start_date = current_date.replace(day=1)
        if current_date.month == 12:
            end_date = date(current_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(current_date.year, current_date.month + 1, 1) - timedelta(days=1)
        # Get Italian month name
        month_names = {
            1: 'Gennaio', 2: 'Febbraio', 3: 'Marzo', 4: 'Aprile',
            5: 'Maggio', 6: 'Giugno', 7: 'Luglio', 8: 'Agosto',
            9: 'Settembre', 10: 'Ottobre', 11: 'Novembre', 12: 'Dicembre'
        }
        month_name = month_names.get(current_date.month, current_date.strftime('%B'))
        title = f"Turni {month_name} {current_date.year}"
        filename = f"turni_{current_date.strftime('%Y-%m')}.pdf"
    
    # Query dei turni
    shifts_query = Shift.query.filter(
        Shift.date >= start_date,
        Shift.date <= end_date
    )
    
    if show_my_shifts:
        shifts_query = shifts_query.filter(Shift.user_id == current_user.id)
        title = f"I Miei {title}"
        filename = f"miei_{filename}"
    
    shifts = shifts_query.order_by(Shift.date, Shift.start_time).all()
    
    # Crea PDF in memoria
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch, bottomMargin=1*inch)
    story = []
    
    # Stili
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1  # Center
    )
    
    date_style = ParagraphStyle(
        'DateHeader',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=10,
        textColor=colors.darkblue,
        leftIndent=0
    )
    
    # Titolo
    story.append(Paragraph(title, title_style))
    story.append(Paragraph(f"Generato il {datetime.now().strftime('%d/%m/%Y alle %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Raggruppa turni per data
    shifts_by_date = {}
    for shift in shifts:
        if shift.date not in shifts_by_date:
            shifts_by_date[shift.date] = []
        shifts_by_date[shift.date].append(shift)
    
    # Genera calendario giorno per giorno
    weekday_names = {
        0: 'Lunedì', 1: 'Martedì', 2: 'Mercoledì', 3: 'Giovedì',
        4: 'Venerdì', 5: 'Sabato', 6: 'Domenica'
    }
    
    current = start_date
    while current <= end_date:
        italian_weekday = weekday_names.get(current.weekday(), current.strftime('%A'))
        date_header = f"{italian_weekday} {current.strftime('%d/%m/%Y')}"
        
        story.append(Paragraph(date_header, date_style))
        
        if current in shifts_by_date:
            # Crea tabella per i turni del giorno
            data = [['Utente', 'Ruolo', 'Orario', 'Tipo Turno', 'Durata']]
            
            for shift in shifts_by_date[current]:
                duration = f"{shift.get_duration_hours():.1f}h"
                data.append([
                    shift.user.get_full_name(),
                    shift.user.role,
                    f"{shift.start_time.strftime('%H:%M')} - {shift.end_time.strftime('%H:%M')}",
                    shift.shift_type,
                    duration
                ])
            
            table = Table(data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1*inch, 0.8*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            
            story.append(table)
        else:
            story.append(Paragraph("Nessun turno programmato", styles['Italic']))
        
        story.append(Spacer(1, 15))
        current += timedelta(days=1)
    
    # Genera PDF
    doc.build(story)
    buffer.seek(0)
    
    # Crea response
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    
    return response



@app.route('/export_attendance_csv')
@login_required  
def export_attendance_csv():
    """Export presenze in formato CSV"""
    from io import StringIO
    from defusedcsv import csv
    
    # Controllo permessi
    if not current_user.can_access_attendance():
        flash('Non hai i permessi per esportare presenze.', 'danger')
        return redirect(url_for('shifts'))
    
    # Handle team/personal view toggle for PM
    view_mode = request.args.get('view', 'personal')
    if current_user.role == 'Project Manager':
        show_team_data = (view_mode == 'team')
    else:
        show_team_data = False
    
    # Handle date filtering
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    if not start_date_str or not end_date_str:
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
    else:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
    
    if show_team_data:
        team_users = User.query.filter(
            User.role.in_(['Redattore', 'Sviluppatore', 'Operatore', 'Project Manager']),
            User.active.is_(True)
        ).all()
        
        records = []
        for user in team_users:
            user_records = AttendanceEvent.get_events_as_records(user.id, start_date, end_date)
            records.extend(user_records)
    else:
        records = AttendanceEvent.get_events_as_records(current_user.id, start_date, end_date)
    
    records.sort(key=lambda x: x.date, reverse=True)
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    
    if show_team_data:
        writer.writerow(['Data', 'Utente', 'Ruolo', 'Entrata', 'Pausa Inizio', 'Pausa Fine', 'Uscita', 'Ore Lavorate', 'Note'])
    else:
        writer.writerow(['Data', 'Entrata', 'Pausa Inizio', 'Pausa Fine', 'Uscita', 'Ore Lavorate', 'Note'])
    
    for record in records:
        row = [record.date.strftime('%d/%m/%Y')]
        
        if show_team_data and hasattr(record, 'user') and record.user:
            row.extend([record.user.get_full_name(), record.user.role])
        elif show_team_data:
            row.extend(['--', '--'])
        
        row.extend([
            record.clock_in.strftime('%H:%M') if record.clock_in else '--:--',
            record.break_start.strftime('%H:%M') if record.break_start else '--:--',
            record.break_end.strftime('%H:%M') if record.break_end else '--:--',
            record.clock_out.strftime('%H:%M') if record.clock_out else '--:--',
            f"{record.get_work_hours():.2f}" if record.clock_in and record.clock_out else '0.00',
            record.notes or ''
        ])
        
        writer.writerow(row)
    
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    
    filename = f"presenze_{'team' if show_team_data else 'personali'}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    
    return response





@app.route('/start_general_intervention', methods=['POST'])
@login_required
def start_general_intervention():
    """Inizia un nuovo intervento generico"""
    # Controlla se l'utente è presente
    user_status, _ = AttendanceEvent.get_user_status(current_user.id)
    if user_status != 'in':
        flash('Devi essere presente per iniziare un intervento.', 'warning')
        return redirect(url_for('dashboard'))
    
    # Controlla se c'è già un intervento attivo
    active_intervention = Intervention.query.filter_by(
        user_id=current_user.id,
        end_datetime=None
    ).first()
    
    if active_intervention:
        flash('Hai già un intervento attivo. Terminalo prima di iniziarne un altro.', 'warning')
        return redirect(url_for('dashboard'))
    
    # Ottieni i dati dal form
    description = request.form.get('description', '')
    priority = request.form.get('priority', 'Media')
    is_remote = request.form.get('is_remote', 'false').lower() == 'true'
    
    # Crea nuovo intervento
    from zoneinfo import ZoneInfo
    italy_tz = ZoneInfo('Europe/Rome')
    now = datetime.now(italy_tz)
    
    intervention = Intervention(
        user_id=current_user.id,
        start_datetime=now,
        description=description,
        priority=priority,
        is_remote=is_remote
    )
    
    try:
        db.session.add(intervention)
        db.session.commit()
        flash(f'Intervento in presenza iniziato alle {now.strftime("%H:%M")}', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Errore nel salvare l\'intervento', 'danger')
    
    return redirect(url_for('dashboard'))

@app.route('/end_general_intervention', methods=['POST'])
@login_required
def end_general_intervention():
    """Termina un intervento generico attivo"""
    # Trova l'intervento attivo
    active_intervention = Intervention.query.filter_by(
        user_id=current_user.id,
        end_datetime=None
    ).first()
    
    if not active_intervention:
        flash('Nessun intervento attivo trovato.', 'warning')
        return redirect(url_for('dashboard'))
    
    # Termina l'intervento
    from zoneinfo import ZoneInfo
    italy_tz = ZoneInfo('Europe/Rome')
    now = datetime.now(italy_tz)
    
    active_intervention.end_datetime = now
    
    # Gestisci la descrizione finale
    end_description = request.form.get('end_description', '').strip()
    if end_description:
        # Combina descrizione iniziale e finale
        initial_desc = active_intervention.description or ''
        if initial_desc and end_description:
            active_intervention.description = f"{initial_desc}\n\n--- Risoluzione ---\n{end_description}"
        elif end_description:
            active_intervention.description = end_description
    
    try:
        db.session.commit()
        duration = active_intervention.duration_minutes
        flash(f'Intervento terminato alle {now.strftime("%H:%M")} (durata: {duration:.1f} minuti)', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Errore nel terminare l\'intervento', 'danger')
    
    return redirect(url_for('dashboard'))

@app.route('/my_interventions')
@login_required
def my_interventions():
    """Pagina per visualizzare gli interventi - tutti per PM/Ente, solo propri per altri utenti"""
    # Solo Admin non può accedere a questa pagina (non ha interventi)
    if current_user.role == 'Admin':
        flash('Accesso non autorizzato.', 'danger')
        return redirect(url_for('dashboard'))
    
    from zoneinfo import ZoneInfo
    italy_tz = ZoneInfo('Europe/Rome')
    today = datetime.now(italy_tz).date()
    
    # Gestisci filtri data
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Default: primo del mese corrente - oggi
    if not start_date_str:
        start_date = today.replace(day=1)
    else:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    
    if not end_date_str:
        end_date = today
    else:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    # Converti le date in datetime per il filtro
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # PM ed Ente vedono tutti gli interventi, altri utenti solo i propri
    if current_user.role in ['Project Manager', 'Ente']:
        # Ottieni tutti gli interventi di reperibilità filtrati per data
        reperibilita_interventions = ReperibilitaIntervention.query.join(User).filter(
            ReperibilitaIntervention.start_datetime >= start_datetime,
            ReperibilitaIntervention.start_datetime <= end_datetime
        ).order_by(ReperibilitaIntervention.start_datetime.desc()).all()
        
        # Ottieni tutti gli interventi generici filtrati per data
        general_interventions = Intervention.query.join(User).filter(
            Intervention.start_datetime >= start_datetime,
            Intervention.start_datetime <= end_datetime
        ).order_by(Intervention.start_datetime.desc()).all()
    else:
        # Ottieni solo gli interventi dell'utente corrente filtrati per data
        reperibilita_interventions = ReperibilitaIntervention.query.filter(
            ReperibilitaIntervention.user_id == current_user.id,
            ReperibilitaIntervention.start_datetime >= start_datetime,
            ReperibilitaIntervention.start_datetime <= end_datetime
        ).order_by(ReperibilitaIntervention.start_datetime.desc()).all()
        
        general_interventions = Intervention.query.filter(
            Intervention.user_id == current_user.id,
            Intervention.start_datetime >= start_datetime,
            Intervention.start_datetime <= end_datetime
        ).order_by(Intervention.start_datetime.desc()).all()
    
    return render_template('my_interventions.html',
                         reperibilita_interventions=reperibilita_interventions,
                         general_interventions=general_interventions,
                         start_date=start_date,
                         end_date=end_date)

@app.route('/export_general_interventions_csv')
@login_required
def export_general_interventions_csv():
    """Export interventi generici in formato CSV"""
    if current_user.role == 'Admin':
        flash('Accesso non autorizzato.', 'danger')
        return redirect(url_for('dashboard'))
    
    from zoneinfo import ZoneInfo
    italy_tz = ZoneInfo('Europe/Rome')
    today = datetime.now(italy_tz).date()
    
    # Gestisci filtri data
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Default: primo del mese corrente - oggi
    if not start_date_str:
        start_date = today.replace(day=1)
    else:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    
    if not end_date_str:
        end_date = today
    else:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    # Converti le date in datetime per il filtro
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # PM ed Ente vedono tutti gli interventi, altri utenti solo i propri
    if current_user.role in ['Project Manager', 'Ente']:
        general_interventions = Intervention.query.join(User).filter(
            Intervention.start_datetime >= start_datetime,
            Intervention.start_datetime <= end_datetime
        ).order_by(Intervention.start_datetime.desc()).all()
    else:
        general_interventions = Intervention.query.filter(
            Intervention.user_id == current_user.id,
            Intervention.start_datetime >= start_datetime,
            Intervention.start_datetime <= end_datetime
        ).order_by(Intervention.start_datetime.desc()).all()
    
    # Crea il CSV
    import io
    import csv
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    if current_user.role in ['Project Manager', 'Ente']:
        header = ['Utente', 'Nome', 'Cognome', 'Ruolo', 'Data Inizio', 'Ora Inizio', 'Data Fine', 'Ora Fine', 
                 'Durata (minuti)', 'Priorità', 'Tipologia', 'Descrizione', 'Stato']
    else:
        header = ['Data Inizio', 'Ora Inizio', 'Data Fine', 'Ora Fine', 
                 'Durata (minuti)', 'Priorità', 'Tipologia', 'Descrizione', 'Stato']
    writer.writerow(header)
    
    # Dati
    for intervention in general_interventions:
        row = []
        
        if current_user.role in ['Project Manager', 'Ente']:
            row.extend([
                intervention.user.username,
                intervention.user.first_name,
                intervention.user.last_name,
                intervention.user.role
            ])
        
        row.extend([
            intervention.start_datetime.strftime('%d/%m/%Y'),
            intervention.start_datetime.strftime('%H:%M'),
            intervention.end_datetime.strftime('%d/%m/%Y') if intervention.end_datetime else 'In corso',
            intervention.end_datetime.strftime('%H:%M') if intervention.end_datetime else '',
            round(intervention.duration_minutes, 1) if intervention.end_datetime else '',
            intervention.priority or '',
            'In presenza',
            intervention.description or '',
            'Completato' if intervention.end_datetime else 'In corso'
        ])
        
        writer.writerow(row)
    
    # Prepara la risposta
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    
    filename = f'interventi_generici_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.csv'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

@app.route('/export_reperibilita_interventions_csv')
@login_required
def export_reperibilita_interventions_csv():
    """Export interventi reperibilità in formato CSV"""
    if current_user.role == 'Admin':
        flash('Accesso non autorizzato.', 'danger')
        return redirect(url_for('dashboard'))
    
    from zoneinfo import ZoneInfo
    italy_tz = ZoneInfo('Europe/Rome')
    today = datetime.now(italy_tz).date()
    
    # Gestisci filtri data
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Default: primo del mese corrente - oggi
    if not start_date_str:
        start_date = today.replace(day=1)
    else:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    
    if not end_date_str:
        end_date = today
    else:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    # Converti le date in datetime per il filtro
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # PM ed Ente vedono tutti gli interventi, altri utenti solo i propri
    if current_user.role in ['Project Manager', 'Ente']:
        reperibilita_interventions = ReperibilitaIntervention.query.join(User).filter(
            ReperibilitaIntervention.start_datetime >= start_datetime,
            ReperibilitaIntervention.start_datetime <= end_datetime
        ).order_by(ReperibilitaIntervention.start_datetime.desc()).all()
    else:
        reperibilita_interventions = ReperibilitaIntervention.query.filter(
            ReperibilitaIntervention.user_id == current_user.id,
            ReperibilitaIntervention.start_datetime >= start_datetime,
            ReperibilitaIntervention.start_datetime <= end_datetime
        ).order_by(ReperibilitaIntervention.start_datetime.desc()).all()
    
    # Crea il CSV
    import io
    import csv
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    if current_user.role in ['Project Manager', 'Ente']:
        header = ['Utente', 'Nome', 'Cognome', 'Ruolo', 'Data Inizio', 'Ora Inizio', 'Data Fine', 'Ora Fine', 
                 'Durata (minuti)', 'Priorità', 'Tipologia', 'Data Turno', 'Ora Inizio Turno', 'Ora Fine Turno', 
                 'Descrizione', 'Stato']
    else:
        header = ['Data Inizio', 'Ora Inizio', 'Data Fine', 'Ora Fine', 
                 'Durata (minuti)', 'Priorità', 'Tipologia', 'Data Turno', 'Ora Inizio Turno', 'Ora Fine Turno', 
                 'Descrizione', 'Stato']
    writer.writerow(header)
    
    # Dati
    for intervention in reperibilita_interventions:
        row = []
        
        if current_user.role in ['Project Manager', 'Ente']:
            row.extend([
                intervention.user.username,
                intervention.user.first_name,
                intervention.user.last_name,
                intervention.user.role
            ])
        
        row.extend([
            intervention.start_datetime.strftime('%d/%m/%Y'),
            intervention.start_datetime.strftime('%H:%M'),
            intervention.end_datetime.strftime('%d/%m/%Y') if intervention.end_datetime else 'In corso',
            intervention.end_datetime.strftime('%H:%M') if intervention.end_datetime else '',
            round(intervention.duration_minutes, 1) if intervention.end_datetime else '',
            intervention.priority or '',
            'Remoto' if intervention.is_remote else 'In presenza',
            intervention.shift.date.strftime('%d/%m/%Y') if intervention.shift else '',
            intervention.shift.start_time.strftime('%H:%M') if intervention.shift else '',
            intervention.shift.end_time.strftime('%H:%M') if intervention.shift else '',
            intervention.description or '',
            'Completato' if intervention.end_datetime else 'In corso'
        ])
        
        writer.writerow(row)
    
    # Prepara la risposta
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    
    filename = f'interventi_reperibilita_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.csv'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@app.route('/qr/<action>')
def qr_page(action):
    """Pagine dedicate per QR Code di entrata e uscita"""
    if action not in ['entrata', 'uscita']:
        return redirect(url_for('login'))
    
    # Genera URL completo per il QR code
    base_url = request.url_root.rstrip('/')
    qr_url = f"{base_url}/qr_login/{action}"
    
    return render_template('qr_page.html', action=action, qr_url=qr_url)


@app.route('/admin/qr_codes')
@require_login
def admin_generate_qr_codes():
    """Gestione codici QR (solo Admin)"""
    if current_user.role != 'Admin':
        return redirect(url_for('not_found_error'))
    
    from utils import qr_codes_exist, get_qr_code_urls
    
    # Verifica se i QR code statici esistono
    qr_exist = qr_codes_exist()
    
    # Genera URL completi per i QR codes
    base_url = request.url_root.rstrip('/')
    qr_urls = {
        'entrata': f"{base_url}/qr_login/entrata",
        'uscita': f"{base_url}/qr_login/uscita"
    }
    
    # Se esistono, ottieni gli URL per visualizzarli
    static_qr_urls = get_qr_code_urls() if qr_exist else None
    
    return render_template('admin_qr_codes.html', 
                         qr_urls=qr_urls,
                         qr_exist=qr_exist,
                         static_qr_urls=static_qr_urls)

@app.route('/admin/generate_static_qr')
@require_login  
def generate_static_qr():
    """Genera QR code statici e li salva su file (solo Admin)"""
    if current_user.role != 'Admin':
        return redirect(url_for('not_found_error'))
    
    from utils import generate_static_qr_codes
    
    if generate_static_qr_codes():
        flash('QR code generati con successo e salvati come file statici', 'success')
    else:
        flash('Errore nella generazione dei QR code statici', 'danger')
    
    # Forza refresh della pagina per mostrare i nuovi QR code
    return redirect(url_for('admin_generate_qr_codes') + '?refresh=1')


# ===============================
# GESTIONE SEDI E ORARI DI LAVORO
# ===============================

@app.route('/admin/sedi')
@login_required
def manage_sedi():
    """Gestione delle sedi aziendali"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per gestire le sedi', 'danger')
        return redirect(url_for('dashboard'))
    
    sedi = Sede.query.order_by(Sede.created_at.desc()).all()
    form = SedeForm()
    return render_template('manage_sedi.html', sedi=sedi, form=form)

@app.route('/admin/sedi/create', methods=['POST'])
@login_required
def create_sede():
    """Crea una nuova sede"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per creare sedi', 'danger')
        return redirect(url_for('dashboard'))
    
    form = SedeForm()
    if form.validate_on_submit():
        sede = Sede(
            name=form.name.data,
            address=form.address.data,
            description=form.description.data,
            active=form.is_active.data
        )
        db.session.add(sede)
        db.session.commit()
        flash('Sede creata con successo', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'danger')
    
    return redirect(url_for('manage_sedi'))

@app.route('/admin/sedi/edit/<int:sede_id>', methods=['GET', 'POST'])
@login_required
def edit_sede(sede_id):
    """Modifica una sede esistente"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per modificare sedi', 'danger')
        return redirect(url_for('dashboard'))
    
    sede = Sede.query.get_or_404(sede_id)
    form = SedeForm(original_name=sede.name, obj=sede)
    
    if form.validate_on_submit():
        sede.name = form.name.data
        sede.address = form.address.data
        sede.description = form.description.data
        sede.active = form.is_active.data
        
        db.session.commit()
        flash(f'Sede "{sede.name}" modificata con successo', 'success')
        return redirect(url_for('manage_sedi'))
    
    return render_template('edit_sede.html', form=form, sede=sede)

@app.route('/admin/sedi/toggle/<int:sede_id>')
@login_required
def toggle_sede(sede_id):
    """Attiva/disattiva una sede"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per modificare sedi', 'danger')
        return redirect(url_for('dashboard'))
    
    sede = Sede.query.get_or_404(sede_id)
    sede.active = not sede.active
    db.session.commit()
    
    status = 'attivata' if sede.active else 'disattivata'
    flash(f'Sede "{sede.name}" {status} con successo', 'success')
    return redirect(url_for('manage_sedi'))

@app.route('/admin/orari')
@login_required
def manage_work_schedules():
    """Gestione degli orari di lavoro"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per gestire gli orari', 'danger')
        return redirect(url_for('dashboard'))
    
    schedules = WorkSchedule.query.join(Sede).order_by(Sede.name, WorkSchedule.start_time).all()
    form = WorkScheduleForm()
    return render_template('manage_work_schedules.html', schedules=schedules, form=form)

@app.route('/admin/orari/create', methods=['POST'])
@login_required
def create_work_schedule():
    """Crea un nuovo orario di lavoro"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per creare orari', 'danger')
        return redirect(url_for('dashboard'))
    
    form = WorkScheduleForm()
    if form.validate_on_submit():
        # Determina i giorni della settimana dal preset o dalla selezione personalizzata
        if form.days_preset.data != 'custom':
            days_of_week = form.get_days_from_preset(form.days_preset.data)
        else:
            days_of_week = form.days_of_week.data
        
        schedule = WorkSchedule(
            sede_id=form.sede.data,
            name=form.name.data,
            start_time_min=form.start_time_min.data,
            start_time_max=form.start_time_max.data,
            end_time_min=form.end_time_min.data,
            end_time_max=form.end_time_max.data,
            # Imposta campi legacy per compatibilità usando il valore minimo
            start_time=form.start_time_min.data,
            end_time=form.end_time_min.data,
            days_of_week=days_of_week,
            description=form.description.data,
            active=form.is_active.data
        )
        db.session.add(schedule)
        db.session.commit()
        flash('Orario di lavoro creato con successo', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'danger')
    
    return redirect(url_for('manage_work_schedules'))

@app.route('/admin/orari/edit/<int:schedule_id>', methods=['GET', 'POST'])
@login_required
def edit_work_schedule(schedule_id):
    """Modifica un orario di lavoro esistente"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per modificare orari', 'danger')
        return redirect(url_for('dashboard'))
    
    schedule = WorkSchedule.query.get_or_404(schedule_id)
    form = WorkScheduleForm(obj=schedule)
    
    # Precompila i campi basandosi sui dati esistenti
    if request.method == 'GET':
        # Precompila range orari
        form.start_time_min.data = schedule.start_time_min
        form.start_time_max.data = schedule.start_time_max
        form.end_time_min.data = schedule.end_time_min
        form.end_time_max.data = schedule.end_time_max
        
        # Precompila giorni della settimana
        form.days_of_week.data = schedule.days_of_week or [0, 1, 2, 3, 4]
        # Determina il preset basandosi sui giorni salvati
        if schedule.days_of_week == [0, 1, 2, 3, 4]:
            form.days_preset.data = 'workdays'
        elif schedule.days_of_week == [5, 6]:
            form.days_preset.data = 'weekend'
        elif schedule.days_of_week == [0, 1, 2, 3, 4, 5, 6]:
            form.days_preset.data = 'all_week'
        else:
            form.days_preset.data = 'custom'
    
    if form.validate_on_submit():
        # Determina i giorni della settimana dal preset o dalla selezione personalizzata
        if form.days_preset.data != 'custom':
            days_of_week = form.get_days_from_preset(form.days_preset.data)
        else:
            days_of_week = form.days_of_week.data
        
        schedule.sede_id = form.sede.data
        schedule.name = form.name.data
        schedule.start_time_min = form.start_time_min.data
        schedule.start_time_max = form.start_time_max.data
        schedule.end_time_min = form.end_time_min.data
        schedule.end_time_max = form.end_time_max.data
        # Aggiorna campi legacy per compatibilità
        schedule.start_time = form.start_time_min.data
        schedule.end_time = form.end_time_min.data
        schedule.days_of_week = days_of_week
        schedule.description = form.description.data
        schedule.active = form.is_active.data
        
        db.session.commit()
        flash(f'Orario "{schedule.name}" modificato con successo', 'success')
        return redirect(url_for('manage_work_schedules'))
    
    return render_template('edit_work_schedule.html', form=form, schedule=schedule)

@app.route('/admin/orari/toggle/<int:schedule_id>')
@login_required
def toggle_work_schedule(schedule_id):
    """Attiva/disattiva un orario di lavoro"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per modificare orari', 'danger')
        return redirect(url_for('dashboard'))
    
    schedule = WorkSchedule.query.get_or_404(schedule_id)
    schedule.active = not schedule.active
    db.session.commit()
    
    status = 'attivato' if schedule.active else 'disattivato'
    flash(f'Orario "{schedule.name}" {status} con successo', 'success')
    return redirect(url_for('manage_work_schedules'))

@app.route('/admin/orari/delete/<int:schedule_id>')
@login_required
def delete_work_schedule(schedule_id):
    """Elimina definitivamente un orario di lavoro"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per eliminare orari', 'danger')
        return redirect(url_for('dashboard'))
    
    schedule = WorkSchedule.query.get_or_404(schedule_id)
    schedule_name = schedule.name
    
    try:
        db.session.delete(schedule)
        db.session.commit()
        flash(f'Orario "{schedule_name}" eliminato definitivamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Errore durante l\'eliminazione. Potrebbero esistere dipendenze.', 'error')
        
    return redirect(url_for('manage_work_schedules'))


# GESTIONE RUOLI DINAMICI

@app.route('/admin/roles')
@login_required
def manage_roles():
    """Gestisce i ruoli dinamici del sistema (solo Admin)"""
    if not current_user.has_permission('can_manage_roles'):
        flash('Non hai i permessi per gestire i ruoli', 'danger')
        return redirect(url_for('dashboard'))
    
    roles = UserRole.query.order_by(UserRole.name).all()
    return render_template('manage_roles.html', roles=roles)


@app.route('/admin/roles/create', methods=['GET', 'POST'])
@login_required
def create_role():
    """Crea un nuovo ruolo dinamico"""
    if not current_user.has_permission('can_manage_roles'):
        flash('Non hai i permessi per creare ruoli', 'danger')
        return redirect(url_for('dashboard'))
    
    form = RoleForm()
    if form.validate_on_submit():
        new_role = UserRole(
            name=form.name.data,
            display_name=form.display_name.data,
            description=form.description.data,
            permissions=form.get_permissions_dict(),
            active=form.is_active.data
        )
        
        db.session.add(new_role)
        db.session.commit()
        
        flash(f'Ruolo "{form.display_name.data}" creato con successo', 'success')
        return redirect(url_for('manage_roles'))
    
    return render_template('create_role.html', form=form)


@app.route('/admin/roles/edit/<int:role_id>', methods=['GET', 'POST'])
@login_required
def edit_role(role_id):
    """Modifica un ruolo esistente"""
    if not current_user.has_permission('can_manage_roles'):
        flash('Non hai i permessi per modificare ruoli', 'danger')
        return redirect(url_for('dashboard'))
    
    role = UserRole.query.get_or_404(role_id)
    
    # Verifica che non sia un ruolo di sistema protetto
    protected_roles = ['Admin', 'Project Manager', 'Management']
    if role.name in protected_roles:
        flash(f'Il ruolo "{role.display_name}" è protetto e non può essere modificato', 'danger')
        return redirect(url_for('manage_roles'))
    
    form = RoleForm(original_name=role.name)
    
    if form.validate_on_submit():
        role.name = form.name.data
        role.display_name = form.display_name.data
        role.description = form.description.data
        role.permissions = form.get_permissions_dict()
        role.active = form.is_active.data
        
        db.session.commit()
        
        flash(f'Ruolo "{form.display_name.data}" modificato con successo', 'success')
        return redirect(url_for('manage_roles'))
    
    # Popola il form con i dati esistenti
    form.name.data = role.name
    form.display_name.data = role.display_name
    form.description.data = role.description
    form.is_active.data = role.active
    form.populate_permissions(role.permissions)
    
    return render_template('edit_role.html', form=form, role=role)


@app.route('/admin/roles/toggle/<int:role_id>')
@login_required
def toggle_role(role_id):
    """Attiva/disattiva un ruolo"""
    if not current_user.has_permission('can_manage_roles'):
        flash('Non hai i permessi per modificare ruoli', 'danger')
        return redirect(url_for('dashboard'))
    
    role = UserRole.query.get_or_404(role_id)
    
    # Verifica che non sia un ruolo di sistema protetto
    protected_roles = ['Admin', 'Project Manager', 'Management']
    if role.name in protected_roles:
        flash(f'Non è possibile disattivare il ruolo "{role.display_name}" perché è protetto dal sistema', 'danger')
        return redirect(url_for('manage_roles'))
    
    role.active = not role.active
    db.session.commit()
    
    status = 'attivato' if role.active else 'disattivato'
    flash(f'Ruolo "{role.display_name}" {status} con successo', 'success')
    return redirect(url_for('manage_roles'))


@app.route('/admin/roles/delete/<int:role_id>')
@login_required
def delete_role(role_id):
    """Elimina un ruolo (solo se non ci sono utenti associati)"""
    if not current_user.has_permission('can_manage_roles'):
        flash('Non hai i permessi per eliminare ruoli', 'danger')
        return redirect(url_for('dashboard'))
    
    role = UserRole.query.get_or_404(role_id)
    
    # Verifica che non sia un ruolo di sistema protetto
    protected_roles = ['Admin', 'Project Manager', 'Management']
    if role.name in protected_roles:
        flash(f'Non è possibile eliminare il ruolo "{role.display_name}" perché è protetto dal sistema', 'danger')
        return redirect(url_for('manage_roles'))
    
    # Verifica che non ci siano utenti con questo ruolo
    users_with_role = User.query.filter_by(role=role.name).count()
    if users_with_role > 0:
        flash(f'Impossibile eliminare il ruolo "{role.display_name}": ci sono {users_with_role} utenti associati', 'danger')
        return redirect(url_for('manage_roles'))
    
    role_name = role.display_name
    db.session.delete(role)
    db.session.commit()
    
    flash(f'Ruolo "{role_name}" eliminato con successo', 'success')
    return redirect(url_for('manage_roles'))
