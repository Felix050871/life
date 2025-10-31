"""
Sistema di messaggistica interna per Life
Gestisce notifiche InternalMessage per workflow di approvazione
"""

import uuid
from app import db
from models import InternalMessage
from utils import italian_now


def send_internal_message(
    recipient_id,
    title,
    message,
    message_type='info',
    sender_id=None,
    related_leave_request_id=None,
    company_id=None
):
    """
    Invia un messaggio interno a un singolo utente
    
    Args:
        recipient_id: ID del destinatario
        title: Titolo del messaggio
        message: Corpo del messaggio
        message_type: Tipo di messaggio ('info', 'success', 'warning', 'danger')
        sender_id: ID del mittente (None per messaggi di sistema)
        related_leave_request_id: ID richiesta ferie correlata (opzionale)
        company_id: ID dell'azienda
    
    Returns:
        InternalMessage creato
    """
    internal_message = InternalMessage(
        recipient_id=recipient_id,
        sender_id=sender_id,
        title=title,
        message=message,
        message_type=message_type,
        related_leave_request_id=related_leave_request_id,
        company_id=company_id,
        created_at=italian_now()
    )
    
    db.session.add(internal_message)
    return internal_message


def send_internal_message_bulk(
    recipient_ids,
    title,
    message,
    message_type='info',
    sender_id=None,
    company_id=None
):
    """
    Invia un messaggio interno a più utenti con message_group_id
    
    Args:
        recipient_ids: Lista di ID destinatari
        title: Titolo del messaggio
        message: Corpo del messaggio
        message_type: Tipo di messaggio ('info', 'success', 'warning', 'danger')
        sender_id: ID del mittente (None per messaggi di sistema)
        company_id: ID dell'azienda
    
    Returns:
        Lista di InternalMessage creati
    """
    group_id = str(uuid.uuid4())
    messages = []
    
    for recipient_id in recipient_ids:
        internal_message = InternalMessage(
            recipient_id=recipient_id,
            sender_id=sender_id,
            title=title,
            message=message,
            message_type=message_type,
            company_id=company_id,
            message_group_id=group_id,
            created_at=italian_now()
        )
        db.session.add(internal_message)
        messages.append(internal_message)
    
    return messages


# =============================================================================
# TIMESHEET NOTIFICATIONS
# =============================================================================

def notify_timesheet_consolidated(user, year, month, consolidator, company_id):
    """
    Notifica l'utente che il suo timesheet è stato consolidato
    
    Args:
        user: User object del dipendente
        year: Anno del timesheet
        month: Mese del timesheet
        consolidator: User object di chi ha consolidato
        company_id: ID dell'azienda
    """
    title = "📋 Timesheet Consolidato"
    message = f"""Il tuo timesheet per {month:02d}/{year} è stato consolidato.

Consolidato da: {consolidator.get_full_name()}
Data: {italian_now().strftime('%d/%m/%Y %H:%M')}

Il timesheet è ora bloccato e non può essere modificato. Se necessiti di apportare correzioni, puoi richiedere la riapertura tramite la funzione apposita."""
    
    return send_internal_message(
        recipient_id=user.id,
        title=title,
        message=message,
        message_type='info',
        sender_id=consolidator.id,
        company_id=company_id
    )


def notify_timesheet_validated(user, year, month, validator, company_id):
    """
    Notifica l'utente che il suo timesheet è stato validato
    
    Args:
        user: User object del dipendente
        year: Anno del timesheet
        month: Mese del timesheet
        validator: User object di chi ha validato
        company_id: ID dell'azienda
    """
    title = "✅ Timesheet Validato"
    message = f"""Il tuo timesheet per {month:02d}/{year} è stato validato e approvato.

Validato da: {validator.get_full_name()}
Data: {italian_now().strftime('%d/%m/%Y %H:%M')}

Il timesheet è ora definitivo e non può più essere modificato."""
    
    return send_internal_message(
        recipient_id=user.id,
        title=title,
        message=message,
        message_type='success',
        sender_id=validator.id,
        company_id=company_id
    )


def notify_timesheet_reopen_request_created(managers, requester, year, month, reason, company_id):
    """
    Notifica i manager che è stata creata una richiesta di riapertura timesheet
    
    Args:
        managers: Lista di User objects (manager/HR)
        requester: User object di chi ha richiesto
        year: Anno del timesheet
        month: Mese del timesheet
        reason: Motivo della richiesta
        company_id: ID dell'azienda
    """
    title = "🔓 Nuova Richiesta Riapertura Timesheet"
    message = f"""L'utente {requester.get_full_name()} ha richiesto la riapertura del timesheet {month:02d}/{year}.

Motivo: {reason}

Accedi alla sezione "Richieste Riapertura Timesheet" per approvare o rifiutare la richiesta."""
    
    manager_ids = [m.id for m in managers]
    
    return send_internal_message_bulk(
        recipient_ids=manager_ids,
        title=title,
        message=message,
        message_type='warning',
        sender_id=requester.id,
        company_id=company_id
    )


def notify_timesheet_reopen_approved(requester, year, month, approver, company_id):
    """
    Notifica l'utente che la sua richiesta di riapertura è stata approvata
    
    Args:
        requester: User object di chi ha richiesto
        year: Anno del timesheet
        month: Mese del timesheet
        approver: User object di chi ha approvato
        company_id: ID dell'azienda
    """
    title = "✅ Richiesta Riapertura Approvata"
    message = f"""La tua richiesta di riapertura del timesheet {month:02d}/{year} è stata APPROVATA.

Approvata da: {approver.get_full_name()}
Data: {italian_now().strftime('%d/%m/%Y %H:%M')}

Ora puoi modificare il timesheet. Ricorda di riconsolidarlo quando hai completato le correzioni."""
    
    return send_internal_message(
        recipient_id=requester.id,
        title=title,
        message=message,
        message_type='success',
        sender_id=approver.id,
        company_id=company_id
    )


def notify_timesheet_reopen_rejected(requester, year, month, approver, rejection_reason, company_id):
    """
    Notifica l'utente che la sua richiesta di riapertura è stata rifiutata
    
    Args:
        requester: User object di chi ha richiesto
        year: Anno del timesheet
        month: Mese del timesheet
        approver: User object di chi ha rifiutato
        rejection_reason: Motivo del rifiuto
        company_id: ID dell'azienda
    """
    title = "❌ Richiesta Riapertura Rifiutata"
    message = f"""La tua richiesta di riapertura del timesheet {month:02d}/{year} è stata RIFIUTATA.

Rifiutata da: {approver.get_full_name()}
Motivo: {rejection_reason}

Se hai bisogno di ulteriori chiarimenti, contatta direttamente il tuo responsabile."""
    
    return send_internal_message(
        recipient_id=requester.id,
        title=title,
        message=message,
        message_type='danger',
        sender_id=approver.id,
        company_id=company_id
    )


# =============================================================================
# LEAVE REQUEST NOTIFICATIONS
# =============================================================================

def notify_leave_request_approved(leave_request, approver, company_id):
    """
    Notifica l'utente che la sua richiesta di assenza è stata approvata
    
    Args:
        leave_request: LeaveRequest object
        approver: User object di chi ha approvato
        company_id: ID dell'azienda
    """
    user = leave_request.user
    leave_type = leave_request.leave_type_obj.name if leave_request.leave_type_obj else leave_request.leave_type or 'ferie/permesso'
    
    # Formatta il periodo
    if leave_request.start_time and leave_request.end_time:
        period = f"{leave_request.start_date.strftime('%d/%m/%Y')} dalle {leave_request.start_time.strftime('%H:%M')} alle {leave_request.end_time.strftime('%H:%M')}"
    else:
        if leave_request.start_date == leave_request.end_date:
            period = leave_request.start_date.strftime('%d/%m/%Y')
        else:
            period = f"{leave_request.start_date.strftime('%d/%m/%Y')} - {leave_request.end_date.strftime('%d/%m/%Y')}"
    
    title = f"✅ Richiesta {leave_type.capitalize()} Approvata"
    message = f"""La tua richiesta di {leave_type} è stata APPROVATA.

Periodo: {period}
Approvata da: {approver.get_full_name()}"""
    
    if leave_request.approval_notes:
        message += f"\nNote: {leave_request.approval_notes}"
    
    if leave_request.use_banca_ore and leave_request.banca_ore_hours_used:
        message += f"\n\nUtilizzate {leave_request.banca_ore_hours_used:.1f}h dalla Banca Ore."
    
    return send_internal_message(
        recipient_id=user.id,
        title=title,
        message=message,
        message_type='success',
        sender_id=approver.id,
        related_leave_request_id=leave_request.id,
        company_id=company_id
    )


def notify_leave_request_rejected(leave_request, approver, rejection_reason, company_id):
    """
    Notifica l'utente che la sua richiesta di assenza è stata rifiutata
    
    Args:
        leave_request: LeaveRequest object
        approver: User object di chi ha rifiutato
        rejection_reason: Motivo del rifiuto
        company_id: ID dell'azienda
    """
    user = leave_request.user
    leave_type = leave_request.leave_type_obj.name if leave_request.leave_type_obj else leave_request.leave_type or 'ferie/permesso'
    
    # Formatta il periodo
    if leave_request.start_time and leave_request.end_time:
        period = f"{leave_request.start_date.strftime('%d/%m/%Y')} dalle {leave_request.start_time.strftime('%H:%M')} alle {leave_request.end_time.strftime('%H:%M')}"
    else:
        if leave_request.start_date == leave_request.end_date:
            period = leave_request.start_date.strftime('%d/%m/%Y')
        else:
            period = f"{leave_request.start_date.strftime('%d/%m/%Y')} - {leave_request.end_date.strftime('%d/%m/%Y')}"
    
    title = f"❌ Richiesta {leave_type.capitalize()} Rifiutata"
    message = f"""La tua richiesta di {leave_type} è stata RIFIUTATA.

Periodo: {period}
Rifiutata da: {approver.get_full_name()}
Motivo: {rejection_reason}"""
    
    return send_internal_message(
        recipient_id=user.id,
        title=title,
        message=message,
        message_type='danger',
        sender_id=approver.id,
        related_leave_request_id=leave_request.id,
        company_id=company_id
    )


# =============================================================================
# MILEAGE REQUEST NOTIFICATIONS
# =============================================================================

def notify_mileage_request_approved(mileage_request, approver, company_id):
    """
    Notifica l'utente che la sua richiesta di rimborso km è stata approvata
    
    Args:
        mileage_request: MileageRequest object
        approver: User object di chi ha approvato
        company_id: ID dell'azienda
    """
    user = mileage_request.employee
    
    title = "✅ Rimborso Chilometrico Approvato"
    message = f"""La tua richiesta di rimborso chilometrico è stata APPROVATA.

Data: {mileage_request.travel_date.strftime('%d/%m/%Y')}
Percorso: {mileage_request.route}
Chilometri: {mileage_request.distance_km} km
Importo: €{mileage_request.amount:.2f}

Approvata da: {approver.get_full_name()}"""
    
    if mileage_request.approval_comment:
        message += f"\nNote: {mileage_request.approval_comment}"
    
    return send_internal_message(
        recipient_id=user.id,
        title=title,
        message=message,
        message_type='success',
        sender_id=approver.id,
        company_id=company_id
    )


def notify_mileage_request_rejected(mileage_request, approver, rejection_reason, company_id):
    """
    Notifica l'utente che la sua richiesta di rimborso km è stata rifiutata
    
    Args:
        mileage_request: MileageRequest object
        approver: User object di chi ha rifiutato
        rejection_reason: Motivo del rifiuto
        company_id: ID dell'azienda
    """
    user = mileage_request.employee
    
    title = "❌ Rimborso Chilometrico Rifiutato"
    message = f"""La tua richiesta di rimborso chilometrico è stata RIFIUTATA.

Data: {mileage_request.travel_date.strftime('%d/%m/%Y')}
Percorso: {mileage_request.route}
Chilometri: {mileage_request.distance_km} km
Importo: €{mileage_request.amount:.2f}

Rifiutata da: {approver.get_full_name()}
Motivo: {rejection_reason}"""
    
    return send_internal_message(
        recipient_id=user.id,
        title=title,
        message=message,
        message_type='danger',
        sender_id=approver.id,
        company_id=company_id
    )
