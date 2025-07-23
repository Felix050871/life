# Presidio Routes - Gestione Copertura Presidio
# Estratto dal sistema completo per implementazione standalone

from flask import request, render_template, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
from models import PresidioCoverageTemplate, PresidioCoverage, User, db
from forms import PresidioCoverageTemplateForm, PresidioCoverageForm

@app.route('/presidio_coverage')
@login_required
def presidio_coverage():
    """Pagina principale per gestione copertura presidio"""
    if not current_user.can_manage_shifts():
        flash('Non hai i permessi per gestire coperture presidio', 'danger')
        return redirect(url_for('dashboard'))
    
    # Ottieni tutti i template di copertura presidio ordinati per data creazione
    templates = PresidioCoverageTemplate.query.filter_by(is_active=True).order_by(
        PresidioCoverageTemplate.created_at.desc()
    ).all()
    
    # Form per nuovo template
    form = PresidioCoverageTemplateForm()
    available_coverages = templates  # Per selezione copertura in turnazioni
    current_template = None
    
    # Gestisci creazione/modifica template
    if request.method == 'POST':
        action = request.form.get('action', 'create')
        
        if action == 'create' and form.validate_on_submit():
            template = PresidioCoverageTemplate(
                name=form.name.data,
                start_date=form.start_date.data,
                end_date=form.end_date.data,
                description=form.description.data,
                created_by=current_user.id
            )
            db.session.add(template)
            db.session.commit()
            flash(f'Template "{template.name}" creato con successo', 'success')
            return redirect(url_for('presidio_coverage', template_id=template.id))
    
    return render_template('presidio_coverage.html', 
                         templates=templates,
                         form=form,
                         available_coverages=available_coverages,
                         current_template=current_template)

@app.route('/presidio_coverage/<int:template_id>')
@login_required 
def presidio_coverage_edit(template_id):
    """Modifica template esistente"""
    if not current_user.can_manage_shifts():
        flash('Non hai i permessi per gestire coperture presidio', 'danger')
        return redirect(url_for('dashboard'))
    
    current_template = PresidioCoverageTemplate.query.get_or_404(template_id)
    templates = PresidioCoverageTemplate.query.filter_by(is_active=True).order_by(
        PresidioCoverageTemplate.created_at.desc()
    ).all()
    
    # Pre-popola form con dati template
    form = PresidioCoverageTemplateForm()
    if request.method == 'GET':
        form.name.data = current_template.name
        form.start_date.data = current_template.start_date
        form.end_date.data = current_template.end_date
        form.description.data = current_template.description
    
    if request.method == 'POST':
        action = request.form.get('action', 'update')
        
        if action == 'update' and form.validate_on_submit():
            current_template.name = form.name.data
            current_template.start_date = form.start_date.data
            current_template.end_date = form.end_date.data
            current_template.description = form.description.data
            db.session.commit()
            flash(f'Template "{current_template.name}" aggiornato con successo', 'success')
            return redirect(url_for('presidio_coverage'))
        
        elif action == 'duplicate' and form.validate_on_submit():
            # Duplica template con nuovo nome
            new_template = PresidioCoverageTemplate(
                name=form.name.data,
                start_date=form.start_date.data,
                end_date=form.end_date.data,
                description=form.description.data,
                created_by=current_user.id
            )
            db.session.add(new_template)
            db.session.flush()  # Per ottenere l'ID
            
            # Duplica tutte le coperture
            for coverage in current_template.coverages:
                new_coverage = PresidioCoverage(
                    template_id=new_template.id,
                    day_of_week=coverage.day_of_week,
                    start_time=coverage.start_time,
                    end_time=coverage.end_time,
                    required_roles=coverage.required_roles,
                    description=coverage.description
                )
                db.session.add(new_coverage)
            
            db.session.commit()
            flash(f'Template duplicato come "{new_template.name}"', 'success')
            return redirect(url_for('presidio_coverage'))
    
    return render_template('presidio_coverage.html',
                         templates=templates,
                         form=form,
                         current_template=current_template,
                         available_coverages=templates)

@app.route('/presidio_detail/<int:template_id>')
@login_required
def presidio_detail(template_id):
    """Visualizza dettagli di un template di copertura presidio"""
    template = PresidioCoverageTemplate.query.get_or_404(template_id)
    
    return render_template('presidio_detail.html', 
                         template=template)

@app.route('/view_presidi')
@login_required
def view_presidi():
    """Visualizzazione sola lettura dei presidi configurati"""
    templates = PresidioCoverageTemplate.query.filter_by(is_active=True).order_by(PresidioCoverageTemplate.start_date.desc()).all()
    return render_template('view_presidi.html', templates=templates)

@app.route('/api/presidio_coverage/<int:template_id>')
@login_required
def api_presidio_coverage(template_id):
    """API per ottenere dettagli copertura presidio"""
    template = PresidioCoverageTemplate.query.get_or_404(template_id)
    
    coverages = []
    for coverage in template.coverages.filter_by(is_active=True):
        coverages.append({
            'id': coverage.id,
            'day_of_week': coverage.day_of_week,
            'start_time': coverage.start_time.strftime('%H:%M'),
            'end_time': coverage.end_time.strftime('%H:%M'),
            'required_roles': coverage.get_required_roles()
        })
    
    return jsonify({
        'success': True,
        'template_name': template.name,
        'start_date': template.start_date.strftime('%Y-%m-%d'),
        'end_date': template.end_date.strftime('%Y-%m-%d'),
        'period': f"{template.start_date.strftime('%d/%m/%Y')} - {template.end_date.strftime('%d/%m/%Y')}",
        'coverages': coverages
    })

@app.route('/presidio_coverage/toggle_status/<int:template_id>', methods=['POST'])
@login_required
def toggle_presidio_template_status(template_id):
    """Attiva/disattiva template presidio"""
    if not current_user.can_manage_shifts():
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403
    
    template = PresidioCoverageTemplate.query.get_or_404(template_id)
    new_status = request.json.get('is_active', True)
    
    template.is_active = new_status
    
    # Aggiorna anche tutte le coperture associate
    for coverage in template.coverages:
        coverage.is_active = new_status
    
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': f'Template {"attivato" if new_status else "disattivato"} con successo'
    })

@app.route('/presidio_coverage/delete/<int:template_id>', methods=['POST'])
@login_required
def delete_presidio_template(template_id):
    """Elimina template presidio (soft delete)"""
    if not current_user.can_manage_shifts():
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403
    
    template = PresidioCoverageTemplate.query.get_or_404(template_id)
    
    # Soft delete del template e di tutte le coperture
    template.is_active = False
    coverages_count = 0
    for coverage in template.coverages:
        coverage.is_active = False
        coverages_count += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Template "{template.name}" eliminato ({coverages_count} coperture)'
    })

# Funzioni di utilità per il calcolo delle coperture
def get_presidio_coverage_for_period(start_date, end_date):
    """Ottieni coperture presidio valide per un periodo"""
    templates = PresidioCoverageTemplate.query.filter(
        PresidioCoverageTemplate.is_active == True,
        PresidioCoverageTemplate.start_date <= end_date,
        PresidioCoverageTemplate.end_date >= start_date
    ).all()
    
    all_coverages = []
    for template in templates:
        for coverage in template.coverages.filter_by(is_active=True):
            all_coverages.append(coverage)
    
    return all_coverages

def get_required_roles_for_day_time(day_of_week, time_slot):
    """Ottieni ruoli richiesti per un giorno e orario specifico"""
    coverages = PresidioCoverage.query.filter(
        PresidioCoverage.is_active == True,
        PresidioCoverage.day_of_week == day_of_week,
        PresidioCoverage.start_time <= time_slot,
        PresidioCoverage.end_time > time_slot
    ).all()
    
    required_roles = set()
    for coverage in coverages:
        required_roles.update(coverage.get_required_roles())
    
    return list(required_roles)