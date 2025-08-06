-- Workly Database Creation Script for PostgreSQL
-- Esegui questo script per creare il database e l'utente PostgreSQL

-- Connettiti come superuser (postgres) ed esegui questi comandi:

-- 1. Crea database
CREATE DATABASE workly
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

-- 2. Crea utente dedicato
CREATE USER workly_user WITH PASSWORD 'workly_secure_password_change_me';

-- 3. Concedi privilegi
GRANT ALL PRIVILEGES ON DATABASE workly TO workly_user;

-- 4. Connettiti al database workly e concedi privilegi sullo schema
\connect workly;

-- Concedi privilegi su schema public
GRANT ALL ON SCHEMA public TO workly_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO workly_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO workly_user;

-- Concedi privilegi per tabelle future
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO workly_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO workly_user;

-- 5. Crea estensioni utili
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 6. Configura timezone
SET timezone = 'Europe/Rome';

-- 7. Ottimizzazioni performance (opzionale)
-- Queste possono essere applicate a livello database o server

-- Commenti informativi
COMMENT ON DATABASE workly IS 'Workly Workforce Management Platform Database';

-- Informazioni per la configurazione dell'applicazione:
-- DATABASE_URL=postgresql://workly_user:workly_secure_password_change_me@localhost:5432/workly

-- Note:
-- 1. Cambia la password nel comando CREATE USER prima di eseguire
-- 2. Aggiorna il DATABASE_URL con la password corretta
-- 3. Le tabelle verranno create automaticamente da Flask-SQLAlchemy