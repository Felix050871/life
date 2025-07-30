#!/usr/bin/env python3
"""
Script per popolare il database con dati di test per il mese di Luglio 2025
Crea presenze, richieste ferie, straordinari, interventi e altri dati realistici
"""

import os
import sys
from datetime import datetime, timedelta, time
import random
from werkzeug.security import generate_password_hash

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import (
    User, UserRole, Sede, WorkSchedule, AttendanceEvent, LeaveRequest, LeaveType,
    OvertimeRequest, OvertimeType, ExpenseReport, ExpenseCategory, InternalMessage,
    Holiday, ReperibilitaShift, Intervention
)

def italian_now():
    """Helper per timezone italiano"""
    return datetime.now()

def create_test_data():
    """Crea tutti i dati di test per luglio 2025"""
    
    with app.app_context():
        try:
            print("🚀 Inizio popolamento database con dati di test per Luglio 2025...")
            
            # 1. Crea ruoli se non esistono
            create_roles()
            db.session.commit()
            
            # 2. Crea sedi se non esistono
            create_sedi()
            db.session.commit()
            
            # 3. Crea orari di lavoro
            create_work_schedules()
            db.session.commit()
            
            # 4. Crea utenti di test
            create_test_users()
            db.session.commit()
            
            # 5. Crea tipologie leave e overtime
            create_leave_and_overtime_types()
            db.session.commit()
            
            # 6. Crea categorie spese
            create_expense_categories()
            db.session.commit()
            
            # 7. Crea festività luglio
            create_july_holidays()
            db.session.commit()
            
            # 8. Popola presenze per tutto luglio
            populate_july_attendance()
            db.session.commit()
            
            # 9. Crea richieste ferie/permessi
            create_leave_requests()
            db.session.commit()
            
            # 10. Crea richieste straordinari
            create_overtime_requests()
            db.session.commit()
            
            # 11. Crea note spese
            create_expense_reports()
            db.session.commit()
            
            # 12. Crea turni reperibilità
            create_reperibilita_shifts()
            db.session.commit()
            
            # 13. Crea interventi
            create_interventions()
            db.session.commit()
            
            # 14. Crea messaggi interni
            create_internal_messages()
            db.session.commit()
            
            print("✅ Popolamento database completato con successo!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Errore durante il popolamento: {e}")
            raise

def create_roles():
    """Crea ruoli base se non esistono"""
    roles_data = [
        ("Amministratore", "Amministratore del sistema", True),
        ("Responsabile", "Responsabile di sede", True),
        ("Supervisore", "Supervisore operativo", True),
        ("Operatore", "Operatore standard", True),
        ("Ospite", "Accesso limitato", True)
    ]
    
    for name, display_name, active in roles_data:
        if not UserRole.query.filter_by(name=name).first():
            role = UserRole(
                name=name,
                display_name=display_name,
                active=active,
                permissions={}  # Permissions will be set later
            )
            db.session.add(role)
            print(f"✓ Ruolo creato: {name}")

def create_sedi():
    """Crea sedi di test se non esistono"""
    sedi_data = [
        ("Sede Principale", "Via Roma 123, Milano", "Sede principale con modalità oraria", "Oraria"),
        ("Sede Turni", "Via Garibaldi 456, Milano", "Sede con modalità turnazioni", "Turni"),
        ("Sede Nord", "Via Manzoni 789, Bergamo", "Filiale nord", "Oraria")
    ]
    
    for name, address, description, tipologia in sedi_data:
        if not Sede.query.filter_by(name=name).first():
            sede = Sede(
                name=name,
                address=address,
                description=description,
                tipologia=tipologia,
                active=True
            )
            db.session.add(sede)
            print(f"✓ Sede creata: {name}")

def create_work_schedules():
    """Crea orari di lavoro standard"""
    schedules_data = [
        ("Orario Standard", "08:45", "09:15", "17:30", "18:30", [0,1,2,3,4], 1),  # Lun-Ven con range
        ("Part-time Mattino", "08:45", "09:15", "12:45", "13:15", [0,1,2,3,4], 1),
        ("Turni", "06:00", "10:00", "14:00", "22:00", [0,1,2,3,4,5,6], 2),  # Per sede turni
        ("Orario Esteso", "07:45", "08:15", "18:45", "19:15", [0,1,2,3,4], 1)
    ]
    
    for name, start_min, start_max, end_min, end_max, days, sede_id in schedules_data:
        if not WorkSchedule.query.filter_by(name=name, sede_id=sede_id).first():
            schedule = WorkSchedule(
                name=name,
                start_time_min=time.fromisoformat(start_min),
                start_time_max=time.fromisoformat(start_max),
                end_time_min=time.fromisoformat(end_min),
                end_time_max=time.fromisoformat(end_max),
                days_of_week=days,
                sede_id=sede_id,
                active=True
            )
            db.session.add(schedule)
            print(f"✓ Orario creato: {name}")

def create_test_users():
    """Crea utenti di test realistici"""
    # Get roles and sedi
    admin_role = UserRole.query.filter_by(name="Amministratore").first()
    resp_role = UserRole.query.filter_by(name="Responsabile").first()
    super_role = UserRole.query.filter_by(name="Supervisore").first()
    op_role = UserRole.query.filter_by(name="Operatore").first()
    
    sede_principale = Sede.query.filter_by(name="Sede Principale").first()
    sede_turni = Sede.query.filter_by(name="Sede Turni").first()
    sede_nord = Sede.query.filter_by(name="Sede Nord").first()
    
    orario_standard = WorkSchedule.query.filter_by(name="Orario Standard").first()
    orario_part_time = WorkSchedule.query.filter_by(name="Part-time Mattino").first()
    orario_turni = WorkSchedule.query.filter_by(name="Turni").first()
    
    users_data = [
        # Admin (già esiste, skippiamo)
        ("marco.rossi", "marco.rossi@workly.com", "Marco", "Rossi", resp_role, sede_principale, orario_standard, 100.0, False),
        ("giulia.bianchi", "giulia.bianchi@workly.com", "Giulia", "Bianchi", super_role, None, None, 100.0, True),  # Multi-sede
        ("luca.ferrari", "luca.ferrari@workly.com", "Luca", "Ferrari", op_role, sede_principale, orario_standard, 100.0, False),
        ("anna.verde", "anna.verde@workly.com", "Anna", "Verde", op_role, sede_principale, orario_part_time, 50.0, False),
        ("paolo.neri", "paolo.neri@workly.com", "Paolo", "Neri", op_role, sede_turni, orario_turni, 100.0, False),
        ("sara.gialli", "sara.gialli@workly.com", "Sara", "Gialli", resp_role, sede_nord, orario_standard, 100.0, False),
        ("davide.blu", "davide.blu@workly.com", "Davide", "Blu", op_role, sede_nord, orario_standard, 100.0, False),
        ("chiara.rosa", "chiara.rosa@workly.com", "Chiara", "Rosa", op_role, sede_principale, orario_standard, 80.0, False),
    ]
    
    for username, email, first_name, last_name, role, sede, schedule, percentage, all_sedi in users_data:
        if not User.query.filter_by(username=username).first():
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password_hash=generate_password_hash("password123"),
                role=role.name if role else "Operatore",
                sede_id=sede.id if sede else None,
                work_schedule_id=schedule.id if schedule else None,
                part_time_percentage=percentage,
                all_sedi=all_sedi,
                active=True
            )
            db.session.add(user)
            print(f"✓ Utente creato: {username} ({first_name} {last_name})")

def create_leave_and_overtime_types():
    """Crea tipologie ferie e straordinari"""
    # Tipologie ferie
    leave_types = [
        ("Ferie", "Giorni di ferie annuali", True),
        ("Permesso", "Permesso retribuito", True),
        ("Malattia", "Assenza per malattia", False),
        ("Congedo", "Congedo straordinario", False)
    ]
    
    for name, description, requires_approval in leave_types:
        if not LeaveType.query.filter_by(name=name).first():
            leave_type = LeaveType(
                name=name,
                description=description,
                requires_approval=requires_approval,
                is_active=True
            )
            db.session.add(leave_type)
            print(f"✓ Tipologia ferie creata: {name}")
    
    # Tipologie straordinari
    overtime_types = [
        ("Straordinario Standard", "Ore straordinarie normali", 1.5),
        ("Straordinario Festivo", "Lavoro nei giorni festivi", 2.0),
        ("Straordinario Notturno", "Lavoro notturno", 1.8),
        ("Reperibilità", "Servizio di reperibilità", 1.2)
    ]
    
    for name, description, multiplier in overtime_types:
        if not OvertimeType.query.filter_by(name=name).first():
            overtime_type = OvertimeType(
                name=name,
                description=description,
                hourly_rate_multiplier=multiplier,
                active=True
            )
            db.session.add(overtime_type)
            print(f"✓ Tipologia straordinario creata: {name}")

def create_expense_categories():
    """Crea categorie note spese"""
    categories = [
        ("Trasferte", "Spese per trasferte di lavoro"),
        ("Carburante", "Rifornimenti carburante"),
        ("Pasti", "Pasti di lavoro"),
        ("Materiali", "Acquisto materiali"),
        ("Telefonia", "Spese telefoniche"),
        ("Formazione", "Corsi e formazione")
    ]
    
    # Get admin user for created_by field
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        print("⚠️ Admin user not found, skipping expense categories")
        return
    
    for name, description in categories:
        if not ExpenseCategory.query.filter_by(name=name).first():
            category = ExpenseCategory(
                name=name,
                description=description,
                is_active=True,
                created_by=admin.id
            )
            db.session.add(category)
            print(f"✓ Categoria spese creata: {name}")

def create_july_holidays():
    """Crea festività di luglio 2025"""
    # Get admin user for created_by field
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        print("⚠️ Admin user not found, skipping holidays")
        return
    
    holidays = [
        ("Festa del Santo Patrono", 7, 15)  # 15 luglio - festa locale esempio
    ]
    
    for name, month, day in holidays:
        if not Holiday.query.filter_by(name=name, month=month, day=day).first():
            holiday = Holiday(
                name=name,
                month=month,
                day=day,
                is_active=True,
                created_by=admin.id,
                description="Festività di test per luglio"
            )
            db.session.add(holiday)
            print(f"✓ Festività creata: {name} ({day}/{month})")

def populate_july_attendance():
    """Popola presenze per tutto luglio 2025"""
    print("📅 Creazione presenze per Luglio 2025...")
    
    # Get all active users except admin
    users = User.query.filter(
        User.is_active == True,
        User.username != 'admin'
    ).all()
    
    # July 2025 dates (excluding weekends for most users)
    start_date = datetime(2025, 7, 1)
    end_date = datetime(2025, 7, 31)
    
    current_date = start_date
    while current_date <= end_date:
        # Skip weekends for office workers (not shift workers)
        if current_date.weekday() < 5:  # Monday=0, Friday=4
            
            for user in users:
                # Skip some days randomly (holidays, sick days, etc.)
                if random.random() < 0.1:  # 10% chance to skip
                    continue
                
                # Check if user has work schedule
                if user.work_schedule:
                    schedule = user.work_schedule
                    
                    # Generate realistic attendance times using range
                    if schedule.start_time_min and schedule.end_time_min:
                        # Random time within the range
                        start_minutes = random.randint(
                            schedule.start_time_min.hour * 60 + schedule.start_time_min.minute,
                            schedule.start_time_max.hour * 60 + schedule.start_time_max.minute
                        )
                        end_minutes = random.randint(
                            schedule.end_time_min.hour * 60 + schedule.end_time_min.minute,
                            schedule.end_time_max.hour * 60 + schedule.end_time_max.minute
                        )
                        
                        entry_time = datetime.combine(current_date.date(), time(start_minutes // 60, start_minutes % 60))
                        exit_time = datetime.combine(current_date.date(), time(end_minutes // 60, end_minutes % 60))
                        
                        # Create entry event
                        entry_event = AttendanceEvent(
                            user_id=user.id,
                            event_type='entry',
                            timestamp=entry_time,
                            notes=f"Entrata {current_date.strftime('%d/%m')}"
                        )
                        db.session.add(entry_event)
                        
                        # Create break events (around lunch time)
                        if "Standard" in schedule.name or "Esteso" in schedule.name:
                            break_start = datetime.combine(current_date.date(), time(12, random.randint(0, 15)))
                            break_end = break_start + timedelta(minutes=random.randint(45, 75))
                            
                            break_start_event = AttendanceEvent(
                                user_id=user.id,
                                event_type='break_start',
                                timestamp=break_start,
                                notes="Inizio pausa pranzo"
                            )
                            db.session.add(break_start_event)
                            
                            break_end_event = AttendanceEvent(
                                user_id=user.id,
                                event_type='break_end',
                                timestamp=break_end,
                                notes="Fine pausa pranzo"
                            )
                            db.session.add(break_end_event)
                        
                        # Create exit event
                        exit_event = AttendanceEvent(
                            user_id=user.id,
                            event_type='exit',
                            timestamp=exit_time,
                            notes=f"Uscita {current_date.strftime('%d/%m')}"
                        )
                        db.session.add(exit_event)
        
        current_date += timedelta(days=1)
    
    print(f"✓ Presenze create per tutto Luglio 2025")

def create_leave_requests():
    """Crea richieste ferie/permessi realistiche"""
    print("🏖️ Creazione richieste ferie e permessi...")
    
    users = User.query.filter(User.active == True, User.username != 'admin').all()
    leave_types = LeaveType.query.filter_by(is_active=True).all()
    
    # Create some leave requests for July
    leave_requests_data = [
        # (user_index, leave_type_name, start_date, end_date, status, reason)
        (0, "Ferie", "2025-07-15", "2025-07-19", "approved", "Vacanze estive"),
        (1, "Permesso", "2025-07-08", "2025-07-08", "approved", "Visita medica"),
        (2, "Ferie", "2025-07-22", "2025-07-26", "pending", "Ferie in famiglia"),
        (3, "Malattia", "2025-07-10", "2025-07-11", "approved", "Influenza"),
        (4, "Permesso", "2025-07-30", "2025-07-30", "pending", "Appuntamento personale"),
        (5, "Ferie", "2025-07-01", "2025-07-05", "approved", "Ponte estivo"),
    ]
    
    for user_idx, leave_type_name, start_str, end_str, status, reason in leave_requests_data:
        if user_idx < len(users):
            user = users[user_idx]
            leave_type = next((lt for lt in leave_types if lt.name == leave_type_name), None)
            
            if leave_type:
                leave_request = LeaveRequest(
                    user_id=user.id,
                    leave_type_id=leave_type.id,
                    leave_type=leave_type.name,  # Add legacy field for compatibility
                    start_date=datetime.strptime(start_str, "%Y-%m-%d").date(),
                    end_date=datetime.strptime(end_str, "%Y-%m-%d").date(),
                    reason=reason,
                    status=status,
                    created_at=italian_now() - timedelta(days=random.randint(1, 20))
                )
                db.session.add(leave_request)
                print(f"✓ Richiesta {leave_type_name} creata per {user.first_name}")

def create_overtime_requests():
    """Crea richieste straordinari"""
    print("⏰ Creazione richieste straordinari...")
    
    users = User.query.filter(User.active == True, User.username != 'admin').all()
    overtime_types = OvertimeType.query.filter_by(active=True).all()
    
    overtime_requests_data = [
        (0, "Straordinario Standard", "2025-07-12", "18:00", "20:00", "approved", "Completamento progetto urgente"),
        (1, "Straordinario Standard", "2025-07-18", "17:00", "19:30", "pending", "Supporto cliente importante"),
        (2, "Straordinario Notturno", "2025-07-25", "22:00", "02:00", "approved", "Manutenzione sistema"),
        (3, "Reperibilità", "2025-07-06", "08:00", "18:00", "approved", "Reperibilità weekend"),
        (4, "Straordinario Standard", "2025-07-29", "18:30", "21:00", "pending", "Chiusura mensile"),
    ]
    
    for user_idx, ot_type_name, date_str, start_time, end_time, status, motivation in overtime_requests_data:
        if user_idx < len(users):
            user = users[user_idx]
            ot_type = next((ot for ot in overtime_types if ot.name == ot_type_name), None)
            
            if ot_type:
                overtime_request = OvertimeRequest(
                    employee_id=user.id,
                    overtime_type_id=ot_type.id,
                    overtime_date=datetime.strptime(date_str, "%Y-%m-%d").date(),
                    start_time=datetime.strptime(start_time, "%H:%M").time(),
                    end_time=datetime.strptime(end_time, "%H:%M").time(),
                    motivation=motivation,
                    status=status,
                    created_at=italian_now() - timedelta(days=random.randint(1, 15))
                )
                db.session.add(overtime_request)
                print(f"✓ Richiesta straordinario creata per {user.first_name}")

def create_expense_reports():
    """Crea note spese di esempio"""
    print("💰 Creazione note spese...")
    
    users = User.query.filter(User.active == True, User.username != 'admin').all()
    categories = ExpenseCategory.query.filter_by(is_active=True).all()
    
    expense_data = [
        (0, "Trasferte", 85.50, "2025-07-08", "approved", "Trasferta Milano - Roma"),
        (1, "Pasti", 45.00, "2025-07-15", "pending", "Pranzo con cliente"),
        (2, "Carburante", 72.30, "2025-07-20", "approved", "Rifornimento auto aziendale"),
        (3, "Materiali", 125.80, "2025-07-12", "approved", "Acquisto materiale ufficio"),
        (4, "Telefonia", 35.90, "2025-07-25", "pending", "Ricarica telefono aziendale"),
        (5, "Formazione", 280.00, "2025-07-18", "approved", "Corso di aggiornamento"),
    ]
    
    for user_idx, cat_name, amount, date_str, status, description in expense_data:
        if user_idx < len(users):
            user = users[user_idx]
            category = next((c for c in categories if c.name == cat_name), None)
            
            if category:
                expense = ExpenseReport(
                    employee_id=user.id,
                    category_id=category.id,
                    amount=amount,
                    expense_date=datetime.strptime(date_str, "%Y-%m-%d").date(),
                    description=description,
                    status=status,
                    created_at=italian_now() - timedelta(days=random.randint(1, 20))
                )
                db.session.add(expense)
                print(f"✓ Nota spese creata per {user.first_name}: €{amount}")

def create_reperibilita_shifts():
    """Crea turni di reperibilità"""
    print("🔄 Creazione turni reperibilità...")
    
    users = User.query.filter(User.active == True, User.username != 'admin').all()
    
    # Create some shifts for July weekends
    shift_dates = [
        ("2025-07-05", "2025-07-06"),  # Weekend 1
        ("2025-07-12", "2025-07-13"),  # Weekend 2
        ("2025-07-19", "2025-07-20"),  # Weekend 3
        ("2025-07-26", "2025-07-27"),  # Weekend 4
    ]
    
    for weekend_start, weekend_end in shift_dates:
        for date_str in [weekend_start, weekend_end]:
            user = random.choice(users[:4])  # Random user from first 4
            
            # Get admin user for created_by field
            admin = User.query.filter_by(username='admin').first()
            if admin:
                shift = ReperibilitaShift(
                    user_id=user.id,
                    date=datetime.strptime(date_str, "%Y-%m-%d").date(),
                    start_time=time(8, 0),
                    end_time=time(20, 0),
                    description=f"Reperibilità {date_str}",
                    created_by=admin.id
                )
                db.session.add(shift)
                print(f"✓ Turno reperibilità creato per {user.first_name} il {date_str}")

def create_interventions():
    """Crea interventi per i turni di reperibilità"""
    print("🚨 Creazione interventi...")
    
    shifts = ReperibilitaShift.query.all()
    
    # Create some interventions
    for i, shift in enumerate(shifts[:6]):  # Create interventions for first 6 shifts
        intervention_time = datetime.combine(
            shift.date, 
            time(random.randint(10, 18), random.randint(0, 59))
        )
        
        intervention = Intervention(
            user_id=shift.user_id,
            start_datetime=intervention_time,
            end_datetime=intervention_time + timedelta(hours=random.randint(1, 3)),
            description=f"Intervento di emergenza #{i+1}",
            priority="Media",
            is_remote=True
        )
        db.session.add(intervention)
        print(f"✓ Intervento creato per il turno del {shift.date}")

def create_internal_messages():
    """Crea messaggi interni di esempio"""
    print("💬 Creazione messaggi interni...")
    
    users = User.query.filter(User.is_active == True).all()
    admin = User.query.filter_by(username='admin').first()
    
    if not admin or len(users) < 2:
        return
    
    messages_data = [
        ("Aggiornamento Orari", "Informativo", "Si comunica che dal prossimo mese gli orari di ufficio saranno modificati."),
        ("Chiusura Estiva", "Attenzione", "Ricordiamo che l'ufficio sarà chiuso dal 10 al 20 agosto."),
        ("Nuovo Sistema", "Successo", "È stato implementato il nuovo sistema di gestione presenze."),
        ("Manutenzione Programmata", "Urgente", "Manutenzione server prevista per questo weekend."),
        ("Formazione Sicurezza", "Informativo", "Corso obbligatorio di sicurezza previsto per il 15 agosto."),
    ]
    
    for title, msg_type, message in messages_data:
        # Send to random users
        recipients = random.sample(users[1:], min(3, len(users)-1))
        
        for recipient in recipients:
            internal_msg = InternalMessage(
                sender_id=admin.id,
                recipient_id=recipient.id,
                title=title,
                message=message,
                message_type=msg_type,
                created_at=italian_now() - timedelta(days=random.randint(1, 15))
            )
            db.session.add(internal_msg)
        
        print(f"✓ Messaggio '{title}' inviato a {len(recipients)} utenti")

if __name__ == "__main__":
    create_test_data()