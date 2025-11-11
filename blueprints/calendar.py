from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from models import db, LeaveRequest, Shift, User, WorkSchedule, Sede
from datetime import datetime, timedelta
from sqlalchemy import and_, or_

calendar_bp = Blueprint('calendar', __name__, url_prefix='/calendar')

@calendar_bp.route('/')
@login_required
def calendar_view():
    """Vista principale del calendario interattivo"""
    if not current_user.company_id:
        return "Accesso negato", 403
    
    sedi = []
    if current_user.can_view_leave() or current_user.can_manage_leave():
        sedi = Sede.query.filter_by(company_id=current_user.company_id).order_by(Sede.name).all()
    
    can_view_all = current_user.can_view_leave() or current_user.can_manage_leave()
    
    return render_template('calendar.html',
                         sedi=sedi,
                         can_view_all=can_view_all)


@calendar_bp.route('/api/events')
@login_required
def get_calendar_events():
    """API endpoint che restituisce eventi in formato FullCalendar"""
    if not current_user.company_id:
        return jsonify([])
    
    start = request.args.get('start')
    end = request.args.get('end')
    view_mode = request.args.get('view_mode', 'my')
    sede_filter = request.args.get('sede_id', '')
    event_types = request.args.getlist('event_types[]')
    
    if not event_types:
        event_types = ['leaves', 'shifts']
    
    events = []
    
    start_date = datetime.fromisoformat(start.replace('Z', '+00:00')).date() if start else None
    end_date = datetime.fromisoformat(end.replace('Z', '+00:00')).date() if end else None
    
    can_view_all = current_user.can_view_leave() or current_user.can_manage_leave()
    
    if 'leaves' in event_types:
        leave_query = LeaveRequest.query.filter_by(company_id=current_user.company_id)
        
        if view_mode == 'my':
            leave_query = leave_query.filter_by(user_id=current_user.id)
        elif view_mode == 'all' and can_view_all:
            if sede_filter:
                sede_users = User.query.filter_by(company_id=current_user.company_id, sede_id=int(sede_filter)).all()
                sede_user_ids = [u.id for u in sede_users]
                leave_query = leave_query.filter(LeaveRequest.user_id.in_(sede_user_ids))
        else:
            leave_query = leave_query.filter_by(user_id=current_user.id)
        
        if start_date and end_date:
            leave_query = leave_query.filter(
                or_(
                    and_(LeaveRequest.start_date >= start_date, LeaveRequest.start_date <= end_date),
                    and_(LeaveRequest.end_date >= start_date, LeaveRequest.end_date <= end_date),
                    and_(LeaveRequest.start_date <= start_date, LeaveRequest.end_date >= end_date)
                )
            )
        
        leaves = leave_query.all()
        
        for leave in leaves:
            user = User.query.get(leave.user_id)
            if not user:
                continue
            
            color = '#28a745'
            if leave.status == 'pending':
                color = '#ffc107'
            elif leave.status == 'rejected':
                color = '#dc3545'
            elif leave.status == 'cancelled':
                color = '#6c757d'
            
            title = f"{user.get_full_name()}"
            if leave.leave_type:
                title += f" - {leave.leave_type.name}"
            
            if leave.status == 'pending':
                title = f"⏳ {title}"
            elif leave.status == 'approved':
                title = f"✓ {title}"
            
            events.append({
                'id': f"leave-{leave.id}",
                'title': title,
                'start': leave.start_date.isoformat(),
                'end': (leave.end_date + timedelta(days=1)).isoformat(),
                'backgroundColor': color,
                'borderColor': color,
                'extendedProps': {
                    'type': 'leave',
                    'status': leave.status,
                    'user': user.get_full_name(),
                    'leave_type': leave.leave_type.name if leave.leave_type else '',
                    'reason': leave.reason or '',
                    'duration_type': leave.duration_type or 'full_day',
                    'leave_id': leave.id
                }
            })
    
    if 'shifts' in event_types:
        shift_query = Shift.query.filter_by(company_id=current_user.company_id)
        
        if view_mode == 'my':
            shift_query = shift_query.filter_by(user_id=current_user.id)
        elif view_mode == 'all' and can_view_all:
            if sede_filter:
                sede_users = User.query.filter_by(company_id=current_user.company_id, sede_id=int(sede_filter)).all()
                sede_user_ids = [u.id for u in sede_users]
                shift_query = shift_query.filter(Shift.user_id.in_(sede_user_ids))
        else:
            shift_query = shift_query.filter_by(user_id=current_user.id)
        
        if start_date and end_date:
            shift_query = shift_query.filter(
                and_(Shift.date >= start_date, Shift.date <= end_date)
            )
        
        shifts = shift_query.all()
        
        for shift in shifts:
            user = User.query.get(shift.user_id)
            if not user:
                continue
            
            start_datetime = datetime.combine(shift.date, shift.start_time) if shift.start_time else datetime.combine(shift.date, datetime.min.time())
            end_datetime = datetime.combine(shift.date, shift.end_time) if shift.end_time else datetime.combine(shift.date, datetime.max.time())
            
            title = f"🔵 {user.get_full_name()}"
            if shift.shift_type:
                title += f" - {shift.shift_type}"
            
            events.append({
                'id': f"shift-{shift.id}",
                'title': title,
                'start': start_datetime.isoformat(),
                'end': end_datetime.isoformat(),
                'backgroundColor': '#007bff',
                'borderColor': '#007bff',
                'extendedProps': {
                    'type': 'shift',
                    'user': user.get_full_name(),
                    'shift_type': shift.shift_type or '',
                    'shift_id': shift.id
                }
            })
    
    return jsonify(events)
