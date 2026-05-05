"""
Job A: End-of-month backlog snapshot.

Runs via Windows Task Scheduler at 11:45 PM on the last day of each month.
FileMaker backlog is a live view — missing this window = permanent data loss.

Exit codes (Task Scheduler consumes these for retry logic):
    0  - success or idempotent skip
    1  - unexpected error (investigate)
    2  - FileMaker unreachable; retry at scheduler's next interval

Log location: logs/backlog_snapshot_{YYYY-MM}.log

Manual recovery
---------------
    python scripts/capture_backlog_snapshot.py --force --period 26.04

Use --force to bypass the last-day-of-month gate (e.g., when a scheduler
miss is being recovered after the fact). --period overrides which month
the snapshot is filed under (defaults to the current calendar month).

Idempotency
-----------
The default path is strict: the script will only consider an existing
file as "today's snapshot" if its mtime is within FRESH_WINDOW_HOURS of
now. Older files are treated as stale leftovers (manual tests, earlier
months wrongly named, etc.) and moved to inputs/{YY.MM}/.stale/ before
a fresh capture proceeds. This prevents the failure mode where a stale
placeholder file silently causes a real EoD run to skip.
"""

from __future__ import annotations

import argparse
import glob
import logging
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fmp_client import fetch_backlog  # noqa: E402

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_NETWORK_RETRY = 2

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Window in which an existing backlog file is considered "today's snapshot"
# rather than a stale leftover. 6h covers normal scheduler retry behavior
# (re-runs across a single evening) while still catching anything older
# than the same business day.
FRESH_WINDOW_HOURS = 6


def _setup_logging(period: str) -> None:
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"backlog_snapshot_{period}.log"
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    # Also echo to stdout so Task Scheduler's "last run" output shows something useful
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


def _file_age_hours(path: str, now: datetime) -> float:
    return (now.timestamp() - os.path.getmtime(path)) / 3600


def _move_to_stale(files: list[str], dest_folder: Path, now: datetime) -> None:
    """Move stale leftover files to dest_folder/.stale/ so they stop
    masquerading as today's snapshot. Preserve the original mtime in the
    archived filename when collisions exist."""
    stale_dir = dest_folder / ".stale"
    stale_dir.mkdir(exist_ok=True)
    for f in files:
        src = Path(f)
        dst = stale_dir / src.name
        if dst.exists():
            mtime_str = datetime.fromtimestamp(os.path.getmtime(f)).strftime("%Y%m%d_%H%M")
            dst = stale_dir / f"{src.stem}_{mtime_str}{src.suffix}"
        os.rename(f, dst)
        logging.info(f"  archived stale file: {src.name} -> .stale/{dst.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture FileMaker backlog snapshot.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass the last-day-of-month gate. Use for manual recovery runs.",
    )
    parser.add_argument(
        "--period",
        default=None,
        help="Override period as YY.MM (default: current month). Useful for "
             "back-filling a missed snapshot into the correct month folder.",
    )
    parser.add_argument(
        "--keep-stale",
        action="store_true",
        help="Warn about stale files but don't move them aside. Default is "
             "to archive them to .stale/.",
    )
    args = parser.parse_args()

    today = datetime.now()
    period = args.period or today.strftime("%y.%m")
    _setup_logging(period)

    logging.info("=" * 60)
    logging.info(f"Backlog snapshot invocation at {today:%Y-%m-%d %H:%M}")
    if args.force:
        logging.info("--force: bypassing last-day-of-month gate")
    if args.period:
        logging.info(f"--period: overriding period to {period}")

    # Gate: only run on the last calendar day of the month, unless --force.
    # (Earlier snapshots would overwrite/preempt the real month-end snapshot.)
    if not args.force:
        import calendar as _cal
        last_day = _cal.monthrange(today.year, today.month)[1]
        if today.day != last_day:
            logging.info(f"Today is day {today.day}; last day of month is {last_day}. Skipping.")
            return EXIT_OK

    logging.info(f"Running snapshot for period {period}")

    dest_folder = PROJECT_ROOT / "inputs" / period
    dest_folder.mkdir(parents=True, exist_ok=True)

    # Freshness-based idempotency:
    #   fresh file exists  -> skip (real idempotent re-run within the day)
    #   only stale files   -> archive them, then capture fresh
    #   no files           -> capture fresh
    existing = glob.glob(str(dest_folder / "Backlog_*.xlsx"))
    fresh = [f for f in existing if _file_age_hours(f, today) < FRESH_WINDOW_HOURS]
    stale = [f for f in existing if _file_age_hours(f, today) >= FRESH_WINDOW_HOURS]

    if fresh:
        names = [os.path.basename(f) for f in fresh]
        logging.info(f"Fresh snapshot already present (<{FRESH_WINDOW_HOURS}h old): {names}")
        logging.info("Skipping (idempotent).")
        return EXIT_OK

    if stale:
        logging.warning(
            f"Found {len(stale)} stale file(s) — treating as leftover, not authoritative:"
        )
        for f in stale:
            logging.warning(f"  {os.path.basename(f)}  ({_file_age_hours(f, today):.1f}h old)")
        if args.keep_stale:
            logging.warning("--keep-stale: leaving in place. New file will land alongside.")
        else:
            _move_to_stale(stale, dest_folder, today)

    try:
        fetch_backlog(today, str(dest_folder))
        logging.info("Snapshot complete.")
        return EXIT_OK
    except Exception as exc:
        tb = traceback.format_exc()
        logging.error(f"Snapshot failed: {exc}\n{tb}")

        # Classify — network/timeout failures get exit 2 so Task Scheduler retries
        import requests
        if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
            return EXIT_NETWORK_RETRY
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
