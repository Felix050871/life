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
    
    # Get statistics for each company
    company_stats = []
    for company in companies:
        stats = {
            'company': company,
            'users_count': company.users.count(),
            'sedi_count': company.sedi.count()
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
        description = request.form.get('description')
        
        # Validate required fields
        if not name or not code:
            flash('Nome e codice azienda sono obbligatori', 'danger')
            return redirect(url_for('companies.create_company'))
        
        # Check if code already exists
        existing = Company.query.filter_by(code=code.upper()).first()
        if existing:
            flash(f'Esiste già un\'azienda con codice {code.upper()}', 'danger')
            return redirect(url_for('companies.create_company'))
        
        # Create new company
        company = Company(
            name=name,
            code=code.upper(),
            description=description,
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
        
        try:
            db.session.add(company)
            db.session.commit()
            flash(f'Azienda {company.name} creata con successo', 'success')
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
        description = request.form.get('description')
        active = request.form.get('active') == 'on'
        
        # Validate required fields
        if not name or not code:
            flash('Nome e codice azienda sono obbligatori', 'danger')
            return redirect(url_for('companies.edit_company', company_id=company_id))
        
        # Check if code already exists (excluding current company)
        existing = Company.query.filter(Company.code == code.upper(), Company.id != company_id).first()
        if existing:
            flash(f'Esiste già un\'azienda con codice {code.upper()}', 'danger')
            return redirect(url_for('companies.edit_company', company_id=company_id))
        
        # Update company data
        company.name = name
        company.code = code.upper()
        company.description = description
        company.active = active
        
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
    
    # Get company statistics
    users_count = company.users.count()
    sedi_count = company.sedi.count()
    
    return render_template('companies/edit.html', 
                         company=company,
                         users_count=users_count,
                         sedi_count=sedi_count)

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
