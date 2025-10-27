# =============================================================================
# COMMESSE (PROJECT MANAGEMENT) BLUEPRINT
# =============================================================================
#
# ROUTES INCLUSE:
# 1. manage_commesse (GET) - Elenco e gestione commesse
# 2. create_commessa (GET/POST) - Creazione nuova commessa
# 3. edit_commessa (GET/POST) - Modifica commessa esistente
# 4. delete_commessa (POST) - Eliminazione commessa
# 5. commessa_detail (GET) - Dettaglio commessa con assegnazioni
# 6. assign_user (POST) - Assegnazione risorsa a commessa
# 7. unassign_user (POST) - Rimozione assegnazione risorsa
# 8. commessa_users (GET) - Lista risorse assegnate a commessa
# 9. user_commesse (GET) - Lista commesse assegnate a risorsa
#
# Total routes: 9 commesse management routes
# =============================================================================

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date
from functools import wraps
from app import db
from models import Commessa, User, CommessaAssignment, italian_now
from forms import CommessaForm
from utils_tenant import filter_by_company, set_company_on_create, get_user_company_id

# Create blueprint
commesse_bp = Blueprint('commesse', __name__, url_prefix='/commesse')

# Helper function per permessi
def require_commesse_permission(f):
    """Decorator per richiedere permessi commesse"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        # Verifica permessi commesse
        if not current_user.can_access_commesse_menu():
            flash('Non hai i permessi necessari per accedere a questa sezione.', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function


# =============================================================================
# COMMESSE CRUD ROUTES
# =============================================================================

@commesse_bp.route('/')
@login_required
@require_commesse_permission
def manage_commesse():
    """Elenco e gestione commesse"""
    # Filtri dalla query string
    stato_filter = request.args.get('stato', '')
    cliente_filter = request.args.get('cliente', '')
    
    # Query base con filtro company
    query = filter_by_company(Commessa.query)
    
    # Applica filtri
    if stato_filter:
        query = query.filter_by(stato=stato_filter)
    if cliente_filter:
        query = query.filter(Commessa.cliente.ilike(f'%{cliente_filter}%'))
    
    # Ordina per data fine (scadenze più vicine prima)
    commesse = query.order_by(Commessa.data_fine.asc()).all()
    
    # Statistiche
    totale_commesse = filter_by_company(Commessa.query).count()
    commesse_attive = filter_by_company(Commessa.query).filter_by(stato='attiva').count()
    commesse_in_corso = filter_by_company(Commessa.query).filter_by(stato='in corso').count()
    commesse_chiuse = filter_by_company(Commessa.query).filter_by(stato='chiusa').count()
    
    # Clienti unici per filtro
    clienti = db.session.query(Commessa.cliente).filter(
        Commessa.company_id == get_user_company_id()
    ).distinct().order_by(Commessa.cliente).all()
    clienti_list = [c.cliente for c in clienti]
    
    return render_template('manage_commesse.html',
                         commesse=commesse,
                         totale_commesse=totale_commesse,
                         commesse_attive=commesse_attive,
                         commesse_in_corso=commesse_in_corso,
                         commesse_chiuse=commesse_chiuse,
                         clienti=clienti_list,
                         stato_filter=stato_filter,
                         cliente_filter=cliente_filter)


@commesse_bp.route('/create', methods=['GET', 'POST'])
@login_required
@require_commesse_permission
def create_commessa():
    """Creazione nuova commessa"""
    # Verifica permesso di gestione
    if not current_user.can_manage_commesse():
        flash('Non hai i permessi necessari per creare commesse.', 'danger')
        return redirect(url_for('commesse.manage_commesse'))
    
    form = CommessaForm()
    
    if form.validate_on_submit():
        commessa = Commessa(
            cliente=form.cliente.data,
            titolo=form.titolo.data,
            descrizione=form.descrizione.data,
            attivita=form.attivita.data,
            data_inizio=form.data_inizio.data,
            data_fine=form.data_fine.data,
            durata_prevista_ore=form.durata_prevista_ore.data,
            stato=form.stato.data,
            tariffa_oraria=form.tariffa_oraria.data,
            note=form.note.data,
            created_by_id=current_user.id
        )
        set_company_on_create(commessa)
        db.session.add(commessa)
        db.session.commit()
        
        flash(f'Commessa "{commessa.titolo}" creata con successo', 'success')
        return redirect(url_for('commesse.commessa_detail', commessa_id=commessa.id))
    
    return render_template('create_commessa.html', form=form)


@commesse_bp.route('/edit/<int:commessa_id>', methods=['GET', 'POST'])
@login_required
@require_commesse_permission
def edit_commessa(commessa_id):
    """Modifica commessa esistente"""
    # Verifica permesso di gestione
    if not current_user.can_manage_commesse():
        flash('Non hai i permessi necessari per modificare commesse.', 'danger')
        return redirect(url_for('commesse.manage_commesse'))
    
    commessa = filter_by_company(Commessa.query).filter_by(id=commessa_id).first_or_404()
    form = CommessaForm(original_titolo=commessa.titolo, obj=commessa)
    
    if form.validate_on_submit():
        commessa.cliente = form.cliente.data
        commessa.titolo = form.titolo.data
        commessa.descrizione = form.descrizione.data
        commessa.attivita = form.attivita.data
        commessa.data_inizio = form.data_inizio.data
        commessa.data_fine = form.data_fine.data
        commessa.durata_prevista_ore = form.durata_prevista_ore.data
        commessa.stato = form.stato.data
        commessa.tariffa_oraria = form.tariffa_oraria.data
        commessa.note = form.note.data
        
        db.session.commit()
        flash(f'Commessa "{commessa.titolo}" modificata con successo', 'success')
        return redirect(url_for('commesse.commessa_detail', commessa_id=commessa.id))
    
    return render_template('edit_commessa.html', form=form, commessa=commessa)


@commesse_bp.route('/delete/<int:commessa_id>', methods=['POST'])
@login_required
@require_commesse_permission
def delete_commessa(commessa_id):
    """Eliminazione commessa"""
    # Verifica permesso di gestione
    if not current_user.can_manage_commesse():
        flash('Non hai i permessi necessari per eliminare commesse.', 'danger')
        return redirect(url_for('commesse.manage_commesse'))
    
    commessa = filter_by_company(Commessa.query).filter_by(id=commessa_id).first_or_404()
    
    # Verifica se ci sono risorse assegnate
    if len(commessa.assigned_users) > 0:
        flash(f'Impossibile eliminare la commessa "{commessa.titolo}": ci sono {len(commessa.assigned_users)} risorse assegnate. Rimuovi prima le assegnazioni.', 'danger')
        return redirect(url_for('commesse.commessa_detail', commessa_id=commessa_id))
    
    titolo = commessa.titolo
    db.session.delete(commessa)
    db.session.commit()
    
    flash(f'Commessa "{titolo}" eliminata con successo', 'success')
    return redirect(url_for('commesse.manage_commesse'))


@commesse_bp.route('/detail/<int:commessa_id>')
@login_required
@require_commesse_permission
def commessa_detail(commessa_id):
    """Dettaglio commessa con gestione assegnazioni risorse"""
    commessa = filter_by_company(Commessa.query).filter_by(id=commessa_id).first_or_404()
    
    # Ottieni tutti gli utenti disponibili per assegnazione
    all_users = filter_by_company(User.query).filter(
        User.active == True,
        User.role != 'Amministratore'
    ).order_by(User.first_name, User.last_name).all()
    
    # Filtra gli utenti non ancora assegnati
    assigned_user_ids = [assignment.user_id for assignment in commessa.resource_assignments]
    available_users = [u for u in all_users if u.id not in assigned_user_ids]
    
    return render_template('commessa_detail.html',
                         commessa=commessa,
                         available_users=available_users)


# =============================================================================
# COMMESSE ASSIGNMENT ROUTES
# =============================================================================

@commesse_bp.route('/assign', methods=['POST'])
@login_required
@require_commesse_permission
def assign_user():
    """Assegnazione risorsa a commessa"""
    # Verifica permesso di gestione
    if not current_user.can_manage_commesse():
        flash('Non hai i permessi necessari per assegnare risorse.', 'danger')
        return redirect(url_for('commesse.manage_commesse'))
    
    commessa_id = request.form.get('commessa_id', type=int)
    user_id = request.form.get('user_id', type=int)
    
    if not commessa_id or not user_id:
        flash('Parametri mancanti per l\'assegnazione', 'danger')
        return redirect(url_for('commesse.manage_commesse'))
    
    commessa = filter_by_company(Commessa.query).filter_by(id=commessa_id).first_or_404()
    user = filter_by_company(User.query).filter_by(id=user_id).first_or_404()
    
    # Verifica se l'assegnazione esiste già
    existing_assignment = commessa.get_assignment_for_user(user)
    if existing_assignment:
        flash(f'{user.get_full_name()} è già assegnato a questa commessa', 'warning')
        return redirect(url_for('commesse.commessa_detail', commessa_id=commessa_id))
    
    # Ottieni date e flag responsabile dal form (default = durata commessa)
    data_inizio_str = request.form.get('data_inizio')
    data_fine_str = request.form.get('data_fine')
    is_responsabile = request.form.get('is_responsabile') == 'on'
    
    # Parse date o usa default
    if data_inizio_str:
        try:
            data_inizio = datetime.strptime(data_inizio_str, '%Y-%m-%d').date()
        except ValueError:
            data_inizio = commessa.data_inizio
    else:
        data_inizio = commessa.data_inizio
    
    if data_fine_str:
        try:
            data_fine = datetime.strptime(data_fine_str, '%Y-%m-%d').date()
        except ValueError:
            data_fine = commessa.data_fine
    else:
        data_fine = commessa.data_fine
    
    # Crea nuova assegnazione
    assignment = CommessaAssignment(
        user_id=user.id,
        commessa_id=commessa.id,
        data_inizio=data_inizio,
        data_fine=data_fine,
        is_responsabile=is_responsabile,
        assigned_by_id=current_user.id
    )
    
    # Valida le date (passa commessa esplicitamente perché la relazione non è ancora caricata)
    validation_errors = assignment.validate_dates(commessa=commessa)
    if validation_errors:
        for error in validation_errors:
            flash(error, 'danger')
        return redirect(url_for('commesse.commessa_detail', commessa_id=commessa_id))
    
    db.session.add(assignment)
    db.session.commit()
    
    role_msg = " come RESPONSABILE" if is_responsabile else ""
    flash(f'{user.get_full_name()} assegnato{role_msg} alla commessa "{commessa.titolo}" ({data_inizio} - {data_fine})', 'success')
    return redirect(url_for('commesse.commessa_detail', commessa_id=commessa_id))


@commesse_bp.route('/unassign', methods=['POST'])
@login_required
@require_commesse_permission
def unassign_user():
    """Rimozione assegnazione risorsa da commessa"""
    # Verifica permesso di gestione
    if not current_user.can_manage_commesse():
        flash('Non hai i permessi necessari per rimuovere assegnazioni.', 'danger')
        return redirect(url_for('commesse.manage_commesse'))
    
    commessa_id = request.form.get('commessa_id', type=int)
    user_id = request.form.get('user_id', type=int)
    
    if not commessa_id or not user_id:
        flash('Parametri mancanti per la rimozione', 'danger')
        return redirect(url_for('commesse.manage_commesse'))
    
    commessa = filter_by_company(Commessa.query).filter_by(id=commessa_id).first_or_404()
    user = filter_by_company(User.query).filter_by(id=user_id).first_or_404()
    
    # Trova l'assegnazione
    assignment = commessa.get_assignment_for_user(user)
    if not assignment:
        flash(f'{user.get_full_name()} non è assegnato a questa commessa', 'warning')
        return redirect(url_for('commesse.commessa_detail', commessa_id=commessa_id))
    
    # Rimuovi assegnazione
    db.session.delete(assignment)
    db.session.commit()
    
    flash(f'{user.get_full_name()} rimosso dalla commessa "{commessa.titolo}"', 'success')
    return redirect(url_for('commesse.commessa_detail', commessa_id=commessa_id))


# =============================================================================
# API ROUTES PER ASSEGNAZIONI
# =============================================================================

@commesse_bp.route('/api/commessa/<int:commessa_id>/users')
@login_required
def commessa_users(commessa_id):
    """API: elenco risorse assegnate a una commessa"""
    commessa = filter_by_company(Commessa.query).filter_by(id=commessa_id).first_or_404()
    
    users_data = []
    for user in commessa.assigned_users:
        users_data.append({
            'id': user.id,
            'nome_completo': user.get_full_name(),
            'email': user.email,
            'ruolo': user.role
        })
    
    return jsonify({
        'success': True,
        'commessa': commessa.titolo,
        'users': users_data,
        'total': len(users_data)
    })


@commesse_bp.route('/api/user/<int:user_id>/commesse')
@login_required
def user_commesse(user_id):
    """API: elenco commesse assegnate a una risorsa"""
    user = filter_by_company(User.query).filter_by(id=user_id).first_or_404()
    
    commesse_data = []
    for commessa in user.assigned_commesse:
        # Verifica che la commessa appartenga alla stessa company
        if commessa.company_id == get_user_company_id():
            commesse_data.append({
                'id': commessa.id,
                'titolo': commessa.titolo,
                'cliente': commessa.cliente,
                'stato': commessa.stato,
                'data_inizio': commessa.data_inizio.isoformat(),
                'data_fine': commessa.data_fine.isoformat(),
                'giorni_rimanenti': commessa.get_giorni_rimanenti(),
                'is_scaduta': commessa.is_scaduta()
            })
    
    return jsonify({
        'success': True,
        'user': user.get_full_name(),
        'commesse': commesse_data,
        'total': len(commesse_data)
    })
