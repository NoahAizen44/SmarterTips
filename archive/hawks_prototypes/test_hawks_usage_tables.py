"""
Test Player Usage Tables - Hawks Only
======================================
Tests creating usage tables for Atlanta Hawks players
"""

import psycopg2

NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

def normalize_name(name):
    """Convert player name to table name format"""
    return name.lower().replace(' ', '_').replace("'", '').replace('.', '').replace('-', '_')

def main():
    print("=" * 70)
    print("🏀 Testing Player Usage Tables - Atlanta Hawks")
    print("=" * 70)
    print()
    
    schema_name = "atlanta_hawks"
    
    # Connect to DB
    conn = psycopg2.connect(NEON_DSN)
    cur = conn.cursor()
    
    try:
        # Get all unique players
        cur.execute(f"""
            SELECT DISTINCT player_name 
            FROM {schema_name}.player_game_logs
            ORDER BY player_name
        """)
        
        players = [row[0] for row in cur.fetchall()]
        print(f"Found {len(players)} players:\n")
        
        # Create usage table for each player
        for idx, player_name in enumerate(players, 1):
            table_name = f"{normalize_name(player_name)}_usage"
            
            print(f"[{idx}/{len(players)}] {player_name}")
            print(f"  → Table: {table_name}")
            
            # Drop if exists for clean test
            cur.execute(f"DROP TABLE IF EXISTS {schema_name}.{table_name} CASCADE")
            
            # Create the usage table
            cur.execute(f"""
                CREATE TABLE {schema_name}.{table_name} (
                    id SERIAL PRIMARY KEY,
                    game_date DATE NOT NULL UNIQUE,
                    usage_rate FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Calculate and insert usage rate
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
            """, (player_name,))
            
            # Show sample data
            cur.execute(f"""
                SELECT game_date, usage_rate 
                FROM {schema_name}.{table_name}
                ORDER BY game_date DESC
                LIMIT 3
            """)
            
            rows = cur.fetchall()
            if rows:
                print(f"  → {len(rows)} games (sample):")
                for game_date, usage in rows[:3]:
                    print(f"     {game_date}: {usage:.2f}%")
            print()
        
        conn.commit()
        print("=" * 70)
        print("✅ Test complete!")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
