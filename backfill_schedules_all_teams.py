"""backfill_schedules_all_teams.py

One-off backfill for team schedule tables.

Problem this fixes
------------------
The original schedule creation/backfill populated schedule rows only up to some date.
`daily_update_1_schedule.py` historically *only updated existing rows* and didn't
insert new ones, so once new games occurred beyond the initial rows, schedules stopped
growing.

This script backfills *missing schedule rows* for a date range and then fills the
same metadata fields + player participation booleans as the daily updater.

Usage
-----
- Intended to be run manually when schedule tables are stale.
- Uses NEON_DSN from the environment when available.

Notes
-----
- It is safe to re-run: it uses upserts and updates by `game_date`.
- This uses NBA API endpoints which can be slow; be patient.
"""

from __future__ import annotations

import os
import time
from datetime import date, timedelta

import pandas as pd
import psycopg2
from nba_api.stats.endpoints import boxscoretraditionalv3, leaguegamefinder
from nba_api.stats.static import teams

NEON_DSN = os.environ.get(
    "NEON_DSN",
    "postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require",
)


def normalize_name(name: str) -> str:
    return (
        name.lower()
        .replace(" ", "_")
        .replace("'", "")
        .replace(".", "")
        .replace("-", "_")
    )


def retry_with_backoff(func, max_retries: int = 5, initial_delay: float = 2.0):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception:
            if attempt >= max_retries - 1:
                raise
            delay = initial_delay * (2**attempt)
            time.sleep(delay)


def ensure_schedule_row(cur, schema_name: str, game_date: date, game_id: str) -> None:
    cur.execute(
        f"""
        INSERT INTO {schema_name}.schedule (game_date, game_id)
        VALUES (%s, %s)
        ON CONFLICT (game_date) DO UPDATE SET
            game_id = EXCLUDED.game_id
        """,
        (game_date, game_id),
    )


def update_schedule_row(
    cur,
    schema_name: str,
    game_row: pd.Series,
    team_id: int,
    box_df: pd.DataFrame,
    players_who_played: set[str],
) -> int:
    # Get all player columns from schedule table
    cur.execute(
        f"""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s
          AND table_name = 'schedule'
          AND column_name NOT IN ('game_date', 'game_id', 'opponent', 'home_away',
                                  'result', 'team_score', 'opponent_score', 'created_at')
        """,
        (schema_name,),
    )
    all_player_columns = [row[0] for row in cur.fetchall()]

    update_parts = [
        f"{col} = {'TRUE' if col in players_who_played else 'FALSE'}" for col in all_player_columns
    ]

    matchup = game_row["MATCHUP"]
    if " @ " in matchup:
        home_away = "Away"
        opponent_abbrev = matchup.split(" @ ")[1]
    else:
        home_away = "Home"
        opponent_abbrev = matchup.split(" vs. ")[1]

    team_score = int(game_row["PTS"])

    opp_team_id = [t["id"] for t in teams.get_teams() if t["abbreviation"] == opponent_abbrev][0]

    if len(box_df[box_df["teamId"] == opp_team_id]) > 0:
        opponent_score = int(box_df[box_df["teamId"] == opp_team_id]["points"].sum())
    else:
        opponent_score = 0

    result = "W" if team_score > opponent_score else "L"

    game_date = pd.to_datetime(game_row["GAME_DATE"]).date()

    cur.execute(
        f"""
        UPDATE {schema_name}.schedule
        SET result = %s,
            team_score = %s,
            opponent_score = %s,
            opponent = %s,
            home_away = %s,
            {', '.join(update_parts)}
        WHERE game_date = %s
        """,
        (result, team_score, opponent_score, opponent_abbrev, home_away, game_date),
    )

    return len(players_who_played)


def backfill_team(team: dict, date_from: date, date_to: date) -> tuple[int, int]:
    team_id = team["id"]
    team_name = team["full_name"]
    schema_name = team_name.lower().replace(" ", "_")

    conn = psycopg2.connect(NEON_DSN)
    cur = conn.cursor()

    games_updated = 0
    rows_touched = 0

    try:
        def fetch_games():
            games = leaguegamefinder.LeagueGameFinder(
                team_id_nullable=str(team_id),
                date_from_nullable=date_from.strftime("%m/%d/%Y"),
                date_to_nullable=date_to.strftime("%m/%d/%Y"),
            )
            return games.get_data_frames()[0]

        games_df = retry_with_backoff(fetch_games, max_retries=5, initial_delay=2)
        if len(games_df) == 0:
            return (0, 0)

        for _, game_row in games_df.iterrows():
            game_id = str(game_row["GAME_ID"])
            game_date = pd.to_datetime(game_row["GAME_DATE"]).date()

            def fetch_box():
                box = boxscoretraditionalv3.BoxScoreTraditionalV3(game_id=game_id)
                return box.get_data_frames()[0]

            box_df = retry_with_backoff(fetch_box, max_retries=6, initial_delay=2)

            team_players = box_df[box_df["teamId"] == team_id]
            players_who_played: set[str] = set()

            for _, player in team_players.iterrows():
                minutes_str = str(player["minutes"]) if player["minutes"] else "0:00"
                if minutes_str != "0:00":
                    player_name = f"{player['firstName']} {player['familyName']}"
                    players_who_played.add(normalize_name(player_name))

            ensure_schedule_row(cur, schema_name, game_date, game_id)
            num_played = update_schedule_row(
                cur=cur,
                schema_name=schema_name,
                game_row=game_row,
                team_id=team_id,
                box_df=box_df,
                players_who_played=players_who_played,
            )

            conn.commit()
            games_updated += 1
            rows_touched += num_played

            # rate limit
            time.sleep(1.2)

    finally:
        cur.close()
        conn.close()

    return (games_updated, rows_touched)


def main():
    # We backfill the last N days. Increase if you need a deeper repair.
    days_back = int(os.environ.get("SCHEDULE_BACKFILL_DAYS", "10"))
    date_to = date.today()
    date_from = date_to - timedelta(days=days_back)

    all_teams = sorted(teams.get_teams(), key=lambda x: x["full_name"])

    print("=" * 70)
    print(f"📅 Schedule backfill (all teams): {date_from} → {date_to}")
    print("=" * 70)

    total_games = 0
    for idx, team in enumerate(all_teams, 1):
        print(f"[{idx}/30] {team['full_name']}...", end=" ", flush=True)
        try:
            games, _ = backfill_team(team, date_from=date_from, date_to=date_to)
            total_games += games
            print(f"✅ {games} games")
        except Exception as e:
            print(f"❌ {type(e).__name__}: {e}")
        time.sleep(0.6)

    print("=" * 70)
    print(f"✅ Done. Updated {total_games} games across all teams")
    print("=" * 70)


if __name__ == "__main__":
    main()
