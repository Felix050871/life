# Workly - Workforce Management Platform

Una piattaforma completa per la gestione delle presenze e delle risorse umane, progettata per semplificare il tracciamento degli orari di lavoro e la gestione delle sedi aziendali.

## Caratteristiche Principali

### 🏢 Gestione Sedi
- Configurazione di multiple sedi aziendali
- Associazione utenti a sedi specifiche
- Gestione indirizzi e descrizioni sedi

### ⏰ Orari di Lavoro
- Configurazione orari personalizzati per sede
- Supporto per orari flessibili e standard
- Validazione automatica orari

### 👥 Gestione Utenti
- Sistema a ruoli: Admin, Responsabili, Sviluppatore, Operatore, Redattore, Management
- Associazione utente-sede
- Gestione percentuali part-time

### 📊 Tracciamento Presenze
- Registrazione entrate/uscite multiple giornaliere
- Gestione pause lavoro
- Calcolo automatico ore lavorate
- Indicatori ritardo/anticipo

### 📱 Sistema QR Code
- QR code per registrazione rapida presenze
- Pagine dedicate per entrata/uscita
- Generazione QR statici per deployment

## Installazione e Configurazione

### Prerequisiti
- Python 3.8+
- PostgreSQL (o SQLite per sviluppo)
- Flask e dipendenze (vedi requirements.txt)

### Setup Rapido

1. **Installazione dipendenze**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configurazione ambiente**:
   ```bash
   export DATABASE_URL="postgresql://user:pass@host:port/db"
   export SESSION_SECRET="your-secret-key"
   ```

3. **Inizializzazione database**:
   ```bash
   python setup_database.py
   ```

4. **Avvio applicazione**:
   ```bash
   python main.py
   ```

### Accesso Sistema

Dopo l'inizializzazione del database, puoi accedere con:

- **Admin**: `admin` / `admin123`
- **Responsabile**: `responsabile` / `resp123`
- **Sviluppatore**: `sviluppatore` / `dev123`
- **Operatore**: `operatore` / `op123`
- **Management**: `management` / `mgmt123`

## Struttura Progetto

```
workly/
├── app.py              # Configurazione Flask app
├── main.py             # Entry point applicazione
├── models.py           # Modelli database SQLAlchemy
├── routes.py           # Route e logica applicazione
├── forms.py            # Form WTForms
├── utils.py            # Utilità e helper functions
├── setup_database.py   # Script inizializzazione DB
├── templates/          # Template Jinja2
├── static/             # File statici (CSS, JS, immagini)
└── README.md          # Documentazione
```

## Funzionalità per Ruolo

### Admin
- Gestione completa utenti
- Configurazione sedi e orari
- Gestione QR codes
- Accesso a tutte le statistiche

### Responsabili
- Gestione turni e coperture
- Approvazione richieste ferie
- Visualizzazione presenze team
- Gestione interventi

### Sviluppatore/Operatore/Redattore
- Registrazione proprie presenze
- Richiesta ferie/permessi
- Visualizzazione propri turni
- Registrazione interventi

### Management
- Visualizzazione turni e presenze team
- Accesso statistiche (sola lettura)
- Monitoraggio generale sistema

## API e Integrazione

### QR Code System
- `/qr/entrata` - Pagina QR per entrata
- `/qr/uscita` - Pagina QR per uscita
- `/qr_login/<action>` - Endpoint registrazione via QR

### Export Dati
- Export CSV presenze e interventi
- Reportistica automatica
- Statistiche team personalizzabili

## Sicurezza

- Autenticazione basata su sessioni Flask-Login
- Validazione CSRF su tutti i form
- Hash password con Werkzeug
- Controllo accessi basato su ruoli

## Deployment

### Produzione con Gunicorn
```bash
gunicorn --bind 0.0.0.0:5001 --workers 2 main:app
```

### Docker (opzionale)
```dockerfile
FROM python:3.9-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "main:app"]
```

## Supporto e Contributi

Per supporto tecnico o segnalazione bug, aprire una issue nel repository.

## Licenza

Sistema proprietario - Tutti i diritti riservati.

---

**Workly** - Semplifica la gestione delle presenze aziendali.