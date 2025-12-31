"""
Daily Update Master Script
===========================
Runs all daily update scripts in sequence:
1. Updates team schedules with game results and player participation
2. Updates player usage tables with usage data and DNP entries
3. Updates player game logs with detailed stats

Usage:
  python3 daily_update_master.py              # Updates today's games
  python3 daily_update_master.py 2025-12-31  # Updates specific date
"""

import sys
from datetime import datetime, date
import subprocess

def run_script(script_name, script_desc):
    """Run a Python script and return success status"""
    print()
    print("=" * 70)
    print(f"Running: {script_desc}")
    print("=" * 70)
    
    result = subprocess.run(['python3', script_name], capture_output=False)
    
    if result.returncode == 0:
        print(f"✅ {script_desc} completed successfully")
        return True
    else:
        print(f"❌ {script_desc} failed with exit code {result.returncode}")
        return False

def main():
    # Parse date argument if provided
    if len(sys.argv) > 1:
        target_date_str = sys.argv[1]
        try:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            print(f"📅 Running daily updates for: {target_date}")
        except ValueError:
            print("❌ Invalid date format. Use: YYYY-MM-DD")
            return
    else:
        target_date = date.today()
        print(f"📅 Running daily updates for today: {target_date}")
    
    print()
    print("🏀 NBA Daily Update Process")
    print("=" * 70)
    
    # Step 1: Update schedules
    success1 = run_script('daily_update_1_schedule.py', 'Step 1: Team Schedules')
    
    if not success1:
        print()
        print("⚠️  Schedule update failed. Stopping here.")
        return
    
    # Step 2: Update usage tables
    success2 = run_script('daily_update_2_usage.py', 'Step 2: Player Usage Tables')
    
    if not success2:
        print()
        print("⚠️  Usage update failed. Stopping here.")
        return
    
    # Step 3: Update game logs
    success3 = run_script('daily_update_3_game_logs.py', 'Step 3: Player Game Logs')
    
    print()
    print("=" * 70)
    if success1 and success2 and success3:
        print("✅ Daily update complete! All data is current.")
    else:
        print("⚠️  Daily update completed with some errors.")
    print("=" * 70)

if __name__ == "__main__":
    main()
