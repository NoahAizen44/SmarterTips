#!/usr/bin/env python3
"""Import NBA player game logs using nba_api library (much more reliable)."""

import os
from datetime import datetime
from supabase import create_client, Client
from nba_api.stats.endpoints import commonteamroster, playergamelog
import time

url = os.environ.get('SUPABASE_URL', 'https://vszmsnikixfdakwzuown.supabase.co')
key = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZzem1zbmlraXhmZGFrd3p1b3duIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUyMjU1NTEsImV4cCI6MjA4MDgwMTU1MX0.oiSiA_LLjfVBh2kr-aqiFyLs6Jn-YK6_1X5t6S-SzY4')
supabase: Client = create_client(url, key)

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

def import_team(team_key: str):
    """Import all player stats for a team."""
    if team_key not in NBA_TEAMS:
        return
    
    team_info = NBA_TEAMS[team_key]
    team_name = team_info['name']
    team_id = team_info['id']
    
    print(f"🏀 {team_name}...", end=" ", flush=True)
    
    try:
        # Get roster
        roster_data = commonteamroster.CommonTeamRoster(team_id=team_id, season='2025-26')
        roster_df = roster_data.get_data_frames()[0]
        
        rows_to_insert = []
        
        for idx, player in roster_df.iterrows():
            player_name = player.get('PLAYER_NAME') or player.get('PlayerName')
            player_id = player.get('PLAYER_ID') or player.get('PlayerID')
            position = player.get('POSITION') or player.get('Pos') or 'UNKNOWN'
            
            # Get player game logs
            game_logs_data = playergamelog.PlayerGameLog(player_id=player_id, season='2025-26', season_type_all_star='Regular Season')
            game_logs_df = game_logs_data.get_data_frames()[0]
            
            for idx, game in game_logs_df.iterrows():
                game_date = game.get('GAME_DATE') or game.get('GameDate')
                game_id = game.get('Game_ID') or game.get('GameID')
                
                if not game_date or not game_id:
                    continue
                
                pts = game.get('PTS') or game.get('Points') or 0
                reb = game.get('REB') or game.get('Rebounds') or 0
                ast = game.get('AST') or game.get('Assists') or 0
                three_pm = game.get('FG3M') or game.get('3PM') or 0
                three_pa = game.get('FG3A') or game.get('3PA') or 0
                stl = game.get('STL') or game.get('Steals') or 0
                blk = game.get('BLK') or game.get('Blocks') or 0
                
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
            
            time.sleep(0.1)  # Rate limit
        
        # Insert in batches
        if rows_to_insert:
            batch_size = 500
            for i in range(0, len(rows_to_insert), batch_size):
                batch = rows_to_insert[i:i+batch_size]
                supabase.table('player_game_logs').insert(batch).execute()
            
            print(f"✅ {len(rows_to_insert)} records")
        else:
            print("⚠️  No data")
            
    except Exception as e:
        print(f"❌ {str(e)[:50]}")

print("🚀 Starting import with nba_api (more reliable)...\n")

try:
    supabase.table('player_game_logs').delete().neq('id', 0).execute()
    print("✅ Cleared existing data\n")
except:
    pass

teams_to_import = list(NBA_TEAMS.keys())[:5]  # Start with 5 teams

for team_key in teams_to_import:
    import_team(team_key)
    time.sleep(1)

print("\n✨ Import complete!")
