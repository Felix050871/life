#!/usr/bin/env python3
"""
Script per creare tutte le tabelle del database Workly
con la struttura ESATTA del database attuale.

Creato automaticamente in base alla struttura PostgreSQL corrente.
Compatibile con la versione corrente dei modelli Python.
"""

import os
import sys
from datetime import datetime

def create_database_schema_script():
    """Genera script SQL per creare tutte le tabelle con struttura corretta"""
    
    sql_script = f"""-- Workly Database Schema Creation Script
-- Generato automaticamente il {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- Struttura basata sul database PostgreSQL attuale

-- Elimina tabelle esistenti (in ordine per rispettare le foreign key)
DROP TABLE IF EXISTS user_sede_association CASCADE;
DROP TABLE IF EXISTS reperibilita_intervention CASCADE;
DROP TABLE IF EXISTS reperibilita_shift CASCADE;
DROP TABLE IF EXISTS reperibilita_coverage CASCADE;
DROP TABLE IF EXISTS reperibilita_template CASCADE;
DROP TABLE IF EXISTS presidio_coverage CASCADE;
DROP TABLE IF EXISTS presidio_coverage_template CASCADE;
DROP TABLE IF EXISTS shift CASCADE;
DROP TABLE IF EXISTS shift_template CASCADE;
DROP TABLE IF EXISTS attendance_event CASCADE;
DROP TABLE IF EXISTS leave_request CASCADE;
DROP TABLE IF EXISTS leave_type CASCADE;
DROP TABLE IF EXISTS overtime_request CASCADE;
DROP TABLE IF EXISTS overtime_type CASCADE;
DROP TABLE IF EXISTS mileage_request CASCADE;
DROP TABLE IF EXISTS expense_report CASCADE;
DROP TABLE IF EXISTS expense_category CASCADE;
DROP TABLE IF EXISTS internal_message CASCADE;
DROP TABLE IF EXISTS intervention CASCADE;
DROP TABLE IF EXISTS password_reset_token CASCADE;
DROP TABLE IF EXISTS holiday CASCADE;
DROP TABLE IF EXISTS "user" CASCADE;
DROP TABLE IF EXISTS user_role CASCADE;
DROP TABLE IF EXISTS work_schedule CASCADE;
DROP TABLE IF EXISTS sede CASCADE;
DROP TABLE IF EXISTS aci_table CASCADE;

-- ============================================================================
-- TABELLE PRINCIPALI
-- ============================================================================

-- Tabella ACI (veicoli e costi chilometrici)
CREATE TABLE aci_table (
    id SERIAL PRIMARY KEY,
    tipologia VARCHAR(100) NOT NULL,
    marca VARCHAR(100) NOT NULL,
    modello VARCHAR(200) NOT NULL,
    costo_km DECIMAL(10,4) NOT NULL,
    fringe_benefit_10 DECIMAL(10,4),
    fringe_benefit_25 DECIMAL(10,4),
    fringe_benefit_30 DECIMAL(10,4),
    fringe_benefit_50 DECIMAL(10,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabella Sedi
CREATE TABLE sede (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    address VARCHAR(200),
    description TEXT,
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tipologia VARCHAR(20) DEFAULT 'Oraria'
);

-- Tabella Ruoli Utente
CREATE TABLE user_role (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    permissions JSON DEFAULT '{{}}',
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabella Orari di Lavoro
CREATE TABLE work_schedule (
    id SERIAL PRIMARY KEY,
    sede_id INTEGER NOT NULL REFERENCES sede(id),
    name VARCHAR(100) NOT NULL,
    start_time TIME,
    end_time TIME,
    description TEXT,
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    days_of_week JSON DEFAULT '[]',
    start_time_min TIME,
    start_time_max TIME,
    end_time_min TIME,
    end_time_max TIME,
    UNIQUE(sede_id, name)
);

-- Tabella Utenti (CAMPO PRINCIPALE: active invece di is_active)
CREATE TABLE "user" (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    role VARCHAR(50) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    sede_id INTEGER REFERENCES sede(id),
    active BOOLEAN DEFAULT true,
    part_time_percentage DOUBLE PRECISION DEFAULT 100.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    all_sedi BOOLEAN DEFAULT false,
    work_schedule_id INTEGER REFERENCES work_schedule(id),
    aci_vehicle_id INTEGER REFERENCES aci_table(id)
);

-- Tabella Associazione Utente-Sedi (Many-to-Many)
CREATE TABLE user_sede_association (
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    sede_id INTEGER NOT NULL REFERENCES sede(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, sede_id)
);

-- ============================================================================
-- TABELLE PRESENZE E TURNI
-- ============================================================================

-- Tabella Eventi Presenza
CREATE TABLE attendance_event (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    date DATE NOT NULL,
    event_type VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    notes TEXT,
    shift_status VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sede_id INTEGER REFERENCES sede(id)
);

-- Tabella Turni
CREATE TABLE shift (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    shift_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER NOT NULL REFERENCES "user"(id)
);

-- Tabella Template Turni
CREATE TABLE shift_template (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    description TEXT,
    created_by INTEGER NOT NULL REFERENCES "user"(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TABELLE FERIE E PERMESSI
-- ============================================================================

-- Tabella Tipi Ferie
CREATE TABLE leave_type (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    requires_approval BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabella Richieste Ferie
CREATE TABLE leave_request (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    leave_type VARCHAR(50) NOT NULL,
    reason TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    approved_by INTEGER REFERENCES "user"(id),
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    start_time TIME,
    end_time TIME,
    leave_type_id INTEGER REFERENCES leave_type(id)
);

-- ============================================================================
-- TABELLE STRAORDINARI
-- ============================================================================

-- Tabella Tipi Straordinario
CREATE TABLE overtime_type (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    hourly_rate_multiplier DOUBLE PRECISION DEFAULT 1.0,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabella Richieste Straordinario
CREATE TABLE overtime_request (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES "user"(id),
    overtime_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    motivation TEXT NOT NULL,
    overtime_type_id INTEGER NOT NULL REFERENCES overtime_type(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    approved_by INTEGER REFERENCES "user"(id),
    approved_at TIMESTAMP,
    approval_comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TABELLE RIMBORSI CHILOMETRICI
-- ============================================================================

-- Tabella Richieste Rimborso Chilometrico
CREATE TABLE mileage_request (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    travel_date DATE NOT NULL,
    route_addresses JSON NOT NULL,
    total_km DOUBLE PRECISION NOT NULL,
    calculated_km DOUBLE PRECISION,
    is_km_manual BOOLEAN DEFAULT false,
    vehicle_id INTEGER REFERENCES aci_table(id),
    vehicle_description VARCHAR(200),
    cost_per_km DOUBLE PRECISION NOT NULL,
    total_amount DOUBLE PRECISION NOT NULL,
    purpose TEXT NOT NULL,
    notes TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    approved_by INTEGER REFERENCES "user"(id),
    approved_at TIMESTAMP,
    approval_comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TABELLE NOTE SPESE
-- ============================================================================

-- Tabella Categorie Spese
CREATE TABLE expense_category (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER NOT NULL REFERENCES "user"(id)
);

-- Tabella Note Spese
CREATE TABLE expense_report (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES "user"(id),
    expense_date DATE NOT NULL,
    description TEXT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    category_id INTEGER NOT NULL REFERENCES expense_category(id),
    receipt_filename VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    approved_by INTEGER REFERENCES "user"(id),
    approved_at TIMESTAMP,
    approval_comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TABELLE MESSAGGI INTERNI
-- ============================================================================

-- Tabella Messaggi Interni
CREATE TABLE internal_message (
    id SERIAL PRIMARY KEY,
    recipient_id INTEGER NOT NULL REFERENCES "user"(id),
    sender_id INTEGER REFERENCES "user"(id),
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    message_type VARCHAR(50) DEFAULT 'general',
    is_read BOOLEAN DEFAULT false,
    related_leave_request_id INTEGER REFERENCES leave_request(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TABELLE FESTIVITÀ
-- ============================================================================

-- Tabella Festività
CREATE TABLE holiday (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    description VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER NOT NULL REFERENCES "user"(id),
    sede_id INTEGER REFERENCES sede(id)
);

-- ============================================================================
-- TABELLE REPERIBILITÀ
-- ============================================================================

-- Tabella Template Reperibilità
CREATE TABLE reperibilita_template (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    description TEXT,
    created_by INTEGER NOT NULL REFERENCES "user"(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabella Copertura Reperibilità
CREATE TABLE reperibilita_coverage (
    id SERIAL PRIMARY KEY,
    day_of_week INTEGER NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    required_roles TEXT NOT NULL,
    description VARCHAR(200),
    is_active BOOLEAN DEFAULT true,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    created_by INTEGER NOT NULL REFERENCES "user"(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sedi_ids TEXT
);

-- Tabella Turni Reperibilità
CREATE TABLE reperibilita_shift (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    description VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER NOT NULL REFERENCES "user"(id)
);

-- Tabella Interventi Reperibilità
CREATE TABLE reperibilita_intervention (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    shift_id INTEGER REFERENCES reperibilita_shift(id),
    start_datetime TIMESTAMP NOT NULL,
    end_datetime TIMESTAMP,
    description TEXT,
    priority VARCHAR(10) NOT NULL DEFAULT 'medium',
    is_remote BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TABELLE PRESIDIO
-- ============================================================================

-- Tabella Template Presidio
CREATE TABLE presidio_coverage_template (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    description VARCHAR(200),
    is_active BOOLEAN DEFAULT true,
    created_by INTEGER NOT NULL REFERENCES "user"(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sede_id INTEGER REFERENCES sede(id)
);

-- Tabella Copertura Presidio
CREATE TABLE presidio_coverage (
    id SERIAL PRIMARY KEY,
    day_of_week INTEGER NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    required_roles TEXT NOT NULL,
    description VARCHAR(200),
    is_active BOOLEAN DEFAULT true,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    created_by INTEGER NOT NULL REFERENCES "user"(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    template_id INTEGER REFERENCES presidio_coverage_template(id),
    role_count INTEGER DEFAULT 1,
    break_start TIME,
    break_end TIME
);

-- ============================================================================
-- TABELLE SUPPORTO
-- ============================================================================

-- Tabella Interventi Generici
CREATE TABLE intervention (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    start_datetime TIMESTAMP NOT NULL,
    end_datetime TIMESTAMP,
    description TEXT,
    priority VARCHAR(10) NOT NULL DEFAULT 'medium',
    is_remote BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabella Token Reset Password
CREATE TABLE password_reset_token (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    token VARCHAR(100) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- INDICI PER PRESTAZIONI
-- ============================================================================

-- Indici su campi più utilizzati per query
CREATE INDEX idx_attendance_event_user_date ON attendance_event(user_id, date);
CREATE INDEX idx_attendance_event_date ON attendance_event(date);
CREATE INDEX idx_shift_user_date ON shift(user_id, date);
CREATE INDEX idx_leave_request_user_dates ON leave_request(user_id, start_date, end_date);
CREATE INDEX idx_mileage_request_user_date ON mileage_request(user_id, travel_date);
CREATE INDEX idx_overtime_request_user_date ON overtime_request(employee_id, overtime_date);
CREATE INDEX idx_internal_message_recipient ON internal_message(recipient_id, is_read);
CREATE INDEX idx_user_active ON "user"(active);
CREATE INDEX idx_holiday_month_day ON holiday(month, day);

-- ============================================================================
-- COMMENTI PER DOCUMENTAZIONE
-- ============================================================================

COMMENT ON TABLE "user" IS 'Tabella utenti - CAMPO PRINCIPALE: active (non is_active)';
COMMENT ON COLUMN "user".active IS 'Campo booleano per utenti attivi (NON is_active)';
COMMENT ON TABLE aci_table IS 'Tabella veicoli ACI per rimborsi chilometrici';
COMMENT ON TABLE mileage_request IS 'Richieste rimborso chilometrico con calcolo automatico distanze';
COMMENT ON TABLE user_role IS 'Ruoli utente con permessi JSON';
COMMENT ON TABLE attendance_event IS 'Eventi presenza (clock-in, clock-out, pause)';

-- Script completato
SELECT 'Schema database Workly creato con successo!' as status;
"""
    
    return sql_script

def create_python_initialization_script():
    """Crea script Python per inizializzazione database corretta"""
    
    python_script = """#!/usr/bin/env python3
\"\"\"
Script Python per inizializzazione database Workly
con struttura corretta basata sui modelli attuali.
\"\"\"

import os
import sys
from datetime import datetime

def initialize_database():
    \"\"\"Inizializza database con struttura corretta\"\"\"
    try:
        # Import corretto dal progetto attuale
        from main import app
        
        with app.app_context():
            # Import dei modelli dal file models.py corrente
            from models import db
            
            print("[INFO] Inizializzazione database...")
            
            # Crea tutte le tabelle basate sui modelli attuali
            db.create_all()
            
            # Verifica connessione
            result = db.session.execute(db.text('SELECT 1')).scalar()
            if result == 1:
                print("[OK] Database inizializzato e connessione verificata")
                return True
            else:
                print("[ERRORE] Problema connessione database")
                return False
                
    except Exception as e:
        print(f"[ERRORE] Inizializzazione database fallita: {e}")
        return False

def create_admin_user(username, email, password, first_name, last_name):
    \"\"\"Crea utente amministratore con ruoli corretti\"\"\"
    try:
        from main import app
        
        with app.app_context():
            from models import db, User, UserRole
            from werkzeug.security import generate_password_hash
            
            # Controlla se utente esiste già
            existing_user = User.query.filter_by(username=username).first()
            existing_email = User.query.filter_by(email=email).first()
            
            if existing_user or existing_email:
                print("[ERRORE] Username o email già esistenti")
                return False
            
            # Crea o ottieni ruolo amministratore
            admin_role = UserRole.query.filter_by(name='Amministratore').first()
            if not admin_role:
                admin_role = UserRole(
                    name='Amministratore',
                    display_name='Amministratore',
                    description='Amministratore sistema con accesso completo',
                    permissions={
                        'can_manage_users': True,
                        'can_view_all_users': True,
                        'can_edit_all_users': True,
                        'can_delete_users': True,
                        'can_manage_roles': True,
                        'can_view_attendance': True,
                        'can_edit_attendance': True,
                        'can_manage_shifts': True,
                        'can_view_all_shifts': True,
                        'can_create_shifts': True,
                        'can_edit_shifts': True,
                        'can_delete_shifts': True,
                        'can_manage_holidays': True,
                        'can_view_reports': True,
                        'can_export_data': True,
                        'can_manage_sedi': True,
                        'can_view_dashboard': True,
                        'can_manage_leave_requests': True,
                        'can_approve_leave_requests': True,
                        'can_view_leave_requests': True,
                        'can_create_leave_requests': True,
                        'can_manage_overtime_requests': True,
                        'can_approve_overtime_requests': True,
                        'can_view_overtime_requests': True,
                        'can_create_overtime_requests': True,
                        'can_manage_mileage_requests': True,
                        'can_approve_mileage_requests': True,
                        'can_view_mileage_requests': True,
                        'can_create_mileage_requests': True,
                        'can_manage_internal_messages': True,
                        'can_send_internal_messages': True,
                        'can_view_internal_messages': True,
                        'can_manage_aci_tables': True,
                        'can_view_aci_tables': True
                    },
                    active=True
                )
                db.session.add(admin_role)
                db.session.flush()
            
            # Crea utente amministratore (CAMPO: active invece di is_active)
            admin_user = User(
                first_name=first_name,
                last_name=last_name,
                email=email,
                username=username,
                password_hash=generate_password_hash(password),
                active=True,  # CAMPO CORRETTO: active (non is_active)
                all_sedi=True,
                role='Amministratore'
            )
            
            db.session.add(admin_user)
            db.session.commit()
            
            print("[OK] Utente amministratore creato con successo")
            return True
            
    except Exception as e:
        print(f"[ERRORE] Creazione utente amministratore fallita: {e}")
        return False

if __name__ == "__main__":
    print("=== SCRIPT INIZIALIZZAZIONE DATABASE WORKLY ===")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Inizializza database
    if initialize_database():
        print("✓ Database inizializzato correttamente")
        
        # Chiedi se creare utente admin
        create_admin = input("Creare utente amministratore? (s/n): ").lower().strip()
        
        if create_admin in ['s', 'si', 'y', 'yes']:
            print("\\nDati utente amministratore:")
            username = input("Username: ").strip()
            email = input("Email: ").strip()
            first_name = input("Nome: ").strip()
            last_name = input("Cognome: ").strip()
            password = input("Password: ").strip()
            
            if create_admin_user(username, email, password, first_name, last_name):
                print("✓ Utente amministratore creato")
            else:
                print("✗ Errore creazione utente amministratore")
    else:
        print("✗ Errore inizializzazione database")
        sys.exit(1)
    
    print("\\n=== INIZIALIZZAZIONE COMPLETATA ===")
"""
    
    return python_script

def main():
    """Funzione principale - crea i file di inizializzazione database"""
    
    print("=== GENERAZIONE SCRIPT CREAZIONE DATABASE WORKLY ===")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. Crea script SQL per creazione schema
    sql_script = create_database_schema_script()
    sql_filename = f"workly_database_schema_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    
    with open(sql_filename, 'w', encoding='utf-8') as f:
        f.write(sql_script)
    
    print(f"✓ Script SQL creato: {sql_filename}")
    
    # 2. Crea script Python per inizializzazione
    python_script = create_python_initialization_script()
    python_filename = "initialize_database.py"
    
    with open(python_filename, 'w', encoding='utf-8') as f:
        f.write(python_script)
    
    print(f"✓ Script Python creato: {python_filename}")
    
    # 3. Crea file documentazione
    readme_content = f"""# Script Creazione Database Workly

## File generati:

### 1. {sql_filename}
Script SQL completo per creare tutte le tabelle con struttura corretta:
- 26 tabelle con tutti i campi attuali
- Vincoli di integrità referenziale
- Indici per prestazioni
- Commenti per documentazione

**Campo importante:** La tabella `user` usa il campo `active` (NON `is_active`)

### 2. {python_filename}
Script Python per inizializzazione database:
- Import corretti dai modelli attuali
- Creazione tabelle con `db.create_all()`
- Funzione per creare utente amministratore
- Gestione errori completa

## Utilizzo:

### Opzione 1: Script SQL diretto
```bash
psql -h hostname -U username -d database_name -f {sql_filename}
```

### Opzione 2: Script Python (raccomandato)
```bash
python {python_filename}
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

Generato automaticamente il {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    readme_filename = "README_DATABASE_CREATION.md"
    with open(readme_filename, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"✓ Documentazione creata: {readme_filename}")
    
    print()
    print("=== RIEPILOGO ===")
    print(f"✓ Script SQL: {sql_filename}")
    print(f"✓ Script Python: {python_filename}")
    print(f"✓ Documentazione: {readme_filename}")
    print()
    print("IMPORTANTE:")
    print("- La tabella 'user' usa il campo 'active' (NON 'is_active')")
    print("- Script compatibili con struttura database attuale")
    print("- Include tutte le 26 tabelle con campi corretti")
    print("- Pronto per installazione e distribuzione")

if __name__ == "__main__":
    main()