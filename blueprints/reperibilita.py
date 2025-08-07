# =============================================================================
# REPERIBILITÀ BLUEPRINT - Modulo gestione turni reperibilità
# =============================================================================
#
# ROUTES INCLUSE:
# 1. reperibilita_coverage (GET) - Visualizzazione coperture reperibilità
# 2. reperibilita_shifts (GET) - Gestione turni reperibilità
# 3. api/get_reperibilita_data (GET) - API dati reperibilità
# 4. generate_reperibilita (POST) - Generazione automatica turni
# 5. my_reperibilita (GET) - Le mie reperibilità
#
# Total routes: 5+ reperibilità management routes
# =============================================================================

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from functools import wraps
from app import db
from models import User, Sede, ReperibilitaShift, italian_now

# Create blueprint
reperibilita_bp = Blueprint('reperibilita', __name__, url_prefix='/reperibilita')

# Helper functions
def require_reperibilita_permissions(f):
    """Decorator to require reperibilità permissions for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.can_access_reperibilita_menu():
            flash('Non hai i permessi per accedere alla reperibilità', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# REPERIBILITÀ MANAGEMENT ROUTES
# =============================================================================

@reperibilita_bp.route('/reperibilita_coverage')
@login_required
@require_reperibilita_permissions
def reperibilita_coverage():
    """Visualizzazione coperture reperibilità"""
    if not (current_user.can_manage_reperibilita() or current_user.can_view_reperibilita()):
        flash('Non hai i permessi per visualizzare le coperture', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    # Parametri dalla query string
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Date di default (settimana corrente)
    today = italian_now().date()
    if not start_date_str:
        # Lunedì della settimana corrente
        start_date = today - timedelta(days=today.weekday())
    else:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    
    if not end_date_str:
        end_date = start_date + timedelta(days=6)  # Domenica
    else:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    # Query per recuperare shifts reperibilità nel periodo
    query = ReperibilitaShift.query.filter(
        ReperibilitaShift.shift_date >= start_date,
        ReperibilitaShift.shift_date <= end_date
    )
    
    # Filtro sede se non multi-sede
    if not current_user.all_sedi and current_user.sede_obj:
        sede_users = User.query.filter_by(sede_id=current_user.sede_obj.id).all()
        user_ids = [u.id for u in sede_users]
        query = query.filter(ReperibilitaShift.user_id.in_(user_ids))
    
    shifts = query.order_by(
        ReperibilitaShift.shift_date,
        ReperibilitaShift.start_time
    ).all()
    
    return render_template('reperibilita_coverage.html',
                         shifts=shifts,
                         start_date=start_date,
                         end_date=end_date,
                         can_manage=current_user.can_manage_reperibilita())

@reperibilita_bp.route('/reperibilita_shifts')
@login_required
@require_reperibilita_permissions
def reperibilita_shifts():
    """Gestione turni reperibilità"""
    if not (current_user.can_manage_reperibilita() or current_user.can_view_reperibilita()):
        flash('Non hai i permessi per gestire i turni reperibilità', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    # Filtri dalla query string
    month_filter = request.args.get('month')
    user_filter = request.args.get('user', 'all')
    
    # Query base
    query = ReperibilitaShift.query
    
    # Filtro mese
    if month_filter:
        try:
            year, month = month_filter.split('-')
            query = query.filter(
                db.extract('year', ReperibilitaShift.shift_date) == int(year),
                db.extract('month', ReperibilitaShift.shift_date) == int(month)
            )
        except ValueError:
            pass
    else:
        # Mese corrente di default
        now = italian_now()
        query = query.filter(
            db.extract('year', ReperibilitaShift.shift_date) == now.year,
            db.extract('month', ReperibilitaShift.shift_date) == now.month
        )
    
    # Filtro utente
    if user_filter != 'all':
        try:
            user_id = int(user_filter)
            query = query.filter(ReperibilitaShift.user_id == user_id)
        except ValueError:
            pass
    
    # Controllo sede
    if not current_user.all_sedi and current_user.sede_obj:
        sede_users = User.query.filter_by(sede_id=current_user.sede_obj.id).all()
        user_ids = [u.id for u in sede_users]
        query = query.filter(ReperibilitaShift.user_id.in_(user_ids))
    
    # Esecuzione query
    shifts = query.join(User, ReperibilitaShift.user_id == User.id).order_by(
        ReperibilitaShift.shift_date.desc(),
        ReperibilitaShift.start_time
    ).all()
    
    # Lista utenti per filtro
    available_users = User.query.filter_by(active=True).order_by(User.last_name, User.first_name).all()
    if not current_user.all_sedi and current_user.sede_obj:
        available_users = [u for u in available_users if u.sede_id == current_user.sede_obj.id]
    
    return render_template('reperibilita_shifts.html',
                         shifts=shifts,
                         available_users=available_users,
                         selected_month=month_filter,
                         selected_user=user_filter,
                         can_manage=current_user.can_manage_reperibilita())

@reperibilita_bp.route('/my_reperibilita')
@login_required
@require_reperibilita_permissions
def my_reperibilita():
    """Le mie reperibilità"""
    if not current_user.can_view_my_reperibilita():
        flash('Non hai i permessi per visualizzare le tue reperibilità', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    # Filtri dalla query string
    month_filter = request.args.get('month')
    status_filter = request.args.get('status', 'all')
    
    # Base query - solo le proprie reperibilità
    query = ReperibilitaShift.query.filter_by(user_id=current_user.id)
    
    # Filtro mese
    if month_filter:
        try:
            year, month = month_filter.split('-')
            query = query.filter(
                db.extract('year', ReperibilitaShift.shift_date) == int(year),
                db.extract('month', ReperibilitaShift.shift_date) == int(month)
            )
        except ValueError:
            pass
    
    # Ordinamento
    shifts = query.order_by(ReperibilitaShift.shift_date.desc()).all()
    
    # Statistiche personali
    stats = {
        'total_shifts': len(shifts),
        'upcoming_shifts': len([s for s in shifts if s.shift_date >= italian_now().date()]),
        'past_shifts': len([s for s in shifts if s.shift_date < italian_now().date()]),
    }
    
    return render_template('my_reperibilita.html',
                         shifts=shifts,
                         stats=stats,
                         selected_month=month_filter,
                         selected_status=status_filter)

@reperibilita_bp.route('/generate_shifts', methods=['GET', 'POST'])
@login_required
@require_reperibilita_permissions
def generate_shifts():
    """Generazione turni reperibilità (placeholder)"""
    if not current_user.can_manage_reperibilita():
        flash('Non hai i permessi per generare turni', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    flash('Funzione generazione automatica turni in sviluppo', 'info')
    return redirect(url_for('reperibilita.reperibilita_coverage'))

@reperibilita_bp.route('/api/get_reperibilita_data')
@login_required
def get_reperibilita_data():
    """API per ottenere dati reperibilità"""
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        if not start_date_str or not end_date_str:
            return jsonify({'error': 'Date mancanti'}), 400
        
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # Query shifts nel periodo
        query = ReperibilitaShift.query.filter(
            ReperibilitaShift.shift_date >= start_date,
            ReperibilitaShift.shift_date <= end_date
        )
        
        # Controllo sede
        if not current_user.all_sedi and current_user.sede_obj:
            sede_users = User.query.filter_by(sede_id=current_user.sede_obj.id).all()
            user_ids = [u.id for u in sede_users]
            query = query.filter(ReperibilitaShift.user_id.in_(user_ids))
        
        shifts = query.all()
        
        # Formatta dati per risposta JSON
        shifts_data = []
        for shift in shifts:
            shifts_data.append({
                'id': shift.id,
                'user_name': shift.user.get_full_name(),
                'shift_date': shift.shift_date.isoformat(),
                'start_time': shift.start_time.strftime('%H:%M'),
                'end_time': shift.end_time.strftime('%H:%M'),
                'type': getattr(shift, 'shift_type', 'Standard')
            })
        
        return jsonify({
            'success': True,
            'data': shifts_data,
            'period': f"{start_date.isoformat()} - {end_date.isoformat()}"
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500