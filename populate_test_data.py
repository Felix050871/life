#!/usr/bin/env python3
"""
Script per popolare il database Workly con dati di test realistici
Crea utenti, presenze, richieste e altri dati per testare il sistema
Versione rigenerata - Agosto 2025
"""

import os
import sys
from datetime import datetime, timedelta, time
import random
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Funzione principale per il popolamento dati"""
    try:
        from main import app
        from models import db
        import models
        from werkzeug.security import generate_password_hash
        
        with app.app_context():
            logger.info("🚀 Avvio popolamento database con dati di test...")
            
            # 1. Verifica e crea ruoli base
            create_base_roles(db, models)
            
            # 2. Verifica e crea sedi
            create_base_sedi(db, models)
            
            # 3. Crea utenti di test
            create_test_users(db, models, generate_password_hash)
            
            # 4. Crea tipologie base
            create_base_types(db, models)
            
            # 5. Crea festività
            create_holidays(db, models)
            
            # 6. Crea dati ACI se non esistenti
            create_aci_data(db, models)
            
            # 7. Crea presenze per ultimi 30 giorni
            create_attendance_data(db, models)
            
            # 8. Crea richieste varie
            create_requests_data(db, models)
            
            # 9. Crea messaggi interni
            create_internal_messages(db, models)
            
            # 10. Crea turni e reperibilità
            create_shifts_data(db, models)
            
            logger.info("✅ Popolamento database completato con successo!")
            print("\n=== RIEPILOGO DATI CREATI ===")
            
            # Mostra statistiche
            show_statistics(db, models)
            
    except Exception as e:
        logger.error(f"❌ Errore durante il popolamento: {str(e)}")
        raise

def create_base_roles(db, models):
    """Crea ruoli base se non esistono"""
    logger.info("Creazione ruoli base...")
    
    roles_data = [
        {
            'name': 'Amministratore',
            'description': 'Amministratore sistema con accesso completo',
            'permissions': {
                'can_manage_users': True,
                'can_view_all_users': True,
                'can_edit_all_users': True,  
                'can_delete_users': True,
                'can_manage_roles': True,
                'can_view_attendance': True,
                'can_edit_attendance': True,
                'can_manage_shifts': True,
                'can_view_all_shifts': True,
                'can_create_shifts': True,
                'can_edit_shifts': True,
                'can_delete_shifts': True,
                'can_manage_holidays': True,
                'can_view_reports': True,
                'can_export_data': True,
                'can_manage_sedi': True,
                'can_view_dashboard': True,
                'can_manage_leave_requests': True,
                'can_approve_leave_requests': True,
                'can_view_leave_requests': True,
                'can_create_leave_requests': True,
                'can_manage_overtime_requests': True,
                'can_approve_overtime_requests': True,
                'can_view_overtime_requests': True,
                'can_create_overtime_requests': True,
                'can_manage_mileage_requests': True,
                'can_approve_mileage_requests': True,
                'can_view_mileage_requests': True,
                'can_create_mileage_requests': True,
                'can_manage_internal_messages': True,
                'can_send_internal_messages': True,
                'can_view_internal_messages': True,
                'can_manage_aci_tables': True,
                'can_view_aci_tables': True
            }
        },
        {
            'name': 'Responsabile',
            'description': 'Responsabile area con permessi gestione team',
            'permissions': {
                'can_view_all_users': True,
                'can_edit_all_users': True,
                'can_view_attendance': True,
                'can_edit_attendance': True,
                'can_view_all_shifts': True,
                'can_create_shifts': True,
                'can_edit_shifts': True,
                'can_view_reports': True,
                'can_export_data': True,
                'can_view_dashboard': True,
                'can_approve_leave_requests': True,
                'can_view_leave_requests': True,
                'can_create_leave_requests': True,
                'can_approve_overtime_requests': True,
                'can_view_overtime_requests': True,
                'can_create_overtime_requests': True,
                'can_approve_mileage_requests': True,
                'can_view_mileage_requests': True,
                'can_create_mileage_requests': True,
                'can_send_internal_messages': True,
                'can_view_internal_messages': True,
                'can_view_aci_tables': True
            }
        },
        {
            'name': 'Supervisore',
            'description': 'Supervisore con permessi limitati di gestione',
            'permissions': {
                'can_view_attendance': True,
                'can_view_all_shifts': True,
                'can_create_shifts': True,
                'can_view_reports': True,
                'can_view_dashboard': True,
                'can_view_leave_requests': True,
                'can_create_leave_requests': True,
                'can_view_overtime_requests': True,
                'can_create_overtime_requests': True,
                'can_view_mileage_requests': True,
                'can_create_mileage_requests': True,
                'can_send_internal_messages': True,
                'can_view_internal_messages': True,
                'can_view_aci_tables': True
            }
        },
        {
            'name': 'Operatore',
            'description': 'Operatore standard',
            'permissions': {
                'can_view_attendance': True,
                'can_view_dashboard': True,
                'can_create_leave_requests': True,
                'can_create_overtime_requests': True,
                'can_create_mileage_requests': True,
                'can_view_internal_messages': True,
                'can_view_aci_tables': True
            }
        }
    ]
    
    for role_data in roles_data:
        existing_role = models.UserRole.query.filter_by(name=role_data['name']).first()
        if not existing_role:
            role = models.UserRole(
                name=role_data['name'],
                description=role_data['description'],
                **role_data['permissions']
            )
            db.session.add(role)
            logger.info(f"  ➕ Creato ruolo: {role_data['name']}")
        else:
            logger.info(f"  ✓ Ruolo esistente: {role_data['name']}")
    
    db.session.commit()

def create_base_sedi(db, models):
    """Crea sedi base se non esistono"""
    logger.info("Creazione sedi base...")
    
    sedi_data = [
        {
            'name': 'Sede Centrale Roma',
            'address': 'Via Roma 123, 00100 Roma RM',
            'description': 'Sede principale dell\'azienda a Roma',
            'active': True,
            'tipologia': 'centrale'
        },
        {
            'name': 'Filiale Milano',
            'address': 'Via Milano 456, 20100 Milano MI',
            'description': 'Filiale operativa di Milano',
            'active': True,
            'tipologia': 'filiale'
        },
        {
            'name': 'Ufficio Napoli',
            'address': 'Via Napoli 789, 80100 Napoli NA',
            'description': 'Ufficio periferico di Napoli',
            'active': True,
            'tipologia': 'ufficio'
        }
    ]
    
    for sede_data in sedi_data:
        existing_sede = models.Sede.query.filter_by(name=sede_data['name']).first()
        if not existing_sede:
            sede = models.Sede(**sede_data)
            db.session.add(sede)
            logger.info(f"  ➕ Creata sede: {sede_data['name']}")
        else:
            logger.info(f"  ✓ Sede esistente: {sede_data['name']}")
    
    db.session.commit()

def create_test_users(db, models, generate_password_hash):
    """Crea utenti di test"""
    logger.info("Creazione utenti di test...")
    
    # Ottieni ruoli e sedi
    admin_role = models.UserRole.query.filter_by(name='Amministratore').first()
    resp_role = models.UserRole.query.filter_by(name='Responsabile').first()
    sup_role = models.UserRole.query.filter_by(name='Supervisore').first()
    op_role = models.UserRole.query.filter_by(name='Operatore').first()
    
    sede_roma = models.Sede.query.filter_by(name='Sede Centrale Roma').first()
    sede_milano = models.Sede.query.filter_by(name='Filiale Milano').first()
    sede_napoli = models.Sede.query.filter_by(name='Ufficio Napoli').first()
    
    users_data = [
        {
            'first_name': 'Mario',
            'last_name': 'Rossi',
            'email': 'mario.rossi@workly.local',
            'username': 'mario.rossi',
            'role': resp_role,
            'sede': sede_roma,
            'modalita_lavoro': 'ORARIA'
        },
        {
            'first_name': 'Anna',
            'last_name': 'Verdi',
            'email': 'anna.verdi@workly.local',
            'username': 'anna.verdi',
            'role': sup_role,
            'sede': sede_milano,
            'modalita_lavoro': 'ORARIA'
        },
        {
            'first_name': 'Giuseppe',
            'last_name': 'Bianchi',
            'email': 'giuseppe.bianchi@workly.local',
            'username': 'giuseppe.bianchi',
            'role': op_role,
            'sede': sede_roma,
            'modalita_lavoro': 'TURNI'
        },
        {
            'first_name': 'Maria',
            'last_name': 'Neri',
            'email': 'maria.neri@workly.local',
            'username': 'maria.neri',
            'role': op_role,
            'sede': sede_napoli,
            'modalita_lavoro': 'ORARIA'
        },
        {
            'first_name': 'Francesco',
            'last_name': 'Gialli',
            'email': 'francesco.gialli@workly.local',
            'username': 'francesco.gialli',
            'role': op_role,
            'sede': sede_milano,
            'modalita_lavoro': 'TURNI'
        }
    ]
    
    password = 'Password123!'  # Password di test standard
    
    for user_data in users_data:
        existing_user = models.User.query.filter_by(username=user_data['username']).first()
        if not existing_user:
            user = models.User(
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                email=user_data['email'],
                username=user_data['username'],
                password_hash=generate_password_hash(password),
                role=user_data['role'].name if user_data['role'] else 'Operatore',
                active=True,
                all_sedi=False,
                part_time_percentage=100.0
            )
            db.session.add(user)
            db.session.flush()
            
            # Associa alla sede principale tramite sede_id
            if user_data['sede']:
                user.sede_id = user_data['sede'].id
            
            logger.info(f"  ➕ Creato utente: {user_data['first_name']} {user_data['last_name']}")
        else:
            logger.info(f"  ✓ Utente esistente: {user_data['first_name']} {user_data['last_name']}")
    
    db.session.commit()

def create_base_types(db, models):
    """Crea tipologie base per leave, overtime, expense"""
    logger.info("Creazione tipologie base...")
    
    # Tipologie ferie/permessi
    leave_types = [
        {'name': 'Ferie', 'description': 'Ferie annuali', 'is_active': True},
        {'name': 'Permesso', 'description': 'Permesso personale', 'is_active': True},
        {'name': 'Malattia', 'description': 'Congedo per malattia', 'is_active': True},
        {'name': 'Lutto', 'description': 'Congedo per lutto', 'is_active': True}
    ]
    
    for lt_data in leave_types:
        existing = models.LeaveType.query.filter_by(name=lt_data['name']).first()
        if not existing:
            leave_type = models.LeaveType(**lt_data)
            db.session.add(leave_type)
            logger.info(f"  ➕ Creata tipologia ferie: {lt_data['name']}")
    
    # Tipologie straordinari - usa 'active' invece di 'is_active'
    overtime_types = [
        {'name': 'Straordinario Feriale', 'description': 'Lavoro straordinario nei giorni feriali', 'active': True},
        {'name': 'Straordinario Festivo', 'description': 'Lavoro straordinario nei giorni festivi', 'active': True},
        {'name': 'Reperibilità', 'description': 'Ore di reperibilità', 'active': True}
    ]
    
    for ot_data in overtime_types:
        existing = models.OvertimeType.query.filter_by(name=ot_data['name']).first()
        if not existing:
            # Crea solo con campi base
            overtime_type = models.OvertimeType(
                name=ot_data['name'],
                description=ot_data['description']
            )
            db.session.add(overtime_type)
            logger.info(f"  ➕ Creata tipologia straordinari: {ot_data['name']}")
    
    # Categorie spese - model non presente, le saltiamo per ora
    logger.info("  ⚠️ Categorie spese saltate - modello non disponibile")
    
    db.session.commit()

def create_holidays(db, models):
    """Crea festività per l'anno corrente"""
    logger.info("Creazione festività...")
    
    current_year = datetime.now().year
    holidays_data = [
        {'date': f'{current_year}-01-01', 'name': 'Capodanno', 'description': 'Primo gennaio'},
        {'date': f'{current_year}-01-06', 'name': 'Epifania', 'description': 'Befana'},
        {'date': f'{current_year}-04-25', 'name': 'Liberazione', 'description': '25 Aprile'},
        {'date': f'{current_year}-05-01', 'name': 'Festa del Lavoro', 'description': '1 Maggio'},
        {'date': f'{current_year}-06-02', 'name': 'Festa della Repubblica', 'description': '2 Giugno'},
        {'date': f'{current_year}-08-15', 'name': 'Ferragosto', 'description': '15 Agosto'},
        {'date': f'{current_year}-11-01', 'name': 'Ognissanti', 'description': '1 Novembre'},
        {'date': f'{current_year}-12-08', 'name': 'Immacolata', 'description': '8 Dicembre'},
        {'date': f'{current_year}-12-25', 'name': 'Natale', 'description': '25 Dicembre'},
        {'date': f'{current_year}-12-26', 'name': 'Santo Stefano', 'description': '26 Dicembre'}
    ]
    
    for holiday_data in holidays_data:
        date_obj = datetime.strptime(holiday_data['date'], '%Y-%m-%d').date()
        existing = models.Holiday.query.filter_by(name=holiday_data['name']).first()
        if not existing:
            holiday = models.Holiday(
                name=holiday_data['name'],
                month=date_obj.month,
                day=date_obj.day,
                description=holiday_data['description'],
                is_active=True,
                created_by=1  # ID admin di default
            )
            db.session.add(holiday)
            logger.info(f"  ➕ Creata festività: {holiday_data['name']}")
    
    db.session.commit()

def create_aci_data(db, models):
    """Crea dati ACI di base se non esistenti"""
    logger.info("Verifica dati ACI...")
    
    aci_count = models.ACITable.query.count()
    if aci_count < 10:
        logger.info("  ➕ Creazione dati ACI di esempio...")
        
        # Alcuni dati ACI di esempio
        aci_data = [
            {'veicolo': 'FIAT PANDA', 'alimentazione': 'Benzina', 'cilindrata': '1.2', 'costo_km': 0.4532},
            {'veicolo': 'VOLKSWAGEN GOLF', 'alimentazione': 'Benzina', 'cilindrata': '1.4', 'costo_km': 0.5123},
            {'veicolo': 'FORD FOCUS', 'alimentazione': 'Diesel', 'cilindrata': '1.6', 'costo_km': 0.4891},
            {'veicolo': 'TOYOTA YARIS', 'alimentazione': 'Ibrida', 'cilindrata': '1.5', 'costo_km': 0.4234},
            {'veicolo': 'OPEL CORSA', 'alimentazione': 'Benzina', 'cilindrata': '1.0', 'costo_km': 0.4123}
        ]
        
        for aci in aci_data:
            aci_table = models.ACITable(
                veicolo=aci['veicolo'],
                alimentazione=aci['alimentazione'], 
                cilindrata=aci['cilindrata'],
                costo_km=aci['costo_km']
            )
            db.session.add(aci_table)
        
        db.session.commit()
        logger.info(f"  ✓ Creati {len(aci_data)} record ACI")
    else:
        logger.info(f"  ✓ Dati ACI esistenti: {aci_count} record")

def create_attendance_data(db, models):
    """Crea dati presenze per gli ultimi 30 giorni"""
    logger.info("Creazione dati presenze ultimi 30 giorni...")
    
    users = models.User.query.filter_by(active=True).all()
    if not users:
        logger.warning("  ⚠️ Nessun utente trovato per creare presenze")
        return
    
    start_date = datetime.now() - timedelta(days=30)
    end_date = datetime.now()
    
    created_count = 0
    for user in users:
        current_date = start_date
        while current_date <= end_date:
            # Salta weekend con probabilità 80%
            if current_date.weekday() >= 5 and random.random() < 0.8:
                current_date += timedelta(days=1)
                continue
            
            # Verifica se esistono già presenze per questo utente/giorno
            existing = models.AttendanceEvent.query.filter_by(
                user_id=user.id,
                date=current_date.date()
            ).first()
            
            if not existing:
                # Crea entrata (clock_in)
                entry_time_obj = time(random.randint(7, 9), random.randint(0, 59))
                entry_datetime = datetime.combine(current_date.date(), entry_time_obj)
                entry_event = models.AttendanceEvent(
                    user_id=user.id,
                    date=current_date.date(),
                    timestamp=entry_datetime,
                    event_type='clock_in',
                    sede_id=user.sede_id,
                    notes='Entrata automatica - Test data'
                )
                db.session.add(entry_event)
                
                # Crea uscita (clock_out) - 8-9 ore dopo
                work_hours = random.randint(8, 9)
                exit_datetime = entry_datetime + timedelta(hours=work_hours)
                exit_event = models.AttendanceEvent(
                    user_id=user.id,
                    date=current_date.date(),
                    timestamp=exit_datetime,
                    event_type='clock_out',
                    sede_id=user.sede_id,
                    notes='Uscita automatica - Test data'
                )
                db.session.add(exit_event)
                created_count += 2
            
            current_date += timedelta(days=1)
    
    db.session.commit()
    logger.info(f"  ✓ Creati {created_count} eventi presenza")

def create_requests_data(db, models):
    """Crea richieste di ferie, straordinari, rimborsi"""
    logger.info("Creazione richieste varie...")
    
    users = models.User.query.filter_by(active=True).all()
    if not users:
        return
    
    # Richieste ferie
    leave_types = models.LeaveType.query.all()
    if leave_types:
        for _ in range(random.randint(5, 10)):
            user = random.choice(users)
            leave_type = random.choice(leave_types)
            start_date = datetime.now() + timedelta(days=random.randint(1, 60))
            end_date = start_date + timedelta(days=random.randint(1, 5))
            
            # Usa un nome abbreviato per rispettare il limite di 50 char
            leave_type_name = leave_type.name[:40] if len(leave_type.name) > 40 else leave_type.name
            
            leave_request = models.LeaveRequest(
                user_id=user.id,
                leave_type_id=leave_type.id,
                leave_type=leave_type_name,
                start_date=start_date.date(),
                end_date=end_date.date(),
                reason=f'Richiesta {leave_type_name} - Test data',
                status=random.choice(['pending', 'approved', 'rejected']),
                created_at=datetime.now() - timedelta(days=random.randint(1, 30))
            )
            db.session.add(leave_request)
    
    # Richieste straordinari
    overtime_types = models.OvertimeType.query.all()
    if overtime_types:
        for _ in range(random.randint(8, 15)):
            user = random.choice(users)
            overtime_type = random.choice(overtime_types)
            work_date = datetime.now() - timedelta(days=random.randint(1, 30))
            
            overtime_request = models.OvertimeRequest(
                employee_id=user.id,
                overtime_type_id=overtime_type.id,
                overtime_date=work_date.date(),
                start_time=time(random.randint(17, 19), 0),
                end_time=time(random.randint(20, 23), 0),
                motivation=f'Lavoro straordinario {overtime_type.name} - Test data',
                status=random.choice(['pending', 'approved', 'rejected']),
                created_at=work_date
            )
            db.session.add(overtime_request)
    
    db.session.commit()
    logger.info("  ✓ Richieste create")

def create_internal_messages(db, models):
    """Crea messaggi interni di test"""
    logger.info("Creazione messaggi interni...")
    
    users = models.User.query.filter_by(active=True).all()
    if len(users) < 2:
        return
    
    messages = [
        "Riunione di team programmata per domani alle 14:00",
        "Ricordo di compilare i timesheet entro venerdì",
        "Nuove procedure di sicurezza in vigore da lunedì",
        "Formazione obbligatoria sui nuovi sistemi",
        "Aggiornamento software previsto per il weekend"
    ]
    
    for _ in range(random.randint(5, 10)):
        sender = random.choice(users)
        recipients = [u for u in users if u.id != sender.id]
        recipient = random.choice(recipients) if recipients else sender
        
        selected_message = random.choice(messages)
        message = models.InternalMessage(
            sender_id=sender.id,
            recipient_id=recipient.id,
            title=f"Comunicazione: {selected_message[:30]}",
            message=selected_message,
            message_type='general',
            created_at=datetime.now() - timedelta(days=random.randint(1, 30))
        )
        db.session.add(message)
    
    db.session.commit()
    logger.info("  ✓ Messaggi interni creati")

def create_shifts_data(db, models):
    """Crea alcuni turni di esempio"""
    logger.info("Creazione turni di esempio...")
    
    users = models.User.query.filter_by(active=True).all()
    sedi = models.Sede.query.all()
    
    if not users or not sedi:
        logger.info("  ⚠️ Nessun utente o sede per creare turni")
        return
    
    for _ in range(random.randint(10, 20)):
        user = random.choice(users)
        sede = random.choice(sedi)
        shift_date = datetime.now() + timedelta(days=random.randint(1, 30))
        
        shift = models.Shift(
            user_id=user.id,
            date=shift_date.date(),
            start_time=time(random.choice([6, 7, 8, 14, 22]), 0),
            end_time=time(random.choice([14, 15, 16, 22, 6]), 0),
            shift_type=random.choice(['mattina', 'pomeriggio', 'notte']),
            created_at=datetime.now(),
            created_by=1  # ID admin di default
        )
        db.session.add(shift)
    
    db.session.commit()
    logger.info("  ✓ Turni creati")

def show_statistics(db, models):
    """Mostra statistiche dei dati creati"""
    stats = {
        'Ruoli': models.UserRole.query.count(),
        'Utenti': models.User.query.count(),
        'Sedi': models.Sede.query.count(),
        'Eventi Presenza': models.AttendanceEvent.query.count(),
        'Richieste Ferie': models.LeaveRequest.query.count(),
        'Richieste Straordinari': models.OvertimeRequest.query.count(),
        'Messaggi Interni': models.InternalMessage.query.count(),
        'Turni': models.Shift.query.count(),
        'Festività': models.Holiday.query.count(),
        'Dati ACI': models.ACITable.query.count()
    }
    
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    print(f"\n✅ Database popolato con successo!")
    print(f"👤 Utenti di test creati con password: Password123!")
    print(f"🔐 Accesso admin esistente o creato durante installazione")

if __name__ == "__main__":
    main()