"""
Daily Update Script #2: Update Player Usage Tables
===================================================
Checks for new games in schedule table and adds usage data for each player:
- If player was TRUE in schedule: fetch real usage data from NBA API
- If player was FALSE in schedule: add DNP row (0 minutes, 0 usage)

Run this SECOND after daily_update_1_schedule.py
"""

import psycopg2
from nba_api.stats.endpoints import boxscoreadvancedv3
from nba_api.stats.static import teams
import time
import os
from datetime import datetime, date, timedelta

# Get database connection from environment variable or use default
NEON_DSN = os.environ.get('NEON_DSN', "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require")

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
                print(f"    Retry {attempt + 1}/{max_retries} after {delay}s...")
                time.sleep(delay)
            else:
                raise

def update_team_usage(team, target_date):
    """Update usage tables for a specific team for a specific date"""
    team_id = team['id']
    team_name = team['full_name']
    schema_name = team_name.lower().replace(' ', '_')
    
    conn = psycopg2.connect(NEON_DSN)
    cur = conn.cursor()
    
    try:
        # Check if this team played today and get game info
        cur.execute(f"""
            SELECT game_id, result
            FROM {schema_name}.schedule 
            WHERE game_date = %s
        """, (target_date,))
        
        game_row = cur.fetchone()
        
        if not game_row:
            print(f"  - No game scheduled")
            cur.close()
            conn.close()
            return 0
        
        game_id, result = game_row
        
        if not result:
            print(f"  ⚠️  Game exists but not yet updated in schedule table")
            cur.close()
            conn.close()
            return 0
        
        # Get all player columns
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
        
        # Get which players were TRUE (played) and FALSE (DNP)
        cur.execute(f"""
            SELECT {', '.join(player_columns)}
            FROM {schema_name}.schedule
            WHERE game_date = %s
        """, (target_date,))
        
        player_statuses = cur.fetchone()
        players_played = []
        players_dnp = []
        
        for idx, col in enumerate(player_columns):
            if player_statuses[idx]:
                players_played.append(col)
            else:
                players_dnp.append(col)
        
        # Fetch advanced box score for players who played
        if players_played:
            try:
                def fetch_advanced():
                    adv_box = boxscoreadvancedv3.BoxScoreAdvancedV3(game_id=game_id)
                    return adv_box.get_data_frames()[0]
                
                adv_df = retry_with_backoff(fetch_advanced, max_retries=3, initial_delay=2)
                team_players = adv_df[adv_df['teamId'] == team_id]
                
                # Insert usage for players who played
                for _, player in team_players.iterrows():
                    player_name = f"{player['firstName']} {player['familyName']}"
                    table_name = normalize_name(player_name)
                    
                    # Check if this player's table exists
                    cur.execute(f"""
                        SELECT COUNT(*) 
                        FROM information_schema.tables 
                        WHERE table_schema = '{schema_name}' 
                        AND table_name = '{table_name}'
                    """)
                    
                    if cur.fetchone()[0] == 0:
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
                    """, (target_date, minutes_played, usage_pct))
                
                conn.commit()
                
            except Exception as e:
                print(f"  ⚠️  Error fetching box score: {e}")
        
        # Add DNP entries (0 minutes, 0 usage) for players who didn't play
        dnp_added = 0
        for player_col in players_dnp:
            table_name = player_col
            
            # Check if table exists
            cur.execute(f"""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = '{schema_name}' 
                AND table_name = '{table_name}'
            """)
            
            if cur.fetchone()[0] == 0:
                continue
            
            # Check if this date already exists
            cur.execute(f"""
                SELECT COUNT(*) 
                FROM {schema_name}.{table_name}
                WHERE game_date = %s
            """, (target_date,))
            
            if cur.fetchone()[0] == 0:
                cur.execute(f"""
                    INSERT INTO {schema_name}.{table_name} (game_date, minutes, usage_percentage)
                    VALUES (%s, 0, 0)
                """, (target_date,))
                dnp_added += 1
        
        conn.commit()
        
        print(f"  ✅ Updated: {len(players_played)} played, {dnp_added} DNP added")
        
        cur.close()
        conn.close()
        return 1
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        cur.close()
        conn.close()
        return 0

def main():
    # Use yesterday's date (to capture all completed games regardless of timezone)
    target_date = date.today() - timedelta(days=1)
    
    print("=" * 70)
    print(f"📊 Daily Update #2: Player Usage Tables for {target_date}")
    print("=" * 70)
    print()
    
    all_teams = teams.get_teams()
    teams_updated = 0
    
    for idx, team in enumerate(sorted(all_teams, key=lambda x: x['full_name']), 1):
        team_name = team['full_name']
        print(f"[{idx}/30] {team_name}...", end=" ", flush=True)
        
        result = update_team_usage(team, target_date)
        teams_updated += result
        
        time.sleep(1.5)  # Rate limit
    
    print()
    print("=" * 70)
    print(f"✅ Complete! Updated usage tables for {teams_updated} teams")
    print("=" * 70)

if __name__ == "__main__":
    main()
