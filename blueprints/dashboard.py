# =============================================================================
# DASHBOARD ROUTES BLUEPRINT
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta, time

# Application Imports
from app import db
from models import (
    User, AttendanceEvent, LeaveRequest, Shift, PresidioCoverageTemplate, 
    ReperibilitaShift, Intervention, ExpenseReport, OvertimeRequest, MileageRequest,
    Sede, italian_now
)
from utils import get_user_statistics, get_team_statistics, format_hours

# Create Blueprint
dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    # Verifica permessi di accesso alla dashboard
    if not current_user.can_access_dashboard():
        flash('Non hai i permessi per accedere alla dashboard.', 'danger')
        return redirect(url_for('auth.login'))
    
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
    
    # Widget team management data (per Management e Responsabile)
    team_management_data = []
    if current_user.can_view_team_management_widget():
        users_to_check = []
        
        if current_user.role == 'Amministratore':
            # Admin vede tutti gli utenti attivi
            users_to_check = User.query.filter(
                User.active.is_(True),
                ~User.role.in_(['Admin', 'Staff'])  # Escludi admin e staff
            ).order_by(User.last_name, User.first_name).all()
        elif current_user.role == 'Management' and current_user.all_sedi:
            # Management multi-sede vede tutti gli utenti
            users_to_check = User.query.filter(
                User.active.is_(True),
                ~User.role.in_(['Admin', 'Staff'])
            ).order_by(User.last_name, User.first_name).all()
        elif current_user.sede_id:
            # Responsabile e Management vede utenti della propria sede
            users_to_check = User.query.filter(
                User.sede_id == current_user.sede_id,
                User.active.is_(True),
                ~User.role.in_(['Admin', 'Staff'])
            ).order_by(User.last_name, User.first_name).all()
        
        for user in users_to_check:
            user_today_status, last_event = AttendanceEvent.get_user_status(user.id, today_date)
            team_management_data.append({
                'user': user,
                'status': user_today_status,
                'last_event': last_event
            })
    
    # Widget reperibilità (on-call) shifts
    upcoming_reperibilita_shifts = []
    active_intervention = None
    active_general_intervention = None
    recent_interventions = []
    
    if current_user.can_view_my_reperibilita():
        # My upcoming reperibilità shifts (next 7 days)
        seven_days_from_now = date.today() + timedelta(days=7)
        upcoming_reperibilita_shifts = ReperibilitaShift.query.filter(
            ReperibilitaShift.user_id == current_user.id,
            ReperibilitaShift.date >= date.today(),
            ReperibilitaShift.date <= seven_days_from_now
        ).order_by(ReperibilitaShift.date, ReperibilitaShift.start_time).all()
        
        # Active intervention for current user
        active_intervention = Intervention.query.filter(
            Intervention.user_id == current_user.id,
            Intervention.end_datetime.is_(None)
        ).first()
        
        # Recent interventions (last 7 days)
        seven_days_ago = date.today() - timedelta(days=7)
        recent_interventions = Intervention.query.filter(
            Intervention.user_id == current_user.id,
            Intervention.start_date >= seven_days_ago
        ).order_by(Intervention.start_date.desc(), Intervention.start_time.desc()).limit(5).all()
    
    # Active general intervention (per tutti gli utenti)
    active_general_intervention = Intervention.query.filter(
        Intervention.user_id.is_(None),  # Intervento generale
        Intervention.end_datetime.is_(None)
    ).first()
    
    # Widget leave requests
    recent_leaves = []
    if current_user.can_view_my_leave():
        # Recent leave requests (last 30 days)
        thirty_days_ago = date.today() - timedelta(days=30)
        recent_leaves = LeaveRequest.query.filter(
            LeaveRequest.user_id == current_user.id,
            LeaveRequest.created_at >= thirty_days_ago
        ).order_by(LeaveRequest.created_at.desc()).limit(5).all()
    
    # Widget calendar view (next 7 days with shifts and events)
    weekly_calendar = []
    if current_user.can_view_shifts() or current_user.can_view_my_reperibilita():
        for i in range(7):
            day = date.today() + timedelta(days=i)
            day_data = {'date': day, 'shifts': [], 'reperibilita': []}
            
            # Get shifts for this day
            if current_user.can_view_shifts():
                day_shifts = Shift.query.filter(
                    Shift.user_id == current_user.id,
                    Shift.date == day
                ).all()
                day_data['shifts'] = day_shifts
            
            # Get reperibilità for this day
            if current_user.can_view_my_reperibilita():
                day_reperibilita = ReperibilitaShift.query.filter(
                    ReperibilitaShift.user_id == current_user.id,
                    ReperibilitaShift.date == day
                ).all()
                day_data['reperibilita'] = day_reperibilita
            
            weekly_calendar.append(day_data)
    
    # Widget for daily attendance data (last 7 days)
    daily_attendance_data = []
    if current_user.can_view_attendance():
        for i in range(7):
            day = date.today() - timedelta(days=i)
            daily_hours = AttendanceEvent.get_daily_work_hours(current_user.id, day)
            daily_attendance_data.append({
                'date': day,
                'hours': daily_hours
            })
        daily_attendance_data.reverse()  # Show oldest first
    
    # Widget shifts coverage alerts
    shifts_coverage_alerts = []
    if current_user.can_view_shifts() and current_user.can_view_team_management_widget():
        # Check for shifts without coverage in next 7 days
        end_date = date.today() + timedelta(days=7)
        templates_to_check = PresidioCoverageTemplate.query.filter(
            PresidioCoverageTemplate.active.is_(True),
            PresidioCoverageTemplate.start_date <= end_date
        ).all()
        
        for template in templates_to_check:
            template_start = max(template.start_date, date.today())
            template_end = min(template.end_date, end_date) if template.end_date else end_date
            
            current_date = template_start
            while current_date <= template_end:
                # Check if this day needs coverage and is missing
                # This is a simplified check - in real implementation you'd check against actual coverage
                shifts_coverage_alerts.append({
                    'date': current_date,
                    'template': template,
                    'missing_roles': []  # Would be calculated based on actual coverage
                })
                current_date += timedelta(days=1)
    
    # Widget my leave requests (pending and recent)
    my_leave_requests = []
    if current_user.can_view_my_leave():
        my_leave_requests = LeaveRequest.query.filter(
            LeaveRequest.user_id == current_user.id
        ).order_by(LeaveRequest.created_at.desc()).limit(5).all()
    
    # Widget my shifts (next 7 days)
    my_shifts = []
    if current_user.can_view_shifts():
        seven_days_from_now = date.today() + timedelta(days=7)
        my_shifts = Shift.query.filter(
            Shift.user_id == current_user.id,
            Shift.date >= date.today(),
            Shift.date <= seven_days_from_now
        ).order_by(Shift.date, Shift.start_time).all()
    
    # Widget my reperibilità (next 7 days)
    my_reperibilita = []
    if current_user.can_view_my_reperibilita():
        seven_days_from_now = date.today() + timedelta(days=7)
        my_reperibilita = ReperibilitaShift.query.filter(
            ReperibilitaShift.user_id == current_user.id,
            ReperibilitaShift.date >= date.today(),
            ReperibilitaShift.date <= seven_days_from_now
        ).order_by(ReperibilitaShift.date, ReperibilitaShift.start_time).all()
    
    # Widget expense reports data
    expense_reports_data = []
    if current_user.can_view_my_expense_reports():
        recent_reports = ExpenseReport.query.filter(
            ExpenseReport.user_id == current_user.id
        ).order_by(ExpenseReport.created_at.desc()).limit(3).all()
        expense_reports_data = recent_reports
    
    # Widget overtime requests
    recent_overtime_requests = []
    my_overtime_requests = []
    if current_user.can_view_my_overtime_requests():
        my_overtime_requests = OvertimeRequest.query.filter(
            OvertimeRequest.user_id == current_user.id
        ).order_by(OvertimeRequest.created_at.desc()).limit(5).all()
    
    if current_user.can_approve_overtime_requests():
        recent_overtime_requests = OvertimeRequest.query.filter(
            OvertimeRequest.status == 'pending'
        ).order_by(OvertimeRequest.created_at.desc()).limit(5).all()
    
    # Widget mileage requests
    recent_mileage_requests = []
    my_mileage_requests = []
    if current_user.can_view_my_mileage_requests():
        my_mileage_requests = MileageRequest.query.filter(
            MileageRequest.user_id == current_user.id
        ).order_by(MileageRequest.created_at.desc()).limit(5).all()
    
    if current_user.can_approve_mileage_requests():
        recent_mileage_requests = MileageRequest.query.filter(
            MileageRequest.status == 'pending'
        ).order_by(MileageRequest.created_at.desc()).limit(5).all()
    
    # Get current time for dashboard display
    today = italian_now()
    current_time = today.time()
    
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

@dashboard_bp.route('/dashboard_team')
@login_required
def dashboard_team():
    """Dashboard per visualizzare le presenze di tutte le sedi - per Management"""
    if not current_user.can_view_all_attendance():
        flash('Non hai i permessi per visualizzare questo contenuto.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
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
    
    # Get today's date for attendance status
    today = date.today()
    
    # Build user data with attendance status
    users_data = []
    for user in all_users:
        user_status, last_event = AttendanceEvent.get_user_status(user.id, today)
        today_events = AttendanceEvent.get_daily_events(user.id, today)
        today_work_hours = AttendanceEvent.get_daily_work_hours(user.id, today)
        
        users_data.append({
            'user': user,
            'status': user_status,
            'last_event': last_event,
            'today_events': today_events,
            'today_work_hours': today_work_hours
        })
    
    # Sort by sede and then by name
    users_data.sort(key=lambda x: (x['user'].sede.nome if x['user'].sede else 'ZZZ', 
                                  x['user'].last_name, 
                                  x['user'].first_name))
    
    # Get all sedi for filtering
    all_sedi = []
    if current_user.role == 'Amministratore' or current_user.all_sedi:
        all_sedi = Sede.query.filter_by(active=True).order_by(Sede.nome).all()
    elif current_user.sede_id:
        all_sedi = [current_user.sede]
    
    return render_template('dashboard_team.html', 
                         users_data=users_data,
                         all_sedi=all_sedi,
                         today=today,
                         format_hours=format_hours)

@dashboard_bp.route('/dashboard_sede')
@login_required
def dashboard_sede():
    """Dashboard specifica per sede - mostra dati aggregati per sede"""
    if not current_user.can_view_all_attendance():
        flash('Non hai i permessi per visualizzare questo contenuto.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    # Get accessible sedi for current user
    if current_user.role == 'Amministratore' or current_user.all_sedi:
        available_sedi = Sede.query.filter_by(active=True).order_by(Sede.nome).all()
    elif current_user.sede_id:
        available_sedi = [current_user.sede]
    else:
        available_sedi = []
    
    # Get selected sede from query parameter
    selected_sede_id = request.args.get('sede_id', type=int)
    selected_sede = None
    
    if selected_sede_id:
        selected_sede = Sede.query.get(selected_sede_id)
        # Verify user has access to this sede
        if selected_sede and not (
            current_user.role == 'Amministratore' or 
            current_user.all_sedi or 
            current_user.sede_id == selected_sede_id
        ):
            selected_sede = None
            flash('Non hai accesso ai dati di questa sede.', 'warning')
    
    # If no valid sede selected, default to user's sede
    if not selected_sede and current_user.sede_id:
        selected_sede = current_user.sede
    
    sede_data = {}
    if selected_sede:
        # Get users from selected sede
        sede_users = User.query.filter(
            User.sede_id == selected_sede.id,
            User.active.is_(True),
            ~User.role.in_(['Admin', 'Staff'])
        ).all()
        
        # Get today's attendance data for sede users
        today = date.today()
        attendance_summary = {
            'total_users': len(sede_users),
            'users_in': 0,
            'users_out': 0,
            'users_on_break': 0,
            'total_work_hours': 0
        }
        
        user_details = []
        for user in sede_users:
            user_status, last_event = AttendanceEvent.get_user_status(user.id, today)
            today_work_hours = AttendanceEvent.get_daily_work_hours(user.id, today)
            
            # Update summary counts
            if user_status == 'in':
                attendance_summary['users_in'] += 1
            elif user_status == 'on_break':
                attendance_summary['users_on_break'] += 1
            else:
                attendance_summary['users_out'] += 1
            
            attendance_summary['total_work_hours'] += today_work_hours
            
            user_details.append({
                'user': user,
                'status': user_status,
                'last_event': last_event,
                'today_work_hours': today_work_hours
            })
        
        # Sort user details by name
        user_details.sort(key=lambda x: (x['user'].last_name, x['user'].first_name))
        
        sede_data = {
            'sede': selected_sede,
            'attendance_summary': attendance_summary,
            'user_details': user_details
        }
    
    return render_template('dashboard_sede.html',
                         available_sedi=available_sedi,
                         selected_sede=selected_sede,
                         sede_data=sede_data,
                         format_hours=format_hours)

@dashboard_bp.route('/ente-home')
@login_required
def ente_home():
    """Home page speciale per enti/organizzazioni - dashboard semplificata"""
    # Questa è una dashboard alternativa più semplice per certi tipi di utenti
    
    # Get basic user stats
    stats = get_user_statistics(current_user.id)
    
    # Get today's attendance status
    today_date = date.today()
    user_status = 'out'
    today_events = []
    today_work_hours = 0
    
    if current_user.can_view_attendance():
        user_status, _ = AttendanceEvent.get_user_status(current_user.id, today_date)
        today_events = AttendanceEvent.get_daily_events(current_user.id, today_date)
        today_work_hours = AttendanceEvent.get_daily_work_hours(current_user.id, today_date)
    
    # Get recent leave requests
    recent_leaves = []
    if current_user.can_view_my_leave():
        recent_leaves = LeaveRequest.query.filter(
            LeaveRequest.user_id == current_user.id
        ).order_by(LeaveRequest.created_at.desc()).limit(3).all()
    
    # Get upcoming shifts
    upcoming_shifts = []
    if current_user.can_view_shifts():
        seven_days_from_now = date.today() + timedelta(days=7)
        upcoming_shifts = Shift.query.filter(
            Shift.user_id == current_user.id,
            Shift.date >= date.today(),
            Shift.date <= seven_days_from_now
        ).order_by(Shift.date, Shift.start_time).limit(5).all()
    
    return render_template('ente_home.html',
                         stats=stats,
                         today_date=today_date,
                         user_status=user_status,
                         today_events=today_events,
                         today_work_hours=today_work_hours,
                         recent_leaves=recent_leaves,
                         upcoming_shifts=upcoming_shifts,
                         format_hours=format_hours)