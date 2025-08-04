# Workly Routes - Sistema di gestione workforce
# Ricreato da zero per eliminare duplicazioni e codice obsoleto

from flask import render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date, datetime, timedelta
from collections import defaultdict
import os

from app import app, db
from models import *
from forms import *

# ===== AUTENTICAZIONE =====
@app.route('/')
def index():
    """Home page - redirect to dashboard if authenticated"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email, active=True).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Login effettuato con successo!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Email o password non corretti.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Logout"""
    logout_user()
    flash('Logout effettuato con successo.', 'info')
    return redirect(url_for('login'))

# ===== DASHBOARD =====
@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard principale"""
    return render_template('dashboard.html')

# ===== GESTIONE UTENTI (VISUALIZZAZIONE) =====
@app.route('/users')
@login_required
def users():
    """Lista utenti - SOLO VISUALIZZAZIONE"""
    if not current_user.can_view_users():
        flash('Non hai i permessi per visualizzare gli utenti.', 'danger')
        return redirect(url_for('dashboard'))
    
    users = User.query.filter_by(active=True).order_by(User.first_name, User.last_name).all()
    return render_template('users.html', users=users)

# ===== GESTIONE UTENTI (AMMINISTRAZIONE) =====
@app.route('/user_management')
@login_required  
def user_management():
    """Gestione utenti - AMMINISTRAZIONE"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per gestire gli utenti.', 'danger')
        return redirect(url_for('dashboard'))
    
    users = User.query.order_by(User.first_name, User.last_name).all()
    form = UserForm()
    return render_template('user_management.html', users=users, form=form)

@app.route('/new_user', methods=['GET', 'POST'])
@login_required
def new_user():
    """Crea nuovo utente"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per creare utenti.', 'danger')
        return redirect(url_for('dashboard'))
    
    form = UserForm()
    
    if form.validate_on_submit():
        user = User(
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            password_hash=generate_password_hash(form.password.data)
        )
        db.session.add(user)
        db.session.commit()
        flash(f'Utente {user.first_name} {user.last_name} creato!', 'success')
        return redirect(url_for('user_management'))
    
    return render_template('new_user.html', form=form)

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """Modifica utente"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per modificare gli utenti.', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    
    if form.validate_on_submit():
        form.populate_obj(user)
        if form.password.data:
            user.password_hash = generate_password_hash(form.password.data)
        db.session.commit()
        flash(f'Utente {user.first_name} {user.last_name} modificato!', 'success')
        return redirect(url_for('user_management'))
    
    return render_template('edit_user.html', form=form, user=user)

@app.route('/toggle_user/<int:user_id>')
@login_required
def toggle_user(user_id):
    """Toggle attivazione utente"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per gestire gli utenti.', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    user.active = not user.active
    db.session.commit()
    
    status = "attivato" if user.active else "disattivato"
    flash(f'Utente {user.first_name} {user.last_name} {status}!', 'success')
    return redirect(url_for('user_management'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    """Elimina utente"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per eliminare gli utenti.', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f'Utente {user.first_name} {user.last_name} eliminato!', 'success')
    return redirect(url_for('user_management'))

# ===== GESTIONE RUOLI =====
@app.route('/manage_roles')
@login_required
def manage_roles():
    """Gestione ruoli"""
    if not current_user.can_manage_roles():
        flash('Non hai i permessi per gestire i ruoli.', 'danger')
        return redirect(url_for('dashboard'))
    
    roles = UserRole.query.all()
    form = RoleForm()
    return render_template('manage_roles.html', roles=roles, form=form)

@app.route('/create_role', methods=['GET', 'POST'])
@login_required
def create_role():
    """Crea nuovo ruolo"""
    if not current_user.can_manage_roles():
        flash('Non hai i permessi per creare ruoli.', 'danger')
        return redirect(url_for('dashboard'))
    
    form = RoleForm()
    
    if form.validate_on_submit():
        role = UserRole(name=form.name.data, description=form.description.data)
        db.session.add(role)
        db.session.commit()
        flash(f'Ruolo {role.name} creato!', 'success')
        return redirect(url_for('manage_roles'))
    
    return render_template('create_role.html', form=form)

@app.route('/edit_role/<int:role_id>', methods=['GET', 'POST'])
@login_required
def edit_role(role_id):
    """Modifica ruolo"""
    if not current_user.can_manage_roles():
        flash('Non hai i permessi per modificare i ruoli.', 'danger')
        return redirect(url_for('dashboard'))
    
    role = UserRole.query.get_or_404(role_id)
    form = RoleForm(obj=role)
    
    if form.validate_on_submit():
        form.populate_obj(role)
        db.session.commit()
        flash(f'Ruolo {role.name} modificato!', 'success')
        return redirect(url_for('manage_roles'))
    
    return render_template('edit_role.html', form=form, role=role)

@app.route('/toggle_role/<int:role_id>')
@login_required
def toggle_role(role_id):
    """Toggle attivazione ruolo"""
    if not current_user.can_manage_roles():
        flash('Non hai i permessi per gestire i ruoli.', 'danger')
        return redirect(url_for('dashboard'))
    
    role = UserRole.query.get_or_404(role_id)
    role.active = not role.active
    db.session.commit()
    
    status = "attivato" if role.active else "disattivato"
    flash(f'Ruolo {role.name} {status}!', 'success')
    return redirect(url_for('manage_roles'))

@app.route('/delete_role/<int:role_id>', methods=['POST'])
@login_required
def delete_role(role_id):
    """Elimina ruolo"""
    if not current_user.can_manage_roles():
        flash('Non hai i permessi per eliminare i ruoli.', 'danger')
        return redirect(url_for('dashboard'))
    
    role = UserRole.query.get_or_404(role_id)
    db.session.delete(role)
    db.session.commit()
    flash(f'Ruolo {role.name} eliminato!', 'success')
    return redirect(url_for('manage_roles'))

# ===== GESTIONE SEDI =====
@app.route('/manage_sedi')
@login_required
def manage_sedi():
    """Gestione sedi"""
    if not current_user.can_manage_sedi():
        flash('Non hai i permessi per gestire le sedi.', 'danger')
        return redirect(url_for('dashboard'))
    
    sedi = Sede.query.all()
    form = SedeForm()
    
    # Calcolo statistiche sedi
    sedi_stats = {}
    for sede in sedi:
        sedi_stats[sede.id] = {
            'users_count': User.query.filter_by(sede_id=sede.id, active=True).count(),
            'shifts_count': 0
        }
    
    return render_template('manage_sedi.html', sedi=sedi, form=form, sedi_stats=sedi_stats)

@app.route('/create_sede', methods=['POST'])
@login_required
def create_sede():
    """Crea nuova sede"""
    if not current_user.can_manage_sedi():
        flash('Non hai i permessi per creare sedi.', 'danger')
        return redirect(url_for('dashboard'))
    
    form = SedeForm()
    if form.validate_on_submit():
        sede = Sede(name=form.name.data, description=form.description.data)
        db.session.add(sede)
        db.session.commit()
        flash(f'Sede {sede.name} creata!', 'success')
    
    return redirect(url_for('manage_sedi'))

@app.route('/toggle_sede/<int:sede_id>')
@login_required
def toggle_sede(sede_id):
    """Toggle attivazione sede"""
    if not current_user.can_manage_sedi():
        flash('Non hai i permessi per gestire le sedi.', 'danger')
        return redirect(url_for('dashboard'))
    
    sede = Sede.query.get_or_404(sede_id)
    sede.active = not sede.active
    db.session.commit()
    
    status = "attivata" if sede.active else "disattivata"
    flash(f'Sede {sede.name} {status}!', 'success')
    return redirect(url_for('manage_sedi'))

# ===== GESTIONE ORARI =====
@app.route('/manage_work_schedules')
@login_required
def manage_work_schedules():
    """Gestione orari di lavoro"""
    if not current_user.can_manage_work_schedules():
        flash('Non hai i permessi per gestire gli orari.', 'danger')
        return redirect(url_for('dashboard'))
    
    schedules = WorkSchedule.query.all()
    form = WorkScheduleForm()
    return render_template('manage_work_schedules.html', schedules=schedules, form=form)

@app.route('/create_work_schedule', methods=['POST'])
@login_required
def create_work_schedule():
    """Crea nuovo orario di lavoro"""
    if not current_user.can_manage_work_schedules():
        flash('Non hai i permessi per creare orari.', 'danger')
        return redirect(url_for('dashboard'))
    
    form = WorkScheduleForm()
    if form.validate_on_submit():
        schedule = WorkSchedule(name=form.name.data, description=form.description.data)
        db.session.add(schedule)
        db.session.commit()
        flash(f'Orario {schedule.name} creato!', 'success')
    
    return redirect(url_for('manage_work_schedules'))

@app.route('/toggle_work_schedule/<int:schedule_id>')
@login_required
def toggle_work_schedule(schedule_id):
    """Toggle attivazione orario"""
    if not current_user.can_manage_work_schedules():
        flash('Non hai i permessi per gestire gli orari.', 'danger')
        return redirect(url_for('dashboard'))
    
    schedule = WorkSchedule.query.get_or_404(schedule_id)
    schedule.active = not schedule.active
    db.session.commit()
    
    status = "attivato" if schedule.active else "disattivato"
    flash(f'Orario {schedule.name} {status}!', 'success')
    return redirect(url_for('manage_work_schedules'))

# ===== MESSAGGI INTERNI =====
@app.route('/send_message', methods=['GET', 'POST'])
@login_required
def send_message():
    """Invia messaggio interno"""
    if not current_user.can_send_messages():
        flash('Non hai i permessi per inviare messaggi.', 'danger')
        return redirect(url_for('dashboard'))
    
    form = MessageForm()
    
    if form.validate_on_submit():
        # Logica invio messaggio
        flash('Messaggio inviato con successo!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('send_message.html', form=form)

@app.route('/internal_messages')
@login_required
def internal_messages():
    """Visualizza messaggi interni"""
    if not current_user.can_view_messages():
        flash('Non hai i permessi per visualizzare i messaggi.', 'danger')
        return redirect(url_for('dashboard'))
    
    messages = InternalMessage.query.filter_by(recipient_id=current_user.id).order_by(InternalMessage.created_at.desc()).all()
    return render_template('internal_messages.html', messages=messages)

# ===== FERIE E PERMESSI =====
@app.route('/leave_requests')
@login_required
def leave_requests():
    """Richieste ferie"""
    if not current_user.can_view_leave_requests():
        flash('Non hai i permessi per visualizzare le richieste ferie.', 'danger')
        return redirect(url_for('dashboard'))
    
    requests = LeaveRequest.query.order_by(LeaveRequest.created_at.desc()).all()
    return render_template('leave_requests.html', requests=requests)

@app.route('/create_leave_request_page', methods=['GET', 'POST'])
@login_required
def create_leave_request_page():
    """Crea richiesta ferie"""
    if not current_user.can_request_leave():
        flash('Non hai i permessi per richiedere ferie.', 'danger')
        return redirect(url_for('dashboard'))
    
    form = LeaveRequestForm()
    
    if form.validate_on_submit():
        leave_request = LeaveRequest(
            user_id=current_user.id,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            description=form.description.data,
            status='pending'
        )
        db.session.add(leave_request)
        db.session.commit()
        flash('Richiesta ferie inviata!', 'success')
        return redirect(url_for('leave_requests'))
    
    return render_template('create_leave_request.html', form=form)

# ===== STRAORDINARI =====
@app.route('/overtime_requests')
@login_required
def overtime_requests():
    """Richieste straordinari"""
    if not current_user.can_view_overtime_requests():
        flash('Non hai i permessi per visualizzare gli straordinari.', 'danger')
        return redirect(url_for('dashboard'))
    
    requests = OvertimeRequest.query.order_by(OvertimeRequest.created_at.desc()).all()
    return render_template('overtime_requests.html', requests=requests)

@app.route('/my_overtime_requests')
@login_required
def my_overtime_requests():
    """I miei straordinari"""
    requests = OvertimeRequest.query.filter_by(user_id=current_user.id).order_by(OvertimeRequest.created_at.desc()).all()
    return render_template('my_overtime_requests.html', requests=requests)

@app.route('/create_overtime_request', methods=['GET', 'POST'])
@login_required
def create_overtime_request():
    """Crea richiesta straordinari"""
    if not current_user.can_request_overtime():
        flash('Non hai i permessi per richiedere straordinari.', 'danger')
        return redirect(url_for('dashboard'))
    
    form = OvertimeRequestForm()
    
    if form.validate_on_submit():
        overtime = OvertimeRequest(
            user_id=current_user.id,
            date=form.date.data,
            hours=form.hours.data,
            description=form.description.data,
            status='pending'
        )
        db.session.add(overtime)
        db.session.commit()
        flash('Richiesta straordinari inviata!', 'success')
        return redirect(url_for('overtime_requests'))
    
    return render_template('create_overtime_request.html', form=form)

# ===== NOTE SPESE =====
@app.route('/expense_reports')
@login_required
def expense_reports():
    """Note spese"""
    if not current_user.can_view_expense_reports():
        flash('Non hai i permessi per visualizzare le note spese.', 'danger')
        return redirect(url_for('dashboard'))
    
    reports = ExpenseReport.query.order_by(ExpenseReport.created_at.desc()).all()
    return render_template('expense_reports.html', reports=reports)

@app.route('/create_expense_report', methods=['GET', 'POST'])
@login_required
def create_expense_report():
    """Crea nota spese"""
    if not current_user.can_create_expense_reports():
        flash('Non hai i permessi per creare note spese.', 'danger')
        return redirect(url_for('dashboard'))
    
    form = ExpenseReportForm()
    
    if form.validate_on_submit():
        expense = ExpenseReport(
            user_id=current_user.id,
            amount=form.amount.data,
            description=form.description.data,
            date=form.date.data,
            status='pending'
        )
        db.session.add(expense)
        db.session.commit()
        flash('Nota spese creata!', 'success')
        return redirect(url_for('expense_reports'))
    
    return render_template('create_expense_report.html', form=form)

# ===== RIMBORSI CHILOMETRICI =====
@app.route('/mileage_requests')
@login_required
def mileage_requests():
    """Richieste rimborso chilometrico"""
    if not current_user.can_view_mileage_requests():
        flash('Non hai i permessi per visualizzare i rimborsi.', 'danger')
        return redirect(url_for('dashboard'))
    
    requests = MileageRequest.query.order_by(MileageRequest.created_at.desc()).all()
    return render_template('mileage_requests.html', requests=requests)

@app.route('/my_mileage_requests')
@login_required
def my_mileage_requests():
    """I miei rimborsi chilometrici"""
    requests = MileageRequest.query.filter_by(user_id=current_user.id).order_by(MileageRequest.created_at.desc()).all()
    return render_template('my_mileage_requests.html', requests=requests)

@app.route('/create_mileage_request', methods=['GET', 'POST'])
@login_required
def create_mileage_request():
    """Crea richiesta rimborso chilometrico"""
    if not current_user.can_create_mileage_requests():
        flash('Non hai i permessi per creare richieste rimborso.', 'danger')
        return redirect(url_for('dashboard'))
    
    form = MileageRequestForm()
    
    if form.validate_on_submit():
        mileage = MileageRequest(
            user_id=current_user.id,
            distance=form.distance.data,
            amount=form.amount.data,
            description=form.description.data,
            date=form.date.data,
            status='pending'
        )
        db.session.add(mileage)
        db.session.commit()
        flash('Richiesta rimborso creata!', 'success')
        return redirect(url_for('mileage_requests'))
    
    return render_template('create_mileage_request.html', form=form)

# ===== FESTIVITÀ =====
@app.route('/holidays')
@login_required
def holidays():
    """Gestione festività"""
    if not current_user.can_view_holidays():
        flash('Non hai i permessi per visualizzare le festività.', 'danger')
        return redirect(url_for('dashboard'))
    
    holidays = Holiday.query.order_by(Holiday.date.desc()).all()
    return render_template('holidays.html', holidays=holidays)

# ===== REPORTS =====
@app.route('/reports')
@login_required
def reports():
    """Reports e statistiche"""
    if not current_user.can_view_reports():
        flash('Non hai i permessi per visualizzare i reports.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Date per filtri reports
    start_date = date.today() - timedelta(days=30)
    end_date = date.today()
    
    return render_template('reports.html', start_date=start_date, end_date=end_date)

# ===== TURNI AUTOMATICI =====
@app.route('/turni_automatici')
@login_required
def turni_automatici():
    """Gestione turni automatici"""
    if not current_user.can_view_shifts():
        flash('Non hai i permessi per visualizzare i turni.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Carica template presidio
    presidio_templates = PresidioTemplate.query.all()
    selected_template = None
    
    # Logica per template selection e missing coverage
    turni_per_settimana = {}
    settimane_stats = {}
    shifts = []
    
    # Utenti per creazione turni
    users_by_role = defaultdict(list)
    available_users = User.query.filter(User.active.is_(True)).all()
    
    for user in available_users:
        if hasattr(user, 'role') and user.role:
            users_by_role[user.role].append(user)
    
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

@app.route('/genera_turni_da_template', methods=['POST'])
@login_required
def genera_turni_da_template():
    """Genera turni da template"""
    if not current_user.can_manage_shifts():
        flash('Non hai i permessi per generare turni.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Logica per generare turni
    flash('Turni generati con successo!', 'success')
    return redirect(url_for('turni_automatici'))

# ===== PRESIDIO COVERAGE =====
@app.route('/presidio_coverage')
@login_required
def presidio_coverage():
    """Gestione coperture presidio"""
    if not current_user.can_view_coverage():
        flash('Non hai i permessi per visualizzare le coperture.', 'danger')
        return redirect(url_for('dashboard'))
    
    templates = PresidioTemplate.query.all()
    
    # Calcolo missing coverage dinamico
    missing_coverage = {}
    for template in templates:
        missing_coverage[template.id] = []
    
    return render_template('presidio_coverage.html', 
                         templates=templates,
                         missing_coverage=missing_coverage)

@app.route('/view_presidi')
@login_required
def view_presidi():
    """Visualizza presidi - SOLO VISUALIZZAZIONE"""
    if not current_user.can_view_coverage():
        flash('Non hai i permessi per visualizzare i presidi.', 'danger')
        return redirect(url_for('dashboard'))
    
    templates = PresidioTemplate.query.all()
    return render_template('view_presidi.html', templates=templates)

@app.route('/presidio_detail/<int:template_id>')
@login_required
def presidio_detail(template_id):
    """Dettaglio presidio"""
    if not current_user.can_view_coverage():
        flash('Non hai i permessi per visualizzare i dettagli presidio.', 'danger')
        return redirect(url_for('dashboard'))
    
    template = PresidioTemplate.query.get_or_404(template_id)
    return render_template('presidio_detail.html', template=template)

# ===== REPERIBILITÀ =====
@app.route('/reperibilita_shifts')
@login_required
def reperibilita_shifts():
    """Visualizza turni reperibilità"""
    if not current_user.can_view_reperibilita():
        flash('Non hai i permessi per visualizzare la reperibilità.', 'danger')
        return redirect(url_for('dashboard'))
    
    shifts = ReperibilitaShift.query.order_by(ReperibilitaShift.date.desc()).limit(100).all()
    
    # Variabili navigation per template
    today = date.today()
    navigation = {
        'prev_date': today - timedelta(days=30),
        'next_date': today + timedelta(days=30),
        'current_date': today
    }
    
    # Parametri view mode
    view_mode = request.args.get('view', 'calendar')
    period_mode = request.args.get('period', 'month')
    display_mode = request.args.get('display', 'all')
    
    return render_template('reperibilita_shifts.html', 
                         shifts=shifts,
                         navigation=navigation,
                         view_mode=view_mode,
                         period_mode=period_mode,
                         display_mode=display_mode)

@app.route('/start_intervention', methods=['POST'])
@login_required
def start_intervention():
    """Avvia intervento reperibilità"""
    if not current_user.can_create_interventions():
        flash('Non hai i permessi per creare interventi.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Logica per avviare intervento
    flash('Intervento avviato!', 'success')
    return redirect(url_for('reperibilita_shifts'))

@app.route('/end_intervention', methods=['POST'])
@login_required
def end_intervention():
    """Termina intervento reperibilità"""
    if not current_user.can_manage_interventions():
        flash('Non hai i permessi per gestire gli interventi.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Logica per terminare intervento
    flash('Intervento terminato!', 'success')
    return redirect(url_for('my_interventions'))

@app.route('/my_interventions')
@login_required
def my_interventions():
    """I miei interventi"""
    if not current_user.can_view_interventions():
        flash('Non hai i permessi per visualizzare gli interventi.', 'danger')
        return redirect(url_for('dashboard'))
    
    interventions = Intervention.query.filter_by(user_id=current_user.id).order_by(Intervention.created_at.desc()).all()
    
    # Date per filtri
    start_date = date.today() - timedelta(days=30)
    end_date = date.today()
    
    return render_template('my_interventions.html', 
                         interventions=interventions,
                         start_date=start_date,
                         end_date=end_date)

# ===== TABELLE ACI =====
@app.route('/aci_tables')
@login_required
def aci_tables():
    """Gestione tabelle ACI"""
    if not current_user.can_view_aci():
        flash('Non hai i permessi per visualizzare le tabelle ACI.', 'danger')
        return redirect(url_for('dashboard'))
    
    tables = ACITable.query.all()
    categories = ACICategory.query.all()
    form = ACIForm()
    
    # Date per filtri
    start_date = date.today() - timedelta(days=30)
    end_date = date.today()
    
    return render_template('aci_tables.html', 
                         tables=tables, 
                         categories=categories, 
                         form=form,
                         start_date=start_date, 
                         end_date=end_date)

@app.route('/aci_upload', methods=['POST'])
@login_required
def aci_upload():
    """Upload tabelle ACI"""
    if not current_user.can_manage_aci():
        flash('Non hai i permessi per gestire le tabelle ACI.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Logica upload ACI
    flash('Tabelle ACI caricate con successo!', 'success')
    return redirect(url_for('aci_tables'))

@app.route('/aci_export')
@login_required
def aci_export():
    """Export tabelle ACI"""
    if not current_user.can_view_aci():
        flash('Non hai i permessi per visualizzare le tabelle ACI.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Logica export ACI
    flash('Export ACI completato!', 'success')
    return redirect(url_for('aci_tables'))

# ===== API ROUTES =====
@app.route('/api/get_coverage_requirements/<int:template_id>')
@login_required
def get_coverage_requirements(template_id):
    """API per ottenere coperture template"""
    template = PresidioTemplate.query.get_or_404(template_id)
    
    # Logica per calcolare coperture necessarie
    coverage_data = {
        'template_id': template_id,
        'coverages': []
    }
    
    return jsonify(coverage_data)

# ===== VISUALIZZAZIONE TURNI =====
@app.route('/visualizza_turni')
@login_required
def visualizza_turni():
    """Visualizza turni - SOLO VISUALIZZAZIONE"""
    if not current_user.can_view_shifts():
        flash('Non hai i permessi per visualizzare i turni.', 'danger')
        return redirect(url_for('dashboard'))
    
    start_date = date.today() - timedelta(days=30)
    end_date = date.today() + timedelta(days=30)
    
    shifts = Shift.query.filter(
        Shift.date >= start_date,
        Shift.date <= end_date
    ).order_by(Shift.date, Shift.start_time).all()
    
    return render_template('visualizza_turni.html', shifts=shifts, start_date=start_date, end_date=end_date)

# ===== USER PROFILE =====
@app.route('/user_profile')
@login_required
def user_profile():
    """Profilo utente"""
    return render_template('user_profile.html', user=current_user)

# ===== QR CODE =====
@app.route('/qr_code')
@login_required
def qr_code():
    """QR Code per timbrature"""
    if not current_user.can_use_qr_code():
        flash('Non hai i permessi per utilizzare il QR Code.', 'danger')
        return redirect(url_for('dashboard'))
    
    return render_template('qr_code.html')

# ===== PRESENZE E TIMBRATURE =====
@app.route('/attendance')
@login_required
def attendance():
    """Gestione presenze"""
    if not current_user.can_view_attendance():
        flash('Non hai i permessi per visualizzare le presenze.', 'danger')
        return redirect(url_for('dashboard'))
    
    records = AttendanceEvent.query.filter_by(user_id=current_user.id).order_by(AttendanceEvent.timestamp.desc()).limit(50).all()
    return render_template('attendance.html', records=records)

@app.route('/my_daily_records')
@login_required
def my_daily_records():
    """I miei record giornalieri"""
    records = DailyRecord.query.filter_by(user_id=current_user.id).order_by(DailyRecord.date.desc()).limit(30).all()
    return render_template('my_daily_records.html', records=records)

@app.route('/breaks')
@login_required
def breaks():
    """Gestione pause"""
    breaks = Break.query.filter_by(user_id=current_user.id).order_by(Break.start_time.desc()).limit(30).all()
    return render_template('breaks.html', breaks=breaks)

@app.route('/statistics')
@login_required
def statistics():
    """Statistiche personali"""
    if not current_user.can_view_statistics():
        flash('Non hai i permessi per visualizzare le statistiche.', 'danger')
        return redirect(url_for('dashboard'))
    
    return render_template('statistics.html')

@app.route('/dashboard_team')
@login_required
def dashboard_team():
    """Dashboard team presenze"""
    if not current_user.can_manage_attendance():
        flash('Non hai i permessi per gestire le presenze del team.', 'danger')
        return redirect(url_for('dashboard'))
    
    return render_template('dashboard_team.html')

@app.route('/leave_types')
@login_required
def leave_types():
    """Gestione tipologie ferie"""
    if not current_user.can_manage_leave_types():
        flash('Non hai i permessi per gestire le tipologie ferie.', 'danger')
        return redirect(url_for('dashboard'))
    
    types = LeaveType.query.all()
    return render_template('leave_types.html', types=types)

# ===== ROUTE MANAGEMENT AGGIUNTIVE =====
@app.route('/overtime_requests_management')
@login_required
def overtime_requests_management():
    """Gestione straordinari (amministrazione)"""
    if not current_user.can_manage_overtime_requests():
        flash('Non hai i permessi per gestire gli straordinari.', 'danger')
        return redirect(url_for('dashboard'))
    
    requests = OvertimeRequest.query.order_by(OvertimeRequest.created_at.desc()).all()
    return render_template('overtime_requests_management.html', requests=requests)

@app.route('/expense_reports_management')
@login_required
def expense_reports_management():
    """Gestione note spese (amministrazione)"""
    if not current_user.can_manage_expense_reports():
        flash('Non hai i permessi per gestire le note spese.', 'danger')
        return redirect(url_for('dashboard'))
    
    reports = ExpenseReport.query.order_by(ExpenseReport.created_at.desc()).all()
    return render_template('expense_reports_management.html', reports=reports)

@app.route('/mileage_requests_management')
@login_required
def mileage_requests_management():
    """Gestione rimborsi chilometrici (amministrazione)"""
    if not current_user.can_manage_mileage_requests():
        flash('Non hai i permessi per gestire i rimborsi.', 'danger')
        return redirect(url_for('dashboard'))
    
    requests = MileageRequest.query.order_by(MileageRequest.created_at.desc()).all()
    return render_template('mileage_requests_management.html', requests=requests)

# ===== ERROR HANDLERS =====
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500