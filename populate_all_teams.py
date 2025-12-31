"""
Populate All NBA Team Schedules Using NBA API
==============================================
Fill game dates for all 30 NBA teams using NBA API
"""

import psycopg2
from nba_api.stats.endpoints import leaguegamefinder
from nba_api.stats.static import teams
import pandas as pd
import time

NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

def main():
    print("=" * 60)
    print("🏀 Populating All NBA Team Schedules from NBA API")
    print("=" * 60)
    print()
    
    # Get all NBA teams
    all_teams = teams.get_teams()
    
    # Connect to DB
    conn = psycopg2.connect(NEON_DSN)
    cur = conn.cursor()
    
    total_games = 0
    
    for i, team in enumerate(sorted(all_teams, key=lambda x: x['full_name']), 1):
        team_id = team['id']
        team_name = team['full_name']
        schema_name = team_name.lower().replace(' ', '_')
        
        print(f"[{i}/30] {team_name}...")
        
        # Clear existing schedule
        cur.execute(f"DELETE FROM {schema_name}.schedule;")
        
        # Get team games from NBA API
        try:
            games = leaguegamefinder.LeagueGameFinder(team_id_nullable=str(team_id))
            games_df = games.get_data_frames()[0]
            
            # Filter for 2025-26 season, Oct onwards (no summer league)
            games_df = games_df[games_df['SEASON_ID'] == '22025']
            games_df['GAME_DATE'] = pd.to_datetime(games_df['GAME_DATE'])
            games_df = games_df[games_df['GAME_DATE'] >= '2025-10-01']
            
            print(f"  → Found {len(games_df)} games")
            
            # Insert each game
            for idx, game in games_df.iterrows():
                from datetime import datetime
                
                # Get date
                game_date = game['GAME_DATE']
                if isinstance(game_date, str):
                    game_date = datetime.strptime(game_date, "%Y-%m-%d")
                
                # Parse matchup
                matchup = game['MATCHUP']
                if ' vs. ' in matchup:
                    home_away = 'HOME'
                    opponent = matchup.split(' vs. ')[1]
                else:
                    home_away = 'AWAY'
                    opponent = matchup.split(' @ ')[1]
                
                # Get result and scores
                result = 'W' if game['WL'] == 'W' else 'L'
                team_score = game['PTS']
                opponent_score = int(game['PTS']) - int(game['PLUS_MINUS']) if game['WL'] == 'W' else int(game['PTS']) + abs(int(game['PLUS_MINUS']))
                game_id = str(game['GAME_ID'])
                
                # Insert
                cur.execute(f"""
                    INSERT INTO {schema_name}.schedule 
                    (game_date, game_id, opponent, home_away, result, team_score, opponent_score)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (game_date) DO NOTHING;
                """, (game_date, game_id, opponent, home_away, result, team_score, opponent_score))
            
            conn.commit()
            total_games += len(games_df)
            print(f"  ✅ Inserted {len(games_df)} games")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue
        
        time.sleep(0.6)  # Rate limit
    
    cur.close()
    conn.close()
    
    print()
    print("=" * 60)
    print(f"✅ Complete! Inserted {total_games} total games across 30 teams")
    print("=" * 60)

if __name__ == "__main__":
    main()
