"""
DuraBrake Dashboard Generator
Generates all required data files for the monthly dashboard
Run this script after copying input files to inputs/YY.MM/

Usage:
    python generate_dashboard.py                    # defaults to previous calendar month
    python generate_dashboard.py --period 26.02     # explicit period
"""

import argparse
import sys
import os
from datetime import datetime, timedelta


def _default_period() -> str:
    """Previous calendar month in YY.MM."""
    today = datetime.now()
    first_of_this_month = today.replace(day=1)
    last_of_prev = first_of_this_month - timedelta(days=1)
    return last_of_prev.strftime("%y.%m")


# ============================================================================
# CONFIGURATION - Accepts --period CLI flag; defaults to previous month
# ============================================================================
parser = argparse.ArgumentParser(description="Generate DuraBrake monthly dashboard data.")
parser.add_argument("--period", default=None, help='Period as YY.MM (default: previous month)')
_args, _ = parser.parse_known_args()  # parse_known_args so legacy callers w/o args still work
PERIOD = _args.period or _default_period()

# Derived configuration
YEAR = 2000 + int(PERIOD.split('.')[0])
MONTH = int(PERIOD.split('.')[1])
MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]
MONTH_NAME = MONTH_NAMES[MONTH - 1]

# Calculate L3M period (3 months prior)
if MONTH >= 3:
    L3M_MONTH = MONTH - 2
    L3M_YEAR = YEAR
else:
    L3M_MONTH = MONTH + 10  # Wrap to previous year
    L3M_YEAR = YEAR - 1

# Last day of month
import calendar
LAST_DAY = calendar.monthrange(YEAR, MONTH)[1]

print("=" * 80)
print(f"DURABRAKE DASHBOARD GENERATOR - {MONTH_NAME} {YEAR}")
print("=" * 80)
print(f"Period: {PERIOD}")
print(f"L3M Start: {L3M_YEAR}-{L3M_MONTH:02d}-01")
print(f"Analysis Date: {YEAR}-{MONTH:02d}-{LAST_DAY}")
print("=" * 80)
print()

# ============================================================================
# STEP 1: Generate Financial Dashboard Data
# ============================================================================
print("STEP 1: Generating financial dashboard data...")
print("-" * 80)

import subprocess

result = subprocess.run([
    sys.executable,
    "export_dashboard_data.py",
    "--period", PERIOD,
], capture_output=True, text=True)

print(result.stdout)
if result.returncode != 0:
    print("ERROR:", result.stderr)
    sys.exit(1)

print("[OK] Financial data generated")
print()

# ============================================================================
# STEP 2: Generate RFM Analysis
# ============================================================================
print("STEP 2: Generating RFM analysis...")
print("-" * 80)

# Import and run RFM analysis
sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))

from rfm_analysis import run_rfm_analysis

rfm_result = run_rfm_analysis(PERIOD, YEAR, MONTH, LAST_DAY)
print("[OK] RFM analysis complete")
print()

# ============================================================================
# STEP 3: Generate Customer Analysis
# ============================================================================
print("STEP 3: Generating customer analysis...")
print("-" * 80)

from customer_analysis import run_customer_analysis

customer_result = run_customer_analysis(PERIOD, YEAR, MONTH, L3M_YEAR, L3M_MONTH)
print("[OK] Customer analysis complete")
print()

# ============================================================================
# STEP 4: Generate Backlog Analysis
# ============================================================================
print("STEP 4: Generating backlog analysis...")
print("-" * 80)

from backlog_analysis import run_backlog_analysis

backlog_result = run_backlog_analysis(PERIOD, YEAR, MONTH, LAST_DAY)
print("[OK] Backlog analysis complete")
print()

# ============================================================================
# STEP 5: Generate Critical Notes & Action Items
# ============================================================================
print("STEP 5: Generating critical notes & action items...")
print("-" * 80)

from generate_notes import run_generate_notes

notes_result = run_generate_notes(PERIOD, YEAR, MONTH)
print("[OK] Notes generation complete")
print()

# ============================================================================
# SUMMARY
# ============================================================================
print("=" * 80)
print("DASHBOARD GENERATION COMPLETE")
print("=" * 80)
print(f"Generated files in: generated/{PERIOD}/")
print()
print("Generated files:")
print(f"  - dashboard_data.json")
print(f"  - customer_dashboard_data.json")
print(f"  - backlog_dashboard_data.json")
print(f"  - rfm_analysis_results.csv")
print(f"  - rfm_summary.json")
print(f"  - dashboard_notes.json")
print()
print("To launch dashboard, run:")
print(f"  streamlit run financial_dashboard.py")
print("=" * 80)
