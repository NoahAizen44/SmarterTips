#!/usr/bin/env python3
"""Create player_game_logs table in Supabase using SQL."""

import os
from supabase import create_client, Client

# Initialize with SERVICE ROLE KEY (has admin privileges)
url = os.environ.get('SUPABASE_URL', 'https://vszmsnikixfdakwzuown.supabase.co')
service_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZzem1zbmlraXhmZGFrd3p1b3duIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTIyNTU1MSwiZXhwIjoyMDgwODAxNTUxfQ.gLuZkV9sR-qK0wH5PzZXqB5RXQEMz9F7X0-gBpd-YPk')

supabase: Client = create_client(url, service_key)

# SQL to create table
create_table_sql = """
CREATE TABLE IF NOT EXISTS player_game_logs (
  id BIGSERIAL PRIMARY KEY,
  team TEXT NOT NULL,
  player_id INTEGER NOT NULL,
  player_name TEXT NOT NULL,
  position TEXT,
  game_date TEXT NOT NULL,
  game_id TEXT NOT NULL,
  pts INTEGER DEFAULT 0,
  reb INTEGER DEFAULT 0,
  ast INTEGER DEFAULT 0,
  "3pm" INTEGER DEFAULT 0,
  "3pa" INTEGER DEFAULT 0,
  stl INTEGER DEFAULT 0,
  blk INTEGER DEFAULT 0,
  season TEXT NOT NULL,
  imported_at TIMESTAMP DEFAULT NOW(),
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_player_game_logs_team ON player_game_logs(team);
CREATE INDEX IF NOT EXISTS idx_player_game_logs_player_name ON player_game_logs(player_name);
CREATE INDEX IF NOT EXISTS idx_player_game_logs_game_id ON player_game_logs(game_id);
CREATE INDEX IF NOT EXISTS idx_player_game_logs_season ON player_game_logs(season);
"""

try:
    print("🚀 Creating player_game_logs table in Supabase...")
    result = supabase.postgrest.from_('player_game_logs').select('id', count='exact').limit(1).execute()
    print("✅ Table already exists!")
except Exception as e:
    error_msg = str(e)
    if 'does not exist' in error_msg or 'PGRST205' in error_msg or '404' in error_msg:
        print("⚠️  Table does not exist. Please create it manually:")
        print("\n1. Go to https://app.supabase.com/")
        print("2. Select your project (SmarterTips)")
        print("3. Click 'SQL Editor' on the left sidebar")
        print("4. Click 'New Query'")
        print("5. Paste this SQL and click 'Run':\n")
        print(create_table_sql)
        print("\nAfter creating the table, run import_player_game_logs.py again.")
    else:
        print(f"❌ Error: {e}")
