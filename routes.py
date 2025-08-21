# WORKLY - WORKFORCE MANAGEMENT ROUTES
# Organized by functional areas for better maintainability
#
# ROUTE ORGANIZATION:
# 1. Global Configuration & Utilities
# 2. Core Navigation Routes
# 3. Authentication Routes
# 4. Dashboard Routes
# 5. Attendance & Clock In/Out Routes
# 6. Shift Management Routes
# 7. Leave Management Routes
# 8. User Management Routes
# 9. Reports Routes
# 10. Holiday Management Routes
# 11. Reperibilità (On-Call) Routes
# 12. Expense Management Routes
# 13. Overtime Management Routes
# 14. Mileage Reimbursement Routes
# 15. Admin & System Management Routes
# 16. API Endpoints
#
# Total Routes: 169+
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
# Authentication routes now handled by auth_bp blueprint
# DASHBOARD ROUTES - MOVED TO blueprints/dashboard.py BLUEPRINT
# Dashboard routes now handled by dashboard_bp blueprint
# NEXT ROUTES TO MIGRATE: ATTENDANCE & CLOCK IN/OUT ROUTES
# ATTENDANCE & CLOCK IN/OUT ROUTES 
# API work_hours migrated to attendance blueprint
# ATTENDANCE & CLOCK IN/OUT ROUTES - MOVED TO blueprints/attendance.py BLUEPRINT  
# Attendance routes now handled by attendance_bp blueprint
# NEXT ROUTES TO MIGRATE: SHIFT MANAGEMENT ROUTES
# La prossima sezione con le vere Shift Management Routes inizia più avanti nel file
# Le routes Attendance sono state migrate al blueprint blueprints/attendance.py
# ROUTES NON ANCORA MIGRATE (da rimuovere quando migrazione completata)
# Prossime routes da migrare: Shift Management, Leave Management, etc.
# SHIFT MANAGEMENT ROUTES (non ancora migrati)  
# DUPLICATE FUNCTION REMOVED - La vera funzione turni_automatici() è alla riga ~941
# ATTENDANCE ROUTES COMPLETAMENTE MIGRATE A BLUEPRINT
# Il codice duplicato verrà rimosso sistematicamente
# FINE RIMOZIONE CODICE DUPLICATO
# NEXT SECTIONS: REMAINING ROUTES TO MIGRATE
# check_shift_before_clock_out migrated to attendance blueprint
# clock_out migrated to attendance blueprint
# break_start migrated to attendance blueprint
# break_end migrated to attendance blueprint
# turni_automatici route MOVED TO shifts_bp blueprint
# SHIFT MANAGEMENT ROUTES
# get_shifts_for_template_api route MOVED TO shifts_bp blueprint
# visualizza_turni route MOVED TO shifts_bp blueprint
# genera_turni_da_template route MOVED TO shifts_bp blueprint
# create_shift route MOVED TO shifts_bp blueprint
# generate_shifts route MOVED TO shifts_bp blueprint
# regenerate_template route MOVED TO shifts_bp blueprint
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
# leave_types migrated to leave module
@login_required
def leave_types():
    if not (current_user.can_manage_leave() or current_user.can_manage_leave_types()):
        flash('Non hai i permessi per gestire le tipologie di permesso', 'danger')
        return redirect(url_for('dashboard'))
    leave_types = LeaveType.query.order_by(LeaveType.name).all()
    return render_template('leave_types.html', leave_types=leave_types)
# leave_types/add migrated to leave module
@login_required
def add_leave_type_page():
    if not (current_user.can_manage_leave() or current_user.can_manage_leave_types()):
        flash('Non hai i permessi per aggiungere tipologie di permesso', 'danger')
        return redirect(url_for('leave_types'))
    if request.method == 'POST':
                pass
    filename = f'interventi_generici_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.xlsx'
    excel_path = os.path.join(temp_dir, filename)
    wb.save(excel_path)
    # Read file for response
    with open(excel_path, 'rb') as f:
        excel_data = f.read()
    # Cleanup
    os.remove(excel_path)
    os.rmdir(temp_dir)
    response = make_response(excel_data)
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
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
# ADMIN & SYSTEM MANAGEMENT ROUTES
        # Tipo
        ws.cell(row=row_idx, column=col, value=request.leave_type)
        col += 1
        # Motivo
        ws.cell(row=row_idx, column=col, value=request.reason or '-')
        col += 1
        # Stato
        status_cell = ws.cell(row=row_idx, column=col, value=request.status)
        if request.status == 'Approved':
            status_cell.fill = PatternFill(start_color="D4F8D4", end_color="D4F8D4", fill_type="solid")
        elif request.status == 'Rejected':
            status_cell.fill = PatternFill(start_color="F8D4D4", end_color="F8D4D4", fill_type="solid")
        elif request.status == 'Pending':
            status_cell.fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
        col += 1
        # Data Richiesta
        ws.cell(row=row_idx, column=col, value=request.created_at.strftime('%d/%m/%Y %H:%M'))
        col += 1
        # Approvato da
        ws.cell(row=row_idx, column=col, value=request.approved_by.get_full_name() if request.approved_by else '-')
        col += 1
        # Data Approvazione
        ws.cell(row=row_idx, column=col, value=request.approved_at.strftime('%d/%m/%Y %H:%M') if request.approved_at else '-')
        col += 1
    # Prepara la risposta
    # Salva in un buffer temporaneo
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    response.data = buffer.getvalue()
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response
# export_expense_reports_excel route MOVED TO expense_bp blueprint
    if not current_user.can_view_expense_reports() and not current_user.can_create_expense_reports():
        flash('Non hai i permessi per esportare le note spese', 'danger')
        return redirect(url_for('dashboard'))
        # Data Spesa
        ws.cell(row=row_idx, column=col, value=expense.expense_date.strftime('%d/%m/%Y'))
        col += 1
        # Categoria
        ws.cell(row=row_idx, column=col, value=expense.category.name if expense.category else '-')
        col += 1
        # Descrizione
        ws.cell(row=row_idx, column=col, value=expense.description)
        col += 1
        # Importo (come numero per calcoli Excel)
        ws.cell(row=row_idx, column=col, value=float(expense.amount))
        col += 1
        # Stato
        status_text = {
            'pending': 'In attesa',
            'approved': 'Approvata',
            'rejected': 'Rifiutata'
        }.get(expense.status, expense.status)
        status_cell = ws.cell(row=row_idx, column=col, value=status_text)
        if expense.status == 'approved':
            status_cell.fill = PatternFill(start_color="D4F8D4", end_color="D4F8D4", fill_type="solid")
        elif expense.status == 'rejected':
            status_cell.fill = PatternFill(start_color="F8D4D4", end_color="F8D4D4", fill_type="solid")
        elif expense.status == 'pending':
            status_cell.fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
        col += 1
        # Data Creazione
        ws.cell(row=row_idx, column=col, value=expense.created_at.strftime('%d/%m/%Y %H:%M'))
        col += 1
        # Approvato da
        approved_by_user = User.query.get(expense.approved_by) if expense.approved_by else None
        ws.cell(row=row_idx, column=col, value=approved_by_user.get_full_name() if approved_by_user else '-')
        col += 1
        # Data Approvazione
        ws.cell(row=row_idx, column=col, value=expense.approved_at.strftime('%d/%m/%Y %H:%M') if expense.approved_at else '-')
        col += 1
        # Note (campo approval_comment del modello)
        ws.cell(row=row_idx, column=col, value=expense.approval_comment or '-')
        col += 1
    # Prepara la risposta
    # Salva in un buffer temporaneo
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    response.data = buffer.getvalue()
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response
# GESTIONE TURNI PER SEDI
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
            PresidioCoverage.active == True
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
# def view_turni_coverage():
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
    coperture = PresidioCoverage.query.filter_by(active=True).order_by(
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
                'active_status': copertura.active and copertura.end_date >= date.today()
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
                         today=datetime.now().date(),
                         is_admin=(current_user.role == 'Admin'))
# def generate_turni_from_coverage():
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
    coperture = PresidioCoverage.query.filter_by(active=True).order_by(
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
                'active_status': copertura.active and copertura.end_date >= date.today(),
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
                         today=datetime.now().date(),
                         is_admin=(current_user.role == 'Admin'))
# def process_generate_turni_from_coverage():
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
            db.session.rollback()
            flash('Errore: categoria già esistente', 'danger')
    return render_template('create_expense_category.html', form=form)
    """Modifica categoria nota spese"""
    if not current_user.can_manage_expense_reports():
        flash('Non hai i permessi per modificare le categorie', 'danger')
        return redirect(url_for('expense_categories'))
    from models import ExpenseCategory
    from forms import ExpenseCategoryForm
    category = ExpenseCategory.query.get_or_404(category_id)
    form = ExpenseCategoryForm(obj=category)
    if form.validate_on_submit():
        category.name = form.name.data
        category.description = form.description.data
        category.active = form.active.data
            db.session.rollback()
            flash('Errore: nome categoria già esistente', 'danger')
    return render_template('edit_expense_category.html', form=form, category=category)
    """Elimina categoria nota spese"""
    if not current_user.can_manage_expense_reports():
        flash('Non hai i permessi per eliminare le categorie', 'danger')
        return redirect(url_for('expense_categories'))
    from models import ExpenseCategory
    category = ExpenseCategory.query.get_or_404(category_id)
    # Verifica se ci sono note spese associate
    if category.expense_reports and len(category.expense_reports) > 0:
        flash('Non è possibile eliminare una categoria con note spese associate', 'warning')
        return redirect(url_for('expense_categories'))
        db.session.rollback()
        flash('Errore nell\'eliminazione della categoria', 'danger')
    return redirect(url_for('expense_categories'))
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
# OVERTIME MANAGEMENT ROUTES
    """Visualizzazione e gestione tipologie straordinari"""
    if not (current_user.can_manage_overtime_types() or current_user.can_view_overtime_types()):
        flash('Non hai i permessi per visualizzare le tipologie di straordinario.', 'warning')
        return redirect(url_for('dashboard'))
    types = OvertimeType.query.all()
    return render_template('overtime_types.html', types=types)
    """Creazione nuova tipologia straordinario"""
    if not (current_user.can_manage_overtime_types() or current_user.can_create_overtime_types()):
        flash('Non hai i permessi per creare tipologie di straordinario.', 'warning')
        return redirect(url_for('overtime_types'))
    form = OvertimeTypeForm()
    if form.validate_on_submit():
        overtime_type = OvertimeType(
            name=form.name.data,
            description=form.description.data,
            hourly_rate_multiplier=form.hourly_rate_multiplier.data,
            active=form.active.data
        )
        db.session.add(overtime_type)
        db.session.commit()
        flash('Tipologia straordinario creata con successo!', 'success')
        return redirect(url_for('overtime_types'))
    return render_template('create_overtime_type.html', form=form)
    """Visualizzazione richieste straordinari"""
    if not current_user.can_view_overtime_requests():
        flash('Non hai i permessi per visualizzare le richieste di straordinario.', 'warning')
        return redirect(url_for('dashboard'))
    # Filtro per sede con join esplicito per evitare ambiguità
    if current_user.all_sedi:
        requests = OvertimeRequest.query.options(
            joinedload(OvertimeRequest.employee),
            joinedload(OvertimeRequest.overtime_type)
        ).order_by(OvertimeRequest.created_at.desc()).all()
    else:
        requests = OvertimeRequest.query.join(
            User, OvertimeRequest.employee_id == User.id
        ).filter(
            User.sede_id == current_user.sede_id
        ).options(
            joinedload(OvertimeRequest.employee),
            joinedload(OvertimeRequest.overtime_type)
        ).order_by(OvertimeRequest.created_at.desc()).all()
    # Crea form per filtri
    form = OvertimeFilterForm()
    return render_template('overtime_requests.html', requests=requests, form=form)
    """Creazione richiesta straordinario"""
    if not current_user.can_create_overtime_requests():
        flash('Non hai i permessi per creare richieste di straordinario.', 'warning')
        return redirect(url_for('dashboard'))
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
        # Invia notifica automatica agli approvatori
        send_overtime_request_message(overtime_request, 'created', current_user)
        flash('Richiesta straordinario inviata con successo!', 'success')
        return redirect(url_for('my_overtime_requests'))
    return render_template('create_overtime_request.html', form=form)
    """Le mie richieste straordinari"""
    if not current_user.can_view_my_overtime_requests():
        flash('Non hai i permessi per visualizzare le tue richieste di straordinario.', 'warning')
        return redirect(url_for('dashboard'))
    requests = OvertimeRequest.query.filter_by(employee_id=current_user.id).options(
        joinedload(OvertimeRequest.overtime_type)
    ).order_by(OvertimeRequest.created_at.desc()).all()
    return render_template('my_overtime_requests.html', requests=requests)
# MILEAGE REIMBURSEMENT ROUTES
def calculate_approximate_distance(start_address, end_address):
    """Calcola distanza approssimativa tra due indirizzi italiani"""
    # Database semplificato di coordinate delle principali città italiane
    city_coords = {
        'roma': (41.9028, 12.4964),
        'milano': (45.4642, 9.1900),
        'napoli': (40.8518, 14.2681),
        'torino': (45.0703, 7.6869),
        'firenze': (43.7696, 11.2558),
        'bologna': (44.4949, 11.3426),
        'genova': (44.4056, 8.9463),
        'palermo': (38.1157, 13.3613),
        'bari': (41.1171, 16.8719),
        'catania': (37.5079, 15.0830),
        'venezia': (45.4408, 12.3155),
        'verona': (45.4384, 10.9916),
        'messina': (38.1938, 15.5540),
        'padova': (45.4064, 11.8768),
        'trieste': (45.6495, 13.7768),
        'brescia': (45.5416, 10.2118),
        'parma': (44.8015, 10.3279),
        'modena': (44.6471, 10.9252),
        'reggio calabria': (38.1059, 15.6219),
        'perugia': (43.1122, 12.3888)
    }
    def extract_city(address):
        """Estrae il nome della città dall'indirizzo"""
        address = address.lower().strip()
        # Cerca la città nell'indirizzo
        for city in city_coords.keys():
            if city in address:
                return city
        # Se non trova la città, prova a estrarre la prima parola
        first_word = address.split(',')[0].strip()
        if first_word in city_coords:
            return first_word
        return None
    def haversine_distance(coord1, coord2):
        """Calcola la distanza in km tra due coordinate usando la formula di Haversine"""
        import math
        lat1, lon1 = coord1
        lat2, lon2 = coord2
        # Converti in radianti
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        # Formula di Haversine
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        # Raggio della Terra in km
        r = 6371
        return c * r
    # Estrai le città dagli indirizzi
    start_city = extract_city(start_address)
    end_city = extract_city(end_address)
    if start_city and end_city and start_city in city_coords and end_city in city_coords:
        # Calcola la distanza reale tra le città
        distance = haversine_distance(city_coords[start_city], city_coords[end_city])
        # Aggiungi un fattore di correzione per le strade (circa 1.3x la distanza in linea d'aria)
        return distance * 1.3
    else:
        # Fallback: distanza approssimativa basata sulla lunghezza degli indirizzi
        return max(20, min(100, len(start_address) + len(end_address)))
# SISTEMA ACI - BACK OFFICE AMMINISTRATORE
# ACI HELPER FUNCTION MIGRATED TO aci_bp blueprint - admin_required
    """Visualizza tabelle ACI con caricamento lazy - record caricati solo dopo filtro"""
    form = ACIFilterForm()
    tables = []
    total_records = ACITable.query.count()
    # LAZY LOADING: carica record solo se è stato applicato un filtro (POST)
    if request.method == "POST" and form.validate_on_submit():
        query = ACITable.query
        # Applica filtri selezionati
        filters_applied = False
        if form.tipologia.data:
            query = query.filter(ACITable.tipologia == form.tipologia.data)
            filters_applied = True
        if form.marca.data:
            query = query.filter(ACITable.marca == form.marca.data)
            filters_applied = True
        if form.modello.data:
            query = query.filter(ACITable.modello == form.modello.data)
            filters_applied = True
        # Carica risultati solo se almeno un filtro è applicato
        if filters_applied:
            tables = query.order_by(ACITable.tipologia, ACITable.marca, ACITable.modello).all()
            import logging
            logging.info(f"ACI Tables: Caricati {len(tables)} record con filtri applicati")
        else:
            # Se nessun filtro è selezionato ma form è stato inviato, mostra messaggio
            flash("⚠️ Seleziona almeno un filtro prima di cercare", "warning")
    return render_template("aci_tables.html", 
                         tables=tables, 
                         form=form, 
                         total_records=total_records,
                         show_results=(request.method == "POST"))
    """API per ottenere le marche filtrate per tipologia"""
    tipologia = request.args.get('tipologia')
    query = db.session.query(ACITable.marca).distinct()
    if tipologia:
        query = query.filter(ACITable.tipologia == tipologia)
    marcas = [row.marca for row in query.order_by(ACITable.marca).all()]
    return jsonify(marcas)
    """API per ottenere i modelli filtrati per tipologia e marca"""
    tipologia = request.args.get('tipologia')
    marca = request.args.get('marca')
    query = db.session.query(ACITable.modello).distinct()
    if tipologia:
        query = query.filter(ACITable.tipologia == tipologia)
    if marca:
        query = query.filter(ACITable.marca == marca)
    modelos = [row.modello for row in query.order_by(ACITable.modello).all()]
    return jsonify(modelos)
    """Upload e importazione file Excel ACI"""
    form = ACIUploadForm()
    if form.validate_on_submit():
        file = form.excel_file.data
        tipologia = form.tipologia.data
                    pass
        # Salva in BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        # Response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=tabelle_aci_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        return response
    except Exception as e:
        flash(f"Errore durante l'export: {str(e)}", "danger")
        return redirect(url_for("aci_tables"))
    """Cancellazione in massa per tipologia"""
    tipologia = request.form.get('tipologia')
    if not tipologia:
        flash("Tipologia non specificata.", "warning")
        return redirect(url_for("aci_tables"))
