-- Migration: Rimuove collegamento channel_id da circle_group
-- I gruppi e i canali sono due entità distinte con scopi diversi

-- Rimuovi foreign key constraint
ALTER TABLE circle_group DROP CONSTRAINT IF EXISTS circle_group_channel_id_fkey;

-- Rimuovi colonna channel_id
ALTER TABLE circle_group DROP COLUMN IF EXISTS channel_id;
