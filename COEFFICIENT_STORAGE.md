# Usage Model Coefficient Storage (Layer 3)

## Purpose
Store trained model coefficients permanently in Neon for fast predictions without re-running regressions.

## Three-Layer Architecture

### Layer 1: Raw Data (Permanent)
- `schedule` tables: Game schedules for each team
- `usage` tables: Historical player usage percentages  
- `player_season_averages`: Season stats for teammate identification

### Layer 2: Regression Tables (Temporary)
- Built on-demand by joining Layer 1 tables
- Lives in memory (pandas DataFrames)
- Thrown away after model training
- Example: Regression dataset with teammate_out indicators

### Layer 3: Model Coefficients (Permanent)
- **Table:** `usage_model_coefficients`
- Stores the final trained model parameters
- Used for real-time predictions on website
- **Why save?** Tiny (one row per teammate), fast lookups, no re-computation

## Table Structure

```sql
CREATE TABLE usage_model_coefficients (
    player_name VARCHAR(100),
    team_name VARCHAR(100),
    teammate_name VARCHAR(100),
    usage_delta DECIMAL(6,3),          -- How much usage changes
    baseline_usage DECIMAL(6,3),       -- Baseline when all play
    p_value DECIMAL(10,8),              -- Statistical significance
    games_used INTEGER,                 -- Sample size
    r_squared DECIMAL(5,3),             -- Model quality
    timestamp TIMESTAMP,
    model_version VARCHAR(50),
    PRIMARY KEY (player_name, teammate_name, model_version)
);
```

## Scripts

### 1. `create_coefficients_table.py`
Creates the storage table in Neon.

```bash
python3 create_coefficients_table.py
```

### 2. `save_model_coefficients.py`
Helper functions to save/retrieve coefficients:

```python
from save_model_coefficients import save_coefficients, get_player_coefficients, predict_usage

# Save after training
save_coefficients(
    player_name='trae_young',
    team_name='atlanta_hawks',
    baseline_usage=17.96,
    teammate_coeffs={'vit_krejci': 11.38, 'kristaps_porzingis': 6.66},
    p_values={'vit_krejci': 0.0016, 'kristaps_porzingis': 0.0166},
    games_used=10,
    r_squared=0.389
)

# Retrieve for predictions
coeffs = get_player_coefficients('trae_young')
# Returns: {'baseline_usage': 17.96, 'teammate_deltas': {...}}

# Make prediction
usage = predict_usage('trae_young', ['vit_krejci', 'kristaps_porzingis'])
# Returns: 35.99% (17.96 + 11.38 + 6.66)
```

### 3. `view_coefficients.py`
View stored coefficients:

```bash
python3 view_coefficients.py
```

### 4. Updated Notebook Cell 19
Now saves coefficients after training:

```python
from save_model_coefficients import save_coefficients

count = save_coefficients(
    player_name=PLAYER_NAME,
    team_name=TEAM_SCHEMA,
    baseline_usage=float(results.params[0]),
    teammate_coeffs=teammate_coeffs,
    p_values=p_values,
    games_used=len(df),
    r_squared=float(results.rsquared),
    model_version='additive_v1'
)
```

## Workflow

1. **Train Model** (in notebook or script)
   - Build regression dataset from Layer 1 tables
   - Run OLS regression on temporary DataFrame
   - Extract coefficients from results

2. **Save Coefficients** (Layer 3)
   - Call `save_coefficients()` function
   - Stores tiny amount of data (6 rows for Trae Young)
   - Old coefficients replaced on each run

3. **Make Predictions** (on website)
   - Load coefficients from Layer 3 (fast!)
   - Apply simple addition: baseline + sum of deltas
   - No need to rebuild regression tables or re-run OLS

## Example: Trae Young

**Stored:**
- Baseline: 17.96%
- jalen_johnson: +2.45%
- kristaps_porzingis: +6.66% (**)
- vit_krejci: +11.38% (**)
- (3 more teammates)

**Prediction when Krejčí out:**
- Usage = 17.96 + 11.38 = 29.34%

**Prediction when Krejčí and Porziņģis out:**
- Usage = 17.96 + 11.38 + 6.66 = 35.99%

## Next Steps

1. ✅ Created coefficient storage table
2. ✅ Created helper functions
3. ✅ Updated notebook to save coefficients
4. 🔄 Run notebook Cell 19 to save Trae Young's coefficients
5. ⏳ Build script to train models for all important players
6. ⏳ Add to daily automation
7. ⏳ Build prediction API using stored coefficients

