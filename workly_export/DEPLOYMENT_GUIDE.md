# Workly - Guida al Deployment

## Panoramica del Progetto
Workly è una piattaforma avanzata di gestione della forza lavoro con funzionalità complete per:
- Gestione presenze e turni
- Sistema QR code per marcature
- Gestione permessi e ferie
- Sistema di messaggistica interna
- Gestione note spese e rimborsi chilometrici
- Reportistica avanzata con grafici
- Sistema di reperibilità

## Requisiti di Sistema

### Database
- **Sviluppo**: SQLite (incluso)
- **Produzione**: PostgreSQL 12+

### Python
- Python 3.8+
- Dipendenze elencate in `requirements.txt`

## Installazione Locale

### 1. Preparazione dell'Ambiente
```bash
# Clona o estrai il progetto
cd workly_export

# Crea ambiente virtuale
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oppure
venv\Scripts\activate     # Windows

# Installa dipendenze
pip install -r requirements.txt
```

### 2. Configurazione Database

#### Per Sviluppo (SQLite)
```bash
# Il database SQLite verrà creato automaticamente
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database creato!')"
```

#### Per Produzione (PostgreSQL)
```bash
# Configura la variabile d'ambiente
export DATABASE_URL="postgresql://username:password@host:port/database_name"

# Crea le tabelle
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database creato!')"
```

### 3. Variabili d'Ambiente
Crea un file `.env` nella root del progetto:

```env
# Segreto per le sessioni Flask
FLASK_SECRET_KEY=your-very-secure-secret-key-here

# Database (opzionale per sviluppo)
DATABASE_URL=sqlite:///workly.db

# Per produzione PostgreSQL
# DATABASE_URL=postgresql://user:pass@host:port/dbname

# Modalità debug (solo sviluppo)
FLASK_DEBUG=True
```

### 4. Avvio dell'Applicazione

#### Sviluppo
```bash
python main.py
# oppure
flask run --host=0.0.0.0 --port=5000
```

#### Produzione con Gunicorn
```bash
gunicorn --bind 0.0.0.0:5000 --workers 4 main:app
```

## Deployment su Replit

### File di Configurazione Inclusi
- `.replit`: Configurazione dell'ambiente Replit
- `replit.nix`: Dipendenze di sistema
- `pyproject.toml`: Configurazione Python

### Variabili d'Ambiente Replit
Nel pannello "Secrets" di Replit, aggiungi:
- `FLASK_SECRET_KEY`: Chiave segreta per le sessioni
- `DATABASE_URL`: URL del database PostgreSQL (per produzione)

## Deployment su Server Dedicato

### Con Docker (Consigliato)
Crea un `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "main:app"]
```

### Con systemd (Linux)
Crea `/etc/systemd/system/workly.service`:

```ini
[Unit]
Description=Workly Workforce Management
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/workly
Environment=PATH=/path/to/workly/venv/bin
EnvironmentFile=/path/to/workly/.env
ExecStart=/path/to/workly/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 4 main:app
Restart=always

[Install]
WantedBy=multi-user.target
```

## Configurazione Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/workly/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

## Primo Accesso

### Utente Amministratore di Default
Al primo avvio, il sistema creerà automaticamente un utente amministratore:
- **Username**: `admin`
- **Password**: `admin123`
- **Email**: `admin@workly.local`

⚠️ **IMPORTANTE**: Cambia immediatamente le credenziali dopo il primo accesso!

### Configurazione Iniziale
1. Accedi con le credenziali di default
2. Vai in "Gestione Utenti" → "Modifica Profilo Admin"
3. Cambia password e email
4. Configura le sedi di lavoro
5. Crea gli utenti del team
6. Configura i ruoli e permessi

## Funzionalità Principali

### Gestione Utenti
- Sistema di ruoli: Amministratore, Responsabile, Supervisore, Operatore, Ospite
- Permessi granulari (oltre 30 permessi specifici)
- Gestione sedi multiple
- Orari di lavoro configurabili

### Presenze e Turni
- Marcature con QR code statico
- Sistema di turni intelligente
- Gestione pause e straordinari
- Reportistica dettagliata

### Sistema Avanzato
- Messaggistica interna
- Gestione ferie e permessi
- Rimborsi chilometrici con tabelle ACI
- Dashboard personalizzabile
- Esportazione dati in Excel

## Backup e Manutenzione

### Backup Database
```bash
# PostgreSQL
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# SQLite
cp workly.db backup_workly_$(date +%Y%m%d).db
```

### Log di Sistema
I log dell'applicazione sono disponibili in:
- Console dell'applicazione
- Log del web server (Gunicorn/Nginx)

## Risoluzione Problemi

### Errori Comuni
1. **Errore 500**: Controlla i log per dettagli
2. **Database non trovato**: Verifica DATABASE_URL
3. **Sessioni non persistenti**: Controlla FLASK_SECRET_KEY
4. **Errori di permessi**: Verifica i permessi sui file

### Debug Mode
Solo per sviluppo, abilita il debug:
```python
export FLASK_DEBUG=1
```

## Supporto e Documentazione

### File di Documentazione Inclusi
- `replit.md`: Documentazione tecnica completa
- `README.md`: Panoramica del progetto
- Commenti nel codice per tutte le funzioni principali

### Struttura del Progetto
```
workly/
├── app.py              # Configurazione Flask principale
├── main.py             # Entry point dell'applicazione
├── models.py           # Modelli database SQLAlchemy
├── routes.py           # Route principali
├── forms.py            # Form WTForms
├── utils.py            # Funzioni di utilità
├── config.py           # Configurazioni
├── templates/          # Template Jinja2
├── static/             # File statici (CSS, JS, immagini)
├── routes/            # Route modulari
└── requirements.txt    # Dipendenze Python
```

---

**Versione**: 1.0  
**Data**: Gennaio 2025  
**Compatibilità**: Python 3.8+, PostgreSQL 12+, Flask 2.3+