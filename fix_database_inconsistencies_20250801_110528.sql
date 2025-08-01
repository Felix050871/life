-- Script correzione incongruenze database Workly
-- Generato automaticamente il 2025-08-01 11:05:28

-- ============================================================================
-- CORREZIONE CAMPI is_active -> active
-- ============================================================================

-- 1. expense_category: is_active -> active
ALTER TABLE expense_category RENAME COLUMN is_active TO active;
ALTER TABLE expense_category ALTER COLUMN active SET DEFAULT true;

-- 2. holiday: is_active -> active  
ALTER TABLE holiday RENAME COLUMN is_active TO active;
ALTER TABLE holiday ALTER COLUMN active SET DEFAULT true;

-- 3. leave_type: is_active -> active
ALTER TABLE leave_type RENAME COLUMN is_active TO active;
ALTER TABLE leave_type ALTER COLUMN active SET DEFAULT true;

-- 4. presidio_coverage: is_active -> active
ALTER TABLE presidio_coverage RENAME COLUMN is_active TO active;
ALTER TABLE presidio_coverage ALTER COLUMN active SET DEFAULT true;

-- 5. presidio_coverage_template: is_active -> active
ALTER TABLE presidio_coverage_template RENAME COLUMN is_active TO active;
ALTER TABLE presidio_coverage_template ALTER COLUMN active SET DEFAULT true;

-- 6. reperibilita_coverage: is_active -> active
ALTER TABLE reperibilita_coverage RENAME COLUMN is_active TO active;
ALTER TABLE reperibilita_coverage ALTER COLUMN active SET DEFAULT true;

-- ============================================================================
-- CORREZIONE PRECISION DECIMAL
-- ============================================================================

-- Standardizza precision fringe_benefit in aci_table
ALTER TABLE aci_table ALTER COLUMN fringe_benefit_10 TYPE DECIMAL(10,4);
ALTER TABLE aci_table ALTER COLUMN fringe_benefit_25 TYPE DECIMAL(10,4);
ALTER TABLE aci_table ALTER COLUMN fringe_benefit_30 TYPE DECIMAL(10,4);
ALTER TABLE aci_table ALTER COLUMN fringe_benefit_50 TYPE DECIMAL(10,4);

-- ============================================================================
-- AGGIUNTA DEFAULT TIMESTAMP
-- ============================================================================

-- Aggiungi default CURRENT_TIMESTAMP dove mancante
ALTER TABLE aci_table ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE aci_table ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE attendance_event ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE expense_category ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE expense_report ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE expense_report ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE holiday ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE internal_message ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE internal_message ALTER COLUMN is_read SET DEFAULT false;

ALTER TABLE intervention ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE leave_request ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE leave_request ALTER COLUMN status SET DEFAULT 'pending';

ALTER TABLE leave_type ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE leave_type ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE leave_type ALTER COLUMN requires_approval SET DEFAULT true;

ALTER TABLE mileage_request ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE mileage_request ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE mileage_request ALTER COLUMN is_km_manual SET DEFAULT false;
ALTER TABLE mileage_request ALTER COLUMN status SET DEFAULT 'pending';

ALTER TABLE overtime_request ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE overtime_request ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE overtime_request ALTER COLUMN status SET DEFAULT 'pending';

ALTER TABLE overtime_type ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE overtime_type ALTER COLUMN hourly_rate_multiplier SET DEFAULT 1.0;

ALTER TABLE password_reset_token ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE password_reset_token ALTER COLUMN used SET DEFAULT false;

ALTER TABLE presidio_coverage ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE reperibilita_coverage ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE reperibilita_intervention ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE reperibilita_intervention ALTER COLUMN is_remote SET DEFAULT false;
ALTER TABLE reperibilita_intervention ALTER COLUMN priority SET DEFAULT 'medium';

ALTER TABLE reperibilita_shift ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE reperibilita_template ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE sede ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE shift ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE shift_template ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE "user" ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "user" ALTER COLUMN part_time_percentage SET DEFAULT 100.0;

ALTER TABLE user_role ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE work_schedule ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;

-- ============================================================================
-- VERIFICA CORREZIONI
-- ============================================================================

-- Controlla che tutte le tabelle ora usino 'active'
SELECT 
    table_name,
    COUNT(CASE WHEN column_name = 'active' THEN 1 END) as has_active,
    COUNT(CASE WHEN column_name = 'is_active' THEN 1 END) as has_is_active
FROM information_schema.columns
WHERE table_schema = 'public' 
    AND (column_name = 'active' OR column_name = 'is_active')
GROUP BY table_name
ORDER BY table_name;

-- Script completato
SELECT 'Incongruenze database corrette con successo!' as status;
