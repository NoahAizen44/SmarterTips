"""
Populate Hawks Schedule Using NBA API
======================================
Fill game dates for Hawks using NBA API instead of API-Sports
"""

import psycopg2
from nba_api.stats.endpoints import leaguegamefinder
import pandas as pd
import time

NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"
HAWKS_TEAM_ID = 1610612737

def main():
    print("=" * 60)
    print("🏀 Populating Hawks Schedule from NBA API")
    print("=" * 60)
    print()
    
    # Get Hawks games from NBA API
    print("📊 Fetching Hawks games...")
    games = leaguegamefinder.LeagueGameFinder(team_id_nullable=str(HAWKS_TEAM_ID))
    games_df = games.get_data_frames()[0]
    
    # Filter for 2025-26 season (SEASON_ID = 22025) and exclude summer league (July games)
    games_df = games_df[games_df['SEASON_ID'] == '22025']
    games_df['GAME_DATE'] = pd.to_datetime(games_df['GAME_DATE'])
    games_df = games_df[games_df['GAME_DATE'] >= '2025-10-01']  # Only Oct onwards
    
    print(f"  → Found {len(games_df)} games (excluding summer league)")
    
    print()
    print("Sample games:")
    print(games_df[['GAME_DATE', 'MATCHUP', 'WL']].head(5))
    print()
    
    # Connect to DB
    conn = psycopg2.connect(NEON_DSN)
    cur = conn.cursor()
    
    print("✍️  Inserting games into Hawks schedule...")
    
    for idx, game in games_df.iterrows():
        from datetime import datetime
        
        # Get date - it's already a timestamp from pandas
        game_date = game['GAME_DATE']
        if isinstance(game_date, str):
            game_date = datetime.strptime(game_date, "%Y-%m-%d")
        db_date_str = game_date.strftime("%Y-%m-%d")
        
        # Parse matchup to get opponent and home/away
        matchup = game['MATCHUP']  # e.g., "ATL vs. MIA" or "ATL @ BOS"
        
        if ' vs. ' in matchup:
            home_away = 'HOME'
            opponent = matchup.split(' vs. ')[1]
        else:
            home_away = 'AWAY'
            opponent = matchup.split(' @ ')[1]
        
        # Get result
        result = 'W' if game['WL'] == 'W' else 'L'
        team_score = game['PTS']
        opponent_score = int(game['PTS']) - int(game['PLUS_MINUS']) if game['WL'] == 'W' else int(game['PTS']) + abs(int(game['PLUS_MINUS']))
        
        # Use NBA game ID
        game_id = str(game['GAME_ID'])
        
        # Insert
        cur.execute("""
            INSERT INTO atlanta_hawks.schedule 
            (game_date, game_id, opponent, home_away, result, team_score, opponent_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (game_date) DO NOTHING;
        """, (game_date, game_id, opponent, home_away, result, team_score, opponent_score))
        
        print(f"  ✓ {game_date.strftime('%Y-%m-%d')}: {matchup} ({result})")
    
    conn.commit()
    cur.close()
    conn.close()
    
    print()
    print("=" * 60)
    print(f"✅ Inserted {len(games_df)} games!")
    print("=" * 60)

if __name__ == "__main__":
    main()
