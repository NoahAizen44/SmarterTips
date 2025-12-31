"""
Drop All Usage Tables for All NBA Teams
========================================
Drops all individual player usage tables across all 30 teams
"""

import psycopg2
from nba_api.stats.static import teams

NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

def get_team_roster_columns(conn, schema_name):
    """Get list of player column names from team schedule table"""
    cur = conn.cursor()
    cur.execute(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = '{schema_name}' 
        AND table_name = 'schedule'
        AND column_name NOT IN ('game_date', 'game_id', 'opponent', 'home_away', 
                                 'result', 'team_score', 'opponent_score', 'created_at');
    """)
    player_columns = [row[0] for row in cur.fetchall()]
    cur.close()
    return player_columns

def main():
    print("=" * 60)
    print("🗑️  Dropping All Usage Tables for All NBA Teams")
    print("=" * 60)
    print()
    
    # Get all NBA teams
    all_teams = teams.get_teams()
    
    # Connect to DB
    conn = psycopg2.connect(NEON_DSN)
    
    total_dropped = 0
    
    for team_idx, team in enumerate(sorted(all_teams, key=lambda x: x['full_name']), 1):
        team_name = team['full_name']
        schema_name = team_name.lower().replace(' ', '_')
        
        print(f"\n[{team_idx}/30] {team_name}")
        print("-" * 60)
        
        # Get player columns
        player_columns = get_team_roster_columns(conn, schema_name)
        print(f"  → {len(player_columns)} players in roster")
        
        dropped = 0
        cur = conn.cursor()
        
        for player_col in player_columns:
            try:
                cur.execute(f"DROP TABLE IF EXISTS {schema_name}.{player_col} CASCADE;")
                dropped += 1
            except Exception as e:
                print(f"    ✗ Failed to drop {player_col}: {e}")
        
        conn.commit()
        cur.close()
        
        total_dropped += dropped
        print(f"  ✅ Dropped {dropped} tables")
    
    conn.close()
    
    print()
    print("=" * 60)
    print(f"✅ Complete! Dropped {total_dropped} total tables")
    print("=" * 60)

if __name__ == "__main__":
    main()
