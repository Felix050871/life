# =============================================================================
# MANSIONI BLUEPRINT - Gestione Mansionario Aziendale
# =============================================================================

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import Mansione, db
from utils_tenant import filter_by_company, set_company_on_create
from functools import wraps

mansioni_bp = Blueprint('mansioni', __name__)

# =============================================================================
# DECORATORS
# =============================================================================

def require_mansioni_permission(f):
    """Decorator per verificare i permessi di accesso al mansionario"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.can_access_mansioni_menu():
            flash('Non hai i permessi per accedere a questa sezione', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# ROUTES
# =============================================================================

@mansioni_bp.route('/mansioni')
@login_required
@require_mansioni_permission
def index():
    """Lista mansioni aziendali"""
    query = filter_by_company(Mansione.query)
    
    # Filtro ricerca
    search = request.args.get('search', '')
    if search:
        query = query.filter(Mansione.nome.ilike(f'%{search}%'))
    
    # Ordina per nome
    mansioni = query.order_by(Mansione.nome.asc()).all()
    
    return render_template('mansioni/index.html', 
                         mansioni=mansioni,
                         search=search,
                         can_manage=current_user.can_manage_mansioni())

@mansioni_bp.route('/mansioni/create', methods=['GET', 'POST'])
@login_required
@require_mansioni_permission
def create():
    """Crea una nuova mansione"""
    if not current_user.can_manage_mansioni():
        flash('Non hai i permessi per creare mansioni', 'danger')
        return redirect(url_for('mansioni.index'))
    
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        descrizione = request.form.get('descrizione', '').strip()
        abilita_turnazioni = request.form.get('abilita_turnazioni') == 'on'
        abilita_reperibilita = request.form.get('abilita_reperibilita') == 'on'
        
        if not nome:
            flash('Il nome della mansione è obbligatorio', 'danger')
            return render_template('mansioni/create.html')
        
        # Verifica duplicati
        existing = filter_by_company(Mansione.query).filter_by(nome=nome).first()
        if existing:
            flash(f'Esiste già una mansione con il nome "{nome}"', 'warning')
            return render_template('mansioni/create.html')
        
        try:
            mansione = Mansione(
                nome=nome,
                descrizione=descrizione if descrizione else None,
                abilita_turnazioni=abilita_turnazioni,
                abilita_reperibilita=abilita_reperibilita,
                created_by_id=current_user.id
            )
            set_company_on_create(mansione)
            db.session.add(mansione)
            db.session.commit()
            
            flash(f'✅ Mansione "{nome}" creata con successo', 'success')
            return redirect(url_for('mansioni.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la creazione: {str(e)}', 'danger')
            return render_template('mansioni/create.html')
    
    return render_template('mansioni/create.html')

@mansioni_bp.route('/mansioni/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@require_mansioni_permission
def edit(id):
    """Modifica una mansione esistente"""
    if not current_user.can_manage_mansioni():
        flash('Non hai i permessi per modificare mansioni', 'danger')
        return redirect(url_for('mansioni.index'))
    
    mansione = filter_by_company(Mansione.query).filter_by(id=id).first_or_404()
    
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        descrizione = request.form.get('descrizione', '').strip()
        active = request.form.get('active') == 'on'
        abilita_turnazioni = request.form.get('abilita_turnazioni') == 'on'
        abilita_reperibilita = request.form.get('abilita_reperibilita') == 'on'
        
        if not nome:
            flash('Il nome della mansione è obbligatorio', 'danger')
            return render_template('mansioni/edit.html', mansione=mansione)
        
        # Verifica duplicati (esclusa la mansione corrente)
        existing = filter_by_company(Mansione.query).filter(
            Mansione.nome == nome,
            Mansione.id != id
        ).first()
        if existing:
            flash(f'Esiste già un\'altra mansione con il nome "{nome}"', 'warning')
            return render_template('mansioni/edit.html', mansione=mansione)
        
        try:
            mansione.nome = nome
            mansione.descrizione = descrizione if descrizione else None
            mansione.active = active
            mansione.abilita_turnazioni = abilita_turnazioni
            mansione.abilita_reperibilita = abilita_reperibilita
            db.session.commit()
            
            flash(f'✅ Mansione "{nome}" modificata con successo', 'success')
            return redirect(url_for('mansioni.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la modifica: {str(e)}', 'danger')
            return render_template('mansioni/edit.html', mansione=mansione)
    
    return render_template('mansioni/edit.html', mansione=mansione)

@mansioni_bp.route('/mansioni/<int:id>/delete', methods=['POST'])
@login_required
@require_mansioni_permission
def delete(id):
    """Elimina una mansione"""
    if not current_user.can_manage_mansioni():
        flash('Non hai i permessi per eliminare mansioni', 'danger')
        return redirect(url_for('mansioni.index'))
    
    mansione = filter_by_company(Mansione.query).filter_by(id=id).first_or_404()
    
    try:
        nome = mansione.nome
        db.session.delete(mansione)
        db.session.commit()
        
        flash(f'✅ Mansione "{nome}" eliminata con successo', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante l\'eliminazione: {str(e)}', 'danger')
    
    return redirect(url_for('mansioni.index'))

@mansioni_bp.route('/mansioni/<int:id>/toggle', methods=['POST'])
@login_required
@require_mansioni_permission
def toggle_active(id):
    """Attiva/disattiva una mansione"""
    if not current_user.can_manage_mansioni():
        flash('Non hai i permessi per modificare mansioni', 'danger')
        return redirect(url_for('mansioni.index'))
    
    mansione = filter_by_company(Mansione.query).filter_by(id=id).first_or_404()
    
    try:
        mansione.active = not mansione.active
        db.session.commit()
        
        stato = "attivata" if mansione.active else "disattivata"
        flash(f'✅ Mansione "{mansione.nome}" {stato} con successo', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Errore: {str(e)}', 'danger')
    
    return redirect(url_for('mansioni.index'))
