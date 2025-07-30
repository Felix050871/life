from flask import render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, date, timedelta, time
import re
import qrcode
from io import BytesIO, StringIO
import base64
import json
from defusedcsv import csv
from urllib.parse import urlparse, urljoin
from app import app, db, csrf
from config import get_config
from sqlalchemy.orm import joinedload
from models import User, AttendanceEvent, LeaveRequest, LeaveType, Shift, ShiftTemplate, ReperibilitaShift, ReperibilitaTemplate, ReperibilitaIntervention, Intervention, Sede, WorkSchedule, UserRole, PresidioCoverage, PresidioCoverageTemplate, ReperibilitaCoverage, Holiday, PasswordResetToken, italian_now, get_active_presidio_templates, get_presidio_coverage_for_day
from forms import LoginForm, UserForm, AttendanceForm, LeaveRequestForm, LeaveTypeForm, ShiftForm, ShiftTemplateForm, SedeForm, WorkScheduleForm, RoleForm, PresidioCoverageTemplateForm, PresidioCoverageForm, PresidioCoverageSearchForm, ForgotPasswordForm, ResetPasswordForm
from utils import generate_shifts_for_period, get_user_statistics, get_team_statistics, format_hours, check_user_schedule_with_permissions

# Inject configuration into all templates
@app.context_processor
def inject_config():
    config = get_config()
    return dict(config=config)

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
    # Verifica permessi di accesso alla dashboard
    if not current_user.can_access_dashboard():
        flash('Non hai i permessi per accedere alla dashboard.', 'danger')
        return redirect(url_for('login'))
    
    stats = get_user_statistics(current_user.id)
    
    # Widget statistics team (solo per utenti autorizzati)
    team_stats = None
    if current_user.can_view_team_stats_widget():
        team_stats = get_team_statistics()
    
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
    if current_user.can_view_attendance() and not current_user.has_role('Amministratore'):
        user_status, _ = AttendanceEvent.get_user_status(current_user.id, today_date)
        today_events = AttendanceEvent.get_daily_events(current_user.id, today_date)
        today_work_hours = AttendanceEvent.get_daily_work_hours(current_user.id, today_date)
    
    # Get presidio coverage templates for shifts widget
    upcoming_shifts = []
    if current_user.can_view_shifts():
        # Show active presidio coverage templates
        upcoming_shifts = PresidioCoverageTemplate.query.filter_by(is_active=True).order_by(PresidioCoverageTemplate.start_date.desc()).all()
    
    # Get upcoming reperibilità shifts for authorized users
    upcoming_reperibilita_shifts = []
    active_intervention = None
    recent_interventions = []
    current_time = italian_now().time()
    if current_user.can_view_reperibilita():
        # Show active reperibilità coverage grouped by period
        upcoming_reperibilita_shifts = db.session.query(ReperibilitaCoverage)\
            .filter(ReperibilitaCoverage.is_active == True)\
            .order_by(ReperibilitaCoverage.start_date.desc())\
            .all()
        
        # Group by period (start_date, end_date) to avoid duplicates
        coverage_periods = {}
        for coverage in upcoming_reperibilita_shifts:
            period_key = (coverage.start_date, coverage.end_date)
            if period_key not in coverage_periods:
                coverage_periods[period_key] = {
                    'start_date': coverage.start_date,
                    'end_date': coverage.end_date,
                    'description': coverage.description,
                    'sedi_names': coverage.get_sedi_names(),
                    'coverage_count': 0
                }
            coverage_periods[period_key]['coverage_count'] += 1
        
        # Convert to list for template
        upcoming_reperibilita_shifts = list(coverage_periods.values())
        
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
    
    # Get recent leave requests for widget
    recent_leaves = []
    if current_user.can_view_leave_requests_widget():
        if current_user.can_manage_leave() or current_user.can_approve_leave():
            # Managers see all requests
            recent_leaves = LeaveRequest.query.order_by(LeaveRequest.created_at.desc()).limit(10).all()
        else:
            # Regular users see only their own
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
    

    
    # Add personal attendance data for PM
    if current_user.can_manage_users() and current_user.can_view_attendance():
        # Get manager's personal attendance data (same as regular users)
        user_status = AttendanceEvent.get_user_status(current_user.id)
        today_events = AttendanceEvent.get_daily_events(current_user.id, today_date)
        today_work_hours = AttendanceEvent.get_daily_work_hours(current_user.id, today_date)


    # Widget data for daily attendance by sede
    daily_attendance_data = {}
    if current_user.can_view_daily_attendance_widget():
        from collections import defaultdict
        attendance_by_sede = defaultdict(lambda: {'present_users': [], 'total_users': 0, 'coverage_rate': 0})
        
        # Get today's attendance events grouped by sede
        today_attendances = AttendanceEvent.query.filter_by(date=date.today()).all()
        present_user_ids = set()
        
        for attendance in today_attendances:
            if attendance.event_type == 'clock_in':
                present_user_ids.add(attendance.user_id)
            elif attendance.event_type == 'clock_out':
                present_user_ids.discard(attendance.user_id)
        
        # Group present users by sede
        if present_user_ids:
            present_users = User.query.filter(User.id.in_(present_user_ids)).all()
            for user in present_users:
                sede_name = user.get_sede_name()
                attendance_by_sede[sede_name]['present_users'].append(user)
        
        # Calculate totals per sede
        accessible_sedi = current_user.get_accessible_sedi() if hasattr(current_user, 'get_accessible_sedi') else []
        for sede in accessible_sedi:
            total_sede_users = User.query.filter_by(sede_id=sede.id, active=True).count()
            present_count = len(attendance_by_sede[sede.name]['present_users'])
            attendance_by_sede[sede.name]['total_users'] = total_sede_users
            attendance_by_sede[sede.name]['coverage_rate'] = (present_count / total_sede_users * 100) if total_sede_users > 0 else 0
        
        daily_attendance_data = dict(attendance_by_sede)
    
    # Widget data for shifts coverage alerts
    shifts_coverage_alerts = []
    if current_user.can_view_shifts_coverage_widget():
        # Get today's shifts with missing coverage
        today_shifts = Shift.query.filter_by(date=date.today()).all()
        for shift in today_shifts:
            if not shift.user_id:  # Uncovered shift
                shifts_coverage_alerts.append({
                    'shift': shift,
                    'alert_type': 'uncovered',
                    'message': f'Turno {shift.start_time.strftime("%H:%M")}-{shift.end_time.strftime("%H:%M")} non coperto'
                })
    
    # Widget data for team management quick access
    team_management_data = {}
    if current_user.can_view_team_management_widget():
        # Get quick stats about team
        # Usa il metodo helper per filtrare automaticamente per sede
        visible_users_query = User.get_visible_users_query(current_user)
        total_team_members = visible_users_query.filter_by(active=True).count()
        pending_users = visible_users_query.filter_by(active=False).count()
        recent_additions = visible_users_query.order_by(User.id.desc()).limit(3).all()
        
        team_management_data = {
            'total_members': total_team_members,
            'pending_users': pending_users,
            'recent_additions': recent_additions,
            'is_multi_sede': current_user.all_sedi
        }

    # Ottieni dati per i nuovi widget personali
    my_leave_requests = []
    my_shifts = []
    my_reperibilita = []
    
    if current_user.can_view_my_leave_requests_widget():
        my_leave_requests = LeaveRequest.query.filter_by(user_id=current_user.id).order_by(LeaveRequest.created_at.desc()).limit(5).all()
    
    if current_user.can_view_my_shifts_widget():
        from datetime import datetime
        from zoneinfo import ZoneInfo
        italy_tz = ZoneInfo('Europe/Rome')
        today_dt = datetime.now(italy_tz).date()
        my_shifts = Shift.query.filter_by(user_id=current_user.id).filter(Shift.date >= today_dt).order_by(Shift.date.asc()).limit(5).all()
    
    if current_user.can_view_my_reperibilita_widget():
        my_reperibilita = ReperibilitaShift.query.filter_by(user_id=current_user.id).order_by(ReperibilitaShift.date.desc()).limit(5).all()
    
    # Widget Note Spese
    expense_reports_data = None
    if current_user.can_view_expense_reports_widget():
        from models import ExpenseReport
        
        # Query base per le note spese
        expense_query = ExpenseReport.query
        
        # Se l'utente non può vedere tutte le note spese, mostra solo le sue
        if not (current_user.can_view_expense_reports() or current_user.can_approve_expense_reports()):
            expense_query = expense_query.filter(ExpenseReport.employee_id == current_user.id)
        elif not current_user.all_sedi and current_user.sede_id:
            # Filtra per sede se non ha accesso globale
            sede_users = User.query.filter(User.sede_id == current_user.sede_id).with_entities(User.id).all()
            sede_user_ids = [u.id for u in sede_users]
            expense_query = expense_query.filter(ExpenseReport.employee_id.in_(sede_user_ids))
        
        # Statistiche note spese
        total_expenses = expense_query.count()
        pending_expenses = expense_query.filter(ExpenseReport.status == 'pending').count()
        approved_expenses = expense_query.filter(ExpenseReport.status == 'approved').count()
        rejected_expenses = expense_query.filter(ExpenseReport.status == 'rejected').count()
        
        # Note spese recenti (ultime 5)
        recent_expenses = expense_query.order_by(ExpenseReport.expense_date.desc()).limit(5).all()
        
        # Total importo note spese approvate del mese corrente
        current_month_start = date.today().replace(day=1)
        monthly_total_query = db.session.query(db.func.sum(ExpenseReport.amount)).filter(
            ExpenseReport.status == 'approved',
            ExpenseReport.expense_date >= current_month_start
        )
        
        if not current_user.all_sedi and current_user.sede_id:
            sede_users = User.query.filter(User.sede_id == current_user.sede_id).with_entities(User.id).all()
            sede_user_ids = [u.id for u in sede_users]
            monthly_total_query = monthly_total_query.filter(ExpenseReport.employee_id.in_(sede_user_ids))
        
        monthly_total = monthly_total_query.scalar() or 0
        
        expense_reports_data = {
            'total_expenses': total_expenses,
            'pending_expenses': pending_expenses,
            'approved_expenses': approved_expenses,
            'rejected_expenses': rejected_expenses,
            'recent_expenses': recent_expenses,
            'monthly_total': monthly_total
        }

    return render_template('dashboard.html', 
                         stats=stats, 
                         team_stats=team_stats,
                         today_attendance=today_attendance,
                         upcoming_shifts=upcoming_shifts,
                         team_management_data=team_management_data,
                         upcoming_reperibilita_shifts=upcoming_reperibilita_shifts,
                         active_intervention=active_intervention,
                         active_general_intervention=active_general_intervention,
                         recent_interventions=recent_interventions,
                         recent_leaves=recent_leaves,
                         weekly_calendar=weekly_calendar,
                         today=today,
                         today_date=today_date,
                         current_time=current_time,
                         user_status=user_status,
                         today_events=today_events,
                         today_work_hours=today_work_hours,
                         daily_attendance_data=daily_attendance_data,
                         shifts_coverage_alerts=shifts_coverage_alerts,
                         my_leave_requests=my_leave_requests,
                         my_shifts=my_shifts,
                         my_reperibilita=my_reperibilita,
                         expense_reports_data=expense_reports_data,
                         format_hours=format_hours)

@app.route('/dashboard_team')
@login_required
def dashboard_team():
    """Dashboard per visualizzare le presenze di tutte le sedi - per Management"""
    if not current_user.can_view_all_attendance():
        flash('Non hai i permessi per visualizzare questo contenuto.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get users visible to current user based on sede access
    all_users = User.get_visible_users_query(current_user).filter(User.active == True).all()
    
    # Get all active sedi
    all_sedi = Sede.query.filter(Sede.active == True).all()
    
    # Parametri di visualizzazione
    period_mode = request.args.get('period', 'today')
    export_format = request.args.get('export')
    
    # Calcolo periodo di visualizzazione
    today = date.today()
    
    if period_mode == 'week':
        # Settimana corrente (lunedì-domenica)
        days_until_monday = today.weekday()
        start_date = today - timedelta(days=days_until_monday)
        end_date = start_date + timedelta(days=6)
        period_label = f"Settimana {start_date.strftime('%d/%m')} - {end_date.strftime('%d/%m/%Y')}"
    elif period_mode == 'month':
        # Mese corrente
        start_date = today.replace(day=1)
        next_month = start_date.replace(month=start_date.month + 1) if start_date.month < 12 else start_date.replace(year=start_date.year + 1, month=1)
        end_date = next_month - timedelta(days=1)
        period_label = f"Mese {start_date.strftime('%B %Y')}"
    else:  # today
        start_date = end_date = today
        period_label = f"Oggi {today.strftime('%d/%m/%Y')}"
    
    # Get attendance data for the period
    attendance_data = {}
    
    for user in all_users:
        if period_mode == 'today':
            status, last_event = AttendanceEvent.get_user_status(user.id, today)
            daily_summary = AttendanceEvent.get_daily_summary(user.id, today)
            
            # Check for approved leave requests
            leave_request = LeaveRequest.query.filter(
                LeaveRequest.user_id == user.id,
                LeaveRequest.status == 'Approved',
                LeaveRequest.start_date <= today,
                LeaveRequest.end_date >= today
            ).first()
            
            attendance_data[user.id] = {
                'user': user,
                'status': status,
                'last_event': last_event,
                'daily_summary': daily_summary,
                'leave_request': leave_request
            }
        else:
            # Per settimana/mese, calcola statistiche aggregate
            total_hours = 0
            total_days = 0
            current_date = start_date
            
            while current_date <= end_date:
                daily_summary = AttendanceEvent.get_daily_summary(user.id, current_date)
                if daily_summary and daily_summary.get('total_work_hours', 0) > 0:
                    total_hours += daily_summary['total_work_hours']
                    total_days += 1
                current_date += timedelta(days=1)
            
            attendance_data[user.id] = {
                'user': user,
                'total_hours': total_hours,
                'total_days': total_days,
                'avg_hours_per_day': total_hours / total_days if total_days > 0 else 0
            }
    
    # Handle export
    if export_format == 'csv':
        return generate_attendance_csv_export(attendance_data, period_mode, period_label, all_sedi)
    
    return render_template('dashboard_team.html',
                         all_users=all_users,
                         all_sedi=all_sedi,
                         attendance_data=attendance_data,
                         today=today,
                         period_mode=period_mode,
                         period_label=period_label,
                         start_date=start_date,
                         end_date=end_date,
                         current_user=current_user)

def generate_attendance_csv_export(attendance_data, period_mode, period_label, all_sedi):
    """Genera export CSV delle presenze"""
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Report Presenze - ' + period_label])
    writer.writerow([])  # Riga vuota
    
    if period_mode == 'today':
        writer.writerow(['Utente', 'Ruolo', 'Sede', 'Stato', 'Entrata', 'Uscita', 'Ore Lavorate', 'Note'])
        
        for user_id, data in attendance_data.items():
            user = data['user']
            sede_name = user.sede.name if user.sede else 'N/A'
            
            if data['leave_request']:
                stato = f"In {data['leave_request'].type}"
                entrata = uscita = ore_lavorate = 'N/A'
                note = data['leave_request'].reason or ''
            elif data['status'] == 'in':
                stato = 'Presente'
                entrata = data['last_event'].timestamp.strftime('%H:%M') if data['last_event'] and data['last_event'].event_type == 'clock_in' else 'N/A'
                uscita = 'In corso'
                ore_lavorate = format_hours(data['daily_summary'].get('total_work_hours', 0)) if data['daily_summary'] else '0h'
                note = data['last_event'].notes if data['last_event'] and data['last_event'].notes else ''
            elif data['status'] == 'out':
                stato = 'Assente'
                entrata = uscita = 'N/A'
                ore_lavorate = format_hours(data['daily_summary'].get('total_work_hours', 0)) if data['daily_summary'] else '0h'
                note = data['last_event'].notes if data['last_event'] and data['last_event'].notes else ''
            else:
                stato = 'Non registrato'
                entrata = uscita = ore_lavorate = 'N/A'
                note = ''
            
            writer.writerow([
                user.get_full_name(),
                user.role.name if user.role else 'N/A',
                sede_name,
                stato,
                entrata,
                uscita,
                ore_lavorate,
                note
            ])
    else:
        writer.writerow(['Utente', 'Ruolo', 'Sede', 'Ore Totali', 'Giorni Lavorati', 'Media Ore/Giorno'])
        
        for user_id, data in attendance_data.items():
            user = data['user']
            sede_name = user.sede.name if user.sede else 'N/A'
            
            writer.writerow([
                user.get_full_name(),
                user.role.name if user.role else 'N/A',
                sede_name,
                format_hours(data['total_hours']),
                data['total_days'],
                format_hours(data['avg_hours_per_day'])
            ])
    
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename="presenze_{period_mode}_{datetime.now().strftime("%Y%m%d")}.csv"'
    
    return response

@app.route('/dashboard_sede')
@login_required
def dashboard_sede():
    """Dashboard per visualizzare le presenze della propria sede - per Responsabili"""
    if not current_user.can_view_sede_attendance():
        flash('Non hai i permessi per visualizzare questo contenuto.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get users from the same sede (esclusi Admin e Management)
    sede_users = User.query.filter(
        User.sede_id == current_user.sede_id,
        User.active == True,
        ~User.role.in_(['Admin', 'Staff'])
    ).all()
    
    # Get attendance data for today
    today = date.today()
    today_attendance = {}
    
    for user in sede_users:
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
    
    # Get current user's sede
    current_sede = current_user.sede_obj
    
    return render_template('dashboard_sede.html',
                         sede_users=sede_users,
                         current_sede=current_sede,
                         today_attendance=today_attendance,
                         today=today,
                         current_user=current_user)

@app.route('/ente-home')
@login_required
def ente_home():
    """Home page per gestori team con vista team e navigazione settimanale"""
    if not (current_user.can_manage_users() or current_user.can_view_all_attendance()):
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
            ~User.role.in_(['Ente', 'Admin', 'Staff'])
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
    
    if current_user.role == 'Management':
        user_status, last_event = AttendanceEvent.get_user_status(current_user.id)
        today_events = AttendanceEvent.get_daily_events(current_user.id, today_date)
        today_work_hours = AttendanceEvent.get_daily_work_hours(current_user.id, today_date)
    
    # Get shifts and intervention data for PM
    upcoming_reperibilita_shifts = []
    active_intervention = None
    recent_interventions = []
    
    if current_user.role == 'Management':
        
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
        return jsonify({
            'success': False, 
            'message': 'Non hai i permessi per registrare presenze.'
        }), 403
        
    app.logger.error(f"CLOCK_IN: User {current_user.id} attempting clock-in")
    
    # Verifica se può fare clock-in
    if not AttendanceEvent.can_perform_action(current_user.id, 'clock_in'):
        status, _ = AttendanceEvent.get_user_status(current_user.id)
        if status == 'in':
            return jsonify({
                'success': False, 
                'message': 'Sei già presente. Devi prima registrare l\'uscita.'
            }), 400
        elif status == 'break':
            return jsonify({
                'success': False, 
                'message': 'Sei in pausa. Devi prima terminare la pausa.'
            }), 400
    
    # Usa l'orario italiano invece di UTC
    from zoneinfo import ZoneInfo
    italy_tz = ZoneInfo('Europe/Rome')
    today = datetime.now(italy_tz).date()
    
    # Verifica se ha richieste ferie/permessi/malattia approvate per oggi
    from models import LeaveRequest
    approved_leave = LeaveRequest.query.filter(
        LeaveRequest.user_id == current_user.id,
        LeaveRequest.start_date <= today,
        LeaveRequest.end_date >= today,
        LeaveRequest.status == 'Approved'
    ).first()
    
    if approved_leave:
        leave_type_display = {
            'Ferie': 'ferie',
            'Permesso': 'permesso', 
            'Malattia': 'malattia'
        }.get(approved_leave.leave_type, approved_leave.leave_type.lower())
        
        return jsonify({
            'success': False, 
            'message': f'Hai una richiesta di {leave_type_display} approvata per oggi ({approved_leave.start_date.strftime("%d/%m/%Y")} - {approved_leave.end_date.strftime("%d/%m/%Y")}). Devi prima cancellare la richiesta di {leave_type_display} se vuoi registrare la presenza.'
        }), 400
    
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
        app.logger.info(f"CLOCK_IN: Event created successfully at {now}")
        return jsonify({
            'success': True, 
            'message': f'Entrata registrata alle {now.strftime("%H:%M")}'
        })
    except Exception as e:
        app.logger.error(f"CLOCK_IN: Database commit failed: {e}")
        db.session.rollback()
        return jsonify({
            'success': False, 
            'message': 'Errore nel salvare l\'entrata'
        }), 500

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
        return jsonify({
            'success': False, 
            'message': 'Non hai i permessi per registrare presenze.'
        }), 403
        
    # Verifica se può fare clock-out
    if not AttendanceEvent.can_perform_action(current_user.id, 'clock_out'):
        status, _ = AttendanceEvent.get_user_status(current_user.id)
        if status == 'out':
            return jsonify({
                'success': False, 
                'message': 'Non sei presente. Devi prima registrare l\'entrata.'
            }), 400
    
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
        return jsonify({
            'success': True, 
            'message': f'Uscita registrata alle {now.strftime("%H:%M")}'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False, 
            'message': 'Errore nel salvare l\'uscita'
        }), 500

@app.route('/break_start', methods=['POST'])
@login_required
def break_start():
    if not current_user.can_access_attendance():
        return jsonify({
            'success': False, 
            'message': 'Non hai i permessi per registrare presenze.'
        }), 403
        
    # Verifica se può iniziare la pausa
    if not AttendanceEvent.can_perform_action(current_user.id, 'break_start'):
        status, _ = AttendanceEvent.get_user_status(current_user.id)
        if status == 'out':
            return jsonify({
                'success': False, 
                'message': 'Non sei presente. Devi prima registrare l\'entrata.'
            }), 400
        elif status == 'break':
            return jsonify({
                'success': False, 
                'message': 'Sei già in pausa.'
            }), 400
    
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
        return jsonify({
            'success': True, 
            'message': f'Pausa iniziata alle {now.strftime("%H:%M")}'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False, 
            'message': 'Errore nel salvare l\'inizio pausa'
        }), 500

@app.route('/break_end', methods=['POST'])
@login_required
def break_end():
    if not current_user.can_access_attendance():
        return jsonify({
            'success': False, 
            'message': 'Non hai i permessi per registrare presenze.'
        }), 403
        
    # Verifica se può terminare la pausa
    if not AttendanceEvent.can_perform_action(current_user.id, 'break_end'):
        status, _ = AttendanceEvent.get_user_status(current_user.id)
        if status == 'out':
            return jsonify({
                'success': False, 
                'message': 'Non sei presente.'
            }), 400
        elif status == 'in':
            return jsonify({
                'success': False, 
                'message': 'Non sei in pausa.'
            }), 400
    
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
        return jsonify({
            'success': True, 
            'message': f'Pausa terminata alle {now.strftime("%H:%M")}'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False, 
            'message': 'Errore nel salvare la fine pausa'
        }), 500

@app.route('/attendance', methods=['GET', 'POST'])
@login_required
def attendance():
    # Controllo permessi di accesso alle presenze
    view_mode = request.args.get('view', 'personal')
    
    # Controllo specifico per vista sede
    if view_mode == 'sede' and not current_user.can_view_sede_attendance():
        flash('Non hai i permessi per visualizzare le presenze della sede.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Controllo generale per accesso alle presenze
    if not current_user.can_access_attendance():
        flash('Non hai i permessi per accedere alla gestione presenze.', 'danger')
        return redirect(url_for('dashboard'))
    
    form = AttendanceForm()
    
    # Ottieni stato attuale dell'utente e eventi di oggi (solo se non è Ente o Staff)
    if current_user.role not in ['Ente', 'Staff']:
        user_status, last_event = AttendanceEvent.get_user_status(current_user.id)
        today_events = AttendanceEvent.get_daily_events(current_user.id)
        today_work_hours = AttendanceEvent.get_daily_work_hours(current_user.id)
    else:
        # Ente e Staff non hanno dati personali di presenza
        user_status, last_event = 'out', None
        today_events = []
        today_work_hours = 0
    
    # Blocca POST per utenti Ente e Staff (solo visualizzazione)
    if request.method == 'POST' and form.validate_on_submit() and current_user.role not in ['Ente', 'Staff']:
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
    
    # Handle team/personal view toggle for PM, Management, Responsabili, Ente and Staff
    view_mode = request.args.get('view', 'personal')
    if current_user.role in ['Management'] and current_user.can_view_all_attendance():
        # Management può scegliere vista personale o team
        show_team_data = (view_mode == 'team')
    elif current_user.role in ['Ente', 'Staff']:
        # Ente e Staff vedono sempre e solo dati team
        show_team_data = True
        view_mode = 'team'
    elif current_user.can_view_sede_attendance() and view_mode == 'sede':
        # Utenti con permesso "Visualizzare Presenze Sede" possono vedere presenze della propria sede
        show_team_data = True
        view_mode = 'sede'
    else:
        # Altri utenti vedono solo dati personali
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
        # Get team attendance data for PM, Management, Responsabili and Ente
        if current_user.role == 'Staff':
            # Staff vede tutti gli utenti di tutte le sedi (esclusi Admin e Staff)
            team_users = User.query.filter(
                User.active.is_(True),
                ~User.role.in_(['Admin', 'Staff'])
            ).all()
        elif current_user.role == 'Management':
            # Management vedono solo utenti della propria sede (esclusi Admin e Staff)
            team_users = User.query.filter(
                User.sede_id == current_user.sede_id,
                User.active.is_(True),
                ~User.role.in_(['Admin', 'Staff'])
            ).all()
        elif view_mode == 'sede':
            # Utenti con permessi visualizzazione sede
            if current_user.all_sedi:
                # Utenti multi-sede vedono tutti gli utenti attivi di tutte le sedi
                team_users = User.query.filter(
                    User.active.is_(True),
                    ~User.role.in_(['Admin', 'Staff'])
                ).all()
            elif current_user.sede_id:
                # Utenti sede-specifica vedono solo utenti della propria sede
                team_users = User.query.filter(
                    User.sede_id == current_user.sede_id,
                    User.active.is_(True),
                    ~User.role.in_(['Admin', 'Staff'])
                ).all()
            else:
                team_users = []
        else:
            # PM e Ente vedono solo utenti operativi (esclusi Admin e Staff)
            team_users = User.query.filter(
                User.role.in_(['Redattore', 'Sviluppatore', 'Operatore', 'Management', 'Staff']),
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
            
            # Calcola indicatori di ENTRATA solo se l'utente ha un orario che richiede controlli
            if hasattr(record, 'clock_in') and record.clock_in and record.user.should_check_attendance_timing():
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
            
            # Calcola indicatori di USCITA solo se l'utente ha un orario che richiede controlli
            if hasattr(record, 'clock_out') and record.clock_out and record.user.should_check_attendance_timing():
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
    
    # Determina gli utenti per cui cercare le richieste di ferie
    if show_team_data:
        # Per vista team, cerca ferie di tutti gli utenti del team
        target_user_ids = [user.id for user in team_users]
    else:
        # Per vista personale, solo l'utente corrente
        target_user_ids = [current_user.id]
    
    if target_user_ids:
        # Cerca richieste di ferie approvate nel periodo per tutti gli utenti target
        approved_leaves = LeaveRequest.query.filter(
            LeaveRequest.user_id.in_(target_user_ids),
            LeaveRequest.status == 'Approved',
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date
        ).all()
        
        for leave in approved_leaves:
            current_date = max(leave.start_date, start_date)
            while current_date <= min(leave.end_date, end_date):
                # Verifica se esiste già un record di presenza per questa data e utente
                existing_record = any(
                    r.date == current_date and getattr(r, 'user_id', None) == leave.user_id 
                    for r in event_records + old_records
                )
                
                if not existing_record:
                    # Crea un record per la giornata di ferie/permesso/malattia
                    class LeaveRecord:
                        def __init__(self, date, leave_type, reason, user_id, leave_request):
                            self.date = date
                            self.break_start = None
                            self.break_end = None
                            self.notes = f"{leave_type}: {reason}" if reason else leave_type
                            self.user_id = user_id
                            self.user = User.query.get(user_id)
                            self.shift_status = leave_type.lower()  # 'ferie', 'permesso', 'malattia'
                            self.exit_status = 'normale'
                            self.leave_type = leave_type
                            self.leave_reason = reason
                            
                            # Determina orari in base al tipo di assenza
                            if leave_type.lower() == 'permesso' and hasattr(leave_request, 'start_time') and leave_request.start_time:
                                # Per i permessi usa gli orari specifici della richiesta - converti in datetime italiano
                                from datetime import datetime
                                from zoneinfo import ZoneInfo
                                
                                if isinstance(leave_request.start_time, datetime):
                                    # Se è già datetime, assicurati che sia in fuso italiano
                                    if leave_request.start_time.tzinfo is None:
                                        # Assumi UTC se non ha timezone
                                        utc_time = leave_request.start_time.replace(tzinfo=ZoneInfo('UTC'))
                                        self.clock_in = utc_time.astimezone(ZoneInfo('Europe/Rome'))
                                    else:
                                        self.clock_in = leave_request.start_time.astimezone(ZoneInfo('Europe/Rome'))
                                else:
                                    # Se è time, combinalo con la data corrente in fuso italiano
                                    self.clock_in = datetime.combine(self.date, leave_request.start_time, ZoneInfo('Europe/Rome'))
                                
                                if hasattr(leave_request, 'end_time') and leave_request.end_time:
                                    if isinstance(leave_request.end_time, datetime):
                                        if leave_request.end_time.tzinfo is None:
                                            utc_time = leave_request.end_time.replace(tzinfo=ZoneInfo('UTC'))
                                            self.clock_out = utc_time.astimezone(ZoneInfo('Europe/Rome'))
                                        else:
                                            self.clock_out = leave_request.end_time.astimezone(ZoneInfo('Europe/Rome'))
                                    else:
                                        self.clock_out = datetime.combine(self.date, leave_request.end_time, ZoneInfo('Europe/Rome'))
                                else:
                                    self.clock_out = None
                            else:
                                # Per ferie e malattie usa orari standard di lavoro dell'utente
                                from models import WorkSchedule
                                from datetime import datetime, time
                                user_schedule = None
                                if self.user.work_schedule_id:
                                    user_schedule = WorkSchedule.query.get(self.user.work_schedule_id)
                                
                                if user_schedule:
                                    # Usa orari standard del turno - converti time in datetime italiano
                                    from zoneinfo import ZoneInfo
                                    self.clock_in = datetime.combine(self.date, user_schedule.start_time_min, ZoneInfo('Europe/Rome'))
                                    self.clock_out = datetime.combine(self.date, user_schedule.end_time_max, ZoneInfo('Europe/Rome'))
                                else:
                                    # Fallback a orari generici 9-17 - converti in datetime italiano
                                    from zoneinfo import ZoneInfo
                                    self.clock_in = datetime.combine(self.date, time(9, 0), ZoneInfo('Europe/Rome'))
                                    self.clock_out = datetime.combine(self.date, time(17, 0), ZoneInfo('Europe/Rome'))
                        
                        def get_work_hours(self):
                            return 0  # Nessuna ora lavorata durante ferie/permessi
                        
                        def get_attendance_indicators(self):
                            return {'entry': None, 'exit': None}
                    
                    leave_records.append(LeaveRecord(
                        date=current_date,
                        leave_type=leave.leave_type,
                        reason=leave.reason,
                        user_id=leave.user_id,
                        leave_request=leave
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
    
    # Organizza i record per sede per utenti multi-sede in modalità team
    records_by_sede = {}
    all_sedi_list = []
    if show_team_data and current_user.all_sedi and view_mode == 'sede':
        from collections import defaultdict
        from models import Sede
        
        # Ottieni tutte le sedi attive
        all_sedi_list = Sede.query.filter_by(active=True).order_by(Sede.name).all()
        records_by_sede = {sede.name: [] for sede in all_sedi_list}
        
        # Aggiungi anche una categoria per utenti senza sede
        records_by_sede['Nessuna Sede'] = []
        
        # Distribuisci i record per sede
        for record in records:
            if hasattr(record, 'user') and record.user:
                sede_name = record.user.sede_obj.name if record.user.sede_obj else 'Nessuna Sede'
                if sede_name in records_by_sede:
                    records_by_sede[sede_name].append(record)
        
        # Rimuovi "Nessuna Sede" se vuota
        if not records_by_sede['Nessuna Sede']:
            del records_by_sede['Nessuna Sede']
    
    return render_template('attendance.html', 
                         form=form, 
                         records=records,
                         records_by_sede=records_by_sede,
                         all_sedi_list=all_sedi_list,
                         today_date=date.today(),
                         start_date=start_date.strftime('%Y-%m-%d'),
                         end_date=end_date.strftime('%Y-%m-%d'),
                         user_status=user_status,
                         today_events=today_events,
                         today_work_hours=today_work_hours,
                         view_mode=view_mode,
                         show_team_data=show_team_data,
                         is_multi_sede=current_user.all_sedi)

@app.route('/turni_automatici')
@login_required
def turni_automatici():
    """Sistema nuovo: Creazione automatica turni da template presidio"""
    if not (current_user.can_manage_shifts() or current_user.can_view_shifts()):
        flash('Non hai i permessi per accedere ai turni', 'danger')
        return redirect(url_for('dashboard'))
    
    # Ottieni template presidio attivi per creazione turni
    from models import PresidioCoverageTemplate
    presidio_templates = PresidioCoverageTemplate.query.filter_by(is_active=True).order_by(
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
                    ).order_by(Shift.date.asc(), Shift.start_time.asc()).all()  # Ordine crescente
                else:
                    shifts = []
                
                # Raggruppa turni per settimana
                turni_per_settimana = defaultdict(list)
                settimane_stats = {}
                
                for shift in shifts:
                    # Calcola inizio settimana (lunedì)
                    settimana_inizio = shift.date - timedelta(days=shift.date.weekday())
                    settimana_fine = settimana_inizio + timedelta(days=6)
                    settimana_key = settimana_inizio.strftime('%Y-%m-%d')
                    
                    turni_per_settimana[settimana_key].append(shift)
                    
                    # Calcola statistiche settimana
                    if settimana_key not in settimane_stats:
                        settimane_stats[settimana_key] = {
                            'inizio': settimana_inizio,
                            'fine': settimana_fine,
                            'total_hours': 0,
                            'unique_users': set(),
                            'shift_count': 0
                        }
                    
                    settimane_stats[settimana_key]['total_hours'] += shift.get_duration_hours()
                    settimane_stats[settimana_key]['unique_users'].add(shift.user_id)
                    settimane_stats[settimana_key]['shift_count'] += 1
                
                # Converti set in count e ordina per data
                for stats in settimane_stats.values():
                    stats['unique_users'] = len(stats['unique_users'])
                
                # Ordina settimane per data crescente
                settimane_stats = dict(sorted(settimane_stats.items(), key=lambda x: x[1]['inizio']))
                turni_per_settimana = dict(sorted(turni_per_settimana.items(), key=lambda x: x[0]))
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

@app.route('/api/get_shifts_for_template/<int:template_id>')
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
        
        # Crea struttura dati per JSON
        for settimana_key in sorted(turni_per_settimana.keys()):
            settimana_inizio = date.fromisoformat(settimana_key)
            settimana_fine = settimana_inizio + timedelta(days=6)
            turni_settimana = turni_per_settimana[settimana_key]
            
            # Statistiche settimana
            total_hours = sum(shift.get_duration_hours() for shift in turni_settimana)
            unique_users = len(set(shift.user_id for shift in turni_settimana))
            
            # Giorni della settimana
            days = []
            for day_num in range(7):
                day_date = settimana_inizio + timedelta(days=day_num)
                day_shifts = [shift for shift in turni_settimana if shift.date == day_date]
                
                shifts_data = []
                for shift in day_shifts:
                    shifts_data.append({
                        'id': shift.id,
                        'user': shift.user.get_full_name(),
                        'user_id': shift.user.id,
                        'role': shift.user.role if isinstance(shift.user.role, str) else (shift.user.role.name if shift.user.role else 'Senza ruolo'),
                        'time': f"{shift.start_time.strftime('%H:%M')}-{shift.end_time.strftime('%H:%M')}"
                    })
                
                days.append({
                    'date': day_date.strftime('%d/%m'),
                    'shifts': shifts_data
                })
            
            weeks_data.append({
                'start': settimana_inizio.strftime('%d/%m/%Y'),
                'end': settimana_fine.strftime('%d/%m/%Y'),
                'shift_count': len(turni_settimana),
                'unique_users': unique_users,
                'total_hours': total_hours,
                'days': days
            })
        
        return jsonify({
            'success': True,
            'period': template.get_period_display(),
            'weeks': weeks_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/visualizza_turni')
@login_required
def visualizza_turni():
    """Visualizza turni - Solo visualizzazione senza generazione"""
    if not current_user.can_view_shifts():
        flash('Non hai i permessi per visualizzare i turni', 'danger')
        return redirect(url_for('dashboard'))
    
    # Ottieni template presidio attivi
    from models import PresidioCoverageTemplate
    presidio_templates = PresidioCoverageTemplate.query.filter_by(is_active=True).order_by(
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
                    ).order_by(Shift.date.asc(), Shift.start_time.asc()).all()  # Ordine crescente
                else:
                    shifts = []
                
                # Raggruppa turni per settimana
                turni_per_settimana = defaultdict(list)
                settimane_stats = {}
                
                for shift in shifts:
                    # Calcola inizio settimana (lunedì)
                    settimana_inizio = shift.date - timedelta(days=shift.date.weekday())
                    settimana_fine = settimana_inizio + timedelta(days=6)
                    settimana_key = settimana_inizio.strftime('%Y-%m-%d')
                    
                    turni_per_settimana[settimana_key].append(shift)
                    
                    # Calcola statistiche settimana
                    if settimana_key not in settimane_stats:
                        settimane_stats[settimana_key] = {
                            'inizio': settimana_inizio,
                            'fine': settimana_fine,
                            'total_hours': 0,
                            'unique_users': set(),
                            'shift_count': 0
                        }
                    
                    settimane_stats[settimana_key]['total_hours'] += shift.get_duration_hours()
                    settimane_stats[settimana_key]['unique_users'].add(shift.user_id)
                    settimane_stats[settimana_key]['shift_count'] += 1
                
                # Converti set in count e ordina per data
                for stats in settimane_stats.values():
                    stats['unique_users'] = len(stats['unique_users'])
                
                # Ordina settimane per data crescente
                settimane_stats = dict(sorted(settimane_stats.items(), key=lambda x: x[1]['inizio']))
                turni_per_settimana = dict(sorted(turni_per_settimana.items(), key=lambda x: x[0]))
        except (ValueError, TypeError):
            pass
    
    # Ottieni utenti disponibili per statistiche
    from collections import defaultdict  
    users_by_role = defaultdict(list)
    available_users = User.query.filter(
        User.active.is_(True)
    ).all()
    
    for user in available_users:
        if hasattr(user, 'role') and user.role:
            users_by_role[user.role].append(user)
    
    from datetime import date, timedelta
    return render_template('visualizza_turni.html', 
                         presidio_templates=presidio_templates,
                         selected_template=selected_template,
                         turni_per_settimana=turni_per_settimana,
                         settimane_stats=settimane_stats,
                         users_by_role=dict(users_by_role),
                         shifts=shifts,
                         today=date.today(),
                         timedelta=timedelta)

@app.route('/genera_turni_da_template', methods=['POST'])
@login_required
def genera_turni_da_template():
    """Genera turni automaticamente da template presidio"""
    if not current_user.can_manage_shifts():
        flash('Non hai i permessi per creare turni', 'danger')
        return redirect(url_for('turni_automatici'))
    
    template_id = request.form.get('template_id')
    force_regenerate = request.form.get('force_regenerate') == 'true'
    
    if not template_id:
        flash('Seleziona un template per la generazione turni', 'danger')
        return redirect(url_for('turni_automatici'))
    
    try:
        from datetime import datetime, timedelta
        from models import PresidioCoverageTemplate, PresidioCoverage, Shift, User
        import json
        import random
        
        # Ottieni template e usa le sue date
        template = PresidioCoverageTemplate.query.get_or_404(template_id)
        start_date = template.start_date
        end_date = template.end_date
        
        # Ottieni coperture del template
        coverages = PresidioCoverage.query.filter_by(
            template_id=template_id,
            is_active=True
        ).all()
        
        if not coverages:
            flash('Il template selezionato non ha coperture configurate', 'warning')
            return redirect(url_for('turni_automatici'))
        
        # Controlla se esistono già turni per questo template nel periodo futuro
        from datetime import date
        today = date.today()
        future_start_date = max(start_date, today)
        
        existing_shifts = Shift.query.filter(
            Shift.date >= future_start_date,
            Shift.date <= end_date
        ).count()
        
        if existing_shifts > 0 and not force_regenerate:
            # Mostra conferma rigenerazione
            return render_template('confirm_regenerate_shifts.html',
                                 template=template,
                                 existing_shifts=existing_shifts,
                                 start_date=future_start_date,
                                 end_date=end_date)
        
        # Se force_regenerate è True, cancella i turni esistenti futuri
        if force_regenerate and existing_shifts > 0:
            deleted_shifts = Shift.query.filter(
                Shift.date >= future_start_date,
                Shift.date <= end_date
            ).delete()
            db.session.commit()
            flash(f'Cancellati {deleted_shifts} turni esistenti per rigenerazione', 'info')
        
        # Controllo preventivo della disponibilità di utenti per tutti i ruoli richiesti
        insufficient_coverage_warnings = []
        for coverage in coverages:
            try:
                required_roles = json.loads(coverage.required_roles) if coverage.required_roles else []
                
                # Controlla la disponibilità per ogni ruolo richiesto separatamente
                for role in required_roles:
                    from models import WorkSchedule
                    available_users_for_role = User.query.join(WorkSchedule, User.work_schedule_id == WorkSchedule.id).filter(
                        User.active.is_(True),
                        User.role == role,  # Controlla ogni ruolo singolarmente
                        WorkSchedule.name == 'Turni'
                    ).all()
                    
                    if len(available_users_for_role) == 0:
                        day_names = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
                        warning_msg = f"{day_names[coverage.day_of_week]} {coverage.start_time}-{coverage.end_time}: NESSUN utente disponibile per ruolo '{role}'"
                        insufficient_coverage_warnings.append(warning_msg)
                    elif len(available_users_for_role) < coverage.role_count:
                        day_names = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
                        warning_msg = f"{day_names[coverage.day_of_week]} {coverage.start_time}-{coverage.end_time}: ruolo '{role}' richiede {coverage.role_count} utenti, disponibili solo {len(available_users_for_role)}"
                        insufficient_coverage_warnings.append(warning_msg)
                        
            except json.JSONDecodeError:
                continue
        
        if insufficient_coverage_warnings:
            flash('ATTENZIONE - Problemi di copertura rilevati:', 'warning')
            for warning in insufficient_coverage_warnings:
                flash(f'• {warning}', 'warning')
        
        turni_creati = 0
        current_date = start_date
        
        while current_date <= end_date:
            # Ottieni giorno della settimana (0 = lunedì)
            day_of_week = current_date.weekday()
            
            # Trova coperture per questo giorno
            day_coverages = [c for c in coverages if c.day_of_week == day_of_week]
            
            for coverage in day_coverages:
                try:
                    # Parsing ruoli richiesti
                    required_roles = json.loads(coverage.required_roles) if coverage.required_roles else []
                    
                    # Trova utenti disponibili per questi ruoli - solo con orario "Turni"
                    from models import WorkSchedule
                    available_users = User.query.join(WorkSchedule, User.work_schedule_id == WorkSchedule.id).filter(
                        User.active.is_(True),
                        User.role.in_(required_roles),
                        WorkSchedule.name == 'Turni'  # Solo utenti con orario speciale "Turni"
                    ).all()
                    
                    if len(available_users) < coverage.role_count:
                        # Usa tutti gli utenti disponibili se insufficienti
                        selected_users = available_users
                    else:
                        # Seleziona casualmente il numero richiesto
                        selected_users = random.sample(available_users, coverage.role_count)
                    
                    if not selected_users:
                        continue
                    

                    
                    # Crea turni per ogni utente selezionato
                    for user in selected_users:
                        # Controlla se esiste già un turno per questo utente in questa data/ora
                        existing_shift = Shift.query.filter_by(
                            user_id=user.id,
                            date=current_date,
                            start_time=coverage.start_time
                        ).first()
                        
                        if not existing_shift:
                            new_shift = Shift(
                                user_id=user.id,
                                date=current_date,
                                start_time=coverage.start_time,
                                end_time=coverage.end_time,
                                shift_type='presidio',
                                created_by=current_user.id
                            )
                            db.session.add(new_shift)
                            turni_creati += 1
                
                except json.JSONDecodeError:
                    continue
            
            current_date += timedelta(days=1)
        
        db.session.commit()
        flash(f'Creati {turni_creati} turni dal template "{template.name}"', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante la generazione turni: {str(e)}', 'danger')
    
    return redirect(url_for('turni_automatici'))

@app.route('/create_shift', methods=['POST'])
@login_required
def create_shift():
    if not current_user.can_manage_shifts():
        flash('Non hai i permessi per creare turni', 'danger')
        return redirect(url_for('manage_turni'))
    
    # Check if user's sede supports turni mode
    if not current_user.sede_obj or not current_user.sede_obj.is_turni_mode():
        flash('La tua sede non supporta la modalità turni', 'warning')
        return redirect(url_for('manage_turni'))
    
    form = ShiftForm()
    # Solo utenti con orario "Turni" possono essere assegnati ai turni
    # Escludi solo ruoli amministrativi (Amministratore)
    workers = User.query.join(WorkSchedule, User.work_schedule_id == WorkSchedule.id, isouter=True).filter(
        User.role != 'Amministratore',
        User.active.is_(True),
        WorkSchedule.name == 'Turni'
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
                return redirect(url_for('manage_turni'))
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
    
    return redirect(url_for('manage_turni'))

@app.route('/generate_shifts', methods=['POST'])
@login_required
def generate_shifts():
    if not current_user.can_manage_shifts():
        flash('Non hai i permessi per generare turni', 'danger')
        return redirect(url_for('manage_turni'))
    
    # Check if user's sede supports turni mode
    if not current_user.sede_obj or not current_user.sede_obj.is_turni_mode():
        flash('La tua sede non supporta la modalità turni', 'warning')
        return redirect(url_for('manage_turni'))
    
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
    
    return redirect(url_for('manage_turni'))

@app.route('/regenerate_template/<int:template_id>', methods=['POST'])
@login_required
def regenerate_template(template_id):
    if not current_user.can_manage_shifts():
        flash('Non hai i permessi per rigenerare turni', 'danger')
        return redirect(url_for('manage_turni'))
    
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
    
    return redirect(url_for('manage_turni'))

@app.route('/delete_template/<int:template_id>', methods=['POST'])
@login_required
def delete_template(template_id):
    if not current_user.can_manage_shifts():
        flash('Non hai i permessi per eliminare template', 'danger')
        return redirect(url_for('manage_turni'))
    
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
    return redirect(url_for('manage_turni'))

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
        
        # Populate user choices for shift form - solo utenti con orario "Turni"
        # Escludi solo ruoli amministrativi (Amministratore)
        workers = User.query.join(WorkSchedule, User.work_schedule_id == WorkSchedule.id, isouter=True).filter(
            User.role != 'Amministratore',
            User.active.is_(True),
            WorkSchedule.name == 'Turni'
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

# Route per gestione tipologie permessi
@app.route('/leave_types')
@login_required
def leave_types():
    if not current_user.can_manage_leave_types():
        flash('Non hai i permessi per gestire le tipologie di permesso', 'danger')
        return redirect(url_for('dashboard'))
    
    leave_types = LeaveType.query.order_by(LeaveType.name).all()
    return render_template('leave_types.html', leave_types=leave_types)

@app.route('/leave_types/add', methods=['GET', 'POST'])
@login_required
def add_leave_type_page():
    if not current_user.can_manage_leave_types():
        flash('Non hai i permessi per aggiungere tipologie di permesso', 'danger')
        return redirect(url_for('leave_types'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            requires_approval = 'requires_approval' in request.form
            is_active = 'is_active' in request.form
            
            # Verifica duplicati
            if LeaveType.query.filter_by(name=name).first():
                flash('Esiste già una tipologia con questo nome', 'warning')
                return render_template('add_leave_type.html')
            
            leave_type = LeaveType(
                name=name,
                description=description,
                requires_approval=requires_approval,
                is_active=is_active
            )
            
            db.session.add(leave_type)
            db.session.commit()
            flash(f'Tipologia "{name}" creata con successo', 'success')
            return redirect(url_for('leave_types'))
        except Exception as e:
            db.session.rollback()
            flash('Errore nella creazione della tipologia', 'danger')
            return render_template('add_leave_type.html')
    
    # GET request - mostra form di creazione
    return render_template('add_leave_type.html')

@app.route('/leave_types/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_leave_type_page(id):
    if not current_user.can_manage_leave_types():
        flash('Non hai i permessi per modificare tipologie di permesso', 'danger')
        return redirect(url_for('leave_types'))
    
    leave_type = LeaveType.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            
            # Verifica duplicati (escludendo il record corrente)
            existing = LeaveType.query.filter(LeaveType.name == name, LeaveType.id != id).first()
            if existing:
                flash('Esiste già una tipologia con questo nome', 'warning')
                return render_template('edit_leave_type.html', leave_type=leave_type)
            
            leave_type.name = name
            leave_type.description = request.form.get('description')
            leave_type.requires_approval = 'requires_approval' in request.form
            leave_type.is_active = 'is_active' in request.form
            leave_type.updated_at = italian_now()
            
            db.session.commit()
            flash(f'Tipologia "{name}" aggiornata con successo', 'success')
            return redirect(url_for('leave_types'))
        except Exception as e:
            db.session.rollback()
            flash('Errore nell\'aggiornamento della tipologia', 'danger')
            return render_template('edit_leave_type.html', leave_type=leave_type)
    
    # GET request - mostra form di modifica
    return render_template('edit_leave_type.html', leave_type=leave_type)

@app.route('/leave_types/<int:id>/delete', methods=['POST'])
@login_required
def delete_leave_type(id):
    if not current_user.can_manage_leave_types():
        flash('Non hai i permessi per eliminare tipologie di permesso', 'danger')
        return redirect(url_for('leave_types'))
    
    leave_type = LeaveType.query.get_or_404(id)
    
    # Verifica che non ci siano richieste associate
    if leave_type.leave_requests.count() > 0:
        flash('Non è possibile eliminare una tipologia con richieste associate', 'warning')
        return redirect(url_for('leave_types'))
    
    try:
        name = leave_type.name
        db.session.delete(leave_type)
        db.session.commit()
        flash(f'Tipologia "{name}" eliminata con successo', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Errore nell\'eliminazione della tipologia', 'danger')
    
    return redirect(url_for('leave_types'))

@app.route('/leave_requests')
@login_required
def leave_requests():
    form = LeaveRequestForm()
    
    if current_user.can_approve_leave():
        if current_user.role == 'Responsabili':
            # Responsabili vedono solo le richieste della propria sede
            requests = LeaveRequest.query.join(User, LeaveRequest.user_id == User.id).filter(
                User.sede_id == current_user.sede_id
            ).order_by(LeaveRequest.created_at.desc()).all()
        else:
            # Project managers e Management vedono tutte le richieste
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

@app.route('/create_leave_request', methods=['GET', 'POST'])
@login_required
def create_leave_request_page():
    if not current_user.can_request_leave():
        flash('Non hai i permessi per richiedere ferie/permessi', 'danger')
        return redirect(url_for('leave_requests'))
    
    form = LeaveRequestForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        # Ottieni la tipologia di permesso selezionata
        leave_type = LeaveType.query.get(form.leave_type_id.data)
        if not leave_type or not leave_type.is_active:
            flash('Tipologia di permesso non valida', 'danger')
            return redirect(url_for('leave_requests'))
        
        # Determina la data di fine in base al tipo
        end_date = form.end_date.data if form.end_date.data else form.start_date.data
        
        # Check for overlapping requests
        overlapping = None
        
        # Controlla sovrapposizioni esistenti
        if form.start_time.data and form.end_time.data:
            # Per permessi orari, controlla sovrapposizione oraria nella stessa giornata
            existing_requests = LeaveRequest.query.filter(
                LeaveRequest.user_id == current_user.id,
                LeaveRequest.status.in_(['Pending', 'Approved']),
                LeaveRequest.start_date == form.start_date.data,  # Stessa giornata
                LeaveRequest.start_time.isnot(None),  # Solo permessi orari
                LeaveRequest.end_time.isnot(None)
            ).all()
            
            # Controlla sovrapposizione oraria
            for existing in existing_requests:
                if not (form.end_time.data <= existing.start_time or 
                       form.start_time.data >= existing.end_time):
                    overlapping = existing
                    break
        else:
            # Per ferie e permessi giornalieri, controllo sovrapposizioni per date
            overlapping = LeaveRequest.query.filter(
                LeaveRequest.user_id == current_user.id,
                LeaveRequest.status.in_(['Pending', 'Approved']),
                LeaveRequest.start_date <= end_date,
                LeaveRequest.end_date >= form.start_date.data
            ).first()
        
        if overlapping:
            if overlapping.start_time and overlapping.end_time:
                flash(f'Hai già un permesso sovrapposto dalle {overlapping.start_time.strftime("%H:%M")} alle {overlapping.end_time.strftime("%H:%M")} in questa giornata', 'warning')
            else:
                flash('Hai già una richiesta sovrapposta in questo periodo', 'warning')
        else:
            leave_request = LeaveRequest(
                user_id=current_user.id,
                leave_type_id=leave_type.id,
                start_date=form.start_date.data,
                end_date=end_date,
                reason=form.reason.data,
                leave_type=leave_type.name  # Manteniamo per retrocompatibilità
            )
            
            # Auto-approva se la tipologia non richiede autorizzazione o se l'utente può auto-approvarsi
            if not leave_type.requires_approval or current_user.can_approve_leave():
                leave_request.status = 'Approved'
                leave_request.approved_by = current_user.id  # Self-approved
                leave_request.approved_at = italian_now()
            else:
                leave_request.status = 'Pending'
            
            # Aggiungi orari se specificati
            if form.start_time.data and form.end_time.data:
                leave_request.start_time = form.start_time.data
                leave_request.end_time = form.end_time.data
            
            db.session.add(leave_request)
            db.session.commit()
            
            # Invia messaggi automatici
            from utils import send_leave_request_message
            send_leave_request_message(leave_request, 'created', current_user)
            
            # Messaggio di successo personalizzato
            if not leave_type.requires_approval:
                flash(f'Richiesta di {leave_type.name.lower()} approvata automaticamente', 'success')
            elif current_user.can_approve_leave():
                flash(f'Richiesta di {leave_type.name.lower()} approvata automaticamente', 'success')
            else:
                duration = leave_request.get_duration_display()
                flash(f'Richiesta di {leave_type.name.lower()} inviata con successo ({duration})', 'success')
            return redirect(url_for('leave_requests'))
    else:
        # Errori di validazione
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'danger')
    
    # GET request - mostra form di creazione
    return render_template('create_leave_request.html', 
                         form=form,
                         today=date.today())

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
    
    # Invia messaggio di approvazione all'utente richiedente
    from utils import send_leave_request_message
    send_leave_request_message(leave_request, 'approved', current_user)
    
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
    
    # Invia messaggio di rifiuto all'utente richiedente
    from utils import send_leave_request_message
    send_leave_request_message(leave_request, 'rejected', current_user)
    
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
    
    # Verifica che la richiesta non sia già approvata E che non sia futura
    from zoneinfo import ZoneInfo
    italy_tz = ZoneInfo('Europe/Rome')
    today = datetime.now(italy_tz).date()
    
    if leave_request.status == 'Approved' and leave_request.start_date < today:
        flash('Non puoi cancellare richieste già approvate e iniziate', 'warning')
        return redirect(url_for('leave_requests'))
    
    # Invia messaggi di cancellazione prima di eliminare la richiesta
    from utils import send_leave_request_message
    send_leave_request_message(leave_request, 'cancelled', current_user)
    
    # Cancella la richiesta
    db.session.delete(leave_request)
    db.session.commit()
    flash('Richiesta cancellata con successo', 'success')
    
    # Determina dove reindirizzare in base al referer
    referer = request.headers.get('Referer', '')
    if 'dashboard' in referer or referer.endswith('/'):
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('leave_requests'))

@app.route('/users')
@login_required
def users():
    if not (current_user.can_manage_users() or current_user.can_view_users()):
        flash('Non hai i permessi per accedere agli utenti', 'danger')
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
            all_sedi=form.all_sedi.data,
            sede_id=form.sede.data if not form.all_sedi.data else None,
            work_schedule_id=form.work_schedule.data,
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
    if not (current_user.can_manage_users() or current_user.can_view_users()):
        flash('Non hai i permessi per accedere alla gestione utenti', 'danger')
        return redirect(url_for('dashboard'))
    
    # Applica filtro automatico per sede usando il metodo helper
    users_query = User.get_visible_users_query(current_user).options(joinedload(User.sede_obj))
    users = users_query.order_by(User.created_at.desc()).all()
    
    # Determina il nome della sede per il titolo
    sede_name = None if current_user.all_sedi else (current_user.sede_obj.name if current_user.sede_obj else None)
    form = UserForm(is_edit=False)
    
    return render_template('user_management.html', users=users, form=form, 
                         sede_name=sede_name, is_multi_sede=current_user.all_sedi)



@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if not current_user.can_manage_users():
        flash('Non hai i permessi per modificare gli utenti', 'danger')
        return redirect(url_for('user_management'))
    
    user = User.query.get_or_404(user_id)
    form = UserForm(original_username=user.username, is_edit=True, obj=user)
    
    if request.method == 'GET':
        # Popola i campi sede e all_sedi con i valori attuali
        form.all_sedi.data = user.all_sedi
        if user.sede_id:
            form.sede.data = user.sede_id
        
        if user.work_schedule_id:
            # Aggiungi l'orario corrente alle scelte se non già presente
            if user.work_schedule:
                schedule_choice = (user.work_schedule.id, f"{user.work_schedule.name} ({user.work_schedule.start_time.strftime('%H:%M') if user.work_schedule.start_time else ''}-{user.work_schedule.end_time.strftime('%H:%M') if user.work_schedule.end_time else ''})")
                if schedule_choice not in form.work_schedule.choices:
                    form.work_schedule.choices.append(schedule_choice)
            form.work_schedule.data = user.work_schedule_id
        else:
            # Se non ha un orario, imposta il valore di default
            form.work_schedule.data = ''
    
    if form.validate_on_submit():
        # Impedisce la disattivazione dell'amministratore
        if user.role == 'Amministratore' and not form.is_active.data:
            flash('Non è possibile disattivare l\'utente amministratore', 'danger')
            return render_template('edit_user.html', form=form, user=user)
        
        user.username = form.username.data
        user.email = form.email.data
        user.role = form.role.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.all_sedi = form.all_sedi.data
        user.sede_id = form.sede.data if not form.all_sedi.data else None
        user.work_schedule_id = form.work_schedule.data
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
    
    # Impedisce la disattivazione dell'amministratore
    if user.role == 'Amministratore':
        flash('Non è possibile disattivare l\'utente amministratore', 'danger')
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
    
    # Get user statistics for all active users (excluding Amministratore and Ospite)
    users = User.query.filter_by(active=True).filter(~User.role.in_(['Amministratore', 'Ospite'])).all()
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
    active_user_ids = [user.id for user in User.query.filter(User.active.is_(True)).filter(~User.role.in_(['Amministratore', 'Ospite'])).all()]
    
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
    """Gestione festività"""
    if not (current_user.can_manage_holidays() or current_user.can_view_holidays()):
        flash('Non hai i permessi per accedere alle festività', 'danger')
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
    if not current_user.can_access_turni():
        flash('Non hai i permessi per modificare turni', 'danger')
        return redirect(url_for('dashboard'))
    
    shift = Shift.query.get_or_404(shift_id)
    
    # Check if shift is in the future or today
    if shift.date < date.today():
        flash('Non è possibile modificare turni passati', 'warning')
        return redirect(url_for('manage_turni'))
    
    # Verifica permessi sulla sede (se non admin)
    if current_user.role != 'Admin':
        if not current_user.sede_obj or current_user.sede_obj.id != shift.user.sede_id:
            flash('Non hai i permessi per modificare turni per questa sede', 'danger')
            return redirect(url_for('dashboard'))
        # Verifica che la sede sia di tipo "Turni" per utenti non-admin
        if not current_user.sede_obj.is_turni_mode():
            flash('La modifica turni è disponibile solo per sedi di tipo "Turni"', 'warning')
            return redirect(url_for('dashboard'))
    
    from forms import EditShiftForm
    form = EditShiftForm()
    
    # Get available users for assignment (only from the same sede as the shift)
    users = User.query.filter(
        User.role.in_(['Management', 'Redattore', 'Sviluppatore', 'Operatore']),
        User.active.is_(True),
        User.sede_id == shift.user.sede_id
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
                
                # Aggiorna il turno
                shift.user_id = form.user_id.data
                shift.start_time = form.start_time.data
                shift.end_time = form.end_time.data
                
                db.session.commit()
                
                new_user = User.query.get(form.user_id.data)
                new_time = f"{form.start_time.data.strftime('%H:%M')} - {form.end_time.data.strftime('%H:%M')}"
                
                flash(f'Turno modificato con successo: {old_user} ({old_time}) → {new_user.get_full_name()} ({new_time})', 'success')
                
                # Redirect back to the referring page or dashboard
                return redirect(request.referrer or url_for('dashboard'))
                
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la modifica del turno: {str(e)}', 'danger')
    
    # Pre-popola il form con i dati esistenti
    if request.method == 'GET':
        form.user_id.data = shift.user_id
        form.start_time.data = shift.start_time
        form.end_time.data = shift.end_time
    
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
    if not current_user.can_view_shifts():
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
    if current_user.role not in ['Management']:
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
    """Lista coperture reperibilità"""
    if not current_user.can_access_reperibilita():
        flash('Non hai i permessi per visualizzare le coperture reperibilità', 'danger')
        return redirect(url_for('dashboard'))
    
    from models import ReperibilitaCoverage
    from collections import defaultdict
    
    # Raggruppa le coperture per periodo + sede per trattare duplicazioni come gruppi separati
    coverages = ReperibilitaCoverage.query.order_by(ReperibilitaCoverage.start_date.desc()).all()
    groups = defaultdict(lambda: {'coverages': [], 'start_date': None, 'end_date': None, 'creator': None, 'created_at': None})
    
    for coverage in coverages:
        # Include sede nel period_key per separare coperture duplicate con sedi diverse
        sede_ids = sorted(coverage.get_sedi_ids_list())
        sede_key = "_".join(map(str, sede_ids)) if sede_ids else "no_sede"
        period_key = f"{coverage.start_date.strftime('%Y-%m-%d')}_{coverage.end_date.strftime('%Y-%m-%d')}_{sede_key}"
        
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
    """Crea nuova copertura reperibilità"""
    if not current_user.can_manage_reperibilita():
        flash('Non hai i permessi per creare coperture reperibilità', 'danger')
        return redirect(url_for('dashboard'))
    
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
            coverage.set_sedi_ids_list(form.sedi.data)  # Aggiungi le sedi selezionate
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
    """Modifica copertura reperibilità"""
    if not current_user.can_manage_reperibilita():
        flash('Non hai i permessi per modificare coperture reperibilità', 'danger')
        return redirect(url_for('dashboard'))
    
    from forms import ReperibilitaCoverageForm
    from models import ReperibilitaCoverage
    
    coverage = ReperibilitaCoverage.query.get_or_404(coverage_id)
    form = ReperibilitaCoverageForm()
    
    if form.validate_on_submit():
        coverage.start_time = form.start_time.data
        coverage.end_time = form.end_time.data
        coverage.set_required_roles_list(form.required_roles.data)
        coverage.set_sedi_ids_list(form.sedi.data)  # Aggiungi le sedi selezionate
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
    """Elimina copertura reperibilità"""
    if not current_user.can_manage_reperibilita():
        flash('Non hai i permessi per eliminare coperture reperibilità', 'danger')
        return redirect(url_for('dashboard'))
    
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
    """Visualizza dettagli coperture reperibilità per un periodo"""
    if not current_user.can_access_reperibilita():
        flash('Non hai i permessi per visualizzare coperture reperibilità', 'danger')
        return redirect(url_for('dashboard'))
    
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
    """Elimina tutte le coperture reperibilità di un periodo"""
    if not current_user.can_manage_reperibilita():
        flash('Non hai i permessi per eliminare periodi reperibilità', 'danger')
        return redirect(url_for('dashboard'))
    
    from models import ReperibilitaCoverage, ReperibilitaShift
    
    # Decodifica period_key
    start_date_str, end_date_str = period_key.split('_')
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    # Trova tutte le coperture per questo periodo
    coverages = ReperibilitaCoverage.query.filter(
        ReperibilitaCoverage.start_date == start_date,
        ReperibilitaCoverage.end_date == end_date
    ).all()
    
    # Trova anche tutti i turni generati per questo periodo
    shifts = ReperibilitaShift.query.filter(
        ReperibilitaShift.date >= start_date,
        ReperibilitaShift.date <= end_date
    ).all()
    
    try:
        coverage_count = len(coverages)
        shift_count = len(shifts)
        
        # Elimina prima i turni, poi le coperture
        for shift in shifts:
            db.session.delete(shift)
        for coverage in coverages:
            db.session.delete(coverage)
            
        db.session.commit()
        flash(f'Eliminate {coverage_count} coperture reperibilità e {shift_count} turni del periodo {start_date.strftime("%d/%m/%Y")} - {end_date.strftime("%d/%m/%Y")}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante l\'eliminazione: {str(e)}', 'error')
    
    return redirect(url_for('reperibilita_shifts'))


@app.route('/reperibilita_shifts')
@require_login
def reperibilita_shifts():
    """Gestione turni reperibilità"""
    from models import ReperibilitaShift, ReperibilitaTemplate
    from datetime import datetime, timedelta
    from collections import defaultdict
    
    # Get current template list for generation (legacy - ora usiamo coperture) 
    templates = []  # Svuotato perché ora usiamo le coperture invece dei template
    
    # Parametri di visualizzazione basati sui permessi granulari
    if current_user.can_manage_reperibilita() or current_user.can_view_all_attendance():
        view_mode = request.args.get('view', 'all')
    else:
        view_mode = 'personal'  # Utenti normali vedono solo i propri
    
    period_mode = request.args.get('period', 'week')
    display_mode = request.args.get('display', 'table')
    
    # Calcolo periodo di visualizzazione con possibilità di navigazione
    today = italian_now().date()
    
    # Ottieni data di riferimento da parametri URL o usa oggi
    ref_date_param = request.args.get('date')
    if ref_date_param:
        try:
            ref_date = datetime.strptime(ref_date_param, '%Y-%m-%d').date()
        except:
            ref_date = today
    else:
        ref_date = today
    
    if period_mode == 'month':
        start_date = ref_date.replace(day=1)
        next_month = start_date.replace(month=start_date.month + 1) if start_date.month < 12 else start_date.replace(year=start_date.year + 1, month=1)
        end_date = next_month - timedelta(days=1)
        # Calcola navigazione mese precedente/successivo
        prev_month = start_date.replace(month=start_date.month - 1) if start_date.month > 1 else start_date.replace(year=start_date.year - 1, month=12)
        next_month_date = next_month
    else:  # week
        days_until_monday = ref_date.weekday()
        start_date = ref_date - timedelta(days=days_until_monday)
        end_date = start_date + timedelta(days=6)
        # Calcola navigazione settimana precedente/successiva
        prev_week = start_date - timedelta(days=7)
        next_week = start_date + timedelta(days=7)
    
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
    
    # Ma nascondiamo completamente la sezione template/coperture se ci sono turni generati
    hide_coverage_section = len(shifts) > 0
    
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
    if current_user.can_view_interventions():
        active_intervention = ReperibilitaIntervention.query.filter_by(
            user_id=current_user.id,
            end_datetime=None
        ).first()
    
    # Raggruppa i turni esistenti per periodo per mostrare i periodi generati
    from collections import OrderedDict
    shift_periods = OrderedDict()
    
    # Ottieni tutti i turni per creare i periodi
    all_shifts_query = ReperibilitaShift.query.order_by(ReperibilitaShift.date.asc()).all()
    
    for shift in all_shifts_query:
        # Raggruppa per settimana o periodo logico
        period_start = shift.date - timedelta(days=shift.date.weekday())  # Inizio settimana
        period_end = period_start + timedelta(days=6)  # Fine settimana
        period_key = f"{period_start}_{period_end}"
        
        if period_key not in shift_periods:
            shift_periods[period_key] = {
                'start_date': period_start,
                'end_date': period_end,
                'duration_days': (period_end - period_start).days + 1,
                'shifts': [],
                'unique_users': set(),
                'unique_sedi': set()
            }
        
        shift_periods[period_key]['shifts'].append(shift)
        shift_periods[period_key]['unique_users'].add(shift.user.get_full_name())
        if shift.user.sede_obj:
            shift_periods[period_key]['unique_sedi'].add(shift.user.sede_obj.name)
    
    # Converti sets in liste ordinate e aggiungi conteggi
    for period_data in shift_periods.values():
        period_data['unique_users'] = sorted(list(period_data['unique_users']))
        period_data['unique_sedi'] = sorted(list(period_data['unique_sedi']))
        period_data['total_shifts'] = len(period_data['shifts'])

    # Prepara dati di navigazione
    navigation = {}
    if period_mode == 'month':
        navigation['prev_date'] = prev_month
        navigation['next_date'] = next_month_date
        navigation['current_period'] = f"{start_date.strftime('%B %Y')}"
    else:  # week
        navigation['prev_date'] = prev_week
        navigation['next_date'] = next_week
        navigation['current_period'] = f"Settimana {start_date.strftime('%d/%m')} - {end_date.strftime('%d/%m/%Y')}"

    return render_template('reperibilita_shifts.html', 
                         shifts=shifts, 
                         templates=templates,
                         shift_periods=shift_periods,
                         shifts_by_day=shifts_by_day,
                         active_intervention=active_intervention,
                         calendar_days=calendar_days,
                         today_date=today,
                         current_time=current_time,
                         hide_coverage_section=hide_coverage_section,
                         navigation=navigation,
                         period_mode=period_mode,
                         view_mode=view_mode,
                         display_mode=display_mode)


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
    """Replica template reperibilità"""
    if not current_user.can_manage_reperibilita():
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
            
            # Gestisce il cambio di sede se specificato
            if form.sede_id.data:
                # Assegna la nuova sede specificata
                new_coverage.set_sedi_ids_list([int(form.sede_id.data)])
            else:
                # Mantiene le sedi originali
                new_coverage.set_sedi_ids_list(original_coverage.get_sedi_ids_list())
            
            db.session.add(new_coverage)
            new_coverages_count += 1
        
        try:
            db.session.commit()
            
            success_msg = f'Template reperibilità replicato con successo. Coperture create: {new_coverages_count}.'
            if role_mapping:
                success_msg += f' Ruoli sostituiti: {len(role_mapping)}.'
            if form.sede_id.data:
                from models import Sede
                sede = Sede.query.get(int(form.sede_id.data))
                success_msg += f' Sede cambiata in: {sede.name}.'
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
    """Genera turnazioni reperibilità"""
    if not current_user.can_manage_reperibilita():
        flash('Non hai i permessi per generare turni di reperibilità', 'danger')
        return redirect(url_for('dashboard'))
    
    from forms import ReperibilitaTemplateForm
    from models import ReperibilitaTemplate, ReperibilitaShift
    from utils import generate_reperibilita_shifts_from_coverage
    
    form = ReperibilitaTemplateForm()
    
    if form.validate_on_submit():
        # Verifica che sia stata selezionata una copertura
        if not form.coverage_period.data:
            flash('Seleziona una copertura reperibilità', 'error')
            return render_template('generate_reperibilita_shifts.html', form=form)
        
        # Determina le date da usare
        if form.use_full_period.data:
            # Usa le date della copertura - formato: start_date__end_date__sede_key
            parts = form.coverage_period.data.split('__')
            coverage_start = parts[0]
            coverage_end = parts[1]
            start_date = datetime.strptime(coverage_start, '%Y-%m-%d').date()
            end_date = datetime.strptime(coverage_end, '%Y-%m-%d').date()
        else:
            # Usa le date personalizzate
            start_date = form.start_date.data
            end_date = form.end_date.data
        
        # Elimina turni esistenti nel periodo
        existing_shifts = ReperibilitaShift.query.filter(
            ReperibilitaShift.date >= start_date,
            ReperibilitaShift.date <= end_date
        ).all()
        
        for shift in existing_shifts:
            db.session.delete(shift)
        
        try:
            import sys
            print(f"[DEBUG] Generazione turni per copertura: {form.coverage_period.data}", flush=True, file=sys.stderr)
            print(f"[DEBUG] Periodo: {start_date} - {end_date}", flush=True, file=sys.stderr)
            print(f"[DEBUG] Usa intero periodo: {form.use_full_period.data}", flush=True, file=sys.stderr)
            
            # Genera turni reperibilità dalla copertura selezionata
            shifts_created, warnings = generate_reperibilita_shifts_from_coverage(
                form.coverage_period.data,  # period_key della copertura
                start_date,
                end_date,
                current_user.id
            )
            
            print(f"[DEBUG] Risultato generazione: {shifts_created} turni, warnings: {warnings}", flush=True, file=sys.stderr)
            
            db.session.commit()
            print(f"[DEBUG] Commit completato", flush=True, file=sys.stderr)
            
            # Costruisci messaggio di successo con dettagli debug
            success_msg = f'Turni reperibilità generati: {shifts_created} per il periodo {start_date.strftime("%d/%m/%Y")} - {end_date.strftime("%d/%m/%Y")}.'
            
            if warnings:
                if len(warnings) <= 3:
                    warning_text = " Attenzione: " + "; ".join(warnings)
                else:
                    warning_text = f" Attenzione: {warnings[0]}; {warnings[1]}; {warnings[2]} e altri {len(warnings) - 3} avvisi."
                success_msg += warning_text
            
            flash(success_msg, 'success' if not warnings else 'warning')
            return redirect(url_for('reperibilita_shifts'))
            
        except Exception as e:
            import traceback
            import sys
            print(f"[ERROR] Errore durante generazione: {e}", flush=True, file=sys.stderr)
            print(f"[ERROR] Traceback: {traceback.format_exc()}", flush=True, file=sys.stderr)
            db.session.rollback()
            flash(f'Errore durante la generazione: {str(e)}', 'error')

    
    return render_template('generate_reperibilita_shifts.html', form=form)


@app.route('/reperibilita_shifts/regenerate/<int:template_id>', methods=['GET'])
@require_login
def regenerate_reperibilita_template(template_id):
    """Rigenera turni reperibilità da template esistente"""
    if not current_user.can_manage_reperibilita():
        flash('Non hai i permessi per rigenerare turni di reperibilità', 'danger')
        return redirect(url_for('dashboard'))
    
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
    if current_user.role not in ['Management', 'Operatore', 'Redattore', 'Sviluppatore']:
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
    if current_user.role not in ['Management', 'Operatore', 'Redattore', 'Sviluppatore']:
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
    if current_user.role == 'Management':
        return redirect(url_for('ente_home'))
    else:
        return redirect(url_for('reperibilita_shifts'))


@app.route('/reperibilita_template/delete/<template_id>')
@require_login
def delete_reperibilita_template(template_id):
    """Elimina un template reperibilità e tutti i suoi turni"""
    if not current_user.can_manage_reperibilita():
        flash('Non hai i permessi per eliminare template di reperibilità', 'danger')
        return redirect(url_for('dashboard'))
    
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
        return redirect(url_for('manage_turni'))
    
    # Handle team/personal view toggle for PM
    view_mode = request.args.get('view', 'personal')
    if current_user.role == 'Management':
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
            User.role.in_(['Redattore', 'Sviluppatore', 'Operatore', 'Management', 'Responsabili']),
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
    if current_user.role in ['Management', 'Ente']:
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
    if current_user.role in ['Management', 'Ente']:
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
    if current_user.role in ['Management', 'Ente']:
        header = ['Utente', 'Nome', 'Cognome', 'Ruolo', 'Data Inizio', 'Ora Inizio', 'Data Fine', 'Ora Fine', 
                 'Durata (minuti)', 'Priorità', 'Tipologia', 'Descrizione', 'Stato']
    else:
        header = ['Data Inizio', 'Ora Inizio', 'Data Fine', 'Ora Fine', 
                 'Durata (minuti)', 'Priorità', 'Tipologia', 'Descrizione', 'Stato']
    writer.writerow(header)
    
    # Dati
    for intervention in general_interventions:
        row = []
        
        if current_user.role in ['Management', 'Ente']:
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
    if current_user.role in ['Management', 'Ente']:
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
    if current_user.role in ['Management', 'Ente']:
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
        
        if current_user.role in ['Management', 'Ente']:
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
    """Gestione codici QR - Solo per chi può gestire"""
    if not current_user.can_manage_qr():
        flash('Non hai i permessi per gestire i codici QR', 'danger')
        return redirect(url_for('dashboard'))
    
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
                         static_qr_urls=static_qr_urls,
                         can_manage=True)


@app.route('/view/qr_codes')
@require_login
def view_qr_codes():
    """Visualizzazione codici QR - Solo per chi può visualizzare"""
    if not current_user.can_view_qr():
        flash('Non hai i permessi per visualizzare i codici QR', 'danger')
        return redirect(url_for('dashboard'))
    
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
    
    return render_template('view_qr_codes.html', 
                         qr_urls=qr_urls,
                         qr_exist=qr_exist,
                         static_qr_urls=static_qr_urls,
                         can_manage=False)

@app.route('/admin/generate_static_qr')
@require_login  
def generate_static_qr():
    """Genera QR code statici e li salva su file"""
    if not current_user.can_manage_qr():
        flash('Non hai i permessi per generare codici QR', 'danger')
        return redirect(url_for('dashboard'))
    
    from utils import generate_static_qr_codes
    
    if generate_static_qr_codes():
        flash('QR code generati con successo e salvati come file statici', 'success')
    else:
        flash('Errore nella generazione dei QR code statici', 'danger')
    
    # Forza refresh della pagina per mostrare i nuovi QR code
    return redirect(url_for('admin_generate_qr_codes') + '?refresh=1')


# ===============================
# GESTIONE TURNI PER SEDI
# ===============================

@app.route('/admin/turni')
@login_required
def manage_turni():
    """Gestione turni per sedi di tipo 'Turni'"""
    if not current_user.can_access_turni():
        flash('Non hai i permessi per accedere alla gestione turni', 'danger')
        return redirect(url_for('dashboard'))
    
    # Ottieni sedi turni accessibili dall'utente
    sedi_turni = current_user.get_turni_sedi()
    
    # Per ogni sede, calcola statistiche sui turni esistenti
    sede_stats = {}
    for sede in sedi_turni:
        from models import Shift, ReperibilitaShift
        
        turni_count = db.session.query(Shift).join(User, Shift.user_id == User.id).filter(
            User.sede_id == sede.id,
            User.active == True
        ).count()
        
        # Conta coperture attive per questa sede (usando PresidioCoverage temporaneamente)
        from models import PresidioCoverage
        coperture_count = PresidioCoverage.query.filter(
            PresidioCoverage.is_active == True
        ).count()
        
        sede_stats[sede.id] = {
            'turni_count': turni_count,
            'coperture_count': coperture_count,
            'users_count': len([u for u in sede.users if u.active])
        }
    
    return render_template('manage_turni.html', 
                         sedi_turni=sedi_turni, 
                         sede_stats=sede_stats,
                         can_manage_all=(current_user.can_manage_shifts()))

@app.route('/admin/turni/coverage/create', methods=['POST'])
@login_required
def create_shift_coverage():
    """Crea nuova copertura turni con supporto numerosità ruoli"""
    if not current_user.can_access_turni():
        flash('Non hai i permessi per creare coperture turni', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        # Ottieni dati dal form
        sede_id = request.form.get('sede_id')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        base_start_time = request.form.get('base_start_time')
        base_end_time = request.form.get('base_end_time')
        description = request.form.get('description', '')
        
        # Giorni selezionati
        days_of_week = request.form.getlist('days_of_week')
        
        # Estrai ruoli selezionati e numerosità
        roles_dict = {}
        # Cerca i campi role_count_ per determinare ruoli e numerosità
        for key in request.form.keys():
            if key.startswith('role_count_'):
                role_name = key.replace('role_count_', '')
                # Verifica se il checkbox corrispondente esiste ed è selezionato
                checkbox_found = False
                for checkbox_key in request.form.keys():
                    if checkbox_key.startswith('role_') and request.form.get(checkbox_key) == role_name:
                        checkbox_found = True
                        break
                
                if checkbox_found:
                    count = int(request.form.get(key, 1))
                    if count > 0:
                        roles_dict[role_name] = count
        
        if not roles_dict:
            flash('Devi selezionare almeno un ruolo con numerosità', 'danger')
            return redirect(url_for('manage_turni'))
        
        from models import PresidioCoverage
        from datetime import datetime, date
        
        # Converti date
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Converti orari  
        start_time_obj = datetime.strptime(base_start_time, '%H:%M').time()
        end_time_obj = datetime.strptime(base_end_time, '%H:%M').time()
        
        success_count = 0
        
        # Crea copertura per ogni giorno selezionato
        for day_str in days_of_week:
            day_of_week = int(day_str)
            
            # Controlla orari personalizzati per questo giorno
            custom_start_key = f'start_time_{day_of_week}'
            custom_end_key = f'end_time_{day_of_week}'
            
            day_start_time = start_time_obj
            day_end_time = end_time_obj
            
            if custom_start_key in request.form and custom_end_key in request.form:
                custom_start = request.form.get(custom_start_key)
                custom_end = request.form.get(custom_end_key)
                if custom_start and custom_end:
                    day_start_time = datetime.strptime(custom_start, '%H:%M').time()
                    day_end_time = datetime.strptime(custom_end, '%H:%M').time()
            
            # Crea la copertura
            coverage = PresidioCoverage(
                day_of_week=day_of_week,
                start_time=day_start_time,
                end_time=day_end_time,
                description=description,
                is_active=True,
                start_date=start_date_obj,
                end_date=end_date_obj,
                created_by=current_user.id
            )
            
            # Imposta ruoli con numerosità
            coverage.set_required_roles_dict(roles_dict)
            
            db.session.add(coverage)
            success_count += 1
        
        db.session.commit()
        
        if success_count > 0:
            total_resources = sum(roles_dict.values())
            flash(f'Copertura creata con successo per {success_count} giorni! Total risorse richieste per turno: {total_resources}', 'success')
        else:
            flash('Nessuna nuova copertura creata', 'warning')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante la creazione della copertura: {str(e)}', 'danger')
    
    return redirect(url_for('manage_turni'))

@app.route('/admin/turni/coperture')
@login_required
def view_turni_coverage():
    """Visualizza le coperture create per una sede specifica"""
    if not current_user.can_access_turni():
        flash('Non hai i permessi per visualizzare le coperture', 'danger')
        return redirect(url_for('dashboard'))
    
    sede_id = request.args.get('sede', type=int)
    if not sede_id:
        # Se l'utente non è Admin, usa la sua sede per default
        if current_user.role != 'Admin' and current_user.sede_obj and current_user.sede_obj.is_turni_mode():
            sede_id = current_user.sede_obj.id
        else:
            flash('ID sede non specificato. Seleziona una sede dalla pagina Gestione Turni.', 'warning')
            return redirect(url_for('manage_turni'))
    
    sede = Sede.query.get_or_404(sede_id)
    
    # Verifica permessi sulla sede - supporta utenti multi-sede
    if not current_user.can_manage_shifts() and not current_user.can_view_shifts():
        flash('Non hai i permessi per visualizzare le coperture', 'danger')
        return redirect(url_for('dashboard'))
    
    # Per utenti non-admin, verifica accesso alla sede specifica
    if not current_user.all_sedi and current_user.sede_obj and current_user.sede_obj.id != sede_id:
        flash('Non hai accesso a questa sede specifica', 'danger')
        return redirect(url_for('manage_turni'))
    
    if not sede.is_turni_mode():
        flash('La sede selezionata non è configurata per la modalità turni', 'warning')
        return redirect(url_for('manage_turni'))
    
    # Ottieni le coperture create per questa sede
    # Per ora prendiamo tutte le coperture attive - in futuro potremmo aggiungere un campo sede_id
    from models import PresidioCoverage
    coperture = PresidioCoverage.query.filter_by(is_active=True).order_by(
        PresidioCoverage.start_date.desc(),
        PresidioCoverage.day_of_week,
        PresidioCoverage.start_time
    ).all()
    
    # Raggruppa coperture per periodo di validità (evita duplicati)
    coperture_grouped = {}
    coperture_ids_seen = set()
    for copertura in coperture:
        # Evita duplicati
        if copertura.id in coperture_ids_seen:
            continue
        coperture_ids_seen.add(copertura.id)
        
        period_key = f"{copertura.start_date.strftime('%Y-%m-%d')} - {copertura.end_date.strftime('%Y-%m-%d')}"
        if period_key not in coperture_grouped:
            coperture_grouped[period_key] = {
                'start_date': copertura.start_date,
                'end_date': copertura.end_date,
                'coperture': [],
                'is_active': copertura.is_active and copertura.end_date >= date.today()
            }
        coperture_grouped[period_key]['coperture'].append(copertura)
    
    # Statistiche
    total_coperture = len(coperture)
    active_coperture = len([c for c in coperture if c.is_valid_for_date(date.today())])
    
    return render_template('view_turni_coverage.html',
                         sede=sede,
                         coperture_grouped=coperture_grouped,
                         total_coperture=total_coperture,
                         active_coperture=active_coperture,
                         today=date.today(),
                         is_admin=(current_user.role == 'Admin'))

@app.route('/admin/turni/genera-da-coperture')
@login_required
def generate_turni_from_coverage():
    """Pagina per generare turni basati sulle coperture create"""
    if not current_user.can_access_turni():
        flash('Non hai i permessi per generare turni', 'danger')
        return redirect(url_for('dashboard'))
    
    sede_id = request.args.get('sede', type=int)
    if not sede_id:
        # Se l'utente non è Admin, usa la sua sede per default
        if current_user.role != 'Admin' and current_user.sede_obj and current_user.sede_obj.is_turni_mode():
            sede_id = current_user.sede_obj.id
        else:
            flash('ID sede non specificato. Seleziona una sede dalla pagina Genera Turni.', 'warning')
            return redirect(url_for('generate_turnazioni'))
    
    sede = Sede.query.get_or_404(sede_id)
    
    # Verifica permessi sulla sede - supporta utenti multi-sede  
    if not current_user.can_manage_shifts():
        flash('Non hai i permessi per generare turni', 'danger')
        return redirect(url_for('dashboard'))
        
    # Per utenti non-admin, verifica accesso alla sede specifica
    if not current_user.all_sedi and current_user.sede_obj and current_user.sede_obj.id != sede_id:
        flash('Non hai accesso a questa sede specifica', 'danger')
        return redirect(url_for('generate_turnazioni'))
    
    if not sede.is_turni_mode():
        flash('La sede selezionata non è configurata per la modalità turni', 'warning')
        return redirect(url_for('generate_turnazioni'))
    
    # Ottieni le coperture attive per questa sede
    from models import PresidioCoverage
    coperture = PresidioCoverage.query.filter_by(is_active=True).order_by(
        PresidioCoverage.start_date.desc(),
        PresidioCoverage.day_of_week,
        PresidioCoverage.start_time
    ).all()
    
    # Raggruppa coperture per periodo di validità (evita duplicati con ID univoci)
    coperture_grouped = {}
    coperture_ids_seen = set()
    for copertura in coperture:
        # Evita duplicati
        if copertura.id in coperture_ids_seen:
            continue
        coperture_ids_seen.add(copertura.id)
        
        period_key = f"{copertura.start_date.strftime('%Y-%m-%d')} - {copertura.end_date.strftime('%Y-%m-%d')}"
        if period_key not in coperture_grouped:
            coperture_grouped[period_key] = {
                'start_date': copertura.start_date,
                'end_date': copertura.end_date,
                'coperture': [],
                'is_active': copertura.is_active and copertura.end_date >= date.today(),
                'period_id': f"{copertura.start_date.strftime('%Y%m%d')}-{copertura.end_date.strftime('%Y%m%d')}"
            }
        coperture_grouped[period_key]['coperture'].append(copertura)
    
    # Statistiche
    total_coperture = len(coperture)
    active_coperture = len([c for c in coperture if c.is_valid_for_date(date.today())])
    
    return render_template('generate_turni_from_coverage.html',
                         sede=sede,
                         coperture_grouped=coperture_grouped,
                         total_coperture=total_coperture,
                         active_coperture=active_coperture,
                         today=date.today(),
                         is_admin=(current_user.role == 'Admin'))

@app.route('/admin/turni/process-generate-from-coverage', methods=['POST'])
@login_required
def process_generate_turni_from_coverage():
    """Processa la generazione dei turni basata sulle coperture"""
    if not current_user.can_access_turni():
        flash('Non hai i permessi per generare turni', 'danger')
        return redirect(url_for('dashboard'))
    
    sede_id = request.form.get('sede_id', type=int)
    coverage_period_id = request.form.get('coverage_period_id')
    use_coverage_dates = 'use_coverage_dates' in request.form
    replace_existing = 'replace_existing' in request.form
    confirm_overwrite = 'confirm_overwrite' in request.form
    
    # Debug parametri ricevuti

    
    if not sede_id or not coverage_period_id or coverage_period_id.strip() == '':
        flash(f'Dati mancanti per la generazione turni (sede_id: {sede_id}, coverage_period_id: \'{coverage_period_id}\')', 'danger')
        return redirect(url_for('generate_turnazioni'))
    
    sede = Sede.query.get_or_404(sede_id)
    
    # Verifica permessi - supporta utenti multi-sede
    if not current_user.can_manage_shifts():
        flash('Non hai i permessi per generare turni', 'danger')
        return redirect(url_for('dashboard'))
        
    # Per utenti non-admin, verifica accesso alla sede specifica
    if not current_user.all_sedi and current_user.sede_obj and current_user.sede_obj.id != sede_id:
        flash('Non hai accesso per generare turni per questa sede', 'danger')
        return redirect(url_for('generate_turnazioni'))
    
    try:
        # Decodifica period_id per ottenere le date della copertura
        start_str, end_str = coverage_period_id.split('-')
        start_date = datetime.strptime(start_str, '%Y%m%d').date()
        end_date = datetime.strptime(end_str, '%Y%m%d').date()
        
        # Importa i modelli necessari
        from models import PresidioCoverage, Shift
        coperture = PresidioCoverage.query.filter(
            PresidioCoverage.start_date <= end_date,
            PresidioCoverage.end_date >= start_date,
            PresidioCoverage.is_active == True
        ).all()
        
        if not coperture:
            flash('Nessuna copertura trovata per il periodo specificato', 'warning')
            return redirect(url_for('generate_turnazioni'))
        
        # Controlla se esistono già turni nel periodo prima di procedere
        existing_shifts = Shift.query.join(User, Shift.user_id == User.id).filter(
            User.sede_id == sede_id,
            Shift.date >= start_date,
            Shift.date <= end_date
        ).all()
        
        # Se esistono turni e l'utente non ha scelto di sostituirli, chiedi conferma
        if existing_shifts and not replace_existing and not confirm_overwrite:
            turni_count = len(existing_shifts)
            date_range = f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"
            
            # Renderizza template di conferma con informazioni sui turni esistenti
            return render_template('confirm_overwrite_shifts.html',
                                 sede=sede,
                                 period_id=coverage_period_id,
                                 start_date=start_date,
                                 end_date=end_date,
                                 date_range=date_range,
                                 existing_shifts_count=turni_count,
                                 use_coverage_dates=use_coverage_dates,
                                 replace_existing=replace_existing)
        
        # Implementa la generazione turni reale basata sulle coperture
        turni_creati = 0
        turni_sostituiti = 0
        current_date = start_date
        
        while current_date <= end_date:
            # Trova le coperture per questo giorno della settimana
            day_of_week = current_date.weekday()  # 0=Lunedì, 6=Domenica
            
            coperture_giorno = [c for c in coperture if c.day_of_week == day_of_week and c.is_valid_for_date(current_date)]
            
            for copertura in coperture_giorno:
                # Verifica se esiste già un turno per questa data e orario
                existing_shift = Shift.query.filter_by(
                    date=current_date,
                    start_time=copertura.start_time,
                    end_time=copertura.end_time
                ).first()
                
                if existing_shift and not replace_existing:
                    continue  # Salta se esiste già e non si vuole sostituire
                elif existing_shift and replace_existing:
                    db.session.delete(existing_shift)
                    turni_sostituiti += 1
                
                # Trova utenti disponibili per i ruoli richiesti con numerosità
                required_roles_dict = copertura.get_required_roles_dict()
                
                # Per ogni ruolo e numerosità richiesta
                for role, count_needed in required_roles_dict.items():
                    available_users = User.query.filter(
                        User.sede_id == sede_id,
                        User.active == True,
                        User.role == role
                    ).all()
                    
                    if len(available_users) >= count_needed:
                        # Assegna il numero richiesto di utenti per questo ruolo
                        for i in range(count_needed):
                            user_index = (current_date.day + copertura.id + i) % len(available_users)
                            assigned_user = available_users[user_index]
                            
                            # Crea il turno
                            new_shift = Shift(
                                user_id=assigned_user.id,
                                date=current_date,
                                start_time=copertura.start_time,
                                end_time=copertura.end_time,
                                shift_type='Normale',
                                created_by=current_user.id
                            )
                            db.session.add(new_shift)
                            turni_creati += 1
            
            current_date += timedelta(days=1)
        
        db.session.commit()
        
        if turni_creati > 0 or turni_sostituiti > 0:
            message_parts = []
            if turni_creati > 0:
                message_parts.append(f'{turni_creati} turni creati')
            if turni_sostituiti > 0:
                message_parts.append(f'{turni_sostituiti} turni sostituiti')
            
            flash(f'Generazione completata! {" e ".join(message_parts)} per {sede.name} dal {start_date.strftime("%d/%m/%Y")} al {end_date.strftime("%d/%m/%Y")}', 'success')
        else:
            flash(f'Nessun turno generato - potrebbero già esistere turni per il periodo o non ci sono utenti disponibili', 'warning')
        
    except (ValueError, AttributeError) as e:
        flash('ID periodo non valido', 'danger')
        return redirect(url_for('generate_turnazioni'))
    
    return redirect(url_for('generate_turnazioni'))



@app.route('/admin/turni/visualizza-generati')
@login_required
def view_generated_shifts():
    """Visualizza i turni generati per una specifica copertura"""
    if not current_user.can_access_turni():
        flash('Non hai i permessi per visualizzare i turni', 'danger')
        return redirect(url_for('dashboard'))
    
    sede_id = request.args.get('sede', type=int)
    period_id = request.args.get('period') or request.args.get('coverage_period')
    
    if not all([sede_id, period_id]):
        flash('Parametri mancanti per la visualizzazione turni', 'danger')
        return redirect(url_for('generate_turnazioni'))
    
    sede = Sede.query.get_or_404(sede_id)
    
    # Verifica permessi sulla sede - supporta utenti multi-sede
    if not current_user.can_view_shifts() and not current_user.can_manage_shifts():
        flash('Non hai i permessi per visualizzare i turni', 'danger')
        return redirect(url_for('dashboard'))
        
    # Per utenti non-admin, verifica accesso alla sede specifica
    if not current_user.all_sedi and current_user.sede_obj and current_user.sede_obj.id != sede_id:
        flash('Non hai accesso per visualizzare i turni di questa sede', 'danger')
        return redirect(url_for('generate_turnazioni'))
    
    # Decodifica period_id per ottenere le date
    try:
        start_str, end_str = period_id.split('-')
        coverage_start_date = datetime.strptime(start_str, '%Y%m%d').date()
        coverage_end_date = datetime.strptime(end_str, '%Y%m%d').date()
    except (ValueError, AttributeError):
        flash('Periodo non valido specificato', 'danger')
        return redirect(url_for('generate_turnazioni'))
    
    # Ottieni i turni generati nel periodo delle coperture
    shifts = Shift.query.filter(
        Shift.user.has(sede_id=sede_id),
        Shift.date >= coverage_start_date,
        Shift.date <= coverage_end_date
    ).order_by(Shift.date, Shift.start_time).all()
    
    # Raggruppa turni per data
    shifts_by_date = {}
    for shift in shifts:
        date_str = shift.date.strftime('%Y-%m-%d')
        if date_str not in shifts_by_date:
            shifts_by_date[date_str] = {
                'date': shift.date,
                'date_display': shift.date.strftime('%d/%m/%Y'),
                'day_name': ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica'][shift.date.weekday()],
                'shifts': []
            }
        shifts_by_date[date_str]['shifts'].append(shift)
    
    # Ottieni le coperture di riferimento per il confronto
    from models import PresidioCoverage
    reference_coverages = PresidioCoverage.query.filter(
        PresidioCoverage.start_date <= coverage_end_date,
        PresidioCoverage.end_date >= coverage_start_date,
        PresidioCoverage.is_active == True
    ).all()
    
    total_shifts = len(shifts)
    dates_with_shifts = len(shifts_by_date)
    period_days = (coverage_end_date - coverage_start_date).days + 1
    
    # Calcola utenti unici coinvolti
    unique_users = set()
    for shift in shifts:
        if shift.user:
            unique_users.add(shift.user.id)
    unique_users_count = len(unique_users)
    
    return render_template('view_generated_shifts.html',
                         sede=sede,
                         coverage_start_date=coverage_start_date,
                         coverage_end_date=coverage_end_date,
                         shifts_by_date=shifts_by_date,
                         reference_coverages=reference_coverages,
                         total_shifts=total_shifts,
                         dates_with_shifts=dates_with_shifts,
                         period_days=period_days,
                         unique_users_count=unique_users_count,
                         today=date.today(),
                         is_admin=(current_user.role == 'Admin'))

@app.route('/admin/turni/regenerate-from-coverage', methods=['POST'])
@login_required
def regenerate_turni_from_coverage():
    """Rigenera i turni eliminando quelli esistenti da oggi in poi e creandone di nuovi"""
    if not current_user.can_access_turni():
        flash('Non hai i permessi per rigenerare turni', 'danger')
        return redirect(url_for('dashboard'))
    
    sede_id = request.form.get('sede_id', type=int)
    coverage_period_id = request.form.get('coverage_period_id')
    
    if not all([sede_id, coverage_period_id]):
        flash('Dati mancanti per la rigenerazione turni', 'danger')
        return redirect(url_for('generate_turnazioni'))
    
    sede = Sede.query.get_or_404(sede_id)
    
    # Verifica permessi
    if current_user.role != 'Admin':
        if not current_user.sede_obj or current_user.sede_obj.id != sede_id:
            flash('Non hai i permessi per rigenerare turni per questa sede', 'danger')
            return redirect(url_for('generate_turnazioni'))
    
    try:
        # Decodifica period_id per ottenere le date della copertura
        start_str, end_str = coverage_period_id.split('-')
        start_date = datetime.strptime(start_str, '%Y%m%d').date()
        end_date = datetime.strptime(end_str, '%Y%m%d').date()
        
        # Data di inizio per l'eliminazione (da oggi in poi)
        from datetime import date, timedelta
        today = date.today()
        delete_from_date = max(start_date, today)
        
        # Elimina turni esistenti da oggi in poi
        from models import Shift
        shifts_to_delete = Shift.query.join(User, Shift.user_id == User.id).filter(
            User.sede_id == sede_id,
            Shift.date >= delete_from_date,
            Shift.date <= end_date
        ).all()
        
        deleted_count = len(shifts_to_delete)
        for shift in shifts_to_delete:
            db.session.delete(shift)
        
        db.session.commit()
        
        # Rigenera turni per tutto il periodo originale
        from models import PresidioCoverage
        
        coperture = PresidioCoverage.query.filter(
            PresidioCoverage.start_date <= end_date,
            PresidioCoverage.end_date >= start_date,
            PresidioCoverage.is_active == True
        ).all()
        
        if not coperture:
            flash('Nessuna copertura trovata per il periodo specificato', 'warning')
            return redirect(url_for('generate_turnazioni'))
        
        # Genera i nuovi turni
        new_shifts_count = 0
        current_date = start_date
        
        while current_date <= end_date:
            # Trova le coperture per questo giorno della settimana
            day_of_week = current_date.weekday()  # 0=Lunedì, 6=Domenica
            
            day_coverages = [c for c in coperture if 
                           c.start_date <= current_date <= c.end_date and
                           c.day_of_week == day_of_week]
            
            for coverage in day_coverages:
                # Ottieni utenti disponibili per questa sede e copertura
                available_users = User.query.filter(
                    User.sede_id == sede_id,
                    User.active == True,
                    User.role.in_(['Operatore', 'Sviluppatore', 'Redattore', 'Management'])
                ).all()
                
                # Calcola il numero totale di staff richiesto dai ruoli
                roles_dict = coverage.get_required_roles_dict()
                total_required_staff = sum(roles_dict.values()) if roles_dict else 1
                
                if available_users and total_required_staff > 0:
                    # Seleziona utenti per questa copertura (logica semplificata)
                    selected_users = available_users[:total_required_staff]
                    
                    for user in selected_users:
                        new_shift = Shift(
                            user_id=user.id,
                            date=current_date,
                            start_time=coverage.start_time,
                            end_time=coverage.end_time,
                            shift_type='Turno',
                            created_by=current_user.id
                        )
                        db.session.add(new_shift)
                        new_shifts_count += 1
            
            current_date += timedelta(days=1)
        
        db.session.commit()
        
        # Messaggio di successo
        if deleted_count > 0:
            flash(f'Turni rigenerati con successo! Eliminati {deleted_count} turni esistenti, creati {new_shifts_count} nuovi turni.', 'success')
        else:
            flash(f'Turni generati con successo! Creati {new_shifts_count} nuovi turni.', 'success')
        
        # Reindirizza alla visualizzazione dei turni generati
        return redirect(url_for('view_generated_shifts', sede=sede_id, period=coverage_period_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante la rigenerazione turni: {str(e)}', 'danger')
        return redirect(url_for('generate_turnazioni'))

@app.route('/delete_shift/<int:shift_id>', methods=['POST'])
@login_required
def delete_shift(shift_id):
    """Elimina un singolo turno"""
    if not current_user.can_access_turni():
        flash('Non hai i permessi per eliminare turni', 'danger')
        return redirect(url_for('dashboard'))
    
    shift = Shift.query.get_or_404(shift_id)
    
    # Verifica che il turno non sia nel passato
    from datetime import date
    if shift.date < date.today():
        flash('Non è possibile eliminare turni passati', 'warning')
        return redirect(request.referrer or url_for('dashboard'))
    
    # Verifica permessi sulla sede (se non admin)
    if current_user.role != 'Admin':
        if not current_user.sede_obj or current_user.sede_obj.id != shift.user.sede_id:
            flash('Non hai i permessi per eliminare turni per questa sede', 'danger')
            return redirect(request.referrer or url_for('dashboard'))
        # Verifica che la sede sia di tipo "Turni" per utenti non-admin
        if not current_user.sede_obj.is_turni_mode():
            flash('La modifica turni è disponibile solo per sedi di tipo "Turni"', 'warning')
            return redirect(request.referrer or url_for('dashboard'))
    
    try:
        # Salva info per messaggio di conferma
        user_name = shift.user.get_full_name()
        shift_date = shift.date.strftime('%d/%m/%Y')
        shift_time = f"{shift.start_time.strftime('%H:%M')} - {shift.end_time.strftime('%H:%M')}"
        
        db.session.delete(shift)
        db.session.commit()
        
        flash(f'Turno eliminato: {user_name} - {shift_date} ({shift_time})', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante l\'eliminazione del turno: {str(e)}', 'danger')
    
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/admin/turni/delete-period', methods=['POST'])
@login_required
def delete_turni_period():
    """Elimina tutti i turni di un periodo da oggi in poi"""
    if not current_user.can_access_turni():
        flash('Non hai i permessi per eliminare turni', 'danger')
        return redirect(url_for('dashboard'))
    
    sede_id = request.form.get('sede_id', type=int)
    coverage_period_id = request.form.get('coverage_period_id')
    
    if not all([sede_id, coverage_period_id]):
        flash('Dati mancanti per l\'eliminazione turni', 'danger')
        return redirect(url_for('generate_turnazioni'))
    
    sede = Sede.query.get_or_404(sede_id)
    
    # Verifica permessi
    if current_user.role != 'Admin':
        if not current_user.sede_obj or current_user.sede_obj.id != sede_id:
            flash('Non hai i permessi per eliminare turni per questa sede', 'danger')
            return redirect(url_for('generate_turnazioni'))
    
    try:
        # Decodifica period_id per ottenere le date della copertura
        start_str, end_str = coverage_period_id.split('-')
        start_date = datetime.strptime(start_str, '%Y%m%d').date()
        end_date = datetime.strptime(end_str, '%Y%m%d').date()
        
        # Data di inizio per l'eliminazione (da oggi in poi)
        from datetime import date
        today = date.today()
        delete_from_date = max(start_date, today)
        
        # Elimina turni esistenti da oggi in poi
        from models import Shift
        shifts_to_delete = Shift.query.join(User, Shift.user_id == User.id).filter(
            User.sede_id == sede_id,
            Shift.date >= delete_from_date,
            Shift.date <= end_date
        ).all()
        
        deleted_count = len(shifts_to_delete)
        for shift in shifts_to_delete:
            db.session.delete(shift)
        
        db.session.commit()
        
        # Messaggio di successo
        if deleted_count > 0:
            preserved_days = (today - start_date).days if today > start_date else 0
            if preserved_days > 0:
                flash(f'Eliminati {deleted_count} turni dal {delete_from_date.strftime("%d/%m/%Y")} al {end_date.strftime("%d/%m/%Y")} (preservati {preserved_days} giorni già lavorati)', 'success')
            else:
                flash(f'Eliminati {deleted_count} turni dal {delete_from_date.strftime("%d/%m/%Y")} al {end_date.strftime("%d/%m/%Y")}', 'success')
        else:
            flash('Nessun turno da eliminare nel periodo specificato', 'info')
        
        # Reindirizza alla visualizzazione dei turni generati
        return redirect(url_for('view_generated_shifts', sede=sede_id, period=coverage_period_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante l\'eliminazione turni: {str(e)}', 'danger')
        return redirect(url_for('generate_turnazioni'))

@app.route('/admin/turnazioni')
@login_required
def generate_turnazioni():
    """Generazione automatica turnazioni con visualizzazione coperture inline"""
    if not current_user.can_access_turni():
        flash('Non hai i permessi per generare turnazioni', 'danger')
        return redirect(url_for('dashboard'))
    
    # Ottieni sedi turni accessibili dall'utente
    sedi_turni = current_user.get_turni_sedi()
    
    # Per ogni sede, carica le coperture direttamente server-side
    from models import PresidioCoverage
    sedi_with_coverage = []
    
    for sede in sedi_turni:
        # Ottieni le coperture attive per questa sede
        coperture = PresidioCoverage.query.filter_by(is_active=True).order_by(
            PresidioCoverage.start_date.desc(),
            PresidioCoverage.day_of_week,
            PresidioCoverage.start_time
        ).all()
        
        # Raggruppa coperture per periodo di validità
        coperture_grouped = {}
        for copertura in coperture:
            period_key = f"{copertura.start_date.strftime('%d/%m/%Y')} - {copertura.end_date.strftime('%d/%m/%Y')}"
            if period_key not in coperture_grouped:
                coperture_grouped[period_key] = {
                    'start_date': copertura.start_date,
                    'end_date': copertura.end_date,
                    'coperture': [],
                    'is_active': copertura.is_active and copertura.end_date >= date.today(),
                    'period_id': f"{copertura.start_date.strftime('%Y%m%d')}-{copertura.end_date.strftime('%Y%m%d')}"
                }
            coperture_grouped[period_key]['coperture'].append(copertura)
        
        # Statistiche
        total_coperture = len(coperture)
        active_coperture = len([c for c in coperture if c.is_valid_for_date(date.today())])
        
        sedi_with_coverage.append({
            'sede': sede,
            'coperture_grouped': coperture_grouped,
            'total_coperture': total_coperture,
            'active_coperture': active_coperture
        })
    
    return render_template('generate_turnazioni.html', 
                         sedi_with_coverage=sedi_with_coverage,
                         today=date.today(),
                         is_admin=(current_user.role == 'Admin'))

@app.route('/api/sede/<int:sede_id>/users')
@login_required
def get_sede_users(sede_id):
    """API per ottenere gli utenti di una sede specifica"""
    if not current_user.can_access_turni():
        return jsonify({'error': 'Non autorizzato'}), 403
    
    sede = Sede.query.get_or_404(sede_id)
    
    # Verifica che l'utente possa accedere a questa sede
    if current_user.role != 'Amministratore' and not current_user.all_sedi and (not current_user.sede_obj or current_user.sede_obj.id != sede_id):
        return jsonify({'error': 'Non autorizzato'}), 403
    
    # Ottieni utenti attivi della sede (esclusi Amministratore)
    users = User.query.filter_by(
        sede_id=sede_id, 
        active=True
    ).filter(
        User.role != 'Amministratore'
    ).order_by(User.first_name, User.last_name).all()
    
    users_data = []
    for user in users:
        users_data.append({
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role
        })
    
    return jsonify(users_data)

@app.route('/api/sede/<int:sede_id>/work_schedules')
@login_required
def api_sede_work_schedules(sede_id):
    """API per ottenere gli orari di lavoro di una sede"""
    try:
        sede = Sede.query.get_or_404(sede_id)
        work_schedules = WorkSchedule.query.filter_by(sede_id=sede_id, active=True).all()
        
        # Se la sede supporta modalità turni e non ha ancora l'orario 'Turni', crealo
        if sede.is_turni_mode() and not sede.has_turni_schedule():
            turni_schedule = sede.get_or_create_turni_schedule()
            work_schedules.append(turni_schedule)
        
        schedules_data = []
        for schedule in work_schedules:
            # Visualizzazione speciale per orario "Turni"
            if schedule.is_turni_schedule():
                schedules_data.append({
                    'id': schedule.id,
                    'name': schedule.name,
                    'start_time': 'Flessibile',
                    'end_time': 'Flessibile',
                    'days_count': 7
                })
            else:
                schedules_data.append({
                    'id': schedule.id,
                    'name': schedule.name,
                    'start_time': schedule.start_time.strftime('%H:%M') if schedule.start_time else '',
                    'end_time': schedule.end_time.strftime('%H:%M') if schedule.end_time else '',
                    'days_count': len(schedule.days_of_week) if schedule.days_of_week else 0
                })
        
        return jsonify({
            'success': True,
            'work_schedules': schedules_data,
            'sede_name': sede.name,
            'has_schedules': len(schedules_data) > 0,
            'is_turni_mode': sede.is_turni_mode()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/roles')
@login_required  
def api_roles():
    """API endpoint per ottenere la lista dei ruoli disponibili"""
    try:
        from models import UserRole
        roles = UserRole.query.filter(
            UserRole.active == True,
            UserRole.name != 'Amministratore'
        ).all()
        role_names = [role.name for role in roles] if roles else ['Responsabile', 'Supervisore', 'Operatore', 'Ospite']
        return jsonify(role_names)
    except Exception as e:
        return jsonify(['Responsabile', 'Supervisore', 'Operatore', 'Ospite'])


# ===============================
# GESTIONE SEDI E ORARI DI LAVORO
# ===============================

@app.route('/admin/sedi')
@login_required
def manage_sedi():
    """Gestione delle sedi aziendali"""
    if not (current_user.can_manage_sedi() or current_user.can_view_sedi()):
        flash('Non hai i permessi per accedere alle sedi', 'danger')
        return redirect(url_for('dashboard'))
    
    sedi = Sede.query.order_by(Sede.created_at.desc()).all()
    
    # Calcola statistiche aggiuntive per ogni sede
    sedi_stats = {}
    for sede in sedi:
        stats = {
            'orari_count': sede.work_schedules.filter_by(active=True).count(),
            'turni_count': 0,
            'reperibilita_turni_count': 0
        }
        
        # Conta turni regolari per utenti di questa sede
        if sede.is_turni_mode():
            from models import Shift
            turni_count = db.session.query(Shift).join(User, Shift.user_id == User.id).filter(
                User.sede_id == sede.id,
                User.active == True
            ).count()
            stats['turni_count'] = turni_count
            
            # Conta turni reperibilità per utenti di questa sede
            from models import ReperibilitaShift
            reperibilita_count = db.session.query(ReperibilitaShift).join(User, ReperibilitaShift.user_id == User.id).filter(
                User.sede_id == sede.id,
                User.active == True
            ).count()
            stats['reperibilita_turni_count'] = reperibilita_count
        
        sedi_stats[sede.id] = stats
    
    form = SedeForm()
    return render_template('manage_sedi.html', sedi=sedi, sedi_stats=sedi_stats, form=form)

@app.route('/admin/sedi/create', methods=['POST'])
@login_required
def create_sede():
    """Crea una nuova sede"""
    if not current_user.can_manage_sedi():
        flash('Non hai i permessi per creare sedi', 'danger')
        return redirect(url_for('dashboard'))
    
    form = SedeForm()
    if form.validate_on_submit():
        sede = Sede(
            name=form.name.data,
            address=form.address.data,
            description=form.description.data,
            tipologia=form.tipologia.data,
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
    if not current_user.can_manage_sedi():
        flash('Non hai i permessi per modificare sedi', 'danger')
        return redirect(url_for('dashboard'))
    
    sede = Sede.query.get_or_404(sede_id)
    form = SedeForm(original_name=sede.name, obj=sede)
    
    if form.validate_on_submit():
        sede.name = form.name.data
        sede.address = form.address.data
        sede.description = form.description.data
        sede.tipologia = form.tipologia.data
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
    if not (current_user.can_manage_schedules() or current_user.can_view_schedules()):
        flash('Non hai i permessi per accedere agli orari', 'danger')
        return redirect(url_for('dashboard'))
    
    schedules = WorkSchedule.query.join(Sede).order_by(Sede.name, WorkSchedule.start_time).all()
    form = WorkScheduleForm()
    return render_template('manage_work_schedules.html', schedules=schedules, form=form)

@app.route('/admin/orari/create', methods=['POST'])
@login_required
def create_work_schedule():
    """Crea un nuovo orario di lavoro"""
    if not current_user.can_manage_schedules():
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
    if not current_user.can_manage_schedules():
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
    if not current_user.can_manage_schedules():
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
    if not current_user.can_manage_schedules():
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
    if not (current_user.has_permission('can_manage_roles') or current_user.has_permission('can_view_roles')):
        flash('Non hai i permessi per accedere ai ruoli', 'danger')
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
    # L'amministratore può modificare solo i widget del ruolo Amministratore
    protected_roles = ['Admin']
    if role.name in protected_roles:
        flash(f'Il ruolo "{role.display_name}" è protetto e non può essere modificato', 'danger')
        return redirect(url_for('manage_roles'))
    
    # Se è il ruolo Amministratore e l'utente corrente non è amministratore, blocca
    if role.name == 'Amministratore' and not current_user.has_role('Amministratore'):
        flash(f'Solo un amministratore può modificare il ruolo "{role.display_name}"', 'danger')
        return redirect(url_for('manage_roles'))
    
    # Determina se l'utente corrente è amministratore e può modificare solo widget
    # Solo quando l'amministratore modifica il ruolo "Amministratore"
    is_admin_widget_only = current_user.has_role('Amministratore') and role.name == 'Amministratore'
    
    form = RoleForm(original_name=role.name, widget_only=is_admin_widget_only)
    

    
    if form.validate_on_submit():
        if is_admin_widget_only:
            # Per l'amministratore, aggiorna solo i permessi widget
            existing_permissions = role.permissions.copy()
            widget_permissions = {
                'can_view_team_stats_widget': form.can_view_team_stats_widget.data,
                'can_view_my_attendance_widget': form.can_view_my_attendance_widget.data,
                'can_view_team_management_widget': form.can_view_team_management_widget.data,
                'can_view_leave_requests_widget': form.can_view_leave_requests_widget.data,
                'can_view_daily_attendance_widget': form.can_view_daily_attendance_widget.data,
                'can_view_shifts_coverage_widget': form.can_view_shifts_coverage_widget.data,
                'can_view_reperibilita_widget': form.can_view_reperibilita_widget.data
            }
            existing_permissions.update(widget_permissions)
            role.permissions = existing_permissions
        else:
            # Per altri utenti autorizzati, aggiorna tutti i permessi
            role.name = form.name.data
            role.display_name = form.display_name.data
            role.description = form.description.data
            role.permissions = form.get_permissions_dict()
            role.active = form.is_active.data
        
        db.session.commit()

        
        flash(f'Ruolo "{role.display_name}" modificato con successo', 'success')
        return redirect(url_for('manage_roles'))
    
    # Popola il form con i dati esistenti
    form.name.data = role.name
    form.display_name.data = role.display_name
    form.description.data = role.description
    form.is_active.data = role.active
    form.populate_permissions(role.permissions)
    
    return render_template('edit_role.html', form=form, role=role, is_admin_widget_only=is_admin_widget_only)


@app.route('/admin/roles/toggle/<int:role_id>')
@login_required
def toggle_role(role_id):
    """Attiva/disattiva un ruolo"""
    if not current_user.has_permission('can_manage_roles'):
        flash('Non hai i permessi per modificare ruoli', 'danger')
        return redirect(url_for('dashboard'))
    
    role = UserRole.query.get_or_404(role_id)
    
    # Verifica che non sia un ruolo di sistema protetto
    protected_roles = ['Admin', 'Amministratore']
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
    protected_roles = ['Admin', 'Amministratore']
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

@app.route('/messages')
@login_required
def internal_messages():
    """Visualizza i messaggi interni per l'utente corrente"""
    if not (current_user.can_send_messages() or current_user.can_view_messages()):
        flash('Non hai i permessi per accedere ai messaggi interni', 'danger')
        return redirect(url_for('dashboard'))
    
    from models import InternalMessage
    
    # Messaggi per l'utente corrente
    messages = InternalMessage.query.filter_by(
        recipient_id=current_user.id
    ).order_by(InternalMessage.created_at.desc()).all()
    
    # Conta messaggi non letti
    unread_count = InternalMessage.query.filter_by(
        recipient_id=current_user.id,
        is_read=False
    ).count()
    
    return render_template('internal_messages.html', 
                         messages=messages, 
                         unread_count=unread_count)

@app.route('/message/<int:message_id>/mark_read')
@login_required  
def mark_message_read(message_id):
    """Segna un messaggio come letto"""
    from models import InternalMessage
    
    message = InternalMessage.query.get_or_404(message_id)
    
    # Verifica che sia il destinatario del messaggio
    if message.recipient_id != current_user.id:
        flash('Non puoi accedere a questo messaggio', 'danger')
        return redirect(url_for('internal_messages'))
    
    # Segna come letto
    message.is_read = True
    db.session.commit()
    
    return redirect(url_for('internal_messages'))

@app.route('/send_message', methods=['GET', 'POST'])
@login_required
def send_message():
    """Invia un nuovo messaggio interno"""
    if not current_user.can_send_messages():
        flash('Non hai i permessi per inviare messaggi', 'danger')
        return redirect(url_for('internal_messages'))
    
    from forms import SendMessageForm
    from models import InternalMessage
    
    form = SendMessageForm(current_user=current_user)
    
    if form.validate_on_submit():
        # Verifica che tutti i destinatari siano validi e accessibili
        recipients = User.query.filter(
            User.id.in_(form.recipient_ids.data),
            User.active == True
        ).all()
        
        if not recipients:
            flash('Nessun destinatario valido selezionato', 'danger')
            return render_template('send_message.html', form=form)
        
        # Verifica permessi sede per tutti i destinatari
        valid_recipients = []
        for recipient in recipients:
            can_send = False
            if current_user.all_sedi:
                can_send = True
            elif current_user.sede_id and recipient.sede_id == current_user.sede_id:
                can_send = True
            
            if can_send:
                valid_recipients.append(recipient)
        
        if not valid_recipients:
            flash('Non hai i permessi per inviare messaggi ai destinatari selezionati', 'danger')
            return render_template('send_message.html', form=form)
        
        # Crea e salva un messaggio per ogni destinatario valido
        messages_sent = 0
        for recipient in valid_recipients:
            message = InternalMessage(
                recipient_id=recipient.id,
                sender_id=current_user.id,
                title=form.title.data,
                message=form.message.data,
                message_type=form.message_type.data
            )
            db.session.add(message)
            messages_sent += 1
        
        db.session.commit()
        
        if messages_sent == 1:
            flash(f'Messaggio inviato con successo a {valid_recipients[0].get_full_name()}', 'success')
        else:
            recipient_names = ', '.join([r.get_full_name() for r in valid_recipients[:3]])
            if len(valid_recipients) > 3:
                recipient_names += f' e altri {len(valid_recipients) - 3}'
            flash(f'Messaggio inviato con successo a {messages_sent} destinatari: {recipient_names}', 'success')
        
        return redirect(url_for('internal_messages'))
    
    return render_template('send_message.html', form=form)


# =====================================
# NUOVO SISTEMA TURNI - 3 FUNZIONALITÀ
# =====================================

@app.route("/manage_coverage")
@login_required
def manage_coverage():
    """Gestione Coperture - Sistema completo basato su template"""
    if not current_user.can_manage_coverage():
        flash("Non hai i permessi per gestire le coperture", "danger")
        return redirect(url_for("dashboard"))
    
    # Reindirizza alla nuova pagina del sistema presidio completo
    return redirect(url_for('presidio_coverage'))

@app.route("/view_presidio_coverage/<period_key>")
@login_required
def view_presidio_coverage(period_key):
    """Visualizza dettagli template copertura presidio"""
    if not current_user.can_view_coverage():
        flash("Non hai i permessi per visualizzare le coperture", "danger")
        return redirect(url_for("dashboard"))
    
    from models import PresidioCoverage
    from datetime import datetime
    
    try:
        # Decodifica period_key per ottenere le date
        start_str, end_str = period_key.split('-')
        start_date = datetime.strptime(start_str, '%Y%m%d').date()
        end_date = datetime.strptime(end_str, '%Y%m%d').date()
    except (ValueError, AttributeError):
        flash('Periodo non valido specificato', 'danger')
        return redirect(url_for('manage_coverage'))
    
    # Ottieni tutte le coperture del template
    coverages = PresidioCoverage.query.filter(
        PresidioCoverage.start_date == start_date,
        PresidioCoverage.end_date == end_date,
        PresidioCoverage.is_active == True
    ).order_by(PresidioCoverage.day_of_week, PresidioCoverage.start_time).all()
    
    if not coverages:
        flash('Template di copertura non trovato', 'danger')
        return redirect(url_for('manage_coverage'))
    
    return render_template("view_presidio_coverage.html",
                         coverages=coverages,
                         start_date=start_date,
                         end_date=end_date,
                         period_key=period_key)

@app.route("/edit_presidio_coverage/<period_key>", methods=['GET', 'POST'])
@login_required
def edit_presidio_coverage(period_key):
    """Modifica template copertura presidio"""
    if not current_user.can_manage_coverage():
        flash("Non hai i permessi per modificare le coperture", "danger")
        return redirect(url_for("dashboard"))
    
    from models import PresidioCoverage
    from datetime import datetime
    
    try:
        # Decodifica period_key per ottenere le date
        start_str, end_str = period_key.split('-')
        start_date = datetime.strptime(start_str, '%Y%m%d').date()
        end_date = datetime.strptime(end_str, '%Y%m%d').date()
    except (ValueError, AttributeError):
        flash('Periodo non valido specificato', 'danger')
        return redirect(url_for('manage_coverage'))
    
    # Ottieni tutte le coperture del template
    coverages = PresidioCoverage.query.filter(
        PresidioCoverage.start_date == start_date,
        PresidioCoverage.end_date == end_date
    ).order_by(PresidioCoverage.day_of_week, PresidioCoverage.start_time).all()
    
    if not coverages:
        flash('Template di copertura non trovato', 'danger')
        return redirect(url_for('manage_coverage'))
    
    # Gestisce POST per salvare le modifiche
    if request.method == 'POST':
        try:
            success_count = 0
            error_count = 0
            
            for coverage in coverages:
                coverage_id = coverage.id
                
                # Controlla se deve essere eliminata
                if request.form.get(f'coverage_{coverage_id}_delete'):
                    db.session.delete(coverage)
                    success_count += 1
                    continue
                
                # Aggiorna i campi
                start_time_str = request.form.get(f'coverage_{coverage_id}_start_time')
                end_time_str = request.form.get(f'coverage_{coverage_id}_end_time')
                break_start_str = request.form.get(f'coverage_{coverage_id}_break_start_time')
                break_end_str = request.form.get(f'coverage_{coverage_id}_break_end_time')
                roles_str = request.form.get(f'coverage_{coverage_id}_roles')
                description = request.form.get(f'coverage_{coverage_id}_description')
                is_active = request.form.get(f'coverage_{coverage_id}_is_active') == '1'
                
                if start_time_str and end_time_str and roles_str:
                    coverage.start_time = datetime.strptime(start_time_str, '%H:%M').time()
                    coverage.end_time = datetime.strptime(end_time_str, '%H:%M').time()
                    
                    # Gestione pause opzionali
                    if break_start_str and break_end_str:
                        coverage.break_start_time = datetime.strptime(break_start_str, '%H:%M').time()
                        coverage.break_end_time = datetime.strptime(break_end_str, '%H:%M').time()
                    else:
                        coverage.break_start_time = None
                        coverage.break_end_time = None
                    
                    # Parsing ruoli - supporta formato "Operatore, 2 Tecnico"
                    roles_dict = {}
                    for role_part in roles_str.split(','):
                        role_part = role_part.strip()
                        # Cerca pattern "numero ruolo" o solo "ruolo"
                        parts = role_part.split()
                        if len(parts) >= 2 and parts[0].isdigit():
                            count = int(parts[0])
                            role_name = ' '.join(parts[1:])
                        elif len(parts) >= 2 and parts[-1].isdigit():
                            count = int(parts[-1])
                            role_name = ' '.join(parts[:-1])
                        else:
                            count = 1
                            role_name = role_part
                        
                        if role_name:
                            roles_dict[role_name] = count
                    
                    coverage.set_required_roles_dict(roles_dict)
                    coverage.description = description.strip() if description else None
                    coverage.is_active = is_active
                    success_count += 1
                else:
                    error_count += 1
            
            db.session.commit()
            
            if error_count == 0:
                flash(f'Template aggiornato con successo! {success_count} coperture modificate.', 'success')
            else:
                flash(f'Template parzialmente aggiornato: {success_count} successi, {error_count} errori.', 'warning')
                
            return redirect(url_for('view_presidio_coverage', period_key=period_key))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante il salvataggio: {str(e)}', 'danger')
    
    # Ottieni ruoli disponibili per la selezione
    from models import UserRole
    available_roles = UserRole.query.filter(UserRole.active == True).all()
    roles_data = [{'name': role.name, 'display_name': role.display_name} for role in available_roles]
    
    return render_template("edit_presidio_coverage.html",
                         coverages=coverages,
                         start_date=start_date,
                         end_date=end_date,
                         period_key=period_key,
                         available_roles=roles_data)


@app.route('/admin/coverage/presidio/create', methods=['GET', 'POST'])
@login_required
def create_presidio_coverage():
    """Crea un nuovo template di copertura presidio"""
    if not current_user.has_permission('can_manage_coverage'):
        flash('Non hai i permessi per creare coperture', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            # Ottieni dati dal form
            start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
            description = request.form.get('description', '')
            is_active = request.form.get('is_active') == 'on'
            
            # Validazione date
            if start_date >= end_date:
                flash('La data di fine deve essere successiva alla data di inizio', 'danger')
                return render_template('create_presidio_coverage.html')
            
            # Verifica sovrapposizioni
            existing = PresidioCoverage.query.filter(
                db.or_(
                    db.and_(PresidioCoverage.start_date <= start_date, PresidioCoverage.end_date >= start_date),
                    db.and_(PresidioCoverage.start_date <= end_date, PresidioCoverage.end_date >= end_date),
                    db.and_(PresidioCoverage.start_date >= start_date, PresidioCoverage.end_date <= end_date)
                )
            ).first()
            
            if existing:
                flash(f'Esiste già una copertura per il periodo {existing.start_date.strftime("%d/%m/%Y")} - {existing.end_date.strftime("%d/%m/%Y")}', 'danger')
                return render_template('create_presidio_coverage.html')
            
            # Crea template base per ogni giorno del periodo
            current_date = start_date
            template_count = 0
            
            while current_date <= end_date:
                coverage = PresidioCoverage(
                    date=current_date,
                    start_date=start_date,
                    end_date=end_date,
                    start_time=time(8, 0),  # Default 08:00
                    end_time=time(17, 0),   # Default 17:00
                    break_start_time=time(12, 0),  # Default 12:00
                    break_end_time=time(13, 0),    # Default 13:00
                    required_roles='Operatore',
                    description=description,
                    is_active=is_active
                )
                db.session.add(coverage)
                template_count += 1
                current_date += timedelta(days=1)
            
            db.session.commit()
            flash(f'Template di copertura creato con successo per {template_count} giorni', 'success')
            return redirect(url_for('manage_coverage'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la creazione: {str(e)}', 'danger')
    
    return render_template('create_presidio_coverage.html')


@app.route('/admin/coverage/presidio/generate/<period_key>')
@login_required
def generate_turnazioni_coverage(period_key):
    """Genera/Rigenera turnazioni per una copertura presidio"""
    if not current_user.has_permission('can_manage_coverage'):
        flash('Non hai i permessi per generare turni', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        # Parse period_key (formato: YYYYMMDD-YYYYMMDD)
        start_str, end_str = period_key.split('-')
        start_date = datetime.strptime(start_str, '%Y%m%d').date()
        end_date = datetime.strptime(end_str, '%Y%m%d').date()
        
        # Trova le coperture per il periodo
        coverages = PresidioCoverage.query.filter(
            PresidioCoverage.start_date == start_date,
            PresidioCoverage.end_date == end_date
        ).all()
        
        if not coverages:
            flash('Nessun template di copertura trovato per il periodo specificato', 'danger')
            return redirect(url_for('manage_coverage'))
        
        # Elimina turni esistenti per il periodo
        from models import Shift
        existing_shifts = Shift.query.filter(
            Shift.date >= start_date,
            Shift.date <= end_date
        ).all()
        
        for shift in existing_shifts:
            db.session.delete(shift)
        
        # Genera nuovi turni basati sui template
        shifts_created = 0
        for coverage in coverages:
            if coverage.is_active:
                # Parse ruoli richiesti
                roles_needed = []
                if coverage.required_roles:
                    parts = coverage.required_roles.split(',')
                    for part in parts:
                        part = part.strip()
                        # Gestisce formato "2 Operatore" o "Operatore"
                        match = re.match(r'^(\d+)\s+(.+)$', part) or re.match(r'^(.+)\s+(\d+)$', part)
                        if match:
                            first, second = match.groups()
                            if first.isdigit():
                                count, role = int(first), second
                            else:
                                role, count = first, int(second)
                        else:
                            role, count = part, 1
                        
                        roles_needed.extend([role] * count)
                
                # Crea turni per ogni ruolo necessario
                for role in roles_needed:
                    shift = Shift(
                        date=coverage.date,
                        start_time=coverage.start_time,
                        end_time=coverage.end_time,
                        shift_type='presidio',
                        created_by=current_user.id
                    )
                    db.session.add(shift)
                    shifts_created += 1
        
        db.session.commit()
        flash(f'Generati {shifts_created} turni per il periodo {start_date.strftime("%d/%m/%Y")} - {end_date.strftime("%d/%m/%Y")}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante la generazione turni: {str(e)}', 'danger')
    
    return redirect(url_for('manage_coverage'))

@app.route("/view_coverage_templates")
@login_required  
def view_coverage_templates():
    """Visualizza Turni - Lista semplificata dei template di copertura"""
    if not current_user.can_view_shifts():
        flash("Non hai i permessi per visualizzare i turni", "danger")
        return redirect(url_for("dashboard"))
    
    # Import necessari
    from models import Sede, PresidioCoverage
    
    # Ottieni le sedi accessibili per utente
    if current_user.all_sedi:
        accessible_sedi = Sede.query.filter_by(tipologia="Turni", active=True).all()
    elif current_user.sede_obj and current_user.sede_obj.is_turni_mode():
        accessible_sedi = [current_user.sede_obj]
    else:
        accessible_sedi = []
        flash("Nessuna sede con modalità turni accessibile", "warning")
        return redirect(url_for("dashboard"))
    
    # Ottieni TUTTI i template di copertura (attivi e non) SENZA DUPLICATI
    all_coverages = PresidioCoverage.query.distinct().order_by(
        PresidioCoverage.start_date.desc(),
        PresidioCoverage.id.desc()
    ).all()
    
    # Raggruppa per periodo per una visualizzazione più chiara
    coverage_periods = {}
    for coverage in all_coverages:
        period_key = f"{coverage.start_date.strftime('%Y-%m-%d')} - {coverage.end_date.strftime('%Y-%m-%d')}"
        if period_key not in coverage_periods:
            coverage_periods[period_key] = {
                'start_date': coverage.start_date,
                'end_date': coverage.end_date,
                'coverages': [],
                'is_active': coverage.is_active
            }
        # Solo aggiungi se non già presente (controllo ID)
        if not any(c.id == coverage.id for c in coverage_periods[period_key]['coverages']):
            coverage_periods[period_key]['coverages'].append(coverage)
    
    return render_template("view_coverage_templates.html",
                         coverage_periods=coverage_periods,
                         accessible_sedi=accessible_sedi,
                         total_templates=len(all_coverages),
                         today=date.today())

@app.route("/view_turni_for_period")
@login_required  
def view_turni_for_period():
    """Visualizza i turni generati per un periodo specifico"""
    if not current_user.can_view_shifts():
        flash("Non hai i permessi per visualizzare i turni", "danger")
        return redirect(url_for("dashboard"))
    
    # Import necessari
    from models import Sede, Shift
    from datetime import datetime
    
    # Ottieni parametri
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    
    if not start_date_str or not end_date_str:
        flash("Periodo non specificato correttamente", "warning")
        return redirect(url_for("view_coverage_templates"))
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Formato data non valido", "error")
        return redirect(url_for("view_coverage_templates"))
    
    # Ottieni le sedi accessibili per utente
    if current_user.all_sedi:
        accessible_sedi = Sede.query.filter_by(tipologia="Turni", active=True).all()
    elif current_user.sede_obj and current_user.sede_obj.is_turni_mode():
        accessible_sedi = [current_user.sede_obj]
    else:
        accessible_sedi = []
        flash("Nessuna sede con modalità turni accessibile", "warning")
        return redirect(url_for("dashboard"))
    
    # Trova i turni per il periodo specificato filtrando per utenti delle sedi accessibili
    turni_periodo = []
    if accessible_sedi:
        # Ottieni tutti gli utenti delle sedi accessibili
        sede_ids = [sede.id for sede in accessible_sedi]
        
        # Query turni filtrando per periodo e utenti delle sedi
        # Specificare la condizione JOIN esplicita per evitare ambiguità
        turni_periodo = Shift.query.join(User, Shift.user_id == User.id).filter(
            User.sede_id.in_(sede_ids),
            Shift.date >= start_date,
            Shift.date <= end_date
        ).order_by(Shift.date.desc(), Shift.start_time).all()
    
    return render_template("view_turni_period.html",
                         turni_periodo=turni_periodo,
                         start_date=start_date,
                         end_date=end_date,
                         accessible_sedi=accessible_sedi,
                         total_turni=len(turni_periodo),
                         today=date.today())


# =====================================
# NUOVO SISTEMA PRESIDIO - PACCHETTO COMPLETO
# =====================================

@app.route('/presidio_coverage', methods=['GET', 'POST'])
@login_required
def presidio_coverage():
    """Pagina principale per gestione copertura presidio - Sistema completo"""
    if not current_user.can_manage_shifts():
        flash('Non hai i permessi per gestire coperture presidio', 'danger')
        return redirect(url_for('dashboard'))
    
    # Ottieni tutti i template di copertura presidio ordinati per data creazione
    templates = get_active_presidio_templates()
    
    # Form per nuovo template
    form = PresidioCoverageTemplateForm()
    search_form = PresidioCoverageSearchForm()
    current_template = None
    
    # Applica filtri di ricerca se presenti
    if request.args.get('search'):
        query = PresidioCoverageTemplate.query.filter_by(is_active=True)
        
        template_name = request.args.get('template_name')
        if template_name:
            query = query.filter(PresidioCoverageTemplate.name.ilike(f"%{template_name}%"))
        
        date_from = request.args.get('date_from')
        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                query = query.filter(PresidioCoverageTemplate.start_date >= date_from)
            except ValueError:
                pass
        
        date_to = request.args.get('date_to')
        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                query = query.filter(PresidioCoverageTemplate.end_date <= date_to)
            except ValueError:
                pass
        
        is_active = request.args.get('is_active')
        if is_active:
            active_bool = is_active == 'true'
            query = query.filter(PresidioCoverageTemplate.is_active == active_bool)
        
        templates = query.order_by(PresidioCoverageTemplate.created_at.desc()).all()
    
    # Gestisci creazione/modifica template
    if request.method == 'POST':
        action = request.form.get('action', 'create')
        
        if action == 'create' and form.validate_on_submit():
            template = PresidioCoverageTemplate(
                name=form.name.data,
                start_date=form.start_date.data,
                end_date=form.end_date.data,
                description=form.description.data,
                sede_id=form.sede_id.data,
                created_by=current_user.id
            )
            db.session.add(template)
            db.session.commit()
            flash(f'Template "{template.name}" creato con successo', 'success')
            return redirect(url_for('presidio_coverage_edit', template_id=template.id))
    
    return render_template('presidio_coverage.html', 
                         templates=templates,
                         form=form,
                         search_form=search_form,
                         current_template=current_template)

@app.route('/presidio_coverage_edit/<int:template_id>', methods=['GET', 'POST'])
@login_required
def presidio_coverage_edit(template_id):
    """Modifica template esistente - Sistema completo"""
    if not current_user.can_manage_shifts():
        flash('Non hai i permessi per gestire coperture presidio', 'danger')
        return redirect(url_for('dashboard'))
    
    current_template = PresidioCoverageTemplate.query.get_or_404(template_id)
    templates = get_active_presidio_templates()
    
    # Pre-popola form con dati template
    form = PresidioCoverageTemplateForm()
    coverage_form = PresidioCoverageForm()
    
    if request.method == 'GET':
        form.name.data = current_template.name
        form.start_date.data = current_template.start_date
        form.end_date.data = current_template.end_date
        form.description.data = current_template.description
        form.sede_id.data = current_template.sede_id
    
    if request.method == 'POST':
        action = request.form.get('action', 'update')
        
        if action == 'update' and form.validate_on_submit():
            current_template.name = form.name.data
            current_template.start_date = form.start_date.data
            current_template.end_date = form.end_date.data
            current_template.description = form.description.data
            current_template.sede_id = form.sede_id.data
            db.session.commit()
            flash(f'Template "{current_template.name}" aggiornato con successo', 'success')
            return redirect(url_for('presidio_coverage_edit', template_id=template_id))
        
        elif action == 'add_coverage' and coverage_form.validate_on_submit():
            # Aggiungi nuove coperture per i giorni selezionati
            success_count = 0
            error_count = 0
            
            for day_of_week in coverage_form.days_of_week.data:
                
                # Crea nuova copertura
                new_coverage = PresidioCoverage(
                    template_id=template_id,
                    day_of_week=day_of_week,
                    start_time=coverage_form.start_time.data,
                    end_time=coverage_form.end_time.data,
                    required_roles=json.dumps(coverage_form.required_roles.data),
                    role_count=coverage_form.role_count.data,
                    description=coverage_form.description.data,
                    is_active=coverage_form.is_active.data,
                    start_date=current_template.start_date,
                    end_date=current_template.end_date,
                    created_by=current_user.id
                )
                
                # Gestione pause opzionali
                if coverage_form.break_start.data and coverage_form.break_end.data:
                    try:
                        new_coverage.break_start = datetime.strptime(coverage_form.break_start.data, '%H:%M').time()
                        new_coverage.break_end = datetime.strptime(coverage_form.break_end.data, '%H:%M').time()
                    except ValueError:
                        pass  # Ignora errori di parsing per campi opzionali
                
                db.session.add(new_coverage)
                success_count += 1
            
            db.session.commit()
            
            if success_count > 0:
                flash(f'{success_count} coperture aggiunte con successo', 'success')
            if error_count > 0:
                flash(f'{error_count} coperture non aggiunte per sovrapposizioni orarie', 'warning')
            
            return redirect(url_for('presidio_coverage_edit', template_id=template_id))
    
    return render_template('presidio_coverage.html', 
                         templates=templates,
                         form=form,
                         coverage_form=coverage_form,
                         current_template=current_template)

@app.route('/presidio_detail/<int:template_id>')
@login_required
def presidio_detail(template_id):
    """Visualizza dettagli di un template di copertura presidio"""
    if not (current_user.can_manage_shifts() or current_user.can_view_shifts()):
        flash('Non hai i permessi per visualizzare le coperture presidio', 'danger')
        return redirect(url_for('dashboard'))
    
    template = PresidioCoverageTemplate.query.get_or_404(template_id)
    
    # Organizza le coperture per giorno della settimana
    coverages_by_day = {}
    for coverage in template.coverages.filter_by(is_active=True).order_by(PresidioCoverage.start_time):
        day = coverage.day_of_week
        if day not in coverages_by_day:
            coverages_by_day[day] = []
        coverages_by_day[day].append(coverage)
    
    return render_template('presidio_detail.html', 
                         template=template,
                         coverages_by_day=coverages_by_day)

@app.route('/view_presidi')
@login_required
def view_presidi():
    """Visualizzazione sola lettura dei presidi configurati"""
    if not current_user.can_view_shifts():
        flash('Non hai i permessi per visualizzare i presidi', 'warning')
        return redirect(url_for('dashboard'))
    
    templates = PresidioCoverageTemplate.query.filter_by(is_active=True).order_by(PresidioCoverageTemplate.start_date.desc()).all()
    return render_template('view_presidi.html', templates=templates)

@app.route('/api/presidio_coverage/<int:template_id>')
@login_required
def api_presidio_coverage(template_id):
    """API per ottenere dettagli copertura presidio"""
    template = PresidioCoverageTemplate.query.get_or_404(template_id)
    
    coverages = []
    for coverage in template.coverages.filter_by(is_active=True):
        coverages.append({
            'id': coverage.id,
            'day_of_week': coverage.day_of_week,
            'start_time': coverage.start_time.strftime('%H:%M'),
            'end_time': coverage.end_time.strftime('%H:%M'),
            'required_roles': coverage.get_required_roles(),
            'role_count': coverage.role_count
        })
    
    return jsonify({
        'success': True,
        'template_name': template.name,
        'start_date': template.start_date.strftime('%Y-%m-%d'),
        'end_date': template.end_date.strftime('%Y-%m-%d'),
        'period': template.get_period_display(),
        'coverages': coverages
    })

@app.route('/presidio_coverage/toggle_status/<int:template_id>', methods=['POST'])
@login_required
def toggle_presidio_template_status(template_id):
    """Attiva/disattiva template presidio"""
    if not current_user.can_manage_shifts():
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403
    
    template = PresidioCoverageTemplate.query.get_or_404(template_id)
    new_status = request.json.get('is_active', not template.is_active)
    
    template.is_active = new_status
    template.updated_at = italian_now()
    
    # Aggiorna anche tutte le coperture associate
    for coverage in template.coverages:
        coverage.is_active = new_status
    
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': f'Template {"attivato" if new_status else "disattivato"} con successo'
    })

@app.route('/presidio_coverage/delete/<int:template_id>', methods=['POST'])
@login_required
def delete_presidio_template(template_id):
    """Elimina template presidio (soft delete)"""
    if not current_user.can_manage_shifts():
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403
    
    template = PresidioCoverageTemplate.query.get_or_404(template_id)
    
    # Soft delete del template e di tutte le coperture
    template.is_active = False
    coverages_count = 0
    for coverage in template.coverages:
        coverage.is_active = False
        coverages_count += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Template "{template.name}" eliminato ({coverages_count} coperture)'
    })

@app.route('/presidio_coverage/duplicate/<int:template_id>', methods=['POST'])
@login_required
def duplicate_presidio_template(template_id):
    """Duplica template presidio con tutte le coperture"""
    if not current_user.can_manage_shifts():
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403
    
    source_template = PresidioCoverageTemplate.query.get_or_404(template_id)
    
    # Crea nuovo template
    new_template = PresidioCoverageTemplate(
        name=f"{source_template.name} (Copia)",
        start_date=source_template.start_date,
        end_date=source_template.end_date,
        description=f"Copia di: {source_template.description}" if source_template.description else None,
        created_by=current_user.id
    )
    db.session.add(new_template)
    db.session.flush()  # Per ottenere l'ID
    
    # Duplica tutte le coperture
    coverages_count = 0
    for coverage in source_template.coverages.filter_by(is_active=True):
        new_coverage = PresidioCoverage(
            template_id=new_template.id,
            day_of_week=coverage.day_of_week,
            start_time=coverage.start_time,
            end_time=coverage.end_time,
            required_roles=coverage.required_roles,
            role_count=coverage.role_count,
            description=coverage.description,
            sede_id=coverage.sede_id,
            shift_type=coverage.shift_type
        )
        db.session.add(new_coverage)
        coverages_count += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Template duplicato come "{new_template.name}" ({coverages_count} coperture)',
        'new_template_id': new_template.id
    })

# ============ FUNZIONI UTILITÀ PRESIDIO ============

def get_presidio_coverage_for_period(start_date, end_date):
    """Ottieni coperture presidio valide per un periodo"""
    templates = PresidioCoverageTemplate.query.filter(
        PresidioCoverageTemplate.is_active == True,
        PresidioCoverageTemplate.start_date <= end_date,
        PresidioCoverageTemplate.end_date >= start_date
    ).all()
    
    all_coverages = []
    for template in templates:
        for coverage in template.coverages.filter_by(is_active=True):
            all_coverages.append(coverage)
    
    return all_coverages

def get_required_roles_for_day_time(day_of_week, time_slot):
    """Ottieni ruoli richiesti per un giorno e orario specifico"""
    from datetime import datetime, time
    if isinstance(time_slot, str):
        time_slot = datetime.strptime(time_slot, '%H:%M').time()
    
    coverages = PresidioCoverage.query.filter(
        PresidioCoverage.is_active == True,
        PresidioCoverage.day_of_week == day_of_week,
        PresidioCoverage.start_time <= time_slot,
        PresidioCoverage.end_time > time_slot
    ).all()
    
    required_roles = set()
    for coverage in coverages:
        required_roles.update(coverage.get_required_roles())
    
    return list(required_roles)

def get_active_presidio_templates():
    """Ottieni tutti i template presidio attivi ordinati per data"""
    return PresidioCoverageTemplate.query.filter_by(is_active=True).order_by(
        PresidioCoverageTemplate.start_date.desc()
    ).all()

def create_presidio_shift_from_template(template, target_week_start, users_by_role):
    """
    Crea turni presidio da template per una settimana specifica
    Args:
        template: PresidioCoverageTemplate
        target_week_start: data inizio settimana (date)
        users_by_role: dict {role_name: [User objects]}
    Returns:
        dict con risultati creazione turni
    """
    from datetime import timedelta
    
    created_shifts = []
    errors = []
    
    for coverage in template.coverages.filter_by(is_active=True):
        # Calcola la data specifica per il giorno della settimana
        target_date = target_week_start + timedelta(days=coverage.day_of_week)
        
        # Ottieni utenti disponibili per i ruoli richiesti
        required_roles = coverage.get_required_roles()
        available_users = []
        
        for role in required_roles:
            if role in users_by_role:
                available_users.extend(users_by_role[role])
        
        if len(available_users) < coverage.role_count:
            errors.append(f"Utenti insufficienti per {coverage.get_day_name()} {coverage.get_time_range()}: richiesti {coverage.role_count}, disponibili {len(available_users)}")
            continue
        
        # Seleziona utenti per il turno (semplice: primi N disponibili)
        selected_users = available_users[:coverage.role_count]
        
        # Crea turni per ogni utente selezionato
        for user in selected_users:
            # Verifica sovrapposizioni esistenti
            existing_shift = Shift.query.filter(
                Shift.user_id == user.id,
                Shift.date == target_date,
                Shift.start_time < coverage.end_time,
                Shift.end_time > coverage.start_time
            ).first()
            
            if existing_shift:
                errors.append(f"Sovrapposizione per {user.get_full_name()} il {target_date.strftime('%d/%m/%Y')}")
                continue
            
            # Crea il turno
            shift = Shift(
                user_id=user.id,
                date=target_date,
                start_time=coverage.start_time,
                end_time=coverage.end_time,
                shift_type='presidio',
                created_by=created_by_id
            )
            
            db.session.add(shift)
            created_shifts.append(shift)
    
    try:
        db.session.commit()
        return {
            'success': True,
            'created_count': len(created_shifts),
            'errors': errors,
            'shifts': created_shifts
        }
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'error': str(e),
            'created_count': 0,
            'errors': errors + [f"Errore database: {str(e)}"]
        }



@app.route('/delete_presidio_coverage/<int:coverage_id>', methods=['POST'])
@login_required
def delete_presidio_coverage(coverage_id):
    """Elimina singola copertura presidio"""
    if not current_user.can_manage_shifts():
        flash('Non hai i permessi per eliminare coperture presidio', 'danger')
        return redirect(url_for('presidio_coverage'))
    
    coverage = PresidioCoverage.query.get_or_404(coverage_id)
    template_id = coverage.template_id
    
    # Controllo di sicurezza
    if coverage.created_by != current_user.id and not current_user.has_role('Amministratore'):
        flash('Puoi eliminare solo coperture che hai creato', 'danger')
        return redirect(url_for('presidio_coverage_edit', template_id=template_id))
    
    # Disattiva invece di eliminare
    coverage.is_active = False
    db.session.commit()
    
    flash('Copertura eliminata con successo', 'success')
    return redirect(url_for('presidio_coverage_edit', template_id=template_id))


# ============================================================================
# NOTE SPESE ROUTES
# ============================================================================

@app.route('/expenses')
@login_required
def expense_reports():
    """Visualizza elenco note spese"""
    if not current_user.can_access_expense_reports_menu():
        flash('Non hai i permessi per accedere alle note spese', 'danger')
        return redirect(url_for('dashboard'))
    
    from models import ExpenseReport, ExpenseCategory
    from forms import ExpenseFilterForm
    
    filter_form = ExpenseFilterForm(current_user=current_user)
    
    # Query base
    query = ExpenseReport.query
    
    # Check view mode from URL parameter
    view_mode = request.args.get('view', 'all')
    
    # Controllo permessi per determinare cosa può vedere l'utente
    if view_mode == 'my' or not (current_user.can_view_expense_reports() or current_user.can_approve_expense_reports()):
        # Mostra solo le note spese dell'utente corrente
        query = query.filter(ExpenseReport.employee_id == current_user.id)
        page_title = "Le Mie Note Spese"
    elif current_user.can_view_expense_reports() or current_user.can_approve_expense_reports():
        # Utente può vedere tutte le note spese (eventualmente filtrate per sede)
        if not current_user.all_sedi and current_user.sede_id:
            # Filtra per sede se non ha accesso globale
            from models import User
            sede_users = User.query.filter(User.sede_id == current_user.sede_id).with_entities(User.id).all()
            sede_user_ids = [u.id for u in sede_users]
            query = query.filter(ExpenseReport.employee_id.in_(sede_user_ids))
        page_title = "Note Spese"
    else:
        # Fallback: mostra solo le proprie
        query = query.filter(ExpenseReport.employee_id == current_user.id)
        page_title = "Le Mie Note Spese"
    
    # Applica filtri se presenti
    if filter_form.validate_on_submit():
        if filter_form.employee_id.data:
            query = query.filter(ExpenseReport.employee_id == filter_form.employee_id.data)
        if filter_form.category_id.data:
            query = query.filter(ExpenseReport.category_id == filter_form.category_id.data)
        if filter_form.status.data:
            query = query.filter(ExpenseReport.status == filter_form.status.data)
        if filter_form.date_from.data:
            query = query.filter(ExpenseReport.expense_date >= filter_form.date_from.data)
        if filter_form.date_to.data:
            query = query.filter(ExpenseReport.expense_date <= filter_form.date_to.data)
    
    # Ordina per data più recente
    expenses = query.order_by(ExpenseReport.expense_date.desc(), ExpenseReport.created_at.desc()).all()
    
    return render_template('expense_reports.html', 
                         expenses=expenses, 
                         filter_form=filter_form,
                         page_title=page_title,
                         view_mode=view_mode)


@app.route('/expenses/create', methods=['GET', 'POST'])
@login_required
def create_expense_report():
    """Crea nuova nota spese"""
    if not current_user.can_create_expense_reports():
        flash('Non hai i permessi per creare note spese', 'danger')
        return redirect(url_for('expense_reports'))
    
    from models import ExpenseReport, ExpenseCategory
    from forms import ExpenseReportForm
    import os
    from werkzeug.utils import secure_filename
    
    form = ExpenseReportForm()
    
    if form.validate_on_submit():
        # Gestione upload file
        receipt_filename = None
        if form.receipt_file.data:
            file = form.receipt_file.data
            filename = secure_filename(file.filename)
            
            # Crea nome file unico
            import uuid
            file_extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
            
            # Crea directory uploads se non esiste
            upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'expenses')
            os.makedirs(upload_dir, exist_ok=True)
            
            file_path = os.path.join(upload_dir, unique_filename)
            file.save(file_path)
            receipt_filename = unique_filename
        
        # Crea nota spese
        expense = ExpenseReport(
            employee_id=current_user.id,
            expense_date=form.expense_date.data,
            description=form.description.data,
            amount=form.amount.data,
            category_id=form.category_id.data,
            receipt_filename=receipt_filename
        )
        
        db.session.add(expense)
        db.session.commit()
        
        flash('Nota spese creata con successo', 'success')
        return redirect(url_for('expense_reports'))
    
    return render_template('create_expense_report.html', form=form)


@app.route('/expenses/edit/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense_report(expense_id):
    """Modifica nota spese esistente"""
    from models import ExpenseReport
    from forms import ExpenseReportForm
    import os
    from werkzeug.utils import secure_filename
    
    expense = ExpenseReport.query.get_or_404(expense_id)
    
    # Verifica permessi
    if expense.employee_id != current_user.id and not current_user.can_manage_expense_reports():
        flash('Non hai i permessi per modificare questa nota spese', 'danger')
        return redirect(url_for('expense_reports'))
    
    # Verifica se modificabile
    if not expense.can_be_edited():
        flash('Questa nota spese non può più essere modificata', 'warning')
        return redirect(url_for('expense_reports'))
    
    form = ExpenseReportForm()
    
    if form.validate_on_submit():
        # Gestione upload file
        if form.receipt_file.data:
            # Elimina vecchio file se esiste
            if expense.receipt_filename:
                old_file_path = os.path.join(app.root_path, 'static', 'uploads', 'expenses', expense.receipt_filename)
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
            
            file = form.receipt_file.data
            filename = secure_filename(file.filename)
            
            # Crea nome file unico
            import uuid
            file_extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
            
            # Crea directory uploads se non esiste
            upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'expenses')
            os.makedirs(upload_dir, exist_ok=True)
            
            file_path = os.path.join(upload_dir, unique_filename)
            file.save(file_path)
            expense.receipt_filename = unique_filename
        
        # Aggiorna dati
        expense.expense_date = form.expense_date.data
        expense.description = form.description.data
        expense.amount = form.amount.data
        expense.category_id = form.category_id.data
        
        db.session.commit()
        flash('Nota spese aggiornata con successo', 'success')
        return redirect(url_for('expense_reports'))
    
    # Precompila form con dati esistenti
    form.expense_date.data = expense.expense_date
    form.description.data = expense.description
    form.amount.data = expense.amount
    form.category_id.data = expense.category_id
    
    return render_template('edit_expense_report.html', form=form, expense=expense)


@app.route('/expenses/approve/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def approve_expense_report(expense_id):
    """Approva/rifiuta nota spese"""
    from models import ExpenseReport
    from forms import ExpenseApprovalForm
    
    expense = ExpenseReport.query.get_or_404(expense_id)
    
    # Verifica permessi
    if not expense.can_be_approved_by(current_user):
        flash('Non hai i permessi per approvare questa nota spese', 'danger')
        return redirect(url_for('expense_reports'))
    
    if expense.status != 'pending':
        flash('Questa nota spese è già stata processata', 'warning')
        return redirect(url_for('expense_reports'))
    
    form = ExpenseApprovalForm()
    
    if form.validate_on_submit():
        if form.action.data == 'approve':
            expense.approve(current_user, form.comment.data)
            flash('Nota spese approvata con successo', 'success')
        else:
            expense.reject(current_user, form.comment.data)
            flash('Nota spese rifiutata', 'info')
        
        db.session.commit()
        return redirect(url_for('expense_reports'))
    
    return render_template('approve_expense_report.html', form=form, expense=expense)


@app.route('/expenses/download/<int:expense_id>')
@login_required
def download_expense_receipt(expense_id):
    """Download ricevuta allegata"""
    from models import ExpenseReport
    from flask import send_file
    import os
    
    expense = ExpenseReport.query.get_or_404(expense_id)
    
    # Verifica permessi
    if (expense.employee_id != current_user.id and 
        not current_user.can_view_expense_reports() and 
        not current_user.can_approve_expense_reports()):
        flash('Non hai i permessi per scaricare questo documento', 'danger')
        return redirect(url_for('expense_reports'))
    
    if not expense.receipt_filename:
        flash('Nessun documento allegato a questa nota spese', 'warning')
        return redirect(url_for('expense_reports'))
    
    file_path = os.path.join(app.root_path, 'static', 'uploads', 'expenses', expense.receipt_filename)
    
    if not os.path.exists(file_path):
        flash('File non trovato', 'danger')
        return redirect(url_for('expense_reports'))
    
    return send_file(file_path, as_attachment=True, 
                    download_name=f"ricevuta_{expense.id}_{expense.expense_date.strftime('%Y%m%d')}.{expense.receipt_filename.split('.')[-1]}")


@app.route('/expenses/categories')
@login_required
def expense_categories():
    """Gestisci categorie note spese"""
    if not current_user.can_manage_expense_reports():
        flash('Non hai i permessi per gestire le categorie', 'danger')
        return redirect(url_for('expense_reports'))
    
    from models import ExpenseCategory
    categories = ExpenseCategory.query.order_by(ExpenseCategory.name).all()
    
    return render_template('expense_categories.html', categories=categories)


@app.route('/expenses/categories/create', methods=['GET', 'POST'])
@login_required
def create_expense_category():
    """Crea nuova categoria"""
    if not current_user.can_manage_expense_reports():
        flash('Non hai i permessi per creare categorie', 'danger')
        return redirect(url_for('expense_reports'))
    
    from models import ExpenseCategory
    from forms import ExpenseCategoryForm
    
    form = ExpenseCategoryForm()
    
    if form.validate_on_submit():
        category = ExpenseCategory(
            name=form.name.data,
            description=form.description.data,
            is_active=form.is_active.data,
            created_by=current_user.id
        )
        
        db.session.add(category)
        
        try:
            db.session.commit()
            flash('Categoria creata con successo', 'success')
            return redirect(url_for('expense_categories'))
        except:
            db.session.rollback()
            flash('Errore: categoria già esistente', 'danger')
    
    return render_template('create_expense_category.html', form=form)


@app.route('/expenses/delete/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense_report(expense_id):
    """Elimina nota spese"""
    from models import ExpenseReport
    import os
    
    expense = ExpenseReport.query.get_or_404(expense_id)
    
    # Verifica permessi
    if expense.employee_id != current_user.id and not current_user.can_manage_expense_reports():
        flash('Non hai i permessi per eliminare questa nota spese', 'danger')
        return redirect(url_for('expense_reports'))
    
    # Solo note in attesa possono essere eliminate
    if expense.status != 'pending':
        flash('Solo le note spese in attesa possono essere eliminate', 'warning')
        return redirect(url_for('expense_reports'))
    
    # Elimina file allegato se esiste
    if expense.receipt_filename:
        file_path = os.path.join(app.root_path, 'static', 'uploads', 'expenses', expense.receipt_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    
    db.session.delete(expense)
    db.session.commit()
    
    flash('Nota spese eliminata con successo', 'success')
    return redirect(url_for('expense_reports'))







