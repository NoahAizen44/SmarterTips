"""
Daily Update Script #4: Update Player Season Averages (OPTIMIZED)
==================================================================
Uses TeamPlayerDashboard to fetch ALL players in ONE API call per team!

Run this AFTER daily_update_3_game_logs.py
"""

import psycopg2
from nba_api.stats.endpoints import teamplayerdashboard
from nba_api.stats.static import teams
import time
import os

NEON_DSN = os.environ.get('NEON_DSN', "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require")
CURRENT_SEASON = "2025-26"
DELAY_BETWEEN_TEAMS = 3.5  # Increased to avoid rate limiting (NBA API limit: ~20 req/min)
MAX_RETRIES = 3

def normalize_name(name):
    """Convert player name to column name format"""
    if name is None:
        return None
    return name.lower().replace(' ', '_').replace("'", '').replace('.', '').replace('-', '_')

def get_active_players_for_team(conn, team_schema):
    """Get list of active players from schedule table columns"""
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = '{team_schema}' 
        AND table_name = 'schedule'
        AND column_name NOT IN ('game_date', 'game_id', 'opponent', 'home_away', 
                                 'result', 'team_score', 'opponent_score', 'created_at',
                                 'missing_usage', 'injury_weight', 'games_ago', 'recency_weight')
        ORDER BY column_name
    """)
    
    player_columns = set(row[0] for row in cursor.fetchall())
    cursor.close()
    
    return player_columns

def update_team_season_averages(conn, team_id, team_schema, team_name):
    """Update season averages for all players on a team using ONE API call"""
    cursor = conn.cursor()
    
    # Get active roster from database
    active_players = get_active_players_for_team(conn, team_schema)
    
    if not active_players:
        return 0
    
    # Fetch ALL player stats for the team in ONE API call!
    for attempt in range(MAX_RETRIES):
        try:
            # Add small delay before first attempt to respect rate limits
            if attempt == 0:
                time.sleep(0.5)
            
            dashboard = teamplayerdashboard.TeamPlayerDashboard(
                team_id=team_id,
                season=CURRENT_SEASON,
                per_mode_detailed='PerGame',
                timeout=60
            )
            
            stats_df = dashboard.get_data_frames()[1]  # PlayersSeasonTotals
            break
            
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = (attempt + 1) * 5
                print(f"\n    ⚠️  API fetch failed (attempt {attempt + 1}/{MAX_RETRIES}), waiting {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                print(f"\n    ❌ Failed after {MAX_RETRIES} attempts: {e}")
                cursor.close()
                return 0
    
    if stats_df.empty:
        cursor.close()
        return 0
    
    # Build name-to-data mapping
    player_stats_map = {}
    for _, row in stats_df.iterrows():
        player_name = row['PLAYER_NAME']
        player_normalized = normalize_name(player_name)
        if player_normalized:
            player_stats_map[player_normalized] = {
                'id': row['PLAYER_ID'],
                'name': player_name,
                'stats': row
            }
    
    players_updated = 0
    players_skipped = 0
    
    for player_col in active_players:
        try:
            if player_col not in player_stats_map:
                players_skipped += 1
                continue
            
            player_data = player_stats_map[player_col]
            player_id = player_data['id']
            player_name = player_data['name']
            stats = player_data['stats']
            
            # Extract stats
            gp = int(stats.get('GP', 0))
            min_avg = float(stats.get('MIN', 0))
            pts_avg = float(stats.get('PTS', 0))
            reb_avg = float(stats.get('REB', 0))
            ast_avg = float(stats.get('AST', 0))
            stl_avg = float(stats.get('STL', 0))
            blk_avg = float(stats.get('BLK', 0))
            tov_avg = float(stats.get('TOV', 0))
            fg_pct = float(stats.get('FG_PCT', 0))
            fg3_pct = float(stats.get('FG3_PCT', 0))
            ft_pct = float(stats.get('FT_PCT', 0))
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
            
            # Upsert into database
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
                updated_at = CURRENT_TIMESTAMP
            """
            
            cursor.execute(insert_query, (
                player_id, player_name, gp, min_avg, pts_avg, reb_avg, ast_avg,
                stl_avg, blk_avg, tov_avg, fg_pct, fg3_pct, ft_pct,
                fgm_avg, fga_avg, fg3m_avg, fg3a_avg, ftm_avg, fta_avg,
                oreb_avg, dreb_avg, pf_avg, plus_minus_avg
            ))
            
            players_updated += 1
            
        except Exception as e:
            print(f"\n    ⚠️  Error updating {player_col}: {e}")
            players_skipped += 1
            continue
    
    conn.commit()
    cursor.close()
    
    if players_skipped > 0:
        print(f"(skipped {players_skipped})", end=" ")
    
    return players_updated

def main():
    print("=" * 70)
    print(f"📊 Daily Update #4: Player Season Averages (OPTIMIZED)")
    print(f"Season: {CURRENT_SEASON}")
    print(f"Using TeamPlayerDashboard: 1 API call per team (30 total)")
    print(f"Rate limit: {DELAY_BETWEEN_TEAMS}s between teams (~{60/DELAY_BETWEEN_TEAMS:.1f} req/min)")
    print("=" * 70)
    print()
    
    all_teams = teams.get_teams()
    conn = psycopg2.connect(NEON_DSN)
    
    teams_updated = 0
    total_players = 0
    
    for idx, team in enumerate(sorted(all_teams, key=lambda x: x['full_name']), 1):
        # Refresh connection before each team
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
        except:
            try:
                conn.close()
            except:
                pass
            conn = psycopg2.connect(NEON_DSN)
        
        team_id = team['id']
        team_name = team['full_name']
        team_schema = team_name.lower().replace(' ', '_')
        
        print(f"[{idx}/30] {team_name}... ", end="", flush=True)
        
        try:
            players_updated = update_team_season_averages(conn, team_id, team_schema, team_name)
            
            if players_updated > 0:
                print(f"✅ {players_updated} players")
                teams_updated += 1
                total_players += players_updated
            else:
                print("- No updates")
            
            # Rate limiting between teams (skip delay after last team)
            if idx < 30:
                time.sleep(DELAY_BETWEEN_TEAMS)
                
        except Exception as e:
            print(f"❌ Error: {e}")
            try:
                conn.close()
            except:
                pass
            conn = psycopg2.connect(NEON_DSN)
            time.sleep(DELAY_BETWEEN_TEAMS)
            continue
    
    conn.close()
    
    print()
    print("=" * 70)
    print(f"✅ Complete! Updated {total_players} players across {teams_updated} teams")
    print("=" * 70)

if __name__ == "__main__":
    main()
