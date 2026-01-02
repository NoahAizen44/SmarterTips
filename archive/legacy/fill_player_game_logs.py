"""
Fill Player Game Logs for All NBA Teams
========================================
Uses NBA API to fetch detailed game stats for all players across all games
"""

import psycopg2
from nba_api.stats.endpoints import playergamelogs
from nba_api.stats.static import teams, players
import pandas as pd
import time
from datetime import datetime

NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

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
                print(f"\n    ⚠️  Timeout, retrying in {delay}s (attempt {attempt + 1}/{max_retries})...", flush=True)
                time.sleep(delay)
            else:
                raise

def main():
    print("=" * 70)
    print("🏀 Fetching Player Game Logs for All NBA Teams")
    print("=" * 70)
    print()
    
    # Get all NBA teams
    all_teams = teams.get_teams()
    
    # Connect to DB
    conn = psycopg2.connect(NEON_DSN)
    cur = conn.cursor()
    
    total_players_processed = 0
    total_games_logged = 0
    
    for team_idx, team in enumerate(sorted(all_teams, key=lambda x: x['full_name']), 1):
        team_id = team['id']
        team_name = team['full_name']
        schema_name = team_name.lower().replace(' ', '_')
        
        print(f"\n[{team_idx}/30] {team_name}")
        print("-" * 70)
        
        try:
            # Get all unique players from team's schedule table
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
            print(f"  → {len(player_columns)} players in roster")
            
            # Convert column names back to player names
            player_names = [col.replace('_', ' ').title() for col in player_columns]
            
            # Get player game logs for each player
            games_logged_this_team = 0
            
            for player_idx, (player_col, player_name) in enumerate(zip(player_columns, player_names), 1):
                try:
                    # Try to get player ID from nba_api
                    print(f"    [{player_idx}/{len(player_columns)}] {player_name}...", end=" ", flush=True)
                    
                    def fetch_player_logs():
                        player_logs = playergamelogs.PlayerGameLogs(
                            team_id_nullable=str(team_id),
                            season_nullable='2025'
                        )
                        return player_logs.get_data_frames()[0]
                    
                    logs_df = retry_with_backoff(fetch_player_logs, max_retries=3, initial_delay=2)
                    
                    # Filter for this player
                    player_logs = logs_df[logs_df['PLAYER_NAME'].str.lower() == player_name.lower()]
                    
                    if len(player_logs) > 0:
                        print(f"{len(player_logs)} games ✓")
                        
                        # Create player_game_logs table if it doesn't exist
                        cur.execute(f"""
                            CREATE TABLE IF NOT EXISTS {schema_name}.player_game_logs (
                                id SERIAL PRIMARY KEY,
                                player_name VARCHAR(255),
                                game_date DATE,
                                opponent VARCHAR(100),
                                minutes FLOAT,
                                points INT,
                                rebounds INT,
                                assists INT,
                                steals INT,
                                blocks INT,
                                turnovers INT,
                                field_goals_made INT,
                                field_goals_attempted INT,
                                three_pointers_made INT,
                                three_pointers_attempted INT,
                                free_throws_made INT,
                                free_throws_attempted INT,
                                plus_minus FLOAT,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                UNIQUE(player_name, game_date)
                            )
                        """)
                        
                        # Insert player game logs
                        for _, log in player_logs.iterrows():
                            game_date = pd.to_datetime(log['GAME_DATE']).date()
                            
                            cur.execute(f"""
                                INSERT INTO {schema_name}.player_game_logs 
                                (player_name, game_date, opponent, minutes, points, rebounds, assists, 
                                 steals, blocks, turnovers, field_goals_made, field_goals_attempted,
                                 three_pointers_made, three_pointers_attempted, free_throws_made, 
                                 free_throws_attempted, plus_minus)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (player_name, game_date) DO UPDATE SET
                                    opponent = EXCLUDED.opponent,
                                    minutes = EXCLUDED.minutes,
                                    points = EXCLUDED.points,
                                    rebounds = EXCLUDED.rebounds,
                                    assists = EXCLUDED.assists,
                                    steals = EXCLUDED.steals,
                                    blocks = EXCLUDED.blocks,
                                    turnovers = EXCLUDED.turnovers,
                                    field_goals_made = EXCLUDED.field_goals_made,
                                    field_goals_attempted = EXCLUDED.field_goals_attempted,
                                    three_pointers_made = EXCLUDED.three_pointers_made,
                                    three_pointers_attempted = EXCLUDED.three_pointers_attempted,
                                    free_throws_made = EXCLUDED.free_throws_made,
                                    free_throws_attempted = EXCLUDED.free_throws_attempted,
                                    plus_minus = EXCLUDED.plus_minus
                            """, (
                                player_name,
                                game_date,
                                log.get('MATCHUP', ''),
                                log.get('MIN', 0),
                                log.get('PTS', 0),
                                log.get('REB', 0),
                                log.get('AST', 0),
                                log.get('STL', 0),
                                log.get('BLK', 0),
                                log.get('TOV', 0),
                                log.get('FGM', 0),
                                log.get('FGA', 0),
                                log.get('FG3M', 0),
                                log.get('FG3A', 0),
                                log.get('FTM', 0),
                                log.get('FTA', 0),
                                log.get('PLUS_MINUS', 0)
                            ))
                        
                        games_logged_this_team += len(player_logs)
                        total_games_logged += len(player_logs)
                    else:
                        print("0 games")
                    
                    time.sleep(0.5)  # Rate limit between players
                    
                except Exception as e:
                    print(f"error: {str(e)[:50]}")
                    time.sleep(0.5)
                    continue
            
            conn.commit()
            total_players_processed += len(player_columns)
            print(f"  ✅ Logged {games_logged_this_team} player games")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            time.sleep(5)
            continue
        
        time.sleep(3)  # Longer wait between teams
    
    cur.close()
    conn.close()
    
    print()
    print("=" * 70)
    print(f"✅ Complete! Processed {total_players_processed} players")
    print(f"📊 Total: {total_games_logged} player game logs recorded")
    print("=" * 70)

if __name__ == "__main__":
    main()
