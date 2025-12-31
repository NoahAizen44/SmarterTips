"""
Test Player Game Logs - Hawks Only
===================================
Tests fetching and storing player game logs for Atlanta Hawks
"""

import psycopg2
from nba_api.stats.endpoints import playergamelogs
import pandas as pd
import time

NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

def main():
    print("=" * 70)
    print("🏀 Testing Player Game Logs - Atlanta Hawks")
    print("=" * 70)
    print()
    
    team_id = 1610612737  # Hawks
    team_name = "Atlanta Hawks"
    schema_name = "atlanta_hawks"
    
    # Connect to DB
    conn = psycopg2.connect(NEON_DSN)
    cur = conn.cursor()
    
    print(f"Fetching all player game logs for {team_name} (team_id={team_id})...\n")
    
    try:
        # Fetch all game logs for Hawks in 2025 season
        logs = playergamelogs.PlayerGameLogs(
            team_id_nullable=str(team_id),
            season_nullable='2025'
        )
        df = logs.get_data_frames()[0]
        
        print(f"✅ Found {len(df)} total player game entries")
        print(f"   Unique players: {df['PLAYER_NAME'].nunique()}")
        print(f"   Unique games: {df['GAME_ID'].nunique()}")
        print()
        
        print("Sample data (first 3 rows):")
        print("-" * 70)
        for idx, row in df.head(3).iterrows():
            print(f"Player: {row['PLAYER_NAME']}")
            print(f"  Date: {row['GAME_DATE']}, Matchup: {row['MATCHUP']}")
            print(f"  Stats: {row['PTS']} pts, {row['REB']} reb, {row['AST']} ast, {row['MIN']} min")
            print()
        
        print("Inserting into database...")
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
        print(f"✅ Inserted {inserted} player game logs")
        
        # Verify the data
        cur.execute(f"SELECT COUNT(*) FROM {schema_name}.player_game_logs")
        total = cur.fetchone()[0]
        print(f"✅ Total records in database: {total}")
        
        cur.execute(f"SELECT COUNT(DISTINCT player_name) FROM {schema_name}.player_game_logs")
        unique_players = cur.fetchone()[0]
        print(f"✅ Unique players: {unique_players}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    cur.close()
    conn.close()
    
    print()
    print("=" * 70)
    print("✅ Test complete!")
    print("=" * 70)

if __name__ == "__main__":
    main()
