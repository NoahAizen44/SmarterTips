"""
Setup Team Schedule Tables in Neon
===================================
1. Delete all existing tables in team schemas
2. Fetch current rosters for 2025-26 season (using NBA API)
3. Create schedule table per team with player columns (Boolean)
4. Populate with all season games from API-Sports
"""

import psycopg2
import requests
import time
from datetime import datetime
from nba_api.stats.endpoints import commonteamroster

# Neon connection
NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"
API_SPORTS_KEY = "bae6a6dbb611f615fed183ef2412bbe3"

# NBA Teams mapping (API-Sports IDs for 2025-2026 schedule, NBA API IDs for roster)
NBA_TEAMS = {
    'atlanta_hawks': {'api_sports_id': 132, 'nba_id': 1610612737, 'abbr': 'ATL', 'name': 'Atlanta Hawks'},
    'boston_celtics': {'api_sports_id': 133, 'nba_id': 1610612738, 'abbr': 'BOS', 'name': 'Boston Celtics'},
    'brooklyn_nets': {'api_sports_id': 134, 'nba_id': 1610612751, 'abbr': 'BKN', 'name': 'Brooklyn Nets'},
    'charlotte_hornets': {'api_sports_id': 135, 'nba_id': 1610612766, 'abbr': 'CHA', 'name': 'Charlotte Hornets'},
    'chicago_bulls': {'api_sports_id': 136, 'nba_id': 1610612741, 'abbr': 'CHI', 'name': 'Chicago Bulls'},
    'cleveland_cavaliers': {'api_sports_id': 137, 'nba_id': 1610612739, 'abbr': 'CLE', 'name': 'Cleveland Cavaliers'},
    'dallas_mavericks': {'api_sports_id': 138, 'nba_id': 1610612742, 'abbr': 'DAL', 'name': 'Dallas Mavericks'},
    'denver_nuggets': {'api_sports_id': 139, 'nba_id': 1610612743, 'abbr': 'DEN', 'name': 'Denver Nuggets'},
    'detroit_pistons': {'api_sports_id': 140, 'nba_id': 1610612765, 'abbr': 'DET', 'name': 'Detroit Pistons'},
    'golden_state_warriors': {'api_sports_id': 141, 'nba_id': 1610612744, 'abbr': 'GSW', 'name': 'Golden State Warriors'},
    'houston_rockets': {'api_sports_id': 142, 'nba_id': 1610612745, 'abbr': 'HOU', 'name': 'Houston Rockets'},
    'indiana_pacers': {'api_sports_id': 143, 'nba_id': 1610612754, 'abbr': 'IND', 'name': 'Indiana Pacers'},
    'los_angeles_clippers': {'api_sports_id': 144, 'nba_id': 1610612746, 'abbr': 'LAC', 'name': 'LA Clippers'},
    'los_angeles_lakers': {'api_sports_id': 145, 'nba_id': 1610612747, 'abbr': 'LAL', 'name': 'Los Angeles Lakers'},
    'memphis_grizzlies': {'api_sports_id': 146, 'nba_id': 1610612763, 'abbr': 'MEM', 'name': 'Memphis Grizzlies'},
    'miami_heat': {'api_sports_id': 147, 'nba_id': 1610612748, 'abbr': 'MIA', 'name': 'Miami Heat'},
    'milwaukee_bucks': {'api_sports_id': 148, 'nba_id': 1610612749, 'abbr': 'MIL', 'name': 'Milwaukee Bucks'},
    'minnesota_timberwolves': {'api_sports_id': 149, 'nba_id': 1610612750, 'abbr': 'MIN', 'name': 'Minnesota Timberwolves'},
    'new_orleans_pelicans': {'api_sports_id': 150, 'nba_id': 1610612740, 'abbr': 'NOP', 'name': 'New Orleans Pelicans'},
    'new_york_knicks': {'api_sports_id': 151, 'nba_id': 1610612752, 'abbr': 'NYK', 'name': 'New York Knicks'},
    'oklahoma_city_thunder': {'api_sports_id': 152, 'nba_id': 1610612760, 'abbr': 'OKC', 'name': 'Oklahoma City Thunder'},
    'orlando_magic': {'api_sports_id': 153, 'nba_id': 1610612753, 'abbr': 'ORL', 'name': 'Orlando Magic'},
    'philadelphia_76ers': {'api_sports_id': 154, 'nba_id': 1610612755, 'abbr': 'PHI', 'name': 'Philadelphia 76ers'},
    'phoenix_suns': {'api_sports_id': 155, 'nba_id': 1610612756, 'abbr': 'PHX', 'name': 'Phoenix Suns'},
    'portland_trail_blazers': {'api_sports_id': 156, 'nba_id': 1610612757, 'abbr': 'POR', 'name': 'Portland Trail Blazers'},
    'sacramento_kings': {'api_sports_id': 157, 'nba_id': 1610612758, 'abbr': 'SAC', 'name': 'Sacramento Kings'},
    'san_antonio_spurs': {'api_sports_id': 158, 'nba_id': 1610612759, 'abbr': 'SAS', 'name': 'San Antonio Spurs'},
    'toronto_raptors': {'api_sports_id': 159, 'nba_id': 1610612761, 'abbr': 'TOR', 'name': 'Toronto Raptors'},
    'utah_jazz': {'api_sports_id': 160, 'nba_id': 1610612762, 'abbr': 'UTA', 'name': 'Utah Jazz'},
    'washington_wizards': {'api_sports_id': 161, 'nba_id': 1610612764, 'abbr': 'WAS', 'name': 'Washington Wizards'},
}

def normalize_name(name):
    """Convert player name to valid SQL column name"""
    return name.lower().replace(' ', '_').replace("'", '').replace('.', '').replace('-', '_')

def fetch_team_roster(nba_team_id):
    """Fetch team roster from NBA API"""
    try:
        roster = commonteamroster.CommonTeamRoster(
            team_id=nba_team_id,
            season='2025-26'
        )
        df = roster.get_data_frames()[0]
        players = []
        for _, row in df.iterrows():
            player_name = row['PLAYER']
            players.append(normalize_name(player_name))
        return players
    except Exception as e:
        print(f"    ⚠️  NBA API error: {e}")
        return []

def fetch_team_schedule(api_sports_id, team_name):
    """Fetch team schedule from API-Sports (your paid API)"""
    url = f"https://v1.basketball.api-sports.io/games"
    headers = {"x-rapidapi-key": API_SPORTS_KEY}
    params = {"league": "12", "season": "2025-2026", "team": api_sports_id}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            games = []
            for game in data.get('response', []):
                game_date = game['date'][:10]  # YYYY-MM-DD
                game_id = str(game['id'])
                
                # Determine opponent and home/away
                home_team = game['teams']['home']['name']
                away_team = game['teams']['away']['name']
                
                games.append({
                    'game_id': game_id,
                    'game_date': game_date,
                    'home_team': home_team,
                    'away_team': away_team
                })
            return games
    except Exception as e:
        print(f"    ⚠️  API-Sports error: {e}")
    return []

def delete_existing_tables(conn):
    """Delete all tables in team schemas"""
    print("\n🗑️  Deleting existing tables in team schemas...")
    cur = conn.cursor()
    
    for schema in NBA_TEAMS.keys():
        try:
            cur.execute(f"""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = '{schema}';
            """)
            tables = cur.fetchall()
            
            for table in tables:
                cur.execute(f'DROP TABLE IF EXISTS {schema}.{table[0]} CASCADE;')
                print(f"  ✓ Deleted {schema}.{table[0]}")
            
            conn.commit()
        except Exception as e:
            print(f"  ✗ Error deleting tables in {schema}: {e}")
            conn.rollback()
    
    print("✅ All existing tables deleted\n")

def create_schedule_table(conn, schema, players):
    """Create schedule table with player columns"""
    cur = conn.cursor()
    
    # Build player columns
    player_columns = ',\n    '.join([f'"{player}" BOOLEAN' for player in players])
    
    create_sql = f"""
    CREATE TABLE {schema}.schedule (
        game_date DATE PRIMARY KEY,
        game_id VARCHAR(20) UNIQUE,
        opponent VARCHAR(50),
        home_away VARCHAR(10),
        result VARCHAR(5),
        team_score INT,
        opponent_score INT,
        
        {player_columns},
        
        created_at TIMESTAMP DEFAULT NOW()
    );
    """
    
    try:
        cur.execute(create_sql)
        conn.commit()
        return True
    except Exception as e:
        print(f"  ✗ Error creating table: {e}")
        conn.rollback()
        return False

def populate_schedule(conn, schema, team_name, games):
    """Insert schedule rows"""
    cur = conn.cursor()
    
    for game in games:
        # Determine opponent and home/away
        if game['home_team'] == team_name:
            opponent = game['away_team']
            home_away = 'HOME'
        else:
            opponent = game['home_team']
            home_away = 'AWAY'
        
        try:
            cur.execute(f"""
                INSERT INTO {schema}.schedule (game_date, game_id, opponent, home_away)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (game_date) DO NOTHING;
            """, (game['game_date'], game['game_id'], opponent, home_away))
        except Exception as e:
            print(f"    ✗ Error inserting game {game['game_date']}: {e}")
    
    conn.commit()

def main():
    print("=" * 60)
    print("🏀 NBA Team Schedule Tables Setup")
    print("=" * 60)
    
    conn = psycopg2.connect(NEON_DSN)
    
    # Step 1: Delete existing tables
    delete_existing_tables(conn)
    
    # Step 2-3: Create tables and populate
    print("📊 Creating and populating schedule tables...\n")
    
    for schema, team_info in NBA_TEAMS.items():
        print(f"🏀 {team_info['name']}...")
        
        # Fetch roster from NBA API
        print(f"  → Fetching roster (NBA API)...")
        players = fetch_team_roster(team_info['nba_id'])
        print(f"  → Found {len(players)} players")
        
        if not players:
            print(f"  ⚠️  No players found, skipping team")
            continue
        
        # Create table
        print(f"  → Creating schedule table...")
        success = create_schedule_table(conn, schema, players)
        
        if success:
            # Fetch schedule from API-Sports
            print(f"  → Fetching schedule (API-Sports)...")
            games = fetch_team_schedule(team_info['api_sports_id'], team_info['name'])
            print(f"  → Found {len(games)} games")
            
            # Populate
            if games:
                print(f"  → Inserting games...")
                populate_schedule(conn, schema, team_info['name'], games)
                print(f"  ✅ Done! ({len(games)} games inserted)")
            else:
                print(f"  ⚠️  No games found")
        
        print()
        time.sleep(0.6)  # Rate limit for NBA API
    
    conn.close()
    print("\n" + "=" * 60)
    print("✅ Setup complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
