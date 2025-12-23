-- Add missing stat columns to player_game_logs table
-- These columns are available from the stats.nba.com API

ALTER TABLE player_game_logs
ADD COLUMN IF NOT EXISTS gp INT DEFAULT 1,              -- Games Played
ADD COLUMN IF NOT EXISTS ftm INT DEFAULT 0,             -- Free Throws Made
ADD COLUMN IF NOT EXISTS fta INT DEFAULT 0,             -- Free Throws Attempted
ADD COLUMN IF NOT EXISTS fga INT DEFAULT 0,             -- Field Goals Attempted
ADD COLUMN IF NOT EXISTS fgm INT DEFAULT 0,             -- Field Goals Made
ADD COLUMN IF NOT EXISTS min INT DEFAULT 0,             -- Minutes Played
ADD COLUMN IF NOT EXISTS tov INT DEFAULT 0,             -- Turnovers
ADD COLUMN IF NOT EXISTS pf INT DEFAULT 0,              -- Personal Fouls
ADD COLUMN IF NOT EXISTS stl INT DEFAULT 0,             -- Steals
ADD COLUMN IF NOT EXISTS blk INT DEFAULT 0,             -- Blocks
ADD COLUMN IF NOT EXISTS fg_pct FLOAT DEFAULT 0,        -- Field Goal Percentage
ADD COLUMN IF NOT EXISTS fg3_pct FLOAT DEFAULT 0,       -- 3-Point Percentage
ADD COLUMN IF NOT EXISTS ft_pct FLOAT DEFAULT 0;        -- Free Throw Percentage

-- Update the updated_at timestamp
UPDATE player_game_logs SET updated_at = NOW() WHERE updated_at IS NULL;
