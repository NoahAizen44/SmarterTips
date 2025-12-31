"""
Create Team Schedule Tables in Neon
====================================
Creates one schedule table per team with:
- Game metadata columns (date, opponent, etc.)
- Boolean column for each player on the roster
"""

import psycopg2
import time
from nba_api.stats.endpoints import commonteamroster

# Neon connection
NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

# NBA Teams (NBA API IDs for roster)
NBA_TEAMS = {
    'atlanta_hawks': {'nba_id': 1610612737, 'name': 'Atlanta Hawks'},
    'boston_celtics': {'nba_id': 1610612738, 'name': 'Boston Celtics'},
    'brooklyn_nets': {'nba_id': 1610612751, 'name': 'Brooklyn Nets'},
    'charlotte_hornets': {'nba_id': 1610612766, 'name': 'Charlotte Hornets'},
    'chicago_bulls': {'nba_id': 1610612741, 'name': 'Chicago Bulls'},
    'cleveland_cavaliers': {'nba_id': 1610612739, 'name': 'Cleveland Cavaliers'},
    'dallas_mavericks': {'nba_id': 1610612742, 'name': 'Dallas Mavericks'},
    'denver_nuggets': {'nba_id': 1610612743, 'name': 'Denver Nuggets'},
    'detroit_pistons': {'nba_id': 1610612765, 'name': 'Detroit Pistons'},
    'golden_state_warriors': {'nba_id': 1610612744, 'name': 'Golden State Warriors'},
    'houston_rockets': {'nba_id': 1610612745, 'name': 'Houston Rockets'},
    'indiana_pacers': {'nba_id': 1610612754, 'name': 'Indiana Pacers'},
    'los_angeles_clippers': {'nba_id': 1610612746, 'name': 'LA Clippers'},
    'los_angeles_lakers': {'nba_id': 1610612747, 'name': 'Los Angeles Lakers'},
    'memphis_grizzlies': {'nba_id': 1610612763, 'name': 'Memphis Grizzlies'},
    'miami_heat': {'nba_id': 1610612748, 'name': 'Miami Heat'},
    'milwaukee_bucks': {'nba_id': 1610612749, 'name': 'Milwaukee Bucks'},
    'minnesota_timberwolves': {'nba_id': 1610612750, 'name': 'Minnesota Timberwolves'},
    'new_orleans_pelicans': {'nba_id': 1610612740, 'name': 'New Orleans Pelicans'},
    'new_york_knicks': {'nba_id': 1610612752, 'name': 'New York Knicks'},
    'oklahoma_city_thunder': {'nba_id': 1610612760, 'name': 'Oklahoma City Thunder'},
    'orlando_magic': {'nba_id': 1610612753, 'name': 'Orlando Magic'},
    'philadelphia_76ers': {'nba_id': 1610612755, 'name': 'Philadelphia 76ers'},
    'phoenix_suns': {'nba_id': 1610612756, 'name': 'Phoenix Suns'},
    'portland_trail_blazers': {'nba_id': 1610612757, 'name': 'Portland Trail Blazers'},
    'sacramento_kings': {'nba_id': 1610612758, 'name': 'Sacramento Kings'},
    'san_antonio_spurs': {'nba_id': 1610612759, 'name': 'San Antonio Spurs'},
    'toronto_raptors': {'nba_id': 1610612761, 'name': 'Toronto Raptors'},
    'utah_jazz': {'nba_id': 1610612762, 'name': 'Utah Jazz'},
    'washington_wizards': {'nba_id': 1610612764, 'name': 'Washington Wizards'},
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

def create_schedule_table(conn, schema, players):
    """Create schedule table with player columns"""
    cur = conn.cursor()
    
    # Drop existing table if it exists
    try:
        cur.execute(f"DROP TABLE IF EXISTS {schema}.schedule CASCADE;")
        conn.commit()
    except Exception as e:
        print(f"  ⚠️  Warning dropping table: {e}")
        conn.rollback()
    
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

def main():
    print("=" * 60)
    print("🏀 Creating NBA Team Schedule Tables")
    print("=" * 60)
    print()
    
    conn = psycopg2.connect(NEON_DSN)
    
    success_count = 0
    
    for schema, team_info in NBA_TEAMS.items():
        print(f"🏀 {team_info['name']}...")
        
        # Fetch roster from NBA API
        print(f"  → Fetching roster...")
        players = fetch_team_roster(team_info['nba_id'])
        print(f"  → Found {len(players)} players")
        
        if not players:
            print(f"  ⚠️  No players found, skipping")
            print()
            continue
        
        # Create table
        print(f"  → Creating schedule table...")
        success = create_schedule_table(conn, schema, players)
        
        if success:
            print(f"  ✅ Done!")
            success_count += 1
        
        print()
        time.sleep(0.6)  # Rate limit for NBA API
    
    conn.close()
    
    print("=" * 60)
    print(f"✅ Complete! Created {success_count}/30 tables")
    print("=" * 60)

if __name__ == "__main__":
    main()
