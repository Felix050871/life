-- Migration: Enhance Commesse Fields
-- Author: System
-- Date: 2025-11-10
-- Description: Adds codice field to Commessa, renames tariffa_oraria to valore_commessa, adds tariffa_vendita to CommessaAssignment

-- ============================================================================
-- PHASE 1: Add new columns (nullable first for backfill)
-- ============================================================================

-- Add codice field to commessa (nullable initially for backfill)
ALTER TABLE commessa ADD COLUMN IF NOT EXISTS codice VARCHAR(50);

-- Add tariffa_vendita to commessa_assignment
ALTER TABLE commessa_assignment 
ADD COLUMN IF NOT EXISTS tariffa_vendita NUMERIC(10, 2);

-- ============================================================================
-- PHASE 2: Backfill data
-- ============================================================================

-- Backfill codice with deterministic values: COMM-{id padded to 6 digits}
UPDATE commessa
SET codice = 'COMM-' || LPAD(id::TEXT, 6, '0')
WHERE codice IS NULL;

-- ============================================================================
-- PHASE 3: Add constraints
-- ============================================================================

-- Make codice NOT NULL
ALTER TABLE commessa ALTER COLUMN codice SET NOT NULL;

-- Add unique constraint on (codice, company_id)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = '_codice_company_uc'
    ) THEN
        ALTER TABLE commessa 
        ADD CONSTRAINT _codice_company_uc UNIQUE (codice, company_id);
    END IF;
END $$;

-- Add index on codice for performance
CREATE INDEX IF NOT EXISTS idx_commessa_codice ON commessa(codice);

-- ============================================================================
-- PHASE 4: Rename tariffa_oraria to valore_commessa
-- ============================================================================

-- Rename the column
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'commessa' 
        AND column_name = 'tariffa_oraria'
    ) THEN
        ALTER TABLE commessa RENAME COLUMN tariffa_oraria TO valore_commessa;
    END IF;
END $$;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify codice is set for all records
DO $$
DECLARE
    null_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO null_count FROM commessa WHERE codice IS NULL;
    IF null_count > 0 THEN
        RAISE EXCEPTION 'Migration failed: % commessa records still have NULL codice', null_count;
    END IF;
    RAISE NOTICE 'Migration successful: All commessa records have valid codice';
END $$;

-- Report summary
DO $$
DECLARE
    total_commesse INTEGER;
    total_assignments INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_commesse FROM commessa;
    SELECT COUNT(*) INTO total_assignments FROM commessa_assignment;
    
    RAISE NOTICE '=== Migration Summary ===';
    RAISE NOTICE 'Total commesse processed: %', total_commesse;
    RAISE NOTICE 'Total commessa_assignments: %', total_assignments;
    RAISE NOTICE 'Codice field: Added and backfilled';
    RAISE NOTICE 'Valore_commessa field: Renamed from tariffa_oraria';
    RAISE NOTICE 'Tariffa_vendita field: Added to assignments';
END $$;
