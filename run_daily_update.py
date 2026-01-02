"""Railway-friendly daily runner.

This runs the 3 daily update steps in order:
  1) Schedule
  2) Usage
  3) Game logs

Design goals:
- Single command entrypoint (good for Railway cron)
- Clear logs
- Non-blocking: one step failure shouldn't prevent the others (configurable)

Env vars:
- NEON_DSN: Postgres connection string
- STRICT_DAILY_UPDATE=1 to hard-fail if any step fails (default: best-effort)
- STRICT_SCHEDULE_UPDATES=1 is honored by daily_update_1_schedule.py

Usage:
  python run_daily_update.py
"""

from __future__ import annotations

import importlib
import os
import sys
import traceback
from datetime import datetime


STEPS = [
    ("schedule", "daily_update_1_schedule"),
    ("usage", "daily_update_2_usage"),
    ("game_logs", "daily_update_3_game_logs"),
    ("season_averages", "daily_update_4_season_averages"),
]


def _run_step(step_name: str, module_name: str) -> bool:
    print("\n" + "=" * 78)
    print(f"▶ Running step: {step_name} ({module_name}.main)")
    print("=" * 78)

    try:
        mod = importlib.import_module(module_name)
        main = getattr(mod, "main", None)
        if not callable(main):
            raise RuntimeError(f"{module_name} has no callable main()")
        main()
        print(f"✅ Step succeeded: {step_name}")
        return True
    except SystemExit as e:
        # Some scripts may call SystemExit; treat non-zero as failure.
        code = e.code if isinstance(e.code, int) else 1
        if code == 0:
            print(f"✅ Step succeeded (SystemExit 0): {step_name}")
            return True
        print(f"❌ Step failed (SystemExit {code}): {step_name}")
        return False
    except Exception:
        print(f"❌ Step raised exception: {step_name}")
        traceback.print_exc()
        return False


def main() -> None:
    started = datetime.utcnow()
    print("=" * 78)
    print(f"Daily update runner started (UTC): {started.isoformat(timespec='seconds')}")
    print("=" * 78)

    strict_daily = os.environ.get("STRICT_DAILY_UPDATE", "0") == "1"

    results: dict[str, bool] = {}
    for step_name, module_name in STEPS:
        ok = _run_step(step_name, module_name)
        results[step_name] = ok

    ended = datetime.utcnow()
    duration_s = (ended - started).total_seconds()

    print("\n" + "=" * 78)
    print(f"Runner finished (UTC): {ended.isoformat(timespec='seconds')}  (took {duration_s:.1f}s)")
    for k in [s[0] for s in STEPS]:
        print(f"- {k}: {'OK' if results.get(k) else 'FAIL'}")
    print("=" * 78)

    if strict_daily and (not all(results.values())):
        sys.exit(1)


if __name__ == "__main__":
    main()
