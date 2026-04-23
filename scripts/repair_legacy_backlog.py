"""
Repair legacy header-less backlog CSV exports.

Early manual backlog exports from FileMaker (pre-automation) were saved
without a header row. The existing `scripts/backlog_analysis.py` pipeline
requires named columns, so those files are unusable as-is.

This tool prepends the correct header row inferred from the column order
of the Feb 2026 export, converts currency strings ($42,640.00) to floats,
parses dates, and writes the result as .xlsx matching the naming
convention `Backlog_YYYY-MM-DD.xlsx` that the rest of the pipeline
expects.

Usage:
    python scripts/repair_legacy_backlog.py --period 26.02
    python scripts/repair_legacy_backlog.py --period 26.02 --csv "inputs/26.02/Backlog 28Feb26.csv"

The original CSV is NEVER deleted or moved — this creates a sibling .xlsx
alongside it so the original stays available.
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd


# Column mapping inferred from the Feb 2026 export sample:
#   Row: "26544","3/3/2026","","","16792X-111","12/18/2025","$1,451,493.26",
#        "","","Chris Johnson","LA","Open","$42,640.00","","Kenworth of Louisiana"
#
# High-confidence positions (non-empty columns with distinctive data):
#   0  -> DocNumber                          e.g. 26544
#   1  -> Estimated Invoice Date             later date
#   2  -> TxnDate                            empty on all rows (= backlog filter)
#   4  -> Item list                          SKU codes
#   5  -> Order Date                         earlier date (when ordered)
#   6  -> Order Total                        aggregate ($1.45M on every row — FM rollup)
#   9  -> SalesRep                           person name
#  10  -> ShippingAddressRegion              2-letter region/state
#  11  -> Status                             "Open"
#  12  -> SubTotal_c for Reports             per-order $ value
#  14  -> InvoicesCustomers::DisplayName     customer name
#
# Empty-on-every-row positions assigned to the remaining expected fields:
#   3  -> OrderGrossProfit
#   7  -> OrderOtherCosts
#   8  -> GM
#  13  -> DaysToPay
FEB_HEADERS = [
    "DocNumber",                           # 0
    "Estimated Invoice Date",              # 1
    "TxnDate",                             # 2
    "OrderGrossProfit",                    # 3
    "Item list",                           # 4
    "Order Date",                          # 5
    "Order Total",                         # 6
    "OrderOtherCosts",                     # 7
    "GM",                                  # 8
    "SalesRep",                            # 9
    "ShippingAddressRegion",               # 10
    "Status",                              # 11
    "SubTotal_c for Reports",              # 12
    "DaysToPay",                           # 13
    "InvoicesCustomers::DisplayName",      # 14
]

CURRENCY_COLS = ["Order Total", "SubTotal_c for Reports",
                 "OrderGrossProfit", "OrderOtherCosts"]
DATE_COLS = ["Order Date", "TxnDate", "Estimated Invoice Date"]


def _clean_currency(value):
    """Turn '$42,640.00' into 42640.00. Pass through blanks/numbers as-is."""
    if pd.isna(value) or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).replace("$", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _last_day_of_period(period: str) -> str:
    """Return YYYY-MM-DD for the last calendar day of a YY.MM period."""
    import calendar
    yy, mm = period.split(".")
    year, month = 2000 + int(yy), int(mm)
    last = calendar.monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-{last:02d}"


def repair(csv_path: str, period: str, project_root: str) -> str:
    """Read header-less CSV, apply headers, clean types, write .xlsx. Returns dest path."""
    df = pd.read_csv(csv_path, header=None, dtype=str, keep_default_na=False)

    if df.shape[1] != len(FEB_HEADERS):
        raise ValueError(
            f"Expected {len(FEB_HEADERS)} columns, found {df.shape[1]} in {csv_path}.\n"
            f"This script assumes the Feb 2026 column layout. "
            f"If this file is from a different export vintage, the mapping may be wrong."
        )

    df.columns = FEB_HEADERS

    # Type coercion
    for col in CURRENCY_COLS:
        df[col] = df[col].map(_clean_currency)
    for col in DATE_COLS:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    df["DocNumber"] = pd.to_numeric(df["DocNumber"], errors="coerce").astype("Int64")

    # Trim whitespace on string columns
    for col in ["InvoicesCustomers::DisplayName", "SalesRep",
                "ShippingAddressRegion", "Status", "Item list"]:
        df[col] = df[col].str.strip()

    # Destination filename — Backlog_{YYYY-MM-DD}.xlsx, at the last day of the period
    last_day = _last_day_of_period(period)
    dest = os.path.join(project_root, "inputs", period, f"Backlog_{last_day}.xlsx")
    df.to_excel(dest, index=False)
    print(f"[OK] Repaired backlog:")
    print(f"     source: {csv_path}  (kept as-is)")
    print(f"     dest:   {dest}  ({len(df)} rows)")
    return dest


def _find_legacy_csv(period: str, project_root: str) -> str:
    folder = Path(project_root) / "inputs" / period
    candidates = [str(p) for p in folder.glob("Backlog*.csv")]
    if not candidates:
        raise FileNotFoundError(
            f"No legacy Backlog*.csv found in {folder}. "
            f"Pass --csv to point explicitly."
        )
    if len(candidates) > 1:
        raise RuntimeError(f"Multiple Backlog*.csv files in {folder}: {candidates}")
    return candidates[0]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add headers to legacy backlog CSV.")
    parser.add_argument("--period", required=True, help="Period in YY.MM format (e.g., 26.02)")
    parser.add_argument("--csv", default=None,
                        help="Optional explicit path to the CSV. Defaults to the single "
                             "Backlog*.csv file in inputs/<period>/.")
    parser.add_argument("--project-root",
                        default=str(Path(__file__).resolve().parent.parent))
    args = parser.parse_args()

    csv_path = args.csv or _find_legacy_csv(args.period, args.project_root)
    repair(csv_path, args.period, args.project_root)
