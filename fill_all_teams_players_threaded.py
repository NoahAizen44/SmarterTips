"""
Fill Player Data for All NBA Teams (Threaded Version)
======================================================
Uses NBA API to fill player participation (TRUE/FALSE) for all 30 teams
Uses threading to process multiple teams concurrently
"""

import psycopg2
from nba_api.stats.endpoints import boxscoretraditionalv3, leaguegamefinder
from nba_api.stats.static import teams
import pandas as pd
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

# Thread-safe counter for progress tracking
progress_lock = threading.Lock()
teams_completed = 0
total_teams = 30

def normalize_name(name):
    """Convert player name to column name format"""
    return name.lower().replace(' ', '_').replace("'", '').replace('.', '').replace('-', '_')

def retry_with_backoff(func, max_retries=5, initial_delay=2):
    """Retry a function with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)
                time.sleep(delay)
            else:
                raise

def get_team_roster_columns(conn, schema_name):
    """Get list of player column names from team schedule table"""
    cur = conn.cursor()
    cur.execute(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = '{schema_name}' 
        AND table_name = 'schedule'
        AND column_name NOT IN ('game_date', 'game_id', 'opponent', 'home_away', 
                                 'result', 'team_score', 'opponent_score', 'created_at');
    """)
    player_columns = [row[0] for row in cur.fetchall()]
    cur.close()
    return player_columns

def process_team(team_data):
    """Process a single team - this function will be run in parallel"""
    team_idx, team = team_data
    team_id = team['id']
    team_name = team['full_name']
    schema_name = team_name.lower().replace(' ', '_')
    
    # Each thread gets its own database connection
    conn = psycopg2.connect(NEON_DSN)
    
    try:
        print(f"\n[{team_idx}/30] {team_name}")
        print("-" * 60)
        
        # Get player columns
        player_columns = get_team_roster_columns(conn, schema_name)
        print(f"  → {len(player_columns)} players in roster")
        
        # Get team games
        def fetch_games():
            games = leaguegamefinder.LeagueGameFinder(team_id_nullable=str(team_id))
            return games.get_data_frames()[0]
        
        games_df = retry_with_backoff(fetch_games, max_retries=5, initial_delay=3)
        
        # Filter for current season, Oct onwards
        games_df = games_df[games_df['SEASON_ID'] == '22025']
        games_df['GAME_DATE'] = pd.to_datetime(games_df['GAME_DATE'])
        games_df = games_df[games_df['GAME_DATE'] >= '2025-10-01']
        
        print(f"  → {len(games_df)} games to process")
        
        # Process each game
        cur = conn.cursor()
        games_with_data = 0
        
        for idx, game_row in games_df.iterrows():
            game_date = game_row['GAME_DATE']
            if isinstance(game_date, str):
                game_date = datetime.strptime(game_date, "%Y-%m-%d")
            db_date_str = game_date.strftime("%Y-%m-%d")
            game_id = str(game_row['GAME_ID'])
            
            # Check if this game exists in DB
            cur.execute(f"SELECT game_date FROM {schema_name}.schedule WHERE game_date = %s", (game_date,))
            if cur.fetchone() is None:
                continue
            
            # Show progress
            print(f"    Processing {db_date_str}...", end=" ", flush=True)
            
            # Get box score with retry
            try:
                def fetch_boxscore():
                    boxscore = boxscoretraditionalv3.BoxScoreTraditionalV3(game_id=game_id)
                    return boxscore.get_data_frames()[0]
                
                player_stats = retry_with_backoff(fetch_boxscore, max_retries=3, initial_delay=2)
                
                # Filter for this team's players
                team_players = player_stats[player_stats['teamId'] == team_id]
                
                # Build full names - only include players with minutes > 0
                players_who_played = []
                for _, p in team_players.iterrows():
                    # Check if player has minutes (format is "MM:SS" or empty)
                    minutes_str = str(p.get('minutes', '0:00'))
                    if minutes_str and minutes_str != '0:00' and minutes_str != 'nan':
                        full_name = f"{p['firstName']} {p['familyName']}"
                        players_who_played.append(full_name)
                
                # Normalize names
                normalized_played = {normalize_name(name) for name in players_who_played}
                
                # Set all to FALSE first
                set_all_false = ', '.join([f'"{col}" = FALSE' for col in player_columns])
                cur.execute(f"""
                    UPDATE {schema_name}.schedule
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
                        UPDATE {schema_name}.schedule
                        SET {', '.join(played_updates)}
                        WHERE game_date = %s;
                    """, (game_date,))
                    games_with_data += 1
                
                print(f"{len(played_updates)} players ✓")
                time.sleep(1.5)  # Rate limit between games
                
            except Exception as e:
                # Skip games with no box score data
                print(f"skipped")
                time.sleep(1)
                continue
        
        conn.commit()
        cur.close()
        print(f"  ✅ Filled {games_with_data}/{len(games_df)} games with player data")
        
        # Update global progress counter
        global teams_completed
        with progress_lock:
            teams_completed += 1
            print(f"\n  📊 Overall progress: {teams_completed}/{total_teams} teams completed")
        
        return (team_name, games_with_data, None)
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return (team_name, 0, str(e))
    finally:
        conn.close()
        time.sleep(2)  # Wait between teams

def main():
    print("=" * 60)
    print("🏀 Filling Player Data for All NBA Teams (Threaded)")
    print("=" * 60)
    print()
    
    # Get all NBA teams
    all_teams = teams.get_teams()
    sorted_teams = sorted(all_teams, key=lambda x: x['full_name'])
    
    # Start from Orlando Magic (team 22)
    start_index = None
    for idx, team in enumerate(sorted_teams):
        if team['full_name'] == 'Orlando Magic':
            start_index = idx
            break
    
    if start_index is not None:
        sorted_teams = sorted_teams[start_index:]
    
    # Create list of (index, team) tuples for processing
    team_data = [(idx, team) for idx, team in enumerate(sorted_teams, 1)]
    
    # Process teams concurrently with 3 threads
    # (3 is a safe number to avoid rate limiting while getting speedup)
    total_games = 0
    errors = []
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all team processing jobs
        future_to_team = {executor.submit(process_team, td): td[1]['full_name'] 
                         for td in team_data}
        
        # Collect results as they complete
        for future in as_completed(future_to_team):
            team_name = future_to_team[future]
            try:
                result = future.result()
                if result:
                    team, games, error = result
                    if error is None:
                        total_games += games
                    else:
                        errors.append((team, error))
            except Exception as e:
                errors.append((team_name, str(e)))
    
    print()
    print("=" * 60)
    print(f"✅ Complete! Processed {total_games} total games")
    
    if errors:
        print("\n⚠️  Errors encountered:")
        for team, error in errors:
            print(f"  - {team}: {error}")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
