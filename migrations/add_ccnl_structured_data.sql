-- Migration: Add CCNL Structured Data Models
-- Date: 2025-11-13
-- Description: Creates three-tier CCNL hierarchy (Contract → Qualification → Level)
--              and extends user_hr_data with FK references while preserving legacy string fields

-- =============================================================================
-- Create CCNLContract table
-- =============================================================================
CREATE TABLE IF NOT EXISTS ccnl_contract (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(200) NOT NULL,
    descrizione TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    company_id INTEGER NOT NULL REFERENCES company(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by_id INTEGER REFERENCES "user"(id),
    CONSTRAINT _ccnl_nome_company_uc UNIQUE (nome, company_id)
);

CREATE INDEX IF NOT EXISTS idx_ccnl_company ON ccnl_contract(company_id);

-- =============================================================================
-- Create CCNLQualification table
-- =============================================================================
CREATE TABLE IF NOT EXISTS ccnl_qualification (
    id SERIAL PRIMARY KEY,
    ccnl_id INTEGER NOT NULL REFERENCES ccnl_contract(id) ON DELETE CASCADE,
    nome VARCHAR(200) NOT NULL,
    descrizione TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    company_id INTEGER NOT NULL REFERENCES company(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT _qualification_nome_ccnl_uc UNIQUE (nome, ccnl_id)
);

CREATE INDEX IF NOT EXISTS idx_qualification_ccnl ON ccnl_qualification(ccnl_id);
CREATE INDEX IF NOT EXISTS idx_qualification_company ON ccnl_qualification(company_id);

-- =============================================================================
-- Create CCNLLevel table
-- =============================================================================
CREATE TABLE IF NOT EXISTS ccnl_level (
    id SERIAL PRIMARY KEY,
    qualification_id INTEGER NOT NULL REFERENCES ccnl_qualification(id) ON DELETE CASCADE,
    codice VARCHAR(50) NOT NULL,
    descrizione TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    company_id INTEGER NOT NULL REFERENCES company(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT _level_codice_qualification_uc UNIQUE (codice, qualification_id)
);

CREATE INDEX IF NOT EXISTS idx_level_qualification ON ccnl_level(qualification_id);
CREATE INDEX IF NOT EXISTS idx_level_company ON ccnl_level(company_id);

-- =============================================================================
-- Add FK columns to user_hr_data
-- =============================================================================
-- Note: Legacy string columns (ccnl, qualifica, ccnl_level) are preserved for backward compatibility
-- The new FK columns are nullable to support gradual migration

DO $$
BEGIN
    -- Add ccnl_contract_id FK
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_hr_data' AND column_name = 'ccnl_contract_id'
    ) THEN
        ALTER TABLE user_hr_data 
        ADD COLUMN ccnl_contract_id INTEGER REFERENCES ccnl_contract(id) ON DELETE SET NULL;
        CREATE INDEX IF NOT EXISTS idx_hr_ccnl_contract ON user_hr_data(ccnl_contract_id);
    END IF;

    -- Add ccnl_qualification_id FK
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_hr_data' AND column_name = 'ccnl_qualification_id'
    ) THEN
        ALTER TABLE user_hr_data 
        ADD COLUMN ccnl_qualification_id INTEGER REFERENCES ccnl_qualification(id) ON DELETE SET NULL;
        CREATE INDEX IF NOT EXISTS idx_hr_ccnl_qualification ON user_hr_data(ccnl_qualification_id);
    END IF;

    -- Add ccnl_level_id FK
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_hr_data' AND column_name = 'ccnl_level_id'
    ) THEN
        ALTER TABLE user_hr_data 
        ADD COLUMN ccnl_level_id INTEGER REFERENCES ccnl_level(id) ON DELETE SET NULL;
        CREATE INDEX IF NOT EXISTS idx_hr_ccnl_level ON user_hr_data(ccnl_level_id);
    END IF;
END $$;

-- =============================================================================
-- Verification Queries (for manual post-migration check)
-- =============================================================================
-- Uncomment to run after migration:
-- SELECT COUNT(*) as ccnl_contracts FROM ccnl_contract;
-- SELECT COUNT(*) as ccnl_qualifications FROM ccnl_qualification;
-- SELECT COUNT(*) as ccnl_levels FROM ccnl_level;
-- SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'user_hr_data' AND column_name LIKE 'ccnl%';
