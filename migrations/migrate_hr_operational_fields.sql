-- ============================================================================
-- MIGRAZIONE: Spostamento campi operativi da User a UserHRData
-- ============================================================================
-- OBIETTIVO: 
--   - Aggiungere all_sedi e work_schedule_id a UserHRData
--   - Rimuovere campo obsoleto cliente da UserHRData
--
-- STRATEGIA (migrazione in fasi):
--   1. Aggiungere nuovi campi nullable
--   2. Backfill da User model (opzionale, vedi sotto)
--   3. Validare dati
--   4. Rimuovere cliente SOLO dopo conferma business (opzionale)
--
-- NOTA: Eseguire in ambiente di staging prima di produzione!
-- ============================================================================

-- ============================================================================
-- FASE 1: AGGIUNTA NUOVI CAMPI
-- ============================================================================

-- Step 1: Aggiungi campo all_sedi
ALTER TABLE user_hr_data 
ADD COLUMN IF NOT EXISTS all_sedi BOOLEAN DEFAULT FALSE NOT NULL;

-- Step 2: Aggiungi campo work_schedule_id con FK
ALTER TABLE user_hr_data 
ADD COLUMN IF NOT EXISTS work_schedule_id INTEGER;

-- Step 3: Aggiungi FK constraint per work_schedule_id
-- ON DELETE SET NULL: se l'orario viene eliminato, il campo diventa NULL
ALTER TABLE user_hr_data 
ADD CONSTRAINT fk_user_hr_data_work_schedule 
FOREIGN KEY (work_schedule_id) 
REFERENCES work_schedule(id) 
ON DELETE SET NULL;

-- Step 4: Crea indice per performance
CREATE INDEX IF NOT EXISTS idx_user_hr_data_work_schedule_id 
ON user_hr_data(work_schedule_id);

-- ============================================================================
-- FASE 2: BACKFILL DA USER MODEL (OPZIONALE)
-- ============================================================================
-- IMPORTANTE: Decommenta e esegui SOLO se vuoi copiare i dati da User a UserHRData
-- Questo è necessario se vuoi mantenere i dati esistenti degli utenti.
-- ============================================================================

-- Backfill work_schedule_id da User
-- UPDATE user_hr_data 
-- SET work_schedule_id = u.work_schedule_id
-- FROM "user" u 
-- WHERE user_hr_data.user_id = u.id 
--   AND u.work_schedule_id IS NOT NULL
--   AND user_hr_data.work_schedule_id IS NULL;

-- Backfill all_sedi da User  
-- UPDATE user_hr_data 
-- SET all_sedi = u.all_sedi
-- FROM "user" u 
-- WHERE user_hr_data.user_id = u.id 
--   AND u.all_sedi IS NOT NULL
--   AND user_hr_data.all_sedi = FALSE;

-- ============================================================================
-- FASE 3: EXPORT CLIENTE (OPZIONALE - PRIMA DI ELIMINARE)
-- ============================================================================
-- IMPORTANTE: Esegui questa query per salvare i dati della colonna cliente
-- prima di eliminarla. Salva il risultato in un file CSV per archivio.
-- ============================================================================

-- SELECT 
--     u.id as user_id,
--     u.username,
--     u.first_name,
--     u.last_name,
--     u.email,
--     u.company_id,
--     hr.matricola,
--     hr.cliente,
--     hr.created_at,
--     hr.updated_at
-- FROM user_hr_data hr
-- JOIN "user" u ON hr.user_id = u.id
-- WHERE hr.cliente IS NOT NULL AND hr.cliente != ''
-- ORDER BY u.company_id, u.last_name, u.first_name;

-- ============================================================================
-- FASE 4: RIMOZIONE CAMPO CLIENTE (OPZIONALE)
-- ============================================================================
-- ATTENZIONE: Questa operazione è IRREVERSIBILE!
-- Esegui SOLO dopo aver:
--   1. Confermato con il team che il campo cliente non è più necessario
--   2. Esportato i dati esistenti (vedi query sopra)
--   3. Validato che non ci sono dipendenze nel codice
-- ============================================================================

-- ALTER TABLE user_hr_data DROP COLUMN IF EXISTS cliente;

-- ============================================================================
-- VERIFICA POST-MIGRAZIONE
-- ============================================================================
-- Esegui queste query per verificare che la migrazione sia andata a buon fine:

-- 1. Verifica che i nuovi campi esistano
-- SELECT column_name, data_type, is_nullable, column_default
-- FROM information_schema.columns
-- WHERE table_name = 'user_hr_data'
--   AND column_name IN ('all_sedi', 'work_schedule_id', 'cliente')
-- ORDER BY column_name;

-- 2. Verifica FK constraint
-- SELECT constraint_name, constraint_type
-- FROM information_schema.table_constraints
-- WHERE table_name = 'user_hr_data'
--   AND constraint_name = 'fk_user_hr_data_work_schedule';

-- 3. Conta record con work_schedule_id popolato
-- SELECT 
--     COUNT(*) as total_hr_records,
--     COUNT(work_schedule_id) as with_work_schedule,
--     COUNT(CASE WHEN all_sedi = TRUE THEN 1 END) as with_all_sedi_access
-- FROM user_hr_data;

-- 4. Verifica allineamento multi-tenant (work_schedule e user nella stessa company)
-- SELECT COUNT(*) as mismatched_companies
-- FROM user_hr_data hr
-- JOIN "user" u ON hr.user_id = u.id
-- JOIN work_schedule ws ON hr.work_schedule_id = ws.id
-- WHERE u.company_id != ws.company_id;
-- -- Risultato atteso: 0 (nessun mismatch)

-- ============================================================================
-- ROLLBACK (in caso di problemi)
-- ============================================================================
-- Se qualcosa va storto, esegui queste query per tornare indietro:

-- DROP INDEX IF EXISTS idx_user_hr_data_work_schedule_id;
-- ALTER TABLE user_hr_data DROP CONSTRAINT IF EXISTS fk_user_hr_data_work_schedule;
-- ALTER TABLE user_hr_data DROP COLUMN IF EXISTS work_schedule_id;
-- ALTER TABLE user_hr_data DROP COLUMN IF EXISTS all_sedi;
-- -- NOTA: Non è possibile recuperare il campo cliente se è stato eliminato!

-- ============================================================================
-- NOTE IMPORTANTI
-- ============================================================================
-- 1. BACKUP: Fai sempre un backup del database prima di eseguire migrazioni
-- 2. STAGING: Testa in staging prima di applicare a produzione
-- 3. TRANSACTION: Considera di wrappare tutto in una transazione:
--    BEGIN;
--    -- ... tutte le query ...
--    COMMIT; -- oppure ROLLBACK; se ci sono problemi
-- 4. DOWNTIME: Pianifica una finestra di manutenzione se necessario
-- 5. MONITORING: Monitora le performance dopo la migrazione
-- ============================================================================
