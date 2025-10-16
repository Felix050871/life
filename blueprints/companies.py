# =============================================================================
# COMPANIES MANAGEMENT BLUEPRINT
# =============================================================================
# Blueprint for managing companies (multi-tenant system)
# Only accessible to system administrators
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
import os

# Local imports
from models import Company, User, Sede
from app import db

# =============================================================================
# BLUEPRINT CONFIGURATION
# =============================================================================

companies_bp = Blueprint(
    'companies', 
    __name__, 
    url_prefix='/system/companies',
    template_folder='../templates',
    static_folder='../static'
)

# =============================================================================
# PERMISSION DECORATORS
# =============================================================================

def require_system_admin(f):
    """Decorator to check system admin permission"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_system_admin:
            flash('Solo gli amministratori di sistema possono accedere a questa sezione', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
UPLOAD_FOLDER = 'static/uploads/companies'

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_company_file(file, company_code, file_type):
    """Save company logo or background image"""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Create company-specific filename
        ext = filename.rsplit('.', 1)[1].lower()
        new_filename = f"{company_code}_{file_type}.{ext}"
        
        # Ensure upload directory exists
        upload_path = os.path.join(UPLOAD_FOLDER)
        os.makedirs(upload_path, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_path, new_filename)
        file.save(file_path)
        
        # Return relative path for database
        return f"uploads/companies/{new_filename}"
    return None

# =============================================================================
# COMPANIES CRUD ROUTES
# =============================================================================

@companies_bp.route('/')
@login_required
@require_system_admin
def list_companies():
    """List all companies"""
    companies = Company.query.order_by(Company.created_at.desc()).all()
    
    # Calculate statistics for each company (same as dashboard)
    company_stats = []
    for company in companies:
        # Get active users count
        active_users = company.users.filter_by(active=True).count()
        
        # Get company admin
        admin = company.users.filter_by(role='Amministratore').first()
        
        stats = {
            'company': company,
            'active_users': active_users,
            'total_users': company.users.count(),
            'admin': admin,
            'sedi_count': company.sedi.count(),
            'usage_percent': round((active_users / company.max_licenses * 100) if company.max_licenses > 0 else 0)
        }
        company_stats.append(stats)
    
    return render_template('companies/list.html', company_stats=company_stats)

@companies_bp.route('/create', methods=['GET', 'POST'])
@login_required
@require_system_admin
def create_company():
    """Create a new company"""
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        slug = request.form.get('slug', '').lower().strip()  # Get slug or generate from code
        description = request.form.get('description')
        max_licenses = request.form.get('max_licenses', 10, type=int)
        
        # Admin user data
        admin_username = request.form.get('admin_username')
        admin_email = request.form.get('admin_email')
        admin_password = request.form.get('admin_password')
        admin_full_name = request.form.get('admin_full_name')
        
        # Validate required fields
        if not name or not code:
            flash('Nome e codice azienda sono obbligatori', 'danger')
            return redirect(url_for('companies.create_company'))
        
        if not admin_username or not admin_email or not admin_password or not admin_full_name:
            flash('Tutti i campi dell\'amministratore sono obbligatori', 'danger')
            return redirect(url_for('companies.create_company'))
        
        # Generate slug from code if not provided
        if not slug:
            slug = code.lower().strip()
        
        # Validate slug format (alphanumeric and hyphens only)
        import re
        if not re.match(r'^[a-z0-9-]+$', slug):
            flash('Lo slug può contenere solo lettere minuscole, numeri e trattini', 'danger')
            return redirect(url_for('companies.create_company'))
        
        # Check if code already exists
        existing = Company.query.filter_by(code=code.upper()).first()
        if existing:
            flash(f'Esiste già un\'azienda con codice {code.upper()}', 'danger')
            return redirect(url_for('companies.create_company'))
        
        # Check if slug already exists
        existing_slug = Company.query.filter_by(slug=slug).first()
        if existing_slug:
            flash(f'Esiste già un\'azienda con slug {slug}', 'danger')
            return redirect(url_for('companies.create_company'))
        
        # Check if admin username or email already exists
        existing_user = User.query.filter(
            (User.username == admin_username) | (User.email == admin_email)
        ).first()
        if existing_user:
            flash('Username o email amministratore già in uso', 'danger')
            return redirect(url_for('companies.create_company'))
        
        try:
            # Create new company
            company = Company(
                name=name,
                code=code.upper(),
                slug=slug,
                description=description,
                max_licenses=max_licenses,
                active=True
            )
            
            # Handle logo upload
            if 'logo' in request.files:
                logo_file = request.files['logo']
                if logo_file.filename:
                    logo_path = save_company_file(logo_file, code.upper(), 'logo')
                    if logo_path:
                        company.logo = logo_path
            
            # Handle background image upload
            if 'background_image' in request.files:
                bg_file = request.files['background_image']
                if bg_file.filename:
                    bg_path = save_company_file(bg_file, code.upper(), 'background')
                    if bg_path:
                        company.background_image = bg_path
            
            db.session.add(company)
            db.session.flush()  # Get company.id without committing
            
            # Split full name into first and last name
            name_parts = admin_full_name.strip().split(' ', 1)
            first_name = name_parts[0] if name_parts else admin_full_name
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            # Create admin user for this company
            admin_user = User(
                username=admin_username,
                email=admin_email,
                password_hash=generate_password_hash(admin_password),
                first_name=first_name,
                last_name=last_name,
                role='Amministratore',
                company_id=company.id,
                active=True,
                is_system_admin=False,
                all_sedi=True  # Admin can access all locations by default
            )
            
            db.session.add(admin_user)
            db.session.commit()
            
            # Invia email di attivazione all'amministratore (usa SMTP globale SUPERADMIN)
            try:
                from email_utils import EmailContext, send_email_smtp
                
                # Usa configurazione globale (SUPERADMIN) per email di onboarding
                context = EmailContext.from_global_config()
                
                # URL di accesso per l'azienda
                tenant_login_url = url_for('auth.tenant_login', slug=slug, _external=True)
                
                subject = f'🎉 Benvenuto su Life Platform - Azienda {company.name} Attivata'
                
                body_text = f"""
Ciao {admin_full_name},

La tua azienda "{company.name}" è stata creata con successo su Life Platform!

Dettagli Accesso:
- URL Login: {tenant_login_url}
- Username: {admin_username}
- Password: (quella impostata durante la creazione)

Codice Azienda: {company.code}
Slug URL: {slug}
Licenze disponibili: {max_licenses}

Come amministratore, hai accesso completo a tutte le funzionalità di FLOW e CIRCLE.

Prossimi passi:
1. Accedi alla piattaforma usando il link sopra
2. Configura il server SMTP della tua azienda in Amministrazione > Configurazione Email
3. Crea le sedi aziendali e gli orari di lavoro
4. Invita i tuoi dipendenti

Per qualsiasi assistenza, contatta il supporto.

---
Life Platform - Sistema Multi-Tenant
"""
                
                body_html = f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8f9fa; border-radius: 10px;">
                        <h2 style="color: #28a745;">🎉 Benvenuto su Life Platform!</h2>
                        <p>Ciao <strong>{admin_full_name}</strong>,</p>
                        <p>La tua azienda "<strong>{company.name}</strong>" è stata creata con successo!</p>
                        
                        <div style="background-color: #28a745; color: white; padding: 15px; border-radius: 5px; margin: 20px 0; text-align: center;">
                            <h3 style="margin: 0;">✓ Azienda Attivata</h3>
                        </div>
                        
                        <div style="background-color: white; padding: 20px; border-radius: 5px; margin: 20px 0;">
                            <h3 style="margin-top: 0; color: #333;">Dettagli Accesso</h3>
                            <ul style="list-style: none; padding: 0;">
                                <li>🔗 <strong>URL Login:</strong> <a href="{tenant_login_url}">{tenant_login_url}</a></li>
                                <li>👤 <strong>Username:</strong> {admin_username}</li>
                                <li>🏢 <strong>Codice Azienda:</strong> {company.code}</li>
                                <li>🔑 <strong>Slug URL:</strong> {slug}</li>
                                <li>📊 <strong>Licenze:</strong> {max_licenses}</li>
                            </ul>
                            
                            <div style="text-align: center; margin-top: 20px;">
                                <a href="{tenant_login_url}" style="display: inline-block; padding: 12px 30px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px;">
                                    Accedi alla Piattaforma
                                </a>
                            </div>
                        </div>
                        
                        <div style="background-color: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <h4 style="margin-top: 0; color: #1976d2;">📝 Prossimi Passi</h4>
                            <ol style="margin: 10px 0; padding-left: 20px;">
                                <li>Accedi alla piattaforma usando il link sopra</li>
                                <li>Configura il server SMTP in <em>Amministrazione > Configurazione Email</em></li>
                                <li>Crea le sedi aziendali e gli orari di lavoro</li>
                                <li>Invita i tuoi dipendenti</li>
                            </ol>
                        </div>
                        
                        <p style="color: #666; font-size: 14px;">
                            Come amministratore, hai accesso completo a <strong>FLOW</strong> (gestione workforce) e <strong>CIRCLE</strong> (social intranet).
                        </p>
                        
                        <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                        <p style="font-size: 12px; color: #999; text-align: center;">Life Platform - Sistema Multi-Tenant</p>
                    </div>
                </body>
                </html>
                """
                
                # Invia email usando SMTP globale
                email_sent = send_email_smtp(context, subject, [admin_email], body_text, body_html)
                
                if email_sent:
                    flash(f'Azienda {company.name} creata con successo. Email di attivazione inviata a {admin_email}', 'success')
                else:
                    flash(f'Azienda {company.name} creata con successo. ATTENZIONE: Email di attivazione NON inviata (verifica SMTP globale)', 'warning')
            except Exception as e:
                # Non bloccare la creazione se l'email fallisce
                print(f"Errore invio email attivazione: {str(e)}")
                flash(f'Azienda {company.name} creata con successo. Admin: {admin_username}. Email non inviata.', 'success')
            
            return redirect(url_for('companies.list_companies'))
        except Exception as e:
            db.session.rollback()
            flash(f'Errore nella creazione dell\'azienda: {str(e)}', 'danger')
            return redirect(url_for('companies.create_company'))
    
    return render_template('companies/create.html')

@companies_bp.route('/edit/<int:company_id>', methods=['GET', 'POST'])
@login_required
@require_system_admin
def edit_company(company_id):
    """Edit an existing company"""
    company = Company.query.get_or_404(company_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        slug = request.form.get('slug', '').lower().strip()
        description = request.form.get('description')
        max_licenses = request.form.get('max_licenses', 10, type=int)
        active = request.form.get('active') == 'on'
        
        # Admin data
        admin_username = request.form.get('admin_username')
        admin_email = request.form.get('admin_email')
        admin_full_name = request.form.get('admin_full_name')
        admin_password = request.form.get('admin_password')
        
        # Validate required fields
        if not name or not code:
            flash('Nome e codice azienda sono obbligatori', 'danger')
            return redirect(url_for('companies.edit_company', company_id=company_id))
        
        # Generate slug from code if not provided
        if not slug:
            slug = code.lower().strip()
        
        # Validate slug format
        import re
        if not re.match(r'^[a-z0-9-]+$', slug):
            flash('Lo slug può contenere solo lettere minuscole, numeri e trattini', 'danger')
            return redirect(url_for('companies.edit_company', company_id=company_id))
        
        # Check if code already exists (excluding current company)
        existing = Company.query.filter(Company.code == code.upper(), Company.id != company_id).first()
        if existing:
            flash(f'Esiste già un\'azienda con codice {code.upper()}', 'danger')
            return redirect(url_for('companies.edit_company', company_id=company_id))
        
        # Check if slug already exists (excluding current company)
        existing_slug = Company.query.filter(Company.slug == slug, Company.id != company_id).first()
        if existing_slug:
            flash(f'Esiste già un\'azienda con slug {slug}', 'danger')
            return redirect(url_for('companies.edit_company', company_id=company_id))
        
        # Update company data
        company.name = name
        company.code = code.upper()
        company.slug = slug
        company.description = description
        company.max_licenses = max_licenses
        company.active = active
        
        # Update admin if data is provided
        if admin_username or admin_email or admin_full_name:
            admin = company.users.filter_by(role='Amministratore').first()
            if admin:
                # Check if username or email already exists (excluding current admin)
                if admin_username and admin_username != admin.username:
                    existing_user = User.query.filter(User.username == admin_username, User.id != admin.id).first()
                    if existing_user:
                        flash('Username amministratore già in uso', 'danger')
                        return redirect(url_for('companies.edit_company', company_id=company_id))
                    admin.username = admin_username
                
                if admin_email and admin_email != admin.email:
                    existing_user = User.query.filter(User.email == admin_email, User.id != admin.id).first()
                    if existing_user:
                        flash('Email amministratore già in uso', 'danger')
                        return redirect(url_for('companies.edit_company', company_id=company_id))
                    admin.email = admin_email
                
                if admin_full_name:
                    # Split full name into first and last name
                    name_parts = admin_full_name.strip().split(' ', 1)
                    admin.first_name = name_parts[0] if name_parts else admin_full_name
                    admin.last_name = name_parts[1] if len(name_parts) > 1 else ''
                
                # Update password if provided
                if admin_password:
                    admin.password_hash = generate_password_hash(admin_password)
        
        # Handle logo upload
        if 'logo' in request.files:
            logo_file = request.files['logo']
            if logo_file.filename:
                logo_path = save_company_file(logo_file, code.upper(), 'logo')
                if logo_path:
                    company.logo = logo_path
        
        # Handle background image upload
        if 'background_image' in request.files:
            bg_file = request.files['background_image']
            if bg_file.filename:
                bg_path = save_company_file(bg_file, code.upper(), 'background')
                if bg_path:
                    company.background_image = bg_path
        
        try:
            db.session.commit()
            flash(f'Azienda {company.name} aggiornata con successo', 'success')
            return redirect(url_for('companies.list_companies'))
        except Exception as e:
            db.session.rollback()
            flash(f'Errore nell\'aggiornamento dell\'azienda: {str(e)}', 'danger')
            return redirect(url_for('companies.edit_company', company_id=company_id))
    
    # Get company statistics and admin
    users_count = company.users.count()
    sedi_count = company.sedi.count()
    admin = company.users.filter_by(role='Amministratore').first()
    
    return render_template('companies/edit.html', 
                         company=company,
                         users_count=users_count,
                         sedi_count=sedi_count,
                         admin=admin)

@companies_bp.route('/delete/<int:company_id>', methods=['POST'])
@login_required
@require_system_admin
def delete_company(company_id):
    """Delete a company"""
    company = Company.query.get_or_404(company_id)
    
    # Check if company has associated users or sedi
    if company.users.count() > 0:
        flash(f'Impossibile eliminare {company.name}: ci sono utenti associati', 'danger')
        return redirect(url_for('companies.list_companies'))
    
    if company.sedi.count() > 0:
        flash(f'Impossibile eliminare {company.name}: ci sono sedi associate', 'danger')
        return redirect(url_for('companies.list_companies'))
    
    try:
        db.session.delete(company)
        db.session.commit()
        flash(f'Azienda {company.name} eliminata con successo', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Errore nell\'eliminazione dell\'azienda: {str(e)}', 'danger')
    
    return redirect(url_for('companies.list_companies'))

# =============================================================================
# COMPANY DETAILS & STATISTICS
# =============================================================================

@companies_bp.route('/view/<int:company_id>')
@login_required
@require_system_admin
def view_company(company_id):
    """View company details and statistics"""
    company = Company.query.get_or_404(company_id)
    
    # Get users and sedi
    users = company.users.all()
    sedi = company.sedi.all()
    
    return render_template('companies/view.html',
                         company=company,
                         users=users,
                         sedi=sedi)
