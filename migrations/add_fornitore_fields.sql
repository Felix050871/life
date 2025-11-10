-- Migration: Add nome_fornitore and partita_iva_fornitore fields to UserHRData table
-- Date: 2025-11-10
-- Description: Adds fields for "Fornitore" contract type (supplier name and VAT number)

-- Add nome_fornitore field
ALTER TABLE user_hr_data 
ADD COLUMN IF NOT EXISTS nome_fornitore VARCHAR(200);

-- Add partita_iva_fornitore field
ALTER TABLE user_hr_data 
ADD COLUMN IF NOT EXISTS partita_iva_fornitore VARCHAR(20);

-- Add comments for documentation
COMMENT ON COLUMN user_hr_data.nome_fornitore IS 'Nome del fornitore (solo per tipo contratto "Fornitore")';
COMMENT ON COLUMN user_hr_data.partita_iva_fornitore IS 'Partita IVA del fornitore (solo per tipo contratto "Fornitore")';
