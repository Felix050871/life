from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from app import db
from models import CirclePost, CircleComment, CircleLike, User, Channel
from utils_tenant import filter_by_company, get_user_company_id, set_company_on_create
from utils_security import sanitize_html, validate_image_upload
from email_utils import send_announcement_notification
from sqlalchemy import desc
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image
import os
import uuid

bp = Blueprint('circle_communications', __name__, url_prefix='/circle/communications')

@bp.route('/')
@login_required
def index():
    """Lista di tutte le comunicazioni (filtrate per canale)"""
    if not current_user.has_permission('can_view_channels'):
        abort(403)
    
    # Filtra comunicazioni per canale (channel_id non null)
    communications = filter_by_company(
        CirclePost.query.filter(CirclePost.channel_id.isnot(None)).filter_by(published=True),
        current_user
    ).order_by(desc(CirclePost.pinned), desc(CirclePost.created_at)).all()
    
    # Carica canali attivi per il filtro
    channels = filter_by_company(Channel.query, current_user).filter_by(active=True).order_by(Channel.name).all()
    
    # Filtro canale selezionato
    selected_channel_id = request.args.get('channel_id', type=int)
    if selected_channel_id:
        communications = [c for c in communications if c.channel_id == selected_channel_id]
    
    return render_template('circle/communications/index.html', 
                         posts=communications, 
                         channels=channels,
                         selected_channel_id=selected_channel_id,
                         now=datetime.now())

@bp.route('/<int:post_id>')
@login_required
def view_post(post_id):
    """Visualizza dettaglio comunicazione con commenti"""
    if not current_user.has_permission('can_view_channels'):
        abort(403)
    
    post = filter_by_company(CirclePost.query, current_user).filter_by(id=post_id).first_or_404()
    
    # Verifica che sia una comunicazione (ha channel_id)
    if post.channel_id is None:
        abort(404)
    
    # Carica commenti
    comments = CircleComment.query.filter_by(post_id=post_id).order_by(CircleComment.created_at).all()
    
    # Verifica se l'utente ha messo like
    user_liked = CircleLike.query.filter_by(post_id=post_id, user_id=current_user.id).first() is not None
    
    # Get tenant slug for URL construction
    from middleware_tenant import get_tenant_slug
    tenant_slug = get_tenant_slug()
    
    return render_template('circle/communications/view.html', 
                         post=post, 
                         comments=comments, 
                         user_liked=user_liked,
                         tenant_slug=tenant_slug)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Crea nuova comunicazione associata a un canale"""
    if not current_user.has_permission('can_create_channel_communications'):
        abort(403)
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        channel_id = request.form.get('channel_id')
        pinned = request.form.get('pinned') == 'on'
        comments_enabled = request.form.get('comments_enabled') == 'on'
        image_url = request.form.get('image_url')
        video_url = request.form.get('video_url')
        
        # SECURITY: Valida che channel_id sia fornito e appartenga alla company dell'utente
        if not channel_id:
            flash('Devi selezionare un canale per la comunicazione', 'danger')
            channels = filter_by_company(Channel.query, current_user).filter_by(active=True).order_by(Channel.name).all()
            return render_template('circle/communications/create.html', channels=channels)
        
        # Valida che il channel appartenga alla company e sia attivo
        channel = filter_by_company(Channel.query, current_user).filter_by(
            id=int(channel_id),
            active=True
        ).first()
        
        if not channel:
            flash('Canale non valido o non accessibile', 'danger')
            channels = filter_by_company(Channel.query, current_user).filter_by(active=True).order_by(Channel.name).all()
            return render_template('circle/communications/create.html', channels=channels)
        
        # Sanitizza HTML per prevenire XSS
        content = sanitize_html(content)
        
        # Handle image upload
        if 'image_file' in request.files and request.files['image_file'].filename:
            file = request.files['image_file']
            
            # Valida immagine
            is_valid, error_msg = validate_image_upload(file)
            if not is_valid:
                flash(error_msg, 'danger')
                channels = filter_by_company(Channel.query, current_user).filter_by(active=True).order_by(Channel.name).all()
                return render_template('circle/communications/create.html', channels=channels)
            
            # Generate unique filename
            file_ext = os.path.splitext(secure_filename(file.filename))[1]
            unique_filename = f"{uuid.uuid4().hex}{file_ext}"
            
            # Save path
            upload_folder = os.path.join('static', 'uploads', 'communications')
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
                image_url = f'/static/uploads/communications/{unique_filename}'
            except Exception as e:
                flash(f'Errore nel caricamento dell\'immagine: {str(e)}', 'warning')
        
        new_post = CirclePost(
            title=title,
            content=content,
            post_type='comunicazione',
            channel_id=channel.id,
            author_id=current_user.id,
            pinned=pinned,
            comments_enabled=comments_enabled,
            image_url=image_url,
            video_url=video_url
        )
        set_company_on_create(new_post)
        
        db.session.add(new_post)
        db.session.commit()
        
        # Invia email se richiesto
        send_email_notification = request.form.get('send_email_notification') == 'on'
        if send_email_notification:
            company_id = get_user_company_id()
            
            # Recupera tutti gli utenti attivi dell'azienda (escluso l'autore)
            company_users = User.query.filter(
                User.company_id == company_id,
                User.active == True,
                User.id != current_user.id,
                User.email.isnot(None)
            ).all()
            
            if company_users:
                # Genera URL completo per il post
                post_url = url_for('circle_communications.view_post', post_id=new_post.id, _external=True)
                
                # Invia notifiche
                sent_count = send_announcement_notification(new_post, company_users, post_url)
                
                if sent_count > 0:
                    flash(f'Comunicazione pubblicata! Email inviate a {sent_count} utenti.', 'success')
                else:
                    flash('Comunicazione pubblicata! Errore nell\'invio delle email.', 'warning')
            else:
                flash('Comunicazione pubblicata! Nessun utente trovato per l\'invio email.', 'info')
        else:
            flash('Comunicazione creata con successo!', 'success')
        
        return redirect(url_for('circle_communications.view_post', post_id=new_post.id))
    
    # GET: carica canali attivi per il dropdown
    channels = filter_by_company(Channel.query, current_user).filter_by(active=True).order_by(Channel.name).all()
    return render_template('circle/communications/create.html', channels=channels)

@bp.route('/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    """Aggiungi commento a una comunicazione"""
    if not current_user.has_permission('can_comment_posts'):
        abort(403)
    
    post = filter_by_company(CirclePost.query, current_user).filter_by(id=post_id).first_or_404()
    
    # Verifica se i commenti sono abilitati per questo post
    if not post.comments_enabled:
        flash('I commenti sono disabilitati per questa comunicazione', 'warning')
        return redirect(url_for('circle_communications.view_post', post_id=post_id))
    
    content = request.form.get('content')
    
    if content:
        # Sanitizza HTML per prevenire XSS
        content = sanitize_html(content)
        
        comment = CircleComment(
            post_id=post_id,
            author_id=current_user.id,
            content=content
        )
        db.session.add(comment)
        db.session.commit()
        
        flash('Commento aggiunto!', 'success')
    
    return redirect(url_for('circle_communications.view_post', post_id=post_id))

@bp.route('/<int:post_id>/like', methods=['POST'])
@login_required
def toggle_like(post_id):
    """Toggle like su una comunicazione"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    post = filter_by_company(CirclePost.query, current_user).filter_by(id=post_id).first_or_404()
    
    # Verifica se già piace
    existing_like = CircleLike.query.filter_by(post_id=post_id, user_id=current_user.id).first()
    
    if existing_like:
        db.session.delete(existing_like)
        db.session.commit()
        flash('Like rimosso', 'info')
    else:
        new_like = CircleLike(
            post_id=post_id,
            user_id=current_user.id
        )
        db.session.add(new_like)
        db.session.commit()
        flash('Like aggiunto!', 'success')
    
    return redirect(url_for('circle_communications.view_post', post_id=post_id))

@bp.route('/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(post_id):
    """Modifica comunicazione esistente"""
    if not current_user.has_permission('can_edit_posts'):
        abort(403)
    
    post = filter_by_company(CirclePost.query, current_user).filter_by(id=post_id).first_or_404()
    
    # Solo l'autore o admin possono modificare
    if post.author_id != current_user.id and not current_user.has_permission('can_delete_posts'):
        abort(403)
    
    if request.method == 'POST':
        # SECURITY: Valida che il nuovo channel_id appartenga alla company dell'utente
        channel_id = request.form.get('channel_id')
        channel = filter_by_company(Channel.query, current_user).filter_by(
            id=int(channel_id),
            active=True
        ).first()
        
        if not channel:
            flash('Canale non valido o non accessibile', 'danger')
            channels = filter_by_company(Channel.query, current_user).filter_by(active=True).order_by(Channel.name).all()
            return render_template('circle/communications/edit.html', post=post, channels=channels)
        
        post.title = request.form.get('title')
        post.content = sanitize_html(request.form.get('content'))
        post.channel_id = channel.id
        post.pinned = request.form.get('pinned') == 'on'
        post.comments_enabled = request.form.get('comments_enabled') == 'on'
        post.video_url = request.form.get('video_url')
        post.updated_at = datetime.utcnow()
        
        # Handle image upload
        if 'image_file' in request.files and request.files['image_file'].filename:
            file = request.files['image_file']
            
            # Valida immagine
            is_valid, error_msg = validate_image_upload(file)
            if not is_valid:
                flash(error_msg, 'danger')
                channels = filter_by_company(Channel.query, current_user).filter_by(active=True).order_by(Channel.name).all()
                return render_template('circle/communications/edit.html', post=post, channels=channels)
            
            # Generate unique filename
            file_ext = os.path.splitext(secure_filename(file.filename))[1]
            unique_filename = f"{uuid.uuid4().hex}{file_ext}"
            
            # Save path
            upload_folder = os.path.join('static', 'uploads', 'communications')
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
                post.image_url = f'/static/uploads/communications/{unique_filename}'
            except Exception as e:
                flash(f'Errore nel caricamento dell\'immagine: {str(e)}', 'warning')
        
        db.session.commit()
        flash('Comunicazione aggiornata!', 'success')
        return redirect(url_for('circle_communications.view_post', post_id=post.id))
    
    # GET: carica canali per il dropdown
    channels = filter_by_company(Channel.query, current_user).filter_by(active=True).order_by(Channel.name).all()
    return render_template('circle/communications/edit.html', post=post, channels=channels)

@bp.route('/<int:post_id>/delete', methods=['POST'])
@login_required
def delete(post_id):
    """Elimina comunicazione"""
    post = filter_by_company(CirclePost.query, current_user).filter_by(id=post_id).first_or_404()
    
    # Solo l'autore o utenti con can_delete_posts possono eliminare
    if post.author_id != current_user.id and not current_user.has_permission('can_delete_posts'):
        abort(403)
    
    # Elimina commenti associati
    CircleComment.query.filter_by(post_id=post_id).delete()
    
    # Elimina likes associati
    CircleLike.query.filter_by(post_id=post_id).delete()
    
    db.session.delete(post)
    db.session.commit()
    
    flash('Comunicazione eliminata', 'success')
    return redirect(url_for('circle_communications.index'))

# API endpoints per AJAX
@bp.route('/api/<int:post_id>/like', methods=['POST'])
@login_required
def api_toggle_like(post_id):
    """Toggle like via AJAX"""
    if not current_user.has_permission('can_access_hubly'):
        return jsonify({'success': False, 'message': 'Permesso negato'}), 403
    
    post = filter_by_company(CirclePost.query, current_user).filter_by(id=post_id).first()
    if not post:
        return jsonify({'success': False, 'message': 'Post non trovato'}), 404
    
    # Verifica se già piace
    existing_like = CircleLike.query.filter_by(post_id=post_id, user_id=current_user.id).first()
    
    if existing_like:
        db.session.delete(existing_like)
        db.session.commit()
        liked = False
    else:
        new_like = CircleLike(
            post_id=post_id,
            user_id=current_user.id
        )
        db.session.add(new_like)
        db.session.commit()
        liked = True
    
    # Conta likes totali
    like_count = CircleLike.query.filter_by(post_id=post_id).count()
    
    return jsonify({
        'success': True,
        'liked': liked,
        'like_count': like_count
    })

@bp.route('/api/<int:post_id>/comment', methods=['POST'])
@login_required
def api_add_comment(post_id):
    """Aggiungi commento via AJAX"""
    if not current_user.has_permission('can_comment_posts'):
        return jsonify({'success': False, 'message': 'Permesso negato'}), 403
    
    post = filter_by_company(CirclePost.query, current_user).filter_by(id=post_id).first()
    if not post:
        return jsonify({'success': False, 'message': 'Post non trovato'}), 404
    
    if not post.comments_enabled:
        return jsonify({'success': False, 'message': 'Commenti disabilitati'}), 403
    
    content = request.json.get('content')
    if not content:
        return jsonify({'success': False, 'message': 'Contenuto mancante'}), 400
    
    # Sanitizza HTML
    content = sanitize_html(content)
    
    comment = CircleComment(
        post_id=post_id,
        author_id=current_user.id,
        content=content
    )
    db.session.add(comment)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'comment': {
            'id': comment.id,
            'content': comment.content,
            'author_name': current_user.get_full_name(),
            'created_at': comment.created_at.strftime('%d/%m/%Y %H:%M')
        }
    })
