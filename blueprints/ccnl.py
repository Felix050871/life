# =============================================================================
# CCNL BLUEPRINT - Gestione CCNL, Qualifiche e Livelli
# =============================================================================

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import CCNLContract, CCNLQualification, CCNLLevel, db
from utils_tenant import filter_by_company, set_company_on_create
from functools import wraps

ccnl_bp = Blueprint('ccnl', __name__)

# =============================================================================
# DECORATORS
# =============================================================================

def require_ccnl_permission(f):
    """Decorator per verificare i permessi di accesso al CCNL"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.can_access_ccnl_menu():
            flash('Non hai i permessi per accedere a questa sezione', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# ROUTES - CCNL CONTRACTS
# =============================================================================

@ccnl_bp.route('/ccnl')
@login_required
@require_ccnl_permission
def index():
    """Lista CCNL aziendali"""
    query = filter_by_company(CCNLContract.query)
    
    # Filtro ricerca
    search = request.args.get('search', '')
    if search:
        query = query.filter(CCNLContract.nome.ilike(f'%{search}%'))
    
    # Ordina per nome
    ccnl_list = query.order_by(CCNLContract.nome.asc()).all()
    
    return render_template('ccnl/index.html', 
                         ccnl_list=ccnl_list,
                         search=search,
                         can_manage=current_user.can_manage_ccnl())

@ccnl_bp.route('/ccnl/create', methods=['GET', 'POST'])
@login_required
@require_ccnl_permission
def create():
    """Crea un nuovo CCNL"""
    if not current_user.can_manage_ccnl():
        flash('Non hai i permessi per creare CCNL', 'danger')
        return redirect(url_for('ccnl.index'))
    
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        descrizione = request.form.get('descrizione', '').strip()
        
        if not nome:
            flash('Il nome del CCNL è obbligatorio', 'danger')
            return render_template('ccnl/create.html')
        
        # Verifica duplicati
        existing = filter_by_company(CCNLContract.query).filter_by(nome=nome).first()
        if existing:
            flash(f'Esiste già un CCNL con il nome "{nome}"', 'warning')
            return render_template('ccnl/create.html')
        
        try:
            ccnl = CCNLContract(
                nome=nome,
                descrizione=descrizione if descrizione else None,
                created_by_id=current_user.id
            )
            set_company_on_create(ccnl)
            db.session.add(ccnl)
            db.session.commit()
            
            flash(f'✅ CCNL "{nome}" creato con successo', 'success')
            return redirect(url_for('ccnl.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la creazione: {str(e)}', 'danger')
            return render_template('ccnl/create.html')
    
    return render_template('ccnl/create.html')

@ccnl_bp.route('/ccnl/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@require_ccnl_permission
def edit(id):
    """Modifica un CCNL esistente"""
    if not current_user.can_manage_ccnl():
        flash('Non hai i permessi per modificare CCNL', 'danger')
        return redirect(url_for('ccnl.index'))
    
    ccnl = filter_by_company(CCNLContract.query).filter_by(id=id).first_or_404()
    
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        descrizione = request.form.get('descrizione', '').strip()
        active = request.form.get('active') == 'on'
        
        if not nome:
            flash('Il nome del CCNL è obbligatorio', 'danger')
            return render_template('ccnl/edit.html', ccnl=ccnl)
        
        # Verifica duplicati (escluso il CCNL corrente)
        existing = filter_by_company(CCNLContract.query).filter(
            CCNLContract.nome == nome,
            CCNLContract.id != id
        ).first()
        if existing:
            flash(f'Esiste già un altro CCNL con il nome "{nome}"', 'warning')
            return render_template('ccnl/edit.html', ccnl=ccnl)
        
        try:
            ccnl.nome = nome
            ccnl.descrizione = descrizione if descrizione else None
            ccnl.active = active
            db.session.commit()
            
            flash(f'✅ CCNL "{nome}" modificato con successo', 'success')
            return redirect(url_for('ccnl.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la modifica: {str(e)}', 'danger')
            return render_template('ccnl/edit.html', ccnl=ccnl)
    
    return render_template('ccnl/edit.html', ccnl=ccnl)

@ccnl_bp.route('/ccnl/<int:id>/delete', methods=['POST'])
@login_required
@require_ccnl_permission
def delete(id):
    """Elimina un CCNL"""
    if not current_user.can_manage_ccnl():
        flash('Non hai i permessi per eliminare CCNL', 'danger')
        return redirect(url_for('ccnl.index'))
    
    ccnl = filter_by_company(CCNLContract.query).filter_by(id=id).first_or_404()
    
    try:
        nome = ccnl.nome
        db.session.delete(ccnl)
        db.session.commit()
        
        flash(f'✅ CCNL "{nome}" eliminato con successo', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante l\'eliminazione: {str(e)}', 'danger')
    
    return redirect(url_for('ccnl.index'))

@ccnl_bp.route('/ccnl/<int:id>/toggle', methods=['POST'])
@login_required
@require_ccnl_permission
def toggle_active(id):
    """Attiva/disattiva un CCNL"""
    if not current_user.can_manage_ccnl():
        flash('Non hai i permessi per modificare CCNL', 'danger')
        return redirect(url_for('ccnl.index'))
    
    ccnl = filter_by_company(CCNLContract.query).filter_by(id=id).first_or_404()
    
    try:
        ccnl.active = not ccnl.active
        db.session.commit()
        
        stato = "attivato" if ccnl.active else "disattivato"
        flash(f'✅ CCNL "{ccnl.nome}" {stato} con successo', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Errore: {str(e)}', 'danger')
    
    return redirect(url_for('ccnl.index'))

# =============================================================================
# ROUTES - QUALIFICATIONS
# =============================================================================

@ccnl_bp.route('/ccnl/<int:ccnl_id>/qualifications')
@login_required
@require_ccnl_permission
def qualifications(ccnl_id):
    """Lista qualifiche di un CCNL"""
    ccnl = filter_by_company(CCNLContract.query).filter_by(id=ccnl_id).first_or_404()
    
    query = filter_by_company(CCNLQualification.query).filter_by(ccnl_id=ccnl_id)
    
    # Filtro ricerca
    search = request.args.get('search', '')
    if search:
        query = query.filter(CCNLQualification.nome.ilike(f'%{search}%'))
    
    qualifications = query.order_by(CCNLQualification.nome.asc()).all()
    
    return render_template('ccnl/qualifications.html', 
                         ccnl=ccnl,
                         qualifications=qualifications,
                         search=search,
                         can_manage=current_user.can_manage_ccnl())

@ccnl_bp.route('/ccnl/<int:ccnl_id>/qualifications/create', methods=['GET', 'POST'])
@login_required
@require_ccnl_permission
def create_qualification(ccnl_id):
    """Crea una nuova qualifica"""
    if not current_user.can_manage_ccnl():
        flash('Non hai i permessi per creare qualifiche', 'danger')
        return redirect(url_for('ccnl.qualifications', ccnl_id=ccnl_id))
    
    ccnl = filter_by_company(CCNLContract.query).filter_by(id=ccnl_id).first_or_404()
    
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        descrizione = request.form.get('descrizione', '').strip()
        
        if not nome:
            flash('Il nome della qualifica è obbligatorio', 'danger')
            return render_template('ccnl/create_qualification.html', ccnl=ccnl)
        
        # Verifica duplicati
        existing = filter_by_company(CCNLQualification.query).filter_by(
            ccnl_id=ccnl_id,
            nome=nome
        ).first()
        if existing:
            flash(f'Esiste già una qualifica con il nome "{nome}" per questo CCNL', 'warning')
            return render_template('ccnl/create_qualification.html', ccnl=ccnl)
        
        try:
            qualification = CCNLQualification(
                ccnl_id=ccnl_id,
                nome=nome,
                descrizione=descrizione if descrizione else None
            )
            set_company_on_create(qualification)
            db.session.add(qualification)
            db.session.commit()
            
            flash(f'✅ Qualifica "{nome}" creata con successo', 'success')
            return redirect(url_for('ccnl.qualifications', ccnl_id=ccnl_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la creazione: {str(e)}', 'danger')
            return render_template('ccnl/create_qualification.html', ccnl=ccnl)
    
    return render_template('ccnl/create_qualification.html', ccnl=ccnl)

@ccnl_bp.route('/ccnl/<int:ccnl_id>/qualifications/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@require_ccnl_permission
def edit_qualification(ccnl_id, id):
    """Modifica una qualifica esistente"""
    if not current_user.can_manage_ccnl():
        flash('Non hai i permessi per modificare qualifiche', 'danger')
        return redirect(url_for('ccnl.qualifications', ccnl_id=ccnl_id))
    
    ccnl = filter_by_company(CCNLContract.query).filter_by(id=ccnl_id).first_or_404()
    qualification = filter_by_company(CCNLQualification.query).filter_by(
        id=id,
        ccnl_id=ccnl_id
    ).first_or_404()
    
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        descrizione = request.form.get('descrizione', '').strip()
        active = request.form.get('active') == 'on'
        
        if not nome:
            flash('Il nome della qualifica è obbligatorio', 'danger')
            return render_template('ccnl/edit_qualification.html', ccnl=ccnl, qualification=qualification)
        
        # Verifica duplicati (esclusa la qualifica corrente)
        existing = filter_by_company(CCNLQualification.query).filter(
            CCNLQualification.ccnl_id == ccnl_id,
            CCNLQualification.nome == nome,
            CCNLQualification.id != id
        ).first()
        if existing:
            flash(f'Esiste già un\'altra qualifica con il nome "{nome}"', 'warning')
            return render_template('ccnl/edit_qualification.html', ccnl=ccnl, qualification=qualification)
        
        try:
            qualification.nome = nome
            qualification.descrizione = descrizione if descrizione else None
            qualification.active = active
            db.session.commit()
            
            flash(f'✅ Qualifica "{nome}" modificata con successo', 'success')
            return redirect(url_for('ccnl.qualifications', ccnl_id=ccnl_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la modifica: {str(e)}', 'danger')
            return render_template('ccnl/edit_qualification.html', ccnl=ccnl, qualification=qualification)
    
    return render_template('ccnl/edit_qualification.html', ccnl=ccnl, qualification=qualification)

@ccnl_bp.route('/ccnl/<int:ccnl_id>/qualifications/<int:id>/delete', methods=['POST'])
@login_required
@require_ccnl_permission
def delete_qualification(ccnl_id, id):
    """Elimina una qualifica"""
    if not current_user.can_manage_ccnl():
        flash('Non hai i permessi per eliminare qualifiche', 'danger')
        return redirect(url_for('ccnl.qualifications', ccnl_id=ccnl_id))
    
    qualification = filter_by_company(CCNLQualification.query).filter_by(
        id=id,
        ccnl_id=ccnl_id
    ).first_or_404()
    
    try:
        nome = qualification.nome
        db.session.delete(qualification)
        db.session.commit()
        
        flash(f'✅ Qualifica "{nome}" eliminata con successo', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante l\'eliminazione: {str(e)}', 'danger')
    
    return redirect(url_for('ccnl.qualifications', ccnl_id=ccnl_id))

@ccnl_bp.route('/ccnl/<int:ccnl_id>/qualifications/<int:id>/toggle', methods=['POST'])
@login_required
@require_ccnl_permission
def toggle_qualification(ccnl_id, id):
    """Attiva/disattiva una qualifica"""
    if not current_user.can_manage_ccnl():
        flash('Non hai i permessi per modificare qualifiche', 'danger')
        return redirect(url_for('ccnl.qualifications', ccnl_id=ccnl_id))
    
    qualification = filter_by_company(CCNLQualification.query).filter_by(
        id=id,
        ccnl_id=ccnl_id
    ).first_or_404()
    
    try:
        qualification.active = not qualification.active
        db.session.commit()
        
        stato = "attivata" if qualification.active else "disattivata"
        flash(f'✅ Qualifica "{qualification.nome}" {stato} con successo', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Errore: {str(e)}', 'danger')
    
    return redirect(url_for('ccnl.qualifications', ccnl_id=ccnl_id))

# =============================================================================
# ROUTES - LEVELS
# =============================================================================

@ccnl_bp.route('/ccnl/<int:ccnl_id>/qualifications/<int:qual_id>/levels')
@login_required
@require_ccnl_permission
def levels(ccnl_id, qual_id):
    """Lista livelli di una qualifica"""
    ccnl = filter_by_company(CCNLContract.query).filter_by(id=ccnl_id).first_or_404()
    qualification = filter_by_company(CCNLQualification.query).filter_by(
        id=qual_id,
        ccnl_id=ccnl_id
    ).first_or_404()
    
    query = filter_by_company(CCNLLevel.query).filter_by(qualification_id=qual_id)
    
    # Filtro ricerca
    search = request.args.get('search', '')
    if search:
        query = query.filter(CCNLLevel.codice.ilike(f'%{search}%'))
    
    levels = query.order_by(CCNLLevel.codice.asc()).all()
    
    return render_template('ccnl/levels.html', 
                         ccnl=ccnl,
                         qualification=qualification,
                         levels=levels,
                         search=search,
                         can_manage=current_user.can_manage_ccnl())

@ccnl_bp.route('/ccnl/<int:ccnl_id>/qualifications/<int:qual_id>/levels/create', methods=['GET', 'POST'])
@login_required
@require_ccnl_permission
def create_level(ccnl_id, qual_id):
    """Crea un nuovo livello"""
    if not current_user.can_manage_ccnl():
        flash('Non hai i permessi per creare livelli', 'danger')
        return redirect(url_for('ccnl.levels', ccnl_id=ccnl_id, qual_id=qual_id))
    
    ccnl = filter_by_company(CCNLContract.query).filter_by(id=ccnl_id).first_or_404()
    qualification = filter_by_company(CCNLQualification.query).filter_by(
        id=qual_id,
        ccnl_id=ccnl_id
    ).first_or_404()
    
    if request.method == 'POST':
        codice = request.form.get('codice', '').strip()
        descrizione = request.form.get('descrizione', '').strip()
        
        if not codice:
            flash('Il codice del livello è obbligatorio', 'danger')
            return render_template('ccnl/create_level.html', ccnl=ccnl, qualification=qualification)
        
        # Verifica duplicati
        existing = filter_by_company(CCNLLevel.query).filter_by(
            qualification_id=qual_id,
            codice=codice
        ).first()
        if existing:
            flash(f'Esiste già un livello con il codice "{codice}" per questa qualifica', 'warning')
            return render_template('ccnl/create_level.html', ccnl=ccnl, qualification=qualification)
        
        try:
            level = CCNLLevel(
                qualification_id=qual_id,
                codice=codice,
                descrizione=descrizione if descrizione else None
            )
            set_company_on_create(level)
            db.session.add(level)
            db.session.commit()
            
            flash(f'✅ Livello "{codice}" creato con successo', 'success')
            return redirect(url_for('ccnl.levels', ccnl_id=ccnl_id, qual_id=qual_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la creazione: {str(e)}', 'danger')
            return render_template('ccnl/create_level.html', ccnl=ccnl, qualification=qualification)
    
    return render_template('ccnl/create_level.html', ccnl=ccnl, qualification=qualification)

@ccnl_bp.route('/ccnl/<int:ccnl_id>/qualifications/<int:qual_id>/levels/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@require_ccnl_permission
def edit_level(ccnl_id, qual_id, id):
    """Modifica un livello esistente"""
    if not current_user.can_manage_ccnl():
        flash('Non hai i permessi per modificare livelli', 'danger')
        return redirect(url_for('ccnl.levels', ccnl_id=ccnl_id, qual_id=qual_id))
    
    ccnl = filter_by_company(CCNLContract.query).filter_by(id=ccnl_id).first_or_404()
    qualification = filter_by_company(CCNLQualification.query).filter_by(
        id=qual_id,
        ccnl_id=ccnl_id
    ).first_or_404()
    level = filter_by_company(CCNLLevel.query).filter_by(
        id=id,
        qualification_id=qual_id
    ).first_or_404()
    
    if request.method == 'POST':
        codice = request.form.get('codice', '').strip()
        descrizione = request.form.get('descrizione', '').strip()
        active = request.form.get('active') == 'on'
        
        if not codice:
            flash('Il codice del livello è obbligatorio', 'danger')
            return render_template('ccnl/edit_level.html', ccnl=ccnl, qualification=qualification, level=level)
        
        # Verifica duplicati (escluso il livello corrente)
        existing = filter_by_company(CCNLLevel.query).filter(
            CCNLLevel.qualification_id == qual_id,
            CCNLLevel.codice == codice,
            CCNLLevel.id != id
        ).first()
        if existing:
            flash(f'Esiste già un altro livello con il codice "{codice}"', 'warning')
            return render_template('ccnl/edit_level.html', ccnl=ccnl, qualification=qualification, level=level)
        
        try:
            level.codice = codice
            level.descrizione = descrizione if descrizione else None
            level.active = active
            db.session.commit()
            
            flash(f'✅ Livello "{codice}" modificato con successo', 'success')
            return redirect(url_for('ccnl.levels', ccnl_id=ccnl_id, qual_id=qual_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la modifica: {str(e)}', 'danger')
            return render_template('ccnl/edit_level.html', ccnl=ccnl, qualification=qualification, level=level)
    
    return render_template('ccnl/edit_level.html', ccnl=ccnl, qualification=qualification, level=level)

@ccnl_bp.route('/ccnl/<int:ccnl_id>/qualifications/<int:qual_id>/levels/<int:id>/delete', methods=['POST'])
@login_required
@require_ccnl_permission
def delete_level(ccnl_id, qual_id, id):
    """Elimina un livello"""
    if not current_user.can_manage_ccnl():
        flash('Non hai i permessi per eliminare livelli', 'danger')
        return redirect(url_for('ccnl.levels', ccnl_id=ccnl_id, qual_id=qual_id))
    
    level = filter_by_company(CCNLLevel.query).filter_by(
        id=id,
        qualification_id=qual_id
    ).first_or_404()
    
    try:
        codice = level.codice
        db.session.delete(level)
        db.session.commit()
        
        flash(f'✅ Livello "{codice}" eliminato con successo', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante l\'eliminazione: {str(e)}', 'danger')
    
    return redirect(url_for('ccnl.levels', ccnl_id=ccnl_id, qual_id=qual_id))

@ccnl_bp.route('/ccnl/<int:ccnl_id>/qualifications/<int:qual_id>/levels/<int:id>/toggle', methods=['POST'])
@login_required
@require_ccnl_permission
def toggle_level(ccnl_id, qual_id, id):
    """Attiva/disattiva un livello"""
    if not current_user.can_manage_ccnl():
        flash('Non hai i permessi per modificare livelli', 'danger')
        return redirect(url_for('ccnl.levels', ccnl_id=ccnl_id, qual_id=qual_id))
    
    level = filter_by_company(CCNLLevel.query).filter_by(
        id=id,
        qualification_id=qual_id
    ).first_or_404()
    
    try:
        level.active = not level.active
        db.session.commit()
        
        stato = "attivato" if level.active else "disattivato"
        flash(f'✅ Livello "{level.codice}" {stato} con successo', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Errore: {str(e)}', 'danger')
    
    return redirect(url_for('ccnl.levels', ccnl_id=ccnl_id, qual_id=qual_id))

# =============================================================================
# API ENDPOINTS - per dropdown a cascata nel form HR
# =============================================================================

@ccnl_bp.route('/api/ccnl/<int:ccnl_id>/qualifications')
@login_required
def api_qualifications(ccnl_id):
    """API JSON per ottenere le qualifiche di un CCNL"""
    qualifications = filter_by_company(CCNLQualification.query).filter_by(
        ccnl_id=ccnl_id,
        active=True
    ).order_by(CCNLQualification.nome).all()
    
    return jsonify([
        {
            'id': q.id,
            'nome': q.nome,
            'descrizione': q.descrizione
        }
        for q in qualifications
    ])

@ccnl_bp.route('/api/qualifications/<int:qual_id>/levels')
@login_required
def api_levels(qual_id):
    """API JSON per ottenere i livelli di una qualifica"""
    levels = filter_by_company(CCNLLevel.query).filter_by(
        qualification_id=qual_id,
        active=True
    ).order_by(CCNLLevel.codice).all()
    
    return jsonify([
        {
            'id': l.id,
            'codice': l.codice,
            'descrizione': l.descrizione
        }
        for l in levels
    ])
