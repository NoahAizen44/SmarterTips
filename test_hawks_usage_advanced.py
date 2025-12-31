"""
Test Fill Player Usage from BoxScoreAdvancedV3 - Hawks Only
============================================================
Uses real NBA usage percentage from BoxScoreAdvancedV3
"""

import psycopg2
from nba_api.stats.endpoints import boxscoreadvancedv3, leaguegamefinder
import pandas as pd
import time

NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

def normalize_name(name):
    """Convert player name to table name format"""
    return name.lower().replace(' ', '_').replace("'", '').replace('.', '').replace('-', '_')

def main():
    print("=" * 70)
    print("🏀 Testing Player Usage Tables - Atlanta Hawks")
    print("=" * 70)
    print()
    
    team_id = 1610612737  # Hawks
    schema_name = "atlanta_hawks"
    
    # Connect to DB
    conn = psycopg2.connect(NEON_DSN)
    cur = conn.cursor()
    
    try:
        # Get Hawks game IDs from their schedule
        print("Fetching Hawks games...")
        games = leaguegamefinder.LeagueGameFinder(team_id_nullable=str(team_id))
        games_df = games.get_data_frames()[0]
        games_df = games_df[games_df['SEASON_ID'] == '22025']
        games_df['GAME_DATE'] = pd.to_datetime(games_df['GAME_DATE'])
        games_df = games_df[games_df['GAME_DATE'] >= '2025-10-01']
        
        print(f"✅ Found {len(games_df)} games\n")
        
        # Get player columns from team schedule table (source of truth for roster)
        cur.execute(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = '{schema_name}' 
            AND table_name = 'schedule'
            AND column_name NOT IN ('game_date', 'game_id', 'opponent', 'home_away', 
                                     'result', 'team_score', 'opponent_score', 'created_at')
            ORDER BY column_name
        """)
        
        player_columns = [row[0] for row in cur.fetchall()]
        # Convert column names back to actual player names
        players = [col.replace('_', ' ').title() for col in player_columns]
        
        print(f"Found {len(players)} players from schedule table\n")
        
        # Create/clear usage tables for each player
        for player_name in players:
            table_name = f"{normalize_name(player_name)}_usage"
            cur.execute(f"DROP TABLE IF EXISTS {schema_name}.{table_name} CASCADE")
            cur.execute(f"""
                CREATE TABLE {schema_name}.{table_name} (
                    id SERIAL PRIMARY KEY,
                    game_date DATE NOT NULL UNIQUE,
                    minutes FLOAT,
                    usage_percentage FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        conn.commit()
        print(f"✅ Created {len(players)} usage tables\n")
        
        # Process each game
        print("Processing games...")
        for idx, game_row in games_df.iterrows():
            game_id = str(game_row['GAME_ID'])
            game_date = game_row['GAME_DATE'].date()
            
            print(f"  {game_date} (ID: {game_id})...", end=" ", flush=True)
            
            try:
                # Get advanced box score with usage
                adv_box = boxscoreadvancedv3.BoxScoreAdvancedV3(game_id=game_id)
                adv_df = adv_box.get_data_frames()[0]
                
                # Filter for Hawks players
                hawks_players = adv_df[adv_df['teamId'] == team_id]
                
                # Insert usage for each player
                inserted = 0
                for _, player in hawks_players.iterrows():
                    player_name = f"{player['firstName']} {player['familyName']}"
                    usage_pct = player['usagePercentage'] * 100  # Convert to percentage
                    
                    # Convert minutes from MM:SS to decimal
                    minutes_played = 0
                    if player['minutes']:
                        time_parts = str(player['minutes']).split(':')
                        if len(time_parts) == 2:
                            minutes_played = int(time_parts[0]) + int(time_parts[1])/60
                    
                    table_name = f"{normalize_name(player_name)}_usage"
                    
                    cur.execute(f"""
                        INSERT INTO {schema_name}.{table_name} (game_date, minutes, usage_percentage)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (game_date) DO UPDATE SET
                            minutes = EXCLUDED.minutes,
                            usage_percentage = EXCLUDED.usage_percentage
                    """, (game_date, minutes_played, usage_pct))
                    inserted += 1
                
                conn.commit()
                print(f"✅ {inserted} players")
                time.sleep(0.8)  # Rate limit
                
            except Exception as e:
                print(f"❌ {str(e)[:50]}")
                continue
        
        print("\n" + "=" * 70)
        print("Verifying data...")
        print("=" * 70)
        
        # Show sample data for a few players
        for player_name in players[:3]:
            table_name = f"{normalize_name(player_name)}_usage"
            cur.execute(f"""
                SELECT game_date, minutes, usage_percentage
                FROM {schema_name}.{table_name}
                ORDER BY game_date DESC
                LIMIT 5
            """)
            rows = cur.fetchall()
            print(f"\n{player_name} (last 5 games):")
            for date, mins, usage in rows:
                print(f"  {date}: {mins:.1f} min, {usage:.2f}% usage")
        
        print("\n" + "=" * 70)
        print("✅ Test complete!")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
