# =============================================================================
# EXPENSE BLUEPRINT - Modulo gestione note spese
# =============================================================================
#
# ROUTES INCLUSE:
# 1. note_spese (GET) - Lista note spese con filtri
# 2. create_expense_note (GET/POST) - Creazione nuova nota spese
# 3. edit_expense_note/<note_id> (GET/POST) - Modifica nota spese
# 4. delete_expense_note/<note_id> (POST) - Eliminazione nota spese
# 5. approve_expense_note/<note_id> (POST) - Approvazione nota spese
# 6. reject_expense_note/<note_id> (POST) - Rifiuto nota spese
# 7. export_expense_notes_excel (GET) - Export Excel note spese
#
# Total routes: 7+ expense management routes
# =============================================================================

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, make_response
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from functools import wraps
from app import db
from models import User, ExpenseNote, Sede, italian_now
import io
import csv

# Create blueprint
expense_bp = Blueprint('expense', __name__, url_prefix='/expense')

# Helper functions
def require_expense_permissions(f):
    """Decorator to require expense permissions for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not (current_user.can_view_my_expense_notes() or current_user.can_view_expense_notes() or current_user.can_create_expense_notes()):
            flash('Non hai i permessi per accedere alle note spese', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# EXPENSE MANAGEMENT ROUTES
# =============================================================================

@expense_bp.route('/note_spese')
@login_required
@require_expense_permissions
def note_spese():
    """Visualizza note spese con filtri"""
    # Controllo permessi per determinare la vista
    view = request.args.get('view', 'my')
    
    if view == 'approve' and not current_user.can_approve_expense_notes():
        flash('Non hai i permessi per approvare note spese', 'danger')
        return redirect(url_for('dashboard'))
    elif view == 'all' and not current_user.can_view_expense_notes():
        flash('Non hai i permessi per visualizzare tutte le note spese', 'danger')
        return redirect(url_for('dashboard'))
    elif view == 'my' and not current_user.can_view_my_expense_notes():
        flash('Non hai i permessi per visualizzare le tue note spese', 'danger')
        return redirect(url_for('dashboard'))
    
    # Base query
    query = ExpenseNote.query
    
    # Filtri per vista
    if view == 'my':
        # Solo le proprie note spese
        query = query.filter(ExpenseNote.user_id == current_user.id)
    elif view == 'approve':
        # Solo note pending per approvazione
        query = query.filter(ExpenseNote.status == 'Pending')
        
        # Se non è multi-sede, filtra per sede
        if not current_user.all_sedi and current_user.sede_obj:
            sede_users = User.query.filter_by(sede_id=current_user.sede_obj.id).all()
            user_ids = [u.id for u in sede_users]
            query = query.filter(ExpenseNote.user_id.in_(user_ids))
    elif view == 'all':
        # Tutte le note con controllo sede
        if not current_user.all_sedi and current_user.sede_obj:
            sede_users = User.query.filter_by(sede_id=current_user.sede_obj.id).all()
            user_ids = [u.id for u in sede_users]
            query = query.filter(ExpenseNote.user_id.in_(user_ids))
    
    # Filtri aggiuntivi
    status_filter = request.args.get('status')
    if status_filter and status_filter != 'all':
        query = query.filter(ExpenseNote.status == status_filter)
    
    month_filter = request.args.get('month')
    if month_filter:
        try:
            year, month = month_filter.split('-')
            query = query.filter(
                db.extract('year', ExpenseNote.expense_date) == int(year),
                db.extract('month', ExpenseNote.expense_date) == int(month)
            )
        except ValueError:
            pass
    
    # Ordinamento
    expense_notes = query.join(User, ExpenseNote.user_id == User.id).order_by(
        ExpenseNote.expense_date.desc()
    ).all()
    
    # Statistiche per dashboard
    stats = {}
    if view in ['approve', 'all']:
        stats = {
            'pending_count': ExpenseNote.query.filter_by(status='Pending').count(),
            'approved_count': ExpenseNote.query.filter_by(status='Approved').count(),
            'rejected_count': ExpenseNote.query.filter_by(status='Rejected').count(),
        }
    
    return render_template('note_spese.html',
                         expense_notes=expense_notes,
                         view=view,
                         stats=stats,
                         selected_status=status_filter,
                         selected_month=month_filter,
                         can_approve=current_user.can_approve_expense_notes(),
                         can_create=current_user.can_create_expense_notes())

@expense_bp.route('/create_expense_note', methods=['GET', 'POST'])
@login_required
def create_expense_note():
    """Crea nuova nota spese"""
    if not current_user.can_create_expense_notes():
        flash('Non hai i permessi per creare note spese', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            # Validazione dati base
            description = request.form.get('description', '').strip()
            amount = request.form.get('amount')
            expense_date_str = request.form.get('expense_date')
            
            if not all([description, amount, expense_date_str]):
                flash('Tutti i campi obbligatori devono essere compilati', 'danger')
                return render_template('create_expense_note.html', form_data=request.form)
            
            # Validazione importo
            try:
                amount_value = float(amount)
                if amount_value <= 0:
                    flash('L\'importo deve essere maggiore di zero', 'danger')
                    return render_template('create_expense_note.html', form_data=request.form)
            except ValueError:
                flash('Importo non valido', 'danger')
                return render_template('create_expense_note.html', form_data=request.form)
            
            # Validazione data
            try:
                expense_date = datetime.strptime(expense_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Data non valida', 'danger')
                return render_template('create_expense_note.html', form_data=request.form)
            
            # Crea nuova nota spese
            new_note = ExpenseNote()
            new_note.user_id = current_user.id
            new_note.description = description
            new_note.amount = amount_value
            new_note.expense_date = expense_date
            new_note.status = 'Pending'
            new_note.created_at = italian_now()
            
            # Categoria opzionale
            category = request.form.get('category')
            if category:
                new_note.category = category
            
            # Note aggiuntive
            notes = request.form.get('notes')
            if notes:
                new_note.notes = notes.strip()
            
            db.session.add(new_note)
            db.session.commit()
            
            flash('Nota spese creata correttamente', 'success')
            return redirect(url_for('expense.note_spese', view='my'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore nella creazione nota spese: {str(e)}', 'danger')
    
    return render_template('create_expense_note.html', 
                         form_data=request.form if request.method == 'POST' else {})

@expense_bp.route('/approve_expense_note/<int:note_id>', methods=['POST'])
@login_required
def approve_expense_note(note_id):
    """Approva nota spese"""
    if not current_user.can_approve_expense_notes():
        return jsonify({'success': False, 'message': 'Non hai i permessi per approvare note spese'}), 403
    
    try:
        expense_note = ExpenseNote.query.get_or_404(note_id)
        
        # Controllo sede se non multi-sede
        if not current_user.all_sedi:
            if (current_user.sede_obj and 
                expense_note.user.sede_id != current_user.sede_obj.id):
                return jsonify({'success': False, 'message': 'Non puoi approvare note spese di altre sedi'}), 403
        
        if expense_note.status != 'Pending':
            return jsonify({'success': False, 'message': 'La nota spese è già stata processata'}), 400
        
        expense_note.status = 'Approved'
        expense_note.approved_by_user_id = current_user.id
        expense_note.approved_at = italian_now()
        
        # Aggiungi note di approvazione se fornite
        approval_notes = request.form.get('approval_notes')
        if approval_notes:
            expense_note.approval_notes = approval_notes
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Nota spese di {expense_note.user.get_full_name()} approvata correttamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Errore: {str(e)}'}), 500

@expense_bp.route('/reject_expense_note/<int:note_id>', methods=['POST'])
@login_required
def reject_expense_note(note_id):
    """Rifiuta nota spese"""
    if not current_user.can_approve_expense_notes():
        return jsonify({'success': False, 'message': 'Non hai i permessi per rifiutare note spese'}), 403
    
    try:
        expense_note = ExpenseNote.query.get_or_404(note_id)
        
        # Controllo sede se non multi-sede
        if not current_user.all_sedi:
            if (current_user.sede_obj and 
                expense_note.user.sede_id != current_user.sede_obj.id):
                return jsonify({'success': False, 'message': 'Non puoi rifiutare note spese di altre sedi'}), 403
        
        if expense_note.status != 'Pending':
            return jsonify({'success': False, 'message': 'La nota spese è già stata processata'}), 400
        
        rejection_reason = request.form.get('rejection_reason')
        if not rejection_reason:
            return jsonify({'success': False, 'message': 'Motivo del rifiuto richiesto'}), 400
        
        expense_note.status = 'Rejected'
        expense_note.approved_by_user_id = current_user.id
        expense_note.approved_at = italian_now()
        expense_note.approval_notes = rejection_reason
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Nota spese di {expense_note.user.get_full_name()} rifiutata'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Errore: {str(e)}'}), 500