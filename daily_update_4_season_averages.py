"""
Daily Update Script #4: Update Player Season Averages
======================================================
Updates season averages for all active players across all teams.
This keeps the averages current as the season progresses.

Run this AFTER daily_update_3_game_logs.py
"""

import psycopg2
from nba_api.stats.endpoints import playerdashboardbygeneralsplits
from nba_api.stats.static import teams
import time
import os
from datetime import datetime

# Get database connection from environment variable or use default
NEON_DSN = os.environ.get('NEON_DSN', "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require")

# Current season
CURRENT_SEASON = "2025-26"

def get_active_players_for_team(conn, team_schema):
    """Get list of active players from the team's roster (from schedule table columns)"""
    cursor = conn.cursor()
    
    # Get all player columns from schedule table (these are the active roster)
    cursor.execute(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = '{team_schema}' 
        AND table_name = 'schedule'
        AND column_name NOT IN ('game_date', 'game_id', 'opponent', 'home_away', 
                                 'result', 'team_score', 'opponent_score', 'created_at')
        ORDER BY column_name
    """)
    
    player_columns = [row[0] for row in cursor.fetchall()]
    cursor.close()
    
    return player_columns

def normalize_name(name):
    """Convert player name to column name format"""
    return name.lower().replace(' ', '_').replace("'", '').replace('.', '').replace('-', '_')

def get_player_id_from_name(player_name_normalized, team_id):
    """Try to get player_id from game logs table or return None"""
    # We'll use the player_name to look up in player_game_logs
    # This is a best-effort approach
    return None  # For now, we'll skip player_id requirement

def get_player_season_stats_by_name(player_name, team_id):
    """Get season averages for a player by searching via team"""
    try:
        # Use team roster to find player ID
        from nba_api.stats.endpoints import commonteamroster
        roster = commonteamroster.CommonTeamRoster(
            team_id=team_id,
            season=CURRENT_SEASON
        )
        roster_df = roster.get_data_frames()[0]
        
        # Find player by name match
        player_row = None
        for _, row in roster_df.iterrows():
            roster_name = f"{row['PLAYER']}".strip()
            roster_normalized = normalize_name(roster_name)
            if roster_normalized == player_name:
                player_row = row
                break
        
        if player_row is None:
            return None
        
        player_id = player_row['PLAYER_ID']
        
        # Get player stats
        dashboard = playerdashboardbygeneralsplits.PlayerDashboardByGeneralSplits(
            player_id=player_id,
            season=CURRENT_SEASON,
            per_mode_detailed='PerGame'
        )
        
        stats_df = dashboard.get_data_frames()[0]
        
        if stats_df.empty:
            return None
        
        stats = stats_df.iloc[0].to_dict()
        return {
            'player_id': player_id,
            'player_name': roster_name,
            'stats': stats
        }
        
    except Exception as e:
        print(f"    ⚠️  Could not fetch stats: {e}")
        return None

def update_team_season_averages(conn, team_id, team_schema, team_name):
    """Update season averages for all active players on a team"""
    cursor = conn.cursor()
    
    # Get active roster
    active_players = get_active_players_for_team(conn, team_schema)
    
    if not active_players:
        print(f"  - No active players found")
        return 0
    
    players_updated = 0
    
    for player_col in active_players:
        try:
            result = get_player_season_stats_by_name(player_col, team_id)
            
            if result is None:
                continue
            
            player_id = result['player_id']
            player_name = result['player_name']
            stats = result['stats']
            
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
            
            # Rate limiting
            time.sleep(0.6)
            
        except Exception as e:
            print(f"    ⚠️  Error updating {player_col}: {e}")
            continue
    
    conn.commit()
    cursor.close()
    
    return players_updated

def main():
    print("=" * 70)
    print(f"📊 Daily Update #4: Player Season Averages")
    print(f"Season: {CURRENT_SEASON}")
    print("=" * 70)
    print()
    
    all_teams = teams.get_teams()
    conn = psycopg2.connect(NEON_DSN)
    
    teams_updated = 0
    total_players = 0
    
    for idx, team in enumerate(sorted(all_teams, key=lambda x: x['full_name']), 1):
        # Refresh connection every 5 teams to avoid pooler timeout
        if idx % 5 == 1:
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
        
        print(f"[{idx}/30] {team_name}...", end=" ", flush=True)
        
        try:
            players_updated = update_team_season_averages(conn, team_id, team_schema, team_name)
            
            if players_updated > 0:
                print(f"✅ Updated {players_updated} players")
                teams_updated += 1
                total_players += players_updated
            else:
                print("- No updates")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            # Refresh connection after error
            try:
                conn.close()
            except:
                pass
            conn = psycopg2.connect(NEON_DSN)
            continue
    
    conn.close()
    
    print()
    print("=" * 70)
    print(f"✅ Complete! Updated {total_players} players across {teams_updated} teams")
    print("=" * 70)

if __name__ == "__main__":
    main()
