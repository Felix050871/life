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
from models import User, AttendanceEvent, LeaveRequest, LeaveType, Shift, ShiftTemplate, ReperibilitaShift, ReperibilitaTemplate, ReperibilitaIntervention, Intervention, Sede, WorkSchedule, UserRole, PresidioCoverage, PresidioCoverageTemplate, ReperibilitaCoverage, Holiday, PasswordResetToken, italian_now, get_active_presidio_templates, get_presidio_coverage_for_day, OvertimeType, OvertimeRequest, ExpenseCategory, ExpenseReport, ACITable, MileageRequest
from forms import LoginForm, UserForm, UserProfileForm, AttendanceForm, LeaveRequestForm, LeaveTypeForm, ShiftForm, ShiftTemplateForm, SedeForm, WorkScheduleForm, RoleForm, PresidioCoverageTemplateForm, PresidioCoverageForm, PresidioCoverageSearchForm, ForgotPasswordForm, ResetPasswordForm, OvertimeTypeForm, OvertimeRequestForm, ApproveOvertimeForm, OvertimeFilterForm, ACIUploadForm, ACIRecordForm, ACIFilterForm, MileageRequestForm, ApproveMileageForm, MileageFilterForm
from utils import get_user_statistics, get_team_statistics, format_hours, check_user_schedule_with_permissions, send_overtime_request_message

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
        upcoming_shifts = PresidioCoverageTemplate.query.filter_by(active=True).order_by(PresidioCoverageTemplate.start_date.desc()).all()
    
    # Get upcoming reperibilità shifts for authorized users
    upcoming_reperibilita_shifts = []
    active_intervention = None
    recent_interventions = []
    current_time = italian_now().time()
    if current_user.can_view_reperibilita():
        # Show active reperibilità coverage grouped by period
        upcoming_reperibilita_shifts = db.session.query(ReperibilitaCoverage)\
            .filter(ReperibilitaCoverage.active == True)\
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
    
    # Get recent overtime requests for widget
    recent_overtime_requests = []
    my_overtime_requests = []
    if current_user.can_view_overtime_widget():
        if current_user.can_manage_overtime_requests() or current_user.can_approve_overtime_requests():
            # Managers see all requests
            recent_overtime_requests = OvertimeRequest.query.options(
                joinedload(OvertimeRequest.employee),
                joinedload(OvertimeRequest.overtime_type)
            ).order_by(OvertimeRequest.created_at.desc()).limit(10).all()
    
    # Get my overtime requests for personal widget  
    if current_user.can_view_my_overtime_widget():
        my_overtime_requests = OvertimeRequest.query.filter_by(
            employee_id=current_user.id
        ).options(
            joinedload(OvertimeRequest.overtime_type)
        ).order_by(OvertimeRequest.created_at.desc()).limit(5).all()
    
    # Get recent mileage requests for widget
    recent_mileage_requests = []
    my_mileage_requests = []
    if current_user.can_view_mileage_widget():
        if current_user.can_manage_mileage_requests() or current_user.can_approve_mileage_requests():
            # Managers see all requests
            recent_mileage_requests = MileageRequest.query.options(
                joinedload(MileageRequest.user),
                joinedload(MileageRequest.vehicle)
            ).order_by(MileageRequest.created_at.desc()).limit(10).all()
    
    # Get my mileage requests for personal widget  
    if current_user.can_view_my_mileage_widget():
        my_mileage_requests = MileageRequest.query.filter_by(
            user_id=current_user.id
        ).options(
            joinedload(MileageRequest.vehicle)
        ).order_by(MileageRequest.created_at.desc()).limit(5).all()
    
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

    # Get all sedi for multi-sede users
    all_sedi_list = []
    if current_user.all_sedi:
        all_sedi_list = Sede.query.filter_by(active=True).all()

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
                         all_sedi_list=all_sedi_list,
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
                         recent_overtime_requests=recent_overtime_requests,
                         my_overtime_requests=my_overtime_requests,
                         recent_mileage_requests=recent_mileage_requests,
                         my_mileage_requests=my_mileage_requests,
                         format_hours=format_hours)

@app.route('/dashboard_team')
@login_required
def dashboard_team():
    """Dashboard per visualizzare le presenze di tutte le sedi - per Management"""
    if not current_user.can_view_all_attendance():
        flash('Non hai i permessi per visualizzare questo contenuto.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get users visible to current user based on role and sede access - consistent with attendance logic
    if current_user.role == 'Amministratore':
        # Amministratori vedono tutti gli utenti di tutte le sedi
        all_users = User.query.filter(
            User.active.is_(True),
            ~User.role.in_(['Admin', 'Staff'])
        ).all()
    elif current_user.role in ['Responsabile', 'Management']:
        # Responsabili e Management vedono solo utenti della propria sede
        all_users = User.query.filter(
            User.sede_id == current_user.sede_id,
            User.active.is_(True),
            ~User.role.in_(['Admin', 'Staff'])
        ).all()
    elif current_user.all_sedi:
        # Utenti multi-sede vedono tutti gli utenti attivi di tutte le sedi
        all_users = User.query.filter(
            User.active.is_(True),
            ~User.role.in_(['Admin', 'Staff'])
        ).all()
    else:
        # Altri utenti vedono solo utenti della propria sede se specificata
        if current_user.sede_id:
            all_users = User.query.filter(
                User.sede_id == current_user.sede_id,
                User.active.is_(True),
                ~User.role.in_(['Admin', 'Staff'])
            ).all()
        else:
            all_users = []
    
    # Get sedi visible to current user 
    if current_user.role == 'Amministratore' or current_user.all_sedi:
        # Amministratori e utenti multi-sede vedono tutte le sedi
        all_sedi = Sede.query.filter(Sede.active == True).all()
    elif current_user.sede_id:
        # Altri utenti vedono solo la propria sede
        all_sedi = [current_user.sede_obj] if current_user.sede_obj and current_user.sede_obj.active else []
    else:
        all_sedi = []
    
    # Parametri di visualizzazione semplificati
    export_format = request.args.get('export')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    today = date.today()
    
    # Range di date - mantieni i valori passati o usa oggi come default
    if start_date_str and start_date_str.strip():
        try:
            start_date = datetime.strptime(start_date_str.strip(), '%Y-%m-%d').date()
        except ValueError:
            start_date = today
    else:
        start_date = today
        
    if end_date_str and end_date_str.strip():
        try:
            end_date = datetime.strptime(end_date_str.strip(), '%Y-%m-%d').date()
        except ValueError:
            end_date = today
    else:
        end_date = today
        
    # Assicurati che start_date <= end_date
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    
    # Etichetta periodo
    if start_date == end_date:
        period_label = f"Giorno {start_date.strftime('%d/%m/%Y')}"
    else:
        period_label = f"Periodo {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"
    
    # Funzione helper per verificare se un giorno è lavorativo
    def is_working_day(check_date, user):
        """Verifica se una data è un giorno lavorativo per l'utente"""
        # Verifica se è un giorno festivo
        holiday = Holiday.query.filter(
            Holiday.month == check_date.month,
            Holiday.day == check_date.day,
            Holiday.active == True
        ).first()
        if holiday:
            return False
        
        # Verifica gli orari di lavoro dell'utente
        if user.work_schedule:
            # Se l'utente ha un orario definito, controlla i giorni della settimana
            if user.work_schedule.days_of_week:
                weekday = check_date.weekday()  # 0=lunedì, 6=domenica
                # Gestisci sia stringa che lista per days_of_week
                if isinstance(user.work_schedule.days_of_week, str):
                    allowed_days = [int(d) for d in user.work_schedule.days_of_week.split(',')]
                elif isinstance(user.work_schedule.days_of_week, list):
                    allowed_days = [int(d) for d in user.work_schedule.days_of_week]
                else:
                    # Default lun-ven se formato non riconosciuto
                    allowed_days = [0, 1, 2, 3, 4]
                    
                if weekday not in allowed_days:
                    return False
        else:
            # Se non ha orario definito (modalità turni), controlla solo weekend di default
            weekday = check_date.weekday()
            if weekday >= 5:  # sabato=5, domenica=6
                return False
        
        return True
    
    # Get attendance data for the period - OTTIMIZZATO
    attendance_data = {}
    
    # Pre-carica tutti i dati necessari con query ottimizzate
    user_ids = [user.id for user in all_users]
    
    # Query batch per richieste di congedo nel periodo
    leave_requests = LeaveRequest.query.filter(
        LeaveRequest.user_id.in_(user_ids),
        LeaveRequest.status == 'Approved',
        LeaveRequest.start_date <= end_date,
        LeaveRequest.end_date >= start_date
    ).all()
    
    # Organizza leave requests per user_id e date
    leave_by_user_date = {}
    for leave in leave_requests:
        if leave.user_id not in leave_by_user_date:
            leave_by_user_date[leave.user_id] = {}
        
        # Aggiungi la richiesta per ogni giorno coperto
        current = max(leave.start_date, start_date)
        end = min(leave.end_date, end_date)
        while current <= end:
            leave_by_user_date[leave.user_id][current] = leave
            current += timedelta(days=1)
    
    # Query batch per eventi di presenza nel periodo
    attendance_events = AttendanceEvent.query.filter(
        AttendanceEvent.user_id.in_(user_ids),
        AttendanceEvent.date >= start_date,
        AttendanceEvent.date <= end_date
    ).order_by(AttendanceEvent.date, AttendanceEvent.timestamp).all()
    
    # Organizza eventi per user_id e date
    events_by_user_date = {}
    for event in attendance_events:
        if event.user_id not in events_by_user_date:
            events_by_user_date[event.user_id] = {}
        if event.date not in events_by_user_date[event.user_id]:
            events_by_user_date[event.user_id][event.date] = []
        events_by_user_date[event.user_id][event.date].append(event)

    for user in all_users:
        if start_date == end_date:
            # Vista giornaliera singola
            is_working = is_working_day(start_date, user)
            leave_request = leave_by_user_date.get(user.id, {}).get(start_date)
            
            if is_working or leave_request:
                # Usa dati pre-caricati invece di query separate
                user_events = events_by_user_date.get(user.id, {}).get(start_date, [])
                status, last_event = AttendanceEvent.calculate_status_from_events(user_events)
                daily_summary = AttendanceEvent.calculate_summary_from_events(user_events)
                
                attendance_data[user.id] = {
                    'user': user,
                    'status': status,
                    'last_event': last_event,
                    'daily_summary': daily_summary,
                    'leave_request': leave_request
                }
        else:
            # Periodo multi-giorno ottimizzato
            daily_details = []
            current_date = start_date
            
            while current_date <= min(end_date, date.today()):
                is_working = is_working_day(current_date, user)
                leave_request = leave_by_user_date.get(user.id, {}).get(current_date)
                
                if is_working or leave_request:
                    user_events = events_by_user_date.get(user.id, {}).get(current_date, [])
                    status, last_event = AttendanceEvent.calculate_status_from_events(user_events)
                    daily_summary = AttendanceEvent.calculate_summary_from_events(user_events)
                    
                    if not daily_summary and not leave_request and not last_event:
                        status = 'out'
                    
                    daily_details.append({
                        'date': current_date,
                        'status': status,
                        'daily_summary': daily_summary,
                        'last_event': last_event,
                        'leave_request': leave_request
                    })
                
                current_date += timedelta(days=1)
            
            if daily_details:
                attendance_data[user.id] = {
                    'user': user,
                    'daily_details': daily_details
                }
                
    # Handle export
    if export_format == 'excel':
        return generate_attendance_excel_export(attendance_data, 'custom', period_label, all_sedi, start_date, end_date)
    
    return render_template('dashboard_team.html',
                         all_users=all_users,
                         all_sedi=all_sedi,
                         attendance_data=attendance_data,
                         today=today,
                         period_label=period_label,
                         start_date=start_date,
                         end_date=end_date,
                         current_user=current_user)

def generate_attendance_excel_export(attendance_data, period_mode, period_label, all_sedi, start_date=None, end_date=None):
    """Genera export Excel delle presenze con un foglio per ogni sede"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from datetime import datetime as dt
    import tempfile
    import os
    from flask import make_response
    
    # Raggruppa utenti per sede
    sedi_data = {}
    for user_id, data in attendance_data.items():
        user = data['user']
        if user.sede_id:
            from models import Sede
            sede = Sede.query.get(user.sede_id)
            sede_name = sede.name if sede else 'Sede Non Definita'
        else:
            sede_name = 'Sede Non Definita'
        
        if sede_name not in sedi_data:
            sedi_data[sede_name] = {}
        sedi_data[sede_name][user_id] = data
    
    # Crea workbook Excel
    wb = Workbook()
    # Rimuovi il foglio di default
    wb.remove(wb.active)
    
    # Crea un foglio per ogni sede
    for sede_name, sede_attendance in sedi_data.items():
        # Nome foglio sicuro (max 31 caratteri per Excel)
        safe_sheet_name = sede_name.replace('/', '_').replace('\\', '_').replace('?', '_').replace('*', '_').replace('[', '_').replace(']', '_')[:31]
        ws = wb.create_sheet(title=safe_sheet_name)
        
        # Header con stile
        ws.append([f'Report Presenze - {sede_name}'])
        ws.append([period_label])
        ws.append([])  # Riga vuota
        
        # Intestazione colonne
        headers = ['Data', 'Utente', 'Ruolo', 'Stato', 'Entrata', 'Uscita', 'Ore Lavorate', 'Note']
        ws.append(headers)
        
        # Stile header
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=4, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
        
        # Dati presenze
        if start_date == end_date:
            # Single day
            for user_id, data in sede_attendance.items():
                user = data['user']
                
                # Determina stato
                if data.get('leave_request'):
                    lr = data['leave_request']
                    stato = lr.leave_type
                    entrata = uscita = '-'
                    ore_lavorate = '-'
                    note = lr.reason[:50] if lr.reason else ''
                else:
                    ds = data.get('daily_summary')
                    le = data.get('last_event')
                    status = data.get('status')
                    
                    if status == 'in':
                        stato = 'Presente'
                        entrata = ds.clock_in.strftime('%H:%M') if ds and ds.clock_in else '-'
                        uscita = '-'
                        ore_lavorate = f"{ds.total_hours:.1f}h" if ds and ds.total_hours else '0h'
                        note = le.notes[:50] if le and le.notes else ''
                    elif status == 'break':
                        stato = 'In Pausa'
                        entrata = ds.clock_in.strftime('%H:%M') if ds and ds.clock_in else '-'
                        uscita = '-'
                        ore_lavorate = f"{ds.total_hours:.1f}h" if ds and ds.total_hours else '0h'
                        note = le.notes[:50] if le and le.notes else ''
                    elif status == 'out':
                        if ds and ds.clock_in:
                            stato = 'Uscito'
                            entrata = ds.clock_in.strftime('%H:%M')
                            uscita = ds.clock_out.strftime('%H:%M') if ds.clock_out else '-'
                            ore_lavorate = f"{ds.total_hours:.1f}h" if ds.total_hours else '0h'
                            note = le.notes[:50] if le and le.notes else ''
                        else:
                            stato = 'Assente'
                            entrata = uscita = '-'
                            ore_lavorate = '0h'
                            note = ''
                    else:
                        stato = 'Non registrato'
                        entrata = uscita = '-'
                        ore_lavorate = '0h'
                        note = ''
                
                ws.append([
                    start_date.strftime('%d/%m/%Y'),
                    user.get_full_name(),
                    user.role if hasattr(user, 'role') and user.role else 'N/A',
                    stato,
                    entrata,
                    uscita,
                    ore_lavorate,
                    note
                ])
        else:
            # Multi-periodo
            all_entries = []
            for user_id, data in sede_attendance.items():
                user = data['user']
                if 'daily_details' in data:
                    for daily in data['daily_details']:
                        all_entries.append((daily['date'], user, daily))
            
            all_entries.sort(key=lambda x: x[0])
            
            for date_val, user, daily in all_entries:
                if daily.get('leave_request'):
                    lr = daily['leave_request']
                    stato = lr.leave_type
                    entrata = uscita = '-'
                    ore_lavorate = '-'
                    note = lr.reason[:50] if lr.reason else ''
                else:
                    ds = daily.get('daily_summary')
                    le = daily.get('last_event')
                    status = daily.get('status')
                    
                    if status == 'in':
                        stato = 'Presente'
                        entrata = ds.clock_in.strftime('%H:%M') if ds and ds.clock_in else '-'
                        uscita = '-'
                        ore_lavorate = f"{ds.total_hours:.1f}h" if ds and ds.total_hours else '0h'
                        note = le.notes[:50] if le and le.notes else ''
                    elif status == 'break':
                        stato = 'In Pausa'
                        entrata = ds.clock_in.strftime('%H:%M') if ds and ds.clock_in else '-'
                        uscita = '-'
                        ore_lavorate = f"{ds.total_hours:.1f}h" if ds and ds.total_hours else '0h'
                        note = le.notes[:50] if le and le.notes else ''
                    elif status == 'out':
                        if ds and ds.clock_in:
                            stato = 'Uscito'
                            entrata = ds.clock_in.strftime('%H:%M')
                            uscita = ds.clock_out.strftime('%H:%M') if ds.clock_out else '-'
                            ore_lavorate = f"{ds.total_hours:.1f}h" if ds.total_hours else '0h'
                            note = le.notes[:50] if le and le.notes else ''
                        else:
                            stato = 'Assente'
                            entrata = uscita = '-'
                            ore_lavorate = '0h'
                            note = ''
                    else:
                        stato = 'Non definito'
                        entrata = uscita = '-'
                        ore_lavorate = '0h'
                        note = ''
                
                ws.append([
                    date_val.strftime('%d/%m/%Y'),
                    user.get_full_name(),
                    user.role if hasattr(user, 'role') and user.role else 'N/A',
                    stato,
                    entrata,
                    uscita,
                    ore_lavorate,
                    note
                ])
        
        # Auto-dimensiona colonne
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
    
    # Salva file temporaneo
    temp_dir = tempfile.mkdtemp()
    excel_path = os.path.join(temp_dir, f'presenze_per_sede_{dt.now().strftime("%Y%m%d")}.xlsx')
    wb.save(excel_path)
    
    # Leggi file per response
    with open(excel_path, 'rb') as f:
        excel_data = f.read()
    
    # Pulizia
    os.remove(excel_path)
    os.rmdir(temp_dir)
    
    response = make_response(excel_data)
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename="presenze_per_sede_{dt.now().strftime("%Y%m%d")}.xlsx"'
    
    return response

def generate_single_sede_excel(attendance_data, period_label, start_date, end_date, sede_name, return_content=False):
    """Genera CSV per una singola sede"""
    from io import StringIO
    import csv
    output = StringIO()
    writer = csv.writer(output)
    
    # Header con nome sede
    writer.writerow([f'Report Presenze - {sede_name}'])
    writer.writerow([period_label])
    writer.writerow([])  # Riga vuota
    writer.writerow(['Data', 'Utente', 'Ruolo', 'Stato', 'Entrata', 'Uscita', 'Ore Lavorate', 'Note'])
    
    # Determina la logica in base al periodo
    if start_date == end_date:
        # Single day
        for user_id, data in attendance_data.items():
            user = data['user']
            
            # Determina stato
            if data.get('leave_request'):
                lr = data['leave_request']
                if lr.leave_type == 'Ferie':
                    stato = 'Ferie'
                elif lr.leave_type == 'Permesso':
                    stato = 'Permesso'
                elif lr.leave_type == 'Malattia':
                    stato = 'Malattia'
                else:
                    stato = f"In {lr.leave_type}"
                entrata = '-'
                uscita = '-'
                ore_lavorate = '-'
                note = lr.reason[:50] if lr.reason else ''
            else:
                ds = data.get('daily_summary')
                le = data.get('last_event')
                status = data.get('status')
                
                if status == 'in':
                    stato = 'Presente'
                    entrata = ds.clock_in.strftime('%H:%M') if ds and ds.clock_in else '-'
                    uscita = '-'
                    ore_lavorate = f"{ds.total_hours:.1f}h" if ds and ds.total_hours else '0h'
                    note = le.notes[:50] if le and le.notes else ''
                elif status == 'break':
                    stato = 'In Pausa'
                    entrata = ds.clock_in.strftime('%H:%M') if ds and ds.clock_in else '-'
                    uscita = '-'
                    ore_lavorate = f"{ds.total_hours:.1f}h" if ds and ds.total_hours else '0h'
                    note = le.notes[:50] if le and le.notes else ''
                elif status == 'out':
                    if ds and ds.clock_in:
                        stato = 'Uscito'
                        entrata = ds.clock_in.strftime('%H:%M')
                        uscita = ds.clock_out.strftime('%H:%M') if ds.clock_out else '-'
                        ore_lavorate = f"{ds.total_hours:.1f}h" if ds.total_hours else '0h'
                        note = le.notes[:50] if le and le.notes else ''
                    else:
                        stato = 'Assente'
                        entrata = '-'
                        uscita = '-'
                        ore_lavorate = '0h'
                        note = ''
                else:
                    stato = 'Non registrato'
                    entrata = '-'
                    uscita = '-'
                    ore_lavorate = '0h'
                    note = ''
            
            writer.writerow([
                start_date.strftime('%d/%m/%Y'),
                user.get_full_name(),
                user.role if hasattr(user, 'role') and user.role else 'N/A',
                stato,
                entrata,
                uscita,
                ore_lavorate,
                note
            ])
    else:
        # Multi-periodo
        all_entries = []
        for user_id, data in attendance_data.items():
            user = data['user']
            if 'daily_details' in data:
                for daily in data['daily_details']:
                    all_entries.append((daily['date'], user, daily))
        
        all_entries.sort(key=lambda x: x[0])
        
        for date_val, user, daily in all_entries:
            if daily.get('leave_request'):
                lr = daily['leave_request']
                if lr.leave_type == 'Ferie':
                    stato = 'Ferie'
                elif lr.leave_type == 'Permesso':
                    stato = 'Permesso'
                elif lr.leave_type == 'Malattia':
                    stato = 'Malattia'
                else:
                    stato = f"In {lr.leave_type}"
                entrata = '-'
                uscita = '-'
                ore_lavorate = '-'
                note = lr.reason[:50] if lr.reason else ''
            else:
                ds = daily.get('daily_summary')
                le = daily.get('last_event')
                status = daily.get('status')
                
                if status == 'in':
                    stato = 'Presente'
                    entrata = ds.clock_in.strftime('%H:%M') if ds and ds.clock_in else '-'
                    uscita = '-'
                    ore_lavorate = f"{ds.total_hours:.1f}h" if ds and ds.total_hours else '0h'
                    note = le.notes[:50] if le and le.notes else ''
                elif status == 'break':
                    stato = 'In Pausa'
                    entrata = ds.clock_in.strftime('%H:%M') if ds and ds.clock_in else '-'
                    uscita = '-'
                    ore_lavorate = f"{ds.total_hours:.1f}h" if ds and ds.total_hours else '0h'
                    note = le.notes[:50] if le and le.notes else ''
                elif status == 'out':
                    if ds and ds.clock_in:
                        stato = 'Uscito'
                        entrata = ds.clock_in.strftime('%H:%M')
                        uscita = ds.clock_out.strftime('%H:%M') if ds.clock_out else '-'
                        ore_lavorate = f"{ds.total_hours:.1f}h" if ds.total_hours else '0h'
                        note = le.notes[:50] if le and le.notes else ''
                    else:
                        stato = 'Assente'
                        entrata = '-'
                        uscita = '-'
                        ore_lavorate = '0h'
                        note = ''
                else:
                    stato = 'Non definito'
                    entrata = '-'
                    uscita = '-'  
                    ore_lavorate = '0h'
                    note = ''
            
            writer.writerow([
                date_val.strftime('%d/%m/%Y'),
                user.get_full_name(),
                user.role if hasattr(user, 'role') and user.role else 'N/A',
                stato,
                entrata,
                uscita,
                ore_lavorate,
                note
            ])
    
    output.seek(0)
    content = output.getvalue()
    
    if return_content:
        return content
    
    from datetime import datetime as dt
    from flask import make_response
    response = make_response(content)
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    safe_sede_name = sede_name.replace(' ', '_').replace('/', '_')
    response.headers['Content-Disposition'] = f'attachment; filename="presenze_{safe_sede_name}_{dt.now().strftime("%Y%m%d")}.csv"'
    
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
                pass  # Silent error handling
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
    pass  # Test route
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
        pass  # Silent error handling
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
        
    pass  # Clock-in attempt
    
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
    
    # Ottieni sede_id da richiesta JSON o utente
    data = request.get_json() or {}
    sede_id = data.get('sede_id')
    
    # Se utente multi-sede, sede_id è obbligatorio
    if current_user.all_sedi and not sede_id:
        return jsonify({
            'success': False, 
            'message': 'Seleziona una sede per registrare la presenza.'
        }), 400
    
    # Se utente con sede specifica, usa quella
    if not current_user.all_sedi:
        sede_id = current_user.sede_id
    
    # Crea nuovo evento di entrata
    event = AttendanceEvent()
    event.user_id = current_user.id
    event.date = now.date()  # Usa la data italiana
    event.event_type = 'clock_in'
    event.timestamp = now
    event.sede_id = sede_id
    
    # Controlla gli orari della sede e permessi per determinare lo stato
    try:
        schedule_check = check_user_schedule_with_permissions(current_user.id, now)
        if schedule_check['has_schedule']:
            event.shift_status = schedule_check['entry_status']
        else:
            event.shift_status = 'normale'
    except Exception as e:
        pass  # Silent error handling
        event.shift_status = 'normale'
    
    try:
        db.session.add(event)
        db.session.commit()
        pass  # Event created successfully
        return jsonify({
            'success': True, 
            'message': f'Entrata registrata alle {now.strftime("%H:%M")}'
        })
    except Exception as e:
        pass  # Silent error handling
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
    
    # Ottieni sede_id da richiesta JSON o utente
    data = request.get_json() or {}
    sede_id = data.get('sede_id')
    
    # Se utente multi-sede, sede_id è obbligatorio
    if current_user.all_sedi and not sede_id:
        return jsonify({
            'success': False, 
            'message': 'Seleziona una sede per registrare la presenza.'
        }), 400
    
    # Se utente con sede specifica, usa quella
    if not current_user.all_sedi:
        sede_id = current_user.sede_id
    
    # Crea nuovo evento di uscita
    event = AttendanceEvent()
    event.user_id = current_user.id
    event.date = now.date()  # Usa la data italiana
    event.event_type = 'clock_out'
    event.timestamp = now
    event.sede_id = sede_id
    
    # Controlla gli orari della sede e permessi per determinare lo stato
    try:
        schedule_check = check_user_schedule_with_permissions(current_user.id, now)
        if schedule_check['has_schedule']:
            event.shift_status = schedule_check['exit_status']
        else:
            event.shift_status = 'normale'
    except Exception as e:
        pass  # Silent error handling
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
    
    # Ottieni sede_id da richiesta JSON o utente
    data = request.get_json() or {}
    sede_id = data.get('sede_id')
    
    # Se utente multi-sede, sede_id è obbligatorio
    if current_user.all_sedi and not sede_id:
        return jsonify({
            'success': False, 
            'message': 'Seleziona una sede per registrare la presenza.'
        }), 400
    
    # Se utente con sede specifica, usa quella
    if not current_user.all_sedi:
        sede_id = current_user.sede_id
    
    # Crea nuovo evento di inizio pausa
    event = AttendanceEvent()
    event.user_id = current_user.id
    event.date = now.date()  # Usa la data italiana
    event.event_type = 'break_start'
    event.timestamp = now
    event.sede_id = sede_id
    
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
    
    # Ottieni sede_id da richiesta JSON o utente
    data = request.get_json() or {}
    sede_id = data.get('sede_id')
    
    # Se utente multi-sede, sede_id è obbligatorio
    if current_user.all_sedi and not sede_id:
        return jsonify({
            'success': False, 
            'message': 'Seleziona una sede per registrare la presenza.'
        }), 400
    
    # Se utente con sede specifica, usa quella
    if not current_user.all_sedi:
        sede_id = current_user.sede_id
    
    # Crea nuovo evento di fine pausa
    event = AttendanceEvent()
    event.user_id = current_user.id
    event.date = now.date()  # Usa la data italiana
    event.event_type = 'break_end'
    event.timestamp = now
    event.sede_id = sede_id
    
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
    
    form = AttendanceForm(user=current_user)
    
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
                
                # Determina sede_id
                sede_id = None
                if current_user.all_sedi and form.sede_id.data:
                    sede_id = form.sede_id.data
                elif current_user.sede_id:
                    sede_id = current_user.sede_id
                
                note_event = AttendanceEvent(
                    user_id=current_user.id,
                    date=now.date(),
                    event_type='clock_in',  # Evento fittizio per salvare le note
                    timestamp=now,
                    sede_id=sede_id,
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
    elif current_user.role in ['Amministratore']:
        # Amministratore vede sempre dati team con sede
        show_team_data = True
        view_mode = 'sede'
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
        elif view_mode == 'sede' or current_user.role == 'Amministratore':
            # Utenti con permessi visualizzazione sede o amministratori
            if current_user.all_sedi or current_user.role == 'Amministratore':
                # Utenti multi-sede e amministratori vedono tutti gli utenti attivi di tutte le sedi
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

@app.route('/send_message')
@login_required
def send_message():
    """Route placeholder per messaging interno"""
    flash('Funzionalità messaggi in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/forgot_password')
def forgot_password():
    """Route placeholder per reset password"""
    flash('Funzionalità reset password in sviluppo', 'info')
    return redirect(url_for('login'))

@app.route('/internal_messages')
@login_required
def internal_messages():
    """Route placeholder per messaggi interni"""
    flash('Funzionalità messaggi interni in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/user_profile')
@login_required
def user_profile():
    """Route placeholder per profilo utente"""
    flash('Funzionalità profilo utente in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/change_password')
@login_required
def change_password():
    """Route placeholder per cambio password"""
    flash('Funzionalità cambio password in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/admin_panel')
@login_required
def admin_panel():
    """Route placeholder per pannello admin"""
    flash('Funzionalità pannello admin in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/shift_calendar')
@login_required
def shift_calendar():
    """Route placeholder per calendario turni"""
    flash('Funzionalità calendario turni in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/reports')
@login_required
def reports():
    """Route placeholder per report"""
    flash('Funzionalità report in sviluppo', 'info')
    return redirect(url_for('dashboard'))

# Route mancanti dal template base.html - aggiunte tutte insieme per evitare errori
@app.route('/manage_roles')
@login_required
def manage_roles():
    flash('Funzionalità gestione ruoli in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/manage_users')
@login_required
def manage_users():
    flash('Funzionalità gestione utenti in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/manage_sedi')
@login_required
def manage_sedi():
    flash('Funzionalità gestione sedi in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/manage_holidays')
@login_required
def manage_holidays():
    flash('Funzionalità gestione festività in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/mileage_requests')
@login_required
def mileage_requests():
    flash('Funzionalità rimborsi chilometrici in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/reperibilita')
@login_required
def reperibilita():
    flash('Funzionalità reperibilità in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/reperibilita_manager')
@login_required
def reperibilita_manager():
    flash('Funzionalità gestione reperibilità in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/expense_notes')
@login_required
def expense_notes():
    flash('Funzionalità note spese in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/overtime_requests')
@login_required
def overtime_requests():
    flash('Funzionalità richieste straordinari in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/leave_requests')
@login_required
def leave_requests():
    flash('Funzionalità richieste ferie in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/manage_presidio_templates')
@login_required
def manage_presidio_templates():
    flash('Funzionalità gestione template presidio in sviluppo', 'info')
    return redirect(url_for('dashboard'))

# AGGIUNTE TUTTE LE ROUTE MANCANTI IDENTIFICATE DAI TEMPLATE
@app.route('/user_management')
@login_required
def user_management():
    flash('Funzionalità gestione utenti in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/manage_work_schedules')
@login_required
def manage_work_schedules():
    flash('Funzionalità gestione orari di lavoro in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/presidio_coverage')
@login_required
def presidio_coverage():
    flash('Funzionalità coperture presidio in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/view_presidi')
@login_required
def view_presidi():
    flash('Funzionalità visualizzazione presidi in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/generate_reperibilita_shifts')
@login_required
def generate_reperibilita_shifts():
    flash('Funzionalità generazione turni reperibilità in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/reperibilita_coverage')
@login_required
def reperibilita_coverage():
    flash('Funzionalità coperture reperibilità in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/reperibilita_shifts')
@login_required
def reperibilita_shifts():
    flash('Funzionalità turni reperibilità in sviluppo', 'info')
    return redirect(url_for('dashboard'))

# dashboard_team già esiste - rimossa duplicazione

@app.route('/aci_tables')
@login_required
def aci_tables():
    flash('Funzionalità tabelle ACI in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/aci_create')
@login_required
def aci_create():
    flash('Funzionalità creazione ACI in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/aci_export')
@login_required
def aci_export():
    flash('Funzionalità esportazione ACI in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/aci_upload')
@login_required
def aci_upload():
    flash('Funzionalità upload ACI in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/holidays')
@login_required
def holidays():
    flash('Funzionalità gestione festività in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/leave_types')
@login_required
def leave_types():
    flash('Funzionalità tipi di ferie in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/overtime_types')
@login_required
def overtime_types():
    flash('Funzionalità tipi straordinari in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/expense_categories')
@login_required
def expense_categories():
    flash('Funzionalità categorie spese in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/expense_reports')
@login_required
def expense_reports():
    flash('Funzionalità report spese in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/create_expense_report')
@login_required
def create_expense_report():
    flash('Funzionalità creazione report spese in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/create_leave_request_page')
@login_required
def create_leave_request_page():
    flash('Funzionalità creazione richiesta ferie in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/create_mileage_request')
@login_required
def create_mileage_request():
    flash('Funzionalità creazione rimborso chilometrico in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/create_overtime_request')
@login_required
def create_overtime_request():
    flash('Funzionalità creazione richiesta straordinari in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/my_mileage_requests')
@login_required
def my_mileage_requests():
    flash('Funzionalità miei rimborsi chilometrici in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/my_overtime_requests')
@login_required
def my_overtime_requests():
    flash('Funzionalità mie richieste straordinari in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/my_interventions') 
@login_required
def my_interventions():
    flash('Funzionalità miei interventi in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/overtime_requests_management')
@login_required
def overtime_requests_management():
    flash('Funzionalità gestione richieste straordinari in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/admin_generate_qr_codes')
@login_required
def admin_generate_qr_codes():
    flash('Funzionalità generazione codici QR in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/visualizza_turni')
@login_required
def visualizza_turni():
    """Visualizza turni - placeholder semplice"""
    flash('Funzionalità visualizzazione turni in sviluppo', 'info')
    return redirect(url_for('dashboard'))

# Route critiche per turni_automatici
@app.route('/genera_turni_da_template', methods=['GET', 'POST'])
@login_required
def genera_turni_da_template():
    """Genera turni da template - placeholder"""
    flash('Funzionalità generazione turni da template in sviluppo', 'info')
    return redirect(url_for('turni_automatici'))

@app.route('/new_user')
@login_required
def new_user():
    flash('Funzionalità nuovo utente in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/users')
@login_required
def users():
    flash('Funzionalità lista utenti in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/shifts')
@login_required
def shifts():
    flash('Funzionalità turni in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/manage_coverage')
@login_required
def manage_coverage():
    flash('Funzionalità gestione coperture in sviluppo', 'info')
    return redirect(url_for('dashboard'))

@app.route('/generate_shifts')
@login_required
def generate_shifts():
    flash('Funzionalità generazione turni in sviluppo', 'info')
    return redirect(url_for('dashboard'))

# index già esiste - rimossa duplicazione


