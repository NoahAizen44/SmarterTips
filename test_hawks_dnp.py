"""
Test DNP Filling for Atlanta Hawks Only
========================================
"""

import psycopg2

NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

def normalize_name(name):
    """Convert player name to table name format"""
    return name.lower().replace(' ', '_').replace("'", '').replace('.', '').replace('-', '_')

# Connect to DB
conn = psycopg2.connect(NEON_DSN)
cur = conn.cursor()

schema_name = 'atlanta_hawks'

print("Testing DNP filling for Atlanta Hawks")
print("=" * 60)

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

print(f"\n{len(players)} players found")
print()

total_added = 0

for player_name, player_col in zip(players, player_columns):
    table_name = normalize_name(player_name)  # No _usage suffix
    
    # Check current count
    cur.execute(f"SELECT COUNT(*) FROM {schema_name}.{table_name}")
    before_count = cur.fetchone()[0]
    
    # Insert rows for games where player was FALSE (absent)
    cur.execute(f"""
        INSERT INTO {schema_name}.{table_name} (game_date, minutes, usage_percentage)
        SELECT game_date, 0, 0
        FROM {schema_name}.schedule
        WHERE "{player_col}" = FALSE
        ON CONFLICT (game_date) DO NOTHING
    """)
    
    added = cur.rowcount
    total_added += added
    
    # Check after count
    cur.execute(f"SELECT COUNT(*) FROM {schema_name}.{table_name}")
    after_count = cur.fetchone()[0]
    
    print(f"{player_name:30} | Before: {before_count:2} | Added: {added:2} | After: {after_count:2}")

conn.commit()
cur.close()
conn.close()

print()
print("=" * 60)
print(f"Total DNP games added: {total_added}")
print("=" * 60)
