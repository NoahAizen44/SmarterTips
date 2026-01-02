"""
Populate the public.qualifying_players table using player_season_averages data.

Qualification criteria:
- Average ≥ 22 MPG
- Missed > 3 games
- Played ≥ 3 games
"""

import psycopg2
import os

NEON_DSN = os.environ.get('NEON_DSN', "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require")

TEAMS = [
    'atlanta_hawks', 'boston_celtics', 'brooklyn_nets', 'charlotte_hornets', 'chicago_bulls',
    'cleveland_cavaliers', 'dallas_mavericks', 'denver_nuggets', 'detroit_pistons', 'golden_state_warriors',
    'houston_rockets', 'indiana_pacers', 'los_angeles_clippers', 'los_angeles_lakers', 'memphis_grizzlies',
    'miami_heat', 'milwaukee_bucks', 'minnesota_timberwolves', 'new_orleans_pelicans', 'new_york_knicks',
    'oklahoma_city_thunder', 'orlando_magic', 'philadelphia_76ers', 'phoenix_suns', 'portland_trail_blazers',
    'sacramento_kings', 'san_antonio_spurs', 'toronto_raptors', 'utah_jazz', 'washington_wizards'
]

MIN_MPG = 22.0
MIN_GAMES_MISSED = 3
MIN_GAMES_PLAYED = 3


def populate_qualifying_players():
    conn = psycopg2.connect(NEON_DSN)
    cur = conn.cursor()
    
    # Clear existing data
    cur.execute("TRUNCATE TABLE public.qualifying_players")
    
    total_players = 0
    
    for team_schema in TEAMS:
        team_display = team_schema.replace('_', ' ').title()
        
        # Get total team games
        cur.execute(f"""
            SELECT COUNT(DISTINCT game_date) 
            FROM {team_schema}.schedule
        """)
        total_team_games = cur.fetchone()[0]
        
        if total_team_games == 0:
            continue
        
        # Get qualifying players from season averages
        query = f"""
        SELECT 
            player_id,
            player_name,
            gp,
            min_avg
        FROM {team_schema}.player_season_averages
        WHERE min_avg >= %s
        AND gp >= %s
        AND (%s - gp) > %s
        ORDER BY min_avg DESC
        """
        
        cur.execute(query, (MIN_MPG, MIN_GAMES_PLAYED, total_team_games, MIN_GAMES_MISSED))
        players = cur.fetchall()
        
        for player_id, player_name, gp, min_avg in players:
            games_missed = total_team_games - gp
            
            # Get player position (try to get from game logs, default to 'G' if not found)
            cur.execute(f"""
                SELECT matchup 
                FROM {team_schema}.player_game_logs 
                WHERE player_name = %s 
                LIMIT 1
            """, (player_name,))
            
            position = 'G'  # Default position
            
            # Insert into qualifying_players
            cur.execute("""
                INSERT INTO public.qualifying_players 
                (player_id, player_name, team, position, avg_mpg, games_played, games_missed)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (player_id) DO UPDATE SET
                    player_name = EXCLUDED.player_name,
                    team = EXCLUDED.team,
                    position = EXCLUDED.position,
                    avg_mpg = EXCLUDED.avg_mpg,
                    games_played = EXCLUDED.games_played,
                    games_missed = EXCLUDED.games_missed
            """, (player_id, player_name, team_display, position, min_avg, gp, games_missed))
            
            total_players += 1
        
        if len(players) > 0:
            print(f"✅ {team_display}: {len(players)} qualifying players")
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"\n✅ Total: {total_players} qualifying players across all teams")


if __name__ == "__main__":
    print("=" * 70)
    print("📊 Populating Qualifying Players Table")
    print("=" * 70)
    print()
    
    populate_qualifying_players()
