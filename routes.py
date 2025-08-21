# WORKLY - WORKFORCE MANAGEMENT ROUTES
# Organized by functional areas for better maintainability
#
# 1. Global Configuration & Utilities
# 16. API Endpoints
#
# Flask Core Imports
from flask import render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
# Standard Library Imports
from datetime import datetime, date, timedelta, time
from urllib.parse import urlparse, urljoin
import re
import qrcode
import base64
import json
from defusedcsv import csv
# Application Imports
from app import app, db, csrf
from config import get_config
# SQLAlchemy Imports
from sqlalchemy.orm import joinedload
# Model Imports
from models import (
    User, AttendanceEvent, LeaveRequest, LeaveType, Shift, ShiftTemplate, 
    ReperibilitaShift, ReperibilitaTemplate, ReperibilitaIntervention, Intervention,
    Sede, WorkSchedule, UserRole, PresidioCoverage, PresidioCoverageTemplate,
    ReperibilitaCoverage, Holiday, PasswordResetToken, OvertimeType, OvertimeRequest,
    ExpenseCategory, ExpenseReport, ACITable, MileageRequest,
    italian_now, get_active_presidio_templates, get_presidio_coverage_for_day
)
# Form Imports
from forms import (
    LoginForm, UserForm, UserProfileForm, AttendanceForm, LeaveRequestForm, LeaveTypeForm,
    ShiftForm, ShiftTemplateForm, SedeForm, WorkScheduleForm, RoleForm,
    PresidioCoverageTemplateForm, PresidioCoverageForm, PresidioCoverageSearchForm,
    ForgotPasswordForm, ResetPasswordForm, OvertimeTypeForm, OvertimeRequestForm,
    ApproveOvertimeForm, OvertimeFilterForm, ACIUploadForm, ACIRecordForm, ACIFilterForm,
    MileageRequestForm, ApproveMileageForm, MileageFilterForm
)
# Utility Imports
from utils import (
    get_user_statistics, get_team_statistics, format_hours, 
    check_user_schedule_with_permissions, send_overtime_request_message
)
# Blueprint registration will be handled at the end of this file
# GLOBAL CONFIGURATION AND UTILITY FUNCTIONS
@app.context_processor
def inject_config():
    """Inject configuration into all templates"""
    config = get_config()
    return dict(config=config)
def require_login(f):
    """Decorator to require login for routes"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
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
# CORE NAVIGATION ROUTES
@app.route('/')
def index():
    """Main entry point - redirect to appropriate dashboard"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    return redirect(url_for('auth.login'))
# AUTHENTICATION ROUTES - MOVED TO routes/auth.py BLUEPRINT
# ATTENDANCE & CLOCK IN/OUT ROUTES 
# Le routes Attendance sono state migrate al blueprint blueprints/attendance.py
# SHIFT MANAGEMENT ROUTES (non ancora migrati)  
# Il codice duplicato verrà rimosso sistematicamente
# FINE RIMOZIONE CODICE DUPLICATO
# SHIFT MANAGEMENT ROUTES
# delete_template migrated to shifts module
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
# view_template migrated to shifts module
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
                         today=datetime.now().date(),
                         total_hours=round(total_hours, 1),
                         future_shifts=future_shifts,
                         unique_users=unique_users,
                         user_hours_list=user_hours_list,
                         get_italian_weekday=get_italian_weekday,
                         can_manage=can_manage,
                         view_mode=view_mode)
# LEAVE MANAGEMENT ROUTES
# leave_types moved to leave blueprint
# All functions moved to respective blueprint modules
# Routes.py cleanup complete - only essential utilities remain
    # Per utenti non-admin, verifica accesso alla sede specifica
    if not current_user.all_sedi and current_user.sede_obj and current_user.sede_obj.id != sede_id:
        flash('Non hai accesso a questa sede specifica', 'danger')
