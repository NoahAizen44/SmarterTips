"""
Fill Player Usage Tables for All NBA Teams
===========================================
Uses BoxScoreAdvancedV3 to get real NBA usage percentage for every player
"""

import psycopg2
from nba_api.stats.endpoints import boxscoreadvancedv3, leaguegamefinder
from nba_api.stats.static import teams
import pandas as pd
import time

NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

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
                print(f"\n    ⚠️  Timeout, retrying in {delay}s (attempt {attempt + 1}/{max_retries})...", flush=True)
                time.sleep(delay)
            else:
                raise

def main():
    print("=" * 70)
    print("🏀 Filling Player Usage Tables for All NBA Teams")
    print("=" * 70)
    print()
    
    # Get all NBA teams
    all_teams = teams.get_teams()
    
    # Connect to DB
    conn = psycopg2.connect(NEON_DSN)
    cur = conn.cursor()
    
    total_tables_created = 0
    total_games_processed = 0
    
    for team_idx, team in enumerate(sorted(all_teams, key=lambda x: x['full_name']), 1):
        team_id = team['id']
        team_name = team['full_name']
        schema_name = team_name.lower().replace(' ', '_')
        
        print(f"\n[{team_idx}/30] {team_name}")
        print("-" * 70)
        
        try:
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
            players = [col.replace('_', ' ').title() for col in player_columns]
            
            print(f"  → {len(players)} players in roster")
            
            # Create usage tables for each player
            for player_name in players:
                table_name = f"{normalize_name(player_name)}_usage"
                cur.execute(f"DROP TABLE IF EXISTS {schema_name}.{table_name} CASCADE")
                cur.execute(f"""
                    CREATE TABLE {schema_name}.{table_name} (
                        id SERIAL PRIMARY KEY,
                        game_date DATE NOT NULL UNIQUE,
                        minutes FLOAT,
                        usage_percentage FLOAT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                total_tables_created += 1
            
            conn.commit()
            
            # Get team games
            def fetch_games():
                games = leaguegamefinder.LeagueGameFinder(team_id_nullable=str(team_id))
                return games.get_data_frames()[0]
            
            games_df = retry_with_backoff(fetch_games, max_retries=5, initial_delay=3)
            games_df = games_df[games_df['SEASON_ID'] == '22025']
            games_df['GAME_DATE'] = pd.to_datetime(games_df['GAME_DATE'])
            games_df = games_df[games_df['GAME_DATE'] >= '2025-10-01']
            
            print(f"  → {len(games_df)} games to process")
            print()
            
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
                    
                    adv_df = retry_with_backoff(fetch_advanced, max_retries=3, initial_delay=2)
                    
                    # Filter for this team's players
                    team_players = adv_df[adv_df['teamId'] == team_id]
                    
                    # Insert usage for each player
                    inserted = 0
                    for _, player in team_players.iterrows():
                        player_name = f"{player['firstName']} {player['familyName']}"
                        
                        # Only insert if player is in our roster
                        if player_name not in players:
                            continue
                        
                        usage_pct = player['usagePercentage'] * 100
                        
                        # Convert minutes from MM:SS to decimal
                        minutes_played = 0
                        if player['minutes']:
                            time_parts = str(player['minutes']).split(':')
                            if len(time_parts) == 2:
                                minutes_played = int(time_parts[0]) + int(time_parts[1])/60
                        
                        table_name = f"{normalize_name(player_name)}_usage"
                        
                        cur.execute(f"""
                            INSERT INTO {schema_name}.{table_name} (game_date, minutes, usage_percentage)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (game_date) DO UPDATE SET
                                minutes = EXCLUDED.minutes,
                                usage_percentage = EXCLUDED.usage_percentage
                        """, (game_date, minutes_played, usage_pct))
                        inserted += 1
                    
                    conn.commit()
                    total_games_processed += 1
                    print(f"✅ {inserted} players")
                    time.sleep(1.5)  # Rate limit
                    
                except Exception as e:
                    print(f"❌ {str(e)[:40]}")
                    time.sleep(1)
                    continue
            
            print(f"  ✅ Filled {len(players)} player usage tables")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            time.sleep(5)
            continue
        
        time.sleep(3)  # Rate limit between teams
    
    cur.close()
    conn.close()
    
    print()
    print("=" * 70)
    print(f"✅ Complete! Created {total_tables_created} usage tables")
    print(f"📊 Processed {total_games_processed} games")
    print("=" * 70)

if __name__ == "__main__":
    main()
