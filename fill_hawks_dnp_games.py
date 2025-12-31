"""
Fill Missing Games (DNP) for Player Usage Tables - Hawks Only
==============================================================
Adds rows with 0 minutes/usage for games where players were absent (FALSE in schedule)
"""

import psycopg2

NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

def normalize_name(name):
    """Convert player name to table name format"""
    return name.lower().replace(' ', '_').replace("'", '').replace('.', '').replace('-', '_')

def main():
    print("=" * 70)
    print("🏀 Filling DNP Games for Hawks Player Usage Tables")
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
            ORDER BY column_name
        """)
        
        player_columns = [row[0] for row in cur.fetchall()]
        players = [col.replace('_', ' ').title() for col in player_columns]
        
        print(f"Found {len(players)} players\n")
        
        total_added = 0
        
        # For each player, add missing games where they were FALSE
        for player_name, player_col in zip(players, player_columns):
            table_name = f"{normalize_name(player_name)}_usage"
            
            print(f"  {player_name}...", end=" ", flush=True)
            
            # Insert rows for games where player was FALSE (absent)
            cur.execute(f"""
                INSERT INTO {schema_name}.{table_name} (game_date, minutes, usage_percentage)
                SELECT game_date, 0, 0
                FROM {schema_name}.schedule
                WHERE "{player_col}" = FALSE
                ON CONFLICT (game_date) DO NOTHING
                RETURNING id
            """)
            
            added = cur.rowcount
            total_added += added
            
            if added > 0:
                print(f"✅ added {added} DNP games")
            else:
                print(f"✅ already complete")
        
        conn.commit()
        
        print()
        print("=" * 70)
        print(f"✅ Complete! Added {total_added} total DNP game rows")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
