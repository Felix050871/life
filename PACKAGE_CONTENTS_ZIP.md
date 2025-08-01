# Workly Platform - Package Contents

## Archivio: workly_platform_complete.zip

### File Python Core
- `main.py` - Entry point dell'applicazione
- `app.py` - Configurazione Flask e database
- `models.py` - Modelli database SQLAlchemy
- `routes.py` - Route e logica applicazione
- `api_routes.py` - API endpoints
- `forms.py` - Form WTForms
- `utils.py` - Utility functions
- `config.py` - Configurazioni

### Template HTML (templates/)
- Tutti i template Jinja2 per l'interfaccia utente
- Layout base e template specifici per ogni funzionalità
- Template per dashboard, gestione utenti, presenze, turni, etc.

### File Statici (static/)
- CSS personalizzati
- JavaScript per interattività
- Immagini e icone
- Font e risorse grafiche

### Configurazione
- `pyproject.toml` - Dipendenze Python
- `requirements.txt` - Lista requirements pip
- `.replit` - Configurazione Replit
- `replit.nix` - Environment Nix
- `replit.md` - Documentazione progetto

### Documentazione
- `README.md` - Guida principale
- `FUNCTIONALITY_DESCRIPTION.md` - Descrizione funzionalità
- `TEST_LOGIN_CREDENTIALS.md` - Credenziali test (password: 123456)

## Note Installazione
1. Estrarre l'archivio
2. Installare dipendenze: `pip install -r requirements.txt`
3. Configurare database PostgreSQL
4. Avviare con: `gunicorn --bind 0.0.0.0:5000 main:app`

## Credenziali Test
- **Admin:** admin / 123456
- **Manager:** management / 123456  
- **Operatore:** operatore / 123456

---
**Data creazione:** 1 Agosto 2025
**Versione:** Production Ready