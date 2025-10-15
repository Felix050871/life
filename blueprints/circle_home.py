from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, send_file
from flask_login import login_required, current_user
from app import db
from models import (
    CirclePost, CircleGroup, CirclePoll, CircleCalendarEvent, 
    CircleDocument, CircleToolLink, User, ConnectionRequest
)
from utils_tenant import filter_by_company, get_user_company_id, set_company_on_create
from datetime import datetime, timedelta
from sqlalchemy import desc
from werkzeug.utils import secure_filename
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import os
import uuid
import io

bp = Blueprint('circle', __name__, url_prefix='/circle')

@bp.route('/')
@login_required
def home():
    """Home page HUBLY con widget dinamici"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    company_id = get_user_company_id()
    
    # Widget: Ultimi post/news in evidenza (pinned)
    pinned_posts = filter_by_company(
        CirclePost.query.filter_by(published=True, pinned=True),
        current_user
    ).order_by(desc(CirclePost.created_at)).limit(3).all()
    
    # Widget: Ultime news/comunicazioni
    recent_posts = filter_by_company(
        CirclePost.query.filter_by(published=True, pinned=False),
        current_user
    ).order_by(desc(CirclePost.created_at)).limit(5).all()
    
    # Widget: Gruppi attivi
    active_groups = filter_by_company(
        CircleGroup.query.filter_by(is_private=False),
        current_user
    ).order_by(desc(CircleGroup.created_at)).limit(6).all()
    
    # Widget: Sondaggi attivi (non scaduti)
    now = datetime.utcnow()
    active_polls = filter_by_company(
        CirclePoll.query.filter(
            (CirclePoll.end_date == None) | (CirclePoll.end_date > now)
        ),
        current_user
    ).order_by(desc(CirclePoll.created_at)).limit(3).all()
    
    # Widget: Prossimi eventi calendario
    upcoming_events = filter_by_company(
        CircleCalendarEvent.query.filter(CircleCalendarEvent.start_datetime >= now),
        current_user
    ).order_by(CircleCalendarEvent.start_datetime).limit(5).all()
    
    # Widget: Strumenti rapidi
    quick_tools = filter_by_company(
        CircleToolLink.query.filter_by(is_active=True),
        current_user
    ).order_by(CircleToolLink.sort_order).limit(8).all()
    
    # Widget: Documenti recenti
    recent_documents = filter_by_company(
        CircleDocument.query.filter_by(is_active=True),
        current_user
    ).order_by(desc(CircleDocument.created_at)).limit(5).all()
    
    return render_template('circle/home.html',
                         pinned_posts=pinned_posts,
                         recent_posts=recent_posts,
                         active_groups=active_groups,
                         active_polls=active_polls,
                         upcoming_events=upcoming_events,
                         quick_tools=quick_tools,
                         recent_documents=recent_documents)

@bp.route('/delorean')
@login_required
def delorean():
    """Sezione Delorean - Archivio storico aziendale"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    delorean_posts = filter_by_company(
        CirclePost.query.filter_by(post_type='delorean', published=True),
        current_user
    ).order_by(desc(CirclePost.created_at)).all()
    
    return render_template('circle/delorean.html', posts=delorean_posts)

@bp.route('/personas')
@login_required
def personas():
    """Sezione Personas - Profili dipendenti"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    company_id = get_user_company_id()
    
    # Filtra utenti della stessa azienda, escludi system admin e amministratori, escludi l'utente corrente
    users = User.query.filter(
        User.company_id == company_id,
        User.active == True,
        User.is_system_admin == False,
        User.role != 'Amministratore',
        User.id != current_user.id
    ).order_by(User.last_name, User.first_name).all()
    
    return render_template('circle/personas.html', users=users)

@bp.route('/personas/<int:user_id>')
@login_required
def persona_detail(user_id):
    """Vista dettagliata profilo persona"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    company_id = get_user_company_id()
    
    # Verifica che l'utente appartenga alla stessa azienda
    user = User.query.filter_by(
        id=user_id,
        company_id=company_id,
        active=True,
        is_system_admin=False
    ).first()
    
    if not user or user.role == 'Amministratore':
        abort(404)
    
    return render_template('circle/persona_detail.html', user=user)

@bp.route('/personas/<int:user_id>/cv-pdf')
@login_required
def download_cv_pdf(user_id):
    """Genera e scarica il CV in formato PDF"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    company_id = get_user_company_id()
    
    # Verifica che l'utente appartenga alla stessa azienda
    user = User.query.filter_by(
        id=user_id,
        company_id=company_id,
        active=True,
        is_system_admin=False
    ).first()
    
    if not user or user.role == 'Amministratore':
        abort(404)
    
    # Crea PDF in memoria
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    story = []
    styles = getSampleStyleSheet()
    
    # Stili personalizzati
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#007bff'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#007bff'),
        spaceAfter=8,
        spaceBefore=12
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#333333'),
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6
    )
    
    # Titolo - Nome completo
    story.append(Paragraph(user.get_full_name(), title_style))
    
    # Job title e department
    if user.job_title:
        story.append(Paragraph(user.job_title, subheading_style))
    if user.department:
        story.append(Paragraph(user.department, body_style))
    
    story.append(Spacer(1, 0.5*cm))
    
    # Contatti
    contact_data = []
    if user.email:
        contact_data.append(['Email:', user.email])
    if user.phone_number:
        contact_data.append(['Telefono:', user.phone_number])
    
    if contact_data:
        contact_table = Table(contact_data, colWidths=[4*cm, 12*cm])
        contact_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(contact_table)
        story.append(Spacer(1, 0.5*cm))
    
    # Bio
    if user.bio:
        story.append(Paragraph('Profilo Professionale', heading_style))
        story.append(Paragraph(user.bio, body_style))
        story.append(Spacer(1, 0.3*cm))
    
    # Formazione
    if user.education:
        story.append(Paragraph('Formazione', heading_style))
        for edu in user.education:
            degree = edu.get('degree', '')
            institution = edu.get('institution', '')
            location = edu.get('location', '')
            start_date = edu.get('start_date', '')
            end_date = edu.get('end_date', '')
            description = edu.get('description', '')
            
            story.append(Paragraph(f"<b>{degree}</b>", subheading_style))
            if institution:
                inst_text = institution
                if location:
                    inst_text += f" - {location}"
                story.append(Paragraph(inst_text, body_style))
            if start_date or end_date:
                period = f"{start_date} - {end_date}" if start_date and end_date else (start_date or end_date)
                story.append(Paragraph(period, body_style))
            if description:
                story.append(Paragraph(description, body_style))
            story.append(Spacer(1, 0.2*cm))
    
    # Esperienza Professionale
    if user.experience:
        story.append(Paragraph('Esperienza Professionale', heading_style))
        for exp in user.experience:
            position = exp.get('position', '')
            company = exp.get('company', '')
            location = exp.get('location', '')
            start_date = exp.get('start_date', '')
            end_date = exp.get('end_date', '')
            current = exp.get('current', False)
            description = exp.get('description', '')
            
            story.append(Paragraph(f"<b>{position}</b>", subheading_style))
            if company:
                comp_text = company
                if location:
                    comp_text += f" - {location}"
                story.append(Paragraph(comp_text, body_style))
            if start_date or end_date or current:
                if current:
                    period = f"{start_date} - Presente" if start_date else "Presente"
                else:
                    period = f"{start_date} - {end_date}" if start_date and end_date else (start_date or end_date)
                story.append(Paragraph(period, body_style))
            if description:
                story.append(Paragraph(description, body_style))
            story.append(Spacer(1, 0.2*cm))
    
    # Competenze
    if user.skills:
        story.append(Paragraph('Competenze', heading_style))
        for skill_group in user.skills:
            category = skill_group.get('category', 'Competenze')
            items = skill_group.get('items', [])
            story.append(Paragraph(f"<b>{category}:</b> {', '.join(items)}", body_style))
        story.append(Spacer(1, 0.3*cm))
    
    # Lingue
    if user.languages:
        story.append(Paragraph('Lingue', heading_style))
        for lang in user.languages:
            language = lang.get('language', '')
            level = lang.get('level', '')
            proficiency = lang.get('proficiency', '')
            certifications = lang.get('certifications', '')
            
            lang_text = f"<b>{language}</b>"
            if level:
                lang_text += f" - {level}"
            if proficiency:
                lang_text += f" ({proficiency})"
            story.append(Paragraph(lang_text, body_style))
            if certifications:
                story.append(Paragraph(f"<i>{certifications}</i>", body_style))
        story.append(Spacer(1, 0.3*cm))
    
    # Certificazioni
    if user.certifications:
        story.append(Paragraph('Certificazioni', heading_style))
        for cert in user.certifications:
            name = cert.get('name', '')
            issuer = cert.get('issuer', '')
            date = cert.get('date', '')
            expiry = cert.get('expiry', '')
            credential_id = cert.get('credential_id', '')
            
            story.append(Paragraph(f"<b>{name}</b>", subheading_style))
            if issuer:
                story.append(Paragraph(f"Ente certificatore: {issuer}", body_style))
            if date or expiry:
                cert_period = f"Rilasciata: {date}" if date else ""
                if expiry:
                    cert_period += f" | Scadenza: {expiry}"
                story.append(Paragraph(cert_period, body_style))
            if credential_id:
                story.append(Paragraph(f"ID Credenziale: {credential_id}", body_style))
            story.append(Spacer(1, 0.2*cm))
    
    # Referenze
    if user.references:
        story.append(Paragraph('Referenze', heading_style))
        # Sostituisci newline con <br/> per il PDF
        references_html = user.references.replace('\n', '<br/>')
        story.append(Paragraph(references_html, body_style))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    
    # Prepara filename
    filename = f"CV_{user.last_name}_{user.first_name}.pdf"
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@bp.route('/tech-feed')
@login_required
def tech_feed():
    """Feed tecnologico - Aggiornamenti IT/Tech"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    tech_posts = filter_by_company(
        CirclePost.query.filter_by(post_type='tech_feed', published=True),
        current_user
    ).order_by(desc(CirclePost.created_at)).all()
    
    return render_template('circle/tech_feed.html', posts=tech_posts)

@bp.route('/delorean/create', methods=['GET', 'POST'])
@login_required
def create_delorean():
    """Crea nuovo post Delorean"""
    if not current_user.has_permission('can_create_posts'):
        abort(403)
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        comments_enabled = request.form.get('comments_enabled') == 'on'
        image_url = request.form.get('image_url')
        video_url = request.form.get('video_url')
        
        # Handle image upload
        if 'image_file' in request.files and request.files['image_file'].filename:
            file = request.files['image_file']
            
            # Generate unique filename
            file_ext = os.path.splitext(secure_filename(file.filename))[1]
            unique_filename = f"{uuid.uuid4().hex}{file_ext}"
            
            # Save path
            upload_folder = os.path.join('static', 'uploads', 'news')
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, unique_filename)
            
            # Save and resize image
            try:
                file.save(file_path)
                
                # Resize image to max 1200x800 using PIL
                with Image.open(file_path) as img:
                    # Convert to RGB if necessary
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                        img = background
                    
                    # Resize maintaining aspect ratio
                    img.thumbnail((1200, 800), Image.Resampling.LANCZOS)
                    img.save(file_path, quality=90, optimize=True)
                
                # Set image URL to uploaded file
                image_url = f'/static/uploads/news/{unique_filename}'
            except Exception as e:
                flash(f'Errore nel caricamento dell\'immagine: {str(e)}', 'warning')
        
        new_post = CirclePost(
            title=title,
            content=content,
            post_type='delorean',  # Tipo fisso
            author_id=current_user.id,
            pinned=False,
            comments_enabled=comments_enabled,
            image_url=image_url,
            video_url=video_url
        )
        set_company_on_create(new_post)
        
        db.session.add(new_post)
        db.session.commit()
        
        flash('Storia aziendale creata con successo!', 'success')
        return redirect(url_for('circle.delorean'))
    
    return render_template('circle/delorean_create.html')

@bp.route('/tech-feed/create', methods=['GET', 'POST'])
@login_required
def create_tech_feed():
    """Crea nuovo post Tech Feed"""
    if not current_user.has_permission('can_create_posts'):
        abort(403)
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        comments_enabled = request.form.get('comments_enabled') == 'on'
        image_url = request.form.get('image_url')
        video_url = request.form.get('video_url')
        
        # Handle image upload
        if 'image_file' in request.files and request.files['image_file'].filename:
            file = request.files['image_file']
            
            # Generate unique filename
            file_ext = os.path.splitext(secure_filename(file.filename))[1]
            unique_filename = f"{uuid.uuid4().hex}{file_ext}"
            
            # Save path
            upload_folder = os.path.join('static', 'uploads', 'news')
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, unique_filename)
            
            # Save and resize image
            try:
                file.save(file_path)
                
                # Resize image to max 1200x800 using PIL
                with Image.open(file_path) as img:
                    # Convert to RGB if necessary
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                        img = background
                    
                    # Resize maintaining aspect ratio
                    img.thumbnail((1200, 800), Image.Resampling.LANCZOS)
                    img.save(file_path, quality=90, optimize=True)
                
                # Set image URL to uploaded file
                image_url = f'/static/uploads/news/{unique_filename}'
            except Exception as e:
                flash(f'Errore nel caricamento dell\'immagine: {str(e)}', 'warning')
        
        new_post = CirclePost(
            title=title,
            content=content,
            post_type='tech_feed',  # Tipo fisso
            author_id=current_user.id,
            pinned=False,
            comments_enabled=comments_enabled,
            image_url=image_url,
            video_url=video_url
        )
        set_company_on_create(new_post)
        
        db.session.add(new_post)
        db.session.commit()
        
        flash('Post tech feed creato con successo!', 'success')
        return redirect(url_for('circle.tech_feed'))
    
    return render_template('circle/tech_feed_create.html')


# =============================================================================
# CONNECTION MANAGEMENT ROUTES
# =============================================================================

@bp.route('/connections/send/<int:user_id>', methods=['POST'])
@login_required
def send_connection_request(user_id):
    """Invia richiesta di connessione a un altro utente"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    # Verifica che l'utente target esista e sia nella stessa company
    target_user = filter_by_company(User.query).filter_by(id=user_id, active=True).first()
    if not target_user:
        flash('Utente non trovato', 'danger')
        return redirect(url_for('circle.personas'))
    
    # Non puoi collegarti a te stesso
    if target_user.id == current_user.id:
        flash('Non puoi collegarti a te stesso', 'warning')
        return redirect(url_for('circle.personas'))
    
    # Verifica se esiste già una connessione o richiesta
    existing = ConnectionRequest.query.filter(
        db.or_(
            db.and_(
                ConnectionRequest.sender_id == current_user.id,
                ConnectionRequest.recipient_id == target_user.id
            ),
            db.and_(
                ConnectionRequest.sender_id == target_user.id,
                ConnectionRequest.recipient_id == current_user.id
            )
        )
    ).first()
    
    if existing:
        if existing.status == 'accepted':
            flash('Sei già collegato con questo utente', 'info')
        elif existing.status == 'pending':
            flash('Hai già una richiesta pendente con questo utente', 'info')
        else:
            flash('Esiste già una richiesta con questo utente', 'warning')
        return redirect(url_for('circle.persona_detail', user_id=user_id))
    
    # Crea nuova richiesta
    new_request = ConnectionRequest(
        sender_id=current_user.id,
        recipient_id=target_user.id,
        status='pending'
    )
    set_company_on_create(new_request)
    
    db.session.add(new_request)
    db.session.commit()
    
    flash(f'Richiesta di connessione inviata a {target_user.get_full_name()}', 'success')
    return redirect(url_for('circle.persona_detail', user_id=user_id))


@bp.route('/connections/accept/<int:request_id>', methods=['POST'])
@login_required
def accept_connection_request(request_id):
    """Accetta richiesta di connessione"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    # Verifica che la richiesta esista e sia destinata all'utente corrente
    connection_request = filter_by_company(ConnectionRequest.query).filter_by(
        id=request_id,
        recipient_id=current_user.id,
        status='pending'
    ).first()
    
    if not connection_request:
        flash('Richiesta non trovata o già gestita', 'warning')
        return redirect(url_for('circle.connection_requests'))
    
    # Accetta la richiesta
    connection_request.status = 'accepted'
    connection_request.responded_at = datetime.utcnow()
    
    db.session.commit()
    
    flash(f'Ora sei collegato con {connection_request.sender.get_full_name()}', 'success')
    return redirect(url_for('circle.connection_requests'))


@bp.route('/connections/reject/<int:request_id>', methods=['POST'])
@login_required
def reject_connection_request(request_id):
    """Rifiuta richiesta di connessione"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    # Verifica che la richiesta esista e sia destinata all'utente corrente
    connection_request = filter_by_company(ConnectionRequest.query).filter_by(
        id=request_id,
        recipient_id=current_user.id,
        status='pending'
    ).first()
    
    if not connection_request:
        flash('Richiesta non trovata o già gestita', 'warning')
        return redirect(url_for('circle.connection_requests'))
    
    # Rifiuta la richiesta
    connection_request.status = 'rejected'
    connection_request.responded_at = datetime.utcnow()
    
    db.session.commit()
    
    flash('Richiesta di connessione rifiutata', 'info')
    return redirect(url_for('circle.connection_requests'))


@bp.route('/connections/cancel/<int:request_id>', methods=['POST'])
@login_required
def cancel_connection_request(request_id):
    """Annulla richiesta di connessione inviata"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    # Verifica che la richiesta esista e sia stata inviata dall'utente corrente
    connection_request = filter_by_company(ConnectionRequest.query).filter_by(
        id=request_id,
        sender_id=current_user.id,
        status='pending'
    ).first()
    
    if not connection_request:
        flash('Richiesta non trovata o già gestita', 'warning')
        return redirect(url_for('circle.personas'))
    
    # Elimina la richiesta
    db.session.delete(connection_request)
    db.session.commit()
    
    flash('Richiesta di connessione annullata', 'info')
    return redirect(url_for('circle.persona_detail', user_id=connection_request.recipient_id))


@bp.route('/connections/remove/<int:user_id>', methods=['POST'])
@login_required
def remove_connection(user_id):
    """Rimuove una connessione esistente"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    # Trova la connessione accettata
    connection = filter_by_company(ConnectionRequest.query).filter(
        db.or_(
            db.and_(
                ConnectionRequest.sender_id == current_user.id,
                ConnectionRequest.recipient_id == user_id
            ),
            db.and_(
                ConnectionRequest.sender_id == user_id,
                ConnectionRequest.recipient_id == current_user.id
            )
        ),
        ConnectionRequest.status == 'accepted'
    ).first()
    
    if not connection:
        flash('Connessione non trovata', 'warning')
        return redirect(url_for('circle.personas'))
    
    # Elimina la connessione
    db.session.delete(connection)
    db.session.commit()
    
    flash('Connessione rimossa', 'info')
    return redirect(url_for('circle.persona_detail', user_id=user_id))


@bp.route('/connections/requests')
@login_required
def connection_requests():
    """Pagina per visualizzare richieste di connessione pendenti"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    # Richieste ricevute (pendenti)
    received_requests = filter_by_company(ConnectionRequest.query).filter_by(
        recipient_id=current_user.id,
        status='pending'
    ).order_by(desc(ConnectionRequest.created_at)).all()
    
    # Richieste inviate (pendenti)
    sent_requests = filter_by_company(ConnectionRequest.query).filter_by(
        sender_id=current_user.id,
        status='pending'
    ).order_by(desc(ConnectionRequest.created_at)).all()
    
    return render_template('circle/connection_requests.html',
                         received_requests=received_requests,
                         sent_requests=sent_requests)
