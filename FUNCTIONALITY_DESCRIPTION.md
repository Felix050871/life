# Workly - Workforce Management Platform

## Descrizione Generale

Workly è una piattaforma completa di gestione della forza lavoro sviluppata con Flask, progettata per aziende che necessitano di tracciamento presenze, gestione turni, amministrazione del personale e controllo operativo avanzato. Il sistema supporta modalità operative flessibili (ORARIA/TURNI) e offre un controllo granulare dei permessi basato sui ruoli.

## Tecnologie Utilizzate

### Backend
- **Framework**: Flask (Python)
- **Database**: PostgreSQL (produzione) / SQLite (sviluppo)
- **ORM**: SQLAlchemy con Flask-SQLAlchemy
- **Autenticazione**: Flask-Login con gestione sessioni
- **Forms**: WTForms con Flask-WTF e validazione CSRF
- **Server**: Gunicorn WSGI con supporto autoscale

### Frontend
- **Template Engine**: Jinja2
- **CSS Framework**: Bootstrap 5 con tema dark personalizzato
- **JavaScript**: Vanilla JS con librerie specifiche
- **Icons**: Font Awesome 6
- **Charts**: Chart.js per statistiche
- **Export**: SheetJS (XLSX) per export Excel

### Deployment
- **Platform**: Replit con deployment automatico
- **Environment**: Configurazione tramite variabili d'ambiente
- **SSL**: Gestione automatica certificati TLS
- **Monitoring**: Health checks integrati

## Architettura Modulare

```
├── Core System
│   ├── Authentication & Authorization
│   ├── Role-Based Permissions (30+ granular permissions)
│   ├── Multi-Site Management
│   └── Configuration Management
│
├── Workforce Management
│   ├── User Management
│   ├── Attendance Tracking
│   ├── Work Schedules
│   └── QR Code System
│
├── Operations
│   ├── Shift Management
│   ├── On-Call Coverage (Reperibilità)
│   ├── Leave Requests
│   └── Overtime Management
│
├── Financial
│   ├── Expense Reports
│   ├── Category Management
│   └── Approval Workflows
│
└── Communication & Reporting
    ├── Internal Messaging
    ├── Dashboard & Analytics
    ├── Export Systems
    └── Holiday Management
```

## Funzionalità Principali

### 🔐 Sistema di Autenticazione e Autorizzazione
- **Login sicuro** con gestione sessioni e "Ricordami"
- **Reset password** con token temporanei
- **5 ruoli standardizzati**: Amministratore, Responsabile, Supervisore, Operatore, Ospite
- **30+ permessi granulari** configurabili per ogni funzionalità
- **Controllo accesso** basato su sede o globale (multi-sede)

### 👥 Gestione Utenti
- **Anagrafica completa** con nome, cognome, email, ruolo
- **Assegnazione sede** specifica o accesso a tutte le sedi
- **Orari di lavoro** personalizzabili per utente
- **Percentuale part-time** per gestione orari ridotti
- **Stato attivo/inattivo** per controllo accessi

### 🏢 Gestione Sedi
- **Sedi multiple** con modalità operative distinte
- **Modalità ORARIA**: controllo presenze con orari fissi
- **Modalità TURNI**: gestione turnazioni senza controllo orario rigido
- **Configurazione orari** per sede e tipologia lavoro

### ⏰ Tracciamento Presenze
- **Entrata/Uscita** con timestamp precisi
- **Gestione pause** (inizio/fine pausa)
- **Controllo ritardi** e anticipi basato su orari assegnati
- **Note giornaliere** per ogni registrazione presenza
- **Storico completo** con filtri per periodo e utente
- **Sistema QR Code** per registrazione rapida

### 📊 Dashboard e Analytics
- **Dashboard personali** con widget configurabili
- **Statistiche presenze** per giorno/settimana/mese
- **Widget team** per supervisori (presenze sede)
- **Contatori real-time** (ore lavorate, giorni, media)
- **Grafici interattivi** per analisi trend

### 🔄 Gestione Turni e Reperibilità
- **Template presidio** per coperture automatiche
- **Generazione turni** intelligente con bilanciamento carichi
- **Turni reperibilità** separati con gestione interventi
- **Calendario turni** con navigazione temporale
- **Missing roles detection** per coperture incomplete

### 🏖️ Richieste Ferie e Permessi
- **8 tipologie configurabili**: Ferie, Permessi, Malattia, Congedi, ecc.
- **Permessi orari** con start/end time per richieste parziali
- **Workflow approvazione** automatico basato su ruoli
- **Validazione sovrapposizioni** e controlli business logic
- **Notifiche automatiche** per approvazioni/rifiuti

### ⏱️ Gestione Straordinari
- **Tipologie straordinari** con moltiplicatori paga
- **Richieste dettagliate** con data, orari, motivazione
- **Calcolo ore automatico** con gestione turni notturni
- **Approvazione gerarchica** per controllo costi

### 💰 Note Spese
- **Categorie personalizzabili**: Trasferte, Carburante, Pasti, ecc.
- **Upload allegati** per ricevute e documenti
- **Workflow approvazione** con commenti
- **Export Excel** con filtri avanzati
- **Dashboard spese** per controllo budget

### 💬 Messaggistica Interna
- **Invio messaggi** multi-destinatario
- **Categorie messaggi**: Informativo, Successo, Attenzione, Urgente
- **Notifiche automatiche** per approvazioni workflow
- **Gestione lettura** e cancellazione messaggi
- **Filtri per sede** per messaggi targettizzati

### 🎯 Sistema QR Code
- **QR statico** per entrata/uscita rapida
- **Generazione dinamica** per ambienti cloud
- **Pagine dedicate** per ogni tipo di registrazione
- **Controlli admin** per rigenerazione codici

### 📈 Reporting e Export
- **Export Excel** per tutti i moduli principali
- **Filtri avanzati** per periodo, utente, stato
- **Report personalizzati** per presenze team
- **Esportazione massiva** con performance ottimizzate

### 🎄 Gestione Festività
- **Festività nazionali** e per sede specifica
- **Configurazione flessibile** mese/giorno
- **Integrazione calcoli** presenze e permessi
- **Gestione admin** completa per calendario

## Modalità Operative

### Modalità ORARIA
- Controllo rigido orari entrata/uscita
- Rilevamento ritardi e anticipi
- Orari fissi con range flessibili (es. 9:00-9:30 entrata)
- Calcolo ore lavorate precise

### Modalità TURNI
- Gestione turnazioni senza controllo orario fisso
- Assegnazione turni da template presidio
- Flessibilità oraria per coperture 24/7
- Bilanciamento automatico carichi lavoro

## Sicurezza e Performance

### Sicurezza
- **CSRF Protection** su tutti i form
- **Password hashing** con Werkzeug Security
- **Session management** sicuro con Flask-Login
- **Validazione input** lato client e server
- **Logging centralizzato** per audit trail

### Performance
- **Connection pooling** PostgreSQL
- **Query optimization** con eager loading
- **Caching intelligente** per dashboard
- **Export asincrono** per large dataset
- **Responsive design** per mobile

## Requisiti di Sistema

### Ambiente di Produzione
- **Python**: 3.11+
- **Database**: PostgreSQL 13+
- **Memory**: 512MB+ RAM
- **Storage**: 1GB+ per applicazione + database
- **Network**: HTTPS (SSL/TLS)

### Dipendenze Principali
- Flask 3.0+
- SQLAlchemy 2.0+
- PostgreSQL adapter (psycopg2)
- Bootstrap 5.3+
- Font Awesome 6+

## Utenti di Test

Il sistema include utenti preconfigurati per testing:

| Username | Password | Ruolo | Descrizione |
|----------|----------|-------|-------------|
| admin | password123 | Amministratore | Accesso completo sistema |
| mario.rossi | password123 | Responsabile | Gestione operativa |
| paolo.verdi | password123 | Supervisore | Controllo globale |
| luca.ferrari | password123 | Operatore | Funzioni base |

## Dataset di Test

Il sistema include un dataset completo per Luglio 2025:
- **31 giorni** presenze realistiche (orari 9:00-18:00)
- **6 richieste ferie** con stati diversi (approvate/pending)
- **5 richieste straordinari** con motivazioni
- **6 note spese** da €35 a €280 per categorie diverse
- **8 turni reperibilità** per weekend luglio
- **6 interventi emergenza** collegati ai turni
- **Tipologie configurate** per tutti i moduli

Questo dataset permette di testare immediatamente tutte le funzionalità senza configurazione aggiuntiva.