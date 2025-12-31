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
        
        # Check if we already have logs for this game
        cur.execute(f"""
            SELECT COUNT(*) 
            FROM {schema_name}.player_game_logs 
            WHERE game_id = %s
        """, (game_id,))
        
        existing_count = cur.fetchone()[0]
        if existing_count > 0:
            print(f"Already filled ({existing_count} players)")
            cur.close()
            conn.close()
            return 0
        
        # Fetch game logs from NBA API
        try:
            game_logs = playergamelogs.PlayerGameLogs(
                team_id_nullable=team_id,
                date_from_nullable=date_from,
                date_to_nullable=date_to,
                season_nullable='2024-25'
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
            
            # Convert minutes string (e.g., "25:30") to decimal
            minutes_str = row['MIN']
            if minutes_str and ':' in str(minutes_str):
                parts = str(minutes_str).split(':')
                minutes = int(parts[0]) + (int(parts[1]) / 60.0)
            else:
                minutes = 0
            
            # Insert with ON CONFLICT to handle duplicates
            cur.execute(f"""
                INSERT INTO {schema_name}.player_game_logs (
                    player_name, game_id, game_date, matchup, wl,
                    min, fgm, fga, fg_pct, fg3m, fg3a, fg3_pct,
                    ftm, fta, ft_pct, oreb, dreb, reb, ast, stl,
                    blk, tov, pf, pts, plus_minus
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                ON CONFLICT (player_name, game_id) DO UPDATE SET
                    game_date = EXCLUDED.game_date,
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
                    stl = EXCLUDED.stl,
                    blk = EXCLUDED.blk,
                    tov = EXCLUDED.tov,
                    pf = EXCLUDED.pf,
                    pts = EXCLUDED.pts,
                    plus_minus = EXCLUDED.plus_minus
            """, (
                player_name, game_id, target_date, row['MATCHUP'], row['WL'],
                minutes, row['FGM'], row['FGA'], row['FG_PCT'], row['FG3M'], row['FG3A'], row['FG3_PCT'],
                row['FTM'], row['FTA'], row['FT_PCT'], row['OREB'], row['DREB'], row['REB'], row['AST'], row['STL'],
                row['BLK'], row['TOV'], row['PF'], row['PTS'], row['PLUS_MINUS']
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
