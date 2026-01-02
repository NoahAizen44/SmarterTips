"""
Fill Player Game Logs for All NBA Teams
========================================
Uses NBA API to fetch detailed game stats for all players across all teams
"""

import psycopg2
from nba_api.stats.endpoints import playergamelogs
from nba_api.stats.static import teams
import pandas as pd
import time

NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

def retry_with_backoff(func, max_retries=5, initial_delay=2):
    """Retry a function with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)
                print(f"\n    ⚠️  Timeout, retrying in {delay}s (attempt {attempt + 1}/{max_retries})...", flush=True)
                time.sleep(delay)
            else:
                raise

def main():
    print("=" * 70)
    print("🏀 Filling Player Game Logs for All NBA Teams")
    print("=" * 70)
    print()
    
    # Get all NBA teams
    all_teams = teams.get_teams()
    
    # Connect to DB
    conn = psycopg2.connect(NEON_DSN)
    cur = conn.cursor()
    
    total_logs_inserted = 0
    
    for team_idx, team in enumerate(sorted(all_teams, key=lambda x: x['full_name']), 1):
        team_id = team['id']
        team_name = team['full_name']
        schema_name = team_name.lower().replace(' ', '_')
        
        print(f"\n[{team_idx}/30] {team_name}")
        print("-" * 70)
        
        try:
            # Fetch all game logs for this team
            def fetch_logs():
                logs = playergamelogs.PlayerGameLogs(
                    team_id_nullable=str(team_id),
                    season_nullable='2025'
                )
                return logs.get_data_frames()[0]
            
            df = retry_with_backoff(fetch_logs, max_retries=5, initial_delay=3)
            
            print(f"  → {len(df)} player game entries")
            print(f"  → {df['PLAYER_NAME'].nunique()} unique players")
            print(f"  → {df['GAME_ID'].nunique()} unique games")
            print()
            print("  Inserting into database...", end=" ", flush=True)
            
            inserted = 0
            
            for _, log in df.iterrows():
                game_date = pd.to_datetime(log['GAME_DATE']).date()
                
                cur.execute(f"""
                    INSERT INTO {schema_name}.player_game_logs 
                    (player_id, player_name, nickname, team_abbreviation, game_id, game_date, matchup, wl,
                     min, fgm, fga, fg_pct, fg3m, fg3a, fg3_pct, ftm, fta, ft_pct,
                     oreb, dreb, reb, ast, tov, stl, blk, blka, pf, pfd, pts, 
                     plus_minus, nba_fantasy_pts, dd2, td3)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (player_name, game_date) DO UPDATE SET
                        player_id = EXCLUDED.player_id,
                        nickname = EXCLUDED.nickname,
                        team_abbreviation = EXCLUDED.team_abbreviation,
                        game_id = EXCLUDED.game_id,
                        matchup = EXCLUDED.matchup,
                        wl = EXCLUDED.wl,
                        min = EXCLUDED.min,
                        fgm = EXCLUDED.fgm,
                        fga = EXCLUDED.fga,
                        fg_pct = EXCLUDED.fg_pct,
                        fg3m = EXCLUDED.fg3m,
                        fg3a = EXCLUDED.fg3a,
                        fg3_pct = EXCLUDED.fg3_pct,
                        ftm = EXCLUDED.ftm,
                        fta = EXCLUDED.fta,
                        ft_pct = EXCLUDED.ft_pct,
                        oreb = EXCLUDED.oreb,
                        dreb = EXCLUDED.dreb,
                        reb = EXCLUDED.reb,
                        ast = EXCLUDED.ast,
                        tov = EXCLUDED.tov,
                        stl = EXCLUDED.stl,
                        blk = EXCLUDED.blk,
                        blka = EXCLUDED.blka,
                        pf = EXCLUDED.pf,
                        pfd = EXCLUDED.pfd,
                        pts = EXCLUDED.pts,
                        plus_minus = EXCLUDED.plus_minus,
                        nba_fantasy_pts = EXCLUDED.nba_fantasy_pts,
                        dd2 = EXCLUDED.dd2,
                        td3 = EXCLUDED.td3
                """, (
                    int(log.get('PLAYER_ID', 0)),
                    log.get('PLAYER_NAME', ''),
                    log.get('NICKNAME', ''),
                    log.get('TEAM_ABBREVIATION', ''),
                    str(log.get('GAME_ID', '')),
                    game_date,
                    log.get('MATCHUP', ''),
                    log.get('WL', ''),
                    log.get('MIN', 0),
                    log.get('FGM', 0),
                    log.get('FGA', 0),
                    log.get('FG_PCT', 0),
                    log.get('FG3M', 0),
                    log.get('FG3A', 0),
                    log.get('FG3_PCT', 0),
                    log.get('FTM', 0),
                    log.get('FTA', 0),
                    log.get('FT_PCT', 0),
                    log.get('OREB', 0),
                    log.get('DREB', 0),
                    log.get('REB', 0),
                    log.get('AST', 0),
                    log.get('TOV', 0),
                    log.get('STL', 0),
                    log.get('BLK', 0),
                    log.get('BLKA', 0),
                    log.get('PF', 0),
                    log.get('PFD', 0),
                    log.get('PTS', 0),
                    log.get('PLUS_MINUS', 0),
                    log.get('NBA_FANTASY_PTS', 0),
                    log.get('DD2', 0),
                    log.get('TD3', 0)
                ))
                inserted += 1
            
            conn.commit()
            total_logs_inserted += inserted
            print(f"✅ {inserted} logs inserted")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            time.sleep(5)
            continue
        
        time.sleep(3)  # Rate limit between teams
    
    cur.close()
    conn.close()
    
    print()
    print("=" * 70)
    print(f"✅ Complete! Total player game logs inserted: {total_logs_inserted}")
    print("=" * 70)

if __name__ == "__main__":
    main()
