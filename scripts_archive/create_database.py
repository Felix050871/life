#!/usr/bin/env python3
"""
Script per inizializzare il database PostgreSQL di Life con dati di esempio
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Directory corrente
current_dir = Path(__file__).parent

def setup_environment():
    """Configura l'ambiente per l'applicazione"""
    # Verifica che DATABASE_URL sia presente
    if not os.environ.get('DATABASE_URL'):
        print("❌ ERRORE: DATABASE_URL non trovata!")
        print("🔧 Assicurati che la variabile di ambiente DATABASE_URL sia configurata per PostgreSQL.")
        sys.exit(1)
        
    database_url = os.environ.get('DATABASE_URL')
    if 'postgresql' not in database_url:
        print("❌ ERRORE: Solo PostgreSQL è supportato!")
        print(f"🔧 DATABASE_URL trovata: {database_url}")
        sys.exit(1)

def create_admin_user(db):
    """Crea l'utente amministratore"""
    from models import User
    from werkzeug.security import generate_password_hash
    
    print("👤 Creazione utente amministratore...")
    
    admin_user = User(
        username='admin',
        email='admin@life.local',
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
            'email': 'resp1@life.local',
            'password': 'resp123',
            'name': 'Mario',
            'surname': 'Rossi',
            'role': 'Responsabile',
            'sede_id': sedi[0].id,
            'all_sedi': True
        },
        {
            'username': 'supervisore1',
            'email': 'super1@life.local',
            'password': 'super123',
            'name': 'Laura',
            'surname': 'Bianchi',
            'role': 'Supervisore',
            'sede_id': sedi[0].id,
            'all_sedi': False
        },
        {
            'username': 'operatore1',
            'email': 'op1@life.local',
            'password': 'op123',
            'name': 'Giuseppe',
            'surname': 'Verdi',
            'role': 'Operatore',
            'sede_id': sedi[0].id,
            'all_sedi': False
        },
        {
            'username': 'operatore2',
            'email': 'op2@life.local',
            'password': 'op123',
            'name': 'Anna',
            'surname': 'Neri',
            'role': 'Operatore',
            'sede_id': sedi[1].id,
            'all_sedi': False
        },
        {
            'username': 'operatore3',
            'email': 'op3@life.local',
            'password': 'op123',
            'name': 'Francesco',
            'surname': 'Blu',
            'role': 'Operatore',
            'sede_id': sedi[2].id,
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
            part_time_percentage=100
        )
        
        db.session.add(user)
        created_users.append(user)
    
    db.session.commit()
    print("✅ Utenti di esempio creati!")
    return created_users

def create_qr_code():
    """Crea il QR code statico per le marcature"""
    print("🔲 Generazione QR code per marcature...")
    
    try:
        import qrcode
        from PIL import Image
        
        # URL per le marcature
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
    """Funzione principale per creare il database PostgreSQL"""
    print("🗄️  Life - Creazione Database PostgreSQL")
    print("========================================")
    
    # Setup ambiente
    setup_environment()
    
    database_url = os.environ.get('DATABASE_URL')
    print(f"📊 Database URL: {database_url}")
    
    try:
        # Import app dopo aver verificato l'ambiente
        from app import app, db
        
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
            
        print("\n🎉 Database PostgreSQL inizializzato con successo!")
        print("========================================")
        print("🔑 CREDENZIALI DI ACCESSO:")
        print("   Username: admin")
        print("   Password: admin123")
        print("   Email: admin@life.local")
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
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRORE: {e}")
        print("🔧 Verifica la configurazione del database PostgreSQL e riprova.")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)