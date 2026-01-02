"""
Drop existing player_season_averages tables and recreate with correct schema.
"""

import psycopg2
from nba_api.stats.static import teams

# Database connection
NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"


def drop_and_recreate_table(cursor, team_schema):
    """Drop old table and create new one with correct schema"""
    
    # Drop existing table
    drop_query = f"DROP TABLE IF EXISTS {team_schema}.player_season_averages CASCADE;"
    cursor.execute(drop_query)
    
    # Create new table with API-matching column names
    create_table_query = f"""
    CREATE TABLE {team_schema}.player_season_averages (
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
    print(f"  ✅ Recreated {team_schema}.player_season_averages")


def main():
    print("🔄 Dropping and Recreating Player Season Averages Tables")
    print("="*80)
    
    # Get all teams
    all_teams = teams.get_teams()
    
    # Connect to database
    conn = psycopg2.connect(NEON_DSN)
    cursor = conn.cursor()
    
    tables_recreated = 0
    
    for team in sorted(all_teams, key=lambda x: x['full_name']):
        team_name = team['full_name']
        team_schema = team_name.lower().replace(' ', '_')
        
        try:
            drop_and_recreate_table(cursor, team_schema)
            tables_recreated += 1
        except Exception as e:
            print(f"  ❌ Error recreating table for {team_name}: {e}")
            continue
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("="*80)
    print(f"✅ Recreated {tables_recreated}/{len(all_teams)} tables")
    print("\nNew column names (matching NBA API):")
    print("  gp, min_avg, pts_avg, reb_avg, ast_avg, stl_avg, blk_avg, tov_avg")
    print("  fg_pct, fg3_pct, ft_pct")
    print("  fgm_avg, fga_avg, fg3m_avg, fg3a_avg, ftm_avg, fta_avg")
    print("  oreb_avg, dreb_avg, pf_avg, plus_minus_avg")


if __name__ == "__main__":
    main()
