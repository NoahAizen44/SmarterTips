"""
Daily Update Script #5: Retrain Usage Prediction Models
========================================================
Retrains usage models for all qualifying players as new games are played.
This keeps the models current with recent performance trends.

Run this AFTER daily_update_4_season_averages.py (or weekly/bi-weekly for efficiency)
"""

import psycopg2
import pandas as pd
import statsmodels.api as sm
import os
from datetime import datetime
from save_model_coefficients import save_coefficients

# Get database connection from environment variable or use default
NEON_DSN = os.environ.get('NEON_DSN', "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require")

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
    """Get all players who qualify for usage models."""
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
    WHERE psa.min_avg >= %s
    AND (sg.total_team_games - psa.gp) > %s
    ORDER BY psa.min_avg DESC
    """
    
    df = pd.read_sql_query(query, conn, params=(MIN_MPG, MIN_GAMES_MISSED))
    return df


def normalize_name(name):
    """Convert player name to column name format."""
    return name.lower().replace(' ', '_').replace("'", '').replace('.', '').replace('-', '_')


def train_usage_model(conn, team_schema, target_player_col, teammate_cols):
    """Train OLS model for target player's usage based on teammate participation."""
    query = f"""
    SELECT 
        game_date,
        {target_player_col}_usage as target_usage,
        {', '.join([f'{tm} as {tm}_played' for tm in teammate_cols])}
    FROM {team_schema}.schedule s
    WHERE {target_player_col} = TRUE
    ORDER BY game_date
    """
    
    try:
        df = pd.read_sql_query(query, conn)
        
        if len(df) < 10:
            return None
        
        # Prepare features
        X = df[[f'{tm}_played' for tm in teammate_cols]].astype(int)
        X = sm.add_constant(X)
        y = df['target_usage']
        
        # Fit model
        model = sm.OLS(y, X).fit()
        
        return {
            'model': model,
            'n_games': len(df),
            'baseline_usage': model.params['const'],
            'r_squared': model.rsquared
        }
        
    except Exception as e:
        return None


def train_models_for_team(conn, team_schema):
    """Train usage models for all qualifying players on a team."""
    # Get qualifying players
    target_players = get_qualifying_players(conn, team_schema)
    
    if target_players.empty:
        return 0
    
    # Normalize names
    target_players['player_col'] = target_players['player_name'].apply(normalize_name)
    
    models_trained = 0
    
    for _, target_row in target_players.iterrows():
        target_col = target_row['player_col']
        target_name = target_row['player_name']
        
        # Get teammates (all other qualifying players)
        teammate_players = target_players[target_players['player_col'] != target_col]
        teammate_cols = teammate_players['player_col'].tolist()
        
        if len(teammate_cols) == 0:
            continue
        
        # Train model
        result = train_usage_model(conn, team_schema, target_col, teammate_cols)
        
        if result is None:
            continue
        
        model = result['model']
        
        # Save coefficients for each teammate
        for teammate_col in teammate_cols:
            coeff_key = f'{teammate_col}_played'
            if coeff_key not in model.params:
                continue
            
            teammate_name = teammate_players[teammate_players['player_col'] == teammate_col]['player_name'].iloc[0]
            
            usage_delta = model.params[coeff_key]
            p_value = model.pvalues[coeff_key]
            
            save_coefficients(
                conn=conn,
                player_col=target_col,
                player_name=target_name,
                team_name=team_schema,
                teammate_name=teammate_name,
                usage_delta=usage_delta,
                baseline_usage=result['baseline_usage'],
                p_value=p_value,
                games_used=result['n_games'],
                r_squared=result['r_squared']
            )
        
        models_trained += 1
    
    return models_trained


def main():
    print("=" * 70)
    print(f"🤖 Daily Update #5: Retrain Usage Prediction Models")
    print(f"Started: {datetime.now()}")
    print("=" * 70)
    print()
    
    conn = psycopg2.connect(NEON_DSN)
    
    total_models = 0
    teams_processed = 0
    
    for idx, team_schema in enumerate(TEAMS, 1):
        team_display = team_schema.replace('_', ' ').title()
        print(f"[{idx}/30] {team_display}...", end=" ", flush=True)
        
        try:
            models_count = train_models_for_team(conn, team_schema)
            
            if models_count > 0:
                print(f"✅ Trained {models_count} models")
                total_models += models_count
                teams_processed += 1
            else:
                print("- No qualifying players")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            continue
    
    conn.close()
    
    print()
    print("=" * 70)
    print(f"✅ Complete! Trained {total_models} models across {teams_processed} teams")
    print(f"Finished: {datetime.now()}")
    print("=" * 70)


if __name__ == "__main__":
    main()
