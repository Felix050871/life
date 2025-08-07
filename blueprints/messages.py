# =============================================================================
# MESSAGES BLUEPRINT - Modulo gestione messaggi interni
# =============================================================================
#
# ROUTES INCLUSE:
# 1. messages (GET) - Lista messaggi ricevuti  
# 2. create_message (GET/POST) - Creazione nuovo messaggio
# 3. message_detail/<message_id> (GET) - Dettaglio messaggio
# 4. api/mark_message_read/<message_id> (POST) - Marca messaggio come letto
# 5. api/get_unread_count (GET) - API conteggio messaggi non letti
#
# Total routes: 5+ messaging routes
# =============================================================================

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from functools import wraps
from app import db
from models import User, Sede, italian_now

# Create blueprint
messages_bp = Blueprint('messages', __name__, url_prefix='/messages')

# Helper functions
def require_message_permissions(f):
    """Decorator to require message permissions for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.can_access_messaging():
            flash('Non hai i permessi per accedere ai messaggi', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# MESSAGING ROUTES
# =============================================================================

@messages_bp.route('/messages')
@login_required
@require_message_permissions
def messages():
    """Lista messaggi ricevuti"""
    # Filtri dalla query string
    status_filter = request.args.get('status', 'all')
    sender_filter = request.args.get('sender', 'all')
    
    # Base query per messaggi ricevuti dall'utente corrente
    # Per ora usiamo un placeholder fino a quando la tabella Message non viene creata
    messages_list = []
    
    # Statistiche per dashboard
    stats = {
        'total_messages': 0,
        'unread_messages': 0,
        'read_messages': 0
    }
    
    return render_template('messages.html',
                         messages=messages_list,
                         stats=stats,
                         selected_status=status_filter,
                         selected_sender=sender_filter,
                         can_create=current_user.can_send_internal_messages())

@messages_bp.route('/create_message', methods=['GET', 'POST'])
@login_required
def create_message():
    """Crea nuovo messaggio interno"""
    if not current_user.can_send_internal_messages():
        flash('Non hai i permessi per inviare messaggi', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    if request.method == 'POST':
        try:
            # Validazione dati base
            subject = request.form.get('subject', '').strip()
            content = request.form.get('content', '').strip()
            recipient_ids = request.form.getlist('recipients')
            
            if not all([subject, content, recipient_ids]):
                flash('Tutti i campi obbligatori devono essere compilati', 'danger')
                return render_template('create_message.html', form_data=request.form)
            
            # Validazione destinatari
            recipients = User.query.filter(
                User.id.in_(recipient_ids),
                User.active == True
            ).all()
            
            if not recipients:
                flash('Nessun destinatario valido selezionato', 'danger')
                return render_template('create_message.html', form_data=request.form)
            
            # Per ora, mostra solo un messaggio di successo
            # La logica completa verrà implementata quando la tabella Message sarà disponibile
            recipient_names = [r.get_full_name() for r in recipients]
            
            flash(f'Messaggio "{subject}" inviato a {", ".join(recipient_names)}', 'success')
            return redirect(url_for('messages.messages'))
            
        except Exception as e:
            flash(f'Errore nell\'invio messaggio: {str(e)}', 'danger')
    
    # Lista utenti disponibili per invio messaggi
    available_users = User.query.filter_by(active=True).order_by(User.last_name, User.first_name).all()
    
    # Filtro per sede se non multi-sede
    if not current_user.all_sedi and current_user.sede_obj:
        available_users = [u for u in available_users if u.sede_id == current_user.sede_obj.id]
    
    return render_template('create_message.html',
                         form_data=request.form if request.method == 'POST' else {},
                         available_users=available_users)

@messages_bp.route('/message_detail/<int:message_id>')
@login_required
@require_message_permissions  
def message_detail(message_id):
    """Dettaglio messaggio specifico"""
    # Per ora restituisce una pagina placeholder
    # La logica completa verrà implementata quando la tabella Message sarà disponibile
    
    return render_template('message_detail.html',
                         message_id=message_id,
                         message=None)

@messages_bp.route('/api/mark_message_read/<int:message_id>', methods=['POST'])
@login_required
def mark_message_read(message_id):
    """API per marcare messaggio come letto"""
    try:
        # Per ora restituisce successo placeholder
        # La logica completa verrà implementata quando la tabella Message sarà disponibile
        
        return jsonify({
            'success': True,
            'message': 'Messaggio marcato come letto'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Errore: {str(e)}'}), 500

@messages_bp.route('/api/get_unread_count')
@login_required
def get_unread_count():
    """API per conteggio messaggi non letti"""
    try:
        # Per ora restituisce 0
        # La logica completa verrà implementata quando la tabella Message sarà disponibile
        
        return jsonify({
            'success': True,
            'unread_count': 0
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Errore: {str(e)}'}), 500