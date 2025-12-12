#!/usr/bin/env python3
"""Import NBA defense stats from CSV files into Supabase."""

import csv
import os
from datetime import datetime
from supabase import create_client, Client

# Initialize Supabase client
url = os.environ.get('SUPABASE_URL', 'https://vszmsnikixfdakwzuown.supabase.co')
key = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZzem1zbmlraXhmZGFrd3p1b3duIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUyMjU1NTEsImV4cCI6MjA4MDgwMTU1MX0.oiSiA_LLjfVBh2kr-aqiFyLs6Jn-YK6_1X5t6S-SzY4')
supabase: Client = create_client(url, key)

# Map team names to match what's expected in the UI
TEAM_NAME_MAP = {
    'Los Angeles Clippers': 'LA Clippers',
    'Los Angeles Lakers': 'LA Lakers',
    'Golden State': 'Golden State',
}

def normalize_team_name(team):
    """Normalize team names to match the UI."""
    return TEAM_NAME_MAP.get(team, team)

def import_csv_file(csv_path, time_period):
    """Import a single CSV file into Supabase."""
    print(f"\n📂 Importing {csv_path} (time_period: {time_period})...")
    
    if not os.path.exists(csv_path):
        print(f"❌ File not found: {csv_path}")
        return 0
    
    rows_to_insert = []
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            team = normalize_team_name(row['Team'])
            position = row['Position']
            
            # Insert one row per stat
            for stat in ['PTS', 'REB', 'AST', '3PM', 'STL', 'BLK']:
                if stat in row:
                    try:
                        value = float(row[stat])
                        rows_to_insert.append({
                            'team': team,
                            'position': position,
                            'stat_name': stat,
                            'value': value,
                            'time_period': time_period,
                            'scraped_at': datetime.utcnow().isoformat()
                        })
                    except ValueError:
                        continue
    
    # Insert in batches of 1000 to avoid timeout
    batch_size = 1000
    total_inserted = 0
    
    for i in range(0, len(rows_to_insert), batch_size):
        batch = rows_to_insert[i:i+batch_size]
        try:
            response = supabase.table('nba_stats').insert(batch).execute()
            total_inserted += len(batch)
            print(f"✅ Inserted {len(batch)} rows ({total_inserted}/{len(rows_to_insert)} total)")
        except Exception as e:
            print(f"❌ Error inserting batch: {e}")
            return total_inserted
    
    return total_inserted

def main():
    """Main import function."""
    print("🚀 Starting NBA stats import to Supabase...")
    
    base_path = '/Users/noaha/NBA_PROGRAMS/defvspos'
    
    csv_files = [
        (f'{base_path}/nba_defense_data_2025-26.csv', '2025-26'),
        (f'{base_path}/nba_defense_data_last15.csv', 'Last 15'),
        (f'{base_path}/nba_defense_data_last7.csv', 'Last 7'),
    ]
    
    total_rows = 0
    
    # Clear existing data first
    try:
        print("\n🗑️  Clearing existing nba_stats data...")
        supabase.table('nba_stats').delete().neq('id', 0).execute()
        print("✅ Cleared existing data")
    except Exception as e:
        print(f"⚠️  Could not clear existing data: {e}")
    
    # Import each CSV file
    for csv_path, time_period in csv_files:
        rows = import_csv_file(csv_path, time_period)
        total_rows += rows
    
    print(f"\n✨ Import complete! Total rows inserted: {total_rows}")
    
    # Verify the data
    try:
        response = supabase.table('nba_stats').select('count').execute()
        print(f"📊 Verified: Database now contains {response.count} rows")
    except Exception as e:
        print(f"⚠️  Could not verify: {e}")

if __name__ == '__main__':
    main()
