# =============================================================================
# HOLIDAY MANAGEMENT ROUTES BLUEPRINT  
# Holiday creation, editing, deletion and automatic generation
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date

from app import db
from models import Holiday, italian_now
from forms import HolidayForm
from utils_tenant import filter_by_company, set_company_on_create, get_user_company_id

# Create blueprint
holidays_bp = Blueprint('holidays', __name__, url_prefix='/holidays')

@holidays_bp.route('/')
@login_required
def holidays():
    """Holiday management page"""
    # Check permissions
    if not current_user.can_access_holidays():
        flash('Non hai i permessi per accedere alle festività.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    holidays = filter_by_company(Holiday.query).order_by(Holiday.month.desc(), Holiday.day.desc()).all()
    return render_template('holidays.html', holidays=holidays)

@holidays_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_holiday():
    """Add new holiday"""
    if not current_user.can_manage_holidays():
        flash('Non hai i permessi per gestire le festività.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    form = HolidayForm()
    if form.validate_on_submit():
        # Check if holiday already exists for this month/day and scope (with company filter)
        sede_id = form.sede_id.data if form.sede_id.data else None
        existing = filter_by_company(Holiday.query).filter_by(
            month=form.month.data,
            day=form.day.data,
            sede_id=sede_id,
            active=True
        ).first()
        
        if existing:
            scope = existing.scope_display if hasattr(existing, 'scope_display') else ('Nazionale' if existing.sede_id is None else f'Sede {existing.sede_id}')
            flash(f'Esiste già una festività attiva il {form.day.data}/{form.month.data} per {scope}: {existing.name}', 'warning')
            return render_template('add_holiday.html', form=form)
        
        holiday = Holiday()
        holiday.name = form.name.data
        holiday.month = form.month.data
        holiday.day = form.day.data
        holiday.sede_id = sede_id
        holiday.description = form.description.data
        holiday.active = form.active.data
        holiday.created_by = current_user.id
        holiday.created_at = italian_now()
        set_company_on_create(holiday)
        
        db.session.add(holiday)
        db.session.commit()
        flash(f'Festività "{holiday.name}" aggiunta con successo.', 'success')
        return redirect(url_for('holidays.holidays'))
    
    return render_template('add_holiday.html', form=form)

@holidays_bp.route('/edit/<int:holiday_id>', methods=['GET', 'POST'])
@login_required
def edit_holiday(holiday_id):
    """Edit existing holiday"""
    if not current_user.can_manage_holidays():
        flash('Non hai i permessi per gestire le festività.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    holiday = filter_by_company(Holiday.query).filter_by(id=holiday_id).first_or_404()
    form = HolidayForm(obj=holiday)
    
    if form.validate_on_submit():
        # Check if another holiday exists for this month/day and scope (excluding current, with company filter)
        sede_id = form.sede_id.data if form.sede_id.data else None
        existing = filter_by_company(Holiday.query).filter(
            Holiday.month == form.month.data,
            Holiday.day == form.day.data,
            Holiday.sede_id == sede_id,
            Holiday.active == True,
            Holiday.id != holiday_id
        ).first()
        
        if existing:
            scope = existing.scope_display if hasattr(existing, 'scope_display') else ('Nazionale' if existing.sede_id is None else f'Sede {existing.sede_id}')
            flash(f'Esiste già una festività attiva il {form.day.data}/{form.month.data} per {scope}: {existing.name}', 'warning')
            return render_template('edit_holiday.html', form=form, holiday=holiday)
        
        holiday.name = form.name.data
        holiday.month = form.month.data
        holiday.day = form.day.data
        holiday.sede_id = sede_id
        holiday.description = form.description.data
        holiday.active = form.active.data
        
        db.session.commit()
        flash(f'Festività "{holiday.name}" aggiornata con successo.', 'success')
        return redirect(url_for('holidays.holidays'))
    
    return render_template('edit_holiday.html', form=form, holiday=holiday)

@holidays_bp.route('/delete/<int:holiday_id>', methods=['POST'])
@login_required
def delete_holiday(holiday_id):
    """Delete holiday"""
    if not current_user.can_manage_holidays():
        flash('Non hai i permessi per gestire le festività.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    holiday = filter_by_company(Holiday.query).filter_by(id=holiday_id).first_or_404()
    
    try:
        db.session.delete(holiday)
        db.session.commit()
        flash(f'Festività "{holiday.name}" eliminata con successo.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Errore durante l\'eliminazione della festività.', 'danger')
    
    return redirect(url_for('holidays.holidays'))

# API endpoint for automatic holiday generation
@holidays_bp.route('/api/generate', methods=['POST'])
@login_required
def api_generate_holidays():
    """Generate standard Italian national holidays for current year"""
    if not current_user.can_manage_holidays():
        return jsonify({'success': False, 'message': 'Permessi insufficienti'}), 403
    
    current_year = datetime.now().year
    
    # Standard Italian national holidays
    standard_holidays = [
        ('Capodanno', f'{current_year}-01-01'),
        ('Epifania', f'{current_year}-01-06'), 
        ('Festa della Liberazione', f'{current_year}-04-25'),
        ('Festa del Lavoro', f'{current_year}-05-01'),
        ('Festa della Repubblica', f'{current_year}-06-02'),
        ('Ferragosto', f'{current_year}-08-15'),
        ('Ognissanti', f'{current_year}-11-01'),
        ('Immacolata Concezione', f'{current_year}-12-08'),
        ('Natale', f'{current_year}-12-25'),
        ('Santo Stefano', f'{current_year}-12-26')
    ]
    
    created_count = 0
    skipped_count = 0
    
    try:
        for name, date_str in standard_holidays:
            holiday_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Check if holiday already exists (national holiday with same month/day, with company filter)
            existing = filter_by_company(Holiday.query).filter_by(
                month=holiday_date.month,
                day=holiday_date.day,
                sede_id=None,  # National holiday
                active=True
            ).first()
            if existing:
                skipped_count += 1
                continue
            
            holiday = Holiday()
            holiday.name = name
            holiday.month = holiday_date.month
            holiday.day = holiday_date.day
            holiday.sede_id = None  # National holiday
            holiday.description = 'Festività nazionale'
            holiday.active = True
            holiday.created_by = current_user.id
            holiday.created_at = italian_now()
            set_company_on_create(holiday)
            
            db.session.add(holiday)
            created_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Generate {created_count} festività, {skipped_count} già esistenti',
            'created': created_count,
            'skipped': skipped_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Errore durante la generazione'}), 500