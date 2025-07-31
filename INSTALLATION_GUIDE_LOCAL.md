# Guida Installazione Locale - Workly Platform

## Panoramica

Workly è una piattaforma completa per la gestione della forza lavoro che include:
- Gestione presenze e turni
- Sistema QR per timbratura
- Gestione ferie e permessi  
- Sistema messaggistica interna
- Gestione note spese e straordinari
- Back office ACI per costi veicoli
- Dashboard analitiche avanzate
- Sistema ruoli granulare (30+ permessi)

## Requisiti di Sistema

### Hardware Minimo
- **RAM**: 4GB (consigliati 8GB)
- **Storage**: 10GB spazio libero
- **CPU**: Dual-core 2.0GHz o superiore

### Software Richiesto
- **Python**: 3.9, 3.10 o 3.11
- **PostgreSQL**: 12.0 o superiore
- **Git**: Per clonare il repository
- **Browser**: Chrome, Firefox, Safari, Edge (versioni recenti)

### Sistemi Operativi Supportati
- Windows 10/11
- macOS 10.15 o superiore  
- Ubuntu 18.04 LTS o superiore
- Debian 10 o superiore
- CentOS 7/8, RHEL 7/8

## Installazione Rapida (Script Automatico)

### 1. Download e Estrazione
```bash
# Estrai il pacchetto scaricato
unzip workly-installation-package.zip
cd workly-installation-package
```

### 2. Esecuzione Script Automatico

**Su Linux/macOS:**
```bash
chmod +x install.sh
./install.sh
```

**Su Windows:**
```batch
install.bat
```

Lo script automatico:
- Verifica i requisiti di sistema
- Installa Python e dipendenze se mancanti
- Configura PostgreSQL
- Crea il database e tabelle
- Popola dati di test
- Avvia l'applicazione

## Installazione Manuale Dettagliata

### Passo 1: Installazione Python

**Windows:**
1. Scarica Python da [python.org](https://www.python.org/downloads/)
2. Installa selezionando "Add Python to PATH"
3. Verifica installazione:
```cmd
python --version
pip --version
```

**macOS:**
```bash
# Con Homebrew
brew install python@3.11

# Con installer ufficiale
# Scarica da python.org e installa
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-pip python3.11-venv
```

**CentOS/RHEL:**
```bash
sudo yum install python3.11 python3.11-pip
# oppure con dnf su versioni recenti
sudo dnf install python3.11 python3.11-pip
```

### Passo 2: Installazione PostgreSQL

**Windows:**
1. Scarica PostgreSQL da [postgresql.org](https://www.postgresql.org/download/windows/)
2. Installa con installer grafico
3. Imposta password per utente `postgres`
4. Avvia pgAdmin per gestione database

**macOS:**
```bash
# Con Homebrew
brew install postgresql
brew services start postgresql

# Crea utente
createuser -s postgres
```

**Ubuntu/Debian:**
```bash
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Configura utente
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'your_password';"
```

**CentOS/RHEL:**
```bash
sudo yum install postgresql-server postgresql-contrib
sudo postgresql-setup initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Configura utenti
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'your_password';"
```

### Passo 3: Preparazione Ambiente

```bash
# Crea directory progetto
mkdir workly-platform
cd workly-platform

# Crea ambiente virtuale Python
python3 -m venv venv

# Attiva ambiente virtuale
# Su Linux/macOS:
source venv/bin/activate
# Su Windows:
venv\Scripts\activate
```

### Passo 4: Installazione Dipendenze

```bash
# Aggiorna pip
pip install --upgrade pip

# Installa dipendenze dalla lista fornita
pip install -r requirements.txt
```

Le dipendenze principali includono:
- Flask (framework web)
- SQLAlchemy (ORM database)
- Flask-Login (autenticazione)
- psycopg2-binary (driver PostgreSQL)
- pandas (elaborazione Excel)
- qrcode (generazione QR)
- openpyxl (gestione Excel)

### Passo 5: Configurazione Database

```bash
# Accedi a PostgreSQL
sudo -u postgres psql

# Crea database
CREATE DATABASE workly_db;
CREATE USER workly_user WITH ENCRYPTED PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE workly_db TO workly_user;

# Esci da psql
\q
```

### Passo 6: Configurazione Variabili Ambiente

Crea file `.env` nella directory principale:

```bash
# Database Configuration
DATABASE_URL=postgresql://workly_user:your_secure_password@localhost:5432/workly_db
PGHOST=localhost
PGPORT=5432
PGDATABASE=workly_db
PGUSER=workly_user
PGPASSWORD=your_secure_password

# Application Configuration
FLASK_SECRET_KEY=your_very_secret_key_change_this_in_production
FLASK_ENV=development
FLASK_DEBUG=True

# Session Configuration
SESSION_SECRET=another_secret_key_for_sessions

# Upload Configuration
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=52428800  # 50MB

# QR Configuration
QR_FOLDER=static/qr_codes
```

**Generazione chiavi sicure:**
```python
# Esegui questo per generare chiavi casuali
import secrets
print("FLASK_SECRET_KEY=" + secrets.token_hex(32))
print("SESSION_SECRET=" + secrets.token_hex(32))
```

### Passo 7: Copia File Applicazione

Copia tutti i file Python e template dalla cartella `workly-platform/`:
- `main.py` - File principale
- `app.py` - Configurazione Flask
- `models.py` - Modelli database
- `routes.py` - Route applicazione
- `forms.py` - Form WTF
- `utils.py` - Funzioni utility
- `config.py` - Configurazioni
- `templates/` - Template HTML
- `static/` - File statici (CSS, JS, immagini)

### Passo 8: Inizializzazione Database

```bash
# Attiva ambiente virtuale se non attivo
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Inizializza database e tabelle
python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database inizializzato!')
"
```

### Passo 9: Popolamento Dati Test (Opzionale)

```bash
# Esegui script popolamento dati
python populate_test_data.py
```

Questo crea:
- 8 utenti di test con diversi ruoli
- Dati presenze luglio 2025
- Richieste ferie/permessi
- Note spese di esempio
- Turni reperibilità
- Festività

### Passo 10: Avvio Applicazione

```bash
# Avvio in modalità sviluppo
python main.py

# Oppure con Gunicorn (produzione)
pip install gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 main:app
```

L'applicazione sarà disponibile su:
- **Sviluppo**: http://localhost:5000
- **Produzione**: http://localhost:5000 (o IP server)

## Accesso Iniziale

### Utenti di Test Creati
| Username | Password | Ruolo | Descrizione |
|----------|----------|-------|-------------|
| admin | password123 | Amministratore | Accesso completo |
| mario.rossi | password123 | Responsabile | Gestione operativa |
| paolo.verdi | password123 | Supervisore | Solo visualizzazione |
| anna.bianchi | password123 | Operatore | Funzioni base |
| guest.user | password123 | Ospite | Accesso limitato |

### Prima Configurazione

1. **Accedi come admin** (admin/password123)
2. **Vai in Gestione Ruoli** per configurare permessi
3. **Vai in Gestione Utenti** per creare utenti reali
4. **Configura Sedi** in base alla tua organizzazione
5. **Imposta Orari di Lavoro** per ogni sede
6. **Configura Festività** per l'anno corrente

## Configurazioni Avanzate

### Configurazione Email (SMTP)

Per notifiche email, aggiungi al file `.env`:

```bash
# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
MAIL_DEFAULT_SENDER=your_email@gmail.com
```

### Configurazione SSL/HTTPS

Per produzione con HTTPS:

```bash
# Genera certificati SSL
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Avvia con SSL
gunicorn --bind 0.0.0.0:443 --workers 4 --certfile=cert.pem --keyfile=key.pem main:app
```

### Backup Automatico Database

Crea script backup `backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -h localhost -U workly_user workly_db > $BACKUP_DIR/workly_backup_$DATE.sql
```

Aggiungi a crontab per backup automatici:
```bash
# Backup giornaliero alle 2:00
0 2 * * * /path/to/backup.sh
```

## Risoluzione Problemi

### Problemi Database
```bash
# Verifica connessione PostgreSQL
psql -h localhost -U workly_user -d workly_db -c "SELECT version();"

# Reset database completo
python -c "
from app import app, db
with app.app_context():
    db.drop_all()
    db.create_all()
    print('Database resettato!')
"
```

### Problemi Dipendenze Python
```bash
# Reinstalla dipendenze
pip uninstall -r requirements.txt -y
pip install -r requirements.txt

# Aggiorna pip e setuptools
pip install --upgrade pip setuptools wheel
```

### Problemi Permessi File
```bash
# Linux/macOS - Correggi permessi
chmod -R 755 workly-platform/
chmod -R 777 uploads/
chmod -R 777 static/qr_codes/
```

### Debug Logging
Aggiungi al file `main.py` per debug avanzato:

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('workly.log'),
        logging.StreamHandler()
    ]
)
```

## Manutenzione

### Aggiornamento Applicazione
1. Backup database
2. Sostituisci file Python
3. Aggiorna dipendenze: `pip install -r requirements.txt --upgrade`
4. Riavvia applicazione

### Monitoraggio Performance
```bash
# Installa monitoring tools
pip install psutil

# Monitor database connections
psql -h localhost -U workly_user -d workly_db -c "SELECT * FROM pg_stat_activity;"
```

### Pulizia Log e File Temporanei
```bash
# Pulisci log vecchi
find . -name "*.log" -mtime +30 -delete

# Pulisci upload temporanei
find uploads/ -name "*.tmp" -mtime +1 -delete
```

## Supporto

Per supporto tecnico:
- Controlla i log: `tail -f workly.log`
- Verifica stato database: `systemctl status postgresql`
- Controlla processi: `ps aux | grep python`

### File Log Importanti
- `workly.log` - Log applicazione
- `/var/log/postgresql/` - Log PostgreSQL
- `access.log` - Log accessi web

---

**Versione Guida**: 1.0  
**Data**: 31 Luglio 2025  
**Compatibilità**: Workly Platform v2.0+