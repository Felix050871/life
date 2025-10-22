from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from models import CircleDocument
from utils_tenant import filter_by_company, get_user_company_id, set_company_on_create
from utils_security import sanitize_html, validate_document_upload
from sqlalchemy import desc
import os
from datetime import datetime

bp = Blueprint('circle_documents', __name__, url_prefix='/circle/documents')

UPLOAD_FOLDER = 'static/uploads/circle_documents'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'zip'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/')
@login_required
def index():
    """Lista documenti per categoria"""
    if not current_user.has_permission('can_view_documents'):
        abort(403)
    
    category = request.args.get('category', 'all')
    
    query = filter_by_company(
        CircleDocument.query.filter_by(is_active=True),
        current_user
    )
    
    if category != 'all':
        query = query.filter_by(category=category)
    
    documents = query.order_by(desc(CircleDocument.created_at)).all()
    
    return render_template('circle/documents/index.html', 
                         documents=documents,
                         selected_category=category)

@bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Carica nuovo documento"""
    if not current_user.has_permission('can_upload_documents'):
        abort(403)
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category', 'quality')
        version = request.form.get('version', '1.0')
        
        # Sanitizza HTML per prevenire XSS
        description = sanitize_html(description)
        
        if 'file' not in request.files:
            flash('Nessun file selezionato', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('Nessun file selezionato', 'danger')
            return redirect(request.url)
        
        # Valida documento
        is_valid, error_msg = validate_document_upload(file)
        if not is_valid:
            flash(error_msg, 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            
            # Usa percorso assoluto per compatibilità Apache
            from flask import current_app
            upload_path = os.path.join(current_app.root_path, UPLOAD_FOLDER)
            
            # Crea cartella se non esiste
            os.makedirs(upload_path, exist_ok=True)
            
            # Nome file univoco
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            filepath = os.path.join(upload_path, unique_filename)
            
            file.save(filepath)
            
            # Estrai estensione
            file_type = filename.rsplit('.', 1)[1].lower()
            
            new_document = CircleDocument(
                title=title,
                description=description,
                category=category,
                file_path=unique_filename,
                file_type=file_type,
                uploader_id=current_user.id,
                version=version
            )
            set_company_on_create(new_document)
            
            db.session.add(new_document)
            db.session.commit()
            
            flash('Documento caricato con successo!', 'success')
            return redirect(url_for('circle_documents.index'))
        else:
            flash('Tipo di file non consentito', 'danger')
            return redirect(request.url)
    
    return render_template('circle/documents/upload.html')

@bp.route('/<int:document_id>/download')
@login_required
def download(document_id):
    """Scarica documento"""
    if not current_user.has_permission('can_view_documents'):
        abort(403)
    
    document = filter_by_company(CircleDocument.query, current_user).filter_by(id=document_id).first_or_404()
    
    # Usa percorso assoluto per compatibilità Apache
    from flask import current_app
    filepath = os.path.join(current_app.root_path, UPLOAD_FOLDER, document.file_path)
    
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=document.file_path)
    else:
        flash('File non trovato', 'danger')
        return redirect(url_for('circle_documents.index'))

@bp.route('/<int:document_id>/delete', methods=['POST'])
@login_required
def delete(document_id):
    """Elimina documento"""
    if not current_user.has_permission('can_manage_documents'):
        abort(403)
    
    document = filter_by_company(CircleDocument.query, current_user).filter_by(id=document_id).first_or_404()
    
    # Elimina file fisico
    from flask import current_app
    filepath = os.path.join(current_app.root_path, UPLOAD_FOLDER, document.file_path)
    if os.path.exists(filepath):
        os.remove(filepath)
    
    db.session.delete(document)
    db.session.commit()
    
    flash('Documento eliminato', 'success')
    return redirect(url_for('circle_documents.index'))
