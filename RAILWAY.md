# Railway setup (daily cron runner)

This repo’s “daily update” is a Python job (not a web server).
Railway can run it on a schedule (cron) so your computer doesn’t need to be on.

## 1) Create a Railway project

1. Go to Railway and create a **New Project**.
2. Choose **Deploy from GitHub repo**.
3. Select this repo.

Railway will detect Python and install dependencies from `requirements.txt`.

## 2) Add environment variables

In your Railway project:

- Settings → Variables → add:
  - `NEON_DSN` = your Neon Postgres connection string

Optional (defaults are fine):
- `NBA_API_TIMEOUT_SECONDS=45` (doesn’t need to be huge; ESPN fallback covers outages)
- `STRICT_DAILY_UPDATE=0` (best-effort; runner won’t fail the whole job)
- `STRICT_SCHEDULE_UPDATES=0` (schedule script won’t hard-fail if some teams fail)

## 3) Configure the service command

Set the start/cron command to run the daily runner:

- Command: `python run_daily_update.py`

This runs:
1. `daily_update_1_schedule.py`
2. `daily_update_2_usage.py`
3. `daily_update_3_game_logs.py`

## 4) Add a cron schedule

In Railway, add a **Cron** trigger for the service.

Examples:

- Run daily at 08:00 UTC (adjust as you like):
  - `0 8 * * *`

Notes:
- Cron uses UTC unless Railway specifies otherwise.
- Pick a time after most games finish for “yesterday” to be complete.

## 5) Verify logs

After the cron runs, open Railway logs. You should see sections like:

- `▶ Running step: schedule`
- `▶ Running step: usage`
- `▶ Running step: game_logs`

If `stats.nba.com` is blocked from where Railway runs, the schedule step should fall back to ESPN.

## Troubleshooting

### Missing Python dependency
If logs show `ModuleNotFoundError`, add it to `requirements.txt` and redeploy.

### Database connection fails
Confirm `NEON_DSN` is set in Railway variables and includes `sslmode=require`.

### Schedule still flakes
That’s usually `stats.nba.com`. ESPN fallback should keep scores/results moving, and the runner is best-effort so later steps still run.
