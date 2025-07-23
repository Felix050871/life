# Pacchetto Funzioni Presidio - Workforce Management

Questo pacchetto contiene tutti i file necessari per implementare le funzionalità del menu "Presidio" del sistema di gestione presenze.

## Funzionalità Incluse

### 1. Gestione Copertura Presidio
- Creazione e modifica template di copertura con nome e periodi di validità
- Definizione fasce orarie per ogni giorno della settimana
- Assegnazione ruoli richiesti per ogni fascia oraria
- Gestione numerosità persone per ruolo
- Sistema di pause opzionali
- Duplicazione e modifica template esistenti
- Attivazione/disattivazione template
- Validazione orari e sovrapposizioni

### 2. Visualizzazione Presidi
- Vista sola lettura dei template di copertura configurati
- Tabella completa con informazioni su ogni template
- Dettaglio coperture per giorno della settimana
- Statistiche ore totali e ruoli coinvolti
- Filtri e ordinamento DataTables
- Export dati (se configurato)

### 3. API e Integrazione
- API REST per dettagli copertura presidio
- Integrazione con sistema turnazioni esistente
- Supporto per validazione date e orari
- Sistema notifiche toast per feedback utente

## Architettura File

```
presidio_package/
├── README.md                     # Documentazione generale
├── INSTALLATION.md              # Guida installazione completa
├── templates/
│   ├── presidio_coverage.html   # Gestione completa copertura
│   ├── view_presidi.html        # Visualizzazione sola lettura
│   └── presidio_detail.html     # Dettaglio singolo template
├── routes/
│   └── presidio_routes.py       # Route Flask complete
├── models/
│   └── presidio_models.py       # Modelli SQLAlchemy
├── forms/
│   └── presidio_forms.py        # Form WTForms con validazione
└── static/
    ├── js/
    │   └── presidio_scripts.js   # JavaScript interattivo
    └── css/
        └── presidio_styles.css   # CSS personalizzati
```

## Modelli Database

### PresidioCoverageTemplate
- Template principale con nome e periodo validità
- Relazione one-to-many con PresidioCoverage
- Soft delete con flag is_active
- Tracking creatore e data creazione

### PresidioCoverage  
- Coperture specifiche per giorno/orario
- Ruoli richiesti in formato JSON
- Supporto pause opzionali
- Validazione sovrapposizioni

## Installazione Rapida

1. **Copia i file** nelle directory del progetto Flask
2. **Integra modelli** nel tuo `models.py`
3. **Importa route** nel tuo `routes.py`
4. **Aggiungi form** al tuo `forms.py`
5. **Includi asset** CSS/JS nei template
6. **Crea menu** di navigazione
7. **Testa** le funzionalità

Vedi `INSTALLATION.md` per la guida completa passo-passo.

## Dipendenze

### Backend
- Flask >= 2.0
- Flask-SQLAlchemy >= 3.0
- Flask-WTF >= 1.0
- Flask-Login per autenticazione
- WTForms per validazione form

### Frontend
- Bootstrap 5.1+ per UI components
- DataTables 1.13+ per tabelle interattive
- Font Awesome 6.0+ per icone
- jQuery 3.6+ per JavaScript

### Database
- SQLAlchemy compatible database (PostgreSQL, MySQL, SQLite)
- Supporto timezone italiano (UTC+2)

## Caratteristiche Tecniche

### Sicurezza
- Controllo permessi con `@login_required`
- Validazione ruoli con `can_manage_shifts()`
- Soft delete per data retention
- Sanitizzazione input con WTForms

### UI/UX
- Design responsive mobile-first
- Dark mode support
- Toast notifications per feedback
- Loading states sui bottoni
- Validazione real-time form

### Performance
- Query ottimizzate con eager loading
- Cache template per API
- Lazy loading tabelle grandi
- Compressione asset statici

### Internazionalizzazione
- Completa localizzazione italiana
- Nomi giorni e formati data italiani
- Messaggi errore in italiano
- Timezone Europa/Roma

## API Endpoints

### GET `/presidio_coverage`
Lista template copertura presidio

### GET `/presidio_coverage/<id>`
Modifica template specifico

### GET `/presidio_detail/<id>`
Dettaglio template con coperture

### GET `/view_presidi`
Visualizzazione sola lettura

### GET `/api/presidio_coverage/<id>`
API JSON dettagli copertura

### POST `/presidio_coverage/toggle_status/<id>`
Attiva/disattiva template

### POST `/presidio_coverage/delete/<id>`
Elimina template (soft delete)

## Compatibilità

- **Flask**: 2.0+
- **Python**: 3.8+
- **Browser**: Chrome 90+, Firefox 88+, Safari 14+
- **Database**: PostgreSQL 12+, MySQL 8+, SQLite 3.35+
- **Mobile**: iOS Safari 14+, Android Chrome 90+

## Supporto e Personalizzazione

### Personalizzazione Ruoli
Modifica l'array `choices` nei form per i tuoi ruoli specifici.

### Personalizzazione Orari
Configura validazioni min/max ore nei form.

### Temi Personalizzati
Override delle classi CSS in `presidio_styles.css`.

### Integrazione Calendario
API REST compatibile con FullCalendar e altri sistemi.

## Risoluzione Problemi

- **Tabelle non create**: Esegui `db.create_all()`
- **Permessi negati**: Verifica `User.can_manage_shifts()`
- **Asset non caricati**: Controlla percorsi statici Flask
- **Errori JavaScript**: Verifica jQuery e Bootstrap caricati
- **Timezone errati**: Configura `italian_now()` nel modello

Per problemi specifici consulta `INSTALLATION.md` per debugging avanzato.