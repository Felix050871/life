"""
Sistema di invio email per Life
Gestisce notifiche per approvazioni, rifiuti, reset password, ecc.
"""

import os
from flask_mail import Mail, Message
from flask import url_for, render_template_string

mail = Mail()

def init_mail(app):
    """Inizializza Flask-Mail con l'app"""
    mail.init_app(app)

def send_email(subject, recipients, body_text, body_html=None):
    """
    Invia email generica
    
    Args:
        subject: Oggetto dell'email
        recipients: Lista di email destinatari
        body_text: Corpo email in formato testo
        body_html: Corpo email in formato HTML (opzionale)
    
    Returns:
        True se inviata con successo, False altrimenti
    """
    try:
        # Per SendGrid: se MAIL_USERNAME è 'apikey', usa MAIL_DEFAULT_SENDER come mittente
        # Altrimenti usa MAIL_DEFAULT_SENDER se impostato, o MAIL_USERNAME
        mail_username = os.environ.get('MAIL_USERNAME', '')
        
        if mail_username == 'apikey':
            # Modalità SendGrid API: usa MAIL_DEFAULT_SENDER obbligatoriamente
            sender = os.environ.get('MAIL_DEFAULT_SENDER')
            if not sender:
                raise ValueError("MAIL_DEFAULT_SENDER è obbligatorio quando MAIL_USERNAME='apikey'")
        else:
            # Modalità SMTP standard: usa MAIL_DEFAULT_SENDER se impostato, altrimenti MAIL_USERNAME
            sender = os.environ.get('MAIL_DEFAULT_SENDER') or mail_username or 'noreply@life.local'
        
        msg = Message(
            subject=subject,
            recipients=recipients,
            sender=sender
        )
        msg.body = body_text
        if body_html:
            msg.html = body_html
        
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Errore invio email: {str(e)}")
        return False


def send_leave_approval_email(leave_request, approver):
    """Notifica approvazione richiesta ferie/permessi"""
    user = leave_request.user
    leave_type = leave_request.leave_type_obj.name if leave_request.leave_type_obj else leave_request.leave_type or 'ferie/permesso'
    
    subject = f"✅ Richiesta {leave_type} Approvata"
    
    # Formatta il periodo
    if leave_request.start_time and leave_request.end_time:
        period = f"{leave_request.start_date.strftime('%d/%m/%Y')} dalle {leave_request.start_time.strftime('%H:%M')} alle {leave_request.end_time.strftime('%H:%M')}"
    else:
        if leave_request.start_date == leave_request.end_date:
            period = leave_request.start_date.strftime('%d/%m/%Y')
        else:
            period = f"{leave_request.start_date.strftime('%d/%m/%Y')} - {leave_request.end_date.strftime('%d/%m/%Y')}"
    
    body_text = f"""
Ciao {user.get_full_name()},

La tua richiesta di {leave_type} è stata APPROVATA.

Dettagli:
- Periodo: {period}
- Approvata da: {approver.get_full_name()}
"""
    
    if leave_request.approval_notes:
        body_text += f"- Note: {leave_request.approval_notes}\n"
    
    if leave_request.use_banca_ore and leave_request.banca_ore_hours_used:
        body_text += f"\nUtilizzate {leave_request.banca_ore_hours_used:.1f}h dalla Banca Ore.\n"
    
    body_text += "\nBuon riposo!\n\n---\nLife - Sistema Gestione Presenze"
    
    body_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8f9fa; border-radius: 10px;">
            <h2 style="color: #28a745;">✅ Richiesta Approvata</h2>
            <p>Ciao <strong>{user.get_full_name()}</strong>,</p>
            <p>La tua richiesta di <strong>{leave_type}</strong> è stata <span style="color: #28a745;">APPROVATA</span>.</p>
            
            <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="margin-top: 0;">Dettagli:</h3>
                <ul style="list-style: none; padding: 0;">
                    <li>📅 <strong>Periodo:</strong> {period}</li>
                    <li>👤 <strong>Approvata da:</strong> {approver.get_full_name()}</li>
                    {f'<li>📝 <strong>Note:</strong> {leave_request.approval_notes}</li>' if leave_request.approval_notes else ''}
                    {f'<li>💰 <strong>Banca Ore:</strong> Utilizzate {leave_request.banca_ore_hours_used:.1f}h</li>' if leave_request.use_banca_ore and leave_request.banca_ore_hours_used else ''}
                </ul>
            </div>
            
            <p style="color: #666;">Buon riposo!</p>
            <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
            <p style="font-size: 12px; color: #999; text-align: center;">Life - Sistema Gestione Presenze</p>
        </div>
    </body>
    </html>
    """
    
    return send_email(subject, [user.email], body_text, body_html)


def send_leave_rejection_email(leave_request, approver, reason=None):
    """Notifica rifiuto richiesta ferie/permessi"""
    user = leave_request.user
    leave_type = leave_request.leave_type_obj.name if leave_request.leave_type_obj else leave_request.leave_type or 'ferie/permesso'
    
    subject = f"❌ Richiesta {leave_type} Rifiutata"
    
    # Formatta il periodo
    if leave_request.start_time and leave_request.end_time:
        period = f"{leave_request.start_date.strftime('%d/%m/%Y')} dalle {leave_request.start_time.strftime('%H:%M')} alle {leave_request.end_time.strftime('%H:%M')}"
    else:
        if leave_request.start_date == leave_request.end_date:
            period = leave_request.start_date.strftime('%d/%m/%Y')
        else:
            period = f"{leave_request.start_date.strftime('%d/%m/%Y')} - {leave_request.end_date.strftime('%d/%m/%Y')}"
    
    body_text = f"""
Ciao {user.get_full_name()},

La tua richiesta di {leave_type} è stata RIFIUTATA.

Dettagli:
- Periodo: {period}
- Rifiutata da: {approver.get_full_name()}
"""
    
    if reason:
        body_text += f"- Motivo: {reason}\n"
    
    body_text += "\nPer maggiori informazioni, contatta il tuo responsabile.\n\n---\nLife - Sistema Gestione Presenze"
    
    body_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8f9fa; border-radius: 10px;">
            <h2 style="color: #dc3545;">❌ Richiesta Rifiutata</h2>
            <p>Ciao <strong>{user.get_full_name()}</strong>,</p>
            <p>La tua richiesta di <strong>{leave_type}</strong> è stata <span style="color: #dc3545;">RIFIUTATA</span>.</p>
            
            <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="margin-top: 0;">Dettagli:</h3>
                <ul style="list-style: none; padding: 0;">
                    <li>📅 <strong>Periodo:</strong> {period}</li>
                    <li>👤 <strong>Rifiutata da:</strong> {approver.get_full_name()}</li>
                    {f'<li>📝 <strong>Motivo:</strong> {reason}</li>' if reason else ''}
                </ul>
            </div>
            
            <p style="color: #666;">Per maggiori informazioni, contatta il tuo responsabile.</p>
            <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
            <p style="font-size: 12px; color: #999; text-align: center;">Life - Sistema Gestione Presenze</p>
        </div>
    </body>
    </html>
    """
    
    return send_email(subject, [user.email], body_text, body_html)


def send_password_reset_email(user, reset_url):
    """Invia email con link per reset password"""
    subject = "🔒 Reset Password - Life"
    
    body_text = f"""
Ciao {user.get_full_name()},

Hai richiesto il reset della password per il tuo account Life.

Clicca sul link seguente per reimpostare la password:
{reset_url}

Questo link è valido per 1 ora.

Se non hai richiesto il reset, ignora questa email.

---
Life - Sistema Gestione Presenze
"""
    
    body_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8f9fa; border-radius: 10px;">
            <h2 style="color: #007bff;">🔒 Reset Password</h2>
            <p>Ciao <strong>{user.get_full_name()}</strong>,</p>
            <p>Hai richiesto il reset della password per il tuo account Life.</p>
            
            <div style="background-color: white; padding: 20px; border-radius: 5px; margin: 20px 0; text-align: center;">
                <p>Clicca sul pulsante seguente per reimpostare la password:</p>
                <a href="{reset_url}" style="display: inline-block; padding: 12px 30px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 10px 0;">
                    Reimposta Password
                </a>
                <p style="font-size: 12px; color: #666; margin-top: 15px;">
                    Questo link è valido per 1 ora.
                </p>
            </div>
            
            <p style="color: #666; font-size: 14px;">
                Se non hai richiesto il reset, ignora questa email. La tua password rimarrà invariata.
            </p>
            
            <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
            <p style="font-size: 12px; color: #999; text-align: center;">Life - Sistema Gestione Presenze</p>
        </div>
    </body>
    </html>
    """
    
    return send_email(subject, [user.email], body_text, body_html)


def send_overtime_approval_email(overtime_request, approver):
    """Notifica approvazione richiesta straordinario"""
    user = overtime_request.user
    
    subject = "✅ Richiesta Straordinario Approvata"
    
    body_text = f"""
Ciao {user.get_full_name()},

La tua richiesta di straordinario è stata APPROVATA.

Dettagli:
- Data: {overtime_request.date.strftime('%d/%m/%Y')}
- Ore: {overtime_request.hours}h
- Approvata da: {approver.get_full_name()}
"""
    
    if overtime_request.notes:
        body_text += f"- Note: {overtime_request.notes}\n"
    
    body_text += "\n---\nLife - Sistema Gestione Presenze"
    
    return send_email(subject, [user.email], body_text)


def send_overtime_rejection_email(overtime_request, approver, reason=None):
    """Notifica rifiuto richiesta straordinario"""
    user = overtime_request.user
    
    subject = "❌ Richiesta Straordinario Rifiutata"
    
    body_text = f"""
Ciao {user.get_full_name()},

La tua richiesta di straordinario è stata RIFIUTATA.

Dettagli:
- Data: {overtime_request.date.strftime('%d/%m/%Y')}
- Ore: {overtime_request.hours}h
- Rifiutata da: {approver.get_full_name()}
"""
    
    if reason:
        body_text += f"- Motivo: {reason}\n"
    
    body_text += "\nPer maggiori informazioni, contatta il tuo responsabile.\n\n---\nLife - Sistema Gestione Presenze"
    
    return send_email(subject, [user.email], body_text)


def send_announcement_notification(post, company_users, post_url):
    """
    Invia notifica email a tutti gli utenti dell'azienda per una nuova comunicazione
    
    Args:
        post: Oggetto CirclePost (comunicazione)
        company_users: Lista di oggetti User dell'azienda
        post_url: URL completo per visualizzare la comunicazione
    
    Returns:
        Numero di email inviate con successo
    """
    subject = f"📢 Nuova Comunicazione: {post.title}"
    
    successful_sends = 0
    
    for user in company_users:
        if not user.email:
            continue
            
        body_text = f"""
Ciao {user.get_full_name()},

È stata pubblicata una nuova comunicazione su Life.

Titolo: {post.title}
Autore: {post.author.get_full_name()}

Accedi a Life per leggere la comunicazione completa:
{post_url}

---
Life - Piattaforma Aziendale
"""
        
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8f9fa; border-radius: 10px;">
                <h2 style="color: #007bff;">📢 Nuova Comunicazione</h2>
                <p>Ciao <strong>{user.get_full_name()}</strong>,</p>
                <p>È stata pubblicata una nuova comunicazione su Life.</p>
                
                <div style="background-color: white; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #333;">{post.title}</h3>
                    <p style="color: #666; margin-bottom: 15px;">
                        <small>Autore: {post.author.get_full_name()}</small>
                    </p>
                    
                    <div style="text-align: center; margin-top: 20px;">
                        <a href="{post_url}" style="display: inline-block; padding: 12px 30px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px;">
                            Leggi la Comunicazione
                        </a>
                    </div>
                </div>
                
                <p style="color: #666; font-size: 14px;">
                    Accedi alla piattaforma Life per visualizzare il contenuto completo.
                </p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="font-size: 12px; color: #999; text-align: center;">Life - Piattaforma Aziendale</p>
            </div>
        </body>
        </html>
        """
        
        if send_email(subject, [user.email], body_text, body_html):
            successful_sends += 1
    
    return successful_sends
