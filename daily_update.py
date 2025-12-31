#!/usr/bin/env python3
"""
Daily Supabase Update Script
- Fetches new NBA games from yesterday/today
- Adds DNP records for those games
- Detects trades and backfills DNPs (TODO: implement trade detection)
"""

import time
from datetime import datetime, timedelta
from supabase import create_client
from nba_api.stats.endpoints import commonteamroster, playergamelog
from collections import defaultdict

SUPABASE_URL = 'https://vszmsnikixfdakwzuown.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZzem1zbmlraXhmZGFrd3p1b3duIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUyMjU1NTEsImV4cCI6MjA4MDgwMTU1MX0.oiSiA_LLjfVBh2kr-aqiFyLs6Jn-YK6_1X5t6S-SzY4'
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

TEAMS = {
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

def get_latest_game_date():
    """Get the most recent game date in the database"""
    print("🔍 Checking latest game date in database...")
    response = supabase.table('player_game_logs').select('game_date').order('game_date', desc=True).limit(1).execute()
    
    if response.data:
        latest_date = response.data[0]['game_date']
        print(f"   Latest game: {latest_date}")
        return latest_date
    return None

def import_new_games_for_team(team_name, team_id, since_date=None):
    """Import games for a team since a given date"""
    print(f"\n{'='*60}")
    print(f"📊 {team_name}")
    print('='*60)
    
    # Get current roster
    print("  Getting roster...", end=" ", flush=True)
    try:
        roster = commonteamroster.CommonTeamRoster(team_id=team_id, season='2025-26')
        roster_df = roster.get_data_frames()[0]
        print(f"✓ {len(roster_df)} players")
    except Exception as e:
        print(f"✗ Error: {e}")
        return 0
    
    all_rows = []
    
    for idx, player in roster_df.iterrows():
        player_name = player.get('PLAYER', '')
        player_id = int(player.get('PLAYER_ID') or 0)
        position = player.get('POSITION', '')
        
        if not player_id:
            continue
        
        print(f"  {player_name:25} ", end="", flush=True)
        time.sleep(0.6)  # Rate limit
        
        try:
            logs = playergamelog.PlayerGameLog(player_id=player_id, season='2025-26')
            logs_df = logs.get_data_frames()[0]
            
            if logs_df.empty:
                print("✓ 0 games")
                continue
            
            # Filter by date if provided
            if since_date:
                logs_df['GAME_DATE'] = logs_df['GAME_DATE'].astype(str)
                logs_df = logs_df[logs_df['GAME_DATE'] > since_date]
                
                if logs_df.empty:
                    print("✓ 0 new games")
                    continue
            
            print(f"✓ {len(logs_df)} new games")
            
            for _, game in logs_df.iterrows():
                row = {
                    'team': team_name,
                    'player_id': player_id,
                    'player_name': player_name,
                    'position': position,
                    'game_date': str(game.get('GAME_DATE', '')),
                    'game_id': str(game.get('GAME_ID', '')),
                    'pts': int(game.get('PTS', 0) or 0),
                    'reb': int(game.get('REB', 0) or 0),
                    'ast': int(game.get('AST', 0) or 0),
                    '3pm': int(game.get('FG3M', 0) or 0),
                    '3pa': int(game.get('FG3A', 0) or 0),
                    'stl': int(game.get('STL', 0) or 0),
                    'blk': int(game.get('BLK', 0) or 0),
                    'gp': 1,
                    'ftm': int(game.get('FTM', 0) or 0),
                    'fta': int(game.get('FTA', 0) or 0),
                    'fga': int(game.get('FGA', 0) or 0),
                    'fgm': int(game.get('FGM', 0) or 0),
                    'min': float(game.get('MIN', 0) or 0),
                    'tov': int(game.get('TOV', 0) or 0),
                }
                all_rows.append(row)
                
        except Exception as e:
            print(f"✗ Error: {e}")
            continue
    
    # Batch insert
    if all_rows:
        print(f"\n  Inserting {len(all_rows)} records...", end=" ", flush=True)
        batch_size = 500
        for i in range(0, len(all_rows), batch_size):
            batch = all_rows[i:i+batch_size]
            supabase.table('player_game_logs').insert(batch).execute()
        print("✓")
    
    return len(all_rows)

def add_dnps_for_team(team_name, since_date=None):
    """Add DNP records for a team, optionally only for games after a certain date"""
    print(f"\n{'='*60}")
    print(f"🚫 Adding DNPs for {team_name}")
    print(f"{'='*60}")
    
    # Get all existing records for this team
    print(f"  Fetching existing records...", end=" ", flush=True)
    response = supabase.table('player_game_logs').select('*').eq('team', team_name).execute()
    existing_records = response.data
    print(f"✓ {len(existing_records)} records")
    
    if not existing_records:
        print(f"  No records found for {team_name}")
        return 0
    
    # Build data structures
    games = {}  # key: game_id, value: game_date
    players = {}  # key: player_id, value: (player_name, position)
    existing_combos = set()  # set of f"{player_id}-{game_id}"
    
    for record in existing_records:
        game_id = record.get('game_id')
        game_date = record.get('game_date')
        player_id = record.get('player_id')
        player_name = record.get('player_name')
        position = record.get('position', 'UNKNOWN')
        
        # Filter by date if specified
        if since_date and game_date and game_date <= since_date:
            continue
        
        if game_id and game_date:
            games[game_id] = game_date
        
        if player_id and player_name:
            players[player_id] = (player_name, position)
        
        if game_id and player_id:
            existing_combos.add(f"{player_id}-{game_id}")
    
    if since_date:
        print(f"  Found {len(games)} games after {since_date}")
    else:
        print(f"  Found {len(games)} total games")
    print(f"  Found {len(players)} unique players")
    
    # Find missing combinations (DNPs)
    print(f"  Identifying DNPs...", end=" ", flush=True)
    dnp_records = []
    
    for player_id, (player_name, position) in players.items():
        for game_id, game_date in games.items():
            combo = f"{player_id}-{game_id}"
            
            if combo not in existing_combos:
                dnp_records.append({
                    'team': team_name,
                    'player_id': player_id,
                    'player_name': player_name,
                    'position': position,
                    'game_date': game_date,
                    'game_id': game_id,
                    'pts': 0,
                    'reb': 0,
                    'ast': 0,
                    '3pm': 0,
                    '3pa': 0,
                    'stl': 0,
                    'blk': 0,
                    'gp': 0,
                    'ftm': 0,
                    'fta': 0,
                    'fga': 0,
                    'fgm': 0,
                    'min': 0,
                    'tov': 0,
                })
    
    print(f"✓ {len(dnp_records)} DNPs found")
    
    # Insert DNPs
    if dnp_records:
        print(f"  Inserting DNPs...", end=" ", flush=True)
        batch_size = 500
        for i in range(0, len(dnp_records), batch_size):
            batch = dnp_records[i:i+batch_size]
            supabase.table('player_game_logs').insert(batch).execute()
        print("✓")
    
    return len(dnp_records)

def main():
    print("="*60)
    print("🏀 DAILY NBA DATABASE UPDATE")
    print("="*60)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    total_games = 0
    total_dnps = 0
    
    # Phase 0: Delete all existing records
    print("\n" + "="*60)
    print("🗑️  PHASE 0: CLEARING DATABASE")
    print("="*60)
    print("  Deleting all existing records...", end=" ", flush=True)
    try:
        supabase.table('player_game_logs').delete().neq('id', 0).execute()
        print("✓ All records deleted")
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    # Phase 1: Import ALL games (full season)
    print("\n" + "="*60)
    print("📥 PHASE 1: IMPORTING ALL GAMES")
    print("="*60)
    
    for team_name, team_id in TEAMS.items():
        try:
            games = import_new_games_for_team(team_name, team_id, since_date=None)
            total_games += games
        except Exception as e:
            print(f"  ✗ Error processing {team_name}: {e}")
            continue
    
    print(f"\n✅ Total games imported: {total_games}")
    
    # Phase 2: Add all DNPs
    print("\n" + "="*60)
    print("📥 PHASE 2: ADDING ALL DNP RECORDS")
    print("="*60)
    
    for team_name in TEAMS.keys():
        try:
            dnps = add_dnps_for_team(team_name, since_date=None)
            total_dnps += dnps
        except Exception as e:
            print(f"  ✗ Error adding DNPs for {team_name}: {e}")
            continue
    
    print(f"\n✅ Total DNPs added: {total_dnps}")
    
    # Summary
    print("\n" + "="*60)
    print("� DAILY UPDATE SUMMARY")
    print("="*60)
    print(f"  Total games imported: {total_games}")
    print(f"  Total DNP records added: {total_dnps}")
    print(f"  Total records in database: {total_games + total_dnps}")
    print(f"  Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

if __name__ == '__main__':
    main()
