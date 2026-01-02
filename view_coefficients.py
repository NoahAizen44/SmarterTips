"""
View stored model coefficients from the database.
"""

import psycopg2
import pandas as pd

NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

def view_all_coefficients():
    """Show all stored coefficients"""
    
    conn = psycopg2.connect(NEON_DSN)
    
    query = """
    SELECT 
        player_name,
        team_name,
        teammate_name,
        usage_delta,
        baseline_usage,
        p_value,
        games_used,
        r_squared,
        timestamp,
        model_version
    FROM usage_model_coefficients
    ORDER BY player_name, ABS(usage_delta) DESC
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    if len(df) == 0:
        print("No coefficients stored yet. Run the notebook to train a model!")
        return
    
    print(f"📊 Total coefficients stored: {len(df)}")
    print(f"   Players with models: {df['player_name'].nunique()}")
    print(f"   Teams: {df['team_name'].nunique()}")
    print()
    
    # Group by player
    for player in df['player_name'].unique():
        player_df = df[df['player_name'] == player]
        baseline = player_df['baseline_usage'].iloc[0]
        r_squared = player_df['r_squared'].iloc[0]
        games = player_df['games_used'].iloc[0]
        
        print(f"\n{'='*60}")
        print(f"Player: {player.upper()}")
        print(f"Team: {player_df['team_name'].iloc[0]}")
        print(f"Baseline usage: {baseline:.2f}%")
        print(f"R² = {r_squared:.3f}, Games = {games}")
        print(f"{'='*60}")
        
        for _, row in player_df.iterrows():
            delta = row['usage_delta']
            p_val = row['p_value']
            
            # Significance stars
            if p_val < 0.001:
                sig = "***"
            elif p_val < 0.01:
                sig = "**"
            elif p_val < 0.05:
                sig = "*"
            else:
                sig = ""
            
            sign = "+" if delta > 0 else ""
            print(f"  {row['teammate_name']:30s}: {sign}{delta:6.2f}% (p={p_val:.4f}) {sig}")


def view_player_coefficients(player_name):
    """Show coefficients for a specific player"""
    
    conn = psycopg2.connect(NEON_DSN)
    
    query = """
    SELECT 
        teammate_name,
        usage_delta,
        baseline_usage,
        p_value,
        games_used,
        r_squared
    FROM usage_model_coefficients
    WHERE player_name = %s
    ORDER BY ABS(usage_delta) DESC
    """
    
    df = pd.read_sql(query, conn, params=(player_name,))
    conn.close()
    
    if len(df) == 0:
        print(f"No coefficients found for {player_name}")
        return None
    
    baseline = df['baseline_usage'].iloc[0]
    r_squared = df['r_squared'].iloc[0]
    games = df['games_used'].iloc[0]
    
    print(f"\n{player_name.upper()}")
    print(f"Baseline: {baseline:.2f}%, R² = {r_squared:.3f}, Games = {games}")
    print("\nTeammate Effects:")
    
    for _, row in df.iterrows():
        delta = row['usage_delta']
        p_val = row['p_value']
        
        if p_val < 0.001:
            sig = "***"
        elif p_val < 0.01:
            sig = "**"
        elif p_val < 0.05:
            sig = "*"
        else:
            sig = ""
        
        sign = "+" if delta > 0 else ""
        print(f"  {row['teammate_name']:30s}: {sign}{delta:6.2f}% (p={p_val:.4f}) {sig}")
    
    return df


if __name__ == "__main__":
    view_all_coefficients()
