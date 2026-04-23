"""
Export Financial Dashboard Data to JSON
Generates a JSON file with monthly financial metrics for web dashboard consumption

Usage:
    python export_dashboard_data.py                 # defaults to previous calendar month
    python export_dashboard_data.py --period 26.02  # explicit period
Output: Creates generated/YY.MM/dashboard_data.json with all key metrics
"""

import argparse
import pandas as pd
import numpy as np
import json
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
_parser = argparse.ArgumentParser(description="Export financial dashboard data.")
_parser.add_argument("--period", default=None, help='Period as YY.MM (default: previous month)')
_args, _ = _parser.parse_known_args()
PERIOD = _args.period or _default_period()

# Derived configuration
CURRENT_YEAR = 2000 + int(PERIOD.split('.')[0])
CURRENT_MONTH_NUM = int(PERIOD.split('.')[1])
MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]
CURRENT_MONTH = MONTH_NAMES[CURRENT_MONTH_NUM - 1]
CURRENT_MONTH_INDEX = CURRENT_MONTH_NUM - 1  # 0-indexed

# Find financial package using fuzzy matching
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))
from file_utils import find_input_file

INPUT_FOLDER = os.path.join("inputs", PERIOD)
FILE_PATH = find_input_file(INPUT_FOLDER, ["financial", "package"])
OUTPUT_PATH = os.path.join("generated", PERIOD, "dashboard_data.json")

# Cross-year L3M: load prior year data when current month < 4
prior_year_monthly = None
prior_year_products = None
if CURRENT_MONTH_INDEX < 3:
    prior_period = f"{CURRENT_YEAR - 2001:02d}.12"
    prior_data_path = os.path.join("generated", prior_period, "dashboard_data.json")
    if os.path.exists(prior_data_path):
        import json as json_module
        with open(prior_data_path, 'r') as f:
            prior_data = json_module.load(f)
        prior_year_monthly = prior_data.get('monthly_series', [])
        prior_year_products = prior_data.get('products', {})
        print(f"[OK] Loaded prior year data from {prior_data_path} for L3M comparison")
    else:
        print(f"[WARN] Prior year data not found at {prior_data_path} - L3M will be partial")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def find_row_by_text(df, text, col=0):
    """Find the first row index containing specific text in a column"""
    for idx, val in df.iloc[:, col].items():
        if pd.notna(val) and isinstance(val, str) and text.lower() in val.lower():
            return idx
    return None

def extract_monthly_data(df, row_idx, start_col=1, num_months=12):
    """Extract monthly values from a specific row"""
    if row_idx is None:
        return [None] * num_months
    values = df.iloc[row_idx, start_col:start_col+num_months].tolist()
    # Convert NaN to None for JSON compatibility
    return [None if pd.isna(v) else float(v) for v in values]

def safe_sum(values):
    """Sum non-None values"""
    return sum([v for v in values if v is not None])

def safe_avg(values):
    """Average non-None values"""
    valid = [v for v in values if v is not None]
    return sum(valid) / len(valid) if valid else None

def calc_rolling_l3m_avg(data_list, current_month_idx):
    """Calculate average of 3 months prior to current month"""
    if current_month_idx < 3:
        return None
    prior_3_months = [data_list[i] for i in range(current_month_idx - 3, current_month_idx)]
    valid = [v for v in prior_3_months if v is not None]
    return sum(valid) / len(valid) if valid else None

# ============================================================================
# DATA EXTRACTION
# ============================================================================

print(f"Extracting dashboard data for {CURRENT_MONTH} {CURRENT_YEAR}...")

months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

# P&L DATA
df_pl = pd.read_excel(FILE_PATH, sheet_name=f'P&L YTD {CURRENT_YEAR}', header=None)

revenue_row = find_row_by_text(df_pl, 'total for 400 sales')
cogs_row = find_row_by_text(df_pl, 'total cost of goods sold')
gross_profit_row = find_row_by_text(df_pl, 'gross profit')
net_income_row = find_row_by_text(df_pl, 'net income')
ebitda_row = find_row_by_text(df_pl, 'ebitda')

revenue = extract_monthly_data(df_pl, revenue_row)
cogs = extract_monthly_data(df_pl, cogs_row)
gross_profit = extract_monthly_data(df_pl, gross_profit_row)
net_income = extract_monthly_data(df_pl, net_income_row)

if ebitda_row:
    ebitda = extract_monthly_data(df_pl, ebitda_row)
else:
    # Calculate EBITDA if not found
    da_row = find_row_by_text(df_pl, 'depreciation')
    interest_row = find_row_by_text(df_pl, 'interest expense')
    da = extract_monthly_data(df_pl, da_row) if da_row else [0] * 12
    interest = extract_monthly_data(df_pl, interest_row) if interest_row else [0] * 12
    ebitda = []
    for i in range(12):
        ni = net_income[i] if net_income[i] is not None else 0
        d = da[i] if da[i] is not None else 0
        int_exp = interest[i] if interest[i] is not None else 0
        ebitda.append(ni + abs(d) + abs(int_exp))

# Calculate margins
gross_margin = [(gp/rev * 100) if gp is not None and rev is not None and rev != 0 else None
                for gp, rev in zip(gross_profit, revenue)]
ebitda_margin = [(eb/rev * 100) if eb is not None and rev is not None and rev != 0 else None
                 for eb, rev in zip(ebitda, revenue)]

# BALANCE SHEET DATA
df_bs = pd.read_excel(FILE_PATH, sheet_name=f'BS YTD {CURRENT_YEAR}', header=None)

ar_row = find_row_by_text(df_bs, 'total accounts receivable')
inventory_row = find_row_by_text(df_bs, 'total 130 inventory asset')
ap_row = find_row_by_text(df_bs, 'total accounts payable')
current_assets_row = find_row_by_text(df_bs, 'total current assets')
current_liabilities_row = find_row_by_text(df_bs, 'total current liabilities')

ar = extract_monthly_data(df_bs, ar_row)
inventory = extract_monthly_data(df_bs, inventory_row)
ap = extract_monthly_data(df_bs, ap_row)
current_assets = extract_monthly_data(df_bs, current_assets_row)
current_liabilities = extract_monthly_data(df_bs, current_liabilities_row)

# Calculate NWC (excluding cash: A/R + Inventory - A/P)
nwc = []
for a, inv, p in zip(ar, inventory, ap):
    if a is not None and inv is not None and p is not None:
        nwc.append(a + inv - p)
    else:
        nwc.append(None)

# CASH FLOW DATA
df_cf = pd.read_excel(FILE_PATH, sheet_name=f'Cashflow YTD {CURRENT_YEAR}', header=None)

ocf_row = find_row_by_text(df_cf, 'net cash provided by operating') or find_row_by_text(df_cf, 'cash from operating')
icf_row = find_row_by_text(df_cf, 'net cash provided by investing') or find_row_by_text(df_cf, 'cash from investing')
fcf_row = find_row_by_text(df_cf, 'net cash provided by financing') or find_row_by_text(df_cf, 'cash from financing')

operating_cf = extract_monthly_data(df_cf, ocf_row)
investing_cf = extract_monthly_data(df_cf, icf_row)
financing_cf = extract_monthly_data(df_cf, fcf_row)

# PRODUCT-LEVEL DATA
df_product = pd.read_excel(FILE_PATH, sheet_name='GP by product', header=None)

# Define product search terms
products = {
    'cast_drums': {
        'name': 'Cast Drums',
        'sales_search': 'Total for 410 DuraBrake-Brake Drum',
        'cogs_search': 'Total for 510 DuraBrake Drum COGS'
    },
    'steel_shell_drums': {
        'name': 'Steel Shell Drums',
        'sales_search': 'Total for 411 Durabrake - Steel Shell Brake Drum',
        'cogs_search': 'Total for 511 Durabrake Steel Shell Brake Drum COGS'
    },
    'rotors': {
        'name': 'Rotors',
        'sales_search': 'Total for 420 DuraBrake-Rotor',
        'cogs_search': 'Total for 520 DuraBrake Rotors COGS'
    },
    'pads': {
        'name': 'Pads',
        'sales_search': 'Total for 430 DuraBrake-Brake Pad',
        'cogs_search': 'Total for 530 DuraBrake Brake Pad/ Linings COGS'
    },
    'calipers': {
        'name': 'Calipers',
        'sales_search': 'Total for 450 DuraBrake- Calipers',
        'cogs_search': 'Total for 550 DuraBrake Caliper COGS'
    },
    'hubs': {
        'name': 'Hubs',
        'sales_search': '460 DuraBrake- Hub',
        'cogs_search': '560 DuraBrake Hubs COGS'
    }
}

# Extract product data
product_data = {}
for product_key, product_info in products.items():
    sales_row = find_row_by_text(df_product, product_info['sales_search'])
    cogs_row = find_row_by_text(df_product, product_info['cogs_search'])

    sales = extract_monthly_data(df_product, sales_row)
    cogs = extract_monthly_data(df_product, cogs_row)

    # Calculate gross profit and margin
    gross_profit_prod = []
    gross_margin_prod = []
    for s, c in zip(sales, cogs):
        if s is not None and c is not None:
            gp = s - c
            gross_profit_prod.append(gp)
            gross_margin_prod.append((gp / s * 100) if s != 0 else None)
        else:
            gross_profit_prod.append(None)
            gross_margin_prod.append(None)

    product_data[product_key] = {
        'name': product_info['name'],
        'sales': sales,
        'cogs': cogs,
        'gross_profit': gross_profit_prod,
        'gross_margin_pct': gross_margin_prod
    }

print("Data extraction complete!")

def get_metric_value(metric_list, month_idx, prior_monthly, metric_key):
    """Get a metric value, falling back to prior year data if needed."""
    if month_idx >= 0:
        return metric_list[month_idx]
    elif prior_monthly:
        prior_idx = 12 + month_idx  # e.g., -1 -> 11 (December)
        if prior_idx < len(prior_monthly):
            return prior_monthly[prior_idx].get(metric_key)
    return None

def get_product_l3m(prod_key, metric, indices, current_data, prior_products):
    """Get product L3M values, falling back to prior year."""
    vals = []
    for i in indices:
        if i >= 0:
            vals.append(current_data[i])
        elif prior_products and prod_key in prior_products:
            prior_idx = 12 + i
            prior_series = prior_products[prod_key].get('monthly_series', [])
            if prior_idx < len(prior_series):
                vals.append(prior_series[prior_idx].get(metric))
            else:
                vals.append(None)
        else:
            vals.append(None)
    return vals

# ============================================================================
# BUILD JSON OUTPUT
# ============================================================================

# Current month metrics
current_month_data = {
    "revenue": revenue[CURRENT_MONTH_INDEX],
    "gross_profit": gross_profit[CURRENT_MONTH_INDEX],
    "gross_margin_pct": gross_margin[CURRENT_MONTH_INDEX],
    "ebitda": ebitda[CURRENT_MONTH_INDEX],
    "ebitda_margin_pct": ebitda_margin[CURRENT_MONTH_INDEX],
    "net_income": net_income[CURRENT_MONTH_INDEX],
    "accounts_receivable": ar[CURRENT_MONTH_INDEX],
    "inventory": inventory[CURRENT_MONTH_INDEX],
    "accounts_payable": ap[CURRENT_MONTH_INDEX],
    "nwc": nwc[CURRENT_MONTH_INDEX],
    "operating_cash_flow": operating_cf[CURRENT_MONTH_INDEX]
}

# L3M comparison (current month vs prior 3 months average)
l3m_indices = list(range(CURRENT_MONTH_INDEX - 3, CURRENT_MONTH_INDEX))

l3m_revenue_avg = safe_avg([get_metric_value(revenue, i, prior_year_monthly, 'revenue') for i in l3m_indices])
l3m_gp_avg = safe_avg([get_metric_value(gross_profit, i, prior_year_monthly, 'gross_profit') for i in l3m_indices])
l3m_gm_avg = safe_avg([get_metric_value(gross_margin, i, prior_year_monthly, 'gross_margin_pct') for i in l3m_indices])
l3m_ebitda_avg = safe_avg([get_metric_value(ebitda, i, prior_year_monthly, 'ebitda') for i in l3m_indices])
l3m_em_avg = safe_avg([get_metric_value(ebitda_margin, i, prior_year_monthly, 'ebitda_margin_pct') for i in l3m_indices])
l3m_ni_avg = safe_avg([get_metric_value(net_income, i, prior_year_monthly, 'net_income') for i in l3m_indices])

l3m_comparison = {
    "revenue": {
        "current": revenue[CURRENT_MONTH_INDEX],
        "l3m_avg": l3m_revenue_avg,
        "variance_pct": ((revenue[CURRENT_MONTH_INDEX] - l3m_revenue_avg) / abs(l3m_revenue_avg) * 100)
                        if revenue[CURRENT_MONTH_INDEX] and l3m_revenue_avg and l3m_revenue_avg != 0 else None
    },
    "gross_profit": {
        "current": gross_profit[CURRENT_MONTH_INDEX],
        "l3m_avg": l3m_gp_avg,
        "variance_pct": ((gross_profit[CURRENT_MONTH_INDEX] - l3m_gp_avg) / abs(l3m_gp_avg) * 100)
                        if gross_profit[CURRENT_MONTH_INDEX] and l3m_gp_avg and l3m_gp_avg != 0 else None
    },
    "gross_margin_pct": {
        "current": gross_margin[CURRENT_MONTH_INDEX],
        "l3m_avg": l3m_gm_avg,
        "variance_pts": (gross_margin[CURRENT_MONTH_INDEX] - l3m_gm_avg)
                        if gross_margin[CURRENT_MONTH_INDEX] and l3m_gm_avg else None
    },
    "ebitda": {
        "current": ebitda[CURRENT_MONTH_INDEX],
        "l3m_avg": l3m_ebitda_avg,
        "variance_pct": ((ebitda[CURRENT_MONTH_INDEX] - l3m_ebitda_avg) / abs(l3m_ebitda_avg) * 100)
                        if ebitda[CURRENT_MONTH_INDEX] and l3m_ebitda_avg and l3m_ebitda_avg != 0 else None
    },
    "ebitda_margin_pct": {
        "current": ebitda_margin[CURRENT_MONTH_INDEX],
        "l3m_avg": l3m_em_avg,
        "variance_pts": (ebitda_margin[CURRENT_MONTH_INDEX] - l3m_em_avg)
                        if ebitda_margin[CURRENT_MONTH_INDEX] and l3m_em_avg else None
    },
    "net_income": {
        "current": net_income[CURRENT_MONTH_INDEX],
        "l3m_avg": l3m_ni_avg,
        "variance_pct": ((net_income[CURRENT_MONTH_INDEX] - l3m_ni_avg) / abs(l3m_ni_avg) * 100)
                        if net_income[CURRENT_MONTH_INDEX] and l3m_ni_avg and l3m_ni_avg != 0 else None
    }
}

# Monthly time series data
monthly_series = []
for i in range(12):
    monthly_series.append({
        "month": months[i],
        "month_num": i + 1,
        "revenue": revenue[i],
        "gross_profit": gross_profit[i],
        "gross_margin_pct": gross_margin[i],
        "ebitda": ebitda[i],
        "ebitda_margin_pct": ebitda_margin[i],
        "net_income": net_income[i],
        "nwc": nwc[i],
        "operating_cf": operating_cf[i],
        "accounts_receivable": ar[i],
        "inventory": inventory[i],
        "accounts_payable": ap[i]
    })

# Rolling L3M comparison for all months
rolling_l3m = []
for i in range(12):
    if i >= 3 or (prior_year_monthly and i < 3):
        l3m_rev_vals = [get_metric_value(revenue, j, prior_year_monthly, 'revenue') for j in range(i-3, i)]
        l3m_ebitda_vals = [get_metric_value(ebitda, j, prior_year_monthly, 'ebitda') for j in range(i-3, i)]
        l3m_gm_vals = [get_metric_value(gross_margin, j, prior_year_monthly, 'gross_margin_pct') for j in range(i-3, i)]

        l3m_rev_avg = safe_avg(l3m_rev_vals)
        l3m_ebitda_avg_val = safe_avg(l3m_ebitda_vals)
        l3m_gm_avg_val = safe_avg(l3m_gm_vals)

        rolling_l3m.append({
            "month": months[i],
            "month_num": i + 1,
            "revenue_vs_l3m_pct": ((revenue[i] - l3m_rev_avg) / abs(l3m_rev_avg) * 100)
                                  if revenue[i] and l3m_rev_avg and l3m_rev_avg != 0 else None,
            "ebitda_vs_l3m_pct": ((ebitda[i] - l3m_ebitda_avg_val) / abs(l3m_ebitda_avg_val) * 100)
                                 if ebitda[i] and l3m_ebitda_avg_val and l3m_ebitda_avg_val != 0 else None,
            "gm_vs_l3m_pts": (gross_margin[i] - l3m_gm_avg_val)
                             if gross_margin[i] and l3m_gm_avg_val else None
        })

# YTD summary
ytd_summary = {
    "total_revenue": safe_sum(revenue),
    "total_gross_profit": safe_sum(gross_profit),
    "avg_gross_margin_pct": safe_avg(gross_margin),
    "total_ebitda": safe_sum(ebitda),
    "avg_ebitda_margin_pct": safe_avg(ebitda_margin),
    "total_net_income": safe_sum(net_income),
    "avg_nwc": safe_avg(nwc),
    "total_operating_cf": safe_sum(operating_cf)
}

# Q4 summary
q4_indices = [9, 10, 11]
q4_summary = {
    "total_revenue": safe_sum([revenue[i] for i in q4_indices]),
    "total_gross_profit": safe_sum([gross_profit[i] for i in q4_indices]),
    "avg_gross_margin_pct": safe_avg([gross_margin[i] for i in q4_indices]),
    "total_ebitda": safe_sum([ebitda[i] for i in q4_indices]),
    "avg_ebitda_margin_pct": safe_avg([ebitda_margin[i] for i in q4_indices]),
    "total_net_income": safe_sum([net_income[i] for i in q4_indices]),
    "avg_nwc": safe_avg([nwc[i] for i in q4_indices]),
    "total_operating_cf": safe_sum([operating_cf[i] for i in q4_indices])
}

# Product-level data with current month and L3M comparison
products_output = {}
for product_key, prod_data in product_data.items():
    # Current month
    current_sales = prod_data['sales'][CURRENT_MONTH_INDEX]
    current_gp = prod_data['gross_profit'][CURRENT_MONTH_INDEX]
    current_gm = prod_data['gross_margin_pct'][CURRENT_MONTH_INDEX]

    # L3M averages
    l3m_sales_vals = get_product_l3m(product_key, 'sales', l3m_indices, prod_data['sales'], prior_year_products)
    l3m_gp_vals = get_product_l3m(product_key, 'gross_profit', l3m_indices, prod_data['gross_profit'], prior_year_products)
    l3m_gm_vals = get_product_l3m(product_key, 'gross_margin_pct', l3m_indices, prod_data['gross_margin_pct'], prior_year_products)

    l3m_sales_avg = safe_avg(l3m_sales_vals)
    l3m_gp_avg = safe_avg(l3m_gp_vals)
    l3m_gm_avg = safe_avg(l3m_gm_vals)

    products_output[product_key] = {
        'name': prod_data['name'],
        'current_month': {
            'sales': current_sales,
            'gross_profit': current_gp,
            'gross_margin_pct': current_gm
        },
        'l3m_comparison': {
            'sales': {
                'current': current_sales,
                'l3m_avg': l3m_sales_avg,
                'variance_pct': ((current_sales - l3m_sales_avg) / abs(l3m_sales_avg) * 100)
                                if current_sales and l3m_sales_avg and l3m_sales_avg != 0 else None
            },
            'gross_profit': {
                'current': current_gp,
                'l3m_avg': l3m_gp_avg,
                'variance_pct': ((current_gp - l3m_gp_avg) / abs(l3m_gp_avg) * 100)
                                if current_gp and l3m_gp_avg and l3m_gp_avg != 0 else None
            },
            'gross_margin_pct': {
                'current': current_gm,
                'l3m_avg': l3m_gm_avg,
                'variance_pts': (current_gm - l3m_gm_avg)
                                if current_gm and l3m_gm_avg else None
            }
        },
        'monthly_series': [
            {
                'month': months[i],
                'month_num': i + 1,
                'sales': prod_data['sales'][i],
                'gross_profit': prod_data['gross_profit'][i],
                'gross_margin_pct': prod_data['gross_margin_pct'][i]
            }
            for i in range(12)
        ]
    }

# Build final JSON structure
dashboard_data = {
    "metadata": {
        "reporting_month": CURRENT_MONTH,
        "reporting_year": CURRENT_YEAR,
        "generated_at": datetime.now().isoformat(),
        "source_file": FILE_PATH
    },
    "current_month": current_month_data,
    "l3m_comparison": l3m_comparison,
    "monthly_series": monthly_series,
    "rolling_l3m": rolling_l3m,
    "ytd_summary": ytd_summary,
    "q4_summary": q4_summary,
    "products": products_output
}

# ============================================================================
# EXPORT TO JSON
# ============================================================================

# Ensure output directory exists
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

with open(OUTPUT_PATH, 'w') as f:
    json.dump(dashboard_data, f, indent=2)

print(f"\n[OK] Dashboard data exported to: {OUTPUT_PATH}")
print(f"[OK] Reporting period: {CURRENT_MONTH} {CURRENT_YEAR}")
print(f"[OK] File size: {len(json.dumps(dashboard_data))} bytes")
print("\nJSON structure includes:")
print("  - Current month metrics")
print("  - L3M comparison (current vs prior 3 months avg)")
print("  - Monthly time series (all 12 months)")
print("  - Rolling L3M comparisons")
print("  - YTD summary")
print("  - Q4 summary")
print("  - Product-level data (6 products with current month and L3M)")
