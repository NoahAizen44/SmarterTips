"""
Create Player Usage Tables for All NBA Teams
=============================================
Creates individual usage tables for each player with game_date and usage_rate
"""

import psycopg2
from nba_api.stats.static import teams

NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

def normalize_name(name):
    """Convert player name to table name format"""
    return name.lower().replace(' ', '_').replace("'", '').replace('.', '').replace('-', '_')

def main():
    print("=" * 70)
    print("🏀 Creating Player Usage Tables for All NBA Teams")
    print("=" * 70)
    print()
    
    # Get all NBA teams
    all_teams = teams.get_teams()
    
    # Connect to DB
    conn = psycopg2.connect(NEON_DSN)
    cur = conn.cursor()
    
    total_tables_created = 0
    
    for team_idx, team in enumerate(sorted(all_teams, key=lambda x: x['full_name']), 1):
        team_name = team['full_name']
        schema_name = team_name.lower().replace(' ', '_')
        
        print(f"\n[{team_idx}/30] {team_name}")
        print("-" * 70)
        
        try:
            # Get all unique players from player_game_logs
            cur.execute(f"""
                SELECT DISTINCT player_name 
                FROM {schema_name}.player_game_logs
                ORDER BY player_name
            """)
            
            players = [row[0] for row in cur.fetchall()]
            print(f"  → {len(players)} players found")
            
            # Create usage table for each player
            for player_name in players:
                table_name = f"{normalize_name(player_name)}_usage"
                
                # Create the usage table
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {schema_name}.{table_name} (
                        id SERIAL PRIMARY KEY,
                        game_date DATE NOT NULL UNIQUE,
                        usage_rate FLOAT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Calculate and insert usage rate from game logs
                # Usage Rate = 100 * ((FGA + 0.44 * FTA + TOV) * (Team Minutes / 5)) / (Minutes * (Team FGA + 0.44 * Team FTA + Team TOV))
                # Simplified version: (FGA + 0.44*FTA + TOV) / MIN as a basic usage metric
                cur.execute(f"""
                    INSERT INTO {schema_name}.{table_name} (game_date, usage_rate)
                    SELECT 
                        game_date,
                        CASE 
                            WHEN min > 0 THEN 
                                100.0 * (fga + 0.44 * fta + tov) / min
                            ELSE 0
                        END as usage_rate
                    FROM {schema_name}.player_game_logs
                    WHERE player_name = %s
                    ON CONFLICT (game_date) DO UPDATE SET
                        usage_rate = EXCLUDED.usage_rate
                """, (player_name,))
                
                total_tables_created += 1
            
            conn.commit()
            print(f"  ✅ Created {len(players)} player usage tables")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue
    
    cur.close()
    conn.close()
    
    print()
    print("=" * 70)
    print(f"✅ Complete! Created {total_tables_created} player usage tables")
    print("=" * 70)

if __name__ == "__main__":
    main()
