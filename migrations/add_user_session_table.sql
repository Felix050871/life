-- Migration: Add user_session table for session management
-- Date: 2025-11-13
-- Description: Creates user_session table to track active user sessions with inactivity timeout (30 min),
--              multi-tenant isolation, and session warning system. Supports security features like
--              audit trails (user_agent, IP), automatic expiration, and concurrent session management.

-- Create user_session table (idempotent)
CREATE TABLE IF NOT EXISTS user_session (
    -- Primary Key - UUID string (secrets.token_urlsafe(32) ~43 chars, future-proof to 96)
    session_id VARCHAR(96) PRIMARY KEY,
    
    -- Foreign Keys with CASCADE delete
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    company_id INTEGER REFERENCES company(id) ON DELETE CASCADE,
    
    -- Tenant context (cached for performance)
    tenant_slug VARCHAR(50),
    
    -- Timestamps (UTC timezone-aware)
    created_at TIMESTAMPTZ NOT NULL DEFAULT (TIMEZONE('UTC', NOW())),
    last_activity TIMESTAMPTZ NOT NULL DEFAULT (TIMEZONE('UTC', NOW())),
    expires_at TIMESTAMPTZ NOT NULL,
    terminated_at TIMESTAMPTZ,
    
    -- Session state
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Audit fields
    user_agent TEXT,
    ip_address VARCHAR(45)  -- IPv6 max length
);

-- Create indexes for performance (idempotent)

-- Index on user_id for FK constraint performance
CREATE INDEX IF NOT EXISTS ix_user_session_user_id 
ON user_session(user_id);

-- Index on company_id for FK constraint performance
CREATE INDEX IF NOT EXISTS ix_user_session_company_id 
ON user_session(company_id);

-- Index on last_activity for expiration checks
CREATE INDEX IF NOT EXISTS ix_user_session_last_activity 
ON user_session(last_activity);

-- Index on is_active for filtering active sessions
CREATE INDEX IF NOT EXISTS ix_user_session_is_active 
ON user_session(is_active);

-- Composite index for get_active_sessions() queries - lookup by user+company+active+activity
-- Used to quickly find active sessions for a specific user in a tenant
CREATE INDEX IF NOT EXISTS ix_user_session_active 
ON user_session(user_id, company_id, is_active, last_activity);

-- Index on expires_at for cleanup job performance
-- Allows fast identification of expired sessions for batch cleanup operations
CREATE INDEX IF NOT EXISTS ix_user_session_expires 
ON user_session(expires_at);

-- Migration complete
-- Summary:
--   - Created user_session table with timezone-aware timestamps
--   - Added 6 indexes for optimal query performance
--   - Configured CASCADE delete to maintain referential integrity
--   - Supports multi-tenant isolation via company_id
--   - Ready for session_manager service integration
