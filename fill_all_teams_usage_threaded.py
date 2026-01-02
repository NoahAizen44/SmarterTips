"""
Fill Player Usage Tables for All NBA Teams (Threaded Version)
===============================================================
Uses BoxScoreAdvancedV3 to get real NBA usage percentage for every player
Uses threading to process multiple teams concurrently
"""

import psycopg2
from nba_api.stats.endpoints import boxscoreadvancedv3, leaguegamefinder
from nba_api.stats.static import teams
import pandas as pd
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

# Thread-safe counter for progress tracking
progress_lock = threading.Lock()
teams_completed = 0
total_teams = 30

def normalize_name(name):
    """Convert player name to table name format"""
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

def process_team(team_data):
    """Process a single team - this function will be run in parallel"""
    team_idx, team = team_data
    team_id = team['id']
    team_name = team['full_name']
    schema_name = team_name.lower().replace(' ', '_')
    
    # Each thread gets its own database connection.
    # Neon can occasionally time out; retry with backoff so one transient issue
    # doesn't cause a whole team to fail (e.g., Knicks).
    conn = retry_with_backoff(lambda: psycopg2.connect(NEON_DSN), max_retries=5, initial_delay=2)
    cur = conn.cursor()
    
    try:
        print(f"\n[{team_idx}/30] {team_name}")
        print("-" * 70)
        
        # Get player columns from team schedule table (roster source of truth)
        cur.execute(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = '{schema_name}' 
            AND table_name = 'schedule'
            AND column_name NOT IN ('game_date', 'game_id', 'opponent', 'home_away', 
                                     'result', 'team_score', 'opponent_score', 'created_at')
            ORDER BY column_name
        """)

        player_columns = [row[0] for row in cur.fetchall()]
        # Use normalized roster keys (column/table name style) for matching.
        # This avoids name formatting mismatches like "Jr" vs "Jr.".
        roster_keys = set(player_columns)

        print(f"  → {len(roster_keys)} players in roster")
        
        # Get team games
        def fetch_games():
            games = leaguegamefinder.LeagueGameFinder(team_id_nullable=str(team_id))
            return games.get_data_frames()[0]
        
        games_df = retry_with_backoff(fetch_games, max_retries=5, initial_delay=3)
        games_df = games_df[games_df['SEASON_ID'] == '22025']
        games_df['GAME_DATE'] = pd.to_datetime(games_df['GAME_DATE'])
        games_df = games_df[games_df['GAME_DATE'] >= '2025-10-01']
        
        print(f"  → {len(games_df)} games to process")
        
        games_processed = 0
        
        # Process each game
        for idx, game_row in games_df.iterrows():
            game_id = str(game_row['GAME_ID'])
            game_date = game_row['GAME_DATE'].date()
            
            print(f"    {game_date}...", end=" ", flush=True)
            
            try:
                # Get advanced box score with usage
                def fetch_advanced():
                    adv_box = boxscoreadvancedv3.BoxScoreAdvancedV3(game_id=game_id)
                    return adv_box.get_data_frames()[0]
                
                # NBA API can be flaky; retry a bit more aggressively to avoid silent gaps.
                adv_df = retry_with_backoff(fetch_advanced, max_retries=6, initial_delay=2)
                
                # Filter for this team's players
                team_players = adv_df[adv_df['teamId'] == team_id]
                
                # Insert usage for each player
                inserted = 0
                for _, player in team_players.iterrows():
                    player_name = f"{player['firstName']} {player['familyName']}"

                    # Only insert if player is in our roster (normalize before matching)
                    table_name = normalize_name(player_name)
                    if table_name not in roster_keys:
                        continue
                    
                    usage_pct = player['usagePercentage'] * 100
                    
                    # Convert minutes from MM:SS to decimal
                    minutes_played = 0
                    if player['minutes']:
                        time_parts = str(player['minutes']).split(':')
                        if len(time_parts) == 2:
                            minutes_played = int(time_parts[0]) + int(time_parts[1])/60
                    
                    cur.execute(f"""
                        INSERT INTO {schema_name}.{table_name} (game_date, minutes, usage_percentage)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (game_date) DO UPDATE SET
                            minutes = EXCLUDED.minutes,
                            usage_percentage = EXCLUDED.usage_percentage
                    """, (game_date, minutes_played, usage_pct))
                    inserted += 1
                
                conn.commit()
                games_processed += 1
                print(f"{inserted} players ✓")
                time.sleep(1.5)  # Rate limit
                
            except Exception as e:
                print(f"skipped ({type(e).__name__})")
                time.sleep(1)
                continue

        print(f"  ✅ Filled {len(roster_keys)} player usage tables ({games_processed} games)")

        # Update global progress counter
        global teams_completed
        with progress_lock:
            teams_completed += 1
            print(f"\n  📊 Overall progress: {teams_completed}/{total_teams} teams completed")

        return (team_name, games_processed, None)
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return (team_name, 0, str(e))
    finally:
        cur.close()
        conn.close()
        time.sleep(2)  # Wait between teams

def main():
    print("=" * 70)
    print("🏀 Filling Player Usage Tables for All NBA Teams (Threaded)")
    print("=" * 70)
    print()
    
    # Get all NBA teams
    all_teams = teams.get_teams()
    sorted_teams = sorted(all_teams, key=lambda x: x['full_name'])
    
    # Optional controls:
    # - LIMIT_TEAMS: run only these team full names
    # - RESUME_FROM_TEAM: start from this team (inclusive) in alphabetical order
    # Example:
    #   LIMIT_TEAMS = ['Brooklyn Nets']
    #   RESUME_FROM_TEAM = 'Portland Trail Blazers'
    LIMIT_TEAMS = None
    RESUME_FROM_TEAM = 'Portland Trail Blazers'

    if LIMIT_TEAMS:
        sorted_teams = [t for t in sorted_teams if t['full_name'] in LIMIT_TEAMS]
    elif RESUME_FROM_TEAM:
        sorted_teams = [t for t in sorted_teams if t['full_name'] >= RESUME_FROM_TEAM]

    global total_teams
    total_teams = len(sorted_teams)
    
    # Create list of (index, team) tuples for processing
    team_data = [(idx, team) for idx, team in enumerate(sorted_teams, 1)]
    
    # Process teams concurrently with 3 threads
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
    print("=" * 70)
    print(f"✅ Complete! Processed {total_games} total games")
    
    if errors:
        print("\n⚠️  Errors encountered:")
        for team, error in errors:
            print(f"  - {team}: {error}")
    
    print("=" * 70)

if __name__ == "__main__":
    main()
