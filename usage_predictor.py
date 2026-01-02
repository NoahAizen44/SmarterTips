"""
Usage Prediction Tool
=====================
Interactive tool to predict player usage when teammates are out.

Usage:
    python usage_predictor.py
"""

import psycopg2
import os

NEON_DSN = os.environ.get('NEON_DSN', "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require")


def get_teams_with_models():
    """Get list of teams that have trained models."""
    conn = psycopg2.connect(NEON_DSN)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT DISTINCT team_name 
        FROM public.usage_model_coefficients 
        ORDER BY team_name
    """)
    
    teams = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    
    return teams


def get_qualifying_players_for_team(team_schema):
    """Get qualifying players for a team who have trained models."""
    conn = psycopg2.connect(NEON_DSN)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT DISTINCT player_name
        FROM public.usage_model_coefficients 
        WHERE team_name = %s
        ORDER BY player_name
    """, (team_schema,))
    
    players = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    
    return players


def get_teammates_for_player(player_col, team_schema):
    """Get teammates who have impact coefficients for this player."""
    conn = psycopg2.connect(NEON_DSN)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT teammate_name, usage_delta, p_value, baseline_usage
        FROM public.usage_model_coefficients 
        WHERE player_name = %s AND team_name = %s
        ORDER BY ABS(usage_delta) DESC
    """, (player_col, team_schema))
    
    teammates = []
    baseline = None
    
    for row in cur.fetchall():
        teammate_name, usage_delta, p_value, baseline_usage = row
        if baseline is None:
            baseline = float(baseline_usage)
        teammates.append({
            'name': teammate_name,
            'usage_delta': float(usage_delta),
            'p_value': float(p_value)
        })
    
    cur.close()
    conn.close()
    
    return teammates, baseline


def predict_usage(player_col, team_schema, injured_teammates):
    """Predict usage for a player given list of injured teammates."""
    teammates, baseline = get_teammates_for_player(player_col, team_schema)
    
    if baseline is None:
        return None, None
    
    # Calculate predicted usage
    predicted_usage = baseline
    impacts = []
    
    for teammate in teammates:
        if teammate['name'] in injured_teammates:
            predicted_usage += teammate['usage_delta']
            impacts.append({
                'teammate': teammate['name'],
                'impact': teammate['usage_delta'],
                'p_value': teammate['p_value']
            })
    
    return predicted_usage, impacts


def main():
    print("=" * 70)
    print("🏀 NBA Usage Prediction Tool")
    print("=" * 70)
    print()
    
    # Step 1: Select team
    teams = get_teams_with_models()
    
    print(f"Found {len(teams)} teams with trained models")
    print("\nSelect a team (type the name or part of it):")
    
    for i, team in enumerate(teams, 1):
        display_name = team.replace('_', ' ').title()
        print(f"  {i}. {display_name}")
    
    team_input = input("\nTeam: ").strip().lower()
    
    # Find matching team
    selected_team = None
    for team in teams:
        if team_input in team or team_input in team.replace('_', ' '):
            selected_team = team
            break
    
    if not selected_team:
        print("❌ Team not found")
        return
    
    team_display = selected_team.replace('_', ' ').title()
    print(f"\n✅ Selected: {team_display}")
    print()
    
    # Step 2: Select target player
    players = get_qualifying_players_for_team(selected_team)
    
    if not players:
        print(f"❌ No qualifying players found for {team_display}")
        return
    
    print(f"Qualifying players on {team_display}:")
    for i, player in enumerate(players, 1):
        print(f"  {i}. {player}")
    
    player_input = input("\nTarget player: ").strip().lower()
    
    # Find matching player
    selected_player = None
    for player in players:
        if player_input in player.lower():
            selected_player = player
            break
    
    if not selected_player:
        print("❌ Player not found")
        return
    
    print(f"\n✅ Selected: {selected_player}")
    print()
    
    # Step 3: Get teammates and their impacts
    teammates, baseline = get_teammates_for_player(selected_player, selected_team)
    
    if not teammates:
        print(f"❌ No model found for {selected_player}")
        return
    
    print(f"Baseline usage: {baseline:.1f}%")
    print()
    print("Teammates with impact on usage:")
    for i, tm in enumerate(teammates, 1):
        sign = "+" if tm['usage_delta'] > 0 else ""
        significant = " *" if tm['p_value'] < 0.05 else ""
        print(f"  {i}. {tm['name']}: {sign}{tm['usage_delta']:.2f}%{significant}")
    
    print("\n(* = statistically significant, p < 0.05)")
    print()
    
    # Step 4: Select injured/out teammates
    print("Select teammates who are OUT (comma-separated numbers, or press Enter to skip):")
    injured_input = input("Out: ").strip()
    
    injured_teammates = []
    if injured_input:
        try:
            indices = [int(x.strip()) - 1 for x in injured_input.split(',')]
            injured_teammates = [teammates[i]['name'] for i in indices if 0 <= i < len(teammates)]
        except:
            print("Invalid input, skipping...")
    
    # Step 5: Calculate and display prediction
    print()
    print("=" * 70)
    predicted_usage, impacts = predict_usage(selected_player, selected_team, injured_teammates)
    
    if predicted_usage is None:
        print("❌ Could not calculate prediction")
        return
    
    print(f"🎯 PREDICTION for {selected_player}")
    print("=" * 70)
    print(f"\nBaseline usage: {baseline:.1f}%")
    
    if impacts:
        print("\nImpacts from missing teammates:")
        total_impact = 0
        for impact in impacts:
            sign = "+" if impact['impact'] > 0 else ""
            sig = " (significant)" if impact['p_value'] < 0.05 else ""
            print(f"  {impact['teammate']}: {sign}{impact['impact']:.2f}%{sig}")
            total_impact += impact['impact']
        
        print(f"\nTotal impact: {'+' if total_impact > 0 else ''}{total_impact:.2f}%")
    else:
        print("\nNo teammates selected as out")
    
    print(f"\n📊 Predicted usage: {predicted_usage:.1f}%")
    print()


if __name__ == "__main__":
    main()
