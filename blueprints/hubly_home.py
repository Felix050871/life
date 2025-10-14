from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from models import (
    HublyPost, HublyGroup, HublyPoll, HublyCalendarEvent, 
    HublyDocument, HublyToolLink, User
)
from utils_tenant import filter_by_company, get_user_company_id, set_company_on_create
from datetime import datetime, timedelta
from sqlalchemy import desc
from werkzeug.utils import secure_filename
from PIL import Image
import os
import uuid

bp = Blueprint('hubly', __name__, url_prefix='/hubly')

@bp.route('/')
@login_required
def home():
    """Home page HUBLY con widget dinamici"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    company_id = get_user_company_id()
    
    # Widget: Ultimi post/news in evidenza (pinned)
    pinned_posts = filter_by_company(
        HublyPost.query.filter_by(published=True, pinned=True),
        current_user
    ).order_by(desc(HublyPost.created_at)).limit(3).all()
    
    # Widget: Ultime news/comunicazioni
    recent_posts = filter_by_company(
        HublyPost.query.filter_by(published=True, pinned=False),
        current_user
    ).order_by(desc(HublyPost.created_at)).limit(5).all()
    
    # Widget: Gruppi attivi
    active_groups = filter_by_company(
        HublyGroup.query.filter_by(is_private=False),
        current_user
    ).order_by(desc(HublyGroup.created_at)).limit(6).all()
    
    # Widget: Sondaggi attivi (non scaduti)
    now = datetime.utcnow()
    active_polls = filter_by_company(
        HublyPoll.query.filter(
            (HublyPoll.end_date == None) | (HublyPoll.end_date > now)
        ),
        current_user
    ).order_by(desc(HublyPoll.created_at)).limit(3).all()
    
    # Widget: Prossimi eventi calendario
    upcoming_events = filter_by_company(
        HublyCalendarEvent.query.filter(HublyCalendarEvent.start_datetime >= now),
        current_user
    ).order_by(HublyCalendarEvent.start_datetime).limit(5).all()
    
    # Widget: Strumenti rapidi
    quick_tools = filter_by_company(
        HublyToolLink.query.filter_by(is_active=True),
        current_user
    ).order_by(HublyToolLink.sort_order).limit(8).all()
    
    # Widget: Documenti recenti
    recent_documents = filter_by_company(
        HublyDocument.query.filter_by(is_active=True),
        current_user
    ).order_by(desc(HublyDocument.created_at)).limit(5).all()
    
    return render_template('hubly/home.html',
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
        HublyPost.query.filter_by(post_type='delorean', published=True),
        current_user
    ).order_by(desc(HublyPost.created_at)).all()
    
    return render_template('hubly/delorean.html', posts=delorean_posts)

@bp.route('/personas')
@login_required
def personas():
    """Sezione Personas - Profili dipendenti"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    company_id = get_user_company_id()
    
    # Filtra utenti della stessa azienda, escludi system admin
    users = User.query.filter_by(
        company_id=company_id, 
        active=True,
        is_system_admin=False
    ).order_by(User.last_name, User.first_name).all()
    
    return render_template('hubly/personas.html', users=users)

@bp.route('/tech-feed')
@login_required
def tech_feed():
    """Feed tecnologico - Aggiornamenti IT/Tech"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    tech_posts = filter_by_company(
        HublyPost.query.filter_by(post_type='tech_feed', published=True),
        current_user
    ).order_by(desc(HublyPost.created_at)).all()
    
    return render_template('hubly/tech_feed.html', posts=tech_posts)

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
        
        new_post = HublyPost(
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
        return redirect(url_for('hubly.delorean'))
    
    return render_template('hubly/delorean_create.html')

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
        
        new_post = HublyPost(
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
        return redirect(url_for('hubly.tech_feed'))
    
    return render_template('hubly/tech_feed_create.html')
