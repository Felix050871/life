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
from sqlalchemy import or_
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
    """Visualizza i messaggi interni per l'utente corrente (ricevuti e inviati)"""
    from datetime import timedelta
    
    # Messaggi ricevuti dall'utente corrente (with company filter)
    received_messages = filter_by_company(InternalMessage.query).filter(
        InternalMessage.recipient_id == current_user.id
    ).order_by(InternalMessage.created_at.desc()).all()
    
    # Messaggi inviati dall'utente corrente (with company filter)
    # Raggruppa per message_group_id per evitare duplicati
    sent_messages_raw = filter_by_company(InternalMessage.query).filter(
        InternalMessage.sender_id == current_user.id
    ).order_by(InternalMessage.created_at.desc()).all()
    
    # Filtra i messaggi inviati per mostrare solo uno per gruppo
    sent_messages = []
    seen_groups = set()
    seen_legacy_groups = set()  # Per messaggi senza group_id
    
    for msg in sent_messages_raw:
        if msg.message_group_id:
            # Nuovi messaggi con group_id
            if msg.message_group_id not in seen_groups:
                sent_messages.append(msg)
                seen_groups.add(msg.message_group_id)
        else:
            # Messaggi vecchi senza group_id: raggruppa per sender+title+timestamp
            # Crea una chiave basata su sender, titolo e timestamp (arrotondato al secondo)
            timestamp_key = msg.created_at.replace(microsecond=0)
            legacy_key = (msg.sender_id, msg.title, timestamp_key)
            
            if legacy_key not in seen_legacy_groups:
                sent_messages.append(msg)
                seen_legacy_groups.add(legacy_key)
    
    # Unisci e ordina tutti i messaggi per data
    messages = sorted(received_messages + sent_messages, 
                     key=lambda x: x.created_at, reverse=True)
    
    # Conta messaggi non letti ricevuti (with company filter)
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
    message = filter_by_company(InternalMessage.query).filter_by(id=message_id).first_or_404()
    
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
    """Cancella un messaggio (ricevuto o inviato)"""
    message = filter_by_company(InternalMessage.query).filter_by(id=message_id).first_or_404()
    
    # Verifica che sia il destinatario o il mittente del messaggio
    if message.recipient_id != current_user.id and message.sender_id != current_user.id:
        flash('Non puoi cancellare questo messaggio', 'danger')
        return redirect(url_for('messages.internal_messages'))
    
    try:
        # Se è il mittente, cancella tutti i messaggi del gruppo
        if message.sender_id == current_user.id:
            if message.message_group_id:
                # Nuovi messaggi con group_id
                grouped_messages = filter_by_company(InternalMessage.query).filter_by(
                    message_group_id=message.message_group_id
                ).all()
                for msg in grouped_messages:
                    db.session.delete(msg)
                db.session.commit()
                flash(f'Messaggio cancellato con successo ({len(grouped_messages)} destinatari)', 'success')
            else:
                # Messaggi vecchi senza group_id: cancella per sender+title+timestamp
                timestamp_key = message.created_at.replace(microsecond=0)
                grouped_messages = filter_by_company(InternalMessage.query).filter_by(
                    sender_id=message.sender_id,
                    title=message.title
                ).filter(
                    db.func.date_trunc('second', InternalMessage.created_at) == timestamp_key
                ).all()
                
                for msg in grouped_messages:
                    db.session.delete(msg)
                db.session.commit()
                
                if len(grouped_messages) > 1:
                    flash(f'Messaggio cancellato con successo ({len(grouped_messages)} destinatari)', 'success')
                else:
                    flash('Messaggio cancellato con successo', 'success')
        else:
            # Il destinatario cancella solo la sua copia
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
        
        # Verifica permessi sede per tutti i destinatari
        valid_recipients = []
        invalid_recipients = []
        for recipient in recipients:
            can_send = False
            # Controlla se l'utente ha permessi sede
            if current_user.all_sedi:
                can_send = True
            elif current_user.sede_id and recipient.sede_id == current_user.sede_id:
                can_send = True
            
            if can_send:
                valid_recipients.append(recipient)
            else:
                invalid_recipients.append(recipient.get_full_name())
        
        if not valid_recipients:
            if invalid_recipients:
                flash(f'Non puoi inviare messaggi agli utenti selezionati: {", ".join(invalid_recipients[:3])}', 'danger')
            else:
                flash('Non hai i permessi per inviare messaggi ai destinatari selezionati', 'danger')
            return render_template('send_message.html', form=form)
        
        # Avvisa se alcuni destinatari sono stati esclusi per permessi sede
        if invalid_recipients:
            flash(f'Attenzione: {len(invalid_recipients)} destinatario/i escluso/i per permessi sede', 'warning')
        
        # Crea e salva un messaggio per ogni destinatario valido
        # Genera un UUID per raggruppare messaggi multipli
        import uuid
        message_group_id = str(uuid.uuid4()) if len(valid_recipients) > 1 else None
        
        messages_sent = 0
        for recipient in valid_recipients:
            message = InternalMessage()
            message.recipient_id = recipient.id
            message.sender_id = current_user.id
            message.title = form.title.data
            message.message = form.message.data
            message.message_type = form.message_type.data
            message.message_group_id = message_group_id
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