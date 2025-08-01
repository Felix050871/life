#!/usr/bin/env python3
"""
Script per rigenerare TUTTI gli script installazione
con database completamente corretto (solo campo 'active')
"""

import os
import shutil
from datetime import datetime

def regenerate_populate_test_data():
    """Rigenera populate_test_data.py con campi corretti"""
    
    script_content = '''#!/usr/bin/env python3
"""
Script per popolare il database Workly con dati di test
AGGIORNATO: Tutti i campi ora usano 'active' invece di 'is_active'
"""

import os
import sys
from datetime import datetime, date, timedelta
import random

def populate_database():
    """Popola database con dati di test usando campi corretti"""
    
    try:
        from main import app
        
        with app.app_context():
            from models import (
                db, User, UserRole, Sede, AttendanceEvent, LeaveRequest, LeaveType,
                OvertimeRequest, OvertimeType, InternalMessage, Shift, Holiday,
                MileageRequest, ExpenseCategory, ExpenseReport, AciTable,
                WorkSchedule
            )
            from werkzeug.security import generate_password_hash
            
            print("[INFO] Inizializzazione database per dati test...")
            db.create_all()
            
            print("[INFO] Creazione dati test...")
            
            # 1. Sedi
            sedi = [
                Sede(name="Sede Centrale", address="Via Roma 1", description="Sede principale", active=True, tipologia="Oraria"),
                Sede(name="Filiale Nord", address="Via Milano 15", description="Filiale settentrionale", active=True, tipologia="Turni"),
                Sede(name="Filiale Sud", address="Via Napoli 32", description="Filiale meridionale", active=True, tipologia="Oraria")
            ]
            
            for sede in sedi:
                db.session.add(sede)
            db.session.flush()
            
            # 2. UserRole con campo 'active'
            roles = [
                UserRole(
                    name="Amministratore",
                    display_name="Amministratore Sistema",
                    description="Accesso completo al sistema",
                    active=True,
                    permissions={
                        "can_manage_users": True,
                        "can_view_all_users": True,
                        "can_edit_all_users": True,
                        "can_delete_users": True,
                        "can_manage_roles": True,
                        "can_view_attendance": True,
                        "can_edit_attendance": True,
                        "can_manage_shifts": True,
                        "can_view_all_shifts": True,
                        "can_create_shifts": True,
                        "can_edit_shifts": True,
                        "can_delete_shifts": True,
                        "can_manage_holidays": True,
                        "can_view_reports": True,
                        "can_export_data": True,
                        "can_manage_sedi": True,
                        "can_view_dashboard": True
                    }
                ),
                UserRole(
                    name="Responsabile",
                    display_name="Responsabile Operativo",
                    description="Gestione operativa e approvazioni",
                    active=True,
                    permissions={
                        "can_view_all_users": True,
                        "can_edit_all_users": False,
                        "can_view_attendance": True,
                        "can_edit_attendance": True,
                        "can_manage_shifts": True,
                        "can_view_all_shifts": True,
                        "can_create_shifts": True,
                        "can_edit_shifts": True,
                        "can_approve_leave_requests": True,
                        "can_view_reports": True,
                        "can_export_data": True
                    }
                )
            ]
            
            for role in roles:
                db.session.add(role)
            db.session.flush()
            
            # 3. Work Schedule
            schedules = [
                WorkSchedule(
                    sede_id=sedi[0].id,
                    name="Orario Standard",
                    start_time=datetime.strptime("09:00", "%H:%M").time(),
                    end_time=datetime.strptime("18:00", "%H:%M").time(),
                    description="Orario di lavoro standard",
                    active=True,
                    days_of_week=[1,2,3,4,5]
                )
            ]
            
            for schedule in schedules:
                db.session.add(schedule)
            db.session.flush()
            
            # 4. ACI Table
            aci_vehicles = [
                AciTable(
                    tipologia="Berlina",
                    marca="Fiat",
                    modello="500",
                    costo_km=0.3450,
                    fringe_benefit_10=1200.00,
                    fringe_benefit_25=2400.00,
                    fringe_benefit_30=2800.00,
                    fringe_benefit_50=4200.00
                ),
                AciTable(
                    tipologia="SUV",
                    marca="Alfa Romeo",
                    modello="Stelvio",
                    costo_km=0.4250,
                    fringe_benefit_10=1800.00,
                    fringe_benefit_25=3200.00,
                    fringe_benefit_30=3600.00,
                    fringe_benefit_50=5400.00
                )
            ]
            
            for vehicle in aci_vehicles:
                db.session.add(vehicle)
            db.session.flush()
            
            # 5. Users con campo 'active'
            users = []
            for i in range(1, 23):
                user = User(
                    username=f"user{i:02d}",
                    email=f"user{i:02d}@workly.com",
                    password_hash=generate_password_hash("Password123!"),
                    first_name=f"Nome{i}",
                    last_name=f"Cognome{i}",
                    role="Operatore" if i > 2 else ("Amministratore" if i == 1 else "Responsabile"),
                    sede_id=sedi[i % len(sedi)].id,
                    active=True,  # CAMPO CORRETTO
                    part_time_percentage=100.0 if i % 5 != 0 else 50.0,
                    all_sedi=i <= 2,
                    work_schedule_id=schedules[0].id,
                    aci_vehicle_id=aci_vehicles[i % len(aci_vehicles)].id
                )
                users.append(user)
                db.session.add(user)
            
            db.session.flush()
            
            # 6. Expense Categories con campo 'active'
            categories = [
                ExpenseCategory(name="Trasporto", description="Spese di trasporto", active=True, created_by=users[0].id),
                ExpenseCategory(name="Vitto", description="Spese per pasti", active=True, created_by=users[0].id),
                ExpenseCategory(name="Alloggio", description="Spese per alloggio", active=True, created_by=users[0].id)
            ]
            
            for category in categories:
                db.session.add(category)
            db.session.flush()
            
            # 7. Leave Types con campo 'active'
            leave_types = [
                LeaveType(name="Ferie", description="Ferie annuali", requires_approval=True, active=True),
                LeaveType(name="Permesso", description="Permesso breve", requires_approval=True, active=True),
                LeaveType(name="Malattia", description="Assenza per malattia", requires_approval=False, active=True)
            ]
            
            for leave_type in leave_types:
                db.session.add(leave_type)
            db.session.flush()
            
            # 8. Overtime Types con campo 'active'
            overtime_types = [
                OvertimeType(name="Straordinario Normale", description="Straordinario standard", hourly_rate_multiplier=1.25, active=True),
                OvertimeType(name="Straordinario Festivo", description="Straordinario in giorni festivi", hourly_rate_multiplier=1.50, active=True)
            ]
            
            for ot_type in overtime_types:
                db.session.add(ot_type)
            db.session.flush()
            
            # 9. Holidays con campo 'active'
            holidays = [
                Holiday(name="Capodanno", month=1, day=1, active=True, description="Primo dell'anno", created_by=users[0].id, sede_id=None),
                Holiday(name="Epifania", month=1, day=6, active=True, description="Befana", created_by=users[0].id, sede_id=None),
                Holiday(name="Festa della Liberazione", month=4, day=25, active=True, description="25 Aprile", created_by=users[0].id, sede_id=None),
                Holiday(name="Festa del Lavoro", month=5, day=1, active=True, description="1 Maggio", created_by=users[0].id, sede_id=None),
                Holiday(name="Festa della Repubblica", month=6, day=2, active=True, description="2 Giugno", created_by=users[0].id, sede_id=None),
                Holiday(name="Ferragosto", month=8, day=15, active=True, description="15 Agosto", created_by=users[0].id, sede_id=None),
                Holiday(name="Ognissanti", month=11, day=1, active=True, description="1 Novembre", created_by=users[0].id, sede_id=None),
                Holiday(name="Immacolata Concezione", month=12, day=8, active=True, description="8 Dicembre", created_by=users[0].id, sede_id=None),
                Holiday(name="Natale", month=12, day=25, active=True, description="25 Dicembre", created_by=users[0].id, sede_id=None),
                Holiday(name="Santo Stefano", month=12, day=26, active=True, description="26 Dicembre", created_by=users[0].id, sede_id=None)
            ]
            
            for holiday in holidays:
                db.session.add(holiday)
            db.session.flush()
            
            # 10. Attendance Events - Genero 1200+ record
            print("[INFO] Generazione 1200+ eventi presenza...")
            attendance_count = 0
            for user in users[:15]:  # Solo primi 15 utenti
                for days_back in range(90):  # Ultimi 90 giorni
                    event_date = date.today() - timedelta(days=days_back)
                    
                    # Skip weekend
                    if event_date.weekday() >= 5:
                        continue
                    
                    # Clock-in mattina
                    clock_in_time = datetime.combine(event_date, datetime.strptime("08:30", "%H:%M").time()) + timedelta(minutes=random.randint(-15, 15))
                    clock_in = AttendanceEvent(
                        user_id=user.id,
                        date=event_date,
                        event_type="clock_in",
                        timestamp=clock_in_time,
                        notes=f"Entrata {user.username}",
                        sede_id=user.sede_id
                    )
                    db.session.add(clock_in)
                    attendance_count += 1
                    
                    # Clock-out sera
                    clock_out_time = datetime.combine(event_date, datetime.strptime("17:30", "%H:%M").time()) + timedelta(minutes=random.randint(-30, 60))
                    clock_out = AttendanceEvent(
                        user_id=user.id,
                        date=event_date,
                        event_type="clock_out",
                        timestamp=clock_out_time,
                        notes=f"Uscita {user.username}",
                        sede_id=user.sede_id
                    )
                    db.session.add(clock_out)
                    attendance_count += 1
            
            db.session.flush()
            print(f"[OK] Creati {attendance_count} eventi presenza")
            
            # 11. Leave Requests
            leave_requests = []
            for user in users[:12]:
                for i in range(5):
                    start_date = date.today() + timedelta(days=random.randint(1, 60))
                    end_date = start_date + timedelta(days=random.randint(1, 5))
                    
                    leave_req = LeaveRequest(
                        user_id=user.id,
                        start_date=start_date,
                        end_date=end_date,
                        leave_type="Ferie",
                        reason=f"Richiesta ferie {i+1} per {user.username}",
                        status=random.choice(["pending", "approved", "rejected"]),
                        approved_by=users[1].id if random.choice([True, False]) else None,
                        leave_type_id=leave_types[0].id
                    )
                    leave_requests.append(leave_req)
                    db.session.add(leave_req)
            
            db.session.flush()
            
            # 12. Overtime Requests
            overtime_requests = []
            for user in users[:12]:
                for i in range(5):
                    overtime_date = date.today() + timedelta(days=random.randint(-30, 30))
                    
                    overtime_req = OvertimeRequest(
                        employee_id=user.id,
                        overtime_date=overtime_date,
                        start_time=datetime.strptime("18:00", "%H:%M").time(),
                        end_time=datetime.strptime("20:00", "%H:%M").time(),
                        motivation=f"Straordinario per progetto urgente - {user.username}",
                        overtime_type_id=overtime_types[0].id,
                        status=random.choice(["pending", "approved", "rejected"]),
                        approved_by=users[1].id if random.choice([True, False]) else None
                    )
                    overtime_requests.append(overtime_req)
                    db.session.add(overtime_req)
            
            db.session.flush()
            
            # 13. Mileage Requests
            mileage_requests = []
            for user in users[:10]:
                for i in range(3):
                    travel_date = date.today() + timedelta(days=random.randint(-15, 15))
                    
                    mileage_req = MileageRequest(
                        user_id=user.id,
                        travel_date=travel_date,
                        route_addresses=[
                            {"address": "Via Roma 1, Milano", "latitude": 45.4642, "longitude": 9.1900},
                            {"address": "Via Venezia 15, Roma", "latitude": 41.9028, "longitude": 12.4964}
                        ],
                        total_km=random.uniform(50.0, 300.0),
                        calculated_km=None,
                        is_km_manual=False,
                        vehicle_id=aci_vehicles[0].id,
                        vehicle_description="Fiat 500",
                        cost_per_km=0.3450,
                        total_amount=random.uniform(20.0, 100.0),
                        purpose=f"Trasferta di lavoro {i+1}",
                        notes=f"Note trasferta {user.username}",
                        status=random.choice(["pending", "approved", "rejected"]),
                        approved_by=users[1].id if random.choice([True, False]) else None
                    )
                    mileage_requests.append(mileage_req)
                    db.session.add(mileage_req)
            
            db.session.flush()
            
            # 14. Internal Messages
            messages = []
            for i in range(36):
                recipient = random.choice(users)
                sender = random.choice(users[:3])
                
                message = InternalMessage(
                    recipient_id=recipient.id,
                    sender_id=sender.id,
                    title=f"Messaggio interno {i+1}",
                    message=f"Contenuto del messaggio interno numero {i+1}. Questo è un messaggio di test per verificare il sistema di messaggistica.",
                    message_type=random.choice(["general", "approval", "notification"]),
                    is_read=random.choice([True, False])
                )
                messages.append(message)
                db.session.add(message)
            
            db.session.flush()
            
            # 15. Shifts
            shifts = []
            for user in users[:8]:
                for days_ahead in range(30):  # Prossimi 30 giorni
                    shift_date = date.today() + timedelta(days=days_ahead)
                    
                    # Skip weekend
                    if shift_date.weekday() >= 5:
                        continue
                    
                    shift = Shift(
                        user_id=user.id,
                        date=shift_date,
                        start_time=datetime.strptime("08:00", "%H:%M").time(),
                        end_time=datetime.strptime("16:00", "%H:%M").time(),
                        shift_type="Normale",
                        created_by=users[1].id
                    )
                    shifts.append(shift)
                    db.session.add(shift)
            
            db.session.flush()
            
            # Commit finale
            db.session.commit()
            
            print(f"[OK] Database popolato con successo!")
            print(f"[OK] Creati {len(users)} utenti")
            print(f"[OK] Creati {attendance_count} eventi presenza")
            print(f"[OK] Creati {len(leave_requests)} richieste ferie")
            print(f"[OK] Creati {len(overtime_requests)} richieste straordinario")
            print(f"[OK] Creati {len(mileage_requests)} richieste rimborso chilometrico")
            print(f"[OK] Creati {len(messages)} messaggi interni")
            print(f"[OK] Creati {len(shifts)} turni")
            print(f"[OK] Creati {len(holidays)} festività")
            print(f"[OK] Password test per tutti gli utenti: 'Password123!'")
            
            return True
            
    except Exception as e:
        print(f"[ERRORE] Errore durante il popolamento database: {e}")
        return False

if __name__ == "__main__":
    print("=== SCRIPT POPOLAMENTO DATABASE WORKLY (CORRECTED) ===")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("IMPORTANTE: Tutti i campi ora usano 'active' invece di 'is_active'")
    print()
    
    if populate_database():
        print("✓ Popolamento database completato con successo")
    else:
        print("✗ Errore durante il popolamento database")
        sys.exit(1)
'''
    
    # Scrivi il file aggiornato
    with open('populate_test_data.py', 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    return True

def main():
    """Rigenera tutti gli script con database corretto"""
    
    print("=== RIGENERAZIONE SCRIPT INSTALLAZIONE CORRETTI ===")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. Rigenera populate_test_data.py
    print("1. Rigenerazione populate_test_data.py...")
    if regenerate_populate_test_data():
        print("✓ populate_test_data.py aggiornato")
    else:
        print("✗ Errore aggiornamento populate_test_data.py")
        return False
    
    # 2. Crea pacchetto finale completo
    print("2. Creazione pacchetto installazione finale...")
    
    PACKAGE_NAME = f"workly-installation-final-corrected-{datetime.now().strftime('%Y%m%d')}"
    TEMP_DIR = f"/tmp/{PACKAGE_NAME}"
    
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # File applicazione essenziali
    essential_files = [
        'main.py', 'models.py', 'forms.py', 'routes.py', 'utils.py', 
        'api_routes.py', 'config.py'
    ]
    
    for file in essential_files:
        if os.path.exists(file):
            shutil.copy2(file, TEMP_DIR)
    
    # Directory statiche
    for dir_name in ['templates', 'static']:
        if os.path.exists(dir_name):
            shutil.copytree(dir_name, os.path.join(TEMP_DIR, dir_name))
    
    # Script installazione corretti
    install_files = [
        'install.sh', 'install.bat', 'install_local.sh', 'install_local.bat'
    ]
    
    for file in install_files:
        if os.path.exists(file):
            shutil.copy2(file, TEMP_DIR)
            # Assicura permessi esecuzione per script Unix
            if file.endswith('.sh'):
                os.chmod(os.path.join(TEMP_DIR, file), 0o755)
    
    # Script database corretti
    database_files = [
        'initialize_database.py',
        'workly_database_schema_corrected_20250801_110528.sql',
        'fix_database_inconsistencies_20250801_110528.sql',
        'README_DATABASE_CREATION.md',
        'README_DATABASE_FIXES.md'
    ]
    
    for file in database_files:
        if os.path.exists(file):
            shutil.copy2(file, TEMP_DIR)
    
    # Script popolamento dati corretto
    shutil.copy2('populate_test_data.py', TEMP_DIR)
    
    # File di configurazione
    config_files = [
        'requirements.txt', 'pyproject.toml', '.replit', 'replit.nix'
    ]
    
    for file in config_files:
        if os.path.exists(file):
            shutil.copy2(file, TEMP_DIR)
    
    # Documentazione
    doc_files = [
        'README_INSTALLAZIONE_LOCALE.md', 'INSTALLATION_GUIDE_LOCAL.md', 
        'README.md', 'INSTALLATION_GUIDE.md', 'VERSION.md', 'PACKAGE_CONTENTS.md'
    ]
    
    for file in doc_files:
        if os.path.exists(file):
            try:
                shutil.copy2(file, TEMP_DIR)
            except FileNotFoundError:
                pass  # File opzionale
    
    # Crea archivio finale
    import subprocess
    
    result = subprocess.run([
        'tar', '-czf', f'{PACKAGE_NAME}.tar.gz', '-C', '/tmp', PACKAGE_NAME
    ], cwd='/home/runner/workspace', capture_output=True, text=True)
    
    if result.returncode == 0:
        # Pulizia
        shutil.rmtree(TEMP_DIR)
        
        print(f"✓ Pacchetto finale creato: {PACKAGE_NAME}.tar.gz")
        
        # Mostra dimensione
        size_result = subprocess.run([
            'ls', '-lh', f'{PACKAGE_NAME}.tar.gz'
        ], cwd='/home/runner/workspace', capture_output=True, text=True)
        
        if size_result.returncode == 0:
            print(f"  Dimensione: {size_result.stdout.split()[4]}")
        
        return True
    else:
        print(f"✗ Errore creazione pacchetto: {result.stderr}")
        return False

if __name__ == "__main__":
    main()