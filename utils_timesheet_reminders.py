"""
Sistema di reminder automatici per compilazione timesheet
"""
from datetime import date, datetime, timedelta
from app import db
from models import MonthlyTimesheet, User
from message_utils import send_internal_message
from utils_tenant import filter_by_company


def send_timesheet_reminders():
    """
    Invia reminder progressivi per timesheet non consolidati
    
    Logica:
    - Giorno 1 del mese: reminder per timesheet mese scorso non consolidato
    - Giorno 3 del mese: secondo reminder se ancora non consolidato
    - Giorno 6 del mese: reminder urgente (il giorno 7 scatta il blocco)
    
    Returns:
        dict: Statistiche reminder inviati {day1: int, day3: int, day6: int}
    """
    today = date.today()
    current_month = today.month
    current_year = today.year
    current_day = today.day
    
    # Calcola mese precedente
    if current_month == 1:
        prev_month = 12
        prev_year = current_year - 1
    else:
        prev_month = current_month - 1
        prev_year = current_year
    
    stats = {'day1': 0, 'day3': 0, 'day6': 0}
    
    # Query tutti i timesheet del mese precedente NON consolidati
    timesheets = MonthlyTimesheet.query.filter_by(
        year=prev_year,
        month=prev_month,
        is_consolidated=False,
        is_validated=False
    ).all()
    
    for timesheet in timesheets:
        user = timesheet.user
        
        # Skip utenti non attivi
        if not user or not user.active:
            continue
        
        # Reminder giorno 1
        if current_day == 1 and not timesheet.reminder_day1_sent_at:
            send_internal_message(
                recipient_id=user.id,
                title="📋 Promemoria: Compila il timesheet",
                message=f"Ciao {user.first_name},<br><br>"
                       f"Ti ricordiamo di compilare e consolidare il timesheet per <strong>{get_month_name(prev_month)} {prev_year}</strong>.<br><br>"
                       f"È importante completare la compilazione entro il <strong>7 {get_month_name(current_month)}</strong>, "
                       f"dopo tale data la compilazione verrà bloccata e dovrai richiedere uno sblocco al tuo responsabile.<br><br>"
                       f"<a href='/my-attendance?year={prev_year}&month={prev_month}' class='btn btn-primary btn-sm'>Vai al Timesheet</a>",
                message_type='info',
                company_id=user.company_id
            )
            timesheet.reminder_day1_sent_at = datetime.now()
            stats['day1'] += 1
        
        # Reminder giorno 3
        elif current_day == 3 and not timesheet.reminder_day3_sent_at:
            send_internal_message(
                recipient_id=user.id,
                title="⏰ Promemoria: Timesheet ancora da compilare",
                message=f"Ciao {user.first_name},<br><br>"
                       f"Il tuo timesheet per <strong>{get_month_name(prev_month)} {prev_year}</strong> non è ancora stato consolidato.<br><br>"
                       f"Hai tempo fino al <strong>7 {get_month_name(current_month)}</strong> per completare la compilazione. "
                       f"Dopo tale data sarà necessario richiedere uno sblocco al responsabile.<br><br>"
                       f"<a href='/my-attendance?year={prev_year}&month={prev_month}' class='btn btn-warning btn-sm'>Compila Ora</a>",
                message_type='warning',
                company_id=user.company_id
            )
            timesheet.reminder_day3_sent_at = datetime.now()
            stats['day3'] += 1
        
        # Reminder giorno 6 (urgente)
        elif current_day == 6 and not timesheet.reminder_day6_sent_at:
            send_internal_message(
                recipient_id=user.id,
                title="🚨 URGENTE: Timesheet in scadenza - Compilazione si bloccherà domani",
                message=f"Ciao {user.first_name},<br><br>"
                       f"<strong style='color: #dc3545;'>ATTENZIONE!</strong> Il tuo timesheet per <strong>{get_month_name(prev_month)} {prev_year}</strong> "
                       f"non è ancora stato consolidato.<br><br>"
                       f"<strong>DOMANI (7 {get_month_name(current_month)}) la compilazione verrà bloccata automaticamente.</strong><br><br>"
                       f"Se hai bisogno di compilare dopo il blocco, dovrai richiedere un'autorizzazione al tuo responsabile. "
                       f"Ti consigliamo di completare la compilazione <strong>OGGI</strong> per evitare ritardi.<br><br>"
                       f"<a href='/my-attendance?year={prev_year}&month={prev_month}' class='btn btn-danger btn-sm'>⚠️ Compila Subito</a>",
                message_type='danger',
                company_id=user.company_id
            )
            timesheet.reminder_day6_sent_at = datetime.now()
            stats['day6'] += 1
    
    # Salva tutti i timestamp dei reminder
    db.session.commit()
    
    return stats


def get_month_name(month_num):
    """Restituisce il nome del mese in italiano"""
    months = {
        1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile",
        5: "Maggio", 6: "Giugno", 7: "Luglio", 8: "Agosto",
        9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre"
    }
    return months.get(month_num, str(month_num))


def get_reminders_summary():
    """Restituisce un riepilogo dei reminder da inviare oggi
    
    Utile per preview/test prima di eseguire l'invio effettivo
    """
    today = date.today()
    current_month = today.month
    current_year = today.year
    current_day = today.day
    
    # Calcola mese precedente
    if current_month == 1:
        prev_month = 12
        prev_year = current_year - 1
    else:
        prev_month = current_month - 1
        prev_year = current_year
    
    # Query tutti i timesheet del mese precedente NON consolidati
    timesheets = MonthlyTimesheet.query.filter_by(
        year=prev_year,
        month=prev_month,
        is_consolidated=False,
        is_validated=False
    ).all()
    
    summary = {
        'day1_pending': 0,
        'day3_pending': 0,
        'day6_pending': 0,
        'total_unconsolidated': len(timesheets)
    }
    
    for timesheet in timesheets:
        if not timesheet.user or not timesheet.user.active:
            continue
            
        if current_day == 1 and not timesheet.reminder_day1_sent_at:
            summary['day1_pending'] += 1
        elif current_day == 3 and not timesheet.reminder_day3_sent_at:
            summary['day3_pending'] += 1
        elif current_day == 6 and not timesheet.reminder_day6_sent_at:
            summary['day6_pending'] += 1
    
    return summary
