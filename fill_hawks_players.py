"""
Fill Player Data for Atlanta Hawks
===================================
For each game in the Hawks schedule, marks which players played (TRUE) 
and which didn't play (FALSE) based on NBA API game logs
"""

import psycopg2
from nba_api.stats.endpoints import playergamelog
import time
from datetime import datetime, timedelta

# Neon connection
NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

# Hawks team ID
HAWKS_TEAM_ID = 1610612737

def normalize_name(name):
    """Convert player name to column name format"""
    return name.lower().replace(' ', '_').replace("'", '').replace('.', '').replace('-', '_')

def get_hawks_roster(conn):
    """Get all player columns from the Hawks schedule table"""
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

def get_hawks_games(conn):
    """Get all Hawks game dates"""
    cur = conn.cursor()
    cur.execute("""
        SELECT game_date
        FROM atlanta_hawks.schedule
        ORDER BY game_date;
    """)
    
    games = [row[0] for row in cur.fetchall()]
    cur.close()
    return games

def get_players_who_played_in_game(team_id, game_date_nba_format, debug=False):
    """Get list of players who played in a specific game by date"""
    from nba_api.stats.endpoints import teamgamelog, boxscoretraditionalv2
    
    try:
        # Get team's game log
        gamelog = teamgamelog.TeamGameLog(team_id=str(team_id), season='2024-25')
        df = gamelog.get_data_frames()[0]
        
        if debug:
            print(f"\n    DEBUG: Team has {len(df)} games total")
            print(f"    DEBUG: Sample dates: {df['GAME_DATE'].head(3).tolist()}")
        
        # Find the game by date
        game_row = df[df['GAME_DATE'] == game_date_nba_format]
        
        if debug:
            print(f"    DEBUG: Looking for '{game_date_nba_format}'")
            print(f"    DEBUG: Found {len(game_row)} matching games")
        
        if len(game_row) == 0:
            return []
        
        # Get game ID
        game_id = str(game_row.iloc[0]['Game_ID'])
        
        if debug:
            print(f"    DEBUG: Game ID: {game_id}")
        
        # Now get box score for that game
        boxscore = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id)
        player_stats = boxscore.get_data_frames()[0]
        
        # Filter for our team and get player names
        team_players = player_stats[player_stats['TEAM_ID'] == int(team_id)]
        player_names = team_players['PLAYER_NAME'].tolist()
        
        if debug:
            print(f"    DEBUG: Found {len(player_names)} players")
        
        return player_names
    
    except Exception as e:
        print(f"Error: {e}")
        return []

def get_hawks_player_ids(conn):
    """Get mapping of normalized column names to actual player names"""
    from nba_api.stats.endpoints import commonteamroster
    
    try:
        roster = commonteamroster.CommonTeamRoster(
            team_id=HAWKS_TEAM_ID,
            season='2025-26'
        )
        df = roster.get_data_frames()[0]
        
        # Map normalized name to player ID
        player_map = {}
        for _, row in df.iterrows():
            normalized = normalize_name(row['PLAYER'])
            player_map[normalized] = row['PLAYER_ID']
        
        return player_map
    except Exception as e:
        print(f"⚠️  Error fetching Hawks roster: {e}")
        return {}

def main():
    print("=" * 60)
    print("🏀 Filling Player Data for Atlanta Hawks")
    print("=" * 60)
    print()
    
    conn = psycopg2.connect(NEON_DSN)
    
    # Step 1: Get roster and games
    print("📋 Getting Hawks roster and schedule...")
    player_columns = get_hawks_roster(conn)
    games = get_hawks_games(conn)
    name_map = get_hawks_player_ids(conn)
    
    print(f"  → {len(player_columns)} players in roster")
    print(f"  → {len(games)} games to fill")
    print()
    
    # Step 2: For each game, get who played
    print("📊 Processing games...")
    cur = conn.cursor()
    
    for i, game_date in enumerate(games, 1):
        # Convert DB date to NBA API format
        db_date_str = game_date.strftime("%Y-%m-%d")
        nba_date_str = game_date.strftime("%b %d, %Y")  # Format: "Oct 22, 2025"
        
        print(f"  [{i}/{len(games)}] {db_date_str} (NBA format: {nba_date_str})...", end=" ")
        
        # Get who played in this game
        players_who_played = get_players_who_played_in_game(HAWKS_TEAM_ID, nba_date_str, debug=(i==1))
        
        # Normalize the names
        normalized_played = {normalize_name(name) for name in players_who_played}
        
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
    
    conn.commit()
    cur.close()
    conn.close()
    
    print()
    print("=" * 60)
    print("✅ Hawks player data filled!")
    print("=" * 60)

if __name__ == "__main__":
    main()
