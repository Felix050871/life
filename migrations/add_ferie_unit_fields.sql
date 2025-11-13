-- Migration: Add ferie_unit and ferie_daily_hours fields
-- Date: 2025-11-13
-- Description: Add fields to support Hours/Days toggle for vacation accrual tracking

-- Add columns to user_hr_data table
ALTER TABLE user_hr_data
ADD COLUMN IF NOT EXISTS ferie_unit VARCHAR(10) DEFAULT 'hours' NOT NULL,
ADD COLUMN IF NOT EXISTS ferie_daily_hours NUMERIC(4, 2) DEFAULT 8 NOT NULL;

-- Update existing records to have default values (hours mode with 8h/day)
UPDATE user_hr_data 
SET ferie_unit = 'hours',
    ferie_daily_hours = 8
WHERE ferie_unit IS NULL OR ferie_daily_hours IS NULL;

-- Add columns to contract_history table for historical tracking
ALTER TABLE contract_history
ADD COLUMN IF NOT EXISTS ferie_unit VARCHAR(10) DEFAULT 'hours' NOT NULL,
ADD COLUMN IF NOT EXISTS ferie_daily_hours NUMERIC(4, 2) DEFAULT 8 NOT NULL;

-- Update existing contract_history records with defaults
UPDATE contract_history 
SET ferie_unit = 'hours',
    ferie_daily_hours = 8
WHERE ferie_unit IS NULL OR ferie_daily_hours IS NULL;

-- Add comments for documentation
COMMENT ON COLUMN user_hr_data.ferie_unit IS 'Unit of measurement for vacation accrual: hours or days';
COMMENT ON COLUMN user_hr_data.ferie_daily_hours IS 'Daily hours for converting days to hours (default: 8)';
COMMENT ON COLUMN contract_history.ferie_unit IS 'Historical snapshot of ferie_unit';
COMMENT ON COLUMN contract_history.ferie_daily_hours IS 'Historical snapshot of ferie_daily_hours';
