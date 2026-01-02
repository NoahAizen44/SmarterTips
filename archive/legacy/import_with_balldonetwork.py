#!/usr/bin/env python3
"""
Import real NBA player game logs using Ball Don't Lie API (free, no auth required)
https://www.balldontlie.io/
"""

import os
import requests
import time
from datetime import datetime
from supabase import create_client

# Initialize Supabase
url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

if not url or not key:
    print("❌ Error: NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY not set")
    exit(1)

supabase = create_client(url, key)

# Ball Don't Lie API base URL
API_BASE = "https://api.balldontlie.io/api/v1"

# 2025-26 season = 2025 (season starts Oct 2025)
SEASON = 2025

# All 30 NBA teams
TEAMS = {
    1: "Atlanta Hawks",
    2: "Boston Celtics",
    3: "Brooklyn Nets",
    4: "Charlotte Hornets",
    5: "Chicago Bulls",
    6: "Cleveland Cavaliers",
    7: "Dallas Mavericks",
    8: "Denver Nuggets",
    9: "Detroit Pistons",
    10: "Golden State Warriors",
    11: "Houston Rockets",
    12: "LA Clippers",
    13: "LA Lakers",
    14: "Memphis Grizzlies",
    15: "Miami Heat",
    16: "Milwaukee Bucks",
    17: "Minnesota Timberwolves",
    18: "New Orleans Pelicans",
    19: "New York Knicks",
    20: "Oklahoma City Thunder",
    21: "Orlando Magic",
    22: "Philadelphia 76ers",
    23: "Phoenix Suns",
    24: "Portland Trail Blazers",
    25: "Sacramento Kings",
    26: "San Antonio Spurs",
    27: "Toronto Raptors",
    28: "Utah Jazz",
    29: "Washington Wizards",
    30: "Indiana Pacers",
}

def get_team_players(team_id, retries=3):
    """Get all players for a team"""
    for attempt in range(retries):
        try:
            response = requests.get(
                f"{API_BASE}/players",
                params={"team_ids[]": team_id},
                timeout=10
            )
            response.raise_for_status()
            return response.json()["data"]
        except Exception as e:
            print(f"  ⚠️  Get players attempt {attempt+1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    return []

def get_player_game_logs(player_id, season, retries=3):
    """Get game logs for a player in a season"""
    for attempt in range(retries):
        try:
            response = requests.get(
                f"{API_BASE}/stats",
                params={
                    "player_ids[]": player_id,
                    "seasons[]": season,
                    "per_page": 100
                },
                timeout=10
            )
            response.raise_for_status()
            return response.json()["data"]
        except Exception as e:
            print(f"  ⚠️  Get game logs attempt {attempt+1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    return []

def import_team_data(team_id, team_name):
    """Import all data for a team"""
    print(f"\n📥 Importing {team_name} (ID: {team_id})...")
    
    # Get all players for this team
    players = get_team_players(team_id)
    if not players:
        print(f"  ❌ No players found for {team_name}")
        return 0
    
    print(f"  Found {len(players)} players")
    
    records = []
    
    # Get game logs for each player
    for player in players:
        player_id = player["id"]
        player_name = player["first_name"] + " " + player["last_name"]
        
        game_logs = get_player_game_logs(player_id, SEASON)
        
        for log in game_logs:
            game = log["game"]
            
            # Determine if this team was home or away
            home_team = game["home_team"]["id"]
            visiting_team = game["visitor_team"]["id"]
            
            is_home = home_team == team_id
            
            # Extract stats
            record = {
                "team": team_name,
                "player_id": str(player_id),
                "player_name": player_name,
                "position": player.get("position", ""),
                "game_date": game["date"][:10],  # YYYY-MM-DD
                "game_id": str(game["id"]),
                "pts": log.get("pts") or 0,
                "reb": log.get("reb") or 0,
                "ast": log.get("ast") or 0,
                "3pm": log.get("fg3m") or 0,  # 3-pointers made
                "3pa": log.get("fg3a") or 0,  # 3-pointers attempted
                "stl": log.get("stl") or 0,
                "blk": log.get("blk") or 0,
                "season": SEASON,
            }
            records.append(record)
        
        if game_logs:
            print(f"    ✅ {player_name}: {len(game_logs)} games")
    
    print(f"  📊 Total records for {team_name}: {len(records)}")
    return records

def main():
    print("🏀 NBA Game Logs Importer (Ball Don't Lie API)")
    print(f"Season: {SEASON}-{SEASON+1}")
    print(f"API: {API_BASE}")
    
    all_records = []
    
    # Import each team sequentially
    for team_id, team_name in TEAMS.items():
        records = import_team_data(team_id, team_name)
        all_records.extend(records)
        time.sleep(0.5)  # Small delay between teams
    
    print(f"\n📊 Total records collected: {len(all_records)}")
    
    # Clear existing data first (optional - comment out if you want to keep existing data)
    # print("\n🗑️  Clearing existing data...")
    # supabase.table("player_game_logs").delete().neq("id", None).execute()
    
    # Insert in batches of 500
    print("\n🚀 Inserting into Supabase...")
    batch_size = 500
    for i in range(0, len(all_records), batch_size):
        batch = all_records[i:i+batch_size]
        try:
            response = supabase.table("player_game_logs").insert(batch).execute()
            print(f"  ✅ Batch {i//batch_size + 1}: Inserted {len(batch)} records")
        except Exception as e:
            print(f"  ❌ Batch {i//batch_size + 1} failed: {e}")
    
    print(f"\n✨ Successfully imported {len(all_records)} game logs!")

if __name__ == "__main__":
    main()
