# =============================================================================
# EXPENSE & FINANCIAL MANAGEMENT BLUEPRINT
# =============================================================================
# Blueprint for managing expense reports, overtime requests, mileage reimbursements
# and all related financial operations including categories and approvals
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response, send_file
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from io import BytesIO
from defusedcsv import csv
import os

# Local imports - Add as needed during migration
# Only import existing models - others will be added during migration
from models import User
from app import db

# =============================================================================
# BLUEPRINT CONFIGURATION
# =============================================================================

expense_bp = Blueprint(
    'expense', 
    __name__, 
    url_prefix='/expense',
    template_folder='../templates',
    static_folder='../static'
)

# =============================================================================
# PERMISSION DECORATORS
# =============================================================================

def require_expense_permission(f):
    """Decorator to check expense viewing permission"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.can_view_expense_reports():
            flash('Non hai i permessi per visualizzare le note spese', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def require_manage_expense_permission(f):
    """Decorator to check expense management permission"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.can_manage_expense_reports():
            flash('Non hai i permessi per gestire le note spese', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def require_overtime_permission(f):
    """Decorator to check overtime permission"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.can_view_overtime_requests():
            flash('Non hai i permessi per visualizzare gli straordinari', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def require_mileage_permission(f):
    """Decorator to check mileage permission"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.can_view_mileage_requests():
            flash('Non hai i permessi per visualizzare i rimborsi chilometrici', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# EXPENSE REPORTS ROUTES
# =============================================================================

@expense_bp.route('/reports', methods=['GET', 'POST'])
@login_required
@require_expense_permission
def expense_reports():
    """Main expense reports page"""
    # Placeholder for expense reports logic - will be migrated from routes.py
    pass

@expense_bp.route('/reports/create', methods=['GET', 'POST'])
@login_required
def create_expense_report():
    """Create new expense report"""
    # Placeholder for create expense logic - will be migrated from routes.py
    pass

@expense_bp.route('/reports/edit/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense_report(expense_id):
    """Edit existing expense report"""
    # Placeholder for edit expense logic - will be migrated from routes.py
    pass

@expense_bp.route('/reports/approve/<int:expense_id>', methods=['GET', 'POST'])
@login_required
@require_manage_expense_permission
def approve_expense_report(expense_id):
    """Approve expense report"""
    # Placeholder for approve expense logic - will be migrated from routes.py
    pass

@expense_bp.route('/reports/download/<int:expense_id>')
@login_required
def download_expense_receipt(expense_id):
    """Download expense receipt"""
    # Placeholder for download receipt logic - will be migrated from routes.py
    pass

@expense_bp.route('/reports/delete/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense_report(expense_id):
    """Delete expense report"""
    # Placeholder for delete expense logic - will be migrated from routes.py
    pass

# =============================================================================
# EXPENSE CATEGORIES ROUTES
# =============================================================================

@expense_bp.route('/categories')
@login_required
@require_expense_permission
def expense_categories():
    """Manage expense categories"""
    # Placeholder for categories logic - will be migrated from routes.py
    pass

@expense_bp.route('/categories/create', methods=['GET', 'POST'])
@login_required
@require_manage_expense_permission
def create_expense_category():
    """Create new expense category"""
    # Placeholder for create category logic - will be migrated from routes.py
    pass

@expense_bp.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
@require_manage_expense_permission
def edit_expense_category(category_id):
    """Edit expense category"""
    # Placeholder for edit category logic - will be migrated from routes.py
    pass

@expense_bp.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
@require_manage_expense_permission
def delete_expense_category(category_id):
    """Delete expense category"""
    # Placeholder for delete category logic - will be migrated from routes.py
    pass

# =============================================================================
# OVERTIME MANAGEMENT ROUTES
# =============================================================================

@expense_bp.route('/overtime/types')
@login_required
@require_overtime_permission
def overtime_types():
    """Manage overtime types"""
    # Placeholder for overtime types logic - will be migrated from routes.py
    pass

@expense_bp.route('/overtime/types/create', methods=['GET', 'POST'])
@login_required
def create_overtime_type():
    """Create overtime type"""
    # Placeholder for create overtime type logic - will be migrated from routes.py
    pass

@expense_bp.route('/overtime/types/<int:type_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_overtime_type(type_id):
    """Edit overtime type"""
    # Placeholder for edit overtime type logic - will be migrated from routes.py
    pass

@expense_bp.route('/overtime/types/<int:type_id>/delete', methods=['POST'])
@login_required
def delete_overtime_type(type_id):
    """Delete overtime type"""
    # Placeholder for delete overtime type logic - will be migrated from routes.py
    pass

@expense_bp.route('/overtime/requests')
@login_required
@require_overtime_permission
def overtime_requests_management():
    """Manage overtime requests"""
    # Placeholder for overtime requests logic - will be migrated from routes.py
    pass

@expense_bp.route('/overtime/requests/create', methods=['GET', 'POST'])
@login_required
def create_overtime_request():
    """Create overtime request"""
    # Placeholder for create overtime request logic - will be migrated from routes.py
    pass

@expense_bp.route('/overtime/requests/my')
@login_required
def my_overtime_requests():
    """View my overtime requests"""
    # Placeholder for my overtime requests logic - will be migrated from routes.py
    pass

@expense_bp.route('/overtime/requests/<int:request_id>/approve', methods=['POST'])
@login_required
def approve_overtime_request(request_id):
    """Approve overtime request"""
    # Placeholder for approve overtime logic - will be migrated from routes.py
    pass

@expense_bp.route('/overtime/requests/<int:request_id>/reject', methods=['POST'])
@login_required
def reject_overtime_request(request_id):
    """Reject overtime request"""
    # Placeholder for reject overtime logic - will be migrated from routes.py
    pass

@expense_bp.route('/overtime/requests/<int:request_id>/delete', methods=['POST'])
@login_required
def delete_overtime_request(request_id):
    """Delete overtime request"""
    # Placeholder for delete overtime logic - will be migrated from routes.py
    pass

# =============================================================================
# MILEAGE MANAGEMENT ROUTES
# =============================================================================

@expense_bp.route('/mileage/requests')
@login_required
@require_mileage_permission
def mileage_requests():
    """Manage mileage requests"""
    # Placeholder for mileage requests logic - will be migrated from routes.py
    pass

@expense_bp.route('/mileage/requests/create', methods=['GET', 'POST'])
@login_required
def create_mileage_request():
    """Create mileage request"""
    # Placeholder for create mileage logic - will be migrated from routes.py
    pass

@expense_bp.route('/mileage/requests/my')
@login_required
def my_mileage_requests():
    """View my mileage requests"""
    # Placeholder for my mileage requests logic - will be migrated from routes.py
    pass

@expense_bp.route('/mileage/requests/<int:request_id>/approve', methods=['POST'])
@login_required
def approve_mileage_request(request_id):
    """Approve mileage request"""
    # Placeholder for approve mileage logic - will be migrated from routes.py
    pass

@expense_bp.route('/mileage/requests/<int:request_id>/delete', methods=['POST'])
@login_required
def delete_mileage_request(request_id):
    """Delete mileage request"""
    # Placeholder for delete mileage logic - will be migrated from routes.py
    pass

# =============================================================================
# EXPORT ROUTES
# =============================================================================

@expense_bp.route('/export/expense_reports_excel')
@login_required
@require_expense_permission
def export_expense_reports_excel():
    """Export expense reports to Excel"""
    # Placeholder for expense export logic - will be migrated from routes.py
    pass

@expense_bp.route('/export/overtime_requests_excel')
@login_required
@require_overtime_permission
def overtime_requests_excel():
    """Export overtime requests to Excel"""
    # Placeholder for overtime export logic - will be migrated from routes.py
    pass

@expense_bp.route('/export/mileage_requests')
@login_required
@require_mileage_permission
def export_mileage_requests():
    """Export mileage requests"""
    # Placeholder for mileage export logic - will be migrated from routes.py
    pass

# =============================================================================
# BLUEPRINT REGISTRATION READY
# =============================================================================
# This blueprint is ready to be registered in main.py:
# from blueprints.expense import expense_bp
# app.register_blueprint(expense_bp)
# =============================================================================