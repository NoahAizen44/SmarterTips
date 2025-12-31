"""
Create Player Game Logs Tables for All NBA Teams
=================================================
Sets up player_game_logs table schema for each team
"""

import psycopg2
from nba_api.stats.static import teams

NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

def main():
    print("=" * 70)
    print("🏀 Creating Player Game Logs Tables for All NBA Teams")
    print("=" * 70)
    print()
    
    # Get all NBA teams
    all_teams = teams.get_teams()
    
    # Connect to DB
    conn = psycopg2.connect(NEON_DSN)
    cur = conn.cursor()
    
    for team_idx, team in enumerate(sorted(all_teams, key=lambda x: x['full_name']), 1):
        team_name = team['full_name']
        schema_name = team_name.lower().replace(' ', '_')
        
        print(f"[{team_idx}/30] {team_name}...", end=" ", flush=True)
        
        try:
            # Drop existing table to recreate with new schema
            cur.execute(f"DROP TABLE IF EXISTS {schema_name}.player_game_logs CASCADE")
            
            # Create player_game_logs table with all NBA API columns
            cur.execute(f"""
                CREATE TABLE {schema_name}.player_game_logs (
                    id SERIAL PRIMARY KEY,
                    player_id BIGINT,
                    player_name VARCHAR(255) NOT NULL,
                    nickname VARCHAR(255),
                    team_abbreviation VARCHAR(10),
                    game_id VARCHAR(20),
                    game_date DATE NOT NULL,
                    matchup VARCHAR(100),
                    wl VARCHAR(1),
                    min FLOAT,
                    fgm INT,
                    fga INT,
                    fg_pct FLOAT,
                    fg3m INT,
                    fg3a INT,
                    fg3_pct FLOAT,
                    ftm INT,
                    fta INT,
                    ft_pct FLOAT,
                    oreb INT,
                    dreb INT,
                    reb INT,
                    ast INT,
                    tov INT,
                    stl INT,
                    blk INT,
                    blka INT,
                    pf INT,
                    pfd INT,
                    pts INT,
                    plus_minus FLOAT,
                    nba_fantasy_pts FLOAT,
                    dd2 INT,
                    td3 INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(player_name, game_date)
                )
            """)
            
            # Create index for faster queries
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{schema_name}_player_game_logs_player_date
                ON {schema_name}.player_game_logs(player_name, game_date)
            """)
            
            conn.commit()
            print("✅")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            continue
    
    cur.close()
    conn.close()
    
    print()
    print("=" * 70)
    print("✅ All player_game_logs tables created successfully!")
    print("=" * 70)

if __name__ == "__main__":
    main()
