"""
Usage Prediction Tool
=====================
Interactive tool to predict a player's usage % when specific teammates are out.
Only includes players who qualify (≥22 MPG, ≥3 games played, ≥3 games missed).

Usage:
    python predict_usage.py
"""

import psycopg2
from nba_api.stats.static import teams

NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

MIN_MPG = 22.0
MIN_GAMES_PLAYED = 3
MIN_GAMES_MISSED = 3


def normalize_name(name):
    """Convert player name to column name format."""
    return name.lower().replace(' ', '_').replace("'", '').replace('.', '').replace('-', '_')


def get_qualifying_players(conn, team_schema):
    """Get all players who qualify for predictions."""
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
    AND psa.gp >= %s
    AND (sg.total_team_games - psa.gp) >= %s
    ORDER BY psa.min_avg DESC
    """
    
    cur = conn.cursor()
    cur.execute(query, (MIN_MPG, MIN_GAMES_PLAYED, MIN_GAMES_MISSED))
    players = cur.fetchall()
    cur.close()
    
    return players


def get_prediction(conn, player_name, team_schema, teammates_out):
    """
    Predict usage % for a player given which teammates are out.
    
    Args:
        conn: Database connection
        player_name: Name of the player (e.g., "Jayson Tatum")
        team_schema: Team schema name (e.g., "boston_celtics")
        teammates_out: List of teammate names who are out
    
    Returns:
        dict with predicted_usage, baseline_usage, change
    """
    cur = conn.cursor()
    
    # Normalize names
    player_col = normalize_name(player_name)
    
    # Get baseline usage
    cur.execute("""
        SELECT baseline_usage
        FROM public.usage_model_coefficients
        WHERE player_id = %s
        AND team_name = %s
        LIMIT 1
    """, (player_col, team_schema))
    
    result = cur.fetchone()
    if not result:
        cur.close()
        return {"error": f"No model found for {player_name}"}
    
    baseline_usage = float(result[0])
    
    # Get coefficients for teammates who are out
    usage_deltas = []
    for teammate in teammates_out:
        teammate_normalized = normalize_name(teammate)
        
        cur.execute("""
            SELECT usage_delta, p_value
            FROM public.usage_model_coefficients
            WHERE player_id = %s
            AND team_name = %s
            AND teammate_name = %s
        """, (player_col, team_schema, teammate_normalized))
        
        coeff_result = cur.fetchone()
        if coeff_result:
            delta = float(coeff_result[0])
            p_value = float(coeff_result[1])
            usage_deltas.append({
                'teammate': teammate,
                'delta': delta,
                'p_value': p_value
            })
    
    cur.close()
    
    # Calculate predicted usage
    total_change = sum([d['delta'] for d in usage_deltas])
    predicted_usage = baseline_usage + total_change
    
    return {
        'player': player_name,
        'baseline_usage': round(baseline_usage, 2),
        'predicted_usage': round(predicted_usage, 2),
        'change': round(total_change, 2),
        'teammates_out': teammates_out,
        'deltas': usage_deltas
    }


def interactive_prediction():
    """Interactive CLI for usage predictions."""
    conn = psycopg2.connect(NEON_DSN)
    
    # Select team
    all_teams = teams.get_teams()
    print("\n🏀 NBA Usage Predictor")
    print("=" * 50)
    print("\nAvailable Teams:")
    for idx, team in enumerate(sorted(all_teams, key=lambda x: x['full_name']), 1):
        print(f"{idx:2d}. {team['full_name']}")
    
    team_choice = int(input("\nSelect team number: ")) - 1
    selected_team = sorted(all_teams, key=lambda x: x['full_name'])[team_choice]
    team_name = selected_team['full_name']
    team_schema = team_name.lower().replace(' ', '_')
    
    # Get qualifying players
    qualifying = get_qualifying_players(conn, team_schema)
    
    if not qualifying:
        print(f"\n❌ No qualifying players found for {team_name}")
        conn.close()
        return
    
    print(f"\n{team_name} - Qualifying Players:")
    print(f"{'#':<4} {'Player':<25} {'MPG':<8} {'GP':<6} {'Missed':<8}")
    print("-" * 60)
    for idx, (name, gp, total, missed, mpg) in enumerate(qualifying, 1):
        print(f"{idx:<4} {name:<25} {mpg:<8.1f} {gp:<6} {missed:<8}")
    
    # Select target player
    target_choice = int(input("\nSelect target player number: ")) - 1
    target_player = qualifying[target_choice][0]
    
    # Select teammates who are out
    print(f"\n{target_player} - Select teammates who are OUT:")
    print("(Enter numbers separated by commas, e.g., 1,3,5)")
    
    # Filter out target player from teammate list
    teammates = [p for p in qualifying if p[0] != target_player]
    print(f"\n{'#':<4} {'Player':<25} {'MPG':<8}")
    print("-" * 40)
    for idx, (name, gp, total, missed, mpg) in enumerate(teammates, 1):
        print(f"{idx:<4} {name:<25} {mpg:<8.1f}")
    
    out_input = input("\nTeammates out (or 0 for none): ").strip()
    
    teammates_out = []
    if out_input and out_input != '0':
        out_indices = [int(x.strip()) - 1 for x in out_input.split(',')]
        teammates_out = [teammates[i][0] for i in out_indices]
    
    # Get prediction
    result = get_prediction(conn, target_player, team_schema, teammates_out)
    
    if 'error' in result:
        print(f"\n❌ {result['error']}")
    else:
        print(f"\n{'=' * 60}")
        print(f"🎯 Usage Prediction for {result['player']}")
        print(f"{'=' * 60}")
        print(f"Baseline Usage: {result['baseline_usage']}%")
        
        if result['deltas']:
            print(f"\nImpact of Missing Teammates:")
            for delta_info in result['deltas']:
                sign = '+' if delta_info['delta'] > 0 else ''
                sig = '***' if delta_info['p_value'] < 0.05 else ''
                print(f"  • {delta_info['teammate']}: {sign}{delta_info['delta']:.2f}% {sig}")
        
        print(f"\n📈 Predicted Usage: {result['predicted_usage']}%")
        print(f"   Change: {result['change']:+.2f}%")
        print(f"{'=' * 60}\n")
    
    conn.close()


if __name__ == "__main__":
    interactive_prediction()
