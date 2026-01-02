#!/usr/bin/env python3
"""Create sample player game logs data for testing."""

from datetime import datetime, timedelta
from supabase import create_client, Client
import os
import random

url = os.environ.get('SUPABASE_URL', 'https://vszmsnikixfdakwzuown.supabase.co')
key = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZzem1zbmlraXhmZGFrd3p1b3duIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUyMjU1NTEsImV4cCI6MjA4MDgwMTU1MX0.oiSiA_LLjfVBh2kr-aqiFyLs6Jn-YK6_1X5t6S-SzY4')
supabase: Client = create_client(url, key)

# Sample data
teams = [
    {'name': 'Boston Celtics', 'players': ['Jayson Tatum', 'Jaylen Brown', 'Derrick White', 'Jrue Holiday', 'Kristaps Porzingis']},
    {'name': 'Denver Nuggets', 'players': ['Nikola Jokic', 'Jamal Murray', 'Michael Porter Jr', 'Christian Braun', 'Peyton Watson']},
    {'name': 'LA Lakers', 'players': ['LeBron James', 'Anthony Davis', 'Austin Reaves', 'Rui Hachimura', 'D Angelo Russell']},
]

sample_data = []
game_id_counter = 1

for team in teams:
    team_name = team['name']
    players = team['players']
    
    # Create 30 sample games
    for game_num in range(30):
        game_date = (datetime.now() - timedelta(days=30-game_num)).strftime('%m/%d/%Y')
        game_id = f"{2025122601}{game_id_counter:02d}"
        game_id_counter += 1
        
        # Randomly select which player is "absent" (didn't play)
        absent_player_idx = random.randint(0, len(players)-1)
        
        for player_idx, player_name in enumerate(players):
            # If this is the "absent" player, skip 1 out of 3 times
            if player_idx == absent_player_idx and random.random() > 0.33:
                continue
            
            # Generate realistic stats
            if player_idx == absent_player_idx:
                # When absent, higher stats for teammates
                pts = random.randint(12, 28)
                reb = random.randint(3, 12)
                ast = random.randint(1, 8)
            else:
                # Normal stats
                pts = random.randint(8, 22)
                reb = random.randint(2, 10)
                ast = random.randint(1, 6)
            
            sample_data.append({
                'team': team_name,
                'player_id': 100000 + players.index(player_name),
                'player_name': player_name,
                'position': ['PG', 'SG', 'SF', 'PF', 'C'][players.index(player_name) % 5],
                'game_date': game_date,
                'game_id': game_id,
                'pts': pts,
                'reb': reb,
                'ast': ast,
                '3pm': random.randint(0, 5),
                '3pa': random.randint(1, 10),
                'stl': random.randint(0, 3),
                'blk': random.randint(0, 3),
                'season': '2025-26',
                'imported_at': datetime.utcnow().isoformat()
            })

print(f"📊 Generated {len(sample_data)} sample records")
print(f"🚀 Inserting into Supabase...")

try:
    # Insert in batches
    batch_size = 100
    for i in range(0, len(sample_data), batch_size):
        batch = sample_data[i:i+batch_size]
        response = supabase.table('player_game_logs').insert(batch).execute()
        print(f"✅ Inserted batch {i//batch_size + 1}")
    
    print(f"\n✨ Successfully inserted {len(sample_data)} sample records!")
    print("You can now test the Teammate Impact tool with this sample data.")
except Exception as e:
    print(f"❌ Error inserting: {e}")
