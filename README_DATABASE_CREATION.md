# Script Creazione Database Workly

## File generati:

### 1. workly_database_schema_20250801_104501.sql
Script SQL completo per creare tutte le tabelle con struttura corretta:
- 26 tabelle con tutti i campi attuali
- Vincoli di integrità referenziale
- Indici per prestazioni
- Commenti per documentazione

**Campo importante:** La tabella `user` usa il campo `active` (NON `is_active`)

### 2. initialize_database.py
Script Python per inizializzazione database:
- Import corretti dai modelli attuali
- Creazione tabelle con `db.create_all()`
- Funzione per creare utente amministratore
- Gestione errori completa

## Utilizzo:

### Opzione 1: Script SQL diretto
```bash
psql -h hostname -U username -d database_name -f workly_database_schema_20250801_104501.sql
```

### Opzione 2: Script Python (raccomandato)
```bash
python initialize_database.py
```

### Opzione 3: In codice Python
```python
from main import app
with app.app_context():
    from models import db
    db.create_all()
```

## Struttura Database:

**Tabelle principali:**
- user (campo: active)
- user_role 
- sede
- aci_table

**Tabelle presenze:**
- attendance_event
- shift
- shift_template

**Tabelle richieste:**
- leave_request, leave_type
- overtime_request, overtime_type
- mileage_request
- expense_report, expense_category

**Tabelle reperibilità:**
- reperibilita_shift
- reperibilita_coverage
- reperibilita_intervention

**Tabelle presidio:**
- presidio_coverage
- presidio_coverage_template

**Altre tabelle:**
- internal_message
- holiday
- work_schedule
- intervention
- password_reset_token
- user_sede_association

Generato automaticamente il 2025-08-01 10:45:01
