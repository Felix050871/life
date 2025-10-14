from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from app import db
from models import CircleCalendarEvent
from utils_tenant import filter_by_company, get_user_company_id, set_company_on_create
from datetime import datetime, timedelta
from sqlalchemy import desc

bp = Blueprint('circle_calendar', __name__, url_prefix='/circle/calendar')

@bp.route('/')
@login_required
def index():
    """Calendario aziendale"""
    if not current_user.has_permission('can_view_calendar'):
        abort(403)
    
    return render_template('circle/calendar/index.html')

@bp.route('/events')
@login_required
def get_events():
    """API JSON per eventi calendario"""
    if not current_user.has_permission('can_view_calendar'):
        abort(403)
    
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    
    query = filter_by_company(CircleCalendarEvent.query, current_user)
    
    if start_date and end_date:
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        # Usa overlap logic: eventi che si sovrappongono alla finestra
        # (start < window_end AND end > window_start)
        query = query.filter(
            CircleCalendarEvent.start_datetime < end,
            CircleCalendarEvent.end_datetime > start
        )
    
    events = query.all()
    
    events_json = [{
        'id': event.id,
        'title': event.title,
        'start': event.start_datetime.isoformat(),
        'end': event.end_datetime.isoformat(),
        'color': event.color,
        'allDay': event.is_all_day,
        'extendedProps': {
            'description': event.description,
            'location': event.location,
            'type': event.event_type
        }
    } for event in events]
    
    return jsonify(events_json)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Crea nuovo evento"""
    if not current_user.has_permission('can_create_events'):
        abort(403)
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        event_type = request.form.get('event_type', 'event')
        start_datetime = datetime.fromisoformat(request.form.get('start_datetime'))
        end_datetime = datetime.fromisoformat(request.form.get('end_datetime'))
        location = request.form.get('location')
        is_all_day = request.form.get('is_all_day') == 'on'
        color = request.form.get('color', '#0d6efd')
        
        # Validazione: end_datetime deve essere dopo start_datetime
        if end_datetime <= start_datetime:
            flash('La data di fine deve essere successiva alla data di inizio', 'danger')
            return redirect(url_for('hubly_calendar.create'))
        
        new_event = CircleCalendarEvent(
            title=title,
            description=description,
            event_type=event_type,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            location=location,
            creator_id=current_user.id,
            is_all_day=is_all_day,
            color=color
        )
        set_company_on_create(new_event)
        
        db.session.add(new_event)
        db.session.commit()
        
        flash('Evento creato con successo!', 'success')
        return redirect(url_for('hubly_calendar.index'))
    
    return render_template('circle/calendar/create.html')

@bp.route('/<int:event_id>')
@login_required
def view(event_id):
    """Visualizza dettaglio evento"""
    if not current_user.has_permission('can_view_calendar'):
        abort(403)
    
    event = filter_by_company(CircleCalendarEvent.query, current_user).filter_by(id=event_id).first_or_404()
    
    return render_template('circle/calendar/view.html', event=event)

@bp.route('/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(event_id):
    """Modifica evento"""
    event = filter_by_company(CircleCalendarEvent.query, current_user).filter_by(id=event_id).first_or_404()
    
    # Solo il creatore o utenti con permesso can_manage_calendar possono modificare
    if event.creator_id != current_user.id and not current_user.has_permission('can_manage_calendar'):
        abort(403)
    
    if request.method == 'POST':
        event.title = request.form.get('title')
        event.description = request.form.get('description')
        event.event_type = request.form.get('event_type', 'event')
        start_datetime = datetime.fromisoformat(request.form.get('start_datetime'))
        end_datetime = datetime.fromisoformat(request.form.get('end_datetime'))
        
        # Validazione: end_datetime deve essere dopo start_datetime
        if end_datetime <= start_datetime:
            flash('La data di fine deve essere successiva alla data di inizio', 'danger')
            return redirect(url_for('hubly_calendar.edit', event_id=event.id))
        
        event.start_datetime = start_datetime
        event.end_datetime = end_datetime
        event.location = request.form.get('location')
        event.is_all_day = request.form.get('is_all_day') == 'on'
        event.color = request.form.get('color', '#0d6efd')
        
        db.session.commit()
        
        flash('Evento aggiornato con successo!', 'success')
        return redirect(url_for('hubly_calendar.view', event_id=event.id))
    
    return render_template('circle/calendar/edit.html', event=event)

@bp.route('/<int:event_id>/delete', methods=['POST'])
@login_required
def delete(event_id):
    """Elimina evento"""
    event = filter_by_company(CircleCalendarEvent.query, current_user).filter_by(id=event_id).first_or_404()
    
    # Solo il creatore o utenti con permesso can_manage_calendar possono eliminare
    if event.creator_id != current_user.id and not current_user.has_permission('can_manage_calendar'):
        abort(403)
    
    db.session.delete(event)
    db.session.commit()
    
    flash('Evento eliminato con successo!', 'success')
    return redirect(url_for('hubly_calendar.index'))
