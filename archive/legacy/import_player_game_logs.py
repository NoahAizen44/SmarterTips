#!/usr/bin/env python3
"""Import NBA player game-by-game stats from NBA Stats API into Supabase."""

import os
import time
from datetime import datetime
from supabase import create_client, Client
import requests
from typing import Dict, List, Optional

# Initialize Supabase client
url = os.environ.get('SUPABASE_URL', 'https://vszmsnikixfdakwzuown.supabase.co')
key = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZzem1zbmlraXhmZGFrd3p1b3duIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUyMjU1NTEsImV4cCI6MjA4MDgwMTU1MX0.oiSiA_LLjfVBh2kr-aqiFyLs6Jn-YK6_1X5t6S-SzY4')
supabase: Client = create_client(url, key)

# NBA Teams and their IDs
NBA_TEAMS = {
    'ATL': {'name': 'Atlanta Hawks', 'id': 1610612737},
    'BOS': {'name': 'Boston Celtics', 'id': 1610612738},
    'BKN': {'name': 'Brooklyn Nets', 'id': 1610612751},
    'CHA': {'name': 'Charlotte Hornets', 'id': 1610612766},
    'CHI': {'name': 'Chicago Bulls', 'id': 1610612741},
    'CLE': {'name': 'Cleveland Cavaliers', 'id': 1610612739},
    'DAL': {'name': 'Dallas Mavericks', 'id': 1610612742},
    'DEN': {'name': 'Denver Nuggets', 'id': 1610612743},
    'DET': {'name': 'Detroit Pistons', 'id': 1610612765},
    'GSW': {'name': 'Golden State Warriors', 'id': 1610612744},
    'HOU': {'name': 'Houston Rockets', 'id': 1610612745},
    'LAC': {'name': 'LA Clippers', 'id': 1610612746},
    'LAL': {'name': 'LA Lakers', 'id': 1610612747},
    'MEM': {'name': 'Memphis Grizzlies', 'id': 1610612766},
    'MIA': {'name': 'Miami Heat', 'id': 1610612748},
    'MIL': {'name': 'Milwaukee Bucks', 'id': 1610612749},
    'MIN': {'name': 'Minnesota Timberwolves', 'id': 1610612750},
    'NOP': {'name': 'New Orleans Pelicans', 'id': 1610612740},
    'NYK': {'name': 'New York Knicks', 'id': 1610612752},
    'OKC': {'name': 'Oklahoma City Thunder', 'id': 1610612753},
    'ORL': {'name': 'Orlando Magic', 'id': 1610612754},
    'PHI': {'name': 'Philadelphia 76ers', 'id': 1610612755},
    'PHX': {'name': 'Phoenix Suns', 'id': 1610612756},
    'POR': {'name': 'Portland Trail Blazers', 'id': 1610612757},
    'SAC': {'name': 'Sacramento Kings', 'id': 1610612758},
    'SAS': {'name': 'San Antonio Spurs', 'id': 1610612759},
    'TOR': {'name': 'Toronto Raptors', 'id': 1610612761},
    'UTA': {'name': 'Utah Jazz', 'id': 1610612762},
    'WAS': {'name': 'Washington Wizards', 'id': 1610612764},
}

def get_player_game_logs(player_id: int, season: str = '2025-26', retries: int = 3) -> Optional[List[Dict]]:
    """Fetch player game logs from NBA Stats API with retry logic."""
    url = "https://stats.nba.com/stats/playergamelog"
    params = {
        'PlayerID': player_id,
        'Season': season,
        'SeasonType': 'Regular Season'
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if data['resultSets'] and len(data['resultSets']) > 0:
                result_set = data['resultSets'][0]
                headers_list = result_set['headers']
                rows = result_set['rowSet']
                
                games = []
                for row in rows:
                    game_data = dict(zip(headers_list, row))
                    games.append(game_data)
                
                return games
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                print(f"    ⏳ Timeout (attempt {attempt+1}/{retries}), retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"    ❌ Failed after {retries} attempts for player {player_id}")
        except Exception as e:
            print(f"    ❌ Error fetching player {player_id}: {e}")
            break
    
    return None

def get_team_roster(team_id: int, season: str = '2025-26', retries: int = 3) -> Optional[List[Dict]]:
    """Fetch team roster from NBA Stats API with retry logic."""
    url = "https://stats.nba.com/stats/commonteamroster"
    params = {
        'TeamID': team_id,
        'Season': season
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if data['resultSets'] and len(data['resultSets']) > 0:
                result_set = data['resultSets'][0]
                headers_list = result_set['headers']
                rows = result_set['rowSet']
                
                players = []
                for row in rows:
                    player_data = dict(zip(headers_list, row))
                    players.append(player_data)
                
                return players
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                wait_time = 2 ** attempt
                print(f"    ⏳ Timeout (attempt {attempt+1}/{retries}), retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"    ❌ Failed after {retries} attempts for team {team_id}")
        except Exception as e:
            print(f"    ❌ Error fetching team {team_id}: {e}")
            break
    
    return None

def import_team_player_stats(team_key: str, season: str = '2025-26'):
    """Import all player stats for a team."""
    if team_key not in NBA_TEAMS:
        print(f"❌ Unknown team: {team_key}")
        return
    
    team_info = NBA_TEAMS[team_key]
    team_name = team_info['name']
    team_id = team_info['id']
    
    print(f"\n🏀 Fetching roster for {team_name}...")
    roster = get_team_roster(team_id, season)
    
    if not roster:
        print(f"❌ Failed to fetch roster for {team_name}")
        return
    
    print(f"✅ Found {len(roster)} players")
    
    rows_to_insert = []
    
    for player in roster:
        player_name = player.get('PLAYER_NAME', '')
        player_id = player.get('PLAYER_ID')
        position = player.get('POSITION', 'UNKNOWN')
        
        if not player_id or player_id == '':
            continue
        
        print(f"  📊 Fetching stats for {player_name} ({position})...")
        time.sleep(0.5)  # Rate limiting
        
        game_logs = get_player_game_logs(player_id, season)
        
        if not game_logs:
            print(f"    ⚠️  No game logs found for {player_name}")
            continue
        
        for game in game_logs:
            try:
                game_date = game.get('GAME_DATE', '')
                game_id = game.get('Game_ID', '')
                
                # Skip if no game date
                if not game_date:
                    continue
                
                # Parse stats (handle None values from DNP games)
                pts = game.get('PTS') or 0
                reb = game.get('REB') or 0
                ast = game.get('AST') or 0
                three_pm = game.get('FG3M') or 0  # 3-pointers made
                three_pa = game.get('FG3A') or 0  # 3-pointers attempted
                stl = game.get('STL') or 0
                blk = game.get('BLK') or 0
                
                rows_to_insert.append({
                    'team': team_name,
                    'player_id': int(player_id),
                    'player_name': player_name,
                    'position': position,
                    'game_date': game_date,
                    'game_id': game_id,
                    'pts': int(pts) if pts else 0,
                    'reb': int(reb) if reb else 0,
                    'ast': int(ast) if ast else 0,
                    '3pm': int(three_pm) if three_pm else 0,
                    '3pa': int(three_pa) if three_pa else 0,
                    'stl': int(stl) if stl else 0,
                    'blk': int(blk) if blk else 0,
                    'season': season,
                    'imported_at': datetime.utcnow().isoformat()
                })
            except Exception as e:
                print(f"    ❌ Error processing game for {player_name}: {e}")
                continue
        
        print(f"    ✅ Processed {len(game_logs)} games for {player_name}")
    
    if not rows_to_insert:
        print(f"❌ No data to insert for {team_name}")
        return
    
    # Insert in batches
    batch_size = 500
    total_inserted = 0
    
    print(f"\n💾 Inserting {len(rows_to_insert)} game records...")
    
    for i in range(0, len(rows_to_insert), batch_size):
        batch = rows_to_insert[i:i+batch_size]
        try:
            response = supabase.table('player_game_logs').insert(batch).execute()
            total_inserted += len(batch)
            print(f"✅ Inserted batch ({total_inserted}/{len(rows_to_insert)} total)")
        except Exception as e:
            print(f"❌ Error inserting batch: {e}")
    
    print(f"✨ Completed {team_name}! Total rows: {total_inserted}")

def main():
    """Main import function."""
    print("🚀 Starting NBA player stats import to Supabase...")
    print(f"📅 Current season: 2025-26")
    
    # Clear existing data
    try:
        print("\n🗑️  Clearing existing player_game_logs data...")
        supabase.table('player_game_logs').delete().neq('id', 0).execute()
        print("✅ Cleared existing data")
    except Exception as e:
        print(f"⚠️  Could not clear existing data: {e}")
    
    # Import all teams (or specific teams if you want to limit)
    teams_to_import = list(NBA_TEAMS.keys())
    
    for team_key in teams_to_import:
        import_team_player_stats(team_key)
        time.sleep(1)  # Rate limiting between teams
    
    print(f"\n✨ Import complete!")

if __name__ == '__main__':
    main()
