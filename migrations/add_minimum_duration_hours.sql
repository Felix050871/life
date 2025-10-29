-- Migration: Add minimum_duration_hours to leave_type table
-- Date: 2025-10-29
-- Description: Adds flexible hour-based minimum duration for leave types

-- Add the column (safe to run multiple times with IF NOT EXISTS)
ALTER TABLE leave_type ADD COLUMN IF NOT EXISTS minimum_duration_hours DOUBLE PRECISION;

-- Set default values for common leave types
-- These defaults are applied once; new companies should set their own values
-- or rely on the seeding function in app.py

-- Ferie (Vacation): 8 hours (1 full day)
UPDATE leave_type 
SET minimum_duration_hours = 8.0
WHERE (code = 'FE' OR name LIKE '%Ferie%')
  AND minimum_duration_hours IS NULL;

-- Malattia (Sick Leave): 4 hours (half day)
UPDATE leave_type 
SET minimum_duration_hours = 4.0
WHERE (code = 'MAL' OR name LIKE '%Malattia%' OR name LIKE '%malattia%')
  AND minimum_duration_hours IS NULL;

-- Note: Other leave types are left as NULL (admin configurable)
-- Admins can configure these through the UI at /tenant/<slug>/leave_types
