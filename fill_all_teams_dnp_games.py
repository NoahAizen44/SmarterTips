"""
Fill Missing Games (DNP) for All Teams Player Usage Tables
===========================================================
Adds rows with 0 minutes/usage for games where players were absent (FALSE in schedule)
"""

import psycopg2
from nba_api.stats.static import teams

NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

def normalize_name(name):
    """Convert player name to table name format"""
    return name.lower().replace(' ', '_').replace("'", '').replace('.', '').replace('-', '_')

def main():
    print("=" * 70)
    print("🏀 Filling DNP Games for All NBA Teams")
    print("=" * 70)
    print()
    
    # Get all NBA teams
    all_teams = teams.get_teams()
    
    # Connect to DB
    conn = psycopg2.connect(NEON_DSN)
    cur = conn.cursor()
    
    total_dnp_added = 0
    
    for team_idx, team in enumerate(sorted(all_teams, key=lambda x: x['full_name']), 1):
        team_name = team['full_name']
        schema_name = team_name.lower().replace(' ', '_')
        
        print(f"\n[{team_idx}/30] {team_name}")
        print("-" * 70)
        
        try:
            # Get player columns from schedule table
            cur.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = '{schema_name}' 
                AND table_name = 'schedule'
                AND column_name NOT IN ('game_date', 'game_id', 'opponent', 'home_away', 
                                         'result', 'team_score', 'opponent_score', 'created_at')
                ORDER BY column_name
            """)
            
            player_columns = [row[0] for row in cur.fetchall()]
            players = [col.replace('_', ' ').title() for col in player_columns]
            
            print(f"  → {len(players)} players")
            
            team_dnp_added = 0
            
            # For each player, add missing games where they were FALSE
            for player_name, player_col in zip(players, player_columns):
                table_name = normalize_name(player_name)  # No _usage suffix
                
                # Insert rows for games where player was FALSE (absent)
                cur.execute(f"""
                    INSERT INTO {schema_name}.{table_name} (game_date, minutes, usage_percentage)
                    SELECT game_date, 0, 0
                    FROM {schema_name}.schedule
                    WHERE "{player_col}" = FALSE
                    ON CONFLICT (game_date) DO NOTHING
                """)
                
                added = cur.rowcount
                team_dnp_added += added
            
            conn.commit()
            total_dnp_added += team_dnp_added
            print(f"  ✅ Added {team_dnp_added} DNP game rows")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue
    
    cur.close()
    conn.close()
    
    print()
    print("=" * 70)
    print(f"✅ Complete! Added {total_dnp_added} total DNP game rows across all teams")
    print("=" * 70)

if __name__ == "__main__":
    main()
