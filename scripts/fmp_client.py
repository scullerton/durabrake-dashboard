"""
FileMaker Cloud Data API client.

Fetches the "ordered but not invoiced" backlog snapshot. FileMaker's backlog
is a LIVE view — this script MUST run at EoD on the last day of each month
or the point-in-time snapshot is lost forever.

Auth model:
    FM Cloud Data API uses session tokens obtained by POSTing to
    /fmi/data/vLatest/databases/{db}/sessions with HTTP Basic auth.
    Tokens last 15 minutes (idle); we obtain one per run.

Setup:
    python scripts/fmp_client.py --setup

Testing:
    python scripts/fmp_client.py --test     # auth only
    python scripts/fmp_client.py --period 26.04   # live snapshot
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from secrets_helper import (  # noqa: E402
    FMP_SERVICE,
    get_secret,
    set_secret,
    prompt_and_store,
)


# ────────────────────────────────────────────────────────────────────────
# Session management
# ────────────────────────────────────────────────────────────────────────

def _base_url() -> str:
    host = get_secret(FMP_SERVICE, "host")
    database = get_secret(FMP_SERVICE, "database")
    return f"https://{host}/fmi/data/vLatest/databases/{database}"


def _open_session() -> str:
    url = f"{_base_url()}/sessions"
    username = get_secret(FMP_SERVICE, "username")
    password = get_secret(FMP_SERVICE, "password")
    resp = requests.post(
        url,
        auth=(username, password),
        headers={"Content-Type": "application/json"},
        json={},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["response"]["token"]


def _close_session(token: str) -> None:
    try:
        requests.delete(
            f"{_base_url()}/sessions/{token}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
    except Exception:
        pass  # best-effort logout; token will expire anyway


# ────────────────────────────────────────────────────────────────────────
# Backlog fetch
# ────────────────────────────────────────────────────────────────────────

def fetch_backlog(as_of_date: datetime, dest_folder: str) -> str:
    """Snapshot the 'ordered but not invoiced' backlog and save as Excel.

    Uses FM Data API `_find` against the "Invoices List" layout with the
    filter `Invoice Date = ""` — this mirrors the saved Find run by the
    "Backlog" button on the DuraBrake FileMaker Customer Orders tab.
    The layout exposes the exact 16 fields scripts/backlog_analysis.py
    expects (DocNumber, InvoicesCustomers::DisplayName, SubTotal_c for
    Reports, OrderGrossProfit, GM, Status, SalesRep, Order Date,
    Estimated Invoice Date, etc.).

    Returns destination path.
    """
    layout = get_secret(FMP_SERVICE, "backlog_layout")

    import urllib.parse
    layout_enc = urllib.parse.quote(layout)

    token = _open_session()
    try:
        all_records: list[dict] = []
        offset = 1
        limit = 500

        while True:
            # FM Data API _find — filter for records with empty Invoice Date.
            # Use "=" (with no value) to match empty fields in FM query syntax.
            # Filter: TxnDate empty = invoice date never set = "ordered but not invoiced"
            # (Matches the saved Find behind the Backlog button on the Customer Orders tab)
            payload = {
                "query": [{"TxnDate": "="}],
                "offset": str(offset),
                "limit": str(limit),
            }
            resp = requests.post(
                f"{_base_url()}/layouts/{layout_enc}/_find",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=60,
            )
            # FM returns 401 "No records match" for empty result sets — treat as done
            if resp.status_code == 401 and "No records match" in resp.text:
                break
            if not resp.ok:
                # Surface FM's error body before raising so credential/layout issues are debuggable
                print(f"[ERR] FM {resp.status_code}: {resp.text[:300]}")
            resp.raise_for_status()
            data = resp.json()["response"].get("data", [])
            if not data:
                break
            all_records.extend(r["fieldData"] for r in data)
            if len(data) < limit:
                break
            offset += limit
    finally:
        _close_session(token)

    df = pd.DataFrame(all_records)

    # File naming mirrors the existing manual export convention
    date_str = as_of_date.strftime("%Y-%m-%d")
    dest = os.path.join(dest_folder, f"Backlog_{date_str}.xlsx")
    df.to_excel(dest, index=False)
    print(f"[OK] Backlog snapshot: {len(df)} records -> {dest}")
    return dest


# ────────────────────────────────────────────────────────────────────────
# Setup & CLI
# ────────────────────────────────────────────────────────────────────────

def setup() -> None:
    print("FileMaker Cloud — Automation Setup")
    print("=" * 60)
    print("PREREQUISITES (ask your FM admin if unsure):")
    print("  - Data API enabled on the FM Cloud instance")
    print("  - Dedicated API user account with [fmrest] extended privilege")
    print("  - Read access to the backlog layout")
    print()
    prompt_and_store(FMP_SERVICE, "host",
                     "FM Cloud host (e.g. myorg.account.filemaker-cloud.com)")
    prompt_and_store(FMP_SERVICE, "database", "Database name")
    prompt_and_store(FMP_SERVICE, "username", "API username")
    prompt_and_store(FMP_SERVICE, "password", "API password", secret=True)
    prompt_and_store(FMP_SERVICE, "backlog_layout",
                     "Layout name exposing the 'ordered-not-invoiced' report")

    print("\nVerifying credentials...")
    try:
        token = _open_session()
        _close_session(token)
        print("[OK] FileMaker credentials valid.")
    except Exception as exc:
        print(f"[FAIL] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FileMaker client for DuraBrake automation.")
    parser.add_argument("--setup", action="store_true", help="Interactive one-time setup")
    parser.add_argument("--test", action="store_true", help="Verify credentials by opening a session")
    parser.add_argument("--period", help="YY.MM period (uses last day of period as snapshot date)")
    parser.add_argument("--project-root",
                        default=str(Path(__file__).resolve().parent.parent))
    args = parser.parse_args()

    if args.setup:
        setup()
    elif args.test:
        token = _open_session()
        _close_session(token)
        print("[OK] FileMaker session opened and closed successfully.")
    elif args.period:
        import calendar as _cal
        yy, mm = args.period.split(".")
        year, month = 2000 + int(yy), int(mm)
        last_day = _cal.monthrange(year, month)[1]
        as_of = datetime(year, month, last_day)
        dest_folder = os.path.join(args.project_root, "inputs", args.period)
        os.makedirs(dest_folder, exist_ok=True)
        fetch_backlog(as_of, dest_folder)
    else:
        parser.print_help()
