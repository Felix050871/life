# =============================================================================
# USER MANAGEMENT BLUEPRINT
# =============================================================================
# Blueprint for managing users, roles, sedi, admin functionality, 
# API endpoints and administrative operations
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from functools import wraps

# Local imports
from models import User, Sede, UserRole, WorkSchedule
from forms import UserForm, SedeForm, RoleForm, WorkScheduleForm
from app import db
from werkzeug.security import generate_password_hash
from sqlalchemy.orm import joinedload
from utils_tenant import filter_by_company, set_company_on_create
from utils_security import validate_image_upload

# =============================================================================
# BLUEPRINT CONFIGURATION
# =============================================================================

user_management_bp = Blueprint(
    'user_management', 
    __name__, 
    url_prefix='/admin',
    template_folder='../templates',
    static_folder='../static'
)

# =============================================================================
# PERMISSION DECORATORS
# =============================================================================

def require_admin_permission(f):
    """Decorator to check admin permission"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.can_manage_users():
            flash('Non hai i permessi per accedere a questa funzione amministrativa', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def require_turni_permission(f):
    """Decorator to check turni management permission"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.can_access_turni():
            flash('Non hai i permessi per accedere alla gestione turni', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# QR CODE ADMINISTRATION ROUTES
# =============================================================================

@user_management_bp.route('/qr_codes')
@login_required
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
    
    from config import get_config
    config = get_config()
    
    return render_template('admin_qr_codes.html', 
                         qr_urls=qr_urls,
                         qr_exist=qr_exist,
                         static_qr_urls=static_qr_urls,
                         can_manage=True,
                         config=config)

@user_management_bp.route('/generate_static_qr')
@login_required
def admin_generate_static_qr():
    """Genera QR code statici e li salva su file"""
    if not current_user.can_manage_qr():
        flash('Non hai i permessi per generare codici QR', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    from utils import generate_static_qr_codes
    
    # Genera i codici QR
    if generate_static_qr_codes():
        flash('QR code generati con successo e salvati come file statici', 'success')
    else:
        flash('Errore nella generazione dei QR code statici', 'danger')
    
    # Forza refresh della pagina per mostrare i nuovi QR code
    return redirect(url_for('user_management.admin_qr_codes') + '?refresh=1')

@user_management_bp.route('/view/qr_codes')
@login_required
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
    
    from config import get_config
    config = get_config()
    
    return render_template('view_qr_codes.html', 
                         qr_urls=qr_urls,
                         qr_exist=qr_exist,
                         static_qr_urls=static_qr_urls,
                         can_manage=False,
                         config=config)

# =============================================================================
# API ENDPOINTS  
# =============================================================================

@user_management_bp.route('/api/sede/<int:sede_id>/users')
@login_required
def api_sede_users(sede_id):
    """API per ottenere utenti di una sede specifica"""
    if not current_user.can_view_users():
        return jsonify({'error': 'Non autorizzato'}), 403
    
    sede = filter_by_company(Sede.query).filter_by(id=sede_id).first_or_404()
    
    # Verifica permessi sede
    if not current_user.all_sedi and current_user.sede_id != sede_id:
        return jsonify({'error': 'Accesso negato a questa sede'}), 403
    
    users = filter_by_company(User.query).filter_by(sede_id=sede_id, active=True).order_by(
        User.last_name, User.first_name
    ).all()
    
    users_data = []
    for user in users:
        users_data.append({
            'id': user.id,
            'name': user.get_full_name(),
            'role': user.role,
            'username': user.username,
            'email': user.email
        })
    
    return jsonify({
        'success': True,
        'sede': sede.name,
        'users': users_data,
        'count': len(users_data)
    })

@user_management_bp.route('/api/sede/<int:sede_id>/work_schedules')
@login_required
def api_sede_work_schedules(sede_id):
    """API per ottenere orari di lavoro di una sede"""
    if not current_user.can_view_work_schedules():
        return jsonify({'error': 'Non autorizzato'}), 403
    
    sede = filter_by_company(Sede.query).filter_by(id=sede_id).first_or_404()
    
    # Verifica permessi sede
    if not current_user.all_sedi and current_user.sede_id != sede_id:
        return jsonify({'error': 'Accesso negato a questa sede'}), 403
    
    schedules = filter_by_company(WorkSchedule.query).filter_by(sede_id=sede_id, active=True).order_by(
        WorkSchedule.name
    ).all()
    
    schedules_data = []
    for schedule in schedules:
        schedules_data.append({
            'id': schedule.id,
            'name': schedule.name,
            'description': schedule.description,
            'start_time': schedule.start_time.strftime('%H:%M') if schedule.start_time else None,
            'end_time': schedule.end_time.strftime('%H:%M') if schedule.end_time else None,
            'is_shift_based': schedule.is_shift_based
        })
    
    return jsonify({
        'success': True,
        'sede': sede.name,
        'work_schedules': schedules_data,
        'count': len(schedules_data)
    })

@user_management_bp.route('/api/roles')
@login_required
def api_roles():
    """API per ottenere lista dei ruoli disponibili"""
    if not current_user.can_view_roles():
        return jsonify({'error': 'Non autorizzato'}), 403
    
    roles = filter_by_company(UserRole.query).filter_by(active=True).order_by(UserRole.name).all()
    
    roles_data = []
    for role in roles:
        roles_data.append({
            'id': role.id,
            'name': role.name,
            'description': role.description,
            'permissions_count': len([p for p in role.__dict__ if p.startswith('can_') and getattr(role, p)])
        })
    
    return jsonify({
        'success': True,
        'roles': roles_data,
        'count': len(roles_data)
    })

# =============================================================================
# USER PROFILE ROUTES
# =============================================================================

@user_management_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def user_profile():
    """User profile page"""
    from forms import UserProfileForm
    from werkzeug.utils import secure_filename
    from PIL import Image
    import os
    import uuid
    
    form = UserProfileForm(obj=current_user, original_email=current_user.email)
    
    if form.validate_on_submit():
        # Update user profile
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.email = form.email.data
        
        # Update CIRCLE social fields
        current_user.bio = form.bio.data
        current_user.job_title = form.job_title.data
        current_user.department = form.department.data
        current_user.phone_number = form.phone_number.data
        current_user.linkedin_url = form.linkedin_url.data
        current_user.twitter_url = form.twitter_url.data
        current_user.instagram_url = form.instagram_url.data
        current_user.facebook_url = form.facebook_url.data
        current_user.github_url = form.github_url.data
        
        # Handle profile image upload
        if form.profile_image.data:
            file = form.profile_image.data
            
            # Valida immagine
            is_valid, error_msg = validate_image_upload(file)
            if not is_valid:
                flash(error_msg, 'danger')
                return render_template('user_profile.html', user=current_user, form=form)
            
            # Generate unique filename
            file_ext = os.path.splitext(secure_filename(file.filename))[1]
            unique_filename = f"{uuid.uuid4().hex}{file_ext}"
            
            # Save path
            upload_folder = os.path.join('static', 'uploads', 'profiles')
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, unique_filename)
            
            # Save and resize image
            file.save(file_path)
            
            # Resize image to 200x200 using PIL
            try:
                with Image.open(file_path) as img:
                    # Convert to RGB if necessary (for PNG with transparency)
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                        img = background
                    
                    # Resize maintaining aspect ratio and crop to square
                    img.thumbnail((200, 200), Image.Resampling.LANCZOS)
                    img.save(file_path, quality=85, optimize=True)
                
                # Delete old profile image if exists
                if current_user.profile_image:
                    old_image_path = os.path.join(upload_folder, current_user.profile_image)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                
                # Update user profile image
                current_user.profile_image = unique_filename
            except Exception as e:
                flash(f'Errore nel caricamento dell\'immagine: {str(e)}', 'danger')
        
        # Update password if provided
        if form.password.data:
            from werkzeug.security import generate_password_hash
            current_user.password_hash = generate_password_hash(form.password.data)
        
        db.session.commit()
        flash('Profilo aggiornato con successo', 'success')
        return redirect(url_for('user_management.user_profile'))
    
    return render_template('user_profile.html', user=current_user, form=form)

@user_management_bp.route('/profile/cv', methods=['GET', 'POST'])
@login_required
def cv_editor():
    """CV Editor page for managing education, experience, skills, and certifications"""
    import json
    
    if request.method == 'POST':
        try:
            # Get JSON data from request
            data = request.json if request.is_json else request.form
            
            # Parse education
            education = []
            if 'education' in data:
                education_data = json.loads(data['education']) if isinstance(data['education'], str) else data['education']
                for edu in education_data:
                    if edu.get('degree') or edu.get('institution'):
                        education.append({
                            'degree': edu.get('degree', ''),
                            'institution': edu.get('institution', ''),
                            'year': edu.get('year', ''),
                            'description': edu.get('description', '')
                        })
            
            # Parse experience
            experience = []
            if 'experience' in data:
                experience_data = json.loads(data['experience']) if isinstance(data['experience'], str) else data['experience']
                for exp in experience_data:
                    if exp.get('title') or exp.get('company'):
                        experience.append({
                            'title': exp.get('title', ''),
                            'company': exp.get('company', ''),
                            'period': exp.get('period', ''),
                            'description': exp.get('description', '')
                        })
            
            # Parse skills
            skills = []
            if 'skills' in data:
                skills_data = json.loads(data['skills']) if isinstance(data['skills'], str) else data['skills']
                skills = [s.strip() for s in skills_data if s.strip()] if isinstance(skills_data, list) else [s.strip() for s in skills_data.split(',') if s.strip()]
            
            # Parse certifications
            certifications = []
            if 'certifications' in data:
                cert_data = json.loads(data['certifications']) if isinstance(data['certifications'], str) else data['certifications']
                for cert in cert_data:
                    if cert.get('name'):
                        certifications.append({
                            'name': cert.get('name', ''),
                            'issuer': cert.get('issuer', ''),
                            'year': cert.get('year', ''),
                            'description': cert.get('description', '')
                        })
            
            # Update user CV data
            current_user.education = education if education else None
            current_user.experience = experience if experience else None
            current_user.skills = skills if skills else None
            current_user.certifications = certifications if certifications else None
            
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'message': 'CV aggiornato con successo'})
            else:
                flash('CV aggiornato con successo', 'success')
                return redirect(url_for('user_management.cv_editor'))
        
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'success': False, 'error': str(e)}), 400
            else:
                flash(f'Errore durante l\'aggiornamento del CV: {str(e)}', 'danger')
                return redirect(url_for('user_management.cv_editor'))
    
    # GET request - show editor
    # Ensure CV fields are initialized as empty lists if None
    education = current_user.education if current_user.education else []
    experience = current_user.experience if current_user.experience else []
    skills = current_user.skills if current_user.skills else []
    certifications = current_user.certifications if current_user.certifications else []
    
    return render_template('cv_editor.html', 
                         education=education, 
                         experience=experience, 
                         skills=skills, 
                         certifications=certifications)

# =============================================================================
# USER MANAGEMENT MAIN ROUTES
# =============================================================================

@user_management_bp.route('/users')
@login_required
def user_management():
    """Main user management page"""
    if not (current_user.can_manage_users() or current_user.can_view_users()):
        flash('Non hai i permessi per accedere alla gestione utenti', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    # Get users with their roles and sedi
    users = filter_by_company(User.query).options(
        joinedload(User.sede_obj)
    ).all()
    
    # Create user form (only for managers)
    form = UserForm() if current_user.can_manage_users() else None
    if form:
        # Populate form choices
        form.role.choices = [(role.name, role.name) for role in filter_by_company(UserRole.query).filter_by(active=True).all()]
        form.sede.choices = [(-1, 'Seleziona una sede')] + [(sede.id, sede.name) for sede in filter_by_company(Sede.query).filter_by(active=True).all()]
    
    return render_template('user_management.html', 
                         users=users, 
                         form=form,
                         can_manage_users=current_user.can_manage_users())

# =============================================================================
# USER CRUD OPERATIONS
# =============================================================================

@user_management_bp.route('/users/new', methods=['POST'])
@login_required
def new_user():
    """Create a new user"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per creare utenti', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    form = UserForm(is_edit=False)
    if form.validate_on_submit():
        # Crea il nuovo utente
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data),
            role=form.role.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            part_time_percentage=form.get_part_time_percentage_as_float(),
            active=form.active.data
        )
        set_company_on_create(user)
        db.session.add(user)
        db.session.flush()  # Per ottenere l'ID dell'utente
        
        db.session.commit()
        flash('Utente creato con successo', 'success')
        return redirect(url_for('user_management.user_management'))
    
    # Se ci sono errori di validazione, torna alla pagina principale con errori
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'{field}: {error}', 'danger')
    
    return redirect(url_for('user_management.user_management'))

@user_management_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """Edit an existing user"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per modificare gli utenti', 'danger')
        return redirect(url_for('user_management.user_management'))
    
    user = filter_by_company(User.query).filter_by(id=user_id).first_or_404()
    form = UserForm(original_username=user.username, is_edit=True, obj=user)
    
    if request.method == 'GET':
        return render_template('edit_user.html', form=form, user=user)
    
    if form.validate_on_submit():
        try:
            # Aggiorna i dati dell'utente
            user.username = form.username.data
            user.email = form.email.data
            if form.password.data and form.password.data.strip():
                user.password_hash = generate_password_hash(form.password.data)
                flash(f'Password aggiornata per utente {user.username}', 'info')
            user.role = form.role.data
            user.first_name = form.first_name.data
            user.last_name = form.last_name.data
            user.part_time_percentage = form.get_part_time_percentage_as_float()
            user.active = form.active.data
            
            db.session.commit()
            flash('Utente modificato con successo', 'success')
            return redirect(url_for('user_management.user_management'))
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante il salvataggio: {str(e)}', 'danger')
            import logging
            logging.error(f'Errore modifica utente {user_id}: {str(e)}', exc_info=True)
    else:
        # Se il form non valida, logga gli errori per debug
        if request.method == 'POST':
            import logging
            logging.debug(f'Form validation failed for user {user_id}. Errors: {form.errors}')
            if form.errors:
                for field, errors in form.errors.items():
                    for error in errors:
                        flash(f'Errore nel campo {field}: {error}', 'danger')
    
    return render_template('edit_user.html', form=form, user=user)

@user_management_bp.route('/users/toggle/<int:user_id>')
@login_required
def toggle_user(user_id):
    """Toggle user active status"""
    if not current_user.can_manage_users():
        flash('Non hai i permessi per modificare utenti', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    user = filter_by_company(User.query).filter_by(id=user_id).first_or_404()
    if user.id == current_user.id:
        flash('Non puoi disattivare il tuo account', 'warning')
        return redirect(url_for('user_management.user_management'))
    
    # Impedisce la disattivazione dell'amministratore
    if user.role == 'Amministratore':
        flash('Non è possibile disattivare l\'utente amministratore', 'danger')
        return redirect(url_for('user_management.user_management'))
    
    user.active = not user.active
    db.session.commit()
    
    status = 'attivato' if user.active else 'disattivato'
    flash(f'Utente {status} con successo', 'success')
    return redirect(url_for('user_management.user_management'))

# =============================================================================
# GDPR COMPLIANCE ROUTES
# =============================================================================

@user_management_bp.route('/account/delete', methods=['GET', 'POST'])
@login_required
def request_account_deletion():
    """Request account deletion (GDPR Right to be Forgotten)"""
    if current_user.is_system_admin:
        flash('Gli account SUPERADMIN non possono essere eliminati tramite questa funzione', 'danger')
        return redirect(url_for('user_management.profile'))
    
    if request.method == 'POST':
        # Verifica password per sicurezza
        from werkzeug.security import check_password_hash
        password = request.form.get('password')
        
        if not password or not check_password_hash(current_user.password_hash, password):
            flash('Password non corretta', 'danger')
            return redirect(url_for('user_management.request_account_deletion'))
        
        # Conferma checkbox
        confirm = request.form.get('confirm_deletion') == 'on'
        if not confirm:
            flash('Devi confermare la richiesta di cancellazione', 'warning')
            return redirect(url_for('user_management.request_account_deletion'))
        
        # Effettua la cancellazione cascade di tutti i dati
        try:
            _delete_user_cascade(current_user.id)
            flash('Il tuo account e tutti i dati personali sono stati eliminati', 'success')
            
            # Logout
            from flask_login import logout_user
            logout_user()
            return redirect(url_for('home.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la cancellazione dell\'account: {str(e)}', 'danger')
            return redirect(url_for('user_management.request_account_deletion'))
    
    return render_template('user/delete_account.html')

@user_management_bp.route('/account/export')
@login_required
def export_personal_data():
    """Export personal data (GDPR Right to Data Portability)"""
    import json
    from flask import Response
    
    # Raccogli tutti i dati personali dell'utente
    user_data = _collect_user_personal_data(current_user.id)
    
    # Formato richiesto
    format_type = request.args.get('format', 'json')
    
    if format_type == 'json':
        # Export in JSON
        json_data = json.dumps(user_data, indent=2, default=str, ensure_ascii=False)
        
        response = Response(
            json_data,
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment;filename=personal_data_{current_user.username}_{datetime.now().strftime("%Y%m%d")}.json'
            }
        )
        return response
    
    elif format_type == 'csv':
        # Export in CSV
        import csv
        from io import StringIO
        
        output = StringIO()
        
        # Crea CSV con dati utente principali
        writer = csv.writer(output)
        writer.writerow(['Campo', 'Valore'])
        
        # Dati profilo
        for key, value in user_data.get('profile', {}).items():
            writer.writerow([key, value])
        
        # Altre sezioni come conteggi
        writer.writerow([])
        writer.writerow(['Categoria', 'Conteggio'])
        for key, value in user_data.get('statistics', {}).items():
            if isinstance(value, int):
                writer.writerow([key, value])
        
        csv_data = output.getvalue()
        
        response = Response(
            csv_data,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment;filename=personal_data_{current_user.username}_{datetime.now().strftime("%Y%m%d")}.csv'
            }
        )
        return response
    
    flash('Formato non supportato', 'danger')
    return redirect(url_for('user_management.profile'))

def _delete_user_cascade(user_id):
    """
    Delete user and all related data (GDPR compliance)
    Implements cascade deletion for all user-related entities
    """
    from models import (
        AttendanceEvent, LeaveRequest, Shift, ShiftTemplate,
        ReperibilitaShift, ReperibilitaTemplate, Intervention,
        Holiday, InternalMessage, PasswordResetToken,
        ExpenseReport, ExpenseCategory, OvertimeRequest, MileageRequest,
        CirclePost, CircleGroup, CirclePoll, CirclePollVote,
        CircleDocument, CircleCalendarEvent, CircleComment, CircleLike,
        CircleToolLink, CircleGroupMembershipRequest, CircleGroupMessage,
        PresidioCoverage, PresidioCoverageTemplate, ReperibilitaIntervention,
        circle_group_members
    )
    
    user = User.query.get(user_id)
    if not user:
        raise ValueError("Utente non trovato")
    
    # 1. Delete attendance events
    filter_by_company(AttendanceEvent.query).filter_by(user_id=user_id).delete()
    
    # 2. Delete leave requests (both as requester and approver)
    filter_by_company(LeaveRequest.query).filter_by(user_id=user_id).delete()
    filter_by_company(LeaveRequest.query).filter_by(approved_by=user_id).update({LeaveRequest.approved_by: None})
    
    # 3. Delete shifts (both assigned and created)
    filter_by_company(Shift.query).filter_by(user_id=user_id).delete()
    filter_by_company(Shift.query).filter_by(created_by=user_id).delete()
    
    # 4. Delete shift templates created by user
    filter_by_company(ShiftTemplate.query).filter_by(created_by=user_id).delete()
    
    # 5. Delete reperibilità shifts and templates
    filter_by_company(ReperibilitaShift.query).filter_by(user_id=user_id).delete()
    filter_by_company(ReperibilitaShift.query).filter_by(created_by=user_id).delete()
    filter_by_company(ReperibilitaTemplate.query).filter_by(created_by=user_id).delete()
    filter_by_company(ReperibilitaIntervention.query).filter_by(user_id=user_id).delete()
    
    # 6. Delete general interventions
    filter_by_company(Intervention.query).filter_by(user_id=user_id).delete()
    
    # 7. Update holidays (set created_by to NULL instead of delete)
    filter_by_company(Holiday.query).filter_by(created_by=user_id).update({Holiday.created_by: None})
    
    # 8. Delete internal messages (received and sent)
    filter_by_company(InternalMessage.query).filter_by(recipient_id=user_id).delete()
    filter_by_company(InternalMessage.query).filter_by(sender_id=user_id).delete()
    
    # 9. Delete password reset tokens
    filter_by_company(PasswordResetToken.query).filter_by(user_id=user_id).delete()
    
    # 10. Delete expense reports and categories
    filter_by_company(ExpenseReport.query).filter_by(employee_id=user_id).delete()
    filter_by_company(ExpenseReport.query).filter_by(approved_by=user_id).update({ExpenseReport.approved_by: None})
    filter_by_company(ExpenseCategory.query).filter_by(created_by=user_id).delete()
    
    # 11. Delete overtime and mileage requests
    filter_by_company(OvertimeRequest.query).filter_by(employee_id=user_id).delete()
    filter_by_company(OvertimeRequest.query).filter_by(approved_by=user_id).update({OvertimeRequest.approved_by: None})
    filter_by_company(MileageRequest.query).filter_by(user_id=user_id).delete()
    filter_by_company(MileageRequest.query).filter_by(approved_by=user_id).update({MileageRequest.approved_by: None})
    
    # 12. Delete CIRCLE social content
    # Delete likes and comments first (FK constraints)
    filter_by_company(CircleLike.query).filter_by(user_id=user_id).delete()
    filter_by_company(CircleComment.query).filter_by(author_id=user_id).delete()
    
    # Delete posts
    filter_by_company(CirclePost.query).filter_by(author_id=user_id).delete()
    
    # 13. Delete poll votes
    filter_by_company(CirclePollVote.query).filter_by(user_id=user_id).delete()
    
    # 14. Handle groups (leave groups, delete created groups)
    # Remove from group memberships (usando filter_by_company su CircleGroup per isolamento)
    groups_to_clean = filter_by_company(CircleGroup.query).filter(
        circle_group_members.c.user_id == user_id
    ).all()
    for group in groups_to_clean:
        db.session.execute(
            circle_group_members.delete().where(
                (circle_group_members.c.user_id == user_id) & 
                (circle_group_members.c.group_id == group.id)
            )
        )
    filter_by_company(CircleGroup.query).filter_by(creator_id=user_id).delete()
    filter_by_company(CircleGroupMembershipRequest.query).filter_by(user_id=user_id).delete()
    filter_by_company(CircleGroupMembershipRequest.query).filter_by(reviewed_by=user_id).update({CircleGroupMembershipRequest.reviewed_by: None})
    
    # 15. Delete group messages
    filter_by_company(CircleGroupMessage.query).filter_by(sender_id=user_id).delete()
    filter_by_company(CircleGroupMessage.query).filter_by(recipient_id=user_id).delete()
    
    # 16. Delete documents uploaded by user
    filter_by_company(CircleDocument.query).filter_by(uploader_id=user_id).delete()
    
    # 17. Delete calendar events
    filter_by_company(CircleCalendarEvent.query).filter_by(creator_id=user_id).delete()
    
    # 18. Delete polls created by user
    # First delete poll options and votes for polls created by user
    polls = filter_by_company(CirclePoll.query).filter_by(creator_id=user_id).all()
    for poll in polls:
        from models import CirclePollOption
        filter_by_company(CirclePollOption.query).filter_by(poll_id=poll.id).delete()
        filter_by_company(CirclePollVote.query).filter_by(poll_id=poll.id).delete()
    filter_by_company(CirclePoll.query).filter_by(creator_id=user_id).delete()
    
    # 19. Update presidio coverage (set created_by to NULL)
    filter_by_company(PresidioCoverage.query).filter_by(created_by=user_id).update({PresidioCoverage.created_by: None})
    filter_by_company(PresidioCoverageTemplate.query).filter_by(created_by=user_id).update({PresidioCoverageTemplate.created_by: None})
    
    # 20. Finally, delete the user
    db.session.delete(user)
    db.session.commit()

def _collect_user_personal_data(user_id):
    """
    Collect all personal data for a user (GDPR compliance)
    Returns a dictionary with all user data for export
    """
    from models import (
        AttendanceEvent, LeaveRequest, Shift,
        ReperibilitaShift, Intervention, InternalMessage,
        ExpenseReport, OvertimeRequest, MileageRequest,
        CirclePost, CirclePoll, CircleDocument, CircleCalendarEvent
    )
    
    user = User.query.get(user_id)
    if not user:
        return {}
    
    data = {
        'profile': {
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'bio': user.bio,
            'linkedin_url': user.linkedin_url,
            'phone_number': user.phone_number,
            'department': user.department,
            'job_title': user.job_title,
            'created_at': user.created_at.isoformat() if user.created_at else None,
        },
        'work_data': {
            'sede': user.sede_obj.name if user.sede_obj else None,
            'work_schedule': user.work_schedule.name if user.work_schedule else None,
            'part_time_percentage': user.part_time_percentage,
            'banca_ore_enabled': user.banca_ore_enabled,
            'banca_ore_saldo': user.banca_ore_saldo,
        },
        'statistics': {
            'total_attendance_events': filter_by_company(AttendanceEvent.query).filter_by(user_id=user_id).count(),
            'total_leave_requests': filter_by_company(LeaveRequest.query).filter_by(user_id=user_id).count(),
            'total_shifts': filter_by_company(Shift.query).filter_by(user_id=user_id).count(),
            'total_reperibilita_shifts': filter_by_company(ReperibilitaShift.query).filter_by(user_id=user_id).count(),
            'total_interventions': filter_by_company(Intervention.query).filter_by(user_id=user_id).count(),
            'total_messages_received': filter_by_company(InternalMessage.query).filter_by(recipient_id=user_id).count(),
            'total_messages_sent': filter_by_company(InternalMessage.query).filter_by(sender_id=user_id).count(),
            'total_expense_reports': filter_by_company(ExpenseReport.query).filter_by(employee_id=user_id).count(),
            'total_overtime_requests': filter_by_company(OvertimeRequest.query).filter_by(employee_id=user_id).count(),
            'total_mileage_requests': filter_by_company(MileageRequest.query).filter_by(user_id=user_id).count(),
            'total_circle_posts': filter_by_company(CirclePost.query).filter_by(author_id=user_id).count(),
            'total_circle_polls': filter_by_company(CirclePoll.query).filter_by(creator_id=user_id).count(),
            'total_circle_documents': filter_by_company(CircleDocument.query).filter_by(uploader_id=user_id).count(),
            'total_circle_events': filter_by_company(CircleCalendarEvent.query).filter_by(creator_id=user_id).count(),
        },
        'export_date': datetime.now().isoformat(),
        'export_format': 'GDPR Personal Data Export'
    }
    
    return data

# =============================================================================
# BLUEPRINT REGISTRATION READY
# =============================================================================
# This blueprint is ready to be registered in main.py:
# from blueprints.user_management import user_management_bp
# app.register_blueprint(user_management_bp)
# =============================================================================