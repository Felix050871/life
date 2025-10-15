from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from app import db
from models import CirclePost, CircleComment, CircleLike, User
from utils_tenant import filter_by_company, get_user_company_id, set_company_on_create
from utils_security import sanitize_html, validate_image_upload
from email_utils import send_announcement_notification
from sqlalchemy import desc
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image
import os
import uuid

bp = Blueprint('circle_news', __name__, url_prefix='/circle/news')

@bp.route('/')
@login_required
def index():
    """Lista di tutte le news/comunicazioni"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    news_posts = filter_by_company(
        CirclePost.query.filter(CirclePost.post_type.in_(['news', 'comunicazione'])).filter_by(published=True),
        current_user
    ).order_by(desc(CirclePost.pinned), desc(CirclePost.created_at)).all()
    
    return render_template('circle/news/index.html', posts=news_posts, now=datetime.now())

@bp.route('/<int:post_id>')
@login_required
def view_post(post_id):
    """Visualizza dettaglio post con commenti"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    post = filter_by_company(CirclePost.query, current_user).filter_by(id=post_id).first_or_404()
    
    # Carica commenti
    comments = CircleComment.query.filter_by(post_id=post_id).order_by(CircleComment.created_at).all()
    
    # Verifica se l'utente ha messo like
    user_liked = CircleLike.query.filter_by(post_id=post_id, user_id=current_user.id).first() is not None
    
    # Get tenant slug for URL construction
    from middleware_tenant import get_tenant_slug
    tenant_slug = get_tenant_slug()
    
    return render_template('circle/news/view.html', 
                         post=post, 
                         comments=comments, 
                         user_liked=user_liked,
                         tenant_slug=tenant_slug)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Crea nuovo post/news"""
    if not current_user.has_permission('can_create_posts'):
        abort(403)
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        post_type = request.form.get('post_type', 'news')
        pinned = request.form.get('pinned') == 'on'
        comments_enabled = request.form.get('comments_enabled') == 'on'
        image_url = request.form.get('image_url')
        video_url = request.form.get('video_url')
        
        # Sanitizza HTML per prevenire XSS
        content = sanitize_html(content)
        
        # Handle image upload
        if 'image_file' in request.files and request.files['image_file'].filename:
            file = request.files['image_file']
            
            # Valida immagine
            is_valid, error_msg = validate_image_upload(file)
            if not is_valid:
                flash(error_msg, 'danger')
                return render_template('circle/news/create.html')
            
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
            post_type=post_type,
            author_id=current_user.id,
            pinned=pinned,
            comments_enabled=comments_enabled,
            image_url=image_url,
            video_url=video_url
        )
        set_company_on_create(new_post)
        
        db.session.add(new_post)
        db.session.commit()
        
        # Invia email se richiesto (solo per comunicazioni)
        send_email_notification = request.form.get('send_email_notification') == 'on'
        if send_email_notification and post_type == 'comunicazione':
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
                post_url = url_for('circle_news.view_post', post_id=new_post.id, _external=True)
                
                # Invia notifiche
                sent_count = send_announcement_notification(new_post, company_users, post_url)
                
                if sent_count > 0:
                    flash(f'Comunicazione pubblicata! Email inviate a {sent_count} utenti.', 'success')
                else:
                    flash('Comunicazione pubblicata! Errore nell\'invio delle email.', 'warning')
            else:
                flash('Comunicazione pubblicata! Nessun utente trovato per l\'invio email.', 'info')
        else:
            flash('Post creato con successo!', 'success')
        
        return redirect(url_for('circle_news.view_post', post_id=new_post.id))
    
    return render_template('circle/news/create.html')

@bp.route('/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    """Aggiungi commento a un post"""
    if not current_user.has_permission('can_comment_posts'):
        abort(403)
    
    post = filter_by_company(CirclePost.query, current_user).filter_by(id=post_id).first_or_404()
    
    # Verifica se i commenti sono abilitati per questo post
    if not post.comments_enabled:
        flash('I commenti sono disabilitati per questo post', 'warning')
        return redirect(url_for('circle_news.view_post', post_id=post_id))
    
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
    
    return redirect(url_for('circle_news.view_post', post_id=post_id))

@bp.route('/<int:post_id>/like', methods=['POST'])
@login_required
def toggle_like(post_id):
    """Toggle like su un post"""
    if not current_user.has_permission('can_like_posts'):
        abort(403)
    
    post = filter_by_company(CirclePost.query, current_user).filter_by(id=post_id).first_or_404()
    
    existing_like = CircleLike.query.filter_by(post_id=post_id, user_id=current_user.id).first()
    
    if existing_like:
        db.session.delete(existing_like)
        db.session.commit()
        flash('Like rimosso', 'info')
    else:
        new_like = CircleLike(post_id=post_id, user_id=current_user.id)
        db.session.add(new_like)
        db.session.commit()
        flash('Like aggiunto!', 'success')
    
    return redirect(url_for('circle_news.view_post', post_id=post_id))

@bp.route('/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(post_id):
    """Modifica post esistente"""
    if not current_user.has_permission('can_edit_posts'):
        abort(403)
    
    post = filter_by_company(CirclePost.query, current_user).filter_by(id=post_id).first_or_404()
    
    # Solo l'autore o admin possono modificare
    if post.author_id != current_user.id and not current_user.has_permission('can_delete_posts'):
        abort(403)
    
    if request.method == 'POST':
        post.title = request.form.get('title')
        post.content = sanitize_html(request.form.get('content'))
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
                return render_template('circle/news/edit.html', post=post)
            
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
                
                # Delete old image if it was uploaded (not a URL)
                if post.image_url and post.image_url.startswith('/static/uploads/news/'):
                    old_image_path = post.image_url.lstrip('/')
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                
                # Set image URL to uploaded file
                post.image_url = f'/static/uploads/news/{unique_filename}'
            except Exception as e:
                flash(f'Errore nel caricamento dell\'immagine: {str(e)}', 'warning')
        else:
            # If no file uploaded, use URL from form
            post.image_url = request.form.get('image_url')
        
        db.session.commit()
        flash('Post aggiornato!', 'success')
        return redirect(url_for('circle_news.view_post', post_id=post.id))
    
    return render_template('circle/news/edit.html', post=post)

@bp.route('/<int:post_id>/delete', methods=['POST'])
@login_required
def delete(post_id):
    """Elimina post"""
    if not current_user.has_permission('can_delete_posts'):
        abort(403)
    
    post = filter_by_company(CirclePost.query, current_user).filter_by(id=post_id).first_or_404()
    
    # Elimina commenti e like associati
    CircleComment.query.filter_by(post_id=post_id).delete()
    CircleLike.query.filter_by(post_id=post_id).delete()
    
    db.session.delete(post)
    db.session.commit()
    
    flash('Post eliminato', 'success')
    return redirect(url_for('circle_news.index'))

# =============================================================================
# API AJAX per interazioni reattive
# =============================================================================

@bp.route('/api/<int:post_id>/like', methods=['POST'])
@login_required
def api_toggle_like(post_id):
    """Toggle like via AJAX"""
    if not current_user.has_permission('can_like_posts'):
        return jsonify({'success': False, 'error': 'Non autorizzato'}), 403
    
    post = filter_by_company(CirclePost.query, current_user).filter_by(id=post_id).first_or_404()
    
    existing_like = CircleLike.query.filter_by(post_id=post_id, user_id=current_user.id).first()
    
    if existing_like:
        db.session.delete(existing_like)
        db.session.commit()
        liked = False
    else:
        new_like = CircleLike(post_id=post_id, user_id=current_user.id)
        db.session.add(new_like)
        db.session.commit()
        liked = True
    
    # Get updated like count and users
    likes = CircleLike.query.filter_by(post_id=post_id).all()
    like_count = len(likes)
    like_users = []
    for like in likes[:5]:  # Primi 5 utenti
        if like.user:
            like_users.append({
                'id': like.user.id,
                'name': like.user.get_full_name(),
                'avatar': like.user.get_profile_image_url()
            })
    
    return jsonify({
        'success': True,
        'liked': liked,
        'like_count': like_count,
        'like_users': like_users
    })

@bp.route('/api/<int:post_id>/comment', methods=['POST'])
@login_required
def api_add_comment(post_id):
    """Aggiungi commento via AJAX"""
    if not current_user.has_permission('can_comment_posts'):
        return jsonify({'success': False, 'error': 'Non autorizzato'}), 403
    
    post = filter_by_company(CirclePost.query, current_user).filter_by(id=post_id).first_or_404()
    
    if not post.comments_enabled:
        return jsonify({'success': False, 'error': 'Commenti disabilitati'}), 400
    
    content = request.json.get('content')
    
    if not content:
        return jsonify({'success': False, 'error': 'Contenuto vuoto'}), 400
    
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
            'author_avatar': current_user.get_profile_image_url(),
            'created_at': comment.created_at.strftime('%d/%m/%Y %H:%M')
        }
    })
