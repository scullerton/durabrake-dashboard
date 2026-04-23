"""
Copy the internal monthly financial package into inputs/{YY.MM}/.

Source convention (Box sync folder on local machine):
    C:\\Users\\scull\\Box\\DuraParts\\Finance\\Monthly Financials\\{YYYY}\\{MMM}\\Reporting Package\\
        Final_DuraBrake ME Package -  {Month YYYY}.xlsx   (note the double space)

Destination (expected by generate_dashboard.py fuzzy matcher):
    inputs/{YY.MM}/DuraBrake Monthly Financial Package.xlsx

Neil typically saves this around the 20th of the following month. If the
file isn't present, this script exits with code 2 so the Task Scheduler
treats it as "try again tomorrow" rather than a hard failure.
"""

import argparse
import calendar
import glob
import os
import shutil
import sys
from datetime import datetime, timedelta

# Month abbreviations matching the Box folder naming: "Jan", "Feb", ...
MONTH_ABBR = list(calendar.month_abbr)  # index 0 is ''; 1..12 = 'Jan'..'Dec'

BOX_ROOT = r"C:\Users\scull\Box\DuraParts\Finance\Monthly Financials"
DEST_FILENAME = "DuraBrake Monthly Financial Package.xlsx"

# Exit codes — Task Scheduler uses these to decide retry behavior
EXIT_OK = 0
EXIT_ALREADY_COPIED = 0  # idempotent success
EXIT_SOURCE_NOT_READY = 2  # retry tomorrow
EXIT_UNEXPECTED_ERROR = 1


def period_to_source_folders(period: str) -> list[str]:
    """Return candidate source folders for a period, in priority order.

    Observed conventions in the Box monthly financials area:
      - Feb 2026: file saved in `.../2026/Feb/Reporting Package/`
      - Mar 2026: file saved directly in `.../2026/Mar/`
    We search both so whichever path Neil uses this month works.
    """
    yy, mm = period.split(".")
    year = 2000 + int(yy)
    month = int(mm)
    month_folder = os.path.join(BOX_ROOT, str(year), MONTH_ABBR[month])
    return [
        os.path.join(month_folder, "Reporting Package"),  # preferred / historical convention
        month_folder,                                     # fallback for when Neil saves at root
    ]


def period_to_source_folder(period: str) -> str:
    """Backward-compatible helper — returns the first candidate for error messages."""
    return period_to_source_folders(period)[0]


def find_source_file(source_folders_or_folder) -> str | None:
    """Locate a Final_DuraBrake ME Package*.xlsx across candidate folders.

    Accepts either a single folder path (legacy callers) or a list of paths.
    Searches each in order and returns the newest matching Final_ file found.
    """
    if isinstance(source_folders_or_folder, str):
        folders = [source_folders_or_folder]
    else:
        folders = list(source_folders_or_folder)

    candidates: list[str] = []
    for folder in folders:
        if not os.path.isdir(folder):
            continue
        found = glob.glob(os.path.join(folder, "Final_DuraBrake ME Package*.xlsx"))
        # Filter out Excel lock files (~$Final_DuraBrake...)
        found = [c for c in found if not os.path.basename(c).startswith("~$")]
        candidates.extend(found)

    if not candidates:
        return None
    if len(candidates) > 1:
        # Prefer most recently modified (usually the final save after Neil's edits)
        candidates.sort(key=os.path.getmtime, reverse=True)
    return candidates[0]


# ──────────────────────────────────────────────────────────────────────────
# TODO (SCOTT): Freshness check — shapes when we treat the file as "ready"
# ──────────────────────────────────────────────────────────────────────────
# Context: This function decides whether a file found at the expected source
# path should be trusted as THIS month's package. The risk: if Neil hasn't
# saved the new one yet but a file with the right name happens to be sitting
# there (e.g., copied manually from an older month, or an old working draft),
# the automation will silently use stale data and publish the wrong dashboard.
#
# Possible rules (pick one, or combine):
#   (a) Modified date >= first day of target period       — "file updated this period or later"
#   (b) Modified date >= 15th of month following target   — "modified recently enough to be the real one"
#   (c) Open the workbook and read a date cell (e.g., "Period Ending" on the P&L tab)
#   (d) No check — trust the folder convention blindly
#
# Trade-offs:
#   - (a) is cheapest. Works well if Neil always creates fresh each month.
#   - (b) is more conservative — gives Neil a window to edit drafts without triggering.
#   - (c) is bulletproof but requires opening the .xlsx each run (~200ms) and knowing the cell.
#   - (d) is fine if the folder is always clean and the filename is reliable.
#
# Recommended default: (a) — strict enough to catch stale files from prior months,
# lenient enough to not annoy you if Neil saves a draft mid-month.
#
# Fill in the 5-10 line implementation below.
def is_file_fresh_for_period(file_path: str, period: str) -> bool:
    """Return True if this file represents the target period's data.

    Rule (option a): file's modification time must be on or after the first
    day of the target period. Catches stale files copied from earlier months
    while still allowing Neil to edit drafts mid-period.

    Args:
        file_path: Absolute path to the found source file.
        period: Target period in YY.MM format (e.g., "26.02").
    """
    yy, mm = period.split(".")
    period_start = datetime(2000 + int(yy), int(mm), 1)
    mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
    return mod_time >= period_start
# ──────────────────────────────────────────────────────────────────────────


def copy_internal_file(period: str, project_root: str = ".", force: bool = False) -> int:
    """Main entry point. Returns process exit code.

    Smart idempotency (Option Y): if destination already exists, compare
    source and destination mtimes. If the Box source is newer (e.g., Neil
    replaced First Draft with Final, or edited the Final), replace the
    staged copy. If destination is same-age or newer, keep it.
    """
    dest_folder = os.path.join(project_root, "inputs", period)
    dest_path = os.path.join(dest_folder, DEST_FILENAME)

    # Smart idempotency check — only relevant if dest exists and not forced
    if os.path.exists(dest_path) and not force:
        source_folders = period_to_source_folders(period)
        candidate = find_source_file(source_folders)
        if not candidate:
            # Source is gone/renamed but we still have a local copy — keep it
            print(f"[OK] Internal file already present at {dest_path}; no source found to compare (skipping)")
            return EXIT_ALREADY_COPIED
        if not is_file_fresh_for_period(candidate, period):
            # Source exists but fails freshness — keep what we have
            print(f"[OK] Internal file already present at {dest_path}; source is stale (skipping)")
            return EXIT_ALREADY_COPIED
        src_mtime = os.path.getmtime(candidate)
        dst_mtime = os.path.getmtime(dest_path)
        if src_mtime <= dst_mtime:
            print(f"[OK] Internal file at {dest_path} is up to date (source not newer, skipping)")
            return EXIT_ALREADY_COPIED
        print(f"[INFO] Source is newer than staged copy — replacing.")
        print(f"       source  mtime: {datetime.fromtimestamp(src_mtime):%Y-%m-%d %H:%M}")
        print(f"       staged  mtime: {datetime.fromtimestamp(dst_mtime):%Y-%m-%d %H:%M}")
        shutil.copy2(candidate, dest_path)
        print(f"[OK] Replaced {os.path.basename(candidate)}")
        print(f"     -> {dest_path}")
        return EXIT_OK

    source_folders = period_to_source_folders(period)
    print(f"Looking in (priority order):")
    for sf in source_folders:
        print(f"  - {sf}")

    source_file = find_source_file(source_folders)
    if not source_file:
        print(
            f"[WAIT] Internal financial package not yet saved in any candidate path above.\n"
            f"       Expected filename: 'Final_DuraBrake ME Package -  <Month> <Year>.xlsx'\n"
            f"       Task Scheduler will retry tomorrow."
        )
        return EXIT_SOURCE_NOT_READY

    if not is_file_fresh_for_period(source_file, period):
        mod = datetime.fromtimestamp(os.path.getmtime(source_file))
        print(
            f"[WAIT] Found {os.path.basename(source_file)} but it looks stale "
            f"(modified {mod:%Y-%m-%d}). Waiting for updated version."
        )
        return EXIT_SOURCE_NOT_READY

    os.makedirs(dest_folder, exist_ok=True)
    shutil.copy2(source_file, dest_path)
    print(f"[OK] Copied {os.path.basename(source_file)}")
    print(f"     -> {dest_path}")
    return EXIT_OK


def _default_period() -> str:
    """Previous calendar month in YY.MM."""
    today = datetime.now()
    first_of_this_month = today.replace(day=1)
    last_of_prev = first_of_this_month - timedelta(days=1)
    return last_of_prev.strftime("%y.%m")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Copy internal financial package into inputs/.")
    parser.add_argument("--period", default=None, help='Period as YY.MM (default: previous month)')
    parser.add_argument("--project-root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        help="Root of KPI Dashboard project")
    parser.add_argument("--force", action="store_true", help="Overwrite destination if present")
    args = parser.parse_args()

    period = args.period or _default_period()
    sys.exit(copy_internal_file(period, args.project_root, args.force))
