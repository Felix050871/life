from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from models import HublyGroup, User, hubly_group_members
from utils_tenant import filter_by_company, get_user_company_id, set_company_on_create
from sqlalchemy import desc

bp = Blueprint('hubly_groups', __name__, url_prefix='/hubly/groups')

@bp.route('/')
@login_required
def index():
    """Lista di tutti i gruppi"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    # Gruppi pubblici
    public_groups = filter_by_company(
        HublyGroup.query.filter_by(is_private=False),
        current_user
    ).order_by(desc(HublyGroup.created_at)).all()
    
    # Gruppi di cui l'utente è membro (anche privati)
    user_groups_query = db.session.query(HublyGroup).join(
        hubly_group_members,
        HublyGroup.id == hubly_group_members.c.group_id
    ).filter(hubly_group_members.c.user_id == current_user.id)
    
    my_groups = filter_by_company(user_groups_query, current_user).all()
    
    return render_template('hubly/groups/index.html', 
                         public_groups=public_groups,
                         my_groups=my_groups)

@bp.route('/<int:group_id>')
@login_required
def view_group(group_id):
    """Visualizza dettaglio gruppo"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    group = filter_by_company(HublyGroup.query, current_user).get_or_404(group_id)
    
    # Verifica accesso gruppo privato
    if group.is_private:
        is_member = db.session.query(hubly_group_members).filter_by(
            user_id=current_user.id,
            group_id=group_id
        ).first() is not None
        
        if not is_member:
            abort(403)
    
    # Carica membri del gruppo
    members_query = db.session.query(User, hubly_group_members.c.is_admin).join(
        hubly_group_members,
        User.id == hubly_group_members.c.user_id
    ).filter(hubly_group_members.c.group_id == group_id)
    
    members = members_query.all()
    
    return render_template('hubly/groups/view.html', group=group, members=members)

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
        
        new_group = HublyGroup(
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
        stmt = hubly_group_members.insert().values(
            user_id=current_user.id,
            group_id=new_group.id,
            is_admin=True
        )
        db.session.execute(stmt)
        db.session.commit()
        
        flash('Gruppo creato con successo!', 'success')
        return redirect(url_for('hubly_groups.view_group', group_id=new_group.id))
    
    return render_template('hubly/groups/create.html')

@bp.route('/<int:group_id>/join', methods=['POST'])
@login_required
def join_group(group_id):
    """Unisciti a un gruppo"""
    if not current_user.has_permission('can_join_groups'):
        abort(403)
    
    group = filter_by_company(HublyGroup.query, current_user).get_or_404(group_id)
    
    # Non puoi unirti a gruppi privati direttamente
    if group.is_private:
        flash('Questo gruppo è privato, serve un invito', 'warning')
        return redirect(url_for('hubly_groups.index'))
    
    # Verifica se già membro
    existing = db.session.query(hubly_group_members).filter_by(
        user_id=current_user.id,
        group_id=group_id
    ).first()
    
    if existing:
        flash('Sei già membro di questo gruppo', 'info')
    else:
        stmt = hubly_group_members.insert().values(
            user_id=current_user.id,
            group_id=group_id,
            is_admin=False
        )
        db.session.execute(stmt)
        db.session.commit()
        flash('Ti sei unito al gruppo!', 'success')
    
    return redirect(url_for('hubly_groups.view_group', group_id=group_id))

@bp.route('/<int:group_id>/leave', methods=['POST'])
@login_required
def leave_group(group_id):
    """Abbandona un gruppo"""
    if not current_user.has_permission('can_access_hubly'):
        abort(403)
    
    group = filter_by_company(HublyGroup.query, current_user).get_or_404(group_id)
    
    # Non puoi lasciare il gruppo se sei il creatore
    if group.creator_id == current_user.id:
        flash('Il creatore non può abbandonare il gruppo', 'danger')
        return redirect(url_for('hubly_groups.view_group', group_id=group_id))
    
    stmt = hubly_group_members.delete().where(
        (hubly_group_members.c.user_id == current_user.id) &
        (hubly_group_members.c.group_id == group_id)
    )
    db.session.execute(stmt)
    db.session.commit()
    
    flash('Hai lasciato il gruppo', 'info')
    return redirect(url_for('hubly_groups.index'))

@bp.route('/<int:group_id>/delete', methods=['POST'])
@login_required
def delete(group_id):
    """Elimina gruppo"""
    if not current_user.has_permission('can_manage_groups'):
        abort(403)
    
    group = filter_by_company(HublyGroup.query, current_user).get_or_404(group_id)
    
    # Solo il creatore o admin possono eliminare
    if group.creator_id != current_user.id and not current_user.has_permission('can_manage_groups'):
        abort(403)
    
    # Elimina membri
    stmt = hubly_group_members.delete().where(hubly_group_members.c.group_id == group_id)
    db.session.execute(stmt)
    
    db.session.delete(group)
    db.session.commit()
    
    flash('Gruppo eliminato', 'success')
    return redirect(url_for('hubly_groups.index'))
