#!/usr/bin/env python3
"""
Import real NBA player game logs using ESPN API (no auth required)
"""

import os
import requests
import json
from datetime import datetime, timedelta
from supabase import create_client
import time

# Initialize Supabase
url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

if not url or not key:
    print("❌ Error: Environment variables not set")
    exit(1)

supabase = create_client(url, key)

# ESPN API endpoints
ESPN_API = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"

TEAMS = [
    {"name": "Boston Celtics", "espn_id": "25"},
    {"name": "Denver Nuggets", "espn_id": "27"},
    {"name": "LA Lakers", "espn_id": "27"},  # Will need correct ID
]

def get_team_schedule(team_id, year=2025):
    """Get team schedule and game stats"""
    print(f"\n📥 Fetching data for team...")
    
    try:
        # Fetch team schedule
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"✅ Got team data")
        return data
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

# Test ESPN API
print("Testing ESPN API...")
response = requests.get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams", timeout=10)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    teams = response.json()["teams"]
    print(f"✅ Found {len(teams)} teams")
    for team in teams[:5]:
        print(f"  - {team['name']} (ID: {team['id']})")
else:
    print("❌ Failed to get teams")
