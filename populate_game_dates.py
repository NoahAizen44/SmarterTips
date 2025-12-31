"""
Populate Game Dates for Team Schedules
=======================================
Fetches games that have been played so far this season (2025-26)
and inserts them into each team's schedule table
"""

import psycopg2
import requests
import time
from datetime import datetime

# Neon connection
NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"
API_SPORTS_KEY = "bae6a6dbb611f615fed183ef2412bbe3"

# NBA Teams (API-Sports IDs for 2025-2026)
NBA_TEAMS = {
    'atlanta_hawks': {'api_sports_id': 132, 'name': 'Atlanta Hawks'},
    'boston_celtics': {'api_sports_id': 133, 'name': 'Boston Celtics'},
    'brooklyn_nets': {'api_sports_id': 134, 'name': 'Brooklyn Nets'},
    'charlotte_hornets': {'api_sports_id': 135, 'name': 'Charlotte Hornets'},
    'chicago_bulls': {'api_sports_id': 136, 'name': 'Chicago Bulls'},
    'cleveland_cavaliers': {'api_sports_id': 137, 'name': 'Cleveland Cavaliers'},
    'dallas_mavericks': {'api_sports_id': 138, 'name': 'Dallas Mavericks'},
    'denver_nuggets': {'api_sports_id': 139, 'name': 'Denver Nuggets'},
    'detroit_pistons': {'api_sports_id': 140, 'name': 'Detroit Pistons'},
    'golden_state_warriors': {'api_sports_id': 141, 'name': 'Golden State Warriors'},
    'houston_rockets': {'api_sports_id': 142, 'name': 'Houston Rockets'},
    'indiana_pacers': {'api_sports_id': 143, 'name': 'Indiana Pacers'},
    'los_angeles_clippers': {'api_sports_id': 144, 'name': 'LA Clippers'},
    'los_angeles_lakers': {'api_sports_id': 145, 'name': 'Los Angeles Lakers'},
    'memphis_grizzlies': {'api_sports_id': 146, 'name': 'Memphis Grizzlies'},
    'miami_heat': {'api_sports_id': 147, 'name': 'Miami Heat'},
    'milwaukee_bucks': {'api_sports_id': 148, 'name': 'Milwaukee Bucks'},
    'minnesota_timberwolves': {'api_sports_id': 149, 'name': 'Minnesota Timberwolves'},
    'new_orleans_pelicans': {'api_sports_id': 150, 'name': 'New Orleans Pelicans'},
    'new_york_knicks': {'api_sports_id': 151, 'name': 'New York Knicks'},
    'oklahoma_city_thunder': {'api_sports_id': 152, 'name': 'Oklahoma City Thunder'},
    'orlando_magic': {'api_sports_id': 153, 'name': 'Orlando Magic'},
    'philadelphia_76ers': {'api_sports_id': 154, 'name': 'Philadelphia 76ers'},
    'phoenix_suns': {'api_sports_id': 155, 'name': 'Phoenix Suns'},
    'portland_trail_blazers': {'api_sports_id': 156, 'name': 'Portland Trail Blazers'},
    'sacramento_kings': {'api_sports_id': 157, 'name': 'Sacramento Kings'},
    'san_antonio_spurs': {'api_sports_id': 158, 'name': 'San Antonio Spurs'},
    'toronto_raptors': {'api_sports_id': 159, 'name': 'Toronto Raptors'},
    'utah_jazz': {'api_sports_id': 160, 'name': 'Utah Jazz'},
    'washington_wizards': {'api_sports_id': 161, 'name': 'Washington Wizards'},
}

def fetch_played_games(api_sports_id, team_name):
    """Fetch games that have already been played from API-Sports"""
    url = "https://v1.basketball.api-sports.io/games"
    headers = {"x-rapidapi-key": API_SPORTS_KEY}
    params = {
        "league": "12",
        "season": "2025-2026",
        "team": api_sports_id
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            games = []
            today = datetime.now().date()
            season_start = datetime(2025, 10, 22).date()  # Regular season starts Oct 22, 2025
            
            for game in data.get('response', []):
                # Use raw date from API (no timezone conversion needed)
                game_date_str = game['date'][:10]  # YYYY-MM-DD
                game_date = datetime.strptime(game_date_str, '%Y-%m-%d').date()
                
                # Only include regular season games that have been played
                if game_date >= season_start and game_date < today:
                    game_id = str(game['id'])
                    home_team = game['teams']['home']['name']
                    away_team = game['teams']['away']['name']
                    
                    # Determine opponent and home/away
                    if home_team == team_name:
                        opponent = away_team
                        home_away = 'HOME'
                    else:
                        opponent = home_team
                        home_away = 'AWAY'
                    
                    # Get scores and result
                    home_score = game['scores']['home']['total']
                    away_score = game['scores']['away']['total']
                    
                    # Skip if scores are null (game not finished)
                    if home_score is None or away_score is None:
                        continue
                    
                    if home_team == team_name:
                        team_score = home_score
                        opponent_score = away_score
                        result = 'W' if home_score > away_score else 'L'
                    else:
                        team_score = away_score
                        opponent_score = home_score
                        result = 'W' if away_score > home_score else 'L'
                    
                    games.append({
                        'game_id': game_id,
                        'game_date': game_date_str,
                        'opponent': opponent,
                        'home_away': home_away,
                        'result': result,
                        'team_score': team_score,
                        'opponent_score': opponent_score
                    })
            
            return games
    except Exception as e:
        print(f"    ⚠️  API error: {e}")
    
    return []

def insert_games(conn, schema, games):
    """Insert game rows into schedule table"""
    cur = conn.cursor()
    
    for game in games:
        try:
            cur.execute(f"""
                INSERT INTO {schema}.schedule (
                    game_date, game_id, opponent, home_away, 
                    result, team_score, opponent_score
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (game_date) DO NOTHING;
            """, (
                game['game_date'],
                game['game_id'],
                game['opponent'],
                game['home_away'],
                game['result'],
                game['team_score'],
                game['opponent_score']
            ))
        except Exception as e:
            print(f"    ✗ Error inserting {game['game_date']}: {e}")
    
    conn.commit()

def main():
    print("=" * 60)
    print("🏀 Populating Game Dates (Played Games Only)")
    print("=" * 60)
    print()
    
    conn = psycopg2.connect(NEON_DSN)
    
    total_games = 0
    
    for schema, team_info in NBA_TEAMS.items():
        print(f"🏀 {team_info['name']}...")
        
        # Fetch played games
        print(f"  → Fetching played games...")
        games = fetch_played_games(team_info['api_sports_id'], team_info['name'])
        print(f"  → Found {len(games)} games played")
        
        if games:
            # Insert games
            print(f"  → Inserting into schedule...")
            insert_games(conn, schema, games)
            print(f"  ✅ Inserted {len(games)} games")
            total_games += len(games)
        else:
            print(f"  ⚠️  No games found")
        
        print()
        time.sleep(0.3)  # Rate limit
    
    conn.close()
    
    print("=" * 60)
    print(f"✅ Complete! Inserted {total_games} total games across 30 teams")
    print("=" * 60)

if __name__ == "__main__":
    main()
