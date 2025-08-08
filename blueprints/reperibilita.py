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
        ReperibilitaShift.date >= start_date,
        ReperibilitaShift.date <= end_date
    )
    
    # Filtro sede se non multi-sede
    if not current_user.all_sedi and current_user.sede_obj:
        sede_users = User.query.filter_by(sede_id=current_user.sede_obj.id).all()
        user_ids = [u.id for u in sede_users]
        query = query.filter(ReperibilitaShift.user_id.in_(user_ids))
    
    shifts = query.order_by(
        ReperibilitaShift.date,
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
                db.extract('year', ReperibilitaShift.date) == int(year),
                db.extract('month', ReperibilitaShift.date) == int(month)
            )
        except ValueError:
            pass
    else:
        # Mese corrente di default
        now = italian_now()
        query = query.filter(
            db.extract('year', ReperibilitaShift.date) == now.year,
            db.extract('month', ReperibilitaShift.date) == now.month
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
        ReperibilitaShift.date.desc(),
        ReperibilitaShift.start_time
    ).all()
    
    # Lista utenti per filtro
    available_users = User.query.filter_by(active=True).order_by(User.last_name, User.first_name).all()
    if not current_user.all_sedi and current_user.sede_obj:
        available_users = [u for u in available_users if u.sede_id == current_user.sede_obj.id]
    
    # Parametri per navigation 
    period_mode = request.args.get('period', 'month')
    view_mode = request.args.get('view', 'calendar')
    display_mode = request.args.get('display', 'calendar')
    
    # Crea oggetto navigation per il template
    from datetime import datetime, timedelta
    try:
        from utils import italian_now
        now = italian_now()
    except ImportError:
        now = datetime.now()
        
    # Calcola navigation date
    if month_filter:
        try:
            year, month = month_filter.split('-')
            current_month = datetime(int(year), int(month), 1)
        except ValueError:
            current_month = datetime(now.year, now.month, 1)
    else:
        current_month = datetime(now.year, now.month, 1)
    
    # Previous/Next month
    prev_month = current_month.replace(day=1) - timedelta(days=1)
    prev_month = prev_month.replace(day=1)
    
    if current_month.month == 12:
        next_month = current_month.replace(year=current_month.year + 1, month=1)
    else:
        next_month = current_month.replace(month=current_month.month + 1)
    
    # Crea oggetto navigation
    navigation = {
        'prev_date': prev_month,
        'next_date': next_month,
        'current_period': current_month.strftime('%B %Y')
    }

    return render_template('reperibilita_shifts.html',
                         shifts=shifts,
                         available_users=available_users,
                         selected_month=month_filter,
                         selected_user=user_filter,
                         navigation=navigation,
                         period_mode=period_mode,
                         view_mode=view_mode,
                         display_mode=display_mode,
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
                db.extract('year', ReperibilitaShift.date) == int(year),
                db.extract('month', ReperibilitaShift.date) == int(month)
            )
        except ValueError:
            pass
    
    # Ordinamento
    shifts = query.order_by(ReperibilitaShift.date.desc()).all()
    
    # Statistiche personali
    stats = {
        'total_shifts': len(shifts),
        'upcoming_shifts': len([s for s in shifts if s.date >= italian_now().date()]),
        'past_shifts': len([s for s in shifts if s.date < italian_now().date()]),
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
            ReperibilitaShift.date >= start_date,
            ReperibilitaShift.date <= end_date
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
                'date': shift.date.isoformat(),
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

# =============================================================================
# INTERVENTION MANAGEMENT ROUTES
# =============================================================================

@reperibilita_bp.route('/start-intervention', methods=['POST'])
@login_required
@require_reperibilita_permissions
def start_intervention():
    """Inizia un intervento di reperibilità"""
    if current_user.role not in ['Management', 'Operatore', 'Redattore', 'Sviluppatore']:
        flash('Non hai i permessi per registrare interventi di reperibilità.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    # Controlla se c'è già un intervento attivo
    from models import ReperibilitaIntervention
    active_intervention = ReperibilitaIntervention.query.filter_by(
        user_id=current_user.id,
        end_datetime=None
    ).first()
    
    if active_intervention:
        flash('Hai già un intervento di reperibilità in corso.', 'warning')
        return redirect(url_for('dashboard.dashboard'))
    
    # Ottieni shift_id dal form se presente
    shift_id = request.form.get('shift_id')
    if shift_id:
        shift_id = int(shift_id)
    
    # Ottieni is_remote dal form (default True = remoto)
    is_remote = request.form.get('is_remote', 'true').lower() == 'true'
    
    # Ottieni priorità dal form (default Media)
    priority = request.form.get('priority', 'Media')
    if priority not in ['Bassa', 'Media', 'Alta']:
        priority = 'Media'
    
    # Crea nuovo intervento
    try:
        from utils import italian_now
        intervention = ReperibilitaIntervention(
            user_id=current_user.id,
            shift_id=shift_id,
            start_datetime=italian_now(),
            description=request.form.get('description', ''),
            priority=priority,
            is_remote=is_remote
        )
    except ImportError:
        intervention = ReperibilitaIntervention(
            user_id=current_user.id,
            shift_id=shift_id,
            start_datetime=datetime.now(),
            description=request.form.get('description', ''),
            priority=priority,
            is_remote=is_remote
        )
    
    db.session.add(intervention)
    db.session.commit()
    
    flash('Intervento di reperibilità iniziato con successo.', 'success')
    return redirect(url_for('reperibilita.reperibilita_shifts'))

@reperibilita_bp.route('/end-intervention', methods=['POST'])
@login_required
@require_reperibilita_permissions
def end_intervention():
    """Termina un intervento di reperibilità"""
    if current_user.role not in ['Management', 'Operatore', 'Redattore', 'Sviluppatore']:
        flash('Non hai i permessi per registrare interventi di reperibilità.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    # Trova l'intervento attivo
    from models import ReperibilitaIntervention
    active_intervention = ReperibilitaIntervention.query.filter_by(
        user_id=current_user.id,
        end_datetime=None
    ).first()
    
    if not active_intervention:
        flash('Nessun intervento di reperibilità attivo da terminare.', 'warning')
        return redirect(url_for('dashboard.dashboard'))
    
    # Termina l'intervento
    try:
        from utils import italian_now
        active_intervention.end_datetime = italian_now()
    except ImportError:
        active_intervention.end_datetime = datetime.now()
    
    active_intervention.description = request.form.get('description', active_intervention.description)
    
    db.session.commit()
    
    flash('Intervento di reperibilità terminato con successo.', 'success')
    
    # Redirect to appropriate page
    if current_user.role == 'Management':
        return redirect(url_for('dashboard.ente_home'))
    else:
        return redirect(url_for('reperibilita.reperibilita_shifts'))