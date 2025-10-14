from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from app import db
from models import HublyPost, HublyComment, HublyLike, User
from utils_tenant import filter_by_company, get_user_company_id, set_company_on_create
from sqlalchemy import desc
from datetime import datetime

bp = Blueprint('hubly_news', __name__, url_prefix='/hubly/news')

@bp.route('/')
@login_required
def index():
    """Lista di tutte le news/comunicazioni"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    news_posts = filter_by_company(
        HublyPost.query.filter_by(post_type='news', published=True),
        current_user
    ).order_by(desc(HublyPost.pinned), desc(HublyPost.created_at)).all()
    
    return render_template('hubly/news/index.html', posts=news_posts, now=datetime.now())

@bp.route('/<int:post_id>')
@login_required
def view_post(post_id):
    """Visualizza dettaglio post con commenti"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    post = filter_by_company(HublyPost.query, current_user).get_or_404(post_id)
    
    # Carica commenti
    comments = HublyComment.query.filter_by(post_id=post_id).order_by(HublyComment.created_at).all()
    
    # Verifica se l'utente ha messo like
    user_liked = HublyLike.query.filter_by(post_id=post_id, user_id=current_user.id).first() is not None
    
    return render_template('hubly/news/view.html', 
                         post=post, 
                         comments=comments, 
                         user_liked=user_liked)

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
        
        new_post = HublyPost(
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
        
        flash('Post creato con successo!', 'success')
        return redirect(url_for('hubly_news.view_post', post_id=new_post.id))
    
    return render_template('hubly/news/create.html')

@bp.route('/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    """Aggiungi commento a un post"""
    if not current_user.has_permission('can_comment_posts'):
        abort(403)
    
    post = filter_by_company(HublyPost.query, current_user).get_or_404(post_id)
    
    # Verifica se i commenti sono abilitati per questo post
    if not post.comments_enabled:
        flash('I commenti sono disabilitati per questo post', 'warning')
        return redirect(url_for('hubly_news.view_post', post_id=post_id))
    
    content = request.form.get('content')
    
    if content:
        comment = HublyComment(
            post_id=post_id,
            author_id=current_user.id,
            content=content
        )
        db.session.add(comment)
        db.session.commit()
        flash('Commento aggiunto!', 'success')
    
    return redirect(url_for('hubly_news.view_post', post_id=post_id))

@bp.route('/<int:post_id>/like', methods=['POST'])
@login_required
def toggle_like(post_id):
    """Toggle like su un post"""
    if not current_user.has_permission('can_like_posts'):
        abort(403)
    
    post = filter_by_company(HublyPost.query, current_user).get_or_404(post_id)
    
    existing_like = HublyLike.query.filter_by(post_id=post_id, user_id=current_user.id).first()
    
    if existing_like:
        db.session.delete(existing_like)
        db.session.commit()
        flash('Like rimosso', 'info')
    else:
        new_like = HublyLike(post_id=post_id, user_id=current_user.id)
        db.session.add(new_like)
        db.session.commit()
        flash('Like aggiunto!', 'success')
    
    return redirect(url_for('hubly_news.view_post', post_id=post_id))

@bp.route('/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(post_id):
    """Modifica post esistente"""
    if not current_user.has_permission('can_edit_posts'):
        abort(403)
    
    post = filter_by_company(HublyPost.query, current_user).get_or_404(post_id)
    
    # Solo l'autore o admin possono modificare
    if post.author_id != current_user.id and not current_user.has_permission('can_delete_posts'):
        abort(403)
    
    if request.method == 'POST':
        post.title = request.form.get('title')
        post.content = request.form.get('content')
        post.pinned = request.form.get('pinned') == 'on'
        post.comments_enabled = request.form.get('comments_enabled') == 'on'
        post.image_url = request.form.get('image_url')
        post.video_url = request.form.get('video_url')
        post.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Post aggiornato!', 'success')
        return redirect(url_for('hubly_news.view_post', post_id=post.id))
    
    return render_template('hubly/news/edit.html', post=post)

@bp.route('/<int:post_id>/delete', methods=['POST'])
@login_required
def delete(post_id):
    """Elimina post"""
    if not current_user.has_permission('can_delete_posts'):
        abort(403)
    
    post = filter_by_company(HublyPost.query, current_user).get_or_404(post_id)
    
    # Elimina commenti e like associati
    HublyComment.query.filter_by(post_id=post_id).delete()
    HublyLike.query.filter_by(post_id=post_id).delete()
    
    db.session.delete(post)
    db.session.commit()
    
    flash('Post eliminato', 'success')
    return redirect(url_for('hubly_news.index'))

# =============================================================================
# API AJAX per interazioni reattive
# =============================================================================

@bp.route('/api/<int:post_id>/like', methods=['POST'])
@login_required
def api_toggle_like(post_id):
    """Toggle like via AJAX"""
    if not current_user.has_permission('can_like_posts'):
        return jsonify({'success': False, 'error': 'Non autorizzato'}), 403
    
    post = filter_by_company(HublyPost.query, current_user).get_or_404(post_id)
    
    existing_like = HublyLike.query.filter_by(post_id=post_id, user_id=current_user.id).first()
    
    if existing_like:
        db.session.delete(existing_like)
        db.session.commit()
        liked = False
    else:
        new_like = HublyLike(post_id=post_id, user_id=current_user.id)
        db.session.add(new_like)
        db.session.commit()
        liked = True
    
    # Get updated like count and users
    likes = HublyLike.query.filter_by(post_id=post_id).all()
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
    
    post = filter_by_company(HublyPost.query, current_user).get_or_404(post_id)
    
    if not post.comments_enabled:
        return jsonify({'success': False, 'error': 'Commenti disabilitati'}), 400
    
    content = request.json.get('content')
    
    if not content:
        return jsonify({'success': False, 'error': 'Contenuto vuoto'}), 400
    
    comment = HublyComment(
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
