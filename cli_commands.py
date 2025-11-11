"""
Flask CLI Commands per Life Platform
"""
import click
from flask.cli import with_appcontext
from app import app


@app.cli.command('send-timesheet-reminders')
@with_appcontext
def send_timesheet_reminders_command():
    """
    Invia reminder progressivi per timesheet non consolidati
    
    Esegui questo comando quotidianamente via cron:
    0 9 * * * cd /path/to/app && flask send-timesheet-reminders
    
    Il sistema invierà automaticamente:
    - Giorno 1 del mese: primo reminder per timesheet mese scorso
    - Giorno 3 del mese: secondo reminder
    - Giorno 6 del mese: reminder urgente pre-blocco
    """
    from utils_timesheet_reminders import send_timesheet_reminders, get_reminders_summary
    from datetime import date
    
    click.echo(f"=== Timesheet Reminders - {date.today().strftime('%Y-%m-%d')} ===\n")
    
    # Preview
    summary = get_reminders_summary()
    click.echo(f"Timesheet non consolidati: {summary['total_unconsolidated']}")
    click.echo(f"Reminder giorno 1 da inviare: {summary['day1_pending']}")
    click.echo(f"Reminder giorno 3 da inviare: {summary['day3_pending']}")
    click.echo(f"Reminder giorno 6 da inviare: {summary['day6_pending']}")
    click.echo()
    
    # Conferma
    if summary['day1_pending'] + summary['day3_pending'] + summary['day6_pending'] == 0:
        click.echo("Nessun reminder da inviare oggi.")
        return
    
    # Invia reminder
    click.echo("Invio reminder in corso...")
    stats = send_timesheet_reminders()
    
    click.echo(f"\n✅ Reminder inviati:")
    click.echo(f"  - Giorno 1: {stats['day1']} messaggi")
    click.echo(f"  - Giorno 3: {stats['day3']} messaggi")
    click.echo(f"  - Giorno 6: {stats['day6']} messaggi")
    click.echo(f"\nTotale: {sum(stats.values())} messaggi inviati")


@app.cli.command('test-reminder-preview')
@with_appcontext
def test_reminder_preview_command():
    """
    Preview dei reminder che verrebbero inviati oggi (senza inviarli)
    Utile per test e debug
    """
    from utils_timesheet_reminders import get_reminders_summary
    from datetime import date
    
    click.echo(f"=== Preview Reminder - {date.today().strftime('%Y-%m-%d')} ===\n")
    
    summary = get_reminders_summary()
    click.echo(f"Timesheet non consolidati: {summary['total_unconsolidated']}")
    click.echo(f"Reminder giorno 1 da inviare: {summary['day1_pending']}")
    click.echo(f"Reminder giorno 3 da inviare: {summary['day3_pending']}")
    click.echo(f"Reminder giorno 6 da inviare: {summary['day6_pending']}")
    
    if summary['day1_pending'] + summary['day3_pending'] + summary['day6_pending'] == 0:
        click.echo("\n✅ Nessun reminder da inviare oggi.")
    else:
        total = summary['day1_pending'] + summary['day3_pending'] + summary['day6_pending']
        click.echo(f"\n⚠️  Sarebbero inviati {total} messaggi se eseguissi 'flask send-timesheet-reminders'")


if __name__ == '__main__':
    app.cli()
