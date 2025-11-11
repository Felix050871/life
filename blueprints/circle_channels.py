from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from models import Channel
from utils_tenant import filter_by_company, set_company_on_create
from utils_security import sanitize_html
from sqlalchemy import desc

bp = Blueprint('circle_channels', __name__, url_prefix='/circle/channels')

@bp.route('/')
@login_required
def index():
    """Lista di tutti i canali"""
    if not current_user.has_permission('can_view_channels'):
        abort(403)
    
    # Canali attivi
    channels = filter_by_company(
        Channel.query,
        current_user
    ).filter_by(active=True).order_by(Channel.name).all()
    
    # Canali inattivi (se admin)
    inactive_channels = []
    if current_user.has_permission('can_manage_channels'):
        inactive_channels = filter_by_company(
            Channel.query,
            current_user
        ).filter_by(active=False).order_by(Channel.name).all()
    
    return render_template('circle/channels/index.html', 
                         channels=channels,
                         inactive_channels=inactive_channels)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Crea nuovo canale"""
    if not current_user.has_permission('can_manage_channels'):
        abort(403)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        icon_class = request.form.get('icon_class', 'fas fa-comments')
        icon_color = request.form.get('icon_color', 'text-primary')
        
        # Sanitizza HTML per prevenire XSS
        if description:
            description = sanitize_html(description)
        
        if not name:
            flash('Il nome del canale è obbligatorio', 'danger')
            return redirect(url_for('circle_channels.create'))
        
        # Verifica unicità del nome per company
        existing = filter_by_company(Channel.query, current_user).filter_by(name=name).first()
        if existing:
            flash('Esiste già un canale con questo nome', 'danger')
            return redirect(url_for('circle_channels.create'))
        
        # Crea canale
        channel = Channel(
            name=name,
            description=description,
            icon_class=icon_class,
            icon_color=icon_color,
            active=True
        )
        set_company_on_create(channel)
        
        db.session.add(channel)
        db.session.commit()
        
        flash(f'Canale "{name}" creato con successo!', 'success')
        return redirect(url_for('circle_channels.index'))
    
    return render_template('circle/channels/create.html')

@bp.route('/<int:channel_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(channel_id):
    """Modifica canale"""
    if not current_user.has_permission('can_manage_channels'):
        abort(403)
    
    channel = filter_by_company(Channel.query, current_user).filter_by(id=channel_id).first_or_404()
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        icon_class = request.form.get('icon_class', 'fas fa-comments')
        icon_color = request.form.get('icon_color', 'text-primary')
        active = request.form.get('active') == 'on'
        
        # Sanitizza HTML per prevenire XSS
        if description:
            description = sanitize_html(description)
        
        if not name:
            flash('Il nome del canale è obbligatorio', 'danger')
            return redirect(url_for('circle_channels.edit', channel_id=channel_id))
        
        # Verifica unicità del nome per company (escludi se stesso)
        existing = filter_by_company(Channel.query, current_user).filter(
            Channel.name == name,
            Channel.id != channel_id
        ).first()
        if existing:
            flash('Esiste già un canale con questo nome', 'danger')
            return redirect(url_for('circle_channels.edit', channel_id=channel_id))
        
        # Aggiorna canale
        channel.name = name
        channel.description = description
        channel.icon_class = icon_class
        channel.icon_color = icon_color
        channel.active = active
        
        db.session.commit()
        
        flash(f'Canale "{name}" aggiornato con successo!', 'success')
        return redirect(url_for('circle_channels.index'))
    
    return render_template('circle/channels/edit.html', channel=channel)

@bp.route('/<int:channel_id>/delete', methods=['POST'])
@login_required
def delete(channel_id):
    """Elimina canale (soft delete - disattiva)"""
    if not current_user.has_permission('can_manage_channels'):
        abort(403)
    
    channel = filter_by_company(Channel.query, current_user).filter_by(id=channel_id).first_or_404()
    
    # Non permettere eliminazione del canale "Generale"
    if channel.name == 'Generale':
        flash('Non è possibile eliminare il canale "Generale"', 'danger')
        return redirect(url_for('circle_channels.index'))
    
    # Soft delete - disattiva il canale
    channel.active = False
    db.session.commit()
    
    flash(f'Canale "{channel.name}" disattivato con successo', 'success')
    return redirect(url_for('circle_channels.index'))

@bp.route('/<int:channel_id>/activate', methods=['POST'])
@login_required
def activate(channel_id):
    """Riattiva canale"""
    if not current_user.has_permission('can_manage_channels'):
        abort(403)
    
    channel = filter_by_company(Channel.query, current_user).filter_by(id=channel_id).first_or_404()
    
    channel.active = True
    db.session.commit()
    
    flash(f'Canale "{channel.name}" riattivato con successo', 'success')
    return redirect(url_for('circle_channels.index'))
