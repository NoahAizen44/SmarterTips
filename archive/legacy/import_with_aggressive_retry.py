#!/usr/bin/env python3
"""
Import real NBA player game logs from Stats API with aggressive retry logic
"""

import os
import requests
import time
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from supabase import create_client

# Initialize Supabase
url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

if not url or not key:
    print("❌ Error: NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY not set")
    exit(1)

supabase = create_client(url, key)

SEASON = 2025

TEAMS = {
    1610612738: "Boston Celtics",
    1610612751: "Denver Nuggets",
    1610612746: "LA Lakers",
}

# Session with custom timeouts and retries
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})

def fetch_with_retry(url, params=None, max_retries=5):
    """Fetch with aggressive retry logic"""
    for attempt in range(max_retries):
        try:
            response = session.get(
                url,
                params=params,
                timeout=30,  # Longer timeout
                allow_redirects=True
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            print(f"  ⏱️  Timeout (attempt {attempt+1}/{max_retries})")
        except requests.exceptions.ConnectionError as e:
            print(f"  🔌 Connection error (attempt {attempt+1}/{max_retries}): {str(e)[:50]}")
        except Exception as e:
            print(f"  ❌ Error (attempt {attempt+1}/{max_retries}): {str(e)[:50]}")
        
        if attempt < max_retries - 1:
            wait_time = min(2 ** attempt, 32)  # Exponential backoff, max 32 sec
            print(f"    Retrying in {wait_time}s...")
            time.sleep(wait_time)
    
    return None

def get_common_team_roster(team_id, season):
    """Get team roster"""
    print(f"  👥 Fetching roster...")
    url = "https://stats.nba.com/stats/commonteamroster"
    params = {
        "TeamID": team_id,
        "Season": f"{season-1}-{str(season)[-2:]}"
    }
    
    data = fetch_with_retry(url, params)
    if not data:
        return []
    
    result = []
    headers = data["resultSets"][0]["headers"]
    for row in data["resultSets"][0]["rowSet"]:
        result.append(dict(zip(headers, row)))
    
    print(f"    ✅ Found {len(result)} players")
    return result

def get_player_game_logs(player_id, season):
    """Get player game logs"""
    url = "https://stats.nba.com/stats/playergamelog"
    params = {
        "PlayerID": player_id,
        "Season": f"{season-1}-{str(season)[-2:]}"
    }
    
    data = fetch_with_retry(url, params)
    if not data:
        return []
    
    result = []
    if len(data["resultSets"]) > 0 and len(data["resultSets"][0]["rowSet"]) > 0:
        headers = data["resultSets"][0]["headers"]
        for row in data["resultSets"][0]["rowSet"]:
            result.append(dict(zip(headers, row)))
    
    return result

def process_team(team_id, team_name):
    """Process one team"""
    print(f"\n📥 Importing {team_name}...")
    
    # Get roster
    roster = get_common_team_roster(team_id, SEASON)
    if not roster:
        print(f"  ❌ Failed to get roster")
        return []
    
    records = []
    
    # Get game logs for each player
    for i, player in enumerate(roster, 1):
        player_id = player["PLAYER_ID"]
        player_name = player["PLAYER_NAME"]
        
        print(f"  [{i}/{len(roster)}] {player_name}...", end=" ", flush=True)
        
        game_logs = get_player_game_logs(player_id, SEASON)
        
        if game_logs:
            for log in game_logs:
                # Game date format: "20251104"
                game_date_str = str(log["GAME_DATE"])
                game_date = f"{game_date_str[:4]}-{game_date_str[4:6]}-{game_date_str[6:8]}"
                
                record = {
                    "team": team_name,
                    "player_id": str(player_id),
                    "player_name": player_name,
                    "position": player.get("POSITION", ""),
                    "game_date": game_date,
                    "game_id": str(log["GAME_ID"]),
                    "pts": log["PTS"] or 0,
                    "reb": log["REB"] or 0,
                    "ast": log["AST"] or 0,
                    "3pm": log["FG3M"] or 0,
                    "3pa": log["FG3A"] or 0,
                    "stl": log["STL"] or 0,
                    "blk": log["BLK"] or 0,
                    "season": SEASON,
                }
                records.append(record)
            print(f"✅ {len(game_logs)} games")
        else:
            print("⏭️  No games")
        
        time.sleep(0.5)  # Rate limiting
    
    print(f"  📊 Total: {len(records)} game records")
    return records

def main():
    print("🏀 NBA Game Logs Importer (Stats API)")
    print(f"Season: {SEASON}-{SEASON+1}")
    print("=" * 50)
    
    all_records = []
    
    # Import teams sequentially to avoid rate limiting
    for team_id, team_name in TEAMS.items():
        records = process_team(team_id, team_name)
        all_records.extend(records)
    
    print(f"\n📊 Total records: {len(all_records)}")
    
    if not all_records:
        print("❌ No data collected!")
        return
    
    # Insert in batches
    print("\n🚀 Inserting into Supabase...")
    batch_size = 500
    inserted_count = 0
    
    for i in range(0, len(all_records), batch_size):
        batch = all_records[i:i+batch_size]
        try:
            supabase.table("player_game_logs").insert(batch).execute()
            inserted_count += len(batch)
            print(f"  ✅ Batch {i//batch_size + 1}: +{len(batch)} records (total: {inserted_count})")
        except Exception as e:
            print(f"  ❌ Batch failed: {str(e)[:100]}")
    
    print(f"\n✨ Success! Imported {inserted_count} game logs")

if __name__ == "__main__":
    main()
