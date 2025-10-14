# =============================================================================
# PRESIDIO COVERAGE MANAGEMENT BLUEPRINT
# =============================================================================
#
# ROUTES INCLUSE:
# 1. manage_coverage (GET) - Redirect alla pagina principale presidio
# 2. view_presidio_coverage (GET) - Visualizza dettagli template copertura
# 3. edit_presidio_coverage (GET/POST) - Modifica template copertura 
# 4. presidio_coverage (GET/POST) - Pagina principale gestione coperture
# 5. presidio_coverage_edit (GET/POST) - Modifica template esistente
# 6. presidio_detail (GET) - Dettagli template
# 7. api_presidio_coverage (GET) - API per dati template
# 8. toggle_presidio_template_status (POST) - Attiva/disattiva template
# 9. delete_presidio_template (POST) - Elimina template (soft delete)
# 10. duplicate_presidio_template (POST) - Duplica template con coperture
#
# Total routes: 10 presidio coverage routes
# =============================================================================

from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, make_response
from flask_login import login_required, current_user
from datetime import datetime
from functools import wraps
import json
from app import db
from models import (
    PresidioCoverageTemplate, PresidioCoverage, italian_now, 
    get_active_presidio_templates, get_presidio_coverage_for_day
)
from sqlalchemy import and_
from forms import PresidioCoverageTemplateForm, PresidioCoverageForm, PresidioCoverageSearchForm
from utils_tenant import filter_by_company, set_company_on_create, get_user_company_id

# Create blueprint
presidio_bp = Blueprint('presidio', __name__)

# Helper functions
def require_presidio_permission(f):
    """Decorator to require presidio permissions for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not (current_user.can_manage_shifts() or current_user.can_view_coverage()):
            flash('Non hai i permessi per accedere alle coperture presidio', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# PRESIDIO COVERAGE MANAGEMENT ROUTES
# =============================================================================

@presidio_bp.route("/manage_coverage")
@login_required
@require_presidio_permission
def manage_coverage():
    """Gestione Coperture - Sistema completo basato su template"""
    if not current_user.can_manage_coverage():
        flash("Non hai i permessi per gestire le coperture", "danger")
        return redirect(url_for("dashboard.dashboard"))
    
    # Reindirizza alla nuova pagina del sistema presidio completo
    return redirect(url_for('presidio.presidio_coverage'))

@presidio_bp.route("/view_presidio_coverage/<period_key>")
@login_required
@require_presidio_permission
def view_presidio_coverage(period_key):
    """Visualizza dettagli template copertura presidio"""
    if not current_user.can_view_coverage():
        flash("Non hai i permessi per visualizzare le coperture", "danger")
        return redirect(url_for("dashboard.dashboard"))
    
    try:
        # Decodifica period_key per ottenere le date
        start_str, end_str = period_key.split('-')
        start_date = datetime.strptime(start_str, '%Y%m%d').date()
        end_date = datetime.strptime(end_str, '%Y%m%d').date()
    except (ValueError, AttributeError):
        flash('Periodo non valido specificato', 'danger')
        return redirect(url_for('presidio.manage_coverage'))
    
    # Ottieni tutte le coperture del template (with company filter)
    coverages = filter_by_company(PresidioCoverage.query).filter(
        PresidioCoverage.start_date == start_date,
        PresidioCoverage.end_date == end_date,
        PresidioCoverage.active == True
    ).order_by(PresidioCoverage.day_of_week, PresidioCoverage.start_time).all()
    
    if not coverages:
        flash('Template di copertura non trovato', 'danger')
        return redirect(url_for('presidio.manage_coverage'))
    
    return render_template("view_presidio_coverage.html",
                         coverages=coverages,
                         start_date=start_date,
                         end_date=end_date,
                         period_key=period_key)

@presidio_bp.route("/edit_presidio_coverage/<period_key>", methods=['GET', 'POST'])
@login_required
@require_presidio_permission
def edit_presidio_coverage(period_key):
    """Modifica template copertura presidio"""
    if not current_user.can_manage_coverage():
        flash("Non hai i permessi per modificare le coperture", "danger")
        return redirect(url_for("dashboard.dashboard"))
    
    try:
        # Decodifica period_key per ottenere le date
        start_str, end_str = period_key.split('-')
        start_date = datetime.strptime(start_str, '%Y%m%d').date()
        end_date = datetime.strptime(end_str, '%Y%m%d').date()
    except (ValueError, AttributeError):
        flash('Periodo non valido specificato', 'danger')
        return redirect(url_for('presidio.manage_coverage'))
    
    # Ottieni tutte le coperture del template (with company filter)
    coverages = filter_by_company(PresidioCoverage.query).filter(
        PresidioCoverage.start_date == start_date,
        PresidioCoverage.end_date == end_date
    ).order_by(PresidioCoverage.day_of_week, PresidioCoverage.start_time).all()
    
    if not coverages:
        flash('Template di copertura non trovato', 'danger')
        return redirect(url_for('presidio.manage_coverage'))
    
    # Gestisce POST per salvare le modifiche
    if request.method == 'POST':
        try:
            success_count = 0
            error_count = 0
            
            for coverage in coverages:
                coverage_id = coverage.id
                
                # Controlla se deve essere eliminata
                if request.form.get(f'coverage_{coverage_id}_delete'):
                    db.session.delete(coverage)
                    success_count += 1
                    continue
                
                # Aggiorna campi modificabili
                coverage.start_time = datetime.strptime(request.form.get(f'coverage_{coverage_id}_start_time'), '%H:%M').time()
                coverage.end_time = datetime.strptime(request.form.get(f'coverage_{coverage_id}_end_time'), '%H:%M').time()
                coverage.role_count = int(request.form.get(f'coverage_{coverage_id}_role_count', 1))
                coverage.description = request.form.get(f'coverage_{coverage_id}_description', '')
                success_count += 1
            
            db.session.commit()
            flash(f'{success_count} coperture aggiornate con successo', 'success')
            if error_count > 0:
                flash(f'{error_count} coperture non aggiornate per errori', 'warning')
                
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante l\'aggiornamento: {str(e)}', 'danger')
        
        return redirect(url_for('presidio.edit_presidio_coverage', period_key=period_key))
    
    return render_template("edit_presidio_coverage.html",
                         coverages=coverages,
                         start_date=start_date,
                         end_date=end_date,
                         period_key=period_key)

@presidio_bp.route('/presidio_coverage', methods=['GET', 'POST'])
@login_required
@require_presidio_permission
def presidio_coverage():
    """Pagina principale per gestione copertura presidio - Sistema completo"""
    if not current_user.can_manage_shifts():
        flash('Non hai i permessi per gestire coperture presidio', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    # Ottieni tutti i template di copertura presidio ordinati per data creazione
    templates = get_active_presidio_templates()
    
    # Form per nuovo template
    form = PresidioCoverageTemplateForm()
    search_form = PresidioCoverageSearchForm()
    current_template = None
    
    # Applica filtri di ricerca se presenti
    if request.args.get('search'):
        query = filter_by_company(PresidioCoverageTemplate.query).filter_by(active=True)
        
        template_name = request.args.get('template_name')
        if template_name:
            query = query.filter(PresidioCoverageTemplate.name.ilike(f"%{template_name}%"))
        
        date_from = request.args.get('date_from')
        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                query = query.filter(PresidioCoverageTemplate.start_date >= date_from)
            except ValueError:
                pass
        
        date_to = request.args.get('date_to')
        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                query = query.filter(PresidioCoverageTemplate.end_date <= date_to)
            except ValueError:
                pass
        
        active_arg = request.args.get('active')
        if active_arg:
            active_bool = active_arg == 'true'
            query = query.filter(PresidioCoverageTemplate.active == active_bool)
        
        templates = query.order_by(PresidioCoverageTemplate.created_at.desc()).all()
    
    # Gestisci creazione/modifica template
    if request.method == 'POST':
        action = request.form.get('action', 'create')
        
        if action == 'create' and form.validate_on_submit():
            template = PresidioCoverageTemplate()
            template.name = form.name.data
            template.start_date = form.start_date.data
            template.end_date = form.end_date.data
            template.description = form.description.data
            template.sede_id = form.sede_id.data
            template.created_by = current_user.id
            
            db.session.add(template)
            db.session.commit()
            flash(f'Template "{template.name}" creato con successo', 'success')
            return redirect(url_for('presidio.presidio_coverage_edit', template_id=template.id))
    
    return render_template('presidio_coverage.html', 
                         templates=templates,
                         form=form,
                         search_form=search_form,
                         current_template=current_template)

@presidio_bp.route('/presidio_coverage_edit/<int:template_id>', methods=['GET', 'POST'])
@login_required
@require_presidio_permission
def presidio_coverage_edit(template_id):
    """Modifica template esistente - Sistema completo"""
    if not current_user.can_manage_shifts():
        flash('Non hai i permessi per gestire coperture presidio', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    current_template = filter_by_company(PresidioCoverageTemplate.query).filter_by(id=template_id).first_or_404()
    templates = get_active_presidio_templates()
    
    # Pre-popola form con dati template
    form = PresidioCoverageTemplateForm()
    coverage_form = PresidioCoverageForm()
    
    if request.method == 'GET':
        form.name.data = current_template.name
        form.start_date.data = current_template.start_date
        form.end_date.data = current_template.end_date
        form.description.data = current_template.description
        form.sede_id.data = current_template.sede_id
    
    if request.method == 'POST':
        action = request.form.get('action', 'update')
        
        if action == 'update' and form.validate_on_submit():
            current_template.name = form.name.data
            current_template.start_date = form.start_date.data
            current_template.end_date = form.end_date.data
            current_template.description = form.description.data
            current_template.sede_id = form.sede_id.data
            db.session.commit()
            flash(f'Template "{current_template.name}" aggiornato con successo', 'success')
            return redirect(url_for('presidio.presidio_coverage_edit', template_id=template_id))
        
        elif action == 'add_coverage' and coverage_form.validate_on_submit():
            # Aggiungi nuove coperture per i giorni selezionati
            success_count = 0
            error_count = 0
            
            for day_of_week in coverage_form.days_of_week.data:
                # Crea nuova copertura
                new_coverage = PresidioCoverage()
                new_coverage.template_id = template_id
                new_coverage.day_of_week = day_of_week
                new_coverage.start_time = coverage_form.start_time.data
                new_coverage.end_time = coverage_form.end_time.data
                new_coverage.required_roles = json.dumps(coverage_form.required_roles.data)
                new_coverage.role_count = coverage_form.role_count.data
                new_coverage.description = coverage_form.description.data
                new_coverage.active = coverage_form.active.data
                new_coverage.start_date = current_template.start_date
                new_coverage.end_date = current_template.end_date
                new_coverage.created_by = current_user.id
                
                # Gestione pause opzionali
                if coverage_form.break_start.data and coverage_form.break_end.data:
                    try:
                        new_coverage.break_start = datetime.strptime(coverage_form.break_start.data, '%H:%M').time()
                        new_coverage.break_end = datetime.strptime(coverage_form.break_end.data, '%H:%M').time()
                    except ValueError:
                        pass  # Ignora errori di parsing per campi opzionali
                
                db.session.add(new_coverage)
                success_count += 1
            
            db.session.commit()
            
            if success_count > 0:
                flash(f'{success_count} coperture aggiunte con successo', 'success')
            if error_count > 0:
                flash(f'{error_count} coperture non aggiunte per sovrapposizioni orarie', 'warning')
            
            return redirect(url_for('presidio.presidio_coverage_edit', template_id=template_id))
    
    return render_template('presidio_coverage.html', 
                         templates=templates,
                         form=form,
                         coverage_form=coverage_form,
                         current_template=current_template)

@presidio_bp.route('/presidio_detail/<int:template_id>')
@login_required
@require_presidio_permission
def presidio_detail(template_id):
    """Dettagli template presidio"""
    template = filter_by_company(PresidioCoverageTemplate.query).filter_by(id=template_id).first_or_404()
    return render_template('presidio_detail.html', template=template)

@presidio_bp.route('/api/presidio_coverage/<int:template_id>')
@login_required
@require_presidio_permission
def api_presidio_coverage(template_id):
    """API per ottenere dati template presidio"""
    template = filter_by_company(PresidioCoverageTemplate.query).filter_by(id=template_id).first_or_404()
    
    # Prepara dati coperture
    coverages = []
    for coverage in template.coverages.filter_by(active=True):
        coverages.append({
            'id': coverage.id,
            'day_of_week': coverage.day_of_week,
            'start_time': coverage.start_time.strftime('%H:%M'),
            'end_time': coverage.end_time.strftime('%H:%M'),
            'required_roles': json.loads(coverage.required_roles) if coverage.required_roles else [],
            'role_count': coverage.role_count,
            'description': coverage.description or ''
        })
    
    return jsonify({
        'success': True,
        'template_name': template.name,
        'start_date': template.start_date.strftime('%Y-%m-%d'),
        'end_date': template.end_date.strftime('%Y-%m-%d'),
        'period': template.get_period_display(),
        'coverages': coverages
    })

@presidio_bp.route('/presidio_coverage/toggle_status/<int:template_id>', methods=['POST'])
@login_required
@require_presidio_permission
def toggle_presidio_template_status(template_id):
    """Attiva/disattiva template presidio"""
    if not current_user.can_manage_shifts():
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403
    
    template = filter_by_company(PresidioCoverageTemplate.query).filter_by(id=template_id).first_or_404()
    new_status = request.json.get('active', not template.active)
    
    template.active = new_status
    template.updated_at = italian_now()
    
    # Aggiorna anche tutte le coperture associate
    for coverage in template.coverages:
        coverage.active = new_status
    
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': f'Template {"attivato" if new_status else "disattivato"} con successo'
    })

@presidio_bp.route('/presidio_coverage/delete/<int:template_id>', methods=['POST'])
@login_required
@require_presidio_permission
def delete_presidio_template(template_id):
    """Elimina template presidio (soft delete)"""
    if not current_user.can_manage_shifts():
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403
    
    template = filter_by_company(PresidioCoverageTemplate.query).filter_by(id=template_id).first_or_404()
    
    # Soft delete del template e di tutte le coperture
    template.active = False
    coverages_count = 0
    for coverage in template.coverages:
        coverage.active = False
        coverages_count += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Template "{template.name}" eliminato ({coverages_count} coperture)'
    })

@presidio_bp.route('/presidio_coverage/duplicate/<int:template_id>', methods=['POST'])
@login_required
@require_presidio_permission
def duplicate_presidio_template(template_id):
    """Duplica template presidio con tutte le coperture"""
    if not current_user.can_manage_shifts():
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403
    
    source_template = filter_by_company(PresidioCoverageTemplate.query).filter_by(id=template_id).first_or_404()
    
    # Crea nuovo template
    new_template = PresidioCoverageTemplate()
    new_template.name = f"{source_template.name} (Copia)"
    new_template.start_date = source_template.start_date
    new_template.end_date = source_template.end_date
    new_template.description = f"Copia di: {source_template.description}" if source_template.description else None
    new_template.created_by = current_user.id
    set_company_on_create(new_template)
    
    db.session.add(new_template)
    db.session.flush()  # Per ottenere l'ID
    
    # Duplica tutte le coperture
    coverages_count = 0
    for coverage in source_template.coverages.filter_by(active=True):
        new_coverage = PresidioCoverage()
        new_coverage.template_id = new_template.id
        new_coverage.day_of_week = coverage.day_of_week
        new_coverage.start_time = coverage.start_time
        new_coverage.end_time = coverage.end_time
        new_coverage.required_roles = coverage.required_roles
        new_coverage.role_count = coverage.role_count
        new_coverage.description = coverage.description
        new_coverage.sede_id = coverage.sede_id
        new_coverage.shift_type = coverage.shift_type
        
        db.session.add(new_coverage)
        coverages_count += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Template duplicato: "{new_template.name}" ({coverages_count} coperture)',
        'new_template_id': new_template.id
    })