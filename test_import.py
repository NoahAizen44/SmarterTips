#!/usr/bin/env python3
"""Test import with just one team to verify everything works."""

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
            response = requests.get(url, params=params, headers=headers, timeout=20)
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
                wait_time = 3 ** attempt  # More aggressive backoff
                print(f"    ⏳ Timeout (attempt {attempt+1}/{retries}), waiting {wait_time}s...")
                time.sleep(wait_time)
        except Exception as e:
            print(f"    ❌ Error: {e}")
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
            response = requests.get(url, params=params, headers=headers, timeout=20)
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
                wait_time = 3 ** attempt
                print(f"    ⏳ Timeout (attempt {attempt+1}/{retries}), waiting {wait_time}s...")
                time.sleep(wait_time)
        except Exception as e:
            print(f"    ❌ Error: {e}")
            break
    
    return None

print("🚀 Testing import with Boston Celtics...")
print("📅 Season: 2025-26\n")

team_id = 1610612738
team_name = "Boston Celtics"

print(f"🏀 Fetching roster for {team_name}...")
roster = get_team_roster(team_id)

if not roster:
    print(f"❌ Failed to fetch roster")
    exit(1)

print(f"✅ Found {len(roster)} players\n")

rows_to_insert = []

for i, player in enumerate(roster[:5]):  # Test with just first 5 players
    player_name = player.get('PLAYER_NAME', '')
    player_id = player.get('PLAYER_ID')
    position = player.get('POSITION', 'UNKNOWN')
    
    if not player_id:
        continue
    
    print(f"  [{i+1}/5] Fetching {player_name}...")
    time.sleep(1)
    
    game_logs = get_player_game_logs(player_id)
    
    if not game_logs:
        print(f"       ⚠️  No games found")
        continue
    
    print(f"       ✅ {len(game_logs)} games")
    
    for game in game_logs[:3]:  # Test with first 3 games
        game_date = game.get('GAME_DATE', '')
        game_id = game.get('Game_ID', '')
        
        if not game_date:
            continue
        
        pts = game.get('PTS') or 0
        reb = game.get('REB') or 0
        ast = game.get('AST') or 0
        three_pm = game.get('FG3M') or 0
        three_pa = game.get('FG3A') or 0
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
            'season': '2025-26',
            'imported_at': datetime.utcnow().isoformat()
        })

if rows_to_insert:
    print(f"\n💾 Inserting {len(rows_to_insert)} test records...")
    try:
        response = supabase.table('player_game_logs').insert(rows_to_insert).execute()
        print(f"✅ Successfully inserted {len(rows_to_insert)} records!")
        print(f"\n✨ Test import successful! Ready to run full import.")
    except Exception as e:
        print(f"❌ Error inserting: {e}")
else:
    print("❌ No data to insert")
