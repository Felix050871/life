# Workly Platform - Pacchetto Installazione Locale

## Avvio Rapido (5 minuti)

### 1. Estrai il Pacchetto
```bash
unzip workly-installation-package.zip
cd workly-installation-package
```

### 2. Esegui Script Automatico

**Linux/macOS:**
```bash
chmod +x install.sh
./install.sh
```

**Windows:**
```batch
install.bat
```

### 3. Avvia l'Applicazione
```bash
./start.sh          # Linux/macOS
start.bat           # Windows
```

### 4. Accedi al Sistema
- **URL**: http://localhost:5000
- **Admin**: admin / password123
- **Responsabile**: mario.rossi / password123

## Contenuto Pacchetto

### File Principali
- `main.py` - Applicazione Flask principale
- `app.py` - Configurazione Flask e database
- `models.py` - Modelli database SQLAlchemy
- `routes.py` - Route e logica applicazione
- `forms.py` - Form WTForms per input utente
- `utils.py` - Funzioni utility condivise
- `config.py` - Configurazioni centralizzate

### Directory
- `templates/` - Template HTML Jinja2
- `static/` - File CSS, JavaScript, immagini
- `scripts/` - Script di utilità e manutenzione

### Documentazione
- `INSTALLATION_GUIDE_LOCAL.md` - Guida completa installazione
- `FUNCTIONALITY_DESCRIPTION.md` - Descrizione funzionalità
- `README.md` - Documentazione generale progetto

### Script Installazione
- `install.sh` - Installazione automatica Linux/macOS
- `install.bat` - Installazione automatica Windows
- `populate_test_data.py` - Popolamento dati di test

## Requisiti Sistema

### Software Necessario
- **Python 3.9+** (3.11 consigliato)
- **PostgreSQL 12+** 
- **4GB RAM** (8GB consigliati)
- **10GB spazio disco**

### Sistemi Supportati
- Windows 10/11
- macOS 10.15+
- Ubuntu 18.04+ / Debian 10+
- CentOS 7+ / RHEL 7+

## Funzionalità Incluse

### Gestione Utenti e Permessi
- 5 ruoli standardizzati (Amministratore → Ospite)
- 30+ permessi granulari configurabili
- Gestione multi-sede con accesso dinamico
- Autenticazione sicura con hash password

### Sistema Presenze
- Timbratura entrata/uscita/pausa
- QR code per timbratura rapida
- Controllo orari e ritardi automatico
- Dashboard presenze team con export Excel

### Gestione Turni e Reperibilità
- Generazione automatica turni da template
- Gestione coperture presidio
- Sistema reperibilità con interventi
- Bilanciamento carichi di lavoro

### Ferie e Permessi
- Richieste con approvazione workflow
- Gestione permessi orari e giornalieri
- Sistema notifiche automatiche
- Export report per amministrazione

### Note Spese e Straordinari
- Categorie spese configurabili
- Richieste straordinari con moltiplicatori
- Sistema approvazione multi-livello
- Report Excel per contabilità

### Sistema ACI (Automobilistico)
- Gestione costi chilometrici veicoli
- Upload Excel massivo ottimizzato
- Filtri avanzati e ricerca
- Back office amministratore only

### Messaggistica Interna
- Sistema messaggi tra utenti
- Notifiche automatiche approvazioni
- Categorizzazione messaggi per tipologia
- Gestione multi-destinatario

### Dashboard e Report
- Widget personalizzabili per ruolo
- Statistiche tempo reale
- Export Excel avanzati
- Grafici presenze e performance

## Configurazione Post-Installazione

### 1. Accesso Amministratore
```
URL: http://localhost:5000/login
User: admin
Password: password123
```

### 2. Configurazione Base
1. **Gestione Ruoli** → Configura permessi per ogni ruolo
2. **Gestione Sedi** → Crea sedi della tua organizzazione  
3. **Orari Lavoro** → Imposta orari per ogni sede
4. **Gestione Utenti** → Crea utenti reali
5. **Festività** → Configura giorni festivi annuali

### 3. Dati di Test Inclusi
- 8 utenti con diversi ruoli
- Presenze Luglio 2025 (31 giorni)
- 6 richieste ferie approvate/pending
- 5 richieste straordinari
- 6 note spese €35-280
- 8 turni reperibilità weekend
- Template presidio operativi

## Sicurezza

### Password di Default
⚠️ **IMPORTANTE**: Cambia immediatamente le password di default:
- Utenti di test: password123
- Database PostgreSQL: generata automaticamente

### File Sensibili
- `.env` - Configurazione ambiente (chiavi segrete)
- `.db_credentials` - Password database (backup sicuro!)

### Backup Database
```bash
# Backup manuale
pg_dump -h localhost -U workly_user workly_db > backup_$(date +%Y%m%d).sql

# Ripristino
psql -h localhost -U workly_user workly_db < backup_20250731.sql
```

## Modalità Produzione

### Avvio Produzione
```bash
./start_production.sh    # Linux/macOS
start_production.bat     # Windows
```

### Servizio Systemd (Linux)
```bash
# Creato automaticamente da install.sh
sudo systemctl start workly
sudo systemctl enable workly
```

### HTTPS/SSL
```bash
# Genera certificati self-signed
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Avvia con SSL
gunicorn --bind 0.0.0.0:443 --workers 4 --certfile=cert.pem --keyfile=key.pem main:app
```

## Risoluzione Problemi

### Database Non Raggiungibile
```bash
# Verifica servizio PostgreSQL
sudo systemctl status postgresql    # Linux
brew services list | grep postgres  # macOS

# Test connessione
psql -h localhost -U workly_user -d workly_db -c "SELECT version();"
```

### Dipendenze Python
```bash
# Reinstalla ambiente virtuale
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Reset Completo
```bash
# ATTENZIONE: Cancella tutti i dati!
python -c "from app import app, db; app.app_context().push(); db.drop_all(); db.create_all()"
python populate_test_data.py
```

### Log Debugging
```bash
# Controlla log applicazione
tail -f logs/workly.log

# Log database PostgreSQL
tail -f /var/log/postgresql/postgresql-*.log
```

## Performance

### Ottimizzazioni Incluse
- **Caricamento Lazy**: ACI tables caricano solo con filtri
- **Batch Processing**: Upload Excel a lotti da 100 record
- **Connection Pooling**: Database connections ottimizzate
- **Compressione**: Response gzip automatica
- **Cache**: Static files caching

### Monitoraggio
```bash
# Processi attivi
ps aux | grep python | grep workly

# Memoria utilizzata
free -h

# Spazio disco
df -h
```

## Aggiornamenti

### Aggiornamento Codice
1. Backup database
2. Sostituisci file Python
3. Aggiorna dipendenze: `pip install -r requirements.txt --upgrade`
4. Riavvia: `./start_production.sh`

### Migrazione Database
Le migrazioni sono automatiche all'avvio se necessarie.

## Supporto Tecnico

### Log Importanti
- `logs/workly.log` - Log applicazione
- `/var/log/postgresql/` - Log database
- `logs/access.log` - Log accessi web

### Comandi Utili
```bash
# Status servizi
systemctl status workly postgresql

# Processo Python
ps aux | grep gunicorn

# Porte in ascolto
netstat -tlnp | grep :5000
```

### Informazioni Sistema
```bash
# Versione Python
python --version

# Versione PostgreSQL
psql --version

# Spazio disponibile
du -sh * | sort -hr
```

---

**Workly Platform v2.0**  
**Pacchetto Installazione Locale**  
**Data Creazione**: 31 Luglio 2025  

Per supporto completo consultare `INSTALLATION_GUIDE_LOCAL.md`