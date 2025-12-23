-- Add missing stat columns to player_game_logs table
-- These columns are available from the stats.nba.com API

ALTER TABLE player_game_logs
ADD COLUMN IF NOT EXISTS gp INT DEFAULT 1,              -- Games Played
ADD COLUMN IF NOT EXISTS fga INT DEFAULT 0,             -- Field Goals Attempted
ADD COLUMN IF NOT EXISTS fta INT DEFAULT 0,             -- Free Throws Attempted
ADD COLUMN IF NOT EXISTS tov INT DEFAULT 0,             -- Turnovers
ADD COLUMN IF NOT EXISTS pf INT DEFAULT 0;              -- Personal Fouls

-- Update the updated_at timestamp
UPDATE player_game_logs SET updated_at = NOW() WHERE updated_at IS NULL;
