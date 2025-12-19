#!/usr/bin/env python3
"""
Import real NBA player game logs using nba_api library
"""

import os
import time
from supabase import create_client
from nba_api.stats.endpoints import playergamelog, commonteamroster
from nba_api.stats.static import teams as static_teams

# Initialize Supabase
url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

if not url or not key:
    print("❌ Error: NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY not set")
    exit(1)

supabase = create_client(url, key)

# Delay to avoid rate limiting
REQUEST_DELAY = 0.6
SEASON = '2025-26'

def import_team(team_id, team_name):
    """Import all game logs for a team"""
    print(f"\n📥 Importing {team_name}...")
    
    try:
        # Get roster
        print("  👥 Fetching roster...", end=" ", flush=True)
        roster = commonteamroster.CommonTeamRoster(team_id=team_id, season=SEASON)
        roster_df = roster.get_data_frames()[0]
        print(f"✅ {len(roster_df)} players")
        time.sleep(REQUEST_DELAY)
        
        records = []
        
        # Get game logs for each player
        for idx, player in roster_df.iterrows():
            player_id = player['PLAYER_ID']
            player_name = player['PLAYER']
            position = player.get('POSITION', '')
            
            print(f"  [{idx+1}/{len(roster_df)}] {player_name}...", end=" ", flush=True)
            
            try:
                logs = playergamelog.PlayerGameLog(
                    player_id=player_id,
                    season=SEASON,
                    season_type_all_star='Regular Season'
                )
                logs_df = logs.get_data_frames()[0]
                time.sleep(REQUEST_DELAY)
                
                if logs_df.empty:
                    print("⏭️  no games")
                    continue
                
                for _, game in logs_df.iterrows():
                    game_date = str(game['GAME_DATE']).strip()
                    
                    record = {
                        "team": team_name,
                        "player_id": str(player_id),
                        "player_name": player_name,
                        "position": position,
                        "game_date": game_date,
                        "game_id": str(game['Game_ID']),
                        "pts": int(game.get('PTS') or 0),
                        "reb": int(game.get('REB') or 0),
                        "ast": int(game.get('AST') or 0),
                        "3pm": int(game.get('FG3M') or 0),
                        "3pa": int(game.get('FG3A') or 0),
                        "stl": int(game.get('STL') or 0),
                        "blk": int(game.get('BLK') or 0),
                        "season": 2025,
                    }
                    records.append(record)
                
                print(f"✅ {len(logs_df)} games")
                
            except Exception as e:
                print(f"❌ Error: {str(e)[:50]}")
                continue
        
        print(f"  📊 Total records: {len(records)}")
        return records
        
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return []

def main():
    print("🏀 NBA Game Logs Importer (nba_api)")
    print(f"Season: {SEASON}")
    print("=" * 50)
    
    # Get all 30 NBA teams
    all_teams = static_teams.get_teams()
    teams_to_import = [(team['id'], team['full_name']) for team in all_teams]
    
    # Get teams already in database
    try:
        response = supabase.table("player_game_logs").select("team").execute()
        teams_in_db = set([r["team"] for r in response.data])
        print(f"Teams already imported: {len(teams_in_db)}")
        if teams_in_db:
            print(f"  {', '.join(sorted(teams_in_db))}\n")
    except:
        teams_in_db = set()
    
    all_records = []
    
    for team_id, team_name in teams_to_import:
        if team_name in teams_in_db:
            print(f"⏭️  Skipping {team_name} (already imported)")
            continue
        records = import_team(team_id, team_name)
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
