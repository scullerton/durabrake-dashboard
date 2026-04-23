"""
Job B: Monthly dashboard generation orchestrator.

Runs via Windows Task Scheduler daily from the 22nd through end-of-month.
The script is idempotent — if outputs already exist in generated/{PERIOD}/,
it exits quickly without doing work, so scheduling it daily is safe.

Pipeline:
    1. Ensure inputs/{PERIOD}/ exists
    2. Fetch QBO Sales Detail + Income Summary (skip if present)
    3. Copy internal financial package (skip if present; exit 2 if not yet saved)
    4. Verify backlog snapshot is present (should already exist from Job A)
    5. Run existing pipeline: generate_dashboard.py --period {PERIOD}
    6. git add/commit/push → Streamlit Cloud auto-redeploys
    7. Write email draft summarizing the run (never auto-sends)

Exit codes:
    0 - success or already-complete
    1 - unexpected error
    2 - inputs not ready yet (retry tomorrow)

Flags:
    --period YY.MM    Override period (default: previous calendar month)
    --skip-qbo        Don't pull from QuickBooks (use existing input files)
    --skip-push       Don't git push (useful for dry runs)
    --force           Regenerate even if generated/{PERIOD}/ already complete
"""

from __future__ import annotations

import argparse
import glob
import logging
import os
import subprocess
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import copy_internal  # noqa: E402

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_NOT_READY = 2

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Files generate_dashboard.py produces — presence of all = "already done"
EXPECTED_OUTPUTS = [
    "dashboard_data.json",
    "customer_dashboard_data.json",
    "backlog_dashboard_data.json",
    "rfm_analysis_results.csv",
    "rfm_summary.json",
    "dashboard_notes.json",
]


def _default_period() -> str:
    today = datetime.now()
    first_of_this_month = today.replace(day=1)
    last_of_prev = first_of_this_month - timedelta(days=1)
    return last_of_prev.strftime("%y.%m")


def _setup_logging(period: str) -> None:
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"monthly_automation_{period}.log"
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


def _is_already_complete(period: str) -> bool:
    gen_dir = PROJECT_ROOT / "generated" / period
    if not gen_dir.is_dir():
        return False
    return all((gen_dir / name).exists() for name in EXPECTED_OUTPUTS)


# ────────────────────────────────────────────────────────────────────────
# Input acquisition
# ────────────────────────────────────────────────────────────────────────

def _fetch_qbo(period: str) -> None:
    """Import locally so script can run with --skip-qbo before QBO is configured."""
    from qbo_client import fetch_both
    fetch_both(period, str(PROJECT_ROOT))


def _copy_internal(period: str) -> int:
    return copy_internal.copy_internal_file(period, str(PROJECT_ROOT))


def _verify_backlog(period: str) -> bool:
    matches = glob.glob(str(PROJECT_ROOT / "inputs" / period / "Backlog_*"))
    matches = [m for m in matches if m.lower().endswith((".xlsx", ".csv"))]
    return len(matches) > 0


# ────────────────────────────────────────────────────────────────────────
# Pipeline + git
# ────────────────────────────────────────────────────────────────────────

def _run_pipeline(period: str) -> None:
    logging.info(f"Running generate_dashboard.py --period {period}")
    result = subprocess.run(
        [sys.executable, "generate_dashboard.py", "--period", period],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    logging.info(result.stdout)
    if result.returncode != 0:
        logging.error(result.stderr)
        raise RuntimeError(f"generate_dashboard.py exited {result.returncode}")


def _git_push(period: str) -> None:
    logging.info("Committing and pushing generated/ folder")
    subprocess.run(["git", "add", f"generated/{period}/"], cwd=str(PROJECT_ROOT), check=True)
    # Only commit if there's something staged
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=str(PROJECT_ROOT))
    if diff.returncode == 0:
        logging.info("No changes to commit.")
        return
    msg = f"Automated dashboard update for {period}"
    subprocess.run(["git", "commit", "-m", msg], cwd=str(PROJECT_ROOT), check=True)
    subprocess.run(["git", "push"], cwd=str(PROJECT_ROOT), check=True)


# ────────────────────────────────────────────────────────────────────────
# Email draft (per global rule: NEVER auto-send)
# ────────────────────────────────────────────────────────────────────────

def _write_email_draft(period: str, status: str, details: str) -> None:
    draft_dir = PROJECT_ROOT / "drafts"
    draft_dir.mkdir(exist_ok=True)
    draft_path = draft_dir / f"monthly_report_{period}.eml"
    body = f"""Subject: DuraBrake KPI Dashboard — {period} — {status}

Status: {status}
Period: {period}
Generated: {datetime.now():%Y-%m-%d %H:%M}

{details}

Dashboard: https://durabrake.streamlit.app

This is an auto-generated draft. Review and send manually.
"""
    draft_path.write_text(body, encoding="utf-8")
    logging.info(f"Draft email written to {draft_path}")


# ────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Monthly dashboard orchestrator.")
    parser.add_argument("--period", default=None, help="YY.MM (default: previous month)")
    parser.add_argument("--skip-qbo", action="store_true")
    parser.add_argument("--skip-push", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    period = args.period or _default_period()
    _setup_logging(period)

    logging.info("=" * 60)
    logging.info(f"Monthly automation invocation at {datetime.now():%Y-%m-%d %H:%M}")

    # Gate: only run on or after the 22nd of the month. The internal report
    # typically lands around the 20th; running earlier is wasted work and
    # pollutes drafts/ with "WAITING" emails. Overridable via --period for
    # manual backfills.
    if args.period is None and datetime.now().day < 22:
        logging.info(f"Today is day {datetime.now().day}; gate is day 22. Skipping.")
        return EXIT_OK

    logging.info(f"Target period: {period}")

    # Idempotency — skip if already done
    if _is_already_complete(period) and not args.force:
        logging.info("Dashboard already complete for this period. Exiting.")
        return EXIT_OK

    try:
        inputs_dir = PROJECT_ROOT / "inputs" / period
        inputs_dir.mkdir(parents=True, exist_ok=True)

        # Step 1-2: QBO reports
        if not args.skip_qbo:
            _fetch_qbo(period)
        else:
            logging.info("Skipping QBO fetch (--skip-qbo).")

        # Step 3: internal file — may not be ready yet
        rc = _copy_internal(period)
        if rc == copy_internal.EXIT_SOURCE_NOT_READY:
            logging.info("Internal financial package not yet available. Will retry tomorrow.")
            _write_email_draft(period, "WAITING",
                               "Internal financial package not yet saved by Neil. "
                               "Scheduler will retry daily.")
            return EXIT_NOT_READY
        elif rc != 0:
            raise RuntimeError(f"copy_internal failed with code {rc}")

        # Step 4: backlog presence
        if not _verify_backlog(period):
            logging.warning("No backlog snapshot found in inputs folder. "
                            "Pipeline may fail or produce partial output.")

        # Step 5: run pipeline
        _run_pipeline(period)

        # Step 6: git push
        if not args.skip_push:
            _git_push(period)
        else:
            logging.info("Skipping git push (--skip-push).")

        # Step 7: success email draft
        _write_email_draft(period, "SUCCESS",
                           f"All {len(EXPECTED_OUTPUTS)} output files generated in "
                           f"generated/{period}/. Streamlit Cloud is redeploying.")

        logging.info("Monthly automation complete.")
        return EXIT_OK

    except Exception as exc:
        logging.error(f"Automation failed: {exc}\n{traceback.format_exc()}")
        _write_email_draft(period, "FAILED", f"Error: {exc}\n\nSee logs/monthly_automation_{period}.log")
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
