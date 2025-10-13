# =============================================================================
# REPORTS & EXPORT BLUEPRINT
# =============================================================================
# Blueprint for managing system reports and data export functionality
# Includes main reports page and all Excel/PDF export functions
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from io import BytesIO
from defusedcsv import csv
import base64

# Local imports - Add as needed during migration
# Import only essential models for reports functionality
from models import User, AttendanceEvent, Intervention, ReperibilitaIntervention
from utils import get_team_statistics, get_user_statistics
from utils_tenant import filter_by_company
from app import db

# =============================================================================
# BLUEPRINT CONFIGURATION
# =============================================================================

reports_bp = Blueprint(
    'reports', 
    __name__, 
    url_prefix='/reports',
    template_folder='../templates',
    static_folder='../static'
)

# =============================================================================
# PERMISSION DECORATORS
# =============================================================================

def require_reports_permission(f):
    """Decorator to check reports viewing permission"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.can_view_reports():
            flash('Non hai i permessi per visualizzare i report', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# MAIN REPORTS ROUTES
# =============================================================================

@reports_bp.route('/')
@login_required
@require_reports_permission
def reports():
    """Main reports page with team and user statistics"""
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
        pass  # Silent error handling
        team_stats = {
            'active_users': 0,
            'total_hours': 0,
            'shifts_this_period': 0,
            'avg_hours_per_user': 0
        }
    
    # Get user statistics for all active users (excluding Amministratore and Ospite)
    users = filter_by_company(User.query, User).filter_by(active=True).filter(~User.role.in_(['Amministratore', 'Ospite'])).all()
    
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
            
        except Exception as e:
            # Silent error handling for individual users
            continue
    
    # Get interventions data for the table (both types)
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    try:
        # General interventions
        interventions = filter_by_company(Intervention.query, Intervention).filter(
            Intervention.start_datetime >= start_datetime,
            Intervention.start_datetime <= end_datetime
        ).order_by(Intervention.start_datetime.desc()).all()
        
        # Reperibilità interventions  
        reperibilita_interventions = filter_by_company(ReperibilitaIntervention.query, ReperibilitaIntervention).filter(
            ReperibilitaIntervention.start_datetime >= start_datetime,
            ReperibilitaIntervention.start_datetime <= end_datetime
        ).order_by(ReperibilitaIntervention.start_datetime.desc()).all()
    except Exception as e:
        interventions = []
        reperibilita_interventions = []
    
    # Get attendance data for charts - calculate real data
    attendance_data = []
    current_date = start_date
    active_user_ids = [user.id for user in filter_by_company(User.query, User).filter(User.active.is_(True)).filter(~User.role.in_(['Amministratore', 'Ospite'])).all()]
    
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

# =============================================================================
# EXCEL EXPORT ROUTES
# =============================================================================

@reports_bp.route('/export_shifts_excel')
@login_required
@require_reports_permission
def export_shifts_excel():
    """Export shifts data to Excel format"""
    # Placeholder for shifts export logic
    # Will be migrated from routes.py
    pass

@reports_bp.route('/export_attendance_excel')
@login_required
@require_reports_permission
def export_attendance_excel():
    """Export attendance data to Excel format"""
    # Placeholder for attendance export logic
    # Will be migrated from routes.py
    pass

@reports_bp.route('/export_leave_requests_excel')
@login_required
@require_reports_permission
def export_leave_requests_excel():
    """Export leave requests to Excel format"""
    # Placeholder for leave requests export logic
    # Will be migrated from routes.py
    pass

@reports_bp.route('/export_interventions_excel')
@login_required
@require_reports_permission
def export_general_interventions_excel():
    """Export general interventions to Excel format"""
    # Placeholder for interventions export logic
    # Will be migrated from routes.py
    pass

@reports_bp.route('/export_reperibilita_interventions_excel')
@login_required
@require_reports_permission
def export_reperibilita_interventions_excel():
    """Export reperibilita interventions to Excel format"""
    # Placeholder for reperibilita interventions export logic
    # Will be migrated from routes.py
    pass

@reports_bp.route('/export_expense_reports_excel')
@login_required
@require_reports_permission
def export_expense_reports_excel():
    """Export expense reports to Excel format"""
    # Placeholder for expense reports export logic
    # Will be migrated from routes.py
    pass

@reports_bp.route('/export_overtime_excel')
@login_required
@require_reports_permission
def overtime_requests_excel():
    """Export overtime requests to Excel format"""
    # Placeholder for overtime export logic
    # Will be migrated from routes.py
    pass

@reports_bp.route('/export_mileage_requests')
@login_required
@require_reports_permission
def export_mileage_requests():
    """Export mileage reimbursement requests"""
    # Placeholder for mileage export logic
    # Will be migrated from routes.py
    pass

@reports_bp.route('/aci_export')
@login_required
@require_reports_permission
def aci_export():
    """Export ACI pricing data"""
    # Placeholder for ACI export logic
    # Will be migrated from routes.py
    pass

# =============================================================================
# PDF EXPORT ROUTES
# =============================================================================

@reports_bp.route('/export_shifts_pdf')
@login_required
@require_reports_permission
def export_shifts_pdf():
    """Export shifts data to PDF format"""
    # Placeholder for shifts PDF export logic
    # Will be migrated from routes.py
    pass

# =============================================================================
# BLUEPRINT REGISTRATION READY
# =============================================================================
# This blueprint is ready to be registered in main.py:
# from blueprints.reports import reports_bp
# app.register_blueprint(reports_bp)
# =============================================================================