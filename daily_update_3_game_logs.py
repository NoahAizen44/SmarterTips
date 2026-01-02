import psycopg2
from nba_api.stats.endpoints import playergamelogs
from nba_api.stats.static import teams
import time
import os
from datetime import datetime, date, timedelta

# Get database connection from environment variable or use default
NEON_DSN = os.environ.get('NEON_DSN', "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require")

def update_team_game_logs(team, target_date):
    """Update player_game_logs table for a team for a specific date"""
    team_name = team['full_name']
    team_id = team['id']
    schema_name = team_name.lower().replace(' ', '_')
    
    try:
        conn = psycopg2.connect(NEON_DSN)
        cur = conn.cursor()
        
        # Format date for NBA API (YYYY-MM-DD)
        date_from = target_date.strftime('%Y-%m-%d')
        date_to = target_date.strftime('%Y-%m-%d')
        
        # Check if team had a game on this date
        cur.execute(f"""
            SELECT game_id 
            FROM {schema_name}.schedule 
            WHERE game_date = %s
        """, (target_date,))
        
        game_result = cur.fetchone()
        if not game_result:
            print("No game")
            cur.close()
            conn.close()
            return 0
        
        game_id = game_result[0]
        
        # Fetch game logs from NBA API (ON CONFLICT will upsert if records already exist)
        try:
            game_logs = playergamelogs.PlayerGameLogs(
                team_id_nullable=team_id,
                date_from_nullable=date_from,
                date_to_nullable=date_to,
                season_nullable='2025-26',
                season_type_nullable='Regular Season'  # Exclude preseason/playoffs
            )
            logs_df = game_logs.get_data_frames()[0]
            
            if logs_df.empty:
                print("No logs found")
                cur.close()
                conn.close()
                return 0
            
            # Filter for this specific game
            logs_df = logs_df[logs_df['GAME_ID'] == game_id]
            
            if logs_df.empty:
                print("No logs for game")
                cur.close()
                conn.close()
                return 0
            
        except Exception as api_error:
            print(f"API error: {api_error}")
            cur.close()
            conn.close()
            return 0
        
        # Insert all player logs
        inserted = 0
        for _, row in logs_df.iterrows():
            player_name = row['PLAYER_NAME']
            
            # Minutes is already a decimal from the API (e.g., 36.283333)
            minutes = float(row['MIN']) if row['MIN'] else 0.0
            
            # Insert with ON CONFLICT to handle duplicates
            cur.execute(f"""
                INSERT INTO {schema_name}.player_game_logs (
                    player_id, player_name, nickname, team_abbreviation,
                    game_id, game_date, matchup, wl,
                    min, fgm, fga, fg_pct, fg3m, fg3a, fg3_pct,
                    ftm, fta, ft_pct, oreb, dreb, reb, ast, tov, stl,
                    blk, blka, pf, pfd, pts, plus_minus,
                    nba_fantasy_pts, dd2, td3
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s
                )
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
                int(row['PLAYER_ID']), player_name, row['NICKNAME'], row['TEAM_ABBREVIATION'],
                game_id, target_date, row['MATCHUP'], row['WL'],
                minutes, int(row['FGM']), int(row['FGA']), float(row['FG_PCT']) if row['FG_PCT'] else None,
                int(row['FG3M']), int(row['FG3A']), float(row['FG3_PCT']) if row['FG3_PCT'] else None,
                int(row['FTM']), int(row['FTA']), float(row['FT_PCT']) if row['FT_PCT'] else None,
                int(row['OREB']), int(row['DREB']), int(row['REB']), int(row['AST']), int(row['TOV']), int(row['STL']),
                int(row['BLK']), int(row['BLKA']), int(row['PF']), int(row['PFD']), int(row['PTS']), float(row['PLUS_MINUS']) if row['PLUS_MINUS'] else None,
                float(row['NBA_FANTASY_PTS']) if row['NBA_FANTASY_PTS'] else None, int(row['DD2']), int(row['TD3'])
            ))
            inserted += 1
        
        conn.commit()
        print(f"✅ Added {inserted} logs")
        
        cur.close()
        conn.close()
        return 1
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
        return 0

def main():
    # Use yesterday's date (to capture all completed games regardless of timezone)
    # Or use command line argument for testing: python3 script.py 2025-12-29
    import sys
    if len(sys.argv) > 1:
        target_date = datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
    else:
        target_date = date.today() - timedelta(days=1)
    
    print("=" * 70)
    print(f"📝 Daily Update #3: Player Game Logs for {target_date}")
    print("=" * 70)
    print()
    
    all_teams = teams.get_teams()
    teams_updated = 0
    
    for idx, team in enumerate(sorted(all_teams, key=lambda x: x['full_name']), 1):
        team_name = team['full_name']
        print(f"[{idx}/30] {team_name}...", end=" ", flush=True)
        
        result = update_team_game_logs(team, target_date)
        teams_updated += result
        
        time.sleep(1.5)  # Rate limit
    
    print()
    print("=" * 70)
    print(f"✅ Complete! Updated game logs for {teams_updated} teams")
    print("=" * 70)

if __name__ == "__main__":
    main()
