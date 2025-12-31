"""
Drop Old Usage Tables (with _usage suffix)
==========================================
Removes old usage tables that have _usage suffix across all teams
"""

import psycopg2
from nba_api.stats.static import teams

NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

def main():
    print("=" * 60)
    print("🗑️  Dropping Old Usage Tables (with _usage suffix)")
    print("=" * 60)
    print()
    
    # Get all NBA teams
    all_teams = teams.get_teams()
    
    # Connect to DB
    conn = psycopg2.connect(NEON_DSN)
    cur = conn.cursor()
    
    total_dropped = 0
    
    # Only process Atlanta Hawks
    for team_idx, team in enumerate(sorted(all_teams, key=lambda x: x['full_name']), 1):
        team_name = team['full_name']
        
        # Skip all teams except Atlanta Hawks
        if team_name != "Atlanta Hawks":
            continue
            
        schema_name = team_name.lower().replace(' ', '_')
        
        print(f"\n[{team_idx}/30] {team_name}")
        print("-" * 60)
        
        # Get all tables in schema that end with _usage
        cur.execute(f"""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = '{schema_name}'
            AND table_type = 'BASE TABLE'
            AND table_name LIKE '%_usage'
            ORDER BY table_name
        """)
        
        usage_tables = [row[0] for row in cur.fetchall()]
        
        if not usage_tables:
            print(f"  → No old _usage tables found")
            continue
        
        print(f"  → Found {len(usage_tables)} old _usage tables")
        
        dropped = 0
        for table_name in usage_tables:
            try:
                cur.execute(f"DROP TABLE {schema_name}.{table_name} CASCADE;")
                dropped += 1
                print(f"    ✓ Dropped: {table_name}")
            except Exception as e:
                print(f"    ✗ Failed to drop {table_name}: {e}")
        
        conn.commit()
        total_dropped += dropped
        print(f"  ✅ Dropped {dropped} tables")
    
    cur.close()
    conn.close()
    
    print()
    print("=" * 60)
    print(f"✅ Complete! Dropped {total_dropped} total old _usage tables")
    print("=" * 60)

if __name__ == "__main__":
    main()
