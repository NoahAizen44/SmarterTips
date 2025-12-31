"""
Check and Drop ACTUAL Usage Tables
===================================
Checks which usage tables actually exist before dropping them
"""

import psycopg2
from nba_api.stats.static import teams

NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

def get_all_tables_in_schema(conn, schema_name):
    """Get all tables in a schema"""
    cur = conn.cursor()
    cur.execute(f"""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = '{schema_name}'
        AND table_type = 'BASE TABLE';
    """)
    tables = [row[0] for row in cur.fetchall()]
    cur.close()
    return tables

def main():
    print("=" * 60)
    print("🔍 Checking and Dropping ACTUAL Usage Tables")
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
        
        # Get ALL tables in schema
        all_tables = get_all_tables_in_schema(conn, schema_name)
        
        # Filter out the non-player tables
        excluded = ['schedule', 'player_game_logs']
        usage_tables = [t for t in all_tables if t not in excluded]
        
        if not usage_tables:
            continue  # Skip teams with no usage tables
        
        print(f"\n[{team_idx}/30] {team_name}")
        print("-" * 60)
        print(f"  → Found {len(usage_tables)} usage tables")
        
        dropped = 0
        cur = conn.cursor()
        
        for table_name in usage_tables:
            try:
                cur.execute(f"DROP TABLE {schema_name}.{table_name} CASCADE;")
                dropped += 1
                print(f"    ✓ Dropped: {table_name}")
            except Exception as e:
                print(f"    ✗ Failed to drop {table_name}: {e}")
        
        conn.commit()
        cur.close()
        
        total_dropped += dropped
    
    conn.close()
    
    print()
    print("=" * 60)
    print(f"✅ Complete! Actually dropped {total_dropped} tables")
    print("=" * 60)

if __name__ == "__main__":
    main()
