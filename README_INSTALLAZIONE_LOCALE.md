# Workly - Guida Installazione Locale PostgreSQL

## Panoramica

Questa guida ti aiuterà a installare Workly localmente sul tuo sistema usando PostgreSQL come database. L'installazione crea un ambiente completamente isolato con tutti i path relativi alla directory del progetto.

## Prerequisiti Sistema

### Tutti i Sistemi
- **Python 3.7+** - [Download](https://www.python.org/downloads/)
- **PostgreSQL 12+** - [Download](https://www.postgresql.org/download/)
- **Git** (opzionale, per clonare il repository)

### Windows
- PowerShell o Command Prompt
- PostgreSQL installato con `psql` nel PATH

### Linux/Ubuntu
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv postgresql postgresql-contrib
```

### macOS
```bash
# Con Homebrew
brew install python3 postgresql
```

## Installazione Rapida

### 1. Scarica il Progetto
```bash
# Se hai git
git clone <repository-url>
cd workly

# Oppure scarica e estrai il pacchetto ZIP
unzip workly-package.zip
cd workly
```

### 2. Esegui Script di Installazione

#### Windows
```cmd
install_local.bat
```

#### Linux/macOS
```bash
chmod +x install_local.sh
./install_local.sh
```

### 3. Avvia Workly

#### Windows
```cmd
start_workly.bat
```

#### Linux/macOS
```bash
./start_workly.sh
```

### 4. Accedi all'Applicazione
Apri il browser e vai su: **http://127.0.0.1:5000**

## Configurazione Dettagliata

### Database PostgreSQL

Durante l'installazione ti verranno richieste le credenziali PostgreSQL:

- **Host**: localhost (default)
- **Porta**: 5432 (default)  
- **Database**: workly_db (default)
- **Username**: postgres (default)
- **Password**: [la tua password PostgreSQL]

### Utente Amministratore

Dovrai creare un utente amministratore fornendo:
- Nome e Cognome
- Email
- Username  
- Password

## Struttura Directory

Dopo l'installazione avrai:

```
workly/
├── workly_venv/           # Ambiente virtuale Python (isolato)
├── config/                # File di configurazione
├── static/                # File statici (CSS, JS, immagini)
├── templates/             # Template HTML
├── .env                   # Variabili ambiente (MANTIENI PRIVATO)
├── install_local.sh       # Script installazione Unix/Linux/macOS
├── install_local.bat      # Script installazione Windows
├── start_workly.sh        # Script avvio Unix/Linux/macOS
├── start_workly.bat       # Script avvio Windows
├── main.py                # Applicazione Flask principale
├── models.py              # Modelli database
├── routes.py              # Route applicazione
└── requirements.txt       # Dipendenze Python
```

## Variabili Ambiente (.env)

Il file `.env` contiene tutte le configurazioni:

```bash
# Database PostgreSQL
DATABASE_URL=postgresql://user:password@host:port/database
PGHOST=localhost
PGPORT=5432
PGDATABASE=workly_db
PGUSER=postgres
PGPASSWORD=your_password

# Flask
FLASK_SECRET_KEY=generated_secret_key
SESSION_SECRET=generated_secret_key
FLASK_ENV=production
FLASK_DEBUG=False

# Workly
WORKLY_ADMIN_EMAIL=admin@workly.local
WORKLY_COMPANY_NAME=Workly Platform
WORKLY_TIMEZONE=Europe/Rome

# Server
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
WORKERS=4
```

## Funzionalità Principali

### Sistema Completo Include:
- ✅ **Gestione Utenti** - Utenti, ruoli, permessi granulari
- ✅ **Presenze** - Clock in/out, pause, QR code
- ✅ **Turni** - Pianificazione, assegnazione, template
- ✅ **Ferie e Permessi** - Richieste, approvazioni, calendario
- ✅ **Straordinari** - Gestione ore extra, tipologie, approvazioni
- ✅ **Rimborsi Chilometrici** - Calcolo automatico, veicoli ACI, approvazioni
- ✅ **Messaggistica Interna** - Comunicazioni team, notifiche
- ✅ **Reperibilità** - Gestione turni on-call, interventi
- ✅ **Dashboard** - Widget dinamici, statistiche real-time
- ✅ **Report** - Export Excel, filtri avanzati
- ✅ **Multi-Sede** - Gestione sedi multiple
- ✅ **Festività** - Calendario festivi personalizzabile

## Troubleshooting

### Errore Connessione Database
```bash
# Verifica che PostgreSQL sia in esecuzione
sudo systemctl status postgresql    # Linux
brew services list | grep postgres  # macOS
```

### Errore Permessi Python
```bash
# Su Linux/macOS, potresti aver bisogno di:
sudo chown -R $USER:$USER workly_venv/
```

### Porta 5000 Occupata
Modifica nel file `.env`:
```bash
FLASK_PORT=8000  # O qualsiasi altra porta libera
```

### Reset Completo
```bash
# Elimina ambiente virtuale e database
rm -rf workly_venv/
dropdb workly_db  # Comando PostgreSQL

# Riesegui installazione
./install_local.sh
```

## Backup e Manutenzione

### Backup Database
```bash
pg_dump -h localhost -U postgres workly_db > backup_workly.sql
```

### Ripristino Database  
```bash
createdb workly_db_restored
psql -h localhost -U postgres workly_db_restored < backup_workly.sql
```

### Aggiornamento Applicazione
1. Mantieni il database esistente
2. Scarica nuova versione del codice
3. Rimuovi ambiente virtuale: `rm -rf workly_venv/`
4. Riesegui script installazione (manterrà database esistente)

## Sicurezza

### File Sensibili
- **`.env`** - Contiene password database, mantieni privato
- **`workly_venv/`** - Ambiente isolato, ricreabile

### Password Amministratore
- Usa password forte per l'utente admin
- Cambia password default dopo il primo accesso
- Abilita autenticazione a due fattori se disponibile

## Supporto

### Log Applicazione
I log sono visibili nella console quando avvii con gli script di avvio.

### Debug Mode
Per abilitare debug (solo sviluppo):
```bash
# Nel file .env
FLASK_DEBUG=True
FLASK_ENV=development
```

### Performance
Per installazioni production:
- Aumenta `WORKERS` nel file `.env`
- Configura reverse proxy (nginx/apache)
- Usa server dedicato PostgreSQL

## File di Configurazione Generati

L'installazione genera automaticamente tutti i file necessari con path relativi:

- **Ambiente virtuale** in `./workly_venv/`
- **Configurazione** in `./.env`
- **Script avvio** in `./start_workly.sh` o `./start_workly.bat`
- **Database** PostgreSQL esterno (non file locali)

Tutti i path sono relativi alla directory del progetto, garantendo portabilità completa dell'installazione.