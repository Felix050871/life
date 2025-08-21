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
# All shift management functions migrated to shifts blueprint
