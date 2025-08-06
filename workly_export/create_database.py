#!/usr/bin/env python3
"""
Script per la creazione e inizializzazione del database Workly
Supporta sia SQLite (sviluppo) che PostgreSQL (produzione)
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Aggiungi la directory corrente al PYTHONPATH
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

def setup_environment():
    """Configura variabili d'ambiente di base"""
    if 'FLASK_SECRET_KEY' not in os.environ:
        os.environ['FLASK_SECRET_KEY'] = 'dev-secret-key-for-database-creation'
    
    if 'DATABASE_URL' not in os.environ:
        # Default SQLite per sviluppo
        db_path = current_dir / 'workly.db'
        os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'

def create_admin_user(db):
    """Crea l'utente amministratore di default"""
    from models import User
    from werkzeug.security import generate_password_hash
    
    print("👤 Creazione utente amministratore...")
    
    admin_user = User(
        username='admin',
        email='admin@workly.local',
        password_hash=generate_password_hash('admin123'),
        first_name='Amministratore',
        last_name='Sistema',
        role='Amministratore',
        active=True,
        created_at=datetime.utcnow()
    )
    
    db.session.add(admin_user)
    db.session.commit()
    print("✅ Utente admin creato!")
    return admin_user

def create_sample_sedi(db):
    """Crea sedi di esempio"""
    from models import Sede
    
    print("🏢 Creazione sedi di esempio...")
    
    sedi = [
        Sede(
            name='Sede Principale',
            address='Via Roma 123, Milano',
            description='Sede principale della società',
            tipologia='Oraria',
            active=True
        ),
        Sede(
            name='Filiale Nord',
            address='Via Garibaldi 456, Torino',
            description='Filiale operativa del Nord Italia',
            tipologia='Oraria',
            active=True
        ),
        Sede(
            name='Ufficio Sud',
            address='Via Nazionale 789, Roma',
            description='Ufficio per il Sud Italia',
            tipologia='Turni',
            active=True
        )
    ]
    
    for sede in sedi:
        db.session.add(sede)
    
    db.session.commit()
    print("✅ Sedi create!")
    return sedi

def create_sample_users(db, sedi):
    """Crea utenti di esempio per ogni ruolo"""
    from models import User
    from werkzeug.security import generate_password_hash
    
    print("👥 Creazione utenti di esempio...")
    
    users_data = [
        {
            'username': 'responsabile1',
            'email': 'resp1@workly.local',
            'password': 'resp123',
            'name': 'Mario',
            'surname': 'Rossi',
            'role': 'Responsabile',
            'sede_id': sedi[0].id,  # Milano
            'all_sedi': True  # Responsabile può accedere a tutte le sedi
        },
        {
            'username': 'supervisore1',
            'email': 'super1@workly.local',
            'password': 'super123',
            'name': 'Laura',
            'surname': 'Bianchi',
            'role': 'Supervisore',
            'sede_id': sedi[0].id,  # Milano
            'all_sedi': False
        },
        {
            'username': 'operatore1',
            'email': 'op1@workly.local',
            'password': 'op123',
            'name': 'Giuseppe',
            'surname': 'Verdi',
            'role': 'Operatore',
            'sede_id': sedi[0].id,  # Milano
            'all_sedi': False
        },
        {
            'username': 'operatore2',
            'email': 'op2@workly.local',
            'password': 'op123',
            'name': 'Anna',
            'surname': 'Neri',
            'role': 'Operatore',
            'sede_id': sedi[1].id,  # Torino
            'all_sedi': False
        },
        {
            'username': 'operatore3',
            'email': 'op3@workly.local',
            'password': 'op123',
            'name': 'Francesco',
            'surname': 'Blu',
            'role': 'Operatore',
            'sede_id': sedi[2].id,  # Roma
            'all_sedi': False
        }
    ]
    
    created_users = []
    
    for user_data in users_data:
        user = User(
            username=user_data['username'],
            email=user_data['email'],
            password_hash=generate_password_hash(user_data['password']),
            first_name=user_data['name'],
            last_name=user_data['surname'],
            role=user_data['role'],
            sede_id=user_data['sede_id'],
            all_sedi=user_data['all_sedi'],
            active=True,
            created_at=datetime.utcnow(),
            part_time_percentage=100  # Full time di default
        )
        
        db.session.add(user)
        created_users.append(user)
    
    db.session.commit()
    print("✅ Utenti di esempio creati!")
    return created_users

def create_sample_work_schedules(db, sedi):
    """Crea orari di lavoro di esempio"""
    from models import WorkSchedule
    
    print("⏰ Creazione orari di lavoro...")
    
    schedules = []
    
    for sede in sedi:
        # Orario standard diurno
        schedule_diurno = WorkSchedule(
            name=f'Diurno {sede.name}',
            sede_id=sede.id,
            start_time='08:00',
            end_time='17:00',
            break_duration=60,  # 1 ora di pausa
            active=True,
            work_type='ORARIA'
        )
        schedules.append(schedule_diurno)
        
        # Orario part-time mattino
        schedule_mattino = WorkSchedule(
            name=f'Part-time Mattino {sede.name}',
            sede_id=sede.id,
            start_time='08:00',
            end_time='13:00',
            break_duration=0,
            active=True,
            work_type='ORARIA'
        )
        schedules.append(schedule_mattino)
        
        # Turno notturno (solo per sede principale)
        if sede.name == 'Sede Principale':
            schedule_notturno = WorkSchedule(
                name=f'Notturno {sede.name}',
                sede_id=sede.id,
                start_time='22:00',
                end_time='06:00',
                break_duration=30,
                active=True,
                work_type='TURNI'
            )
            schedules.append(schedule_notturno)
    
    for schedule in schedules:
        db.session.add(schedule)
    
    db.session.commit()
    print("✅ Orari di lavoro creati!")
    return schedules

def create_sample_holidays(db, sedi):
    """Crea festività di esempio"""
    from models import Holiday
    
    print("🎄 Creazione festività...")
    
    current_year = datetime.now().year
    holidays_data = [
        {'name': 'Capodanno', 'date': f'{current_year}-01-01'},
        {'name': 'Epifania', 'date': f'{current_year}-01-06'},
        {'name': 'Festa della Liberazione', 'date': f'{current_year}-04-25'},
        {'name': 'Festa del Lavoro', 'date': f'{current_year}-05-01'},
        {'name': 'Festa della Repubblica', 'date': f'{current_year}-06-02'},
        {'name': 'Ferragosto', 'date': f'{current_year}-08-15'},
        {'name': 'Ognissanti', 'date': f'{current_year}-11-01'},
        {'name': 'Immacolata Concezione', 'date': f'{current_year}-12-08'},
        {'name': 'Natale', 'date': f'{current_year}-12-25'},
        {'name': 'Santo Stefano', 'date': f'{current_year}-12-26'}
    ]
    
    for sede in sedi:
        for holiday_data in holidays_data:
            parsed_date = datetime.strptime(holiday_data['date'], '%Y-%m-%d').date()
            holiday = Holiday(
                name=holiday_data['name'],
                month=parsed_date.month,
                day=parsed_date.day,
                sede_id=sede.id,
                active=True,
                created_by=1  # Admin user ID
            )
            db.session.add(holiday)
    
    db.session.commit()
    print("✅ Festività create!")

def create_sample_vehicles(db):
    """Crea veicoli aziendali di esempio"""
    from models import Vehicle
    
    print("🚗 Creazione veicoli aziendali...")
    
    vehicles = [
        Vehicle(
            targa='AB123CD',
            marca='Fiat',
            modello='Punto',
            alimentazione='Benzina',
            active=True
        ),
        Vehicle(
            targa='EF456GH',
            marca='Ford',
            modello='Focus',
            alimentazione='Diesel',
            active=True
        ),
        Vehicle(
            targa='IJ789KL',
            marca='Volkswagen',
            modello='Golf',
            alimentazione='Benzina',
            active=True
        )
    ]
    
    for vehicle in vehicles:
        db.session.add(vehicle)
    
    db.session.commit()
    print("✅ Veicoli creati!")
    return vehicles

def create_sample_attendance_events(db, users):
    """Crea eventi presenza di esempio per gli ultimi giorni"""
    from models import AttendanceEvent
    
    print("📊 Creazione presenze di esempio...")
    
    # Crea presenze per gli ultimi 5 giorni lavorativi
    today = datetime.now().date()
    events = []
    
    for i in range(5):
        work_date = today - timedelta(days=i)
        
        # Skip weekend
        if work_date.weekday() >= 5:
            continue
            
        for user in users[:3]:  # Solo primi 3 utenti
            # Entrata
            entry_time = datetime.combine(work_date, datetime.min.time().replace(hour=8, minute=0)) + timedelta(minutes=i*5)
            entry_event = AttendanceEvent(
                user_id=user.id,
                event_type='entry',
                timestamp=entry_time,
                location='Sede Principale',
                notes=f'Marcatura automatica giorno {work_date}'
            )
            events.append(entry_event)
            
            # Pausa pranzo inizio
            break_start = entry_time + timedelta(hours=4)
            break_event = AttendanceEvent(
                user_id=user.id,
                event_type='break_start',
                timestamp=break_start,
                location='Sede Principale'
            )
            events.append(break_event)
            
            # Pausa pranzo fine
            break_end = break_start + timedelta(hours=1)
            break_end_event = AttendanceEvent(
                user_id=user.id,
                event_type='break_end',
                timestamp=break_end,
                location='Sede Principale'
            )
            events.append(break_end_event)
            
            # Uscita
            exit_time = entry_time + timedelta(hours=8)
            exit_event = AttendanceEvent(
                user_id=user.id,
                event_type='exit',
                timestamp=exit_time,
                location='Sede Principale'
            )
            events.append(exit_event)
    
    for event in events:
        db.session.add(event)
    
    db.session.commit()
    print(f"✅ {len(events)} eventi presenza creati!")

def create_qr_code():
    """Crea il QR code statico per le marcature"""
    print("🔲 Generazione QR code per marcature...")
    
    try:
        import qrcode
        from PIL import Image
        import io
        
        # URL per le marcature (statico)
        qr_url = "http://localhost:5000/qr_attendance"
        
        # Genera QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_url)
        qr.make(fit=True)
        
        # Crea immagine
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Salva in static/images
        static_dir = current_dir / 'static' / 'images'
        static_dir.mkdir(parents=True, exist_ok=True)
        
        qr_path = static_dir / 'attendance_qr.png'
        img.save(qr_path)
        
        print(f"✅ QR code salvato in: {qr_path}")
        print(f"   URL: {qr_url}")
        
    except ImportError:
        print("⚠️  Libreria qrcode non disponibile, QR code non generato")
    except Exception as e:
        print(f"❌ Errore nella generazione QR code: {e}")

def main():
    """Funzione principale"""
    print("🗄️  Workly - Creazione Database")
    print("=" * 40)
    
    # Setup ambiente
    setup_environment()
    
    try:
        # Importa l'app dopo la configurazione dell'ambiente
        from app import app, db
        
        print(f"📊 Database URL: {os.environ.get('DATABASE_URL', 'Non configurato')}")
        
        with app.app_context():
            print("🔄 Eliminazione tabelle esistenti...")
            db.drop_all()
            
            print("🔄 Creazione struttura database...")
            db.create_all()
            print("✅ Struttura database creata!")
            
            # Crea dati di base
            admin_user = create_admin_user(db)
            sedi = create_sample_sedi(db)
            users = create_sample_users(db, sedi)
            
            # Genera QR code
            create_qr_code()
            
            print("\n🎉 Database inizializzato con successo!")
            print("=" * 40)
            print("🔑 CREDENZIALI DI ACCESSO:")
            print("   Username: admin")
            print("   Password: admin123")
            print("   Email: admin@workly.local")
            print("\n👥 UTENTI DI ESEMPIO CREATI:")
            print("   responsabile1 / resp123")
            print("   supervisore1 / super123")  
            print("   operatore1 / op123")
            print("   operatore2 / op123")
            print("   operatore3 / op123")
            print("\n🏢 SEDI CREATE:")
            print("   - Sede Principale (Milano)")
            print("   - Filiale Nord (Torino)")
            print("   - Ufficio Sud (Roma)")
            print("\n⚠️  IMPORTANTE:")
            print("   - Cambia le password di default dopo il primo accesso!")
            print("   - Configura le tue sedi e orari di lavoro")
            print("   - Personalizza ruoli e permessi secondo necessità")
            print("\n🚀 Il sistema è pronto per essere utilizzato!")
            
    except Exception as e:
        print(f"❌ Errore durante la creazione del database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()