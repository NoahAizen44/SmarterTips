"""
Fix Hyphenated Player Names Usage Data
========================================
Finds players with hyphens in their names and re-fills their usage data
by properly matching NBA API names (with hyphens) to schedule columns (with underscores)
"""

import psycopg2
from nba_api.stats.endpoints import boxscoreadvancedv3, leaguegamefinder
from nba_api.stats.static import teams
import pandas as pd
import time

NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

def normalize_name(name):
    """Convert player name to table name format (lowercase, replace spaces/hyphens with underscores)"""
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

def find_hyphenated_players():
    """Find all players across all teams who have hyphens in their NBA API names"""
    print("🔍 Scanning all teams for hyphenated player names...")
    print()
    
    conn = psycopg2.connect(NEON_DSN)
    cur = conn.cursor()
    
    all_teams = teams.get_teams()
    hyphenated_players = []
    
    for team in sorted(all_teams, key=lambda x: x['full_name']):
        team_id = team['id']
        team_name = team['full_name']
        schema_name = team_name.lower().replace(' ', '_')
        
        try:
            # Get one recent game for this team
            def fetch_games():
                games = leaguegamefinder.LeagueGameFinder(team_id_nullable=str(team_id))
                return games.get_data_frames()[0]
            
            games_df = retry_with_backoff(fetch_games, max_retries=3, initial_delay=2)
            games_df = games_df[games_df['SEASON_ID'] == '22025']
            games_df['GAME_DATE'] = pd.to_datetime(games_df['GAME_DATE'])
            games_df = games_df[games_df['GAME_DATE'] >= '2025-10-01']
            
            if len(games_df) == 0:
                continue
            
            # Get most recent game
            game_id = str(games_df.iloc[0]['GAME_ID'])
            
            # Get advanced box score
            def fetch_advanced():
                adv_box = boxscoreadvancedv3.BoxScoreAdvancedV3(game_id=game_id)
                return adv_box.get_data_frames()[0]
            
            adv_df = retry_with_backoff(fetch_advanced, max_retries=3, initial_delay=2)
            team_players = adv_df[adv_df['teamId'] == team_id]
            
            # Check each player for hyphens
            for _, player in team_players.iterrows():
                player_name = f"{player['firstName']} {player['familyName']}"
                
                if '-' in player_name:
                    # Check if this player's usage table exists and is incomplete
                    table_name = normalize_name(player_name)
                    
                    cur.execute(f"""
                        SELECT COUNT(*) 
                        FROM information_schema.tables 
                        WHERE table_schema = '{schema_name}' 
                        AND table_name = '{table_name}'
                    """)
                    
                    if cur.fetchone()[0] > 0:
                        # Check how many rows in usage table
                        cur.execute(f"""
                            SELECT COUNT(*) FROM {schema_name}.{table_name}
                        """)
                        usage_count = cur.fetchone()[0]
                        
                        # Check how many games marked TRUE in schedule
                        column_name = normalize_name(player_name)
                        cur.execute(f"""
                            SELECT COUNT(*) 
                            FROM {schema_name}.schedule 
                            WHERE {column_name} = TRUE
                        """)
                        true_count = cur.fetchone()[0]
                        
                        if usage_count < true_count:
                            hyphenated_players.append({
                                'team_id': team_id,
                                'team_name': team_name,
                                'schema_name': schema_name,
                                'player_name': player_name,
                                'table_name': table_name,
                                'column_name': column_name,
                                'usage_count': usage_count,
                                'true_count': true_count,
                                'missing': true_count - usage_count
                            })
                            print(f"  Found: {player_name} ({team_name}) - {usage_count}/{true_count} games filled")
            
            time.sleep(1)
            
        except Exception as e:
            print(f"  ⚠️  {team_name}: {e}")
            time.sleep(1)
            continue
    
    cur.close()
    conn.close()
    
    return hyphenated_players

def fix_player_usage(player_info):
    """Re-fill usage data for a specific hyphenated player"""
    team_id = player_info['team_id']
    team_name = player_info['team_name']
    schema_name = player_info['schema_name']
    player_name = player_info['player_name']
    table_name = player_info['table_name']
    
    print(f"\n📝 Fixing: {player_name} ({team_name})")
    print("-" * 70)
    
    conn = psycopg2.connect(NEON_DSN)
    cur = conn.cursor()
    
    try:
        # Get team games
        def fetch_games():
            games = leaguegamefinder.LeagueGameFinder(team_id_nullable=str(team_id))
            return games.get_data_frames()[0]
        
        games_df = retry_with_backoff(fetch_games, max_retries=5, initial_delay=3)
        games_df = games_df[games_df['SEASON_ID'] == '22025']
        games_df['GAME_DATE'] = pd.to_datetime(games_df['GAME_DATE'])
        games_df = games_df[games_df['GAME_DATE'] >= '2025-10-01']
        
        print(f"  → {len(games_df)} games to check")
        
        inserted = 0
        skipped = 0
        
        # Process each game
        for idx, game_row in games_df.iterrows():
            game_id = str(game_row['GAME_ID'])
            game_date = game_row['GAME_DATE'].date()
            
            try:
                # Get advanced box score with usage
                def fetch_advanced():
                    adv_box = boxscoreadvancedv3.BoxScoreAdvancedV3(game_id=game_id)
                    return adv_box.get_data_frames()[0]
                
                adv_df = retry_with_backoff(fetch_advanced, max_retries=3, initial_delay=2)
                
                # Filter for this team's players
                team_players = adv_df[adv_df['teamId'] == team_id]
                
                # Find our specific player (match by name with hyphen)
                player_row = None
                for _, p in team_players.iterrows():
                    api_name = f"{p['firstName']} {p['familyName']}"
                    if api_name == player_name:
                        player_row = p
                        break
                
                if player_row is not None:
                    usage_pct = player_row['usagePercentage'] * 100
                    
                    # Convert minutes from MM:SS to decimal
                    minutes_played = 0
                    if player_row['minutes']:
                        time_parts = str(player_row['minutes']).split(':')
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
                    print(f"    {game_date}: {minutes_played:.1f} min, {usage_pct:.1f}% usage ✓")
                else:
                    skipped += 1
                
                conn.commit()
                time.sleep(1.5)  # Rate limit
                
            except Exception as e:
                print(f"    {game_date}: Error - {e}")
                time.sleep(1)
                continue
        
        print(f"  ✅ Inserted/updated {inserted} games, {skipped} games player didn't play")
        
        # Verify final count
        cur.execute(f"SELECT COUNT(*) FROM {schema_name}.{table_name}")
        final_count = cur.fetchone()[0]
        print(f"  📊 Final usage table count: {final_count} rows")
        
        return inserted
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return 0
    finally:
        cur.close()
        conn.close()

def main():
    print("=" * 70)
    print("🔧 Fix Hyphenated Player Names Usage Data")
    print("=" * 70)
    print()
    
    # Find all hyphenated players with incomplete data
    hyphenated_players = find_hyphenated_players()
    
    if not hyphenated_players:
        print("\n✅ No hyphenated players with missing usage data found!")
        return
    
    print()
    print("=" * 70)
    print(f"Found {len(hyphenated_players)} hyphenated players with missing data:")
    for p in hyphenated_players:
        print(f"  • {p['player_name']} ({p['team_name']}) - missing {p['missing']} games")
    print("=" * 70)
    
    # Fix each player
    total_fixed = 0
    for player_info in hyphenated_players:
        fixed = fix_player_usage(player_info)
        total_fixed += fixed
        time.sleep(2)  # Wait between players
    
    print()
    print("=" * 70)
    print(f"✅ Complete! Fixed {total_fixed} total game records")
    print("=" * 70)

if __name__ == "__main__":
    main()
