"""
Create Usage Tables for All NBA Teams
======================================
Creates individual usage tables for each player in each team's roster
Tables structure: game_date, minutes, usage_percentage
Does NOT fill data - just creates empty tables
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

def table_exists(conn, schema_name, table_name):
    """Check if a table already exists"""
    cur = conn.cursor()
    cur.execute(f"""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = '{schema_name}' 
            AND table_name = '{table_name}'
        );
    """)
    exists = cur.fetchone()[0]
    cur.close()
    return exists

def create_usage_table(conn, schema_name, player_name):
    """Create usage table for a single player"""
    cur = conn.cursor()
    
    # Create table
    cur.execute(f"""
        CREATE TABLE {schema_name}.{player_name} (
            game_date DATE PRIMARY KEY,
            minutes NUMERIC(5, 2),
            usage_percentage NUMERIC(5, 2)
        );
    """)
    
    conn.commit()
    cur.close()

def main():
    print("=" * 60)
    print("📊 Creating Usage Tables for All NBA Teams")
    print("=" * 60)
    print()
    
    # Get all NBA teams
    all_teams = teams.get_teams()
    
    # Connect to DB
    conn = psycopg2.connect(NEON_DSN)
    
    total_tables_created = 0
    total_tables_skipped = 0
    
    for team_idx, team in enumerate(sorted(all_teams, key=lambda x: x['full_name']), 1):
        team_name = team['full_name']
        schema_name = team_name.lower().replace(' ', '_')
        
        print(f"\n[{team_idx}/30] {team_name}")
        print("-" * 60)
        
        # Get player columns
        player_columns = get_team_roster_columns(conn, schema_name)
        print(f"  → {len(player_columns)} players in roster")
        
        tables_created = 0
        tables_skipped = 0
        
        for player_col in player_columns:
            # Check if table already exists
            if table_exists(conn, schema_name, player_col):
                tables_skipped += 1
                continue
            
            # Create the table
            try:
                create_usage_table(conn, schema_name, player_col)
                tables_created += 1
                print(f"    ✓ Created table: {player_col}")
            except Exception as e:
                print(f"    ✗ Failed to create {player_col}: {e}")
        
        total_tables_created += tables_created
        total_tables_skipped += tables_skipped
        
        if tables_skipped > 0:
            print(f"  → Created {tables_created} new tables, {tables_skipped} already existed")
        else:
            print(f"  ✅ Created {tables_created} tables")
    
    conn.close()
    
    print()
    print("=" * 60)
    print(f"✅ Complete!")
    print(f"   Created: {total_tables_created} tables")
    if total_tables_skipped > 0:
        print(f"   Skipped: {total_tables_skipped} tables (already existed)")
    print("=" * 60)

if __name__ == "__main__":
    main()
