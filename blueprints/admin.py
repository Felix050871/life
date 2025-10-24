# =============================================================================
# ADMIN & SYSTEM MANAGEMENT BLUEPRINT
# =============================================================================
#
# ROUTES INCLUSE:
# 1. admin_qr_codes (GET) - Gestione codici QR sistema
# 2. view_qr_codes (GET) - Visualizzazione codici QR
# 3. generate_qr_codes (POST) - Generazione codici QR
# 4. admin_settings (GET/POST) - Configurazioni sistema generali
# 5. system_info (GET) - Informazioni sistema e diagnostica
#
# Total routes: 5+ admin/system routes
# =============================================================================

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, make_response
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from functools import wraps
from app import db
from models import User, Sede, Shift, ReperibilitaShift, WorkSchedule, UserRole, italian_now
from forms import SedeForm, WorkScheduleForm, RoleForm
from utils_tenant import filter_by_company, set_company_on_create, get_user_company_id
import io
import os

# Create blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Helper functions
def require_admin_permission(f):
    """Decorator to require admin permissions for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.can_manage_roles():
            flash('Non hai i permessi per accedere a questa sezione', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def require_qr_permission(f):
    """Decorator to require QR code permissions"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not (current_user.can_manage_qr() or current_user.can_view_qr()):
            flash('Non hai i permessi per accedere ai codici QR', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# QR CODE MANAGEMENT ROUTES
# =============================================================================

@admin_bp.route('/qr_codes')
@login_required
@require_qr_permission
def admin_qr_codes():
    """Gestione codici QR - Solo per chi può gestire"""
    if not current_user.can_manage_qr():
        flash('Non hai i permessi per gestire i codici QR', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    from utils import qr_codes_exist, get_qr_code_urls
    
    # Verifica se i QR code statici esistono
    qr_exist = qr_codes_exist()
    
    # Genera URL globali per i QR codes (tenant isolation tramite user login)
    base_url = request.url_root.rstrip('/')
    qr_urls = {
        'entrata': f"{base_url}/qr/login/entrata",
        'uscita': f"{base_url}/qr/login/uscita"
    }
    
    # Se esistono, ottieni gli URL per visualizzarli
    static_qr_urls = get_qr_code_urls() if qr_exist else None
    
    try:
        from config import get_config
        config = get_config()
    except ImportError:
        config = {}
    
    return render_template('admin_qr_codes.html', 
                         qr_urls=qr_urls,
                         qr_exist=qr_exist,
                         static_qr_urls=static_qr_urls,
                         can_manage=True,
                         config=config)

@admin_bp.route('/qr_codes/view')
@login_required
@require_qr_permission
def view_qr_codes():
    """Visualizzazione codici QR - Solo per chi può visualizzare"""
    if not current_user.can_view_qr():
        flash('Non hai i permessi per visualizzare i codici QR', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    from utils import qr_codes_exist, get_qr_code_urls
    
    # Verifica se i QR code statici esistono
    qr_exist = qr_codes_exist()
    
    # Genera URL globali per i QR codes (tenant isolation tramite user login)
    base_url = request.url_root.rstrip('/')
    qr_urls = {
        'entrata': f"{base_url}/qr/login/entrata",
        'uscita': f"{base_url}/qr/login/uscita"
    }
    
    # Se esistono, ottieni gli URL per visualizzarli
    static_qr_urls = get_qr_code_urls() if qr_exist else None
    
    try:
        from config import get_config
        config = get_config()
    except ImportError:
        config = {}
    
    return render_template('admin_qr_codes.html', 
                         qr_urls=qr_urls,
                         qr_exist=qr_exist,
                         static_qr_urls=static_qr_urls,
                         can_manage=current_user.can_manage_qr(),
                         config=config)

@admin_bp.route('/qr_codes/generate', methods=['POST'])
@login_required
@require_admin_permission
def generate_qr_codes():
    """Genera i codici QR statici del sistema"""
    if not current_user.can_manage_qr():
        return jsonify({'success': False, 'message': 'Non hai i permessi per generare i codici QR'}), 403
    
    try:
        from utils import generate_static_qr_codes
        
        # Genera i codici QR
        result = generate_static_qr_codes()
        
        if result:
            flash('Codici QR generati con successo', 'success')
            return jsonify({'success': True, 'message': 'Codici QR generati con successo'})
        else:
            flash('Errore nella generazione dei codici QR', 'danger')
            return jsonify({'success': False, 'message': 'Errore nella generazione dei codici QR'}), 500
            
    except ImportError:
        flash('Funzione di generazione QR non disponibile', 'warning')
        return jsonify({'success': False, 'message': 'Funzione non disponibile'}), 501
    except Exception as e:
        flash(f'Errore: {str(e)}', 'danger')
        return jsonify({'success': False, 'message': f'Errore: {str(e)}'}), 500

# =============================================================================
# SEDE MANAGEMENT ROUTES
# =============================================================================

@admin_bp.route('/sedi')
@login_required
@require_admin_permission
def manage_sedi():
    """Gestione delle sedi aziendali"""
    if not (current_user.can_manage_sedi() or current_user.can_view_sedi()):
        flash('Non hai i permessi per accedere alle sedi', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    sedi = filter_by_company(Sede.query).order_by(Sede.created_at.desc()).all()
    
    form = SedeForm()
    return render_template('manage_sedi.html', sedi=sedi, form=form)

@admin_bp.route('/sedi/create', methods=['POST'])
@login_required
@require_admin_permission
def create_sede():
    """Crea una nuova sede"""
    if not current_user.can_manage_sedi():
        flash('Non hai i permessi per creare sedi', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    form = SedeForm()
    if form.validate_on_submit():
        sede = Sede(
            name=form.name.data,
            address=form.address.data,
            description=form.description.data,
            active=form.active.data
        )
        set_company_on_create(sede)
        db.session.add(sede)
        db.session.commit()
        flash('Sede creata con successo', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'danger')
    
    return redirect(url_for('admin.manage_sedi'))

@admin_bp.route('/sedi/edit/<int:sede_id>', methods=['GET', 'POST'])
@login_required
@require_admin_permission
def edit_sede(sede_id):
    """Modifica una sede esistente"""
    if not current_user.can_manage_sedi():
        flash('Non hai i permessi per modificare sedi', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    sede = filter_by_company(Sede.query).filter(Sede.id == sede_id).first_or_404()
    form = SedeForm(original_name=sede.name, obj=sede)
    
    if form.validate_on_submit():
        sede.name = form.name.data
        sede.address = form.address.data
        sede.description = form.description.data
        sede.active = form.active.data
        
        db.session.commit()
        flash(f'Sede "{sede.name}" modificata con successo', 'success')
        return redirect(url_for('admin.manage_sedi'))
    
    return render_template('edit_sede.html', form=form, sede=sede)

@admin_bp.route('/sedi/toggle/<int:sede_id>')
@login_required
@require_admin_permission
def toggle_sede(sede_id):
    """Attiva/disattiva una sede"""
    if not current_user.can_manage_sedi():  # FIXED: era can_manage_users()
        flash('Non hai i permessi per modificare sedi', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    sede = filter_by_company(Sede.query).filter(Sede.id == sede_id).first_or_404()
    sede.active = not sede.active
    db.session.commit()
    
    status = 'attivata' if sede.active else 'disattivata'
    flash(f'Sede "{sede.name}" {status} con successo', 'success')
    return redirect(url_for('admin.manage_sedi'))

# =============================================================================
# WORK SCHEDULE MANAGEMENT ROUTES
# =============================================================================

@admin_bp.route('/orari')
@login_required
def manage_work_schedules():
    """Gestione degli orari di lavoro"""
    if not (current_user.can_manage_schedules() or current_user.can_view_schedules()):
        flash('Non hai i permessi per accedere agli orari', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    # Ottieni tutti gli orari globali dell'azienda
    schedules = filter_by_company(WorkSchedule.query).order_by(WorkSchedule.name).all()
    form = WorkScheduleForm()
    return render_template('manage_work_schedules.html', schedules=schedules, form=form)

@admin_bp.route('/orari/create', methods=['POST'])
@login_required
def create_work_schedule():
    """Crea un nuovo orario di lavoro"""
    if not current_user.can_manage_schedules():
        flash('Non hai i permessi per creare orari', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    form = WorkScheduleForm()
    if form.validate_on_submit():
        # Determina i giorni della settimana dal preset o dalla selezione personalizzata
        if form.days_preset.data != 'custom':
            days_of_week = form.get_days_from_preset(form.days_preset.data)
        else:
            days_of_week = form.days_of_week.data
        
        schedule = WorkSchedule(
            name=form.name.data,
            start_time_min=form.start_time_min.data,
            start_time_max=form.start_time_max.data,
            end_time_min=form.end_time_min.data,
            end_time_max=form.end_time_max.data,
            # Imposta campi legacy per compatibilità usando il valore minimo
            start_time=form.start_time_min.data,
            end_time=form.end_time_min.data,
            days_of_week=days_of_week,
            description=form.description.data,
            active=form.active.data
        )
        set_company_on_create(schedule)
        db.session.add(schedule)
        db.session.commit()
        flash('Orario di lavoro creato con successo', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'danger')
    
    return redirect(url_for('admin.manage_work_schedules'))

@admin_bp.route('/orari/edit/<int:schedule_id>', methods=['GET', 'POST'])
@login_required
def edit_work_schedule(schedule_id):
    """Modifica un orario di lavoro esistente"""
    if not current_user.can_manage_schedules():
        flash('Non hai i permessi per modificare orari', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    schedule = filter_by_company(WorkSchedule.query).filter_by(id=schedule_id).first_or_404()
    form = WorkScheduleForm(original_name=schedule.name, obj=schedule)
    
    # Precompila i campi basandosi sui dati esistenti
    if request.method == 'GET':
        # Precompila range orari
        form.start_time_min.data = schedule.start_time_min
        form.start_time_max.data = schedule.start_time_max
        form.end_time_min.data = schedule.end_time_min
        form.end_time_max.data = schedule.end_time_max
        
        # Precompila giorni della settimana
        form.days_of_week.data = schedule.days_of_week or [0, 1, 2, 3, 4]
        # Determina il preset basandosi sui giorni salvati
        if schedule.days_of_week == [0, 1, 2, 3, 4]:
            form.days_preset.data = 'workdays'
        elif schedule.days_of_week == [5, 6]:
            form.days_preset.data = 'weekend'
        elif schedule.days_of_week == [0, 1, 2, 3, 4, 5, 6]:
            form.days_preset.data = 'all_week'
        else:
            form.days_preset.data = 'custom'
    
    if form.validate_on_submit():
        # Determina i giorni della settimana dal preset o dalla selezione personalizzata
        if form.days_preset.data != 'custom':
            days_of_week = form.get_days_from_preset(form.days_preset.data)
        else:
            days_of_week = form.days_of_week.data
        
        schedule.name = form.name.data
        schedule.start_time_min = form.start_time_min.data
        schedule.start_time_max = form.start_time_max.data
        schedule.end_time_min = form.end_time_min.data
        schedule.end_time_max = form.end_time_max.data
        # Aggiorna campi legacy per compatibilità
        schedule.start_time = form.start_time_min.data
        schedule.end_time = form.end_time_min.data
        schedule.days_of_week = days_of_week
        schedule.description = form.description.data
        schedule.active = form.active.data
        
        db.session.commit()
        flash(f'Orario "{schedule.name}" modificato con successo', 'success')
        return redirect(url_for('admin.manage_work_schedules'))
    
    return render_template('edit_work_schedule.html', form=form, schedule=schedule)

@admin_bp.route('/orari/toggle/<int:schedule_id>')
@login_required
def toggle_work_schedule(schedule_id):
    """Attiva/disattiva un orario di lavoro"""
    if not current_user.can_manage_schedules():
        flash('Non hai i permessi per modificare orari', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    schedule = filter_by_company(WorkSchedule.query).filter_by(id=schedule_id).first_or_404()
    schedule.active = not schedule.active
    db.session.commit()
    
    status = 'attivato' if schedule.active else 'disattivato'
    flash(f'Orario "{schedule.name}" {status} con successo', 'success')
    return redirect(url_for('admin.manage_work_schedules'))

@admin_bp.route('/orari/delete/<int:schedule_id>')
@login_required
@require_admin_permission
def delete_work_schedule(schedule_id):
    """Elimina definitivamente un orario di lavoro"""
    if not current_user.can_manage_schedules():
        flash('Non hai i permessi per eliminare orari', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    schedule = filter_by_company(WorkSchedule.query).filter_by(id=schedule_id).first_or_404()
    schedule_name = schedule.name
    
    try:
        db.session.delete(schedule)
        db.session.commit()
        flash(f'Orario "{schedule_name}" eliminato definitivamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Errore durante l\'eliminazione. Potrebbero esistere dipendenze.', 'error')
        
    return redirect(url_for('admin.manage_work_schedules'))

# =============================================================================
# ROLE MANAGEMENT ROUTES
# =============================================================================

@admin_bp.route('/roles')
@login_required
@require_admin_permission
def manage_roles():
    """Gestisce i ruoli dinamici del sistema (solo Admin)"""
    # Chi può gestire può automaticamente visualizzare
    if not (current_user.has_permission('can_manage_roles') or current_user.has_permission('can_view_roles')):
        flash('Non hai i permessi per accedere ai ruoli', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    roles = filter_by_company(UserRole.query).order_by(UserRole.name).all()
    
    # Force cache refresh with headers
    response = make_response(render_template('manage_roles.html', roles=roles))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@admin_bp.route('/roles/create', methods=['GET', 'POST'])
@login_required
@require_admin_permission
def create_role():
    """Crea un nuovo ruolo dinamico"""
    if not current_user.has_permission('can_manage_roles'):
        flash('Non hai i permessi per creare ruoli', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    form = RoleForm()
    if form.validate_on_submit():
        new_role = UserRole(
            name=form.name.data,
            display_name=form.display_name.data,
            description=form.description.data,
            permissions=form.get_permissions_dict(),
            active=form.active.data
        )
        set_company_on_create(new_role)
        db.session.add(new_role)
        db.session.commit()
        
        flash(f'Ruolo "{form.display_name.data}" creato con successo', 'success')
        return redirect(url_for('admin.manage_roles'))
    
    return render_template('create_role.html', form=form)

@admin_bp.route('/roles/edit/<int:role_id>', methods=['GET', 'POST'])
@login_required
@require_admin_permission
def edit_role(role_id):
    """Modifica un ruolo esistente"""
    if not current_user.has_permission('can_manage_roles'):
        flash('Non hai i permessi per modificare ruoli', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    role = filter_by_company(UserRole.query).filter_by(id=role_id).first_or_404()
    
    # Verifica che non sia un ruolo di sistema protetto (solo Admin rimane completamente protetto)
    fully_protected_roles = ['Admin']
    if role.name in fully_protected_roles:
        flash(f'Il ruolo "{role.display_name}" è protetto e non può essere modificato', 'danger')
        return redirect(url_for('admin.manage_roles'))
    
    # Se è il ruolo Amministratore e l'utente corrente non è amministratore, blocca
    if role.name == 'Amministratore' and not current_user.has_role('Amministratore'):
        flash(f'Solo un amministratore può modificare il ruolo "{role.display_name}"', 'danger')
        return redirect(url_for('admin.manage_roles'))
    
    # Determina se l'utente corrente è amministratore che modifica ruolo Amministratore
    # In questo caso può modificare TUTTI i permessi eccetto quelli critici
    is_admin_editing_admin_role = current_user.has_role('Amministratore') and role.name == 'Amministratore'
    
    # Lista dei permessi critici che non possono essere modificati dall'admin (per sicurezza)
    protected_permissions = ['can_manage_roles', 'can_manage_users'] if is_admin_editing_admin_role else []
    
    form = RoleForm(original_name=role.name, widget_only=False, protected_permissions=protected_permissions)
    
    if form.validate_on_submit():
        if is_admin_editing_admin_role:
            # Per l'amministratore che modifica il ruolo Amministratore:
            # può modificare TUTTI i permessi eccetto quelli protetti
            existing_permissions = role.permissions.copy()
            new_permissions = form.get_permissions_dict()
            
            # Mantieni i permessi protetti con i valori esistenti
            for protected_perm in protected_permissions:
                if protected_perm in existing_permissions:
                    new_permissions[protected_perm] = existing_permissions[protected_perm]
            
            # Aggiorna tutti gli altri permessi
            role.permissions = new_permissions
            # Non modificare name, display_name per il ruolo Amministratore
            role.description = form.description.data
            role.active = form.active.data
        else:
            # Per altri utenti autorizzati, aggiorna tutti i permessi normalmente
            role.name = form.name.data
            role.display_name = form.display_name.data
            role.description = form.description.data
            role.permissions = form.get_permissions_dict()
            role.active = form.active.data
        
        db.session.commit()
        
        flash(f'Ruolo "{role.display_name}" modificato con successo', 'success')
        return redirect(url_for('admin.manage_roles'))
    
    # Popola il form con i dati esistenti
    form.name.data = role.name
    form.display_name.data = role.display_name
    form.description.data = role.description
    form.active.data = role.active
    form.populate_permissions(role.permissions)
    
    return render_template('edit_role.html', form=form, role=role, 
                         is_admin_widget_only=False,
                         is_admin_editing_admin_role=is_admin_editing_admin_role,
                         protected_permissions=protected_permissions)

@admin_bp.route('/roles/toggle/<int:role_id>')
@login_required
@require_admin_permission
def toggle_role(role_id):
    """Attiva/disattiva un ruolo"""
    if not current_user.has_permission('can_manage_roles'):
        flash('Non hai i permessi per modificare ruoli', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    role = filter_by_company(UserRole.query).filter_by(id=role_id).first_or_404()
    
    # Verifica che non sia un ruolo di sistema protetto
    protected_roles = ['Admin', 'Amministratore']
    if role.name in protected_roles:
        flash(f'Non è possibile disattivare il ruolo "{role.display_name}" perché è protetto dal sistema', 'danger')
        return redirect(url_for('admin.manage_roles'))
    
    role.active = not role.active
    db.session.commit()
    
    status = 'attivato' if role.active else 'disattivato'
    flash(f'Ruolo "{role.display_name}" {status} con successo', 'success')
    return redirect(url_for('admin.manage_roles'))

@admin_bp.route('/roles/delete/<int:role_id>')
@login_required
@require_admin_permission
def delete_role(role_id):
    """Elimina un ruolo (solo se non ci sono utenti associati)"""
    if not current_user.has_permission('can_manage_roles'):
        flash('Non hai i permessi per eliminare ruoli', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    role = filter_by_company(UserRole.query).filter_by(id=role_id).first_or_404()
    
    # Verifica che non sia un ruolo di sistema protetto
    protected_roles = ['Admin', 'Amministratore']
    if role.name in protected_roles:
        flash(f'Non è possibile eliminare il ruolo "{role.display_name}" perché è protetto dal sistema', 'danger')
        return redirect(url_for('admin.manage_roles'))
    
    # Verifica che non ci siano utenti con questo ruolo
    users_with_role = User.query.filter_by(role=role.name).count()
    if users_with_role > 0:
        flash(f'Impossibile eliminare il ruolo "{role.display_name}": ci sono {users_with_role} utenti associati', 'danger')
        return redirect(url_for('admin.manage_roles'))
    
    role_name = role.display_name
    db.session.delete(role)
    db.session.commit()
    
    flash(f'Ruolo "{role_name}" eliminato con successo', 'success')
    return redirect(url_for('admin.manage_roles'))

# =============================================================================
# SYSTEM SETTINGS ROUTES
# =============================================================================

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@require_admin_permission
def admin_settings():
    """Configurazioni sistema generali"""
    if request.method == 'POST':
        try:
            # Placeholder per salvare configurazioni
            # Implementare secondo le necessità del sistema
            flash('Configurazioni aggiornate con successo', 'success')
            return redirect(url_for('admin.admin_settings'))
        except Exception as e:
            flash(f'Errore nell\'aggiornamento configurazioni: {str(e)}', 'danger')
    
    # Carica configurazioni attuali
    try:
        from config import get_config
        config = get_config()
    except ImportError:
        config = {}
    
    return render_template('admin_settings.html', config=config)


@admin_bp.route('/email-settings', methods=['GET', 'POST'])
@login_required
@require_admin_permission
def email_settings():
    """Configurazione SMTP per l'azienda"""
    from models import CompanyEmailSettings
    from forms import CompanyEmailSettingsForm, TestEmailForm
    from utils_tenant import get_user_company_id
    
    company_id = get_user_company_id()
    if not company_id:
        flash('Errore: azienda non trovata', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Ottieni configurazione esistente o creane una nuova
    email_config = CompanyEmailSettings.query.filter_by(company_id=company_id).first()  # type: ignore
    
    form = CompanyEmailSettingsForm()
    test_form = TestEmailForm()
    
    if form.validate_on_submit():
        try:
            if not email_config:
                email_config = CompanyEmailSettings(company_id=company_id)
                db.session.add(email_config)
            
            # Aggiorna configurazione
            email_config.mail_server = form.mail_server.data
            email_config.mail_port = form.mail_port.data
            email_config.mail_use_tls = form.mail_use_tls.data
            email_config.mail_use_ssl = form.mail_use_ssl.data
            email_config.mail_username = form.mail_username.data
            email_config.set_password(form.mail_password.data)  # Cripta la password
            email_config.mail_default_sender = form.mail_default_sender.data
            email_config.mail_reply_to = form.mail_reply_to.data
            email_config.active = True
            
            db.session.commit()
            flash('Configurazione email salvata con successo! Prova ad inviare un\'email di test.', 'success')
            return redirect(url_for('admin.email_settings'))
        except Exception as e:
            db.session.rollback()
            flash(f'Errore nel salvataggio: {str(e)}', 'danger')
    
    # Pre-popola form con dati esistenti
    if email_config and request.method == 'GET':
        form.mail_server.data = email_config.mail_server
        form.mail_port.data = email_config.mail_port
        form.mail_use_tls.data = email_config.mail_use_tls
        form.mail_use_ssl.data = email_config.mail_use_ssl
        form.mail_username.data = email_config.mail_username
        form.mail_default_sender.data = email_config.mail_default_sender
        form.mail_reply_to.data = email_config.mail_reply_to
    
    return render_template('admin_email_settings.html', 
                         form=form, 
                         test_form=test_form,
                         email_config=email_config)


@admin_bp.route('/email-settings/test', methods=['POST'])
@login_required
@require_admin_permission
def test_email():
    """Testa configurazione SMTP inviando email di prova"""
    from models import CompanyEmailSettings
    from forms import TestEmailForm
    from email_utils import EmailContext, send_email_smtp
    from utils_tenant import get_user_company_id
    from datetime import datetime
    
    company_id = get_user_company_id()
    if not company_id:
        flash('Errore: azienda non trovata', 'danger')
        return redirect(url_for('admin.email_settings'))
    
    form = TestEmailForm()
    email_config = None  # Inizializza qui
    
    if form.validate_on_submit():
        try:
            # Ottieni configurazione email
            email_config = CompanyEmailSettings.query.filter_by(
                company_id=company_id, 
                active=True
            ).first()  # type: ignore
            
            if not email_config:
                flash('Configurazione email non trovata. Salva prima la configurazione.', 'warning')
                return redirect(url_for('admin.email_settings'))
            
            # Crea contesto email
            context = EmailContext.from_company_settings(company_id)
            
            # Invia email di test
            subject = '✅ Test Configurazione SMTP - Life Platform'
            recipient = form.test_email.data
            
            body_text = f"""
Ciao,

Questa è un'email di test per verificare la configurazione SMTP della tua azienda su Life Platform.

Se ricevi questa email, la configurazione è corretta!

Dettagli configurazione:
- Server SMTP: {email_config.mail_server}
- Porta: {email_config.mail_port}
- TLS: {'Sì' if email_config.mail_use_tls else 'No'}
- SSL: {'Sì' if email_config.mail_use_ssl else 'No'}
- Mittente: {email_config.mail_default_sender}

Data test: {datetime.now().strftime('%d/%m/%Y %H:%M')}

---
Life Platform - Sistema Multi-Tenant
"""
            
            body_html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8f9fa; border-radius: 10px;">
                    <h2 style="color: #28a745;">✅ Test Configurazione SMTP</h2>
                    <p>Ciao,</p>
                    <p>Questa è un'email di test per verificare la configurazione SMTP della tua azienda su <strong>Life Platform</strong>.</p>
                    
                    <div style="background-color: #28a745; color: white; padding: 15px; border-radius: 5px; margin: 20px 0; text-align: center;">
                        <h3 style="margin: 0;">✓ Configurazione Corretta!</h3>
                    </div>
                    
                    <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="margin-top: 0;">Dettagli Configurazione:</h3>
                        <ul style="list-style: none; padding: 0;">
                            <li>📡 <strong>Server SMTP:</strong> {email_config.mail_server}</li>
                            <li>🔌 <strong>Porta:</strong> {email_config.mail_port}</li>
                            <li>🔒 <strong>TLS:</strong> {'Sì' if email_config.mail_use_tls else 'No'}</li>
                            <li>🔐 <strong>SSL:</strong> {'Sì' if email_config.mail_use_ssl else 'No'}</li>
                            <li>📧 <strong>Mittente:</strong> {email_config.mail_default_sender}</li>
                        </ul>
                        <p style="color: #666; font-size: 12px; margin-top: 15px;">
                            Data test: {datetime.now().strftime('%d/%m/%Y %H:%M')}
                        </p>
                    </div>
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    <p style="font-size: 12px; color: #999; text-align: center;">Life Platform - Sistema Multi-Tenant</p>
                </div>
            </body>
            </html>
            """
            
            # Invia email
            success = send_email_smtp(context, subject, [recipient], body_text, body_html)
            
            # Aggiorna stato test
            email_config.last_tested_at = datetime.now()
            email_config.test_status = 'success' if success else 'failed'
            email_config.test_error = None if success else 'Errore invio SMTP'
            db.session.commit()
            
            if success:
                flash(f'✅ Email di test inviata con successo a {recipient}', 'success')
            else:
                flash(f'❌ Errore nell\'invio dell\'email di test. Verifica la configurazione.', 'danger')
                
        except Exception as e:
            # Salva errore
            if email_config:
                email_config.last_tested_at = datetime.now()
                email_config.test_status = 'failed'
                email_config.test_error = str(e)
                db.session.commit()
            
            flash(f'Errore nel test email: {str(e)}', 'danger')
    else:
        flash('Email di test non valida', 'danger')
    
    return redirect(url_for('admin.email_settings'))

@admin_bp.route('/system_info')
@login_required
@require_admin_permission
def system_info():
    """Informazioni sistema e diagnostica"""
    import sys
    import platform
    from flask import __version__ as flask_version, current_app
    
    try:
        # Informazioni sistema
        system_info = {
            'python_version': sys.version,
            'platform': platform.platform(),
            'flask_version': flask_version,
            'database_url': os.environ.get('DATABASE_URL', 'Non configurato'),
            'environment': os.environ.get('ENVIRONMENT', 'development'),
            'debug_mode': current_app.debug,
        }
        
        # Statistiche database
        db_stats = {
            'total_users': User.query.count(),
            'active_users': User.query.filter_by(active=True).count(),
            'inactive_users': User.query.filter_by(active=False).count(),
        }
        
        return render_template('admin_system_info.html', 
                             system_info=system_info,
                             db_stats=db_stats)
                             
    except Exception as e:
        flash(f'Errore nel caricamento informazioni sistema: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_settings'))


# =============================================================================
# TIMEZONE DATA MIGRATION (One-time fix)
# =============================================================================

@admin_bp.route('/migrate_attendance_timestamps', methods=['GET', 'POST'])
@login_required
@require_admin_permission
def migrate_attendance_timestamps():
    """
    Migrazione dati una tantum per correggere i timestamp AttendanceEvent.
    
    Converte i timestamp esistenti da Italian time (salvati erroneamente come naive)
    a UTC naive corretto.
    
    IMPORTANTE: Questa operazione deve essere eseguita UNA SOLA VOLTA.
    """
    from models import AttendanceEvent
    from zoneinfo import ZoneInfo
    from datetime import timezone
    
    if request.method == 'GET':
        # Conta quanti record devono essere migrati
        total_events = AttendanceEvent.query.count()
        
        flash(f'Trovati {total_events} eventi di presenza. Clicca "Esegui Migrazione" per convertire i timestamp da Italian time a UTC.', 'info')
        
        return render_template('admin_system_info.html', 
                             show_migration=True,
                             total_events=total_events)
    
    # POST: Esegui la migrazione
    try:
        italy_tz = ZoneInfo('Europe/Rome')
        events = AttendanceEvent.query.all()
        migrated_count = 0
        
        for event in events:
            if event.timestamp:
                # Interpreta il timestamp corrente come Italian time naive
                # (è quello che è stato salvato erroneamente)
                italian_naive = event.timestamp
                
                # Aggiungi il timezone italiano
                italian_aware = italian_naive.replace(tzinfo=italy_tz)
                
                # Converti in UTC
                utc_aware = italian_aware.astimezone(timezone.utc)
                
                # Salva come naive UTC (l'event listener non serve qui poiché modifichiamo direttamente)
                event.timestamp = utc_aware.replace(tzinfo=None)
                migrated_count += 1
        
        db.session.commit()
        
        flash(f'✅ Migrazione completata con successo! {migrated_count} eventi aggiornati.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Errore durante la migrazione: {str(e)}', 'danger')
    
    return redirect(url_for('admin.system_info'))