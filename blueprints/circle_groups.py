from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from models import (CircleGroup, User, circle_group_members, CircleGroupMembershipRequest,
                   CircleGroupPost, CircleGroupMessage, CircleGroupPostLike, CircleGroupPostComment)
from utils_tenant import filter_by_company, get_user_company_id, set_company_on_create
from utils_security import sanitize_html, validate_image_upload
from sqlalchemy import desc, or_, and_
from werkzeug.utils import secure_filename
from PIL import Image
import os
import uuid

bp = Blueprint('circle_groups', __name__, url_prefix='/circle/groups')

@bp.route('/')
@login_required
def index():
    """Lista di tutti i gruppi"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    # Gruppi pubblici
    public_groups = filter_by_company(
        CircleGroup.query,
        current_user
    ).filter_by(is_private=False).order_by(desc(CircleGroup.created_at)).all()
    
    # Gruppi di cui l'utente è membro (anche privati)
    user_groups_query = db.session.query(CircleGroup).join(
        circle_group_members,
        CircleGroup.id == circle_group_members.c.group_id
    ).filter(circle_group_members.c.user_id == current_user.id)
    
    my_groups = filter_by_company(user_groups_query, current_user).all()
    
    return render_template('circle/groups/index.html', 
                         public_groups=public_groups,
                         my_groups=my_groups)

@bp.route('/<int:group_id>')
@login_required
def view_group(group_id):
    """Visualizza dettaglio gruppo"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    group = filter_by_company(CircleGroup.query, current_user).filter_by(id=group_id).first_or_404()
    
    # Verifica accesso gruppo privato
    if group.is_private:
        is_member = db.session.query(circle_group_members).filter_by(
            user_id=current_user.id,
            group_id=group_id
        ).first() is not None
        
        if not is_member:
            abort(403)
    
    # Carica membri del gruppo
    members_query = db.session.query(User, circle_group_members.c.is_admin).join(
        circle_group_members,
        User.id == circle_group_members.c.user_id
    ).filter(circle_group_members.c.group_id == group_id)
    
    members = members_query.all()
    
    return render_template('circle/groups/view.html', group=group, members=members)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Crea nuovo gruppo"""
    if not current_user.has_permission('can_create_groups'):
        abort(403)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        group_type = request.form.get('group_type', 'interest')
        is_private = request.form.get('is_private') == 'on'
        
        # Sanitizza HTML per prevenire XSS
        description = sanitize_html(description)
        
        new_group = CircleGroup(
            name=name,
            description=description,
            group_type=group_type,
            is_private=is_private,
            creator_id=current_user.id
        )
        set_company_on_create(new_group)
        
        db.session.add(new_group)
        db.session.flush()
        
        # Aggiungi il creatore come membro admin
        stmt = circle_group_members.insert().values(
            user_id=current_user.id,
            group_id=new_group.id,
            is_admin=True
        )
        db.session.execute(stmt)
        db.session.commit()
        
        flash('Gruppo creato con successo!', 'success')
        return redirect(url_for('circle_groups.view_group', group_id=new_group.id))
    
    return render_template('circle/groups/create.html')

@bp.route('/<int:group_id>/join', methods=['POST'])
@login_required
def join_group(group_id):
    """Unisciti a un gruppo"""
    if not current_user.has_permission('can_join_groups'):
        abort(403)
    
    group = filter_by_company(CircleGroup.query, current_user).filter_by(id=group_id).first_or_404()
    
    # Non puoi unirti a gruppi privati direttamente
    if group.is_private:
        flash('Questo gruppo è privato, serve un invito', 'warning')
        return redirect(url_for('circle_groups.index'))
    
    # Verifica se già membro
    existing = db.session.query(circle_group_members).filter_by(
        user_id=current_user.id,
        group_id=group_id
    ).first()
    
    if existing:
        flash('Sei già membro di questo gruppo', 'info')
    else:
        stmt = circle_group_members.insert().values(
            user_id=current_user.id,
            group_id=group_id,
            is_admin=False
        )
        db.session.execute(stmt)
        db.session.commit()
        flash('Ti sei unito al gruppo!', 'success')
    
    return redirect(url_for('circle_groups.view_group', group_id=group_id))

@bp.route('/<int:group_id>/leave', methods=['POST'])
@login_required
def leave_group(group_id):
    """Abbandona un gruppo"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    group = filter_by_company(CircleGroup.query, current_user).filter_by(id=group_id).first_or_404()
    
    # Non puoi lasciare il gruppo se sei il creatore
    if group.creator_id == current_user.id:
        flash('Il creatore non può abbandonare il gruppo', 'danger')
        return redirect(url_for('circle_groups.view_group', group_id=group_id))
    
    stmt = circle_group_members.delete().where(
        (circle_group_members.c.user_id == current_user.id) &
        (circle_group_members.c.group_id == group_id)
    )
    db.session.execute(stmt)
    db.session.commit()
    
    flash('Hai lasciato il gruppo', 'info')
    return redirect(url_for('circle_groups.index'))

@bp.route('/<int:group_id>/delete', methods=['POST'])
@login_required
def delete(group_id):
    """Elimina gruppo"""
    group = filter_by_company(CircleGroup.query, current_user).filter_by(id=group_id).first_or_404()
    
    # Solo il creatore o utenti con can_manage_groups possono eliminare
    if group.creator_id != current_user.id and not current_user.has_permission('can_manage_groups'):
        abort(403)
    
    # Elimina membri
    stmt = circle_group_members.delete().where(circle_group_members.c.group_id == group_id)
    db.session.execute(stmt)
    
    db.session.delete(group)
    db.session.commit()
    
    flash('Gruppo eliminato', 'success')
    return redirect(url_for('circle_groups.index'))

# ==================================================
# RICHIESTE DI ADESIONE (Gruppi Privati)
# ==================================================

@bp.route('/<int:group_id>/request-membership', methods=['POST'])
@login_required
def request_membership(group_id):
    """Richiedi adesione a un gruppo privato"""
    if not current_user.has_permission('can_join_groups'):
        abort(403)
    
    group = filter_by_company(CircleGroup.query, current_user).filter_by(id=group_id).first_or_404()
    
    if not group.is_private:
        flash('Questo gruppo è pubblico, puoi unirti direttamente', 'info')
        return redirect(url_for('circle_groups.join_group', group_id=group_id))
    
    # Verifica se già membro
    if group.is_member(current_user):
        flash('Sei già membro di questo gruppo', 'info')
        return redirect(url_for('circle_groups.view_group', group_id=group_id))
    
    # Verifica se esiste già una richiesta pendente
    existing_request = CircleGroupMembershipRequest.query.filter_by(
        group_id=group_id,
        user_id=current_user.id,
        status='pending'
    ).first()
    
    if existing_request:
        flash('Hai già una richiesta pendente per questo gruppo', 'warning')
        return redirect(url_for('circle_groups.index'))
    
    # Crea nuova richiesta
    message = request.form.get('message', '')
    # Sanitizza HTML per prevenire XSS
    message = sanitize_html(message)
    
    new_request = CircleGroupMembershipRequest(
        group_id=group_id,
        user_id=current_user.id,
        message=message
    )
    
    db.session.add(new_request)
    db.session.commit()
    
    flash('Richiesta di adesione inviata al creatore del gruppo', 'success')
    return redirect(url_for('circle_groups.index'))

@bp.route('/<int:group_id>/manage-requests')
@login_required
def manage_requests(group_id):
    """Gestisci richieste di adesione (solo creatore/admin)"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    group = filter_by_company(CircleGroup.query, current_user).filter_by(id=group_id).first_or_404()
    
    # Solo admin del gruppo possono gestire richieste
    if not group.is_admin(current_user):
        abort(403)
    
    # Carica richieste pendenti
    pending_requests = CircleGroupMembershipRequest.query.filter_by(
        group_id=group_id,
        status='pending'
    ).order_by(CircleGroupMembershipRequest.created_at.desc()).all()
    
    return render_template('circle/groups/manage_requests.html', 
                         group=group, 
                         requests=pending_requests)

@bp.route('/<int:group_id>/accept-request/<int:request_id>', methods=['POST'])
@login_required
def accept_request(group_id, request_id):
    """Accetta richiesta di adesione"""
    group = filter_by_company(CircleGroup.query, current_user).filter_by(id=group_id).first_or_404()
    
    if not group.is_admin(current_user):
        abort(403)
    
    membership_request = CircleGroupMembershipRequest.query.filter_by(
        id=request_id,
        group_id=group_id,
        status='pending'
    ).first_or_404()
    
    # Aggiungi utente al gruppo
    stmt = circle_group_members.insert().values(
        user_id=membership_request.user_id,
        group_id=group_id,
        is_admin=False
    )
    db.session.execute(stmt)
    
    # Aggiorna stato richiesta
    membership_request.status = 'accepted'
    membership_request.reviewed_at = db.func.now()
    membership_request.reviewed_by = current_user.id
    
    db.session.commit()
    
    flash('Richiesta accettata', 'success')
    return redirect(url_for('circle_groups.manage_requests', group_id=group_id))

@bp.route('/<int:group_id>/reject-request/<int:request_id>', methods=['POST'])
@login_required
def reject_request(group_id, request_id):
    """Rifiuta richiesta di adesione"""
    group = filter_by_company(CircleGroup.query, current_user).filter_by(id=group_id).first_or_404()
    
    if not group.is_admin(current_user):
        abort(403)
    
    membership_request = CircleGroupMembershipRequest.query.filter_by(
        id=request_id,
        group_id=group_id,
        status='pending'
    ).first_or_404()
    
    # Aggiorna stato richiesta
    membership_request.status = 'rejected'
    membership_request.reviewed_at = db.func.now()
    membership_request.reviewed_by = current_user.id
    
    db.session.commit()
    
    flash('Richiesta rifiutata', 'info')
    return redirect(url_for('circle_groups.manage_requests', group_id=group_id))

# ==================================================
# BACHECA GRUPPO (Post)
# ==================================================

@bp.route('/<int:group_id>/post', methods=['POST'])
@login_required
def create_post(group_id):
    """Crea un post nella bacheca del gruppo"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    group = filter_by_company(CircleGroup.query, current_user).filter_by(id=group_id).first_or_404()
    
    # Verifica membership
    if not group.is_member(current_user):
        abort(403)
    
    content = request.form.get('content')
    if not content:
        flash('Il contenuto non può essere vuoto', 'danger')
        return redirect(url_for('circle_groups.view_group', group_id=group_id))
    
    # Sanitizza HTML per prevenire XSS
    content = sanitize_html(content)
    
    # Gestione immagine
    image_url = None
    if 'image_file' in request.files:
        image_file = request.files['image_file']
        if image_file and image_file.filename:
            # Valida immagine
            is_valid, error_msg = validate_image_upload(image_file)
            if not is_valid:
                flash(error_msg, 'danger')
                return redirect(url_for('circle_groups.view_group', group_id=group_id))
            
            filename = secure_filename(image_file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            upload_folder = 'static/uploads/groups'
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, unique_filename)
            
            # Ridimensiona e salva
            img = Image.open(image_file)
            img.thumbnail((800, 800))
            img.save(filepath)
            image_url = f"/static/uploads/groups/{unique_filename}"
    
    # Crea post
    new_post = CircleGroupPost(
        group_id=group_id,
        author_id=current_user.id,
        content=content,
        image_url=image_url
    )
    
    db.session.add(new_post)
    db.session.commit()
    
    flash('Post pubblicato!', 'success')
    return redirect(url_for('circle_groups.view_group', group_id=group_id))

@bp.route('/<int:group_id>/delete-post/<int:post_id>', methods=['POST'])
@login_required
def delete_post(group_id, post_id):
    """Elimina un post dalla bacheca"""
    post = CircleGroupPost.query.filter_by(id=post_id, group_id=group_id).first_or_404()
    group = filter_by_company(CircleGroup.query, current_user).filter_by(id=group_id).first_or_404()
    
    # Solo autore o admin del gruppo possono eliminare
    if post.author_id != current_user.id and not group.is_admin(current_user):
        abort(403)
    
    db.session.delete(post)
    db.session.commit()
    
    flash('Post eliminato', 'success')
    return redirect(url_for('circle_groups.view_group', group_id=group_id))

@bp.route('/<int:group_id>/post/<int:post_id>/like', methods=['POST'])
@login_required
def toggle_post_like(group_id, post_id):
    """Toggle like su un post del gruppo"""
    if not current_user.has_permission('can_like_posts'):
        abort(403)
    
    group = filter_by_company(CircleGroup.query, current_user).filter_by(id=group_id).first_or_404()
    
    # Verifica membership
    if not group.is_member(current_user):
        abort(403)
    
    post = CircleGroupPost.query.filter_by(id=post_id, group_id=group_id).first_or_404()
    
    existing_like = CircleGroupPostLike.query.filter_by(post_id=post_id, user_id=current_user.id).first()
    
    if existing_like:
        db.session.delete(existing_like)
        db.session.commit()
    else:
        new_like = CircleGroupPostLike(
            post_id=post_id,
            user_id=current_user.id
        )
        db.session.add(new_like)
        db.session.commit()
    
    return redirect(url_for('circle_groups.view_group', group_id=group_id))

@bp.route('/<int:group_id>/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_post_comment(group_id, post_id):
    """Aggiungi commento a un post del gruppo"""
    if not current_user.has_permission('can_comment_posts'):
        abort(403)
    
    group = filter_by_company(CircleGroup.query, current_user).filter_by(id=group_id).first_or_404()
    
    # Verifica membership
    if not group.is_member(current_user):
        abort(403)
    
    post = CircleGroupPost.query.filter_by(id=post_id, group_id=group_id).first_or_404()
    
    content = request.form.get('content')
    if not content:
        flash('Il commento non può essere vuoto', 'danger')
        return redirect(url_for('circle_groups.view_group', group_id=group_id))
    
    # Sanitizza HTML per prevenire XSS
    content = sanitize_html(content)
    
    comment = CircleGroupPostComment(
        post_id=post_id,
        author_id=current_user.id,
        content=content
    )
    
    db.session.add(comment)
    db.session.commit()
    
    flash('Commento aggiunto!', 'success')
    return redirect(url_for('circle_groups.view_group', group_id=group_id))

@bp.route('/<int:group_id>/post/<int:post_id>/delete-comment/<int:comment_id>', methods=['POST'])
@login_required
def delete_post_comment(group_id, post_id, comment_id):
    """Elimina un commento da un post del gruppo"""
    comment = CircleGroupPostComment.query.filter_by(id=comment_id, post_id=post_id).first_or_404()
    group = filter_by_company(CircleGroup.query, current_user).filter_by(id=group_id).first_or_404()
    
    # Solo autore del commento o admin del gruppo possono eliminare
    if comment.author_id != current_user.id and not group.is_admin(current_user):
        abort(403)
    
    db.session.delete(comment)
    db.session.commit()
    
    flash('Commento eliminato', 'success')
    return redirect(url_for('circle_groups.view_group', group_id=group_id))

# ==================================================
# MESSAGGI DIRETTI (tra membri del gruppo)
# ==================================================

@bp.route('/<int:group_id>/messages')
@login_required
def messages(group_id):
    """Visualizza messaggi diretti del gruppo"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    group = filter_by_company(CircleGroup.query, current_user).filter_by(id=group_id).first_or_404()
    
    # Verifica membership
    if not group.is_member(current_user):
        abort(403)
    
    # Carica conversazioni (raggruppa per utente)
    sent_messages = CircleGroupMessage.query.filter_by(
        group_id=group_id,
        sender_id=current_user.id
    ).all()
    
    received_messages = CircleGroupMessage.query.filter_by(
        group_id=group_id,
        recipient_id=current_user.id
    ).all()
    
    # Crea lista utenti con cui hai conversazioni
    conversation_users = set()
    for msg in sent_messages:
        conversation_users.add(msg.recipient_id)
    for msg in received_messages:
        conversation_users.add(msg.sender_id)
    
    # Carica info utenti
    users = User.query.filter(User.id.in_(conversation_users)).all() if conversation_users else []
    
    return render_template('circle/groups/messages.html', 
                         group=group, 
                         users=users,
                         current_user=current_user)

@bp.route('/<int:group_id>/messages/<int:user_id>')
@login_required
def conversation(group_id, user_id):
    """Visualizza conversazione con un membro specifico"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    group = filter_by_company(CircleGroup.query, current_user).filter_by(id=group_id).first_or_404()
    other_user = User.query.get_or_404(user_id)
    
    # Verifica membership di entrambi
    if not group.is_member(current_user) or not group.is_member(other_user):
        abort(403)
    
    # Carica messaggi tra i due utenti
    messages = CircleGroupMessage.query.filter(
        CircleGroupMessage.group_id == group_id,
        or_(
            and_(CircleGroupMessage.sender_id == current_user.id, CircleGroupMessage.recipient_id == user_id),
            and_(CircleGroupMessage.sender_id == user_id, CircleGroupMessage.recipient_id == current_user.id)
        )
    ).order_by(CircleGroupMessage.created_at.asc()).all()
    
    # Segna come letti i messaggi ricevuti
    for msg in messages:
        if msg.recipient_id == current_user.id and not msg.is_read:
            msg.is_read = True
    db.session.commit()
    
    return render_template('circle/groups/conversation.html', 
                         group=group, 
                         other_user=other_user,
                         messages=messages)

@bp.route('/<int:group_id>/messages/<int:user_id>/send', methods=['POST'])
@login_required
def send_message(group_id, user_id):
    """Invia messaggio diretto a un membro"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    group = filter_by_company(CircleGroup.query, current_user).filter_by(id=group_id).first_or_404()
    other_user = User.query.get_or_404(user_id)
    
    # Verifica membership
    if not group.is_member(current_user) or not group.is_member(other_user):
        abort(403)
    
    content = request.form.get('content')
    if not content:
        flash('Il messaggio non può essere vuoto', 'danger')
        return redirect(url_for('circle_groups.conversation', group_id=group_id, user_id=user_id))
    
    # Sanitizza HTML per prevenire XSS
    content = sanitize_html(content)
    
    # Crea messaggio
    new_message = CircleGroupMessage(
        group_id=group_id,
        sender_id=current_user.id,
        recipient_id=user_id,
        content=content
    )
    
    db.session.add(new_message)
    db.session.commit()
    
    return redirect(url_for('circle_groups.conversation', group_id=group_id, user_id=user_id))
