"""
Helper functions to save regression model coefficients to Neon (Layer 3).
These functions can be imported into notebooks or scripts.
"""

import psycopg2
from datetime import datetime

NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

def save_coefficients(player_name, team_name, baseline_usage, teammate_coeffs, 
                      p_values, games_used, r_squared, model_version='additive_v1'):
    """
    Save regression model coefficients to the database.
    
    Args:
        player_name: Target player name (e.g., 'trae_young')
        team_name: Team schema name (e.g., 'atlanta_hawks')
        baseline_usage: Intercept/baseline usage percentage
        teammate_coeffs: Dict of {teammate_name: usage_delta}
        p_values: Dict of {teammate_name: p_value}
        games_used: Number of games in the regression
        r_squared: Model R-squared value
        model_version: Version identifier for the model
    
    Returns:
        Number of coefficients saved
    """
    
    conn = psycopg2.connect(NEON_DSN)
    conn.set_client_encoding('UTF8')
    cursor = conn.cursor()
    
    # Delete old coefficients for this player/version
    cursor.execute("""
        DELETE FROM usage_model_coefficients 
        WHERE player_name = %s AND model_version = %s
    """, (player_name, model_version))
    
    # Insert new coefficients
    count = 0
    for teammate_name, usage_delta in teammate_coeffs.items():
        p_value = p_values.get(teammate_name, None)
        
        cursor.execute("""
            INSERT INTO usage_model_coefficients 
            (player_name, team_name, teammate_name, usage_delta, baseline_usage, 
             p_value, games_used, r_squared, model_version)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (player_name, team_name, teammate_name, usage_delta, baseline_usage,
              p_value, games_used, r_squared, model_version))
        
        count += 1
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return count


def get_player_coefficients(player_name, model_version='additive_v1'):
    """
    Retrieve stored coefficients for a player.
    
    Args:
        player_name: Target player name
        model_version: Version identifier
    
    Returns:
        Dict with baseline_usage and teammate_deltas
    """
    
    conn = psycopg2.connect(NEON_DSN)
    conn.set_client_encoding('UTF8')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT teammate_name, usage_delta, baseline_usage, p_value
        FROM usage_model_coefficients
        WHERE player_name = %s AND model_version = %s
        ORDER BY ABS(usage_delta) DESC
    """, (player_name, model_version))
    
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not rows:
        return None
    
    baseline_usage = rows[0][2]  # Same for all rows
    teammate_deltas = {row[0]: {'delta': float(row[1]), 'p_value': float(row[3])} 
                       for row in rows}
    
    return {
        'baseline_usage': float(baseline_usage),
        'teammate_deltas': teammate_deltas
    }


def predict_usage(player_name, teammates_out, model_version='additive_v1'):
    """
    Predict usage percentage given which teammates are out.
    
    Args:
        player_name: Target player name
        teammates_out: List of teammate names who are out
        model_version: Version identifier
    
    Returns:
        Predicted usage percentage
    """
    
    coeffs = get_player_coefficients(player_name, model_version)
    
    if coeffs is None:
        return None
    
    predicted_usage = coeffs['baseline_usage']
    
    for teammate in teammates_out:
        if teammate in coeffs['teammate_deltas']:
            predicted_usage += coeffs['teammate_deltas'][teammate]['delta']
    
    return predicted_usage


if __name__ == "__main__":
    # Example usage
    print("Example: Saving Trae Young's coefficients")
    print("(Run this after training the model in the notebook)")
    
    # These would come from your regression results
    example_coeffs = {
        'jalen_johnson': 2.5,
        'kristaps_porzingis': 6.66,
        'vit_krejci': 11.38
    }
    
    example_p_values = {
        'jalen_johnson': 0.15,
        'kristaps_porzingis': 0.0166,
        'vit_krejci': 0.0016
    }
    
    count = save_coefficients(
        player_name='trae_young',
        team_name='atlanta_hawks',
        baseline_usage=17.96,
        teammate_coeffs=example_coeffs,
        p_values=example_p_values,
        games_used=10,
        r_squared=0.389
    )
    
    print(f"✅ Saved {count} coefficients")
    
    # Test retrieval
    print("\nRetrieving coefficients:")
    coeffs = get_player_coefficients('trae_young')
    print(f"Baseline usage: {coeffs['baseline_usage']:.2f}%")
    print("Teammate deltas:")
    for teammate, data in coeffs['teammate_deltas'].items():
        print(f"  {teammate}: +{data['delta']:.2f}% (p={data['p_value']:.4f})")
    
    # Test prediction
    print("\nPrediction when Krejci and Porzingis are out:")
    pred = predict_usage('trae_young', ['vit_krejci', 'kristaps_porzingis'])
    print(f"Predicted usage: {pred:.2f}%")
