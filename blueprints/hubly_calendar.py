from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from app import db
from models import HublyCalendarEvent
from utils_tenant import filter_by_company, get_user_company_id, set_company_on_create
from datetime import datetime, timedelta
from sqlalchemy import desc

bp = Blueprint('hubly_calendar', __name__, url_prefix='/hubly/calendar')

@bp.route('/')
@login_required
def index():
    """Calendario aziendale"""
    if not current_user.has_permission('can_view_calendar'):
        abort(403)
    
    return render_template('hubly/calendar/index.html')

@bp.route('/events')
@login_required
def get_events():
    """API JSON per eventi calendario"""
    if not current_user.has_permission('can_view_calendar'):
        abort(403)
    
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    
    query = filter_by_company(HublyCalendarEvent.query, current_user)
    
    if start_date and end_date:
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        query = query.filter(
            HublyCalendarEvent.start_datetime >= start,
            HublyCalendarEvent.end_datetime <= end
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
        
        new_event = HublyCalendarEvent(
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
        set_company_on_create(new_event, current_user)
        
        db.session.add(new_event)
        db.session.commit()
        
        flash('Evento creato con successo!', 'success')
        return redirect(url_for('hubly_calendar.index'))
    
    return render_template('hubly/calendar/create.html')

@bp.route('/<int:event_id>/delete', methods=['POST'])
@login_required
def delete(event_id):
    """Elimina evento"""
    if not current_user.has_permission('can_manage_calendar'):
        abort(403)
    
    event = filter_by_company(HublyCalendarEvent.query, current_user).get_or_404(event_id)
    
    # Solo il creatore o admin possono eliminare
    if event.creator_id != current_user.id and not current_user.has_permission('can_manage_calendar'):
        abort(403)
    
    db.session.delete(event)
    db.session.commit()
    
    flash('Evento eliminato', 'success')
    return redirect(url_for('hubly_calendar.index'))
