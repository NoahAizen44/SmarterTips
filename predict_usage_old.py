"""
Usage Prediction Tool
=====================
Uses trained usage models to predict player usage when teammates are out.

Usage:
    from predict_usage import predict_player_usage
    
    result = predict_player_usage(
        player_name="Jayson Tatum",
        team_name="boston_celtics",
        out_teammates=["Jaylen Brown", "Kristaps Porzingis"]
    )
    
    print(f"Predicted usage: {result['predicted_usage']:.1f}%")
    print(f"Baseline usage: {result['baseline_usage']:.1f}%")
    print(f"Change: {result['usage_change']:.1f}%")
"""

import psycopg2
import os
from typing import List, Dict, Optional

# Get database connection
NEON_DSN = os.environ.get('NEON_DSN', "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require")


def normalize_name(name: str) -> str:
    """Convert player name to column name format."""
    return name.lower().replace(' ', '_').replace("'", '').replace('.', '').replace('-', '_')


def predict_player_usage(
    player_name: str,
    team_name: str,
    out_teammates: List[str],
    conn: Optional[psycopg2.extensions.connection] = None
) -> Dict:
    """
    Predict a player's usage when specific teammates are out.
    
    Args:
        player_name: Target player's name (e.g., "Jayson Tatum")
        team_name: Team schema name (e.g., "boston_celtics")
        out_teammates: List of teammate names who are out (e.g., ["Jaylen Brown"])
        conn: Optional DB connection (will create if not provided)
        
    Returns:
        Dictionary with:
            - predicted_usage: float
            - baseline_usage: float
            - usage_change: float
            - breakdown: dict of teammate impacts
            - confidence: str (based on p-values and sample size)
    """
    
    # Normalize names
    player_col = normalize_name(player_name)
    
    # Create connection if not provided
    close_conn = False
    if conn is None:
        conn = psycopg2.connect(NEON_DSN)
        close_conn = True
    
    try:
        cur = conn.cursor()
        
        # Get baseline usage
        cur.execute("""
            SELECT baseline_usage
            FROM public.usage_model_coefficients
            WHERE player_id = (
                SELECT player_id FROM public.usage_model_coefficients
                WHERE player_name = %s AND team_name = %s
                LIMIT 1
            )
            LIMIT 1
        """, (player_col, team_name))
        
        baseline_row = cur.fetchone()
        
        if not baseline_row:
            return {
                'error': f"No model found for {player_name} on {team_name}",
                'predicted_usage': None,
                'baseline_usage': None,
                'usage_change': None,
                'breakdown': {},
                'confidence': 'N/A'
            }
        
        baseline_usage = float(baseline_row[0])
        
        # Get coefficients for each out teammate
        usage_deltas = {}
        total_change = 0.0
        min_p_value = 1.0
        min_games = 999
        
        for teammate in out_teammates:
            teammate_normalized = normalize_name(teammate)
            
            cur.execute("""
                SELECT usage_delta, p_value, games_used
                FROM public.usage_model_coefficients
                WHERE player_name = %s
                AND team_name = %s
                AND teammate_name = %s
            """, (player_col, team_name, teammate_normalized))
            
            coeff_row = cur.fetchone()
            
            if coeff_row:
                usage_delta = float(coeff_row[0])
                p_value = float(coeff_row[1])
                games_used = int(coeff_row[2])
                
                usage_deltas[teammate] = {
                    'delta': usage_delta,
                    'p_value': p_value,
                    'games_used': games_used
                }
                
                total_change += usage_delta
                min_p_value = min(min_p_value, p_value)
                min_games = min(min_games, games_used)
            else:
                usage_deltas[teammate] = {
                    'delta': 0.0,
                    'p_value': 1.0,
                    'games_used': 0,
                    'note': 'No coefficient found'
                }
        
        predicted_usage = baseline_usage + total_change
        
        # Determine confidence level
        if min_games < 15:
            confidence = "Low (small sample)"
        elif min_p_value > 0.1:
            confidence = "Low (not statistically significant)"
        elif min_p_value > 0.05:
            confidence = "Medium"
        else:
            confidence = "High"
        
        cur.close()
        
        return {
            'predicted_usage': predicted_usage,
            'baseline_usage': baseline_usage,
            'usage_change': total_change,
            'breakdown': usage_deltas,
            'confidence': confidence,
            'out_teammates': out_teammates
        }
        
    finally:
        if close_conn:
            conn.close()


def get_team_roster_with_models(team_name: str) -> List[Dict]:
    """
    Get all players on a team who have usage models.
    
    Returns list of dicts with player info.
    """
    conn = psycopg2.connect(NEON_DSN)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT DISTINCT player_name, baseline_usage
        FROM public.usage_model_coefficients
        WHERE team_name = %s
        ORDER BY baseline_usage DESC
    """, (team_name,))
    
    players = []
    for row in cur.fetchall():
        players.append({
            'player_name': row[0],
            'baseline_usage': float(row[1])
        })
    
    cur.close()
    conn.close()
    
    return players


def get_player_teammates(player_name: str, team_name: str) -> List[str]:
    """
    Get all teammates that affect this player's usage (have coefficients).
    
    Returns list of teammate names.
    """
    player_col = normalize_name(player_name)
    
    conn = psycopg2.connect(NEON_DSN)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT teammate_name, usage_delta, p_value
        FROM public.usage_model_coefficients
        WHERE player_name = %s
        AND team_name = %s
        ORDER BY ABS(usage_delta) DESC
    """, (player_col, team_name))
    
    teammates = []
    for row in cur.fetchall():
        teammates.append({
            'name': row[0],
            'usage_delta': float(row[1]),
            'p_value': float(row[2])
        })
    
    cur.close()
    conn.close()
    
    return teammates


# Example usage
if __name__ == "__main__":
    # Example 1: Single prediction
    result = predict_player_usage(
        player_name="jayson_tatum",
        team_name="boston_celtics",
        out_teammates=["jaylen_brown"]
    )
    
    print("\n" + "="*60)
    print("Usage Prediction Example")
    print("="*60)
    
    if 'error' in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Player: Jayson Tatum")
        print(f"Out: {', '.join(result['out_teammates'])}")
        print(f"\nBaseline usage: {result['baseline_usage']:.1f}%")
        print(f"Predicted usage: {result['predicted_usage']:.1f}%")
        print(f"Change: {result['usage_change']:+.1f}%")
        print(f"Confidence: {result['confidence']}")
        
        print("\nBreakdown by teammate:")
        for teammate, data in result['breakdown'].items():
            print(f"  {teammate}: {data['delta']:+.1f}% (p={data['p_value']:.3f})")
