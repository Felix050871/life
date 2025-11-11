-- Migration: Aggiungi campi per blocco timesheet e sistema di reminder
-- Data: 2025-11-11
-- Descrizione: Aggiunge campi a monthly_timesheet per gestire:
--   1. Sistema di reminder progressivi (giorno 1, 3, 6 dopo fine mese)
--   2. Blocco compilazione dopo 7gg dal mese successivo
--   3. Sblocco temporaneo su richiesta approvata

-- Aggiungi campi per tracking reminder a monthly_timesheet
ALTER TABLE monthly_timesheet
ADD COLUMN IF NOT EXISTS reminder_day1_sent_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS reminder_day3_sent_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS reminder_day6_sent_at TIMESTAMP;

-- Aggiungi campi per sblocco temporaneo a monthly_timesheet
ALTER TABLE monthly_timesheet
ADD COLUMN IF NOT EXISTS is_unlocked BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS unlocked_until TIMESTAMP,
ADD COLUMN IF NOT EXISTS unlocked_by INTEGER REFERENCES "user"(id);

-- Crea tabella per richieste di sblocco compilazione
CREATE TABLE IF NOT EXISTS timesheet_unlock_request (
    id SERIAL PRIMARY KEY,
    timesheet_id INTEGER NOT NULL REFERENCES monthly_timesheet(id) ON DELETE CASCADE,
    requested_by INTEGER NOT NULL REFERENCES "user"(id),
    requested_at TIMESTAMP NOT NULL DEFAULT NOW(),
    reason TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Pending',
    reviewed_by INTEGER REFERENCES "user"(id),
    reviewed_at TIMESTAMP,
    review_notes TEXT,
    company_id INTEGER REFERENCES company(id),
    
    -- Indici per performance
    CONSTRAINT chk_unlock_request_status CHECK (status IN ('Pending', 'Approved', 'Rejected'))
);

-- Crea indici per migliorare le performance delle query
CREATE INDEX IF NOT EXISTS idx_timesheet_unlock_request_timesheet 
    ON timesheet_unlock_request(timesheet_id);
CREATE INDEX IF NOT EXISTS idx_timesheet_unlock_request_status 
    ON timesheet_unlock_request(status);
CREATE INDEX IF NOT EXISTS idx_timesheet_unlock_request_company 
    ON timesheet_unlock_request(company_id);
CREATE INDEX IF NOT EXISTS idx_monthly_timesheet_consolidated 
    ON monthly_timesheet(is_consolidated) WHERE is_consolidated = FALSE;
CREATE INDEX IF NOT EXISTS idx_monthly_timesheet_year_month 
    ON monthly_timesheet(year, month);

-- Commenta i campi aggiunti
COMMENT ON COLUMN monthly_timesheet.reminder_day1_sent_at IS 'Timestamp invio primo reminder (giorno 1 dopo fine mese)';
COMMENT ON COLUMN monthly_timesheet.reminder_day3_sent_at IS 'Timestamp invio secondo reminder (giorno 3 dopo fine mese)';
COMMENT ON COLUMN monthly_timesheet.reminder_day6_sent_at IS 'Timestamp invio terzo reminder urgente (giorno 6 prima del blocco)';
COMMENT ON COLUMN monthly_timesheet.is_unlocked IS 'Flag sblocco temporaneo per compilazione oltre deadline';
COMMENT ON COLUMN monthly_timesheet.unlocked_until IS 'Data/ora fine validità sblocco temporaneo';
COMMENT ON COLUMN monthly_timesheet.unlocked_by IS 'Utente che ha approvato lo sblocco';

COMMENT ON TABLE timesheet_unlock_request IS 'Richieste di sblocco compilazione timesheet oltre deadline (7gg dal mese successivo)';
