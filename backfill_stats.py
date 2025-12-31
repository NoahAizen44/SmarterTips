#!/usr/bin/env python3
"""
Backfill all player game logs with complete stat data from NBA API
Uses nba_api library for reliable data extraction
"""

import time
from datetime import datetime
from supabase import create_client
from nba_api.stats.endpoints import commonteamroster, playergamelog
import socket

# Set socket timeout to prevent hanging
socket.setdefaulttimeout(5)

# Initialize Supabase
supabase = create_client(
    'https://vszmsnikixfdakwzuown.supabase.co',
    'sb_secret_A2RLLNm4pOfRRDOI73z8iQ_5e6nwC1b'
)

TEAM_NAMES = [
    'Atlanta Hawks', 'Boston Celtics', 'Brooklyn Nets', 'Charlotte Hornets',
    'Chicago Bulls', 'Cleveland Cavaliers', 'Dallas Mavericks', 'Denver Nuggets',
    'Detroit Pistons', 'Golden State Warriors', 'Houston Rockets', 'Indiana Pacers',
    'Los Angeles Clippers', 'Los Angeles Lakers', 'Memphis Grizzlies', 'Miami Heat',
    'Milwaukee Bucks', 'Minnesota Timberwolves', 'New Orleans Pelicans', 'New York Knicks',
    'Oklahoma City Thunder', 'Orlando Magic', 'Philadelphia 76ers', 'Phoenix Suns',
    'Portland Trail Blazers', 'Sacramento Kings', 'San Antonio Spurs', 'Toronto Raptors',
    'Utah Jazz', 'Washington Wizards'
]

TEAM_IDS = {
    'Atlanta Hawks': 1610612737, 'Boston Celtics': 1610612738, 'Brooklyn Nets': 1610612751,
    'Charlotte Hornets': 1610612766, 'Chicago Bulls': 1610612741, 'Cleveland Cavaliers': 1610612739,
    'Dallas Mavericks': 1610612742, 'Denver Nuggets': 1610612743, 'Detroit Pistons': 1610612765,
    'Golden State Warriors': 1610612744, 'Houston Rockets': 1610612745, 'Indiana Pacers': 1610612754,
    'Los Angeles Clippers': 1610612746, 'Los Angeles Lakers': 1610612747, 'Memphis Grizzlies': 1610612763,
    'Miami Heat': 1610612748, 'Milwaukee Bucks': 1610612749, 'Minnesota Timberwolves': 1610612750,
    'New Orleans Pelicans': 1610612740, 'New York Knicks': 1610612752, 'Oklahoma City Thunder': 1610612760,
    'Orlando Magic': 1610612753, 'Philadelphia 76ers': 1610612755, 'Phoenix Suns': 1610612756,
    'Portland Trail Blazers': 1610612757, 'Sacramento Kings': 1610612758, 'San Antonio Spurs': 1610612759,
    'Toronto Raptors': 1610612761, 'Utah Jazz': 1610612762, 'Washington Wizards': 1610612764,
}

def fetch_team_games(team_id):
    """Fetch all player game logs for a team using nba_api"""
    try:
        print(f"      Fetching roster...", flush=True)
        # Get team roster with timeout
        roster_data = commonteamroster.CommonTeamRoster(team_id=team_id, season='2025-26')
        roster_df = roster_data.get_data_frames()[0]
        print(f"      Got {len(roster_df)} players", flush=True)
        
        all_games = []
        
        # Get game logs for each player
        for idx, player in roster_df.iterrows():
            player_id = player.get('PLAYER_ID')
            if not player_id:
                continue
            
            try:
                print(f"      Fetching games for player {player_id}...", end=" ", flush=True)
                game_logs_data = playergamelog.PlayerGameLog(
                    player_id=player_id, 
                    season='2025-26',
                    season_type_all_star='Regular Season'
                )
                game_logs_df = game_logs_data.get_data_frames()[0]
                print(f"{len(game_logs_df)} games", flush=True)
                
                # Convert dataframe to list of records
                for idx, game in game_logs_df.iterrows():
                    all_games.append(game)
                    
            except socket.timeout:
                print(f"TIMEOUT", flush=True)
                continue
            except Exception as e:
                print(f"ERROR: {str(e)[:30]}", flush=True)
                continue
        
        return all_games
    except socket.timeout:
        print(f"      TIMEOUT fetching roster", flush=True)
        return []
    except Exception as e:
        print(f"      Error fetching roster: {str(e)[:50]}", flush=True)
        return []

def backfill_team(team_name):
    """Backfill stats for all players on a team"""
    print(f"\n📊 {team_name}")
    team_id = TEAM_IDS[team_name]
    
    # Fetch games from nba_api
    games = fetch_team_games(team_id)
    if not games or len(games) == 0:
        print(f"   No data from API")
        return 0
    
    print(f"   ✓ Fetched {len(games)} game records from API")
    
    # Get existing records for this team
    response = supabase.from_('player_game_logs').select('id, game_id, player_id, player_name').eq('team', team_name).execute()
    records = response.data if response.data else []
    
    if not records:
        print(f"   No records in database")
        return 0
    
    print(f"   ✓ Found {len(records)} records in database")
    
    # Create map for O(1) lookup by game_id + player_id
    record_map = {}
    for record in records:
        key = f"{record['game_id']}-{record['player_id']}"
        record_map[key] = record['id']
    
    # Prepare updates
    updates_to_send = []
    for game in games:
        # nba_api returns Game_ID as string like '0022500395'
        game_id = str(game.get('Game_ID', ''))
        player_id = int(game.get('Player_ID', 0))
        
        # Try to match with database using game_id + player_id
        key = f"{game_id}-{player_id}"
        
        if key in record_map:
            updates_to_send.append({
                'id': record_map[key],
                'gp': 1,
                'ftm': int(game.get('FTM') or 0),
                'fta': int(game.get('FTA') or 0),
                'fga': int(game.get('FGA') or 0),
                'fgm': int(game.get('FGM') or 0),
                'min': int(game.get('MIN') or 0),
                'tov': int(game.get('TOV') or 0),
                'pf': int(game.get('PF') or 0),
                'stl': int(game.get('STL') or 0),
                'blk': int(game.get('BLK') or 0),
                'fg_pct': float(game.get('FG_PCT') or 0),
                'fg3_pct': float(game.get('FG3_PCT') or 0),
                'ft_pct': float(game.get('FT_PCT') or 0),
            })
    
    print(f"   ✓ Matched {len(updates_to_send)} games to database records")
    
    # Send updates in batches
    updated_count = 0
    batch_size = 50
    
    for i in range(0, len(updates_to_send), batch_size):
        batch = updates_to_send[i:i+batch_size]
        
        for update in batch:
            record_id = update.pop('id')
            try:
                supabase.from_('player_game_logs').update(update).eq('id', record_id).execute()
                updated_count += 1
            except Exception as e:
                print(f"   Error updating record: {e}")
        
        print(f"   ✓ Updated {min(i + batch_size, len(updates_to_send))}/{len(updates_to_send)}")
        time.sleep(0.5)  # Rate limit
    
    print(f"   ✅ Completed: {updated_count}/{len(records)} records updated")
    return updated_count

def main():
    print("=" * 60)
    print("🚀 NBA Stats Backfill - Loading all season data")
    print("=" * 60)
    
    total_updated = 0
    
    for team_name in TEAM_NAMES:
        count = backfill_team(team_name)
        total_updated += count
        time.sleep(1)  # Rate limit between teams
    
    print("\n" + "=" * 60)
    print(f"✅ COMPLETE! Updated {total_updated:,} total records")
    print("=" * 60)

if __name__ == '__main__':
    main()
