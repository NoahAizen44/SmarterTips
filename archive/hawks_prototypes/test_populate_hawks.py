"""
Test populate script - Atlanta Hawks only
"""

import psycopg2
from nba_api.stats.endpoints import commonteamroster, playerdashboardbygeneralsplits
import time
from datetime import datetime

# Database connection
NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

# Current season
CURRENT_SEASON = "2025-26"

# Atlanta Hawks
TEAM_ID = 1610612737
TEAM_NAME = "Atlanta Hawks"
TEAM_SCHEMA = "atlanta_hawks"


def get_team_roster(team_id, season):
    """Get current roster for a team"""
    try:
        roster = commonteamroster.CommonTeamRoster(
            team_id=team_id,
            season=season
        )
        roster_df = roster.get_data_frames()[0]
        return roster_df
    except Exception as e:
        print(f"❌ Error getting roster: {e}")
        return None


def get_player_season_stats(player_id, season):
    """Get season averages for a player"""
    try:
        dashboard = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(
            player_id=player_id,
            season=season,
            per_mode_detailed='PerGame'  # This gives us averages
        )
        stats_df = dashboard.get_data_frames()[0]
        
        if len(stats_df) == 0:
            return None
            
        # Get overall season stats (first row)
        stats = stats_df.iloc[0]
        return stats
        
    except Exception as e:
        print(f"  ⚠️  Could not get stats for player {player_id}: {e}")
        return None


def main():
    print(f"🏀 Testing Population: {TEAM_NAME}")
    print(f"Season: {CURRENT_SEASON}")
    print("="*80)
    
    # Connect to database
    conn = psycopg2.connect(NEON_DSN)
    cursor = conn.cursor()
    
    # Get roster
    print("Fetching roster...")
    roster_df = get_team_roster(TEAM_ID, CURRENT_SEASON)
    
    if roster_df is None or len(roster_df) == 0:
        print("❌ No roster found")
        return
    
    print(f"✅ Found {len(roster_df)} players on roster\n")
    
    players_added = 0
    
    for idx, player in roster_df.iterrows():
        player_id = player['PLAYER_ID']
        player_name = player['PLAYER']
        
        print(f"[{idx+1}/{len(roster_df)}] {player_name}...", end=" ")
        
        # Get player stats
        stats = get_player_season_stats(player_id, CURRENT_SEASON)
        
        if stats is None:
            print("No stats available")
            time.sleep(0.6)
            continue
        
        # Extract stats matching API column names
        gp = int(stats.get('GP', 0))
        min_avg = float(stats.get('MIN', 0))
        pts_avg = float(stats.get('PTS', 0))
        reb_avg = float(stats.get('REB', 0))
        ast_avg = float(stats.get('AST', 0))
        stl_avg = float(stats.get('STL', 0))
        blk_avg = float(stats.get('BLK', 0))
        tov_avg = float(stats.get('TOV', 0))
        fg_pct = float(stats.get('FG_PCT', 0))
        fg3_pct = float(stats.get('FG3_PCT', 0)) if stats.get('FG3_PCT') else None
        ft_pct = float(stats.get('FT_PCT', 0)) if stats.get('FT_PCT') else None
        fgm_avg = float(stats.get('FGM', 0))
        fga_avg = float(stats.get('FGA', 0))
        fg3m_avg = float(stats.get('FG3M', 0))
        fg3a_avg = float(stats.get('FG3A', 0))
        ftm_avg = float(stats.get('FTM', 0))
        fta_avg = float(stats.get('FTA', 0))
        oreb_avg = float(stats.get('OREB', 0))
        dreb_avg = float(stats.get('DREB', 0))
        pf_avg = float(stats.get('PF', 0))
        plus_minus_avg = float(stats.get('PLUS_MINUS', 0))
        
        # Insert into database
        insert_query = f"""
        INSERT INTO {TEAM_SCHEMA}.player_season_averages (
            player_id, player_name, gp, min_avg, pts_avg, reb_avg, ast_avg,
            stl_avg, blk_avg, tov_avg, fg_pct, fg3_pct, ft_pct,
            fgm_avg, fga_avg, fg3m_avg, fg3a_avg, ftm_avg, fta_avg,
            oreb_avg, dreb_avg, pf_avg, plus_minus_avg, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, CURRENT_TIMESTAMP
        )
        ON CONFLICT (player_id) 
        DO UPDATE SET
            gp = EXCLUDED.gp,
            min_avg = EXCLUDED.min_avg,
            pts_avg = EXCLUDED.pts_avg,
            reb_avg = EXCLUDED.reb_avg,
            ast_avg = EXCLUDED.ast_avg,
            stl_avg = EXCLUDED.stl_avg,
            blk_avg = EXCLUDED.blk_avg,
            tov_avg = EXCLUDED.tov_avg,
            fg_pct = EXCLUDED.fg_pct,
            fg3_pct = EXCLUDED.fg3_pct,
            ft_pct = EXCLUDED.ft_pct,
            fgm_avg = EXCLUDED.fgm_avg,
            fga_avg = EXCLUDED.fga_avg,
            fg3m_avg = EXCLUDED.fg3m_avg,
            fg3a_avg = EXCLUDED.fg3a_avg,
            ftm_avg = EXCLUDED.ftm_avg,
            fta_avg = EXCLUDED.fta_avg,
            oreb_avg = EXCLUDED.oreb_avg,
            dreb_avg = EXCLUDED.dreb_avg,
            pf_avg = EXCLUDED.pf_avg,
            plus_minus_avg = EXCLUDED.plus_minus_avg,
            updated_at = CURRENT_TIMESTAMP;
        """
        
        cursor.execute(insert_query, (
            player_id, player_name, gp, min_avg, pts_avg, reb_avg, ast_avg,
            stl_avg, blk_avg, tov_avg, fg_pct, fg3_pct, ft_pct,
            fgm_avg, fga_avg, fg3m_avg, fg3a_avg, ftm_avg, fta_avg,
            oreb_avg, dreb_avg, pf_avg, plus_minus_avg
        ))
        
        print(f"✅ GP:{gp}, {min_avg:.1f} MPG, {pts_avg:.1f} PPG, {reb_avg:.1f} RPG, {ast_avg:.1f} APG")
        players_added += 1
        
        # Rate limiting
        time.sleep(0.6)
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("\n" + "="*80)
    print(f"✅ {TEAM_NAME}: Added {players_added}/{len(roster_df)} players")
    print(f"Finished: {datetime.now()}")


if __name__ == "__main__":
    main()
