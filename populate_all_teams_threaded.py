"""
Populate player season averages for all 30 teams using multithreading.
Much faster than sequential processing!
"""

import psycopg2
from nba_api.stats.endpoints import commonteamroster, playerdashboardbygeneralsplits
from nba_api.stats.static import teams
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Database connection
NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

# Current season
CURRENT_SEASON = "2025-26"

# Thread-safe printing
print_lock = threading.Lock()


def safe_print(*args, **kwargs):
    """Thread-safe print function"""
    with print_lock:
        print(*args, **kwargs)


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
        safe_print(f"❌ Error getting roster for team {team_id}: {e}")
        return None


def get_player_season_stats(player_id, season):
    """Get season averages for a player"""
    try:
        dashboard = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(
            player_id=player_id,
            season=season,
            per_mode_detailed='PerGame'
        )
        stats_df = dashboard.get_data_frames()[0]
        
        if len(stats_df) == 0:
            return None
            
        stats = stats_df.iloc[0]
        return stats
        
    except Exception as e:
        return None


def populate_team_averages(team_id, team_schema, team_name):
    """Populate season averages for one team"""
    safe_print(f"🏀 Starting: {team_name}")
    
    # Each thread gets its own database connection
    conn = psycopg2.connect(NEON_DSN)
    cursor = conn.cursor()
    
    # Get roster
    roster_df = get_team_roster(team_id, CURRENT_SEASON)
    if roster_df is None or len(roster_df) == 0:
        safe_print(f"❌ {team_name}: No roster found")
        conn.close()
        return {"team": team_name, "success": False, "players": 0}
    
    players_added = 0
    
    for idx, player in roster_df.iterrows():
        player_id = player['PLAYER_ID']
        player_name = player['PLAYER']
        
        # Get player stats
        stats = get_player_season_stats(player_id, CURRENT_SEASON)
        
        if stats is None:
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
        INSERT INTO {team_schema}.player_season_averages (
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
        
        try:
            cursor.execute(insert_query, (
                player_id, player_name, gp, min_avg, pts_avg, reb_avg, ast_avg,
                stl_avg, blk_avg, tov_avg, fg_pct, fg3_pct, ft_pct,
                fgm_avg, fga_avg, fg3m_avg, fg3a_avg, ftm_avg, fta_avg,
                oreb_avg, dreb_avg, pf_avg, plus_minus_avg
            ))
            players_added += 1
        except Exception as e:
            safe_print(f"  ❌ {team_name} - {player_name}: {e}")
        
        # Rate limiting
        time.sleep(0.6)
    
    conn.commit()
    cursor.close()
    conn.close()
    
    safe_print(f"✅ {team_name}: {players_added}/{len(roster_df)} players")
    return {"team": team_name, "success": True, "players": players_added, "total": len(roster_df)}


def main():
    print("🏀 Populating Player Season Averages (Multithreaded)")
    print(f"Season: {CURRENT_SEASON}")
    print("="*80)
    
    start_time = datetime.now()
    
    # Get all teams
    all_teams = teams.get_teams()
    
    # Use ThreadPoolExecutor for parallel processing
    # 5 threads = good balance between speed and API rate limits
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Submit all team jobs
        futures = {
            executor.submit(
                populate_team_averages,
                team['id'],
                team['full_name'].lower().replace(' ', '_'),
                team['full_name']
            ): team['full_name']
            for team in all_teams
        }
        
        # Collect results as they complete
        results = []
        for future in as_completed(futures):
            team_name = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                safe_print(f"❌ {team_name} failed: {e}")
                results.append({"team": team_name, "success": False, "players": 0})
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    successful_teams = sum(1 for r in results if r["success"])
    total_players = sum(r.get("players", 0) for r in results)
    
    print(f"Teams processed: {successful_teams}/{len(all_teams)}")
    print(f"Total players added: {total_players}")
    print(f"Time elapsed: {duration:.1f} seconds")
    print(f"Finished: {end_time}")
    
    # Show any failed teams
    failed = [r for r in results if not r["success"]]
    if failed:
        print("\n⚠️  Failed teams:")
        for r in failed:
            print(f"  - {r['team']}")


if __name__ == "__main__":
    main()
