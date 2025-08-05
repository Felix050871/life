"""
Dashboard Routes
Main dashboard and overview functionality
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import date, datetime, timedelta

from app import db
from models import AttendanceEvent, User
from utils import get_user_statistics, get_team_statistics

# Create blueprint
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
    user_status, last_event = AttendanceEvent.get_user_status(current_user.id)
    work_hours_today = AttendanceEvent.get_daily_work_hours(current_user.id, today_date)
    
    # Ottieni le richieste di permesso recenti per l'utente corrente
    recent_leave_requests = []
    if hasattr(current_user, 'can_view_leaves') and (current_user.can_view_leaves() or current_user.can_manage_leaves()):
        from models import LeaveRequest
        recent_leave_requests = LeaveRequest.query.filter_by(
            user_id=current_user.id
        ).order_by(LeaveRequest.created_at.desc()).limit(5).all()
    
    # Ottieni turni futuri per l'utente corrente
    upcoming_shifts = []
    if hasattr(current_user, 'can_view_shifts') and current_user.can_view_shifts():
        from models import Shift
        upcoming_shifts = Shift.query.filter(
            Shift.user_id == current_user.id,
            Shift.date >= date.today(),
            Shift.active == True
        ).order_by(Shift.date, Shift.start_time).limit(5).all()
    
    # Ottieni reperibilità future
    upcoming_reperibilita = []
    if hasattr(current_user, 'can_view_reperibilita') and current_user.can_view_reperibilita():
        from models import ReperibilitaShift
        upcoming_reperibilita = ReperibilitaShift.query.filter(
            ReperibilitaShift.user_id == current_user.id,
            ReperibilitaShift.date >= date.today(),
            ReperibilitaShift.active == True
        ).order_by(ReperibilitaShift.date).limit(5).all()
    
    # Ottieni richieste di rimborso chilometrico recenti  
    recent_mileage_requests = []
    if hasattr(current_user, 'can_view_mileage_requests') and current_user.can_view_mileage_requests():
        from models import MileageRequest
        recent_mileage_requests = MileageRequest.query.filter_by(
            user_id=current_user.id
        ).order_by(MileageRequest.created_at.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                         stats=stats, 
                         team_stats=team_stats,
                         today_attendance=today_attendance,
                         user_status=user_status,
                         last_event=last_event,
                         work_hours_today=work_hours_today,
                         recent_leave_requests=recent_leave_requests,
                         upcoming_shifts=upcoming_shifts,
                         upcoming_reperibilita=upcoming_reperibilita,
                         recent_mileage_requests=recent_mileage_requests)

@dashboard_bp.route('/reports')
@login_required
def reports():
    if not current_user.can_view_reports():
        flash('Non hai i permessi per visualizzare i report', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
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
    except Exception:
        team_stats = {
            'active_users': 0,
            'total_hours': 0,
            'shifts_this_period': 0,
            'avg_hours_per_user': 0
        }
    
    # Get user statistics for all active users (excluding Amministratore and Ospite)
    users = User.query.filter_by(active=True).filter(~User.role.in_(['Amministratore', 'Ospite'])).all()
    
    user_stats = []
    chart_data = []
    
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
        except Exception:
            continue
    
    # Get interventions data for the table
    from models import Intervention, ReperibilitaIntervention
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    try:
        # Interventi generici
        interventions = Intervention.query.filter(
            Intervention.start_datetime >= start_datetime,
            Intervention.start_datetime <= end_datetime
        ).order_by(Intervention.start_datetime.desc()).all()
        
        # Interventi di reperibilità  
        reperibilita_interventions = ReperibilitaIntervention.query.filter(
            ReperibilitaIntervention.start_datetime >= start_datetime,
            ReperibilitaIntervention.start_datetime <= end_datetime
        ).order_by(ReperibilitaIntervention.start_datetime.desc()).all()
        
    except Exception:
        interventions = []
        reperibilita_interventions = []
    
    return render_template('reports.html',
                         team_stats=team_stats,
                         user_stats=user_stats,
                         chart_data=chart_data,
                         interventions=interventions,
                         reperibilita_interventions=reperibilita_interventions,
                         start_date=start_date,
                         end_date=end_date)