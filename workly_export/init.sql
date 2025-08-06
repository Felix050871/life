-- Workly Database Initialization Script
-- Questo script viene eseguito automaticamente alla creazione del database PostgreSQL

-- Estensioni utili
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Impostazioni per performance
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET track_activity_query_size = 2048;
ALTER SYSTEM SET pg_stat_statements.track = 'all';

-- Configurazioni per timezone (opzionale)
-- SET timezone = 'Europe/Rome';

-- Indici personalizzati per ottimizzazioni (verranno creati dopo la creazione delle tabelle)
-- Questi verranno applicati dopo il primo avvio dell'applicazione

-- Funzioni personalizzate per Workly
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Commenti per documentazione
COMMENT ON DATABASE workly IS 'Workly Workforce Management Platform Database';

-- Note: Le tabelle verranno create automaticamente da SQLAlchemy
-- al primo avvio dell'applicazione Flask