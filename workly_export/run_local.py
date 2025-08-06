#!/usr/bin/env python3
"""
Script di avvio locale per Workly
Utile per test e sviluppo rapido
"""

import os
import sys
from pathlib import Path

# Aggiungi la directory corrente al PYTHONPATH
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

def setup_environment():
    """Configura l'ambiente di sviluppo"""
    # Carica variabili d'ambiente da .env se esiste
    env_file = current_dir / '.env'
    if env_file.exists():
        print("📄 Caricamento file .env...")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    else:
        print("⚠️  File .env non trovato, usando configurazioni di default")
        
    # Configurazioni di default per sviluppo
    if 'FLASK_SECRET_KEY' not in os.environ:
        os.environ['FLASK_SECRET_KEY'] = 'dev-secret-key-change-in-production'
        print("🔑 Usando chiave segreta di sviluppo")
    
    if 'DATABASE_URL' not in os.environ:
        db_path = current_dir / 'workly.db'
        os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
        print(f"💾 Database SQLite: {db_path}")
    
    os.environ['FLASK_ENV'] = 'development'
    os.environ['FLASK_DEBUG'] = 'True'

def create_initial_data():
    """Crea dati iniziali se il database è vuoto"""
    try:
        from app import app, db
        from models import User
        
        with app.app_context():
            # Controlla se esistono utenti
            if User.query.count() == 0:
                print("👤 Creazione utente amministratore di default...")
                
                from werkzeug.security import generate_password_hash
                admin_user = User(
                    username='admin',
                    email='admin@workly.local',
                    password_hash=generate_password_hash('admin123'),
                    name='Amministratore',
                    surname='Sistema',
                    role='Amministratore',
                    active=True
                )
                
                db.session.add(admin_user)
                db.session.commit()
                
                print("✅ Utente admin creato!")
                print("   Username: admin")
                print("   Password: admin123")
                print("   ⚠️  CAMBIA LA PASSWORD AL PRIMO ACCESSO!")
                
    except Exception as e:
        print(f"❌ Errore nella creazione dati iniziali: {e}")

def main():
    """Funzione principale"""
    print("🚀 Avvio Workly - Workforce Management Platform")
    print("=" * 50)
    
    # Setup ambiente
    setup_environment()
    
    try:
        # Importa l'app dopo la configurazione dell'ambiente
        from app import app, db
        
        # Crea database se non exists
        with app.app_context():
            print("📊 Inizializzazione database...")
            db.create_all()
            print("✅ Database inizializzato")
            
            # Crea dati iniziali
            create_initial_data()
        
        # Informazioni di avvio
        host = '0.0.0.0'
        port = int(os.environ.get('FLASK_PORT', 5000))
        
        print(f"🌐 Server in avvio su http://{host}:{port}")
        print("📱 Accessibile anche da altri dispositivi nella rete locale")
        print("🛑 Premi CTRL+C per fermare il server")
        print("=" * 50)
        
        # Avvia il server Flask
        app.run(
            host=host,
            port=port,
            debug=True,
            use_reloader=True,
            threaded=True
        )
        
    except KeyboardInterrupt:
        print("\n👋 Server fermato dall'utente")
    except Exception as e:
        print(f"❌ Errore nell'avvio del server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()