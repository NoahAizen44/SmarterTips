"""
Create player_season_averages tables for all 30 NBA teams.
This just creates the empty table structure - no data yet.
"""

import psycopg2
from nba_api.stats.static import teams

# Database connection
NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"


def create_season_averages_table(cursor, team_schema):
    """Create player_season_averages table in team schema"""
    
    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS {team_schema}.player_season_averages (
        player_id BIGINT PRIMARY KEY,
        player_name VARCHAR(100) NOT NULL,
        gp INTEGER,
        min_avg DECIMAL(5,2),
        pts_avg DECIMAL(5,2),
        reb_avg DECIMAL(5,2),
        ast_avg DECIMAL(5,2),
        stl_avg DECIMAL(5,2),
        blk_avg DECIMAL(5,2),
        tov_avg DECIMAL(5,2),
        fg_pct DECIMAL(5,3),
        fg3_pct DECIMAL(5,3),
        ft_pct DECIMAL(5,3),
        fgm_avg DECIMAL(5,2),
        fga_avg DECIMAL(5,2),
        fg3m_avg DECIMAL(5,2),
        fg3a_avg DECIMAL(5,2),
        ftm_avg DECIMAL(5,2),
        fta_avg DECIMAL(5,2),
        oreb_avg DECIMAL(5,2),
        dreb_avg DECIMAL(5,2),
        pf_avg DECIMAL(5,2),
        plus_minus_avg DECIMAL(5,2),
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    cursor.execute(create_table_query)
    print(f"  ✅ {team_schema}.player_season_averages")


def main():
    print("🏀 Creating Player Season Averages Tables")
    print("="*80)
    
    # Get all teams
    all_teams = teams.get_teams()
    
    # Connect to database
    conn = psycopg2.connect(NEON_DSN)
    cursor = conn.cursor()
    
    tables_created = 0
    
    for team in sorted(all_teams, key=lambda x: x['full_name']):
        team_name = team['full_name']
        team_schema = team_name.lower().replace(' ', '_')
        
        try:
            create_season_averages_table(cursor, team_schema)
            tables_created += 1
        except Exception as e:
            print(f"  ❌ Error creating table for {team_name}: {e}")
            continue
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("="*80)
    print(f"✅ Created {tables_created}/{len(all_teams)} tables")
    print("\nTable structure:")
    print("  - player_id (PRIMARY KEY)")
    print("  - player_name")
    print("  - gp (games played)")
    print("  - min_avg, pts_avg, reb_avg, ast_avg")
    print("  - stl_avg, blk_avg, tov_avg")
    print("  - fg_pct, fg3_pct, ft_pct")
    print("  - fgm_avg, fga_avg, fg3m_avg, fg3a_avg, ftm_avg, fta_avg")
    print("  - oreb_avg, dreb_avg, pf_avg")
    print("  - plus_minus_avg")
    print("  - updated_at")
    print("\nNext step: Run populate_player_season_averages.py to fill with data")


if __name__ == "__main__":
    main()
