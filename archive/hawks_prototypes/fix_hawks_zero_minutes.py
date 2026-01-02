"""
Fix Hawks Schedule Table - Set FALSE for 0 Minutes Players
===========================================================
Updates schedule table: if player played 0 minutes, set them to FALSE
"""

import psycopg2

NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

def main():
    print("=" * 70)
    print("🏀 Fixing Hawks Schedule Table - 0 Minutes = FALSE")
    print("=" * 70)
    print()
    
    schema_name = "atlanta_hawks"
    
    # Connect to DB
    conn = psycopg2.connect(NEON_DSN)
    cur = conn.cursor()
    
    try:
        # Get player columns from schedule table
        cur.execute(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = '{schema_name}' 
            AND table_name = 'schedule'
            AND column_name NOT IN ('game_date', 'game_id', 'opponent', 'home_away', 
                                     'result', 'team_score', 'opponent_score', 'created_at')
        """)
        
        player_columns = [row[0] for row in cur.fetchall()]
        players = [col.replace('_', ' ').title() for col in player_columns]
        
        print(f"Found {len(players)} players\n")
        
        total_fixes = 0
        
        # For each player, check their game logs and set FALSE if 0 minutes
        for player_name, player_col in zip(players, player_columns):
            print(f"  {player_name}...", end=" ", flush=True)
            
            # Get games where player has 0 minutes in game logs
            cur.execute(f"""
                SELECT game_date
                FROM {schema_name}.player_game_logs
                WHERE player_name = %s AND min = 0
            """, (player_name,))
            
            zero_min_dates = [row[0] for row in cur.fetchall()]
            
            if len(zero_min_dates) > 0:
                fixes = 0
                # Update schedule to FALSE for those dates
                for game_date in zero_min_dates:
                    cur.execute(f"""
                        UPDATE {schema_name}.schedule
                        SET "{player_col}" = FALSE
                        WHERE game_date = %s AND "{player_col}" = TRUE
                    """, (game_date,))
                    
                    if cur.rowcount > 0:
                        fixes += 1
                        total_fixes += 1
                
                if fixes > 0:
                    print(f"✅ fixed {fixes} games")
                else:
                    print(f"✅ already correct")
            else:
                print(f"✅ no 0-min games")
        
        conn.commit()
        
        print()
        print("=" * 70)
        print(f"✅ Complete! Fixed {total_fixes} total entries")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
