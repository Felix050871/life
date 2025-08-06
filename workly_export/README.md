# Workly - Workforce Management Platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Una piattaforma completa di gestione della forza lavoro sviluppata con Flask, progettata per aziende che necessitano di tracciamento presenze, gestione turni, amministrazione del personale e controllo operativo avanzato.

## 🚀 Quick Start

### Installazione Rapida (Replit)
1. Fork questo progetto su Replit
2. Configura le variabili d'ambiente nel pannello Secrets
3. Premi "Run" per avviare l'applicazione
4. Accedi con: `admin` / `password123`

### Installazione Locale
```bash
git clone <repository-url>
cd workly
./scripts/setup.sh
```

### Con Docker
```bash
docker-compose up -d
```

## 📋 Funzionalità Principali

### 🔐 Autenticazione e Autorizzazione
- **Sistema di ruoli** con 5 livelli: Amministratore, Responsabile, Supervisore, Operatore, Ospite
- **30+ permessi granulari** configurabili per ogni funzionalità
- **Multi-sede** con controllo accessi per sede o globale
- **Reset password** sicuro con token temporanei

### 👥 Gestione Utenti e Sedi
- **Anagrafica completa** con assegnazione ruoli e sedi
- **Orari personalizzabili** per utente e tipologia lavoro
- **Modalità operative**: ORARIA (controllo presenze) e TURNI (gestione turnazioni)
- **Percentuale part-time** per orari ridotti

### ⏰ Tracciamento Presenze
- **Registrazione Entrata/Uscita** con timestamp precisi
- **Gestione pause** con tracciamento dettagliato
- **Controllo automatico** ritardi e anticipi
- **Sistema QR Code** per registrazione rapida
- **Storico completo** con filtri avanzati

### 📊 Dashboard e Analytics
- **Dashboard personalizzate** con widget configurabili
- **Statistiche real-time** presenze, ore lavorate, trend
- **Vista team** per supervisori con analisi sede
- **Grafici interattivi** per analisi performance
- **Export Excel** per tutti i dati

### 🔄 Gestione Turni e Reperibilità
- **Template presidio** per coperture automatiche
- **Generazione intelligente** turni con bilanciamento carichi
- **Turni reperibilità** separati con gestione interventi
- **Calendario avanzato** con navigazione temporale
- **Rilevamento missing roles** per coperture incomplete

### 🏖️ Richieste Ferie e Permessi
- **8 tipologie configurabili**: Ferie, Permessi, Malattia, Congedi
- **Permessi orari** con definizione start/end time
- **Workflow approvazione** automatico basato su ruoli
- **Validazione sovrapposizioni** e controlli business logic
- **Notifiche automatiche** per stato richieste

### ⏱️ Gestione Straordinari
- **Tipologie personalizzabili** con moltiplicatori retributivi
- **Richieste dettagliate** con motivazioni e approvazioni
- **Calcolo automatico ore** con gestione turni notturni
- **Controllo gerarchico** per approvazione costi

### 💰 Note Spese
- **Categorie configurabili**: Trasferte, Carburante, Pasti, Materiali
- **Upload allegati** per ricevute e documenti
- **Workflow approvazione** con commenti e feedback
- **Dashboard budget** per controllo spese
- **Export dettagliato** con filtri avanzati

### 💬 Messaggistica Interna
- **Sistema messaggi** multi-destinatario per sede
- **Categorie messaggi**: Informativo, Successo, Attenzione, Urgente
- **Notifiche automatiche** per workflow approvazioni
- **Gestione lettura** e archiviazione messaggi

## 🛠️ Tecnologie

### Backend
- **Framework**: Flask 3.0+ con SQLAlchemy ORM
- **Database**: PostgreSQL (produzione) / SQLite (sviluppo)
- **Autenticazione**: Flask-Login con gestione sessioni sicure
- **Forms**: WTForms con validazione CSRF
- **Server**: Gunicorn WSGI con supporto autoscale

### Frontend
- **Template**: Jinja2 con Bootstrap 5 tema dark
- **JavaScript**: Vanilla JS con librerie specifiche
- **Icons**: Font Awesome 6 per iconografia
- **Charts**: Chart.js per grafici e analytics
- **Export**: SheetJS per export Excel client-side

### Deployment
- **Cloud**: Ottimizzato per Replit con PostgreSQL managed
- **Docker**: Configurazione multi-container con nginx
- **VPS**: Script automatici per Ubuntu/CentOS
- **SSL**: Configurazione automatica Let's Encrypt

## 📦 Installazione

### Requisiti
- Python 3.11+
- PostgreSQL 13+ (produzione) o SQLite (sviluppo)
- 512MB+ RAM (1GB+ raccomandato)

### Setup Automatico
```bash
# Clone repository
git clone <repository-url>
cd workly

# Esegui setup automatico
chmod +x scripts/setup.sh
./scripts/setup.sh

# Attiva ambiente virtuale
source venv/bin/activate

# Avvia applicazione
python main.py
```

### Setup Manuale
```bash
# Crea ambiente virtuale
python3 -m venv venv
source venv/bin/activate

# Installa dipendenze
pip install -r requirements.txt

# Configura database
export DATABASE_URL="postgresql://user:pass@localhost/workly"
export FLASK_SECRET_KEY="your-secret-key"

# Popola dati di test
python populate_test_data.py

# Avvia applicazione
gunicorn --bind 0.0.0.0:5000 main:app
```

## 🔧 Configurazione

### Variabili d'Ambiente
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/database

# Security
FLASK_SECRET_KEY=your-very-secure-secret-key

# Environment
FLASK_ENV=production  # development/production
DEBUG=False          # True per debug mode
PORT=5000           # Porta applicazione
```

### Utenti di Test
Il sistema include utenti preconfigurati:

| Username | Password | Ruolo | Accesso |
|----------|----------|-------|---------|
| admin | password123 | Amministratore | Completo |
| mario.rossi | password123 | Responsabile | Gestione |
| paolo.verdi | password123 | Supervisore | Supervisione |
| luca.ferrari | password123 | Operatore | Base |

### Dataset di Test
- **31 giorni** presenze Luglio 2025 (orari 9:00-18:00)
- **6 richieste ferie** con stati diversi
- **5 richieste straordinari** con motivazioni
- **6 note spese** €35-280 per categorie
- **8 turni reperibilità** weekend
- **Tipologie complete** per tutti i moduli

## 🚀 Deployment

### Replit (Raccomandato)
```bash
# Database e SSL automatici
# Configurazione zero setup
# Auto-scaling integrato
```

### Docker
```bash
# Multi-container con nginx
docker-compose up -d

# Accesso su http://localhost
```

### VPS/Server
```bash
# Ubuntu/CentOS con script automatico
./scripts/deploy.sh

# Setup completo nginx + systemd
```

### Cloud Providers
- **AWS**: EC2 + RDS con ALB
- **Azure**: App Service + Database
- **GCP**: App Engine + Cloud SQL

Consulta [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) per istruzioni dettagliate.

## 📚 Documentazione

- [FUNCTIONALITY_DESCRIPTION.md](FUNCTIONALITY_DESCRIPTION.md) - Descrizione completa funzionalità
- [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) - Guida installazione dettagliata
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Strategie deployment produzione

## 🔒 Sicurezza

- **CSRF Protection** su tutti i form
- **Password hashing** sicuro con Werkzeug
- **Session management** con Flask-Login
- **Input validation** client e server-side
- **Logging centralizzato** per audit trail
- **Rate limiting** su endpoint critici

## 📈 Performance

- **Connection pooling** PostgreSQL ottimizzato
- **Query optimization** con eager loading
- **Caching intelligente** per dashboard
- **Export asincrono** per dataset grandi
- **Responsive design** mobile-first

## 🛠️ Sviluppo

### Struttura Progetto
```
workly/
├── main.py              # Entry point applicazione
├── models.py            # Modelli database SQLAlchemy
├── routes.py            # Route principali applicazione
├── api_routes.py        # API REST endpoints
├── forms.py             # Form WTForms
├── utils.py             # Utility e helper functions
├── config.py            # Configurazione centralizzata
├── templates/           # Template Jinja2
├── static/             # File statici (CSS, JS, img)
├── scripts/            # Script gestione e deployment
└── docs/               # Documentazione
```

### Testing
```bash
# Unit tests
python -m pytest tests/

# Coverage report
python -m pytest --cov=. tests/

# Integration tests
python -m pytest tests/integration/
```

### Contributing
1. Fork del repository
2. Crea feature branch (`git checkout -b feature/amazing-feature`)
3. Commit modifiche (`git commit -m 'Add amazing feature'`)
4. Push branch (`git push origin feature/amazing-feature`)
5. Apri Pull Request

## 📞 Supporto

- **Issues**: Segnala bug su GitHub Issues
- **Documentazione**: Consulta i file .md nella repo
- **FAQ**: Vedi sezione Troubleshooting in INSTALLATION_GUIDE.md

## 📄 Licenza

Questo progetto è licenziato sotto la Licenza MIT - vedi il file [LICENSE](LICENSE) per dettagli.

## 🙏 Riconoscimenti

- **Flask** e l'ecosistema Python
- **Bootstrap** per il framework CSS
- **Font Awesome** per le icone
- **PostgreSQL** per il database
- **Replit** per la piattaforma di hosting

---

**Workly** - La soluzione completa per la gestione della forza lavoro moderna.