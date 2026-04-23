"""
Job A: End-of-month backlog snapshot.

Runs via Windows Task Scheduler at 11:45 PM on the last day of each month.
FileMaker backlog is a live view — missing this window = permanent data loss.

Exit codes (Task Scheduler consumes these for retry logic):
    0  - success or idempotent skip
    1  - unexpected error (investigate)
    2  - FileMaker unreachable; retry at scheduler's next interval

Log location: logs/backlog_snapshot_{YYYY-MM}.log
"""

from __future__ import annotations

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


def main() -> int:
    today = datetime.now()
    period = today.strftime("%y.%m")
    _setup_logging(period)

    logging.info("=" * 60)
    logging.info(f"Backlog snapshot invocation at {today:%Y-%m-%d %H:%M}")

    # Gate: only run on the last calendar day of the month.
    # (Earlier snapshots would overwrite/preempt the real month-end snapshot.)
    import calendar as _cal
    last_day = _cal.monthrange(today.year, today.month)[1]
    if today.day != last_day:
        logging.info(f"Today is day {today.day}; last day of month is {last_day}. Skipping.")
        return EXIT_OK

    logging.info(f"Running snapshot for period {period}")

    dest_folder = PROJECT_ROOT / "inputs" / period
    dest_folder.mkdir(parents=True, exist_ok=True)

    # Idempotency — skip if we already captured today
    existing = glob.glob(str(dest_folder / "Backlog_*.xlsx"))
    if existing:
        logging.info(f"Backlog file(s) already present: {[os.path.basename(f) for f in existing]}")
        logging.info("Skipping (idempotent).")
        return EXIT_OK

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
