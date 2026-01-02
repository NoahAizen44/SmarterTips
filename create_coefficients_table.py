"""
Create the usage_model_coefficients table to store model results (Layer 3).
This table holds the final coefficients that will be used for predictions.
"""

import psycopg2

# Database connection
NEON_DSN = "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require"

def create_coefficients_table():
    """Create the usage_model_coefficients table"""
    
    conn = psycopg2.connect(NEON_DSN)
    cursor = conn.cursor()
    
    create_table_query = """
    CREATE TABLE IF NOT EXISTS usage_model_coefficients (
        player_id SERIAL,
        player_name VARCHAR(100),
        team_name VARCHAR(100),
        teammate_name VARCHAR(100),
        usage_delta DECIMAL(6,3),
        baseline_usage DECIMAL(6,3),
        p_value DECIMAL(10,8),
        games_used INTEGER,
        r_squared DECIMAL(5,3),
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        model_version VARCHAR(50),
        PRIMARY KEY (player_name, teammate_name, model_version)
    );
    
    CREATE INDEX IF NOT EXISTS idx_player_name ON usage_model_coefficients(player_name);
    CREATE INDEX IF NOT EXISTS idx_team_name ON usage_model_coefficients(team_name);
    CREATE INDEX IF NOT EXISTS idx_timestamp ON usage_model_coefficients(timestamp);
    """
    
    cursor.execute(create_table_query)
    conn.commit()
    
    print("✅ Created usage_model_coefficients table")
    print("\nTable structure:")
    print("  - player_name: Name of the target player (e.g., 'trae_young')")
    print("  - team_name: Team schema name (e.g., 'atlanta_hawks')")
    print("  - teammate_name: Name of teammate whose absence affects usage")
    print("  - usage_delta: How much usage changes when teammate is out")
    print("  - baseline_usage: Player's usage when all teammates play")
    print("  - p_value: Statistical significance")
    print("  - games_used: Number of games in the regression")
    print("  - r_squared: Model fit quality")
    print("  - timestamp: When the model was run")
    print("  - model_version: Version identifier (e.g., 'additive_v1')")
    
    cursor.close()
    conn.close()


if __name__ == "__main__":
    create_coefficients_table()
