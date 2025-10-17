# Life - Multi-Tenant Workforce Management Platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Life** è una piattaforma SaaS multi-tenant completa per la gestione delle risorse umane e la comunicazione aziendale interna. Combina potenti funzionalità operative (**FLOW**) con strumenti di social networking aziendale (**CIRCLE**) per creare un ecosistema digitale integrato.

## 🎯 Panoramica

La piattaforma è divisa in due sezioni principali:

- **FLOW** - *"Il tuo gestore smart del tempo"*  
  Gestione operativa: presenze, turni, ferie, straordinari, rimborsi, reperibilità
  
- **CIRCLE** - *"Il centro della tua community aziendale"*  
  Social intranet: news, gruppi, sondaggi, documenti, calendario, directory dipendenti

### 🏢 Multi-Tenant Architecture

Sistema **path-based multi-tenancy** con isolamento completo dei dati:
- Ogni azienda opera su `/tenant/<slug>/` con autenticazione dedicata
- Segregazione totale a livello database tramite `company_id`
- Username ed email univoci **per azienda** (non globali)
- Due livelli amministrativi: **SUPERADMIN** (sistema) e **ADMIN** (aziendale)

## 🚀 Quick Start

### Installazione Rapida (Replit)
1. Fork questo progetto su Replit
2. Il database PostgreSQL viene creato automaticamente
3. Premi "Run" per avviare l'applicazione
4. **SUPERADMIN**: Crea la tua prima azienda dalla dashboard globale
5. **ADMIN**: Accedi a `/tenant/<slug>/` e configura la tua azienda

### Installazione Locale
```bash
git clone <repository-url>
cd life

# Setup ambiente
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configura database
export DATABASE_URL="postgresql://user:pass@localhost/life"
export SESSION_SECRET="your-secret-key"

# Avvia applicazione
gunicorn --bind 0.0.0.0:5000 --reload main:app
```

### Con Docker
```bash
docker-compose up -d
```

## 📋 Funzionalità Complete

### 🏢 Sistema Multi-Tenant

#### Gestione Aziende
- **Path-based tenancy**: Ogni company con slug univoco e URL dedicato
- **Isolamento dati**: Segregazione completa a livello database
- **Branding personalizzato**: Logo, colori, configurazioni per azienda
- **SUPERADMIN dashboard**: Gestione globale tutte le aziende

#### Ruoli e Permessi
- **SUPERADMIN**: Gestione sistema, creazione aziende, news piattaforma
- **ADMIN aziendale**: Amministrazione completa propria company
- **70+ permessi granulari**: Controllo dettagliato su ogni funzionalità
- **5 ruoli standard configurabili**: Personalizzabili per ogni azienda
- **Accesso multi-sede**: Gestione `all_sedi` o `sede_id` specifico

---

## 🔄 FLOW - Gestione Operativa

### ⏰ Tracciamento Presenze
- **Clock-in/out digitale**: Registrazione entrata/uscita con timestamp precisi
- **Gestione pause**: Tracciamento completo pause lavoro
- **Sistema QR Code statico**: QR permanente per sede, scansione rapida
- **Storico completo**: Visualizzazione cronologia con filtri avanzati
- **Validazione automatica**: Controllo sovrapposizioni e coerenza orari
- **Export Excel/CSV**: Esportazione dati con openpyxl e SheetJS

### 📅 Pianificazione Turni
- **Creazione turni**: Definizione orari, pause, note operative
- **Template ricorrenti**: Pattern turni ripetitivi con generazione automatica
- **Assegnazione intelligente**: Verifica disponibilità e bilanciamento carichi
- **Vista calendario**: Visualizzazione mensile/settimanale/giornaliera
- **Notifiche automatiche**: Alert per nuovi turni e modifiche
- **Regole sicurezza**: Limiti ore consecutive, riposi obbligatori

### 🔔 Gestione Reperibilità (On-Call)
- **Calendario reperibilità**: Pianificazione turni di guardia separati
- **Rotazione automatica**: Gestione equa delle reperibilità
- **Compensazione**: Tracciamento ore per retribuzione
- **Gestione interventi**: Registrazione chiamate e interventi

### 🏖️ Richieste Ferie e Permessi
- **Tipologie multiple**: Ferie, permessi retribuiti, malattia, aspettativa
- **Workflow approvazione**: Richiesta → Revisione Manager → Approvazione/Rifiuto
- **Permessi orari**: Definizione start/end time per assenze parziali
- **Validazione intelligente**: Controllo disponibilità, sovrapposizioni, festività
- **Storico completo**: Archivio richieste con motivi e decisioni
- **Notifiche sistema**: Alert automatici per manager e dipendenti

### ⏱️ Gestione Straordinari
- **Tracciamento automatico**: Calcolo ore extra da timbrature
- **Tipologie personalizzabili**: Moltiplicatori retributivi configurabili
- **Approvazione manager**: Validazione straordinari con motivazioni
- **Report dettagliati**: Esportazione dati per amministrazione
- **Banca ore**: Accumulo/utilizzo ore con soglie e scadenze

### 🚗 Rimborsi Chilometrici (Mileage)
- **Calcolo automatico**: Integrazione tabelle ACI per rimborsi kilometrici
- **Categorie veicolo**: Auto, moto, diverse cilindrate
- **Workflow approvazione**: Manager review con documentazione allegata
- **Upload documenti**: Allegati per giustificativi
- **Report mensili**: Esportazione per contabilità

### 🎊 Gestione Festività
- **Database festività**: Calendario nazionale italiano
- **Festività per sede**: Eventi specifici per location
- **Configurazione flessibile**: Gestione date, nomi, attivazione
- **Integrazione automatica**: Con pianificazione turni e ferie

### 📊 Report e Analytics
- **Dashboard manager**: Vista team con presenze real-time
- **Statistiche aggregate**: Ore lavorate, straordinari, assenze
- **Export multipli**: Excel/CSV server-side e client-side
- **Filtri avanzati**: Per dipendente, sede, reparto, periodo
- **KPI operativi**: Metriche performance e alerts anomalie

---

## 🤝 CIRCLE - Social Intranet

### 📰 News Feed e Comunicazioni
- **Post aziendali**: Pubblicazione news, aggiornamenti, annunci
- **Tipologie post**: Comunicazione ufficiale, news, evento, altro
- **Interazione social**: Like, commenti, thread discussione
- **Notifiche real-time**: Alert per nuovi contenuti rilevanti
- **Email integration**: Invio comunicazioni via email opzionale

### ⏳ Delorean - Storia Aziendale
- **Timeline eventi**: Cronologia eventi storici azienda
- **Milestone**: Traguardi, successi, momenti importanti
- **Ricorrenze**: Gestione anniversari e celebrazioni
- **Media gallery**: Foto e documenti storici

### 👥 Gruppi e Community
- **Gruppi di lavoro**: Team progetto, dipartimenti, commissioni
- **Membership**: Gestione membri e permessi gruppo
- **Spazio condiviso**: Area discussione e risorse
- **Privacy**: Gruppi pubblici o riservati

### 📊 Sondaggi e Survey
- **Creazione sondaggi**: Domande multiple choice, scala, testo libero
- **Targeting**: Invio a gruppi/reparti specifici
- **Anonimato**: Opzione risposte anonime
- **Analytics**: Risultati aggregati con visualizzazioni grafiche

### 📅 Calendario Aziendale
- **Eventi condivisi**: Eventi aziendali, riunioni, scadenze
- **Promemoria**: Notifiche automatiche pre-evento
- **Partecipazione**: RSVP e gestione presenza
- **Integrazione**: Sync con calendar esterni

### 📁 Document Management
- **Repository centralizzato**: Archiviazione documenti aziendali
- **Categorizzazione**: Organizzazione per cartelle/tag
- **Permessi**: Controllo accesso per ruolo/gruppo
- **Versioning**: Storico modifiche e revisioni
- **Ricerca full-text**: Trova documenti velocemente

### 🔗 Tool Links - Portale Strumenti
- **Directory strumenti**: Raccolta link applicazioni aziendali
- **Categorizzazione**: Organizzazione per tipologia/reparto
- **Single Sign-On**: Integrazione SSO dove possibile
- **Guide rapide**: Descrizioni utilizzo strumenti

### 👤 Personas - Directory Dipendenti
- **Profili completi**: Info personali, contatti, competenze
- **Organigramma**: Visualizzazione gerarchia aziendale
- **Social fields**: Interessi, hobby, bio personale
- **Foto profilo**: Upload con resize automatico (circolare)
- **Search avanzata**: Trova colleghi per skills/reparto/sede

---

## 💬 Sistema di Messaggistica Interna

### Caratteristiche Avanzate
- **Messaggi multi-destinatario**: Invio a più utenti simultaneamente
- **Raggruppamento intelligente**: Messaggi multipli visualizzati come uno solo
- **UUID group tracking**: `message_group_id` per gestione gruppi
- **Backward compatibility**: Raggruppamento legacy via sender+title+timestamp
- **Tipologie messaggio**: Info, warning, success, danger con icone colorate
- **Stato lettura**: Tracking messaggi letti/non letti con badge contatori
- **Gestione completa**: Marca letto, elimina, marca tutti, elimina gruppo

### Notifiche Workflow
- **Automatizzazione**: Notifiche auto per eventi rilevanti
- **Integrazione SMTP**: Email notifications opzionali
- **Badge contatori**: Numero non letti sempre visibile
- **Filtri intelligenti**: Organizzazione per tipo, mittente, data

---

## 📧 Sistema Email Multi-Tenant

### Architettura Ibrida SMTP
- **Config globale SUPERADMIN**: Server SMTP sistema per comunicazioni piattaforma
- **Config per azienda**: Ogni company può configurare proprio SMTP
- **Crittografia Fernet**: Password SMTP encrypted at rest
- **Test UI**: Interfaccia per verificare configurazione email
- **Fallback intelligente**: Sistema → Aziendale in base al contesto

### Funzionalità Email
- **Template brandizzati**: Email personalizzate per azienda
- **Email transazionali**: Conferme, reset password, alerts
- **Broadcast selettivi**: Invio massivo a gruppi specifici
- **Log completi**: Tracking invii, successi ed errori

---

## 📰 Platform News Management

### Gestione Novità Sistema
- **Esclusivo SUPERADMIN**: Solo admin sistema pubblica news
- **Visibilità globale**: Tutte le aziende vedono novità piattaforma
- **Customizzazione**: Icone Font Awesome, colori Bootstrap
- **Ordinamento**: Priorità visualizzazione configurabile
- **Attivazione**: On/off per singola news
- **Display homepage**: Sezione dedicata con card colorate

---

## 🔒 Sicurezza Avanzata

### Password Security
- **Policy forte**: Minimo 8 caratteri con uppercase, lowercase, numero, speciale
- **Validazione real-time**: Feedback immediato durante digitazione
- **Hash sicuro**: Werkzeug con salt automatico
- **Reset sicuro**: Token temporaneo con scadenza

### Protezioni Sistema
- **CSRF Protection**: Token anti-forgery su tutti i form
- **Session management**: Flask-Login con timeout configurabile
- **Input validation**: Client e server-side su tutti gli input
- **SQL injection prevention**: SQLAlchemy ORM con parametrized queries
- **XSS protection**: Template auto-escaping Jinja2
- **Audit trail**: Log completo accessi e azioni sensibili

### Multi-Tenant Security
- **Data isolation**: Filtri company_id su tutte le query
- **Middleware tenancy**: Protezione automatica path-based
- **Session scoping**: Sessioni isolate per azienda
- **Permission checking**: Verifica permessi su ogni operazione

---

## 🛠️ Stack Tecnologico

### Backend
- **Framework**: Flask 3.0+ con blueprint architecture
- **ORM**: SQLAlchemy con declarative base
- **Database**: PostgreSQL (esclusivo, no SQLite)
- **Authentication**: Flask-Login con session management
- **Forms**: WTForms + Flask-WTF con CSRF protection
- **Server**: Gunicorn WSGI production-ready
- **Email**: Flask-Mail con SMTP multi-tenant

### Frontend
- **Template Engine**: Jinja2 con inheritance e macros
- **CSS Framework**: Bootstrap 5 (dark theme)
- **Icons**: Font Awesome 6 completo
- **JavaScript**: Vanilla JS con librerie specifiche
- **Charts**: Chart.js per analytics (optional)
- **Export**: SheetJS (XLSX) per Excel client-side

### Libraries & Tools
- **Image Processing**: Pillow per resize/crop profili
- **Excel Generation**: openpyxl server-side
- **Encryption**: Cryptography (Fernet) per SMTP passwords
- **QR Codes**: qrcode per generazione QR sedi
- **PDF**: ReportLab (optional)
- **CSV Safe**: defusedcsv per import sicuri
- **Email Validation**: email-validator
- **JWT**: PyJWT (optional)

### Infrastructure
- **Multi-tenancy**: Path-based con middleware custom
- **Database Migrations**: SQLAlchemy db.create_all() + manual ALTER
- **Session Storage**: Server-side con Flask sessions
- **File Storage**: Local filesystem + database BLOB
- **Caching**: Optional Redis/Memcached ready

---

## 📦 Installazione Dettagliata

### Requisiti
- Python 3.11+
- PostgreSQL 13+ (richiesto, no SQLite)
- 1GB+ RAM raccomandato
- Gunicorn per produzione

### Setup Completo

```bash
# Clone repository
git clone <repository-url>
cd life

# Crea ambiente virtuale
python3 -m venv venv
source venv/bin/activate

# Installa dipendenze
pip install -r requirements.txt

# Configura variabili ambiente
export DATABASE_URL="postgresql://user:pass@localhost:5432/life"
export SESSION_SECRET="your-very-secure-secret-key-min-32-chars"

# Opzionale: Config SMTP globale
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USERNAME="your-email@gmail.com"
export SMTP_PASSWORD="your-app-password"
export SMTP_FROM_EMAIL="noreply@yourcompany.com"
export SMTP_FROM_NAME="Life Platform"

# Inizializza database (crea tabelle)
python
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
>>> exit()

# Avvia applicazione
gunicorn --bind 0.0.0.0:5000 --reload --workers 2 main:app
```

### Primo Setup Sistema

1. **Accedi come SUPERADMIN**:
   - Crea primo utente SUPERADMIN via script o manualmente nel DB
   - Login dalla root `/` (non `/tenant/<slug>`)

2. **Crea prima azienda**:
   - Dashboard SUPERADMIN → "Crea Nuova Azienda"
   - Compila: Nome, Slug (URL-safe), Configurazioni
   - Assegna primo ADMIN aziendale

3. **Setup aziendale**:
   - Login ADMIN a `/tenant/<slug>/login`
   - Configura: Sedi, Reparti, Ruoli personalizzati
   - Importa utenti (manuale o CSV bulk)
   - Setup SMTP aziendale (opzionale)
   - Configura permessi ruoli

4. **Go-live**:
   - Comunica URL `/tenant/<slug>` ai dipendenti
   - Distribuisci credenziali iniziali
   - Configura QR code sedi per presenze

---

## 🔧 Configurazione

### Variabili d'Ambiente Essenziali

```bash
# Database (REQUIRED)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Security (REQUIRED)
SESSION_SECRET=your-very-secure-secret-key-minimum-32-characters

# Environment
FLASK_ENV=production  # development/production
DEBUG=False          # True solo in sviluppo

# SMTP Globale (OPTIONAL - per email sistema)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@yourplatform.com
SMTP_FROM_NAME=Life Platform

# Replit Auto-Config (gestite automaticamente)
PGDATABASE=...
PGHOST=...
PGUSER=...
PGPASSWORD=...
PGPORT=...
```

### Configurazione SMTP per Azienda

ADMIN aziendale può configurare SMTP custom:
- Dashboard → Impostazioni → Configurazione Email
- Inserisci credenziali SMTP
- Test configurazione con email prova
- Salva (password encrypted con Fernet)

---

## 🚀 Deployment

### Replit (Raccomandato)
- Database PostgreSQL automatico
- SSL/TLS integrato
- Autoscaling built-in
- Zero configuration
- Deploy immediato

### Docker

```bash
# Build e run
docker-compose up -d

# Logs
docker-compose logs -f

# Stop
docker-compose down
```

### VPS/Server

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip postgresql nginx

# Setup virtualenv e app
# Configura systemd service
# Setup nginx reverse proxy
# Configura SSL con Let's Encrypt
```

### Cloud Providers
- **AWS**: EC2 + RDS PostgreSQL + ALB
- **Azure**: App Service + Azure Database
- **GCP**: App Engine + Cloud SQL
- **DigitalOcean**: Droplet + Managed PostgreSQL

Vedi [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) per guide dettagliate.

---

## 📁 Struttura Progetto

```
life/
├── main.py                    # Entry point applicazione
├── app.py                     # Flask app initialization
├── models.py                  # Modelli database SQLAlchemy
├── middleware_tenant.py       # Multi-tenant middleware
├── encryption_utils.py        # Fernet encryption per SMTP
├── blueprints/               # Blueprint modulari
│   ├── auth.py               # Autenticazione multi-tenant
│   ├── admin.py              # Gestione azienda (ADMIN)
│   ├── superadmin.py         # Dashboard globale (SUPERADMIN)
│   ├── attendance.py         # Presenze e timbrature
│   ├── shifts.py             # Turni e pianificazione
│   ├── leaves.py             # Ferie e permessi
│   ├── overtime.py           # Straordinari e banca ore
│   ├── mileage.py            # Rimborsi chilometrici
│   ├── messages.py           # Messaggistica interna
│   ├── circle.py             # Social intranet (CIRCLE)
│   ├── news.py               # News feed aziendali
│   ├── platform_news.py      # News piattaforma (SUPERADMIN)
│   └── ...                   # Altri blueprint
├── templates/                # Template Jinja2
│   ├── base.html            # Template base con sidebar
│   ├── auth/                # Login, register, reset
│   ├── admin/               # Dashboard amministrazione
│   ├── attendance/          # UI presenze
│   ├── circle/              # UI social intranet
│   └── ...
├── static/                   # Assets statici
│   ├── css/                 # Custom CSS
│   ├── js/                  # JavaScript
│   ├── img/                 # Immagini
│   └── uploads/             # Upload utenti
├── scripts/                  # Utility scripts
├── docs/                     # Documentazione
├── requirements.txt          # Dipendenze Python
├── README.md                # Questo file
└── FUNCTIONALITY_DESCRIPTION.md  # Descrizione commerciale
```

---

## 🧪 Testing

```bash
# Unit tests (quando implementati)
python -m pytest tests/

# Coverage report
python -m pytest --cov=. tests/

# Integration tests
python -m pytest tests/integration/

# Load testing
locust -f tests/load_test.py
```

---

## 📊 Performance

### Ottimizzazioni Implementate
- **Connection pooling**: PostgreSQL con pool_recycle e pre_ping
- **Eager loading**: Riduzione N+1 queries con joinedload
- **Query optimization**: Indici database su colonne critiche
- **Caching**: Session-based per dashboard frequenti
- **Lazy loading**: Caricamento differito dati pesanti
- **Export asincrono**: Background jobs per dataset grandi
- **Responsive design**: Mobile-first con Bootstrap

### Metriche Target
- Login: < 500ms
- Dashboard load: < 1s
- Query presenze: < 200ms
- Export Excel 1000 righe: < 3s

---

## 📚 Documentazione

### Guide Disponibili
- **[FUNCTIONALITY_DESCRIPTION.md](FUNCTIONALITY_DESCRIPTION.md)**: Descrizione completa funzionalità (commerciale)
- **[replit.md](replit.md)**: Architettura tecnica e decisioni design
- **README.md**: Questo file (setup e overview)

### Guide da Creare
- `INSTALLATION_GUIDE.md`: Setup passo-passo dettagliato
- `DEPLOYMENT_GUIDE.md`: Strategie deployment produzione
- `API_DOCUMENTATION.md`: Endpoints API (se implementati)
- `USER_MANUAL.md`: Manuale utente finale

---

## 🤝 Sviluppo e Contributi

### Workflow Sviluppo

```bash
# Fork e clone
git clone <your-fork-url>
cd life

# Crea feature branch
git checkout -b feature/nome-feature

# Sviluppa e testa
# ... codice ...

# Commit con messaggio descrittivo
git commit -m "feat: Aggiunta funzionalità X"

# Push e crea PR
git push origin feature/nome-feature
```

### Convenzioni Codice
- **Python**: PEP 8 style guide
- **Imports**: Standard library → Third party → Local
- **Naming**: snake_case per funzioni/variabili, PascalCase per classi
- **Docstrings**: Google style per funzioni pubbliche
- **Comments**: Italiano o inglese consistente

### Best Practices
- Mai hardcodare `user_id` o `company_id` nelle query
- Sempre usare `filter_by_company()` per filtri multi-tenant
- Validare input client e server-side
- Log operazioni sensibili per audit
- Test prima di commit (quando implementati)

---

## 🐛 Troubleshooting

### Database Connection Errors
```bash
# Verifica DATABASE_URL
echo $DATABASE_URL

# Test connessione PostgreSQL
psql $DATABASE_URL -c "SELECT version();"

# Check pool connections
# Aumenta pool_size se necessario in app.py
```

### Multi-Tenant Issues
```bash
# Verifica slug azienda esistente
SELECT id, name, slug FROM company;

# Check user company_id
SELECT id, username, company_id FROM user WHERE username='...';

# Verifica middleware attivo
# Log in middleware_tenant.py
```

### Email SMTP Errors
```bash
# Test SMTP manualmente
python -c "
from flask_mail import Mail, Message
from app import app, mail
with app.app_context():
    msg = Message('Test', recipients=['test@example.com'])
    msg.body = 'Test email'
    mail.send(msg)
"

# Verifica encryption SMTP password
# Check encryption_utils.py con key corretta
```

### Performance Issues
```bash
# Enable SQL logging
export SQLALCHEMY_ECHO=True

# Analizza slow queries
# Check PostgreSQL pg_stat_statements

# Profile con werkzeug
export FLASK_DEBUG=True
# Usa profiler middleware
```

---

## 📞 Supporto

- **GitHub Issues**: Segnala bug e richiedi features
- **Documentazione**: Consulta file .md nella repo
- **Email**: [inserire contatto supporto]

---

## 🗺️ Roadmap

### In Sviluppo
- [ ] Mobile App (iOS/Android native)
- [ ] API RESTful pubbliche per integrazioni
- [ ] Advanced Analytics con BI dashboard
- [ ] Integrazione ERP (SAP, Oracle)
- [ ] AI/ML per predizioni assenze e ottimizzazione turni

### Considerazioni Future
- [ ] Recruitment Module (ATS)
- [ ] Performance Review System
- [ ] Training Management
- [ ] Expense Management completo
- [ ] Project Management integrato
- [ ] Multi-language (i18n completo)

---

## 📄 Licenza

Questo progetto è licenziato sotto la Licenza MIT - vedi il file [LICENSE](LICENSE) per dettagli.

---

## 🙏 Ringraziamenti

- **Flask** e l'ecosistema Python per il framework robusto
- **Bootstrap** per il design system moderno
- **Font Awesome** per l'iconografia completa
- **PostgreSQL** per il database enterprise-grade
- **SQLAlchemy** per l'ORM potente e flessibile
- **Replit** per la piattaforma di hosting e sviluppo
- Tutti i contributor e utilizzatori della piattaforma

---

## 📈 Statistiche Progetto

- **70+ permessi granulari**: Controllo accesso dettagliato
- **15+ blueprints modulari**: Architettura organizzata
- **50+ template Jinja2**: UI completa e responsiva
- **30+ modelli database**: Schema completo
- **Multi-tenant nativo**: Architettura scalabile
- **FLOW + CIRCLE**: Doppia value proposition

---

**Life Platform** - *Semplifica il lavoro, connettiti alle persone.* ⏱️🤝

La soluzione completa per la digital transformation delle risorse umane nelle PMI.
