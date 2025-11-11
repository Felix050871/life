# =============================================================================
# SOCIAL SAFETY NET (AMMORTIZZATORI SOCIALI) BLUEPRINT
# =============================================================================
#
# ROUTES INCLUSE:
# 1. manage_programs (GET) - Elenco programmi ammortizzatori sociali
# 2. create_program (GET/POST) - Creazione nuovo programma
# 3. edit_program (GET/POST) - Modifica programma esistente
# 4. delete_program (POST) - Eliminazione programma
# 5. program_detail (GET) - Dettaglio programma con assegnazioni
# 6. manage_assignments (GET) - Gestione assegnazioni dipendenti
# 7. create_assignment (GET/POST) - Assegnazione dipendente a programma
# 8. edit_assignment (GET/POST) - Modifica assegnazione
# 9. delete_assignment (POST) - Eliminazione assegnazione
# 10. approve_assignment (POST) - Approvazione assegnazione
# 11. compliance_report (GET) - Report compliance e scadenze
# 12. download_decree (GET) - Download file decreto
#
# Total routes: 12 social safety net management routes
# =============================================================================

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, send_from_directory
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from functools import wraps
from werkzeug.utils import secure_filename
import os
from app import db
from models import SocialSafetyNetProgram, SocialSafetyNetAssignment, User, ContractHistory, italian_now
from forms import SocialSafetyProgramForm, SocialSafetyAssignmentForm
from utils_tenant import filter_by_company, set_company_on_create, get_user_company_id
from utils_contract_history import create_contract_snapshot

# Create blueprint
social_safety_bp = Blueprint('social_safety', __name__, url_prefix='/ammortizzatori')

# Upload configuration
UPLOAD_FOLDER = 'uploads/social_safety_decrees'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    """Verifica se il file ha un'estensione consentita"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Helper function per permessi
def require_social_safety_permission(f):
    """Decorator per richiedere permessi ammortizzatori sociali"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        # Verifica permessi ammortizzatori
        if not current_user.can_access_social_safety_menu():
            flash('Non hai i permessi necessari per accedere a questa sezione.', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function


def require_manage_programs_permission(f):
    """Decorator per richiedere permesso gestione programmi"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.can_manage_social_safety_programs():
            flash('Non hai i permessi necessari per gestire i programmi.', 'danger')
            return redirect(url_for('social_safety.manage_programs'))
        return f(*args, **kwargs)
    return decorated_function


def require_assign_permission(f):
    """Decorator per richiedere permesso assegnazioni"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.can_assign_social_safety_programs():
            flash('Non hai i permessi necessari per gestire le assegnazioni.', 'danger')
            return redirect(url_for('social_safety.manage_programs'))
        return f(*args, **kwargs)
    return decorated_function


def require_reports_permission(f):
    """Decorator per richiedere permesso visualizzazione report (read-only)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.can_view_social_safety_reports():
            flash('Non hai i permessi necessari per visualizzare i report.', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# =============================================================================
# PROGRAMMI CRUD ROUTES
# =============================================================================

@social_safety_bp.route('/programmi')
@login_required
@require_social_safety_permission
def manage_programs():
    """Elenco e gestione programmi ammortizzatori sociali"""
    # Filtri dalla query string
    tipo_filter = request.args.get('tipo', '')
    stato_filter = request.args.get('stato', 'active')
    
    # Query base con filtro company
    query = filter_by_company(SocialSafetyNetProgram.query)
    
    # Applica filtri
    if tipo_filter:
        query = query.filter_by(program_type=tipo_filter)
    if stato_filter:
        query = query.filter_by(status=stato_filter)
    
    # Ordina per data fine (scadenze più vicine prima)
    programs = query.order_by(SocialSafetyNetProgram.end_date.asc()).all()
    
    # Statistiche
    total_programs = filter_by_company(SocialSafetyNetProgram.query).count()
    active_programs = filter_by_company(SocialSafetyNetProgram.query).filter_by(status='active').count()
    expired_programs = filter_by_company(SocialSafetyNetProgram.query).filter_by(status='expired').count()
    
    # Conteggio assegnazioni attive per ogni programma
    today = date.today()
    for program in programs:
        program.active_assignments_count = len([a for a in program.assignments 
                                                 if a.is_active_on_date(today)])
    
    # Tipi di programma disponibili
    program_types = ['CIGS', 'Solidarietà', 'FIS', 'CIG Ordinaria', 'Altro']
    
    return render_template('social_safety_programs.html',
                         programs=programs,
                         total_programs=total_programs,
                         active_programs=active_programs,
                         expired_programs=expired_programs,
                         program_types=program_types,
                         tipo_filter=tipo_filter,
                         stato_filter=stato_filter)


@social_safety_bp.route('/programmi/create', methods=['GET', 'POST'])
@login_required
@require_social_safety_permission
@require_manage_programs_permission
def create_program():
    """Creazione nuovo programma ammortizzatore sociale"""
    form = SocialSafetyProgramForm()
    
    if form.validate_on_submit():
        # Debug logging
        import logging
        logging.debug(f"Form data - reduction_type: {form.reduction_type.data}")
        logging.debug(f"Form data - reduction_percentage: {form.reduction_percentage.data}")
        logging.debug(f"Form data - target_weekly_hours: {form.target_weekly_hours.data}")
        # Gestione upload decreto
        decree_path = None
        if form.decree_file.data:
            file = form.decree_file.data
            if allowed_file(file.filename):
                # Crea la directory se non esiste
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                
                # Nome file sicuro con timestamp
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                
                file.save(filepath)
                decree_path = filepath
        
        program = SocialSafetyNetProgram(
            program_type=form.program_type.data,
            name=form.name.data,
            description=form.description.data,
            legal_basis=form.legal_basis.data,
            decree_number=form.decree_number.data,
            protocol_number=form.protocol_number.data,
            decree_file_path=decree_path,
            reduction_type=form.reduction_type.data,
            reduction_percentage=form.reduction_percentage.data if form.reduction_type.data == 'percentage' else None,
            target_weekly_hours=form.target_weekly_hours.data if form.reduction_type.data == 'fixed_hours' else None,
            payroll_code=form.payroll_code.data,
            inps_coverage=form.inps_coverage.data,
            overtime_forbidden=form.overtime_forbidden.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            status='active',
            created_by_id=current_user.id
        )
        set_company_on_create(program)
        db.session.add(program)
        db.session.commit()
        
        flash(f'Programma "{program.name}" creato con successo.', 'success')
        return redirect(url_for('social_safety.manage_programs'))
    
    return render_template('add_social_safety_program.html', form=form)


@social_safety_bp.route('/programmi/<int:program_id>/edit', methods=['GET', 'POST'])
@login_required
@require_social_safety_permission
@require_manage_programs_permission
def edit_program(program_id):
    """Modifica programma esistente"""
    program = filter_by_company(SocialSafetyNetProgram.query).filter_by(id=program_id).first_or_404()
    
    if request.method == 'POST':
        form = SocialSafetyProgramForm()
    else:
        # Popola il form con i valori del programma per il GET
        form = SocialSafetyProgramForm(data={
            'program_type': program.program_type,
            'name': program.name,
            'description': program.description,
            'legal_basis': program.legal_basis,
            'decree_number': program.decree_number,
            'protocol_number': program.protocol_number,
            'reduction_type': program.reduction_type,
            'reduction_percentage': program.reduction_percentage,
            'target_weekly_hours': program.target_weekly_hours,
            'payroll_code': program.payroll_code,
            'inps_coverage': program.inps_coverage,
            'overtime_forbidden': program.overtime_forbidden,
            'start_date': program.start_date,
            'end_date': program.end_date
        })
    
    if form.validate_on_submit():
        # Gestione upload nuovo decreto
        if form.decree_file.data:
            file = form.decree_file.data
            if allowed_file(file.filename):
                # Crea la directory se non esiste
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                
                # Elimina vecchio file se esiste
                if program.decree_file_path and os.path.exists(program.decree_file_path):
                    try:
                        os.remove(program.decree_file_path)
                    except:
                        pass
                
                # Salva nuovo file
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                
                file.save(filepath)
                program.decree_file_path = filepath
        
        # Aggiorna campi
        program.program_type = form.program_type.data
        program.name = form.name.data
        program.description = form.description.data
        program.legal_basis = form.legal_basis.data
        program.decree_number = form.decree_number.data
        program.protocol_number = form.protocol_number.data
        program.reduction_type = form.reduction_type.data
        program.reduction_percentage = form.reduction_percentage.data if form.reduction_type.data == 'percentage' else None
        program.target_weekly_hours = form.target_weekly_hours.data if form.reduction_type.data == 'fixed_hours' else None
        program.payroll_code = form.payroll_code.data
        program.inps_coverage = form.inps_coverage.data
        program.overtime_forbidden = form.overtime_forbidden.data
        program.start_date = form.start_date.data
        program.end_date = form.end_date.data
        program.updated_at = italian_now()
        
        db.session.commit()
        
        flash(f'Programma "{program.name}" aggiornato con successo.', 'success')
        return redirect(url_for('social_safety.manage_programs'))
    
    return render_template('edit_social_safety_program.html', form=form, program=program)


@social_safety_bp.route('/programmi/<int:program_id>/delete', methods=['POST'])
@login_required
@require_social_safety_permission
@require_manage_programs_permission
def delete_program(program_id):
    """Eliminazione programma"""
    program = filter_by_company(SocialSafetyNetProgram.query).filter_by(id=program_id).first_or_404()
    
    # Verifica se ci sono assegnazioni attive
    active_assignments = [a for a in program.assignments if a.status in ['approved', 'active']]
    if active_assignments:
        flash('Impossibile eliminare il programma: ci sono assegnazioni attive.', 'danger')
        return redirect(url_for('social_safety.manage_programs'))
    
    # Elimina file decreto se esiste
    if program.decree_file_path and os.path.exists(program.decree_file_path):
        try:
            os.remove(program.decree_file_path)
        except:
            pass
    
    program_name = program.name
    db.session.delete(program)
    db.session.commit()
    
    flash(f'Programma "{program_name}" eliminato con successo.', 'success')
    return redirect(url_for('social_safety.manage_programs'))


# =============================================================================
# ASSEGNAZIONI ROUTES
# =============================================================================

@social_safety_bp.route('/assegnazioni')
@login_required
@require_social_safety_permission
@require_assign_permission
def manage_assignments():
    """Gestione assegnazioni dipendenti"""
    # Filtri dalla query string
    status_filter = request.args.get('status', '')
    program_filter = request.args.get('program_id', '')
    
    # Query base con filtro company
    query = filter_by_company(SocialSafetyNetAssignment.query)
    
    # Applica filtri
    if status_filter:
        query = query.filter_by(status=status_filter)
    if program_filter:
        query = query.filter_by(program_id=program_filter)
    
    # Ordina per data inizio (più recenti prima)
    assignments = query.order_by(SocialSafetyNetAssignment.start_date.desc()).all()
    
    # Statistiche
    total_assignments = filter_by_company(SocialSafetyNetAssignment.query).count()
    pending_assignments = filter_by_company(SocialSafetyNetAssignment.query).filter_by(status='pending').count()
    active_assignments = filter_by_company(SocialSafetyNetAssignment.query).filter_by(status='active').count()
    
    # Programmi disponibili per filtro
    programs = filter_by_company(SocialSafetyNetProgram.query).filter_by(status='active').all()
    
    return render_template('social_safety_assignments.html',
                         assignments=assignments,
                         total_assignments=total_assignments,
                         pending_assignments=pending_assignments,
                         active_assignments=active_assignments,
                         programs=programs,
                         status_filter=status_filter,
                         program_filter=program_filter)


@social_safety_bp.route('/assegnazioni/create', methods=['GET', 'POST'])
@login_required
@require_social_safety_permission
@require_assign_permission
def create_assignment():
    """Assegnazione dipendente a programma"""
    form = SocialSafetyAssignmentForm()
    
    # Popola choices per select
    form.program_id.choices = [(p.id, f"{p.program_type} - {p.name}") 
                                for p in filter_by_company(SocialSafetyNetProgram.query).filter_by(status='active').all()]
    form.user_id.choices = [(u.id, f"{u.nome} {u.cognome}") 
                            for u in filter_by_company(User.query).filter_by(active=True).order_by(User.cognome, User.nome).all()]
    
    if form.validate_on_submit():
        # Crea snapshot contratto se richiesto
        contract_snapshot_id = None
        if form.create_contract_snapshot.data:
            user = User.query.get(form.user_id.data)
            if user and user.hr_data:
                from datetime import datetime
                # Converti date a datetime per effective_date
                effective_datetime = datetime.combine(form.start_date.data, datetime.min.time())
                snapshot = create_contract_snapshot(
                    user.hr_data,
                    changed_by_user_id=current_user.id,
                    notes=f"Inizio ammortizzatore sociale: {form.notes.data or 'N/A'}",
                    effective_date=effective_datetime
                )
                if snapshot:
                    contract_snapshot_id = snapshot.id
        
        assignment = SocialSafetyNetAssignment(
            program_id=form.program_id.data,
            user_id=form.user_id.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            custom_weekly_hours=form.custom_weekly_hours.data,
            custom_payroll_code=form.custom_payroll_code.data,
            notes=form.notes.data,
            status='pending',
            contract_snapshot_id=contract_snapshot_id,
            requested_by_id=current_user.id
        )
        set_company_on_create(assignment)
        db.session.add(assignment)
        db.session.commit()
        
        flash('Assegnazione creata con successo. In attesa di approvazione.', 'success')
        return redirect(url_for('social_safety.manage_assignments'))
    
    # TODO: Creare template dedicato
    flash('Funzionalità in fase di sviluppo', 'warning')
    return redirect(url_for('social_safety.manage_assignments'))


@social_safety_bp.route('/assegnazioni/<int:assignment_id>/edit', methods=['GET', 'POST'])
@login_required
@require_social_safety_permission
@require_assign_permission
def edit_assignment(assignment_id):
    """Modifica assegnazione esistente"""
    assignment = filter_by_company(SocialSafetyNetAssignment.query).filter_by(id=assignment_id).first_or_404()
    
    # Non permettere modifica se già attiva o completata
    if assignment.status in ['completed', 'cancelled']:
        flash('Impossibile modificare un\'assegnazione completata o annullata.', 'danger')
        return redirect(url_for('social_safety.manage_assignments'))
    
    form = SocialSafetyAssignmentForm(obj=assignment)
    
    # Popola choices per select
    form.program_id.choices = [(p.id, f"{p.program_type} - {p.name}") 
                                for p in filter_by_company(SocialSafetyNetProgram.query).filter_by(status='active').all()]
    form.user_id.choices = [(u.id, f"{u.nome} {u.cognome}") 
                            for u in filter_by_company(User.query).filter_by(active=True).order_by(User.cognome, User.nome).all()]
    
    if form.validate_on_submit():
        assignment.program_id = form.program_id.data
        assignment.user_id = form.user_id.data
        assignment.start_date = form.start_date.data
        assignment.end_date = form.end_date.data
        assignment.custom_weekly_hours = form.custom_weekly_hours.data
        assignment.custom_payroll_code = form.custom_payroll_code.data
        assignment.notes = form.notes.data
        assignment.updated_at = italian_now()
        
        db.session.commit()
        
        flash('Assegnazione aggiornata con successo.', 'success')
        return redirect(url_for('social_safety.manage_assignments'))
    
    # TODO: Creare template dedicato
    flash('Funzionalità in fase di sviluppo', 'warning')
    return redirect(url_for('social_safety.manage_assignments'))


@social_safety_bp.route('/assegnazioni/<int:assignment_id>/delete', methods=['POST'])
@login_required
@require_social_safety_permission
@require_assign_permission
def delete_assignment(assignment_id):
    """Eliminazione assegnazione"""
    assignment = filter_by_company(SocialSafetyNetAssignment.query).filter_by(id=assignment_id).first_or_404()
    
    # Non permettere eliminazione se attiva
    if assignment.status == 'active':
        flash('Impossibile eliminare un\'assegnazione attiva. Annullarla prima.', 'danger')
        return redirect(url_for('social_safety.manage_assignments'))
    
    user_name = f"{assignment.user.nome} {assignment.user.cognome}"
    db.session.delete(assignment)
    db.session.commit()
    
    flash(f'Assegnazione di {user_name} eliminata con successo.', 'success')
    return redirect(url_for('social_safety.manage_assignments'))


@social_safety_bp.route('/assegnazioni/<int:assignment_id>/approve', methods=['POST'])
@login_required
@require_social_safety_permission
@require_assign_permission
def approve_assignment(assignment_id):
    """Approvazione assegnazione"""
    assignment = filter_by_company(SocialSafetyNetAssignment.query).filter_by(id=assignment_id).first_or_404()
    
    if assignment.status != 'pending':
        flash('Solo le assegnazioni in stato pending possono essere approvate.', 'warning')
        return redirect(url_for('social_safety.manage_assignments'))
    
    assignment.approve(current_user)
    
    # Se la data di inizio è oggi o passata, attiva immediatamente
    if assignment.start_date <= date.today():
        assignment.activate()
    
    db.session.commit()
    
    flash(f'Assegnazione approvata con successo.', 'success')
    return redirect(url_for('social_safety.manage_assignments'))


@social_safety_bp.route('/assegnazioni/<int:assignment_id>/cancel', methods=['POST'])
@login_required
@require_social_safety_permission
@require_assign_permission
def cancel_assignment(assignment_id):
    """Annullamento assegnazione"""
    assignment = filter_by_company(SocialSafetyNetAssignment.query).filter_by(id=assignment_id).first_or_404()
    
    assignment.cancel()
    db.session.commit()
    
    flash('Assegnazione annullata con successo.', 'success')
    return redirect(url_for('social_safety.manage_assignments'))


# =============================================================================
# COMPLIANCE & REPORTING
# =============================================================================

@social_safety_bp.route('/compliance')
@login_required
@require_social_safety_permission
def compliance_report():
    """Report compliance e scadenze"""
    # Solo per utenti con permesso report
    if not current_user.can_view_social_safety_reports():
        flash('Non hai i permessi necessari per visualizzare i report.', 'danger')
        return redirect(url_for('social_safety.manage_programs'))
    
    # Programmi in scadenza (entro 30 giorni)
    today = date.today()
    expiring_threshold = today + timedelta(days=30)
    
    expiring_programs = filter_by_company(SocialSafetyNetProgram.query).filter(
        SocialSafetyNetProgram.status == 'active',
        SocialSafetyNetProgram.end_date <= expiring_threshold,
        SocialSafetyNetProgram.end_date >= today
    ).order_by(SocialSafetyNetProgram.end_date.asc()).all()
    
    # Assegnazioni attive per dipendente
    active_assignments = filter_by_company(SocialSafetyNetAssignment.query).filter(
        SocialSafetyNetAssignment.status.in_(['approved', 'active']),
        SocialSafetyNetAssignment.start_date <= today,
        SocialSafetyNetAssignment.end_date >= today
    ).all()
    
    # Assegnazioni in attesa di approvazione
    pending_assignments = filter_by_company(SocialSafetyNetAssignment.query).filter_by(status='pending').all()
    
    # Statistiche globali
    total_employees_affected = len(set([a.user_id for a in active_assignments]))
    total_active_programs = filter_by_company(SocialSafetyNetProgram.query).filter_by(status='active').count()
    
    # TODO: Creare template report compliance
    flash('Report compliance in fase di sviluppo', 'warning')
    return redirect(url_for('social_safety.manage_programs'))
    
    return render_template('social_safety_programs.html',
                         expiring_programs=expiring_programs,
                         active_assignments=active_assignments,
                         pending_assignments=pending_assignments,
                         total_employees_affected=total_employees_affected,
                         total_active_programs=total_active_programs,
                         today=today)


# =============================================================================
# DOWNLOAD ROUTES
# =============================================================================

@social_safety_bp.route('/download/<int:program_id>/decree')
@login_required
@require_social_safety_permission
def download_decree(program_id):
    """Download file decreto"""
    program = filter_by_company(SocialSafetyNetProgram.query).filter_by(id=program_id).first_or_404()
    
    if not program.decree_file_path or not os.path.exists(program.decree_file_path):
        flash('File decreto non trovato.', 'danger')
        return redirect(url_for('social_safety.program_detail', program_id=program_id))
    
    directory = os.path.dirname(program.decree_file_path)
    filename = os.path.basename(program.decree_file_path)
    
    return send_from_directory(directory, filename, as_attachment=True)


# =============================================================================
# USER-SPECIFIC ASSIGNMENT VIEW (READ-ONLY)
# =============================================================================

@social_safety_bp.route('/dipendente/<int:user_id>/assegnazioni')
@login_required
@require_social_safety_permission
@require_reports_permission
def user_assignments(user_id):
    """Visualizza assegnazioni ammortizzatori sociali per dipendente specifico (read-only)"""
    # Ottieni utente con tenant filtering
    user = filter_by_company(User.query).filter_by(id=user_id).first_or_404()
    
    # Ottieni tutte le assegnazioni per questo utente
    assignments = filter_by_company(SocialSafetyNetAssignment.query).filter_by(
        user_id=user_id
    ).order_by(SocialSafetyNetAssignment.start_date.desc()).all()
    
    # Trova assegnazione attualmente attiva
    active_assignment = None
    today = date.today()
    for assignment in assignments:
        if assignment.status in ['approved', 'active'] and assignment.start_date <= today and (
            assignment.end_date >= today
        ):
            active_assignment = assignment
            break
    
    # Statistiche
    total_assignments = len(assignments)
    approved_count = len([a for a in assignments if a.is_approved])
    pending_count = len([a for a in assignments if not a.is_approved])
    
    return render_template('user_assignments_social_safety.html',
                         user=user,
                         assignments=assignments,
                         active_assignment=active_assignment,
                         total_assignments=total_assignments,
                         approved_count=approved_count,
                         pending_count=pending_count)


@social_safety_bp.route('/le-mie-assegnazioni')
@login_required
@require_social_safety_permission
def my_assignments():
    """Reindirizza alla visualizzazione assegnazioni del utente corrente"""
    return redirect(url_for('social_safety.user_assignments', user_id=current_user.id))
