-- Workly Database Schema Creation Script (CORRECTED)
-- Generato automaticamente il 2025-08-01 11:05:28
-- Struttura CORRETTA senza incongruenze is_active vs active

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
    permissions JSON DEFAULT '{}',
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

-- Tabella Utenti
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
-- TABELLE FERIE E PERMESSI (CORRECTED: active instead of is_active)
-- ============================================================================

-- Tabella Tipi Ferie
CREATE TABLE leave_type (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    requires_approval BOOLEAN DEFAULT true,
    active BOOLEAN DEFAULT true,
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
-- TABELLE STRAORDINARI (CORRECTED: active instead of is_active)
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
-- TABELLE NOTE SPESE (CORRECTED: active instead of is_active)
-- ============================================================================

-- Tabella Categorie Spese
CREATE TABLE expense_category (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255),
    active BOOLEAN DEFAULT true,
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
-- TABELLE FESTIVITÀ (CORRECTED: active instead of is_active)
-- ============================================================================

-- Tabella Festività
CREATE TABLE holiday (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    active BOOLEAN NOT NULL DEFAULT true,
    description VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER NOT NULL REFERENCES "user"(id),
    sede_id INTEGER REFERENCES sede(id)
);

-- ============================================================================
-- TABELLE REPERIBILITÀ (CORRECTED: active instead of is_active)
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
    active BOOLEAN DEFAULT true,
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
-- TABELLE PRESIDIO (CORRECTED: active instead of is_active)
-- ============================================================================

-- Tabella Template Presidio
CREATE TABLE presidio_coverage_template (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    description VARCHAR(200),
    active BOOLEAN DEFAULT true,
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
    active BOOLEAN DEFAULT true,
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

COMMENT ON TABLE "user" IS 'Tabella utenti - Usa campo active (non is_active)';
COMMENT ON COLUMN "user".active IS 'Campo booleano per utenti attivi';
COMMENT ON TABLE aci_table IS 'Tabella veicoli ACI per rimborsi chilometrici';
COMMENT ON TABLE mileage_request IS 'Richieste rimborso chilometrico con calcolo automatico distanze';

-- Script completato - TUTTE LE TABELLE USANO 'active' INVECE DI 'is_active'
SELECT 'Schema database Workly CORRETTO creato con successo!' as status;
