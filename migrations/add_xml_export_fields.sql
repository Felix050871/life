-- Aggiungi campo cod_azienda_ufficiale alla tabella company
ALTER TABLE company ADD COLUMN IF NOT EXISTS cod_azienda_ufficiale VARCHAR(10);

-- Aggiungi campo cod_giustificativo alla tabella attendance_type
ALTER TABLE attendance_type ADD COLUMN IF NOT EXISTS cod_giustificativo VARCHAR(10);

-- Aggiungi campo cod_giustificativo alla tabella leave_type
ALTER TABLE leave_type ADD COLUMN IF NOT EXISTS cod_giustificativo VARCHAR(10);
