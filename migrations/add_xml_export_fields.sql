-- Aggiungi campo cod_azienda_ufficiale alla tabella company
ALTER TABLE company ADD COLUMN IF NOT EXISTS cod_azienda_ufficiale VARCHAR(10);

-- Aggiungi campo cod_giustificativo alla tabella attendance_type
ALTER TABLE attendance_type ADD COLUMN IF NOT EXISTS cod_giustificativo VARCHAR(10);

-- Aggiungi campo cod_giustificativo alla tabella leave_type
ALTER TABLE leave_type ADD COLUMN IF NOT EXISTS cod_giustificativo VARCHAR(10);

-- Aggiungi campo matricola alla tabella user (sincronizzato da UserHRData.cod_si_number)
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS matricola VARCHAR(7);

-- Sincronizza matricola esistenti da UserHRData
UPDATE "user" 
SET matricola = LPAD(CAST(hr.cod_si_number AS TEXT), 7, '0')
FROM user_hr_data hr
WHERE "user".id = hr.user_id 
  AND hr.cod_si_number IS NOT NULL;
