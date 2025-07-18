#!/usr/bin/env python3
"""
Script per esportare il database in diversi formati
"""
import os
import json
import csv
from datetime import datetime
from app import app, db
from models import (User, AttendanceEvent, LeaveRequest, Shift, 
                   ReperibilitaShift, ReperibilitaIntervention, 
                   PresidioCoverage, ReperibilitaCoverage, 
                   ShiftTemplate, Holiday)

def export_to_json():
    """Esporta tutto il database in formato JSON"""
    with app.app_context():
        data = {}
        
        # Users
        users = User.query.all()
        data['users'] = []
        for user in users:
            data['users'].append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'part_time_percentage': float(user.part_time_percentage),
                'is_active': user.is_active,
                'created_at': user.created_at.isoformat() if user.created_at else None
            })
        
        # Attendance Events
        events = AttendanceEvent.query.all()
        data['attendance_events'] = []
        for event in events:
            data['attendance_events'].append({
                'id': event.id,
                'user_id': event.user_id,
                'event_type': event.event_type,
                'timestamp': event.timestamp.isoformat(),
                'notes': event.notes
            })
        
        # Leave Requests
        leave_requests = LeaveRequest.query.all()
        data['leave_requests'] = []
        for request in leave_requests:
            data['leave_requests'].append({
                'id': request.id,
                'user_id': request.user_id,
                'start_date': request.start_date.isoformat(),
                'end_date': request.end_date.isoformat(),
                'leave_type': request.leave_type,
                'reason': request.reason,
                'status': request.status,
                'created_at': request.created_at.isoformat() if request.created_at else None
            })
        
        # Shifts
        shifts = Shift.query.all()
        data['shifts'] = []
        for shift in shifts:
            data['shifts'].append({
                'id': shift.id,
                'user_id': shift.user_id,
                'date': shift.date.isoformat(),
                'start_time': shift.start_time.isoformat(),
                'end_time': shift.end_time.isoformat(),
                'shift_type': shift.shift_type,
                'created_at': shift.created_at.isoformat() if shift.created_at else None,
                'created_by': shift.created_by
            })
        
        # Reperibilità Shifts
        reperibilita_shifts = ReperibilitaShift.query.all()
        data['reperibilita_shifts'] = []
        for shift in reperibilita_shifts:
            data['reperibilita_shifts'].append({
                'id': shift.id,
                'user_id': shift.user_id,
                'date': shift.date.isoformat(),
                'start_time': shift.start_time.isoformat(),
                'end_time': shift.end_time.isoformat(),
                'created_at': shift.created_at.isoformat() if shift.created_at else None,
                'created_by': shift.created_by
            })
        
        # Reperibilità Interventions
        interventions = ReperibilitaIntervention.query.all()
        data['reperibilita_interventions'] = []
        for intervention in interventions:
            data['reperibilita_interventions'].append({
                'id': intervention.id,
                'user_id': intervention.user_id,
                'start_datetime': intervention.start_datetime.isoformat(),
                'end_datetime': intervention.end_datetime.isoformat() if intervention.end_datetime else None,
                'description': intervention.description,
                'shift_id': intervention.shift_id,
                'is_remote': intervention.is_remote,
                'priority': intervention.priority,
                'created_at': intervention.created_at.isoformat() if intervention.created_at else None
            })
        
        # Presidio Coverage
        presidio_coverages = PresidioCoverage.query.all()
        data['presidio_coverages'] = []
        for coverage in presidio_coverages:
            data['presidio_coverages'].append({
                'id': coverage.id,
                'start_date': coverage.start_date.isoformat(),
                'end_date': coverage.end_date.isoformat(),
                'day_of_week': coverage.day_of_week,
                'start_time': coverage.start_time.isoformat(),
                'end_time': coverage.end_time.isoformat(),
                'required_roles': coverage.required_roles,
                'description': coverage.description,
                'is_active': coverage.is_active,
                'created_by': coverage.created_by,
                'created_at': coverage.created_at.isoformat() if coverage.created_at else None
            })
        
        # Reperibilità Coverage
        reperibilita_coverages = ReperibilitaCoverage.query.all()
        data['reperibilita_coverages'] = []
        for coverage in reperibilita_coverages:
            data['reperibilita_coverages'].append({
                'id': coverage.id,
                'start_date': coverage.start_date.isoformat(),
                'end_date': coverage.end_date.isoformat(),
                'day_of_week': coverage.day_of_week,  # This model uses day_of_week (single)
                'start_time': coverage.start_time.isoformat(),
                'end_time': coverage.end_time.isoformat(),
                'required_roles': coverage.required_roles,
                'description': coverage.description,
                'is_active': coverage.is_active,
                'created_by': coverage.created_by,
                'created_at': coverage.created_at.isoformat() if coverage.created_at else None
            })
        
        # Shift Templates
        templates = ShiftTemplate.query.all()
        data['shift_templates'] = []
        for template in templates:
            data['shift_templates'].append({
                'id': template.id,
                'name': template.name,
                'description': template.description,
                'start_date': template.start_date.isoformat(),
                'end_date': template.end_date.isoformat(),
                'created_by': template.created_by,
                'created_at': template.created_at.isoformat() if template.created_at else None
            })
        
        # Holidays
        holidays = Holiday.query.all()
        data['holidays'] = []
        for holiday in holidays:
            data['holidays'].append({
                'id': holiday.id,
                'name': holiday.name,
                'day': holiday.day,
                'month': holiday.month,
                'description': holiday.description,
                'is_active': holiday.is_active
            })
        
        # Salva file JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"database_export_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Database esportato in formato JSON: {filename}")
        print(f"  - Utenti: {len(data['users'])}")
        print(f"  - Eventi presenze: {len(data['attendance_events'])}")
        print(f"  - Richieste ferie: {len(data['leave_requests'])}")
        print(f"  - Turni presidio: {len(data['shifts'])}")
        print(f"  - Turni reperibilità: {len(data['reperibilita_shifts'])}")
        print(f"  - Interventi: {len(data['reperibilita_interventions'])}")
        return filename

def export_attendance_to_csv():
    """Esporta presenze in formato CSV"""
    with app.app_context():
        events = db.session.query(AttendanceEvent, User).join(User).all()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"presenze_export_{timestamp}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['ID', 'Utente', 'Nome', 'Cognome', 'Tipo Evento', 'Data/Ora', 'Note'])
            
            for event, user in events:
                writer.writerow([
                    event.id,
                    user.username,
                    user.first_name,
                    user.last_name,
                    event.event_type,
                    event.timestamp.strftime("%d/%m/%Y %H:%M:%S"),
                    event.notes or ''
                ])
        
        print(f"✓ Presenze esportate in CSV: {filename}")
        return filename

def export_users_to_csv():
    """Esporta utenti in formato CSV"""
    with app.app_context():
        users = User.query.all()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"utenti_export_{timestamp}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['ID', 'Username', 'Email', 'Nome', 'Cognome', 'Ruolo', '% Lavoro', 'Attivo', 'Data Creazione'])
            
            for user in users:
                writer.writerow([
                    user.id,
                    user.username,
                    user.email,
                    user.first_name,
                    user.last_name,
                    user.role,
                    user.part_time_percentage,
                    'Sì' if user.is_active else 'No',
                    user.created_at.strftime("%d/%m/%Y") if user.created_at else ''
                ])
        
        print(f"✓ Utenti esportati in CSV: {filename}")
        return filename

def export_sql_dump():
    """Genera dump SQL usando SQLAlchemy"""
    with app.app_context():
        # Questo è un dump semplificato - per un dump completo serve pg_dump
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"database_dump_{timestamp}.sql"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("-- Database Dump generated by export_database.py\n")
            f.write(f"-- Generated on: {datetime.now().isoformat()}\n\n")
            
            # Per un dump SQL completo avresti bisogno di generare le CREATE TABLE e INSERT
            # statements per tutte le tabelle. Questo è un esempio base.
            f.write("-- Note: This is a simplified dump. For complete SQL dump use pg_dump\n")
            f.write("-- Use the JSON export for complete data backup\n")
        
        print(f"✓ SQL dump base creato: {filename}")
        print("  NOTA: Per un dump SQL completo usa: pg_dump $DATABASE_URL > backup.sql")
        return filename

if __name__ == "__main__":
    print("=== Export Database NS12 Workforce Management ===\n")
    
    try:
        # Export completo JSON
        json_file = export_to_json()
        
        # Export CSV separati
        csv_attendance = export_attendance_to_csv()
        csv_users = export_users_to_csv()
        
        # Info SQL dump
        export_sql_dump()
        
        print(f"\n=== Export completato ===")
        print(f"File generati:")
        print(f"  - {json_file} (backup completo)")
        print(f"  - {csv_attendance} (presenze)")
        print(f"  - {csv_users} (utenti)")
        
    except Exception as e:
        print(f"Errore durante export: {e}")