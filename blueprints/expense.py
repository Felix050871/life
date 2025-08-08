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
from models import User, ExpenseReport, ExpenseCategory, OvertimeRequest, OvertimeType, MileageRequest
from forms import ExpenseFilterForm, ExpenseReportForm, OvertimeRequestForm, MileageRequestForm, MileageFilterForm
from app import db, app
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename
import uuid

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
    """Visualizza elenco note spese"""
    filter_form = ExpenseFilterForm(current_user=current_user)
    
    # Query base
    query = ExpenseReport.query
    
    # Check view mode from URL parameter
    view_mode = request.args.get('view', 'all')
    
    # Usa i nuovi permessi espliciti per determinare cosa può vedere l'utente
    if view_mode == 'my' or current_user.can_view_my_expense_reports() and not current_user.can_view_expense_reports():
        # Mostra solo le note spese dell'utente corrente
        query = query.filter(ExpenseReport.employee_id == current_user.id)
        page_title = "Le Mie Note Spese"
    elif current_user.can_view_expense_reports() or current_user.can_approve_expense_reports():
        # Utente può vedere tutte le note spese (eventualmente filtrate per sede)
        if not current_user.all_sedi and current_user.sede_id:
            # Filtra per sede se non ha accesso globale
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

@expense_bp.route('/reports/create', methods=['GET', 'POST'])
@login_required
def create_expense_report():
    """Crea nuova nota spese"""
    if not current_user.can_create_expense_reports():
        flash('Non hai i permessi per creare note spese', 'danger')
        return redirect(url_for('expense.expense_reports'))
    
    form = ExpenseReportForm()
    
    if form.validate_on_submit():
        # Gestione upload file
        receipt_filename = None
        if form.receipt_file.data:
            file = form.receipt_file.data
            filename = secure_filename(file.filename)
            
            # Crea nome file unico
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
        return redirect(url_for('expense.expense_reports'))
    
    return render_template('create_expense_report.html', form=form)

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
    """Gestione richieste straordinario"""
    from models import OvertimeRequest, OvertimeType
    from forms import OvertimeFilterForm
    
    filter_form = OvertimeFilterForm()
    
    # Query base
    query = OvertimeRequest.query
    
    # Filtra per sede se l'utente non ha accesso globale
    if not current_user.all_sedi and current_user.sede_id:
        sede_users = User.query.filter(User.sede_id == current_user.sede_id).with_entities(User.id).all()
        sede_user_ids = [u.id for u in sede_users]
        query = query.filter(OvertimeRequest.employee_id.in_(sede_user_ids))
    
    # Applica filtri
    if filter_form.validate_on_submit():
        if filter_form.user_id.data:
            query = query.filter(OvertimeRequest.employee_id == filter_form.user_id.data)
        if filter_form.status.data:
            query = query.filter(OvertimeRequest.status == filter_form.status.data)
        if filter_form.overtime_type_id.data:
            query = query.filter(OvertimeRequest.overtime_type_id == filter_form.overtime_type_id.data)
        if filter_form.date_from.data:
            query = query.filter(OvertimeRequest.overtime_date >= filter_form.date_from.data)
        if filter_form.date_to.data:
            query = query.filter(OvertimeRequest.overtime_date <= filter_form.date_to.data)
    
    # Ordina per data più recente
    requests = query.order_by(OvertimeRequest.overtime_date.desc()).all()
    
    return render_template('overtime_requests.html', 
                         requests=requests, 
                         form=filter_form)

@expense_bp.route('/overtime/requests/create', methods=['GET', 'POST'])
@login_required
def create_overtime_request():
    """Creazione richiesta straordinario"""
    if not current_user.can_create_overtime_requests():
        flash('Non hai i permessi per creare richieste di straordinario.', 'warning')
        return redirect(url_for('dashboard.dashboard'))
    
    form = OvertimeRequestForm()
    if form.validate_on_submit():
        # Calcola le ore di straordinario
        start_datetime = datetime.combine(form.overtime_date.data, form.start_time.data)
        end_datetime = datetime.combine(form.overtime_date.data, form.end_time.data)
        hours = (end_datetime - start_datetime).total_seconds() / 3600
        
        overtime_request = OvertimeRequest(
            employee_id=current_user.id,
            overtime_date=form.overtime_date.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            motivation=form.motivation.data,
            overtime_type_id=form.overtime_type_id.data,
            status='pending'
        )
        db.session.add(overtime_request)
        db.session.commit()
        
        # Invia notifica automatica agli approvatori (se la funzione esiste)
        try:
            from utils import send_overtime_request_message
            send_overtime_request_message(overtime_request, 'created', current_user)
        except ImportError:
            pass  # Funzione di notifica non disponibile
        
        flash('Richiesta straordinario inviata con successo!', 'success')
        return redirect(url_for('expense.my_overtime_requests'))
    
    return render_template('create_overtime_request.html', form=form)

@expense_bp.route('/overtime/requests/my')
@login_required
def my_overtime_requests():
    """Le mie richieste straordinari"""
    if not current_user.can_view_my_overtime_requests():
        flash('Non hai i permessi per visualizzare le tue richieste di straordinario.', 'warning')
        return redirect(url_for('dashboard.dashboard'))
    
    requests = OvertimeRequest.query.filter_by(employee_id=current_user.id).options(
        joinedload(OvertimeRequest.overtime_type)
    ).order_by(OvertimeRequest.created_at.desc()).all()
    
    return render_template('my_overtime_requests.html', requests=requests)

@expense_bp.route('/overtime/requests/<int:request_id>/approve', methods=['POST'])
@login_required
def approve_overtime_request(request_id):
    """Approva richiesta straordinario"""
    if not current_user.can_approve_overtime_requests():
        flash('Non hai i permessi per approvare richieste di straordinario.', 'warning')
        return redirect(url_for('expense.overtime_requests_management'))
    
    overtime_request = OvertimeRequest.query.get_or_404(request_id)
    
    if not current_user.all_sedi and overtime_request.employee.sede_id != current_user.sede_id:
        flash('Non puoi approvare richieste di altre sedi.', 'warning')
        return redirect(url_for('expense.overtime_requests_management'))
    
    overtime_request.status = 'approved'
    overtime_request.approval_comment = request.form.get('approval_comment', '')
    overtime_request.approved_by = current_user.id
    try:
        from utils import italian_now
        overtime_request.approved_at = italian_now()
    except ImportError:
        overtime_request.approved_at = datetime.now()
    
    db.session.commit()
    
    # Invia notifica automatica all'utente (se la funzione esiste)
    try:
        from utils import send_overtime_request_message
        send_overtime_request_message(overtime_request, 'approved', current_user)
    except ImportError:
        pass  # Funzione di notifica non disponibile
    
    flash('Richiesta straordinario approvata con successo!', 'success')
    return redirect(url_for('expense.overtime_requests_management'))

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
    """Visualizza le richieste di rimborso chilometrico"""
    try:
        if not (current_user.can_view_mileage_requests() or current_user.can_manage_mileage_requests()):
            flash('Non hai i permessi per visualizzare le richieste di rimborso chilometrico.', 'warning')
            return redirect(url_for('dashboard.dashboard'))
        
        # Filtri
        filter_form = MileageFilterForm(current_user=current_user)
        
        # Base query
        query = MileageRequest.query.options(
            joinedload(MileageRequest.user),
            joinedload(MileageRequest.approver),  
            joinedload(MileageRequest.vehicle)
        )
        
        # Filtri per sede (se l'utente non ha accesso globale)
        if not current_user.all_sedi and current_user.sede_id:
            query = query.join(User, MileageRequest.user_id == User.id).filter(User.sede_id == current_user.sede_id)
        
        # Applica filtri dal form
        if request.method == 'POST' and filter_form.validate_on_submit():
            if filter_form.status.data:
                query = query.filter(MileageRequest.status == filter_form.status.data)
            if filter_form.user_id.data:
                query = query.filter(MileageRequest.user_id == filter_form.user_id.data)
            if filter_form.date_from.data:
                query = query.filter(MileageRequest.travel_date >= filter_form.date_from.data)
            if filter_form.date_to.data:
                query = query.filter(MileageRequest.travel_date <= filter_form.date_to.data)
        
        # Ordina per data più recente
        requests = query.order_by(MileageRequest.created_at.desc()).all()
        
        return render_template('mileage_requests.html', requests=requests, filter_form=filter_form)
    except Exception as e:
        flash('Errore nel caricamento delle richieste di rimborso.', 'danger')
        return redirect(url_for('dashboard.dashboard'))

@expense_bp.route('/mileage/requests/create', methods=['GET', 'POST'])
@login_required
def create_mileage_request():
    """Crea una nuova richiesta di rimborso chilometrico"""
    if not current_user.can_create_mileage_requests():
        flash('Non hai i permessi per creare richieste di rimborso chilometrico.', 'warning')
        return redirect(url_for('dashboard.dashboard'))
    
    # Controlla se l'utente ha un veicolo ACI assegnato
    if not current_user.aci_vehicle_id:
        flash('Non puoi creare richieste di rimborso chilometrico senza avere un veicolo ACI assegnato. Contatta l\'amministratore per associare un veicolo al tuo profilo.', 'warning')
        return redirect(url_for('expense.my_mileage_requests'))
    
    form = MileageRequestForm(user=current_user)
    
    if form.validate_on_submit():
        try:
            # Converti route_addresses da stringa a array
            route_addresses_list = []
            if form.route_addresses.data:
                # Dividi per righe e filtra righe vuote
                route_addresses_list = [addr.strip() for addr in form.route_addresses.data.split('\n') if addr.strip()]
            
            # Crea la richiesta
            mileage_request = MileageRequest(
                user_id=current_user.id,
                travel_date=form.travel_date.data,
                route_addresses=route_addresses_list,  # Array invece di stringa
                total_km=form.total_km.data,
                is_km_manual=form.is_km_manual.data,
                purpose=form.purpose.data,
                notes=form.notes.data,
                vehicle_id=form.vehicle_id.data if form.vehicle_id.data else None,
                vehicle_description=form.vehicle_description.data if form.vehicle_description.data else None
            )
            
            # Calcola l'importo del rimborso
            mileage_request.calculate_reimbursement_amount()
            
            db.session.add(mileage_request)
            db.session.commit()
            
            flash('Richiesta di rimborso chilometrico inviata con successo!', 'success')
            return redirect(url_for('expense.my_mileage_requests'))
            
        except Exception as e:
            db.session.rollback()
            flash('Errore nella creazione della richiesta di rimborso. Riprova più tardi.', 'danger')
            return render_template('create_mileage_request.html', form=form)
    
    return render_template('create_mileage_request.html', form=form)

@expense_bp.route('/mileage/requests/my')
@login_required
def my_mileage_requests():
    """Visualizza le richieste di rimborso chilometrico dell'utente corrente"""
    try:
        if not current_user.can_view_my_mileage_requests():
            flash('Non hai i permessi per visualizzare le tue richieste di rimborso chilometrico.', 'warning')
            return redirect(url_for('dashboard.dashboard'))
        
        requests = MileageRequest.query.filter_by(user_id=current_user.id)\
                                      .options(joinedload(MileageRequest.approver),
                                              joinedload(MileageRequest.vehicle))\
                                      .order_by(MileageRequest.created_at.desc()).all()
        
        return render_template('my_mileage_requests.html', requests=requests)
    except Exception as e:
        flash('Errore nel caricamento delle richieste di rimborso.', 'danger')
        return redirect(url_for('dashboard.dashboard'))

@expense_bp.route('/mileage/requests/<int:request_id>/approve', methods=['POST'])
@login_required
def approve_mileage_request(request_id):
    """Approva una richiesta di rimborso chilometrico"""
    if not current_user.can_approve_mileage_requests():
        flash('Non hai i permessi per approvare richieste di rimborso chilometrico.', 'warning')
        return redirect(url_for('expense.mileage_requests'))
    
    mileage_request = MileageRequest.query.get_or_404(request_id)
    
    # Controllo per sede se necessario
    if not current_user.all_sedi and current_user.sede_id:
        if mileage_request.user.sede_id != current_user.sede_id:
            flash('Non puoi approvare richieste di utenti di altre sedi.', 'warning')
            return redirect(url_for('expense.mileage_requests'))
    
    action = request.form.get('action')
    comment = request.form.get('comment', '')
    
    if action == 'approve':
        mileage_request.status = 'approved'
        mileage_request.approval_comment = comment
        mileage_request.approved_by = current_user.id
        try:
            from utils import italian_now
            mileage_request.approved_at = italian_now()
        except ImportError:
            mileage_request.approved_at = datetime.now()
        
        flash('Richiesta di rimborso chilometrico approvata con successo!', 'success')
    elif action == 'reject':
        if not comment:
            flash('Il commento è obbligatorio per rifiutare una richiesta.', 'warning')
            return redirect(url_for('expense.mileage_requests'))
        
        mileage_request.status = 'rejected'
        mileage_request.approval_comment = comment
        mileage_request.approved_by = current_user.id
        try:
            from utils import italian_now
            mileage_request.approved_at = italian_now()
        except ImportError:
            mileage_request.approved_at = datetime.now()
        
        flash('Richiesta di rimborso chilometrico rifiutata.', 'success')
    else:
        flash('Azione non valida.', 'danger')
        return redirect(url_for('expense.mileage_requests'))
    
    db.session.commit()
    
    # Invia notifica automatica all'utente (se la funzione esiste)
    try:
        from utils import send_mileage_request_message
        send_mileage_request_message(mileage_request, action, current_user)
    except ImportError:
        pass  # Funzione di notifica non disponibile
    
    return redirect(url_for('expense.mileage_requests'))

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