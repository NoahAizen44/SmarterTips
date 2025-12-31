"""
Fill Player Data for Atlanta Hawks - Version 2
===============================================
Uses NBA API exclusively for consistency
"""

import psycopg2
from nba_api.stats.endpoints import boxscoretraditionalv3
import time
from datetime import datetime

NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"
HAWKS_TEAM_ID = 1610612737

def normalize_name(name):
    """Convert player name to column name format"""
    return name.lower().replace(' ', '_').replace("'", '').replace('.', '').replace('-', '_')

def get_hawks_roster_columns(conn):
    """Get list of player column names from Hawks schedule table"""
    cur = conn.cursor()
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'atlanta_hawks' 
        AND table_name = 'schedule'
        AND column_name NOT IN ('game_date', 'game_id', 'opponent', 'home_away', 
                                 'result', 'team_score', 'opponent_score', 'created_at');
    """)
    player_columns = [row[0] for row in cur.fetchall()]
    cur.close()
    return player_columns

def main():
    print("=" * 60)
    print("🏀 Filling Player Data for Atlanta Hawks (NBA API)")
    print("=" * 60)
    print()
    
    conn = psycopg2.connect(NEON_DSN)
    
    # Get player columns from DB
    print("📋 Getting Hawks roster columns...")
    player_columns = get_hawks_roster_columns(conn)
    print(f"  → {len(player_columns)} players in roster")
    print()
    
    # Get Hawks game log from NBA API
    print("📊 Fetching Hawks games from NBA API...")
    from nba_api.stats.endpoints import leaguegamefinder
    games = leaguegamefinder.LeagueGameFinder(team_id_nullable=str(HAWKS_TEAM_ID))
    games_df = games.get_data_frames()[0]
    
    # Filter for current season, Oct onwards (no summer league)
    games_df = games_df[games_df['SEASON_ID'] == '22025']
    import pandas as pd
    games_df['GAME_DATE'] = pd.to_datetime(games_df['GAME_DATE'])
    games_df = games_df[games_df['GAME_DATE'] >= '2025-10-01']
    
    print(f"  → Found {len(games_df)} games")
    print()
    
    if len(games_df) == 0:
        print("⚠️  No games found! Check season format.")
        return
    
    print(f"Sample games:")
    print(games_df[['GAME_DATE', 'MATCHUP']].head(3))
    print()
    
    # Process each game
    print("✍️  Processing games...")
    cur = conn.cursor()
    
    for idx, game_row in games_df.iterrows():
        game_date_str = game_row['GAME_DATE']  # Timestamp
        game_id = str(game_row['GAME_ID'])
        matchup = game_row['MATCHUP']
        
        # Convert to datetime
        game_date = game_row['GAME_DATE']
        if isinstance(game_date, str):
            game_date = datetime.strptime(game_date_str, "%Y-%m-%d")
        db_date_str = game_date.strftime("%Y-%m-%d")
        
        # Check if this game exists in our DB
        cur.execute("SELECT game_date FROM atlanta_hawks.schedule WHERE game_date = %s", (game_date,))
        if cur.fetchone() is None:
            continue  # Game not in our DB
        
        print(f"  → {db_date_str} ({matchup})...", end=" ")
        
        # Get box score for this game
        try:
            boxscore = boxscoretraditionalv3.BoxScoreTraditionalV3(game_id=game_id)
            player_stats = boxscore.get_data_frames()[0]
            
            if idx == 0:  # Debug first game
                print(f"\n    DEBUG: Box score has {len(player_stats)} total players")
                print(f"    DEBUG: Team IDs: {player_stats['teamId'].unique()}")
                print(f"    DEBUG: HAWKS_TEAM_ID = {HAWKS_TEAM_ID}")
            
            # Filter for Hawks players
            hawks_players = player_stats[player_stats['teamId'] == HAWKS_TEAM_ID]
            
            # Build full names
            players_who_played = []
            for _, p in hawks_players.iterrows():
                full_name = f"{p['firstName']} {p['familyName']}"
                players_who_played.append(full_name)
            
            if idx == 0:
                print(f"    DEBUG: Hawks players found: {len(hawks_players)}")
                print(f"    DEBUG: Player names: {players_who_played[:3]}")
            
            # Normalize names
            normalized_played = {normalize_name(name) for name in players_who_played}
            
            if idx == 0:
                print(f"    DEBUG: Normalized: {list(normalized_played)[:3]}")
                print(f"    DEBUG: Roster columns: {player_columns[:3]}\n")
            
            # Set all to FALSE first
            set_all_false = ', '.join([f'"{col}" = FALSE' for col in player_columns])
            cur.execute(f"""
                UPDATE atlanta_hawks.schedule
                SET {set_all_false}
                WHERE game_date = %s;
            """, (game_date,))
            
            # Set TRUE for who played
            played_updates = []
            for player_col in player_columns:
                if player_col in normalized_played:
                    played_updates.append(f'"{player_col}" = TRUE')
            
            if played_updates:
                cur.execute(f"""
                    UPDATE atlanta_hawks.schedule
                    SET {', '.join(played_updates)}
                    WHERE game_date = %s;
                """, (game_date,))
            
            print(f"{len(played_updates)} played")
            
            time.sleep(0.6)  # Rate limit
            
        except Exception as e:
            print(f"Error: {e}")
            continue
    
    conn.commit()
    cur.close()
    conn.close()
    
    print()
    print("=" * 60)
    print("✅ Hawks player data filled!")
    print("=" * 60)

if __name__ == "__main__":
    main()
