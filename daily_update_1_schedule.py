"""
Daily Update Script #1: Update Team Schedules
==============================================
Checks for games played today and updates schedule tables with:
- Game results (score, opponent, home/away)
- Player participation (TRUE if in box score with minutes > 0, FALSE otherwise)

Run this FIRST before daily_update_2_usage.py
"""

import psycopg2
from nba_api.stats.endpoints import boxscoretraditionalv3, leaguegamefinder
from nba_api.stats.static import teams
import pandas as pd
import time
import os
from datetime import datetime, date, timedelta

# Get database connection from environment variable or use default
NEON_DSN = os.environ.get('NEON_DSN', "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require")

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
                print(f"    Retry {attempt + 1}/{max_retries} after {delay}s...")
                time.sleep(delay)
            else:
                raise

def update_team_schedule(team, target_date):
    """Update schedule for a specific team for a specific date"""
    team_id = team['id']
    team_name = team['full_name']
    schema_name = team_name.lower().replace(' ', '_')
    
    conn = psycopg2.connect(NEON_DSN)
    cur = conn.cursor()
    
    try:
        # Check if this date already has complete data in schedule
        cur.execute(f"""
            SELECT game_id, result 
            FROM {schema_name}.schedule 
            WHERE game_date = %s
        """, (target_date,))
        
        existing = cur.fetchone()
        if existing and existing[1]:  # If result is already filled
            print(f"  ✓ Already updated")
            cur.close()
            conn.close()
            return 0
        
        # Get games for this team on this date
        def fetch_games():
            games = leaguegamefinder.LeagueGameFinder(
                team_id_nullable=str(team_id),
                date_from_nullable=target_date.strftime('%m/%d/%Y'),
                date_to_nullable=target_date.strftime('%m/%d/%Y')
            )
            return games.get_data_frames()[0]
        
        games_df = retry_with_backoff(fetch_games, max_retries=3, initial_delay=2)
        
        if len(games_df) == 0:
            print(f"  - No game today")
            cur.close()
            conn.close()
            return 0
        
        game_row = games_df.iloc[0]
        game_id = str(game_row['GAME_ID'])
        game_date = pd.to_datetime(game_row['GAME_DATE']).date()
        
        # Get box score to determine player participation
        def fetch_box_score():
            box = boxscoretraditionalv3.BoxScoreTraditionalV3(game_id=game_id)
            return box.get_data_frames()[0]
        
        box_df = retry_with_backoff(fetch_box_score, max_retries=3, initial_delay=2)
        
        # Get players from this team who played (minutes > 0)
        team_players = box_df[box_df['teamId'] == team_id]
        players_who_played = set()
        
        for _, player in team_players.iterrows():
            minutes_str = str(player['minutes']) if player['minutes'] else '0:00'
            if minutes_str != '0:00':
                player_name = f"{player['firstName']} {player['familyName']}"
                column_name = normalize_name(player_name)
                players_who_played.add(column_name)
        
        # Get all player columns from schedule table
        cur.execute(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = '{schema_name}' 
            AND table_name = 'schedule'
            AND column_name NOT IN ('game_date', 'game_id', 'opponent', 'home_away', 
                                     'result', 'team_score', 'opponent_score', 'created_at')
        """)
        
        all_player_columns = [row[0] for row in cur.fetchall()]
        
        # Build UPDATE statement to set all player columns
        update_parts = []
        for col in all_player_columns:
            if col in players_who_played:
                update_parts.append(f"{col} = TRUE")
            else:
                update_parts.append(f"{col} = FALSE")
        
        # Determine opponent, home/away, result
        matchup = game_row['MATCHUP']
        if ' @ ' in matchup:
            home_away = 'Away'
            opponent = matchup.split(' @ ')[1]
        else:
            home_away = 'Home'
            opponent = matchup.split(' vs. ')[1]
        
        team_score = int(game_row['PTS'])
        
        # Get opponent score from the game
        opp_team_id = [t['id'] for t in teams.get_teams() if t['abbreviation'] == opponent][0]
        opp_score_row = box_df[box_df['teamId'] == opp_team_id].iloc[0] if len(box_df[box_df['teamId'] == opp_team_id]) > 0 else None
        
        if opp_score_row is not None:
            opponent_score = int(box_df[box_df['teamId'] == opp_team_id]['points'].sum())
        else:
            opponent_score = 0
        
        result = 'W' if team_score > opponent_score else 'L'
        
        # Update the row
        update_sql = f"""
            UPDATE {schema_name}.schedule
            SET result = %s,
                team_score = %s,
                opponent_score = %s,
                opponent = %s,
                home_away = %s,
                {', '.join(update_parts)}
            WHERE game_date = %s
        """
        
        cur.execute(update_sql, (result, team_score, opponent_score, opponent, home_away, game_date))
        conn.commit()
        
        print(f"  ✅ Updated: {result} {team_score}-{opponent_score} vs {opponent} ({len(players_who_played)} players)")
        
        cur.close()
        conn.close()
        return 1
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        cur.close()
        conn.close()
        return 0

def main():
    # Use yesterday's date to capture all games that finished
    # Since script runs at 2 AM EST, yesterday's games are all complete
    target_date = date.today() - timedelta(days=1)
    
    print("=" * 70)
    print(f"📅 Daily Update #1: Team Schedules for {target_date}")
    print("=" * 70)
    print()
    
    all_teams = teams.get_teams()
    teams_updated = 0
    
    for idx, team in enumerate(sorted(all_teams, key=lambda x: x['full_name']), 1):
        team_name = team['full_name']
        print(f"[{idx}/30] {team_name}...", end=" ", flush=True)
        
        result = update_team_schedule(team, target_date)
        teams_updated += result
        
        time.sleep(1.5)  # Rate limit
    
    print()
    print("=" * 70)
    print(f"✅ Complete! Updated {teams_updated} team schedules")
    print("=" * 70)

if __name__ == "__main__":
    main()
