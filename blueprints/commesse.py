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
from models import Commessa, User, commessa_assignment, italian_now
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
        # TODO: aggiungere permessi specifici quando implementati nel sistema permessi
        # Per ora consentiamo a tutti gli utenti autenticati
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
            budget_ore=form.budget_ore.data,
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
        commessa.budget_ore = form.budget_ore.data
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
    assigned_user_ids = [u.id for u in commessa.assigned_users]
    available_users = [u for u in all_users if u.id not in assigned_user_ids]
    
    return render_template('commessa_detail.html',
                         commessa=commessa,
                         assigned_users=commessa.assigned_users,
                         available_users=available_users)


# =============================================================================
# COMMESSE ASSIGNMENT ROUTES
# =============================================================================

@commesse_bp.route('/assign', methods=['POST'])
@login_required
@require_commesse_permission
def assign_user():
    """Assegnazione risorsa a commessa"""
    commessa_id = request.form.get('commessa_id', type=int)
    user_id = request.form.get('user_id', type=int)
    
    if not commessa_id or not user_id:
        flash('Parametri mancanti per l\'assegnazione', 'danger')
        return redirect(url_for('commesse.manage_commesse'))
    
    commessa = filter_by_company(Commessa.query).filter_by(id=commessa_id).first_or_404()
    user = filter_by_company(User.query).filter_by(id=user_id).first_or_404()
    
    # Verifica se l'assegnazione esiste già
    if user in commessa.assigned_users:
        flash(f'{user.get_full_name()} è già assegnato a questa commessa', 'warning')
        return redirect(url_for('commesse.commessa_detail', commessa_id=commessa_id))
    
    # Aggiungi assegnazione
    commessa.assigned_users.append(user)
    db.session.commit()
    
    flash(f'{user.get_full_name()} assegnato con successo alla commessa "{commessa.titolo}"', 'success')
    return redirect(url_for('commesse.commessa_detail', commessa_id=commessa_id))


@commesse_bp.route('/unassign', methods=['POST'])
@login_required
@require_commesse_permission
def unassign_user():
    """Rimozione assegnazione risorsa da commessa"""
    commessa_id = request.form.get('commessa_id', type=int)
    user_id = request.form.get('user_id', type=int)
    
    if not commessa_id or not user_id:
        flash('Parametri mancanti per la rimozione', 'danger')
        return redirect(url_for('commesse.manage_commesse'))
    
    commessa = filter_by_company(Commessa.query).filter_by(id=commessa_id).first_or_404()
    user = filter_by_company(User.query).filter_by(id=user_id).first_or_404()
    
    # Verifica se l'assegnazione esiste
    if user not in commessa.assigned_users:
        flash(f'{user.get_full_name()} non è assegnato a questa commessa', 'warning')
        return redirect(url_for('commesse.commessa_detail', commessa_id=commessa_id))
    
    # Rimuovi assegnazione
    commessa.assigned_users.remove(user)
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
