-- Migration: Add Channels System to CIRCLE
-- Date: November 11, 2025
-- Description: Adds Channel model and updates CircleGroup and CirclePost

-- Create channel table
CREATE TABLE IF NOT EXISTS channel (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon_class VARCHAR(100) DEFAULT 'fas fa-comments',
    icon_color VARCHAR(50) DEFAULT 'text-primary',
    active BOOLEAN DEFAULT TRUE,
    company_id INTEGER NOT NULL REFERENCES company(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_channel_name_company UNIQUE (name, company_id)
);

-- Add channel_id to circle_post
ALTER TABLE circle_post ADD COLUMN IF NOT EXISTS channel_id INTEGER REFERENCES channel(id);

-- Add index for performance
CREATE INDEX IF NOT EXISTS idx_circlepost_company_channel_type ON circle_post(company_id, channel_id, post_type);

-- Add channel_id to circle_group and make group_type nullable
ALTER TABLE circle_group ADD COLUMN IF NOT EXISTS channel_id INTEGER REFERENCES channel(id);
ALTER TABLE circle_group ALTER COLUMN group_type DROP NOT NULL;

-- Create default "Generale" channel for each existing company
INSERT INTO channel (name, description, icon_class, icon_color, active, company_id, created_at, updated_at)
SELECT 
    'Generale',
    'Canale generale per comunicazioni aziendali',
    'fas fa-comments',
    'text-primary',
    TRUE,
    id,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
FROM company
WHERE NOT EXISTS (
    SELECT 1 FROM channel WHERE channel.company_id = company.id AND channel.name = 'Generale'
);

-- Assign existing groups to "Generale" channel
UPDATE circle_group 
SET channel_id = (
    SELECT id FROM channel 
    WHERE channel.company_id = circle_group.company_id 
    AND channel.name = 'Generale'
)
WHERE channel_id IS NULL;
