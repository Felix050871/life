"""
Sistema di invio email multi-tenant per Life
Gestisce notifiche per approvazioni, rifiuti, reset password, ecc.

Sistema Ibrido:
- SUPERADMIN: usa SMTP globale da variabili ambiente (per email di onboarding/attivazione azienda)
- TENANT: usa CompanyEmailSettings specifico dell'azienda (per email operative)
"""

import os
from flask_mail import Mail, Message
from flask import url_for, render_template_string, g
from dataclasses import dataclass
from typing import Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

mail = Mail()

def init_mail(app):
    """Inizializza Flask-Mail con l'app (solo per SMTP globale SUPERADMIN)"""
    mail.init_app(app)


@dataclass
class EmailContext:
    """Contesto email che determina quale SMTP usare"""
    server: str
    port: int
    use_tls: bool
    use_ssl: bool
    username: str
    password: str
    sender: str
    reply_to: Optional[str] = None
    
    @classmethod
    def from_global_config(cls):
        """Crea EmailContext da configurazione globale (SUPERADMIN)"""
        return cls(
            server=os.environ.get('MAIL_SERVER', 'smtp.gmail.com'),
            port=int(os.environ.get('MAIL_PORT', '587')),
            use_tls=os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true',
            use_ssl=False,
            username=os.environ.get('MAIL_USERNAME', ''),
            password=os.environ.get('MAIL_PASSWORD', ''),
            sender=os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@life.local')
        )
    
    @classmethod
    def from_company_settings(cls, company_id):
        """Crea EmailContext da CompanyEmailSettings (TENANT)"""
        from models import CompanyEmailSettings
        from app import db
        
        settings = CompanyEmailSettings.query.filter_by(
            company_id=company_id, 
            active=True
        ).first()
        
        if not settings:
            raise ValueError(f"Nessuna configurazione email attiva per company_id={company_id}")
        
        return cls(
            server=settings.mail_server,
            port=settings.mail_port,
            use_tls=settings.mail_use_tls,
            use_ssl=settings.mail_use_ssl,
            username=settings.mail_username,
            password=settings.get_decrypted_password(),
            sender=settings.mail_default_sender,
            reply_to=settings.mail_reply_to
        )
    
    @classmethod
    def get_current(cls):
        """
        Determina automaticamente il contesto email corretto:
        - Se c'è g.company (tenant context): usa CompanyEmailSettings
        - Altrimenti: usa configurazione globale (SUPERADMIN)
        """
        if hasattr(g, 'company') and g.company:
            try:
                return cls.from_company_settings(g.company.id)
            except ValueError:
                # Fallback a global se non c'è config per il tenant
                print(f"WARNING: Nessuna config email per company {g.company.id}, uso global config")
                return cls.from_global_config()
        else:
            # SUPERADMIN context
            return cls.from_global_config()


def send_email_smtp(context: EmailContext, subject: str, recipients: list, body_text: str, body_html: Optional[str] = None):
    """
    Invia email usando SMTP diretto (non Flask-Mail) con EmailContext specifico
    
    Args:
        context: EmailContext con configurazione SMTP
        subject: Oggetto dell'email
        recipients: Lista di email destinatari
        body_text: Corpo email in formato testo
        body_html: Corpo email in formato HTML (opzionale)
    
    Returns:
        True se inviata con successo, False altrimenti
    """
    try:
        # Crea messaggio
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = context.sender
        msg['To'] = ', '.join(recipients)
        if context.reply_to:
            msg['Reply-To'] = context.reply_to
        
        # Aggiungi corpo testo
        part_text = MIMEText(body_text, 'plain')
        msg.attach(part_text)
        
        # Aggiungi corpo HTML se presente
        if body_html:
            part_html = MIMEText(body_html, 'html')
            msg.attach(part_html)
        
        # Connetti al server SMTP con timeout di 15 secondi
        if context.use_ssl:
            server = smtplib.SMTP_SSL(context.server, context.port, timeout=15)
        else:
            server = smtplib.SMTP(context.server, context.port, timeout=15)
            if context.use_tls:
                server.starttls()
        
        # Autenticazione
        if context.username and context.password:
            server.login(context.username, context.password)
        
        # Invia email
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Errore invio email: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def send_email(subject, recipients, body_text, body_html=None, company_id=None):
    """
    Invia email generica usando il sistema multi-tenant
    
    Args:
        subject: Oggetto dell'email
        recipients: Lista di email destinatari
        body_text: Corpo email in formato testo
        body_html: Corpo email in formato HTML (opzionale)
        company_id: ID azienda (opzionale, auto-detect da g.company)
    
    Returns:
        True se inviata con successo, False altrimenti
    """
    try:
        # Determina il contesto email
        if company_id:
            # Usa configurazione specifica dell'azienda
            context = EmailContext.from_company_settings(company_id)
        else:
            # Auto-detect: usa g.company se presente, altrimenti global
            context = EmailContext.get_current()
        
        # Invia usando SMTP diretto
        return send_email_smtp(context, subject, recipients, body_text, body_html)
    except Exception as e:
        print(f"Errore invio email: {str(e)}")
        import traceback
        traceback.print_exc()
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
