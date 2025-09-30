# =============================================================================
# LEAVE BLUEPRINT - Modulo gestione ferie, permessi e malattie
# =============================================================================
#
# ROUTES INCLUSE:
# 1. leave_requests (GET/POST) - Gestione richieste ferie/permessi/malattie
# 2. create_leave_request (GET/POST) - Creazione nuova richiesta
# 3. approve_leave_request/<request_id> (POST) - Approvazione richiesta
# 4. reject_leave_request/<request_id> (POST) - Rifiuto richiesta
# 5. delete_leave_request/<request_id> (POST) - Eliminazione richiesta
# 6. api/leave_balance/<user_id>/<year> (GET) - API saldo ferie
# 7. export_leave_requests_excel (GET) - Export Excel richieste
#
# Total routes: 7+ leave management routes
# =============================================================================

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, make_response
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from functools import wraps
from app import db
from models import User, LeaveRequest, LeaveType, Sede, Holiday, italian_now
from forms import LeaveRequestForm
import io
import csv

# Form imported from forms.py

# Create blueprint
leave_bp = Blueprint('leave', __name__, url_prefix='/leave')

# Helper functions
def require_login(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# LEAVE MANAGEMENT ROUTES
# =============================================================================

@leave_bp.route('/leave_requests')
@login_required
def leave_requests():
    """Visualizza richieste ferie/permessi/malattie"""
    # Controllo permessi in base alla vista richiesta
    view = request.args.get('view', 'my')
    
    if view == 'approve' and not current_user.can_approve_leave():
        flash('Non hai i permessi per approvare richieste', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    elif view == 'view' and not current_user.can_view_leave():
        flash('Non hai i permessi per visualizzare tutte le richieste', 'danger') 
        return redirect(url_for('dashboard.dashboard'))
    elif view == 'my' and not (current_user.can_view_my_leave() or current_user.can_request_leave()):
        flash('Non hai i permessi per accedere alle richieste', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    # Base query
    query = LeaveRequest.query
    
    # Filtri per vista
    if view == 'my':
        # Solo le proprie richieste
        query = query.filter(LeaveRequest.user_id == current_user.id)
    elif view == 'approve':
        # Solo richieste in pending per approvazione
        query = query.filter(LeaveRequest.status == 'Pending')
        
        # Se non è multi-sede, filtra per sede
        if not current_user.all_sedi and current_user.sede_obj:
            sede_users = User.query.filter_by(sede_id=current_user.sede_obj.id).all()
            user_ids = [u.id for u in sede_users]
            query = query.filter(LeaveRequest.user_id.in_(user_ids))
    elif view == 'view':
        # Tutte le richieste con controllo sede
        if not current_user.all_sedi and current_user.sede_obj:
            sede_users = User.query.filter_by(sede_id=current_user.sede_obj.id).all()
            user_ids = [u.id for u in sede_users]
            query = query.filter(LeaveRequest.user_id.in_(user_ids))
    
    # Filtri aggiuntivi
    status_filter = request.args.get('status')
    if status_filter and status_filter != 'all':
        query = query.filter(LeaveRequest.status == status_filter)
    
    leave_type_filter = request.args.get('leave_type')  
    if leave_type_filter and leave_type_filter != 'all':
        query = query.filter(LeaveRequest.leave_type == leave_type_filter)
    
    year_filter = request.args.get('year')
    if year_filter:
        try:
            year = int(year_filter)
            query = query.filter(
                db.extract('year', LeaveRequest.start_date) == year
            )
        except ValueError:
            pass
    
    # Ordinamento
    requests = query.join(User, LeaveRequest.user_id == User.id).order_by(
        LeaveRequest.created_at.desc()
    ).all()
    
    # Statistiche per dashboard
    stats = {}
    if view in ['approve', 'view']:
        stats = {
            'pending_count': LeaveRequest.query.filter_by(status='Pending').count(),
            'approved_count': LeaveRequest.query.filter_by(status='Approved').count(),
            'rejected_count': LeaveRequest.query.filter_by(status='Rejected').count(),
        }
    
    # Lista anni disponibili per filtro
    years = db.session.query(
        db.extract('year', LeaveRequest.start_date).label('year')
    ).distinct().order_by('year').all()
    available_years = [y.year for y in years if y.year]
    
    return render_template('leave_requests.html',
                         requests=requests,
                         view=view,
                         stats=stats,
                         available_years=available_years,
                         selected_status=status_filter,
                         selected_type=leave_type_filter,
                         selected_year=year_filter,
                         can_approve=current_user.can_approve_leave(),
                         can_create=current_user.can_request_leave(),
                         today=date.today())

@leave_bp.route('/create_leave_request', methods=['GET', 'POST'])
@login_required
def create_leave_request():
    """Crea nuova richiesta ferie/permessi/malattie"""
    if not current_user.can_request_leave():
        flash('Non hai i permessi per creare richieste', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    form = LeaveRequestForm()
    
    if form.validate_on_submit():
        try:
            # Verifica che le date siano valide
            if not form.start_date.data:
                flash('Data di inizio richiesta', 'danger')
                return render_template('create_leave_request.html', form=form, today=date.today())
            
            # Per permessi orari, usa la stessa data per inizio e fine
            end_date = form.end_date.data if form.end_date.data else form.start_date.data
            
            # Verifica sovrapposizioni esistenti
            existing_requests = LeaveRequest.query.filter(
                LeaveRequest.user_id == current_user.id,
                LeaveRequest.status.in_(['Pending', 'Approved']),
                LeaveRequest.start_date <= end_date,
                LeaveRequest.end_date >= form.start_date.data
            ).first()
            
            if existing_requests:
                flash('Hai già una richiesta nel periodo selezionato', 'warning')
                return render_template('create_leave_request.html', form=form, today=date.today())
            
            # Crea nuova richiesta
            new_request = LeaveRequest()
            new_request.user_id = current_user.id
            new_request.leave_type_id = form.leave_type_id.data
            new_request.start_date = form.start_date.data
            new_request.end_date = end_date
            new_request.reason = form.reason.data
            new_request.status = 'Pending'
            new_request.created_at = italian_now()
            
            # Aggiungi orari se forniti (per permessi orari)
            if form.start_time.data:
                new_request.start_time = form.start_time.data
            if form.end_time.data:
                new_request.end_time = form.end_time.data
            
            # Gestisci banca ore
            if form.use_banca_ore.data and current_user.banca_ore_enabled:
                # Verifica se è un permesso orario (prerequisito per banca ore)
                if new_request.is_time_based():
                    # Calcola ore necessarie
                    hours_needed = new_request.calculate_banca_ore_hours_needed()
                    
                    # Verifica saldo disponibile
                    from blueprints.banca_ore import calculate_banca_ore_balance
                    wallet = calculate_banca_ore_balance(current_user.id)
                    
                    if wallet and wallet['ore_saldo'] >= hours_needed:
                        new_request.use_banca_ore = True
                        # Le ore effettive verranno scalate all'approvazione
                    else:
                        available = wallet['ore_saldo'] if wallet else 0.0
                        flash(f'Ore banca ore insufficienti. Disponibili: {available:.1f}h, Richieste: {hours_needed:.1f}h', 'warning')
                        return render_template('create_leave_request.html', form=form, today=date.today())
                else:
                    flash('La banca ore può essere utilizzata solo per permessi orari', 'warning')
                    return render_template('create_leave_request.html', form=form, today=date.today())
            
            db.session.add(new_request)
            db.session.commit()
            
            flash('Richiesta creata correttamente', 'success')
            return redirect(url_for('leave.leave_requests', view='my'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore nella creazione richiesta: {str(e)}', 'danger')
    
    return render_template('create_leave_request.html', form=form, today=date.today())

@leave_bp.route('/approve_leave_request/<int:request_id>', methods=['POST'])
@login_required
def approve_leave_request(request_id):
    """Approva richiesta ferie/permessi/malattie"""
    if not current_user.can_approve_leave():
        flash('Non hai i permessi per approvare richieste', 'danger')
        return redirect(url_for('leave.leave_requests'))
    
    try:
        leave_request = LeaveRequest.query.get_or_404(request_id)
        
        # Controllo sede se non multi-sede
        if not current_user.all_sedi:
            if (current_user.sede_obj and 
                leave_request.user.sede_id != current_user.sede_obj.id):
                flash('Non puoi approvare richieste di altre sedi', 'danger')
                return redirect(url_for('leave.leave_requests'))
        
        if leave_request.status != 'Pending':
            flash('La richiesta è già stata processata', 'warning')
            return redirect(url_for('leave.leave_requests'))
        
        leave_request.status = 'Approved'
        leave_request.approved_by = current_user.id
        leave_request.approved_at = italian_now()
        
        # Aggiungi note di approvazione se fornite
        approval_notes = request.form.get('approval_notes')
        if approval_notes:
            leave_request.approval_notes = approval_notes
        
        # Scala ore dalla banca ore se richiesto
        if leave_request.use_banca_ore and leave_request.user.banca_ore_enabled:
            hours_to_deduct = leave_request.calculate_banca_ore_hours_needed()
            
            # Verifica nuovamente il saldo disponibile al momento dell'approvazione
            from blueprints.banca_ore import calculate_banca_ore_balance
            wallet = calculate_banca_ore_balance(leave_request.user.id)
            
            if wallet and wallet['ore_saldo'] >= hours_to_deduct:
                # Registra le ore effettivamente utilizzate
                leave_request.banca_ore_hours_used = hours_to_deduct
                flash(f'Richiesta approvata. Scalate {hours_to_deduct:.1f}h dalla banca ore dell\'utente.', 'success')
            else:
                # Saldo insufficiente, approva ma senza utilizzare banca ore
                leave_request.use_banca_ore = False
                leave_request.banca_ore_hours_used = None
                available = wallet['ore_saldo'] if wallet else 0.0
                flash(f'Richiesta approvata. Attenzione: ore banca ore insufficienti ({available:.1f}h disponibili), utilizzato permesso standard.', 'warning')
        
        db.session.commit()
        
        # Notifica al richiedente via email
        try:
            from email_utils import send_leave_approval_email
            send_leave_approval_email(leave_request, current_user)
        except Exception as e:
            # Continua anche se l'email fallisce
            print(f"Errore invio email approvazione: {str(e)}")
        
        # Determina il tipo per il messaggio
        leave_type_name = 'ferie/permesso'
        if leave_request.leave_type_obj:
            leave_type_name = leave_request.leave_type_obj.name.lower()
        elif leave_request.leave_type:
            leave_type_name = leave_request.leave_type.lower()
        
        flash(f'Richiesta {leave_type_name} approvata correttamente', 'success')
        return redirect(url_for('leave.leave_requests'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Errore: {str(e)}', 'danger')
        return redirect(url_for('leave.leave_requests'))

@leave_bp.route('/reject_leave_request/<int:request_id>', methods=['POST'])
@login_required
def reject_leave_request(request_id):
    """Rifiuta richiesta ferie/permessi/malattie"""
    if not current_user.can_approve_leave():
        flash('Non hai i permessi per rifiutare richieste', 'danger')
        return redirect(url_for('leave.leave_requests'))
    
    try:
        leave_request = LeaveRequest.query.get_or_404(request_id)
        
        # Controllo sede se non multi-sede
        if not current_user.all_sedi:
            if (current_user.sede_obj and 
                leave_request.user.sede_id != current_user.sede_obj.id):
                flash('Non puoi rifiutare richieste di altre sedi', 'danger')
                return redirect(url_for('leave.leave_requests'))
        
        if leave_request.status != 'Pending':
            flash('La richiesta è già stata processata', 'warning')
            return redirect(url_for('leave.leave_requests'))
        
        rejection_reason = request.form.get('rejection_reason', 'Richiesta rifiutata')
        
        leave_request.status = 'Rejected'
        leave_request.approved_by = current_user.id
        leave_request.approved_at = italian_now()
        leave_request.approval_notes = rejection_reason
        
        db.session.commit()
        
        # Notifica al richiedente via email
        try:
            from email_utils import send_leave_rejection_email
            send_leave_rejection_email(leave_request, current_user, rejection_reason)
        except Exception as e:
            # Continua anche se l'email fallisce
            print(f"Errore invio email rifiuto: {str(e)}")
        
        # Determina il tipo per il messaggio
        leave_type_name = 'ferie/permesso'
        if leave_request.leave_type_obj:
            leave_type_name = leave_request.leave_type_obj.name.lower()
        elif leave_request.leave_type:
            leave_type_name = leave_request.leave_type.lower()
        
        flash(f'Richiesta {leave_type_name} rifiutata', 'warning')
        return redirect(url_for('leave.leave_requests'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Errore: {str(e)}', 'danger')
        return redirect(url_for('leave.leave_requests'))

@leave_bp.route('/view_leave_request/<int:request_id>')
@login_required  
def view_leave_request(request_id):
    """Visualizza dettagli di una singola richiesta ferie/permessi"""
    leave_request = LeaveRequest.query.get_or_404(request_id)
    
    # Controllo permessi: solo proprietario o chi può visualizzare tutte le richieste
    if leave_request.user_id != current_user.id and not current_user.can_view_leave():
        flash('Non hai i permessi per visualizzare questa richiesta', 'danger')
        return redirect(url_for('leave.leave_requests'))
    
    # Controllo sede se non multi-sede
    if (not current_user.all_sedi and current_user.sede_obj and 
        leave_request.user.sede_id != current_user.sede_obj.id and 
        leave_request.user_id != current_user.id):
        flash('Non puoi visualizzare richieste di altre sedi', 'danger')
        return redirect(url_for('leave.leave_requests'))
    
    return render_template('leave_detail.html', 
                         request=leave_request,
                         can_approve=current_user.can_approve_leave(),
                         today=date.today())

@leave_bp.route('/delete_leave_request/<int:request_id>', methods=['POST'])
@login_required
def delete_leave_request(request_id):
    """Elimina richiesta ferie/permessi"""
    leave_request = LeaveRequest.query.get_or_404(request_id)
    
    # Verifica che sia l'utente proprietario della richiesta
    if leave_request.user_id != current_user.id:
        flash('Non puoi cancellare richieste di altri utenti', 'danger')
        return redirect(url_for('leave.leave_requests'))
    
    # Verifica che la richiesta non sia già approvata E che non sia futura
    from zoneinfo import ZoneInfo
    italy_tz = ZoneInfo('Europe/Rome')
    today = datetime.now(italy_tz).date()
    
    if leave_request.status == 'Approved' and leave_request.start_date < today:
        flash('Non puoi cancellare richieste già approvate e iniziate', 'warning')
        return redirect(url_for('leave.leave_requests'))
    
    # Invia messaggi di cancellazione prima di eliminare la richiesta
    from utils import send_leave_request_message
    send_leave_request_message(leave_request, 'cancelled', current_user)
    
    # Cancella la richiesta
    db.session.delete(leave_request)
    db.session.commit()
    flash('Richiesta cancellata con successo', 'success')
    
    # Determina dove reindirizzare in base al referer
    referer = request.headers.get('Referer', '')
    if 'dashboard' in referer or referer.endswith('/'):
        return redirect(url_for('dashboard.dashboard'))
    else:
        return redirect(url_for('leave.leave_requests'))

@leave_bp.route('/api/leave_balance/<int:user_id>/<int:year>')
@login_required
def leave_balance_api(user_id, year):
    """API per ottenere saldo ferie di un utente per un anno specifico"""
    try:
        # Controllo permessi
        if user_id != current_user.id and not current_user.can_view_leave():
            return jsonify({'error': 'Non hai i permessi per visualizzare questi dati'}), 403
        
        user = User.query.get_or_404(user_id)
        
        # Controllo sede se non multi-sede
        if not current_user.all_sedi:
            if current_user.sede_obj and user.sede_id != current_user.sede_obj.id:
                return jsonify({'error': 'Non puoi visualizzare dati di altre sedi'}), 403
        
        # Calcola saldo ferie semplificato
        approved_requests = LeaveRequest.query.filter(
            LeaveRequest.user_id == user_id,
            LeaveRequest.status == 'Approved',
            db.extract('year', LeaveRequest.start_date) == year
        ).all()
        
        used_days = sum(req.working_days or 0 for req in approved_requests)
        balance = {'used_days': used_days, 'remaining_days': max(0, 22 - used_days)}
        
        return jsonify({
            'success': True,
            'user_name': user.get_full_name(),
            'year': year,
            'balance': balance
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================================================
# LEAVE TYPES MANAGEMENT ROUTES (Migrated from routes.py)
# =============================================================================

@leave_bp.route('/leave_types')
@login_required
def leave_types():
    """Gestione tipologie ferie/permessi"""
    if not (current_user.can_manage_leave() or current_user.can_manage_leave_types()):
        flash('Non hai i permessi per gestire le tipologie di permesso', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    leave_types = LeaveType.query.order_by(LeaveType.name).all()
    return render_template('leave_types.html', leave_types=leave_types)

@leave_bp.route('/leave_types/add', methods=['GET', 'POST'])
@login_required
def add_leave_type_page():
    """Aggiungi nuova tipologia ferie/permessi"""
    if not (current_user.can_manage_leave() or current_user.can_manage_leave_types()):
        flash('Non hai i permessi per aggiungere tipologie di permesso', 'danger')
        return redirect(url_for('leave.leave_types'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            requires_approval = 'requires_approval' in request.form
            active_status = 'active' in request.form
            
            # Verifica duplicati
            if LeaveType.query.filter_by(name=name).first():
                flash('Esiste già una tipologia con questo nome', 'warning')
                return render_template('add_leave_type.html')
            
            leave_type = LeaveType(
                name=name,
                description=description,
                requires_approval=requires_approval,
                active=active_status
            )
            
            db.session.add(leave_type)
            db.session.commit()
            flash(f'Tipologia "{name}" creata con successo', 'success')
            return redirect(url_for('leave.leave_types'))
        except Exception as e:
            db.session.rollback()
            flash('Errore nella creazione della tipologia', 'danger')
            return render_template('add_leave_type.html')
    
    # GET request - mostra form di creazione
    return render_template('add_leave_type.html')

@leave_bp.route('/leave_types/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_leave_type_page(id):
    """Modifica tipologia ferie/permessi"""
    if not (current_user.can_manage_leave() or current_user.can_manage_leave_types()):
        flash('Non hai i permessi per modificare tipologie di permesso', 'danger')
        return redirect(url_for('leave.leave_types'))
    
    leave_type = LeaveType.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            
            # Verifica duplicati (escludendo il record corrente)
            existing = LeaveType.query.filter(LeaveType.name == name, LeaveType.id != id).first()
            if existing:
                flash('Esiste già una tipologia con questo nome', 'warning')
                return render_template('edit_leave_type.html', leave_type=leave_type)
            
            leave_type.name = name
            leave_type.description = request.form.get('description')
            leave_type.requires_approval = 'requires_approval' in request.form
            leave_type.active = 'active' in request.form
            leave_type.updated_at = italian_now()
            
            db.session.commit()
            flash(f'Tipologia "{name}" aggiornata con successo', 'success')
            return redirect(url_for('leave.leave_types'))
        except Exception as e:
            db.session.rollback()
            flash('Errore nell\'aggiornamento della tipologia', 'danger')
            return render_template('edit_leave_type.html', leave_type=leave_type)
    
    # GET request - mostra form di modifica
    return render_template('edit_leave_type.html', leave_type=leave_type)

@leave_bp.route('/leave_types/delete/<int:id>', methods=['POST'])
@login_required
def delete_leave_type(id):
    """Elimina tipologia ferie/permessi"""
    if not (current_user.can_manage_leave() or current_user.can_manage_leave_types()):
        flash('Non hai i permessi per eliminare tipologie di permesso', 'danger')
        return redirect(url_for('leave.leave_types'))
    
    leave_type = LeaveType.query.get_or_404(id)
    
    # Verifica che non ci siano richieste associate
    if leave_type.leave_requests.count() > 0:
        flash('Non è possibile eliminare una tipologia con richieste associate', 'warning')
        return redirect(url_for('leave.leave_types'))
    
    try:
        name = leave_type.name
        db.session.delete(leave_type)
        db.session.commit()
        flash(f'Tipologia "{name}" eliminata con successo', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Errore nell\'eliminazione della tipologia', 'danger')
    
    return redirect(url_for('leave.leave_types'))