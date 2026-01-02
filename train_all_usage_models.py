"""
Train usage prediction models for all qualifying players across all 30 NBA teams.

Qualifications (same for target players and teammates):
- Average ≥ 22 MPG
- Missed > 3 games (provides variation in the data)
"""

import psycopg2
import pandas as pd
import statsmodels.api as sm
import numpy as np
from save_model_coefficients import save_coefficients
import time

# Database connection
NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

# All 30 NBA teams
TEAMS = [
    'atlanta_hawks', 'boston_celtics', 'brooklyn_nets', 'charlotte_hornets', 'chicago_bulls',
    'cleveland_cavaliers', 'dallas_mavericks', 'denver_nuggets', 'detroit_pistons', 'golden_state_warriors',
    'houston_rockets', 'indiana_pacers', 'la_clippers', 'los_angeles_lakers', 'memphis_grizzlies',
    'miami_heat', 'milwaukee_bucks', 'minnesota_timberwolves', 'new_orleans_pelicans', 'new_york_knicks',
    'oklahoma_city_thunder', 'orlando_magic', 'philadelphia_76ers', 'phoenix_suns', 'portland_trail_blazers',
    'sacramento_kings', 'san_antonio_spurs', 'toronto_raptors', 'utah_jazz', 'washington_wizards'
]

# Qualification criteria
MIN_MPG = 22.0
MIN_GAMES_MISSED = 3


def get_qualifying_players(conn, team_schema):
    """
    Get all players on a team who qualify for usage models.
    Returns list of (player_name, player_name_normalized, games_missed, avg_minutes)
    """
    
    query = f"""
    WITH schedule_games AS (
        SELECT COUNT(DISTINCT game_date) as total_team_games
        FROM {team_schema}.schedule
    )
    SELECT 
        psa.player_name,
        psa.gp as games_played,
        sg.total_team_games,
        (sg.total_team_games - psa.gp) as games_missed,
        psa.min_avg as avg_minutes
    FROM {team_schema}.player_season_averages psa
    CROSS JOIN schedule_games sg
    WHERE psa.min_avg >= {MIN_MPG}
      AND (sg.total_team_games - psa.gp) > {MIN_GAMES_MISSED}
    ORDER BY psa.min_avg DESC;
    """
    
    df = pd.read_sql(query, conn)
    
    # Normalize player names for table names
    qualified = []
    for _, row in df.iterrows():
        player_name = row['player_name']
        player_normalized = player_name.lower().replace(' ', '_').replace("'", "").replace(".", "").replace("-", "_")
        qualified.append((player_name, player_normalized, row['games_missed'], row['avg_minutes']))
    
    return qualified


def check_usage_table_exists(conn, team_schema, player_normalized):
    """Check if a usage table exists for this player"""
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = '{team_schema}' 
            AND table_name = '{player_normalized}'
        );
    """)
    exists = cursor.fetchone()[0]
    cursor.close()
    return exists


def train_usage_model(conn, team_schema, player_name, player_normalized, qualifying_teammates):
    """
    Train usage prediction model for one player.
    Returns (success, num_coefficients, r_squared, error_message)
    """
    
    try:
        # Get important teammates (exclude the target player)
        teammates = [
            (name, normalized) 
            for name, normalized, _, _ in qualifying_teammates 
            if normalized != player_normalized
        ]
        
        if len(teammates) == 0:
            return (False, 0, 0, "No qualifying teammates")
        
        # Build regression query
        teammate_cols = ", ".join([
            f"CASE WHEN s.{tm_norm} = FALSE THEN 1 ELSE 0 END as {tm_norm}_out"
            for _, tm_norm in teammates
        ])
        
        query = f"""
        SELECT 
            p.game_date,
            p.usage_percentage as usage,
            {teammate_cols}
        FROM {team_schema}.{player_normalized} p
        JOIN {team_schema}.schedule s 
            ON p.game_date = s.game_date
        WHERE p.minutes > 0
        ORDER BY p.game_date;
        """
        
        # Load data
        df = pd.read_sql(query, conn)
        
        if len(df) < 5:
            return (False, 0, 0, f"Insufficient data ({len(df)} games)")
        
        # Prepare regression
        y = df['usage']
        X = df[[f"{tm_norm}_out" for _, tm_norm in teammates]]
        X = sm.add_constant(X)
        
        # Fit model
        model = sm.OLS(y, X).fit()
        
        # Extract coefficients
        baseline_usage = float(model.params['const'])
        teammate_coeffs = {}
        p_values = {}
        
        for _, tm_norm in teammates:
            col = f"{tm_norm}_out"
            teammate_coeffs[tm_norm] = float(model.params[col])
            p_values[tm_norm] = float(model.pvalues[col])
        
        # Save to database
        count = save_coefficients(
            player_name=player_normalized,
            team_name=team_schema,
            baseline_usage=baseline_usage,
            teammate_coeffs=teammate_coeffs,
            p_values=p_values,
            games_used=len(df),
            r_squared=float(model.rsquared),
            model_version='additive_v1'
        )
        
        return (True, count, model.rsquared, None)
        
    except Exception as e:
        return (False, 0, 0, str(e))


def main():
    print("=" * 70)
    print("TRAINING USAGE PREDICTION MODELS FOR ALL QUALIFYING PLAYERS")
    print("=" * 70)
    print(f"\nQualifications: ≥{MIN_MPG} MPG, >{MIN_GAMES_MISSED} games missed\n")
    
    conn = psycopg2.connect(NEON_DSN)
    
    total_players = 0
    successful_models = 0
    failed_models = 0
    total_coefficients = 0
    
    start_time = time.time()
    
    for team_idx, team in enumerate(TEAMS, 1):
        print(f"\n[{team_idx}/30] {team.upper().replace('_', ' ')}")
        print("-" * 70)
        
        # Get qualifying players for this team
        qualifying_players = get_qualifying_players(conn, team)
        
        if len(qualifying_players) == 0:
            print(f"  ⚠️  No qualifying players found")
            continue
        
        print(f"  Found {len(qualifying_players)} qualifying players:")
        for name, norm, games_missed, mpg in qualifying_players:
            print(f"    • {name} ({mpg:.1f} MPG, {games_missed} games missed)")
        
        # Train model for each qualifying player
        for player_name, player_normalized, games_missed, mpg in qualifying_players:
            total_players += 1
            
            # Check if usage table exists
            if not check_usage_table_exists(conn, team, player_normalized):
                print(f"  ❌ {player_name}: No usage table")
                failed_models += 1
                continue
            
            # Train model
            success, num_coeffs, r_squared, error = train_usage_model(
                conn, team, player_name, player_normalized, qualifying_players
            )
            
            if success:
                print(f"  ✅ {player_name}: {num_coeffs} coefficients, R²={r_squared:.3f}")
                successful_models += 1
                total_coefficients += num_coeffs
            else:
                print(f"  ❌ {player_name}: {error}")
                failed_models += 1
    
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total players processed: {total_players}")
    print(f"Successful models: {successful_models}")
    print(f"Failed models: {failed_models}")
    print(f"Total coefficients saved: {total_coefficients}")
    print(f"Time elapsed: {elapsed:.1f} seconds")
    print(f"Average: {elapsed/max(total_players, 1):.2f} seconds per player")
    
    conn.close()
    print("\n✅ Complete!")


if __name__ == "__main__":
    main()
