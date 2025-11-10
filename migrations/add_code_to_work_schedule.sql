-- ============================================================================
-- MIGRATION: Aggiunta campo "code" alla tabella work_schedule
-- Data: 10 Novembre 2025
-- Descrizione: Aggiunge un campo codice identificativo univoco per azienda
-- ============================================================================

-- IMPORTANTE: Eseguire questi comandi in sequenza sul database di produzione

-- Step 1: Aggiungere la colonna code (nullable temporaneamente)
ALTER TABLE work_schedule ADD COLUMN IF NOT EXISTS code VARCHAR(20);

-- Step 2: Popolare i codici per gli orari esistenti
-- NOTA: Modifica questi valori in base ai tuoi orari esistenti
-- Puoi verificare gli orari con: SELECT id, name, company_id FROM work_schedule;

-- Esempio per popolare automaticamente con abbreviazioni del nome
UPDATE work_schedule 
SET code = UPPER(LEFT(REPLACE(name, ' ', ''), 3))
WHERE code IS NULL;

-- Oppure popola manualmente per ogni orario:
-- UPDATE work_schedule SET code = 'STD' WHERE id = 1 AND code IS NULL;
-- UPDATE work_schedule SET code = 'TUR' WHERE id = 2 AND code IS NULL;
-- UPDATE work_schedule SET code = 'PT' WHERE id = 3 AND code IS NULL;

-- Step 3: Rendere la colonna NOT NULL (dopo aver popolato tutti i record)
ALTER TABLE work_schedule ALTER COLUMN code SET NOT NULL;

-- Step 4: Aggiungere constraint UNIQUE per company_id + code
ALTER TABLE work_schedule 
ADD CONSTRAINT _company_schedule_code_uc UNIQUE (company_id, code);

-- ============================================================================
-- VERIFICA POST-MIGRAZIONE
-- ============================================================================
-- Esegui queste query per verificare che la migrazione sia andata a buon fine:

-- 1. Verifica che tutti gli orari abbiano un codice
-- SELECT id, company_id, code, name FROM work_schedule WHERE code IS NULL;
-- (dovrebbe restituire 0 righe)

-- 2. Verifica il constraint UNIQUE
-- SELECT company_id, code, COUNT(*) 
-- FROM work_schedule 
-- GROUP BY company_id, code 
-- HAVING COUNT(*) > 1;
-- (dovrebbe restituire 0 righe - nessun duplicato)

-- 3. Mostra tutti gli orari con i loro codici
-- SELECT company_id, code, name, active FROM work_schedule ORDER BY company_id, code;
