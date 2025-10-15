# =============================================================================
# INTERNAL MESSAGES BLUEPRINT
# =============================================================================
#
# ROUTES INCLUSE:
# 1. internal_messages (GET) - Visualizza messaggi interni utente corrente
# 2. mark_message_read (GET) - Segna singolo messaggio come letto
# 3. delete_message (POST) - Cancella singolo messaggio
# 4. mark_all_messages_read (POST) - Segna tutti i messaggi come letti
# 5. send_message (GET/POST) - Invia nuovo messaggio interno
#
# Total routes: 5 internal messages routes
# =============================================================================

from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from app import db
from models import User, InternalMessage
from forms import SendMessageForm
from utils_tenant import filter_by_company, set_company_on_create

# Create blueprint
messages_bp = Blueprint('messages', __name__)

# Helper functions
def require_messages_permission(f):
    """Decorator to require messages permissions for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not (current_user.can_send_messages() or current_user.can_view_messages()):
            flash('Non hai i permessi per accedere ai messaggi interni', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# INTERNAL MESSAGES ROUTES
# =============================================================================

@messages_bp.route('/messages')
@login_required
@require_messages_permission
def internal_messages():
    """Visualizza i messaggi interni per l'utente corrente"""
    # Messaggi per l'utente corrente (with company filter)
    messages = filter_by_company(InternalMessage.query).filter_by(
        recipient_id=current_user.id
    ).order_by(InternalMessage.created_at.desc()).all()
    
    # Conta messaggi non letti (with company filter)
    unread_count = filter_by_company(InternalMessage.query).filter_by(
        recipient_id=current_user.id,
        is_read=False
    ).count()
    
    return render_template('internal_messages.html', 
                         messages=messages, 
                         unread_count=unread_count)

@messages_bp.route('/message/<int:message_id>/mark_read')
@login_required  
def mark_message_read(message_id):
    """Segna un messaggio come letto"""
    message = filter_by_company(InternalMessage.query).get_or_404(message_id)
    
    # Verifica che sia il destinatario del messaggio
    if message.recipient_id != current_user.id:
        flash('Non puoi accedere a questo messaggio', 'danger')
        return redirect(url_for('messages.internal_messages'))
    
    # Segna come letto
    message.is_read = True
    db.session.commit()
    
    return redirect(url_for('messages.internal_messages'))

@messages_bp.route('/message/<int:message_id>/delete', methods=['POST'])
@login_required  
def delete_message(message_id):
    """Cancella un messaggio"""
    message = filter_by_company(InternalMessage.query).get_or_404(message_id)
    
    # Verifica che sia il destinatario del messaggio
    if message.recipient_id != current_user.id:
        flash('Non puoi cancellare questo messaggio', 'danger')
        return redirect(url_for('messages.internal_messages'))
    
    try:
        db.session.delete(message)
        db.session.commit()
        flash('Messaggio cancellato con successo', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Errore nella cancellazione del messaggio', 'danger')
    
    return redirect(url_for('messages.internal_messages'))

@messages_bp.route('/messages/mark_all_read', methods=['POST'])
@login_required  
@require_messages_permission
def mark_all_messages_read():
    """Segna tutti i messaggi dell'utente come letti"""
    try:
        # Segna tutti i messaggi non letti dell'utente corrente come letti (with company filter)
        unread_messages = filter_by_company(InternalMessage.query).filter_by(
            recipient_id=current_user.id,
            is_read=False
        ).all()
        
        for message in unread_messages:
            message.is_read = True
        
        db.session.commit()
        
        count = len(unread_messages)
        if count > 0:
            flash(f'Tutti i {count} messaggi non letti sono stati marcati come letti', 'success')
        else:
            flash('Nessun messaggio da marcare come letto', 'info')
            
    except Exception as e:
        db.session.rollback()
        flash('Errore nel marcare i messaggi come letti', 'danger')
    
    return redirect(url_for('messages.internal_messages'))

@messages_bp.route('/send_message', methods=['GET', 'POST'])
@login_required
def send_message():
    """Invia un nuovo messaggio interno"""
    if not current_user.can_send_messages():
        flash('Non hai i permessi per inviare messaggi', 'danger')
        return redirect(url_for('messages.internal_messages'))
    
    form = SendMessageForm(current_user=current_user)
    
    if form.validate_on_submit():
        # Verifica che tutti i destinatari siano validi e accessibili (with company filter)
        recipients = filter_by_company(User.query).filter(
            User.id.in_(form.recipient_ids.data),
            User.active == True
        ).all()
        
        if not recipients:
            flash('Nessun destinatario valido selezionato', 'danger')
            return render_template('send_message.html', form=form)
        
        # Verifica permessi sede e connessioni per tutti i destinatari
        valid_recipients = []
        non_connected_recipients = []
        for recipient in recipients:
            can_send = False
            # Prima controlla se l'utente ha permessi sede
            if current_user.all_sedi:
                can_send = True
            elif current_user.sede_id and recipient.sede_id == current_user.sede_id:
                can_send = True
            
            # Poi verifica se sono collegati (solo se CIRCLE è abilitato)
            if can_send and current_user.has_permission('can_access_hubly'):
                # Se CIRCLE è attivo, verifica la connessione
                if not current_user.is_connected_with(recipient):
                    can_send = False
                    non_connected_recipients.append(recipient.get_full_name())
            
            if can_send:
                valid_recipients.append(recipient)
        
        if not valid_recipients:
            if non_connected_recipients:
                flash(f'Non puoi inviare messaggi agli utenti con cui non sei collegato: {", ".join(non_connected_recipients[:3])}', 'danger')
            else:
                flash('Non hai i permessi per inviare messaggi ai destinatari selezionati', 'danger')
            return render_template('send_message.html', form=form)
        
        # Avvisa se alcuni destinatari sono stati esclusi per mancanza di connessione
        if non_connected_recipients:
            flash(f'Attenzione: {len(non_connected_recipients)} destinatario/i escluso/i perché non collegato/i', 'warning')
        
        # Crea e salva un messaggio per ogni destinatario valido
        messages_sent = 0
        for recipient in valid_recipients:
            message = InternalMessage()
            message.recipient_id = recipient.id
            message.sender_id = current_user.id
            message.title = form.title.data
            message.message = form.message.data
            message.message_type = form.message_type.data
            set_company_on_create(message)
            db.session.add(message)
            messages_sent += 1
        
        db.session.commit()
        
        if messages_sent == 1:
            flash(f'Messaggio inviato con successo a {valid_recipients[0].get_full_name()}', 'success')
        else:
            recipient_names = ', '.join([r.get_full_name() for r in valid_recipients[:3]])
            if len(valid_recipients) > 3:
                recipient_names += f' e altri {len(valid_recipients) - 3}'
            flash(f'Messaggio inviato con successo a {messages_sent} destinatari: {recipient_names}', 'success')
        
        return redirect(url_for('messages.internal_messages'))
    
    return render_template('send_message.html', form=form)