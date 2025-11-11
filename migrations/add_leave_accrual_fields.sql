-- Migration: Add leave and permit accrual fields to user_hr_data table
-- Date: 2025-11-11
-- Description: Adds monthly accrual rates for vacation days and permit hours to track employee leave balances

-- Add columns for leave/permit accrual rates
ALTER TABLE user_hr_data 
ADD COLUMN IF NOT EXISTS gg_ferie_maturate_mese NUMERIC(10, 2) NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS hh_permesso_maturate_mese NUMERIC(10, 2) NOT NULL DEFAULT 0;

-- Add comments to document field usage
COMMENT ON COLUMN user_hr_data.gg_ferie_maturate_mese IS 'Giorni di ferie maturati mensilmente (es. 2.33 per 28 giorni/anno)';
COMMENT ON COLUMN user_hr_data.hh_permesso_maturate_mese IS 'Ore di permesso (ROL) maturate mensilmente (es. 7 ore/mese per 84 ore/anno)';

-- No data seeding needed - defaults to 0 for existing records
-- HR users will configure these values per employee based on contract/CCNL
