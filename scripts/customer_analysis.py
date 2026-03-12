"""
Customer Analysis Module
Parameterized version for dashboard generation.
Extracts product categories, computes cross-sell opportunities,
order frequency analysis, and customers needing attention.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
import os
from file_utils import find_input_file


# ---------------------------------------------------------------------------
# Product category classification
# ---------------------------------------------------------------------------
NON_PRODUCT_ITEMS = {
    'buying group discount', 'gst', 'freight', 'customs and duty',
    'surcharge', 'restocking fee', 'promotion discount',
    'product/service full name',
}

def classify_product(product_service, description):
    """Classify a product/service into a business category."""
    if not product_service or pd.isna(product_service):
        return None
    ps = str(product_service).strip()
    ps_lower = ps.lower()

    # Filter non-product line items
    if ps_lower in NON_PRODUCT_ITEMS:
        return None
    if ps_lower.startswith('credit memo adjustment'):
        return None

    desc = str(description).strip().lower() if description and pd.notna(description) else ''

    # Air Disc Brake components (calipers, pads, shoes, sensors, kits)
    if ps.startswith('BC') or ps.startswith('BP') or ps.startswith('BS'):
        return 'ADB Components'
    if 'brake shoe' in desc:
        return 'ADB Components'
    if 'brake pad' in desc or 'caliper' in desc or 'sensor' in desc:
        return 'ADB Components'

    # Hub assemblies
    if '91101' in ps or 'hub' in desc.lower():
        return 'Hub Assemblies'
    if ps.startswith('3281908') or ps.startswith('3281909'):
        return 'Hub Assemblies'

    # Brake Rotors (including RT-prefix remanufactured rotors)
    if ps.startswith('RT') or 'rotor' in desc:
        return 'Brake Rotors'

    # Steel Shell Brake Drums
    if 'steel shell' in desc:
        return 'Steel Shell Drums'

    # Balanced Brake Drums
    if 'balanced' in desc:
        return 'Balanced Drums'

    # Standard Brake Drums (catch-all for drum descriptions)
    if 'brake drum' in desc or 'drum' in desc or 'front drum' in desc:
        return 'Brake Drums'

    # 3rd Party Items
    if '3rd party' in ps_lower:
        return '3rd Party'

    # Wheel hardware
    if ps.startswith('WB'):
        return 'Other'

    # DD-prefix drums
    if ps.startswith('DD'):
        return 'Brake Drums'

    # OTR-prefix (relabeled rotors)
    if ps.startswith('OTR'):
        return 'Brake Rotors'

    return 'Other'


# Higher-level grouping for cross-sell analysis (fewer buckets)
CROSS_SELL_CATEGORIES = {
    'Brake Drums': 'Drums',
    'Balanced Drums': 'Drums',
    'Steel Shell Drums': 'Drums',
    'Brake Rotors': 'Rotors',
    'ADB Components': 'ADB',
    'Hub Assemblies': 'Hubs',
    '3rd Party': '3rd Party',
    'Other': 'Other',
}

ALL_CROSS_SELL_CATEGORIES = ['Drums', 'Rotors', 'ADB', 'Hubs']


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def parse_customer_sales_data(file_path):
    """Parse the customer sales detail Excel file and extract transactions
    with product category information."""
    df = pd.read_excel(file_path)
    transactions = []
    current_customer = None

    for idx, row in df.iterrows():
        if idx <= 3:
            continue

        if pd.notna(row.iloc[0]) and pd.isna(row.iloc[1]):
            customer_name = str(row.iloc[0]).strip()
            if not customer_name.startswith('Total for'):
                current_customer = customer_name

        elif pd.notna(row.iloc[1]) and current_customer:
            transaction_date = row.iloc[1]
            transaction_type = row.iloc[2]
            amount = row.iloc[8]
            product_service = row.iloc[4] if len(row) > 4 else None
            description = row.iloc[5] if len(row) > 5 else None

            if transaction_type == 'Invoice' and pd.notna(amount) and amount != 0:
                try:
                    if isinstance(transaction_date, str):
                        trans_date = pd.to_datetime(transaction_date)
                    else:
                        trans_date = transaction_date

                    category = classify_product(product_service, description)

                    transactions.append({
                        'customer': current_customer,
                        'date': trans_date,
                        'amount': float(amount),
                        'product_service': str(product_service).strip() if pd.notna(product_service) else '',
                        'category': category,
                    })
                except:
                    pass

    return pd.DataFrame(transactions)


def load_customer_income_data(file_path):
    """Load customer income data (revenue and gross profit)"""
    df = pd.read_excel(file_path, header=None, skiprows=3)
    df.columns = ['customer', 'income', 'expenses', 'net_income']
    df = df.iloc[1:]
    df = df[df['customer'] != 'TOTAL'].copy()
    df['customer'] = df['customer'].str.strip()

    df['income'] = pd.to_numeric(df['income'], errors='coerce')
    df['expenses'] = pd.to_numeric(df['expenses'], errors='coerce')
    df['net_income'] = pd.to_numeric(df['net_income'], errors='coerce')

    df = df[df['income'].notna()].copy()
    df['gp_margin_pct'] = (df['net_income'] / df['income'] * 100).where(df['income'] > 0, 0)

    df = df[['customer', 'income', 'net_income', 'gp_margin_pct']].copy()
    df.columns = ['customer', 'annual_revenue', 'annual_gross_profit', 'gp_margin_pct']

    return df


def load_backlog_customers(period, base_path="."):
    """Load backlog data and return dict of {customer: backlog_value}
    and dict of {customer: sales_rep}."""
    backlog_file = os.path.join(base_path, f"generated/{period}/backlog_dashboard_data.json")
    if not os.path.exists(backlog_file):
        return {}, {}
    with open(backlog_file, 'r') as f:
        backlog = json.load(f)
    values = {}
    reps = {}
    for entry in backlog.get('backlog_by_customer', backlog.get('top_customers', [])):
        values[entry['customer']] = entry.get('total_value', 0)
        if entry.get('sales_rep'):
            reps[entry['customer']] = entry['sales_rep']
    return values, reps


# ---------------------------------------------------------------------------
# Metrics calculation
# ---------------------------------------------------------------------------

def calculate_customer_metrics(transactions_df, customer_income_df, l3m_year, l3m_month, year, month):
    """Calculate L3M and L12M metrics for each customer.
    L12M = trailing 12 months ending at the reporting month.
    """
    from dateutil.relativedelta import relativedelta
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    analysis_date = datetime(year, month, last_day)

    l3m_start = datetime(l3m_year, l3m_month, 1)
    l12m_start = analysis_date - relativedelta(months=12) + relativedelta(days=1)

    l3m_trans = transactions_df[transactions_df['date'] >= l3m_start]
    l12m_trans = transactions_df[transactions_df['date'] >= l12m_start]

    l3m_by_customer = l3m_trans.groupby('customer').agg({
        'amount': ['sum', 'count']
    }).reset_index()
    l3m_by_customer.columns = ['customer', 'l3m_sales', 'l3m_transactions']

    l12m_by_customer = l12m_trans.groupby('customer').agg({
        'amount': ['sum', 'count']
    }).reset_index()
    l12m_by_customer.columns = ['customer', 'l12m_sales', 'l12m_transactions']

    customer_metrics = pd.merge(
        l12m_by_customer,
        l3m_by_customer,
        on='customer',
        how='outer'
    ).fillna(0)

    total_l3m_sales = customer_metrics['l3m_sales'].sum()
    total_l12m_sales = customer_metrics['l12m_sales'].sum()

    customer_metrics['l3m_pct_of_total'] = (customer_metrics['l3m_sales'] / total_l3m_sales * 100) if total_l3m_sales > 0 else 0
    customer_metrics['l12m_pct_of_total'] = (customer_metrics['l12m_sales'] / total_l12m_sales * 100) if total_l12m_sales > 0 else 0

    customer_metrics = pd.merge(
        customer_metrics,
        customer_income_df[['customer', 'gp_margin_pct']],
        on='customer',
        how='left'
    )

    avg_gp_margin_pct = customer_income_df['gp_margin_pct'].mean()
    customer_metrics['gp_margin_pct'] = customer_metrics['gp_margin_pct'].fillna(avg_gp_margin_pct)

    customer_metrics['l3m_gross_profit'] = customer_metrics['l3m_sales'] * (customer_metrics['gp_margin_pct'] / 100)
    customer_metrics['l12m_gross_profit'] = customer_metrics['l12m_sales'] * (customer_metrics['gp_margin_pct'] / 100)

    customer_metrics['l3m_gp_margin'] = customer_metrics['gp_margin_pct']
    customer_metrics['l12m_gp_margin'] = customer_metrics['gp_margin_pct']

    return customer_metrics, total_l3m_sales, total_l12m_sales


def calculate_category_metrics(transactions_df, l3m_start):
    """Calculate per-customer product category breakdown."""
    # Only consider product transactions (category not None)
    product_trans = transactions_df[transactions_df['category'].notna()].copy()
    product_trans['cross_sell_cat'] = product_trans['category'].map(CROSS_SELL_CATEGORIES)

    l3m_product = product_trans[product_trans['date'] >= l3m_start]

    # Per-customer category breakdown (L3M)
    customer_cats = (
        l3m_product.groupby(['customer', 'cross_sell_cat'])['amount']
        .sum()
        .reset_index()
    )

    # Build per-customer dict: {customer: {cat: revenue}}
    customer_category_map = {}
    for _, row in customer_cats.iterrows():
        cust = row['customer']
        if cust not in customer_category_map:
            customer_category_map[cust] = {}
        customer_category_map[cust][row['cross_sell_cat']] = float(row['amount'])

    # Overall category summary
    cat_summary = (
        l3m_product.groupby('category')
        .agg(revenue=('amount', 'sum'), transactions=('amount', 'count'),
             customers=('customer', 'nunique'))
        .reset_index()
        .sort_values('revenue', ascending=False)
    )

    return customer_category_map, cat_summary


def calculate_order_frequency(transactions_df, rfm_df, analysis_date, l12m_start):
    """Calculate expected order interval using unique order dates within L12M.

    Uses unique transaction dates (not line item counts) so a single order
    with many line items counts as one order event.  Only L12M activity is
    used for the interval calculation so the metric reflects recent
    purchasing behaviour.
    """
    # Build per-customer unique order dates within L12M
    l12m_trans = transactions_df[transactions_df['date'] >= l12m_start].copy()
    l12m_trans['order_date'] = l12m_trans['date'].dt.date

    order_dates_by_cust = (
        l12m_trans.groupby('customer')['order_date']
        .apply(lambda x: sorted(x.unique()))
        .to_dict()
    )

    results = []
    for _, row in rfm_df.iterrows():
        cust = row['customer']
        recency = row['recency_days']
        last = pd.to_datetime(row['last_purchase_date'])
        segment = row['segment']
        monetary = float(row['monetary_value'])

        dates = order_dates_by_cust.get(cust, [])
        n_orders = len(dates)

        if n_orders >= 2:
            first_l12m = pd.Timestamp(dates[0])
            last_l12m = pd.Timestamp(dates[-1])
            span_days = (last_l12m - first_l12m).days
            expected_interval = span_days / (n_orders - 1)
        else:
            expected_interval = None

        days_overdue = 0
        if expected_interval and expected_interval > 0 and recency > 0:
            days_overdue = max(0, recency - expected_interval * 1.3)

        results.append({
            'customer': cust,
            'recency_days': int(recency),
            'l12m_order_count': n_orders,
            'monetary_value': monetary,
            'expected_interval_days': round(expected_interval, 0) if expected_interval else None,
            'days_overdue': round(days_overdue, 0),
            'last_purchase_date': str(last.date()),
            'segment': segment,
        })

    return results


def calculate_scorecard_kpis(transactions_df, l3m_start, analysis_date):
    """Calculate aggregate KPIs for the scorecard header.

    Returns dict with L3M and L12M order counts, unique customers,
    average order size, and new customer count.
    """
    from dateutil.relativedelta import relativedelta

    l12m_start = analysis_date - relativedelta(months=12) + relativedelta(days=1)

    l3m_trans = transactions_df[transactions_df['date'] >= l3m_start].copy()
    l12m_trans = transactions_df[transactions_df['date'] >= l12m_start].copy()

    # Unique orders = unique (customer, date) pairs
    l3m_trans['order_date'] = l3m_trans['date'].dt.date
    l12m_trans['order_date'] = l12m_trans['date'].dt.date

    l3m_orders = l3m_trans.drop_duplicates(subset=['customer', 'order_date'])
    l12m_orders = l12m_trans.drop_duplicates(subset=['customer', 'order_date'])

    l3m_order_count = len(l3m_orders)
    l12m_order_count = len(l12m_orders)

    l3m_unique_customers = l3m_trans['customer'].nunique()
    l12m_unique_customers = l12m_trans['customer'].nunique()

    l3m_total_revenue = l3m_trans['amount'].sum()
    l12m_total_revenue = l12m_trans['amount'].sum()

    l3m_avg_order_size = l3m_total_revenue / l3m_order_count if l3m_order_count > 0 else 0
    l12m_avg_order_size = l12m_total_revenue / l12m_order_count if l12m_order_count > 0 else 0

    # New customers: active in L3M but NO orders in the 12 months before L3M start
    prior_12m_start = l3m_start - relativedelta(months=12)
    prior_12m_end = l3m_start - relativedelta(days=1)
    prior_trans = transactions_df[
        (transactions_df['date'] >= prior_12m_start) &
        (transactions_df['date'] <= prior_12m_end)
    ]
    prior_customers = set(prior_trans['customer'].unique())
    l3m_customers = set(l3m_trans['customer'].unique())
    new_customers = l3m_customers - prior_customers
    new_customer_names = sorted(new_customers)

    return {
        'l3m_orders': int(l3m_order_count),
        'l12m_orders': int(l12m_order_count),
        'l3m_unique_customers': int(l3m_unique_customers),
        'l12m_unique_customers': int(l12m_unique_customers),
        'l3m_avg_order_size': float(l3m_avg_order_size),
        'l12m_avg_order_size': float(l12m_avg_order_size),
        'new_customers_count': len(new_customers),
        'new_customer_names': new_customer_names,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_customer_analysis(period, year, month, l3m_year, l3m_month, base_path="."):
    """Main function to run customer analysis"""
    print("=" * 80)
    print("CUSTOMER ANALYSIS FOR DASHBOARD")
    print("=" * 80)
    print()

    # File paths
    input_folder = os.path.join(base_path, f"inputs/{period}")
    sales_file = find_input_file(input_folder, ["sales", "customer"])
    income_file = find_input_file(input_folder, ["income", "customer"])
    rfm_file = os.path.join(base_path, f"generated/{period}/rfm_analysis_results.csv")
    output_dir = os.path.join(base_path, f"generated/{period}")
    os.makedirs(output_dir, exist_ok=True)

    import calendar
    last_day = calendar.monthrange(year, month)[1]
    analysis_date = datetime(year, month, last_day)
    l3m_start = datetime(l3m_year, l3m_month, 1)

    # Load and parse transaction data (now with product categories)
    print("Loading customer sales data...")
    transactions_df = parse_customer_sales_data(sales_file)
    print(f"[OK] Loaded {len(transactions_df):,} transactions")
    cat_counts = transactions_df['category'].value_counts()
    print(f"[OK] Product categories: {dict(cat_counts)}")
    print()

    # Load customer income data
    print("Loading customer income/GP data...")
    customer_income_df = load_customer_income_data(income_file)
    print(f"[OK] Loaded income data for {len(customer_income_df)} customers")
    print(f"[OK] Average GP margin: {customer_income_df['gp_margin_pct'].mean():.1f}%")
    print()

    # Calculate customer metrics
    print("Calculating L3M and L12M metrics...")
    customer_metrics, total_l3m, total_l12m = calculate_customer_metrics(
        transactions_df, customer_income_df, l3m_year, l3m_month, year, month
    )
    print(f"[OK] Analyzed {len(customer_metrics)} customers")
    print()

    # Calculate product category metrics
    print("Analyzing product categories...")
    customer_category_map, cat_summary = calculate_category_metrics(transactions_df, l3m_start)
    print(f"[OK] {len(cat_summary)} product categories identified")
    print()

    # Get top 15 customers by L12M sales
    top_15_l12m = customer_metrics.nlargest(15, 'l12m_sales')

    # Load RFM data
    print("Loading RFM analysis results...")
    rfm_df = pd.read_csv(rfm_file)
    print(f"[OK] Loaded RFM data for {len(rfm_df)} customers")
    print()

    # Calculate order frequency and overdue status (using trailing 12-month unique order dates)
    print("Calculating order frequency and overdue status...")
    from dateutil.relativedelta import relativedelta
    trailing_12m_start = analysis_date - relativedelta(months=12)
    frequency_data = calculate_order_frequency(transactions_df, rfm_df, analysis_date, trailing_12m_start)
    print(f"[OK] Frequency analysis complete")
    print()

    # Load backlog for cross-reference
    print("Loading backlog data for cross-reference...")
    backlog_customers, backlog_reps = load_backlog_customers(period, base_path)
    print(f"[OK] {len(backlog_customers)} customers with active backlog orders")
    print()

    # Calculate scorecard KPIs
    print("Calculating scorecard KPIs...")
    scorecard_kpis = calculate_scorecard_kpis(transactions_df, l3m_start, analysis_date)
    print(f"[OK] L3M: {scorecard_kpis['l3m_orders']} orders, {scorecard_kpis['l3m_unique_customers']} customers, avg ${scorecard_kpis['l3m_avg_order_size']:,.0f}")
    print(f"[OK] New customers in L3M: {scorecard_kpis['new_customers_count']}")
    print()

    # Merge RFM data with top 15
    top_15_with_rfm = pd.merge(
        top_15_l12m,
        rfm_df[['customer', 'segment', 'rfm_score', 'rfm_total', 'recency_days']],
        on='customer',
        how='left'
    )

    # Prepare output data
    print("Preparing dashboard data...")

    # --- Top 15 customers (enhanced with categories) ---
    top_customers_list = []
    for idx, row in top_15_with_rfm.iterrows():
        cust = row['customer']
        cats = customer_category_map.get(cust, {})
        cats_list = sorted(cats.keys())

        top_customers_list.append({
            'customer': cust,
            'l3m_sales': float(row['l3m_sales']),
            'l3m_gross_profit': float(row['l3m_gross_profit']),
            'l3m_gp_margin': float(row['l3m_gp_margin']),
            'l3m_pct_of_total': float(row['l3m_pct_of_total']),
            'l12m_sales': float(row['l12m_sales']),
            'l12m_gross_profit': float(row['l12m_gross_profit']),
            'l12m_gp_margin': float(row['l12m_gp_margin']),
            'l12m_pct_of_total': float(row['l12m_pct_of_total']),
            'rfm_segment': row['segment'] if pd.notna(row['segment']) else 'Unknown',
            'rfm_score': row['rfm_score'] if pd.notna(row['rfm_score']) else 'N/A',
            'recency_days': int(row['recency_days']) if pd.notna(row['recency_days']) else None,
            'categories': cats_list,
            'category_count': len(cats_list),
        })

    # --- RFM segment summary ---
    segment_summary = []
    for segment, group in rfm_df.groupby('segment'):
        segment_summary.append({
            'segment': segment,
            'customer_count': len(group),
            'total_revenue': float(group['monetary_value'].sum()),
            'avg_revenue_per_customer': float(group['monetary_value'].mean()),
            'avg_recency_days': float(group['recency_days'].mean()),
            'avg_frequency': float(group['frequency'].mean())
        })
    segment_summary = sorted(segment_summary, key=lambda x: x['total_revenue'], reverse=True)

    # --- Overdue customers ---
    overdue_list = []
    for fd in frequency_data:
        if fd['days_overdue'] > 0 and fd['l12m_order_count'] >= 3:
            has_backlog = fd['customer'] in backlog_customers
            backlog_val = backlog_customers.get(fd['customer'], 0)
            overdue_list.append({
                'customer': fd['customer'],
                'expected_interval_days': fd['expected_interval_days'],
                'recency_days': fd['recency_days'],
                'days_overdue': fd['days_overdue'],
                'last_purchase_date': fd['last_purchase_date'],
                'l12m_sales': fd['monetary_value'],
                'segment': fd['segment'],
                'has_backlog_order': has_backlog,
                'backlog_value': backlog_val,
            })
    overdue_list.sort(key=lambda x: (-x['l12m_sales'] if not x['has_backlog_order'] else 0, -x['days_overdue']))

    # --- Cross-sell opportunities ---
    cross_sell_list = []
    # Only consider customers with meaningful L3M activity
    active_customers = customer_metrics[customer_metrics['l3m_sales'] > 0]
    for _, row in active_customers.iterrows():
        cust = row['customer']
        cats = customer_category_map.get(cust, {})
        cats_list = [c for c in cats.keys() if c in ALL_CROSS_SELL_CATEGORIES]
        missing = [c for c in ALL_CROSS_SELL_CATEGORIES if c not in cats_list]
        if missing and len(cats_list) >= 1 and row['l3m_sales'] >= 5000:
            cross_sell_list.append({
                'customer': cust,
                'categories_purchased': cats_list,
                'missing_categories': missing,
                'l3m_sales': float(row['l3m_sales']),
                'category_count': len(cats_list),
            })
    cross_sell_list.sort(key=lambda x: -x['l3m_sales'])
    cross_sell_list = cross_sell_list[:25]

    # --- Customers needing attention ---
    attention_list = []
    rfm_lookup = {r['customer']: r for r in frequency_data}
    for _, row in customer_metrics.iterrows():
        cust = row['customer']
        reasons = []
        rfm_info = rfm_lookup.get(cust, {})
        segment = rfm_info.get('segment', '')

        # Signal 1: Overdue to order (excluding backlog-covered)
        days_overdue = rfm_info.get('days_overdue', 0)
        has_backlog = cust in backlog_customers
        if days_overdue > 0 and rfm_info.get('l12m_order_count', 0) >= 3 and not has_backlog:
            reasons.append('Order Overdue')

        # Signal 2: At Risk or Need Attention segment
        if segment in ('At Risk', 'Need Attention', 'Cannot Lose Them'):
            reasons.append('At Risk')

        # Signal 3: Declining trend (L3M monthly rate vs L12M monthly rate)
        trend_pct = 0
        if row['l12m_sales'] > 0 and row['l3m_sales'] >= 0:
            l3m_monthly = row['l3m_sales'] / 3
            l12m_monthly = row['l12m_sales'] / 12
            if l12m_monthly > 0:
                trend_pct = ((l3m_monthly - l12m_monthly) / l12m_monthly) * 100
                if trend_pct < -25:
                    reasons.append('Declining')

        # Signal 4: Low margin on significant volume
        if row['gp_margin_pct'] < 15 and row['l3m_sales'] > 10000:
            reasons.append('Low Margin')

        if reasons and (row['l3m_sales'] > 0 or row['l12m_sales'] > 5000):
            # Suggest action based on highest-priority flag
            if 'Order Overdue' in reasons:
                action = 'Follow up on reorder'
            elif 'Low Margin' in reasons:
                action = 'Review pricing strategy'
            elif 'Declining' in reasons:
                action = 'Review pricing/service'
            elif 'At Risk' in reasons:
                action = 'Schedule retention call'
            else:
                action = 'Review account'

            attention_list.append({
                'customer': cust,
                'reasons': reasons,
                'l3m_sales': float(row['l3m_sales']),
                'l12m_sales': float(row['l12m_sales']),
                'recency_days': rfm_info.get('recency_days', 0),
                'days_overdue': days_overdue,
                'trend_pct': round(trend_pct, 1),
                'gp_margin': float(row['gp_margin_pct']),
                'rfm_segment': segment,
                'has_backlog_order': has_backlog,
                'backlog_value': backlog_customers.get(cust, 0),
                'suggested_action': action,
                'sales_rep': backlog_reps.get(cust, ''),
            })
    # Sort: most reasons first, then by L12M sales descending
    attention_list.sort(key=lambda x: (-len(x['reasons']), -x['l12m_sales']))
    attention_list = attention_list[:30]

    # --- Product category summary ---
    product_categories = []
    for _, row in cat_summary.iterrows():
        product_categories.append({
            'category': row['category'],
            'l3m_revenue': float(row['revenue']),
            'l3m_transactions': int(row['transactions']),
            'l3m_customers': int(row['customers']),
        })

    # --- Category heatmap data for top customers ---
    category_heatmap = []
    for tc in top_customers_list:
        cust = tc['customer']
        cats = customer_category_map.get(cust, {})
        entry = {'customer': cust.split('/')[0].strip()}
        for cat in ALL_CROSS_SELL_CATEGORIES:
            entry[cat] = round(cats.get(cat, 0), 0)
        category_heatmap.append(entry)

    # Build output
    month_names = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
    l3m_period = f"{month_names[l3m_month-1][:3]}-{month_names[month-1][:3]} {year}"

    # L12M period label (trailing 12 months)
    from dateutil.relativedelta import relativedelta
    l12m_start_date = analysis_date - relativedelta(months=12) + relativedelta(days=1)
    l12m_period = f"{month_names[l12m_start_date.month-1][:3]} {l12m_start_date.year}-{month_names[month-1][:3]} {year}"

    dashboard_data = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'analysis_period_l3m': l3m_period,
            'analysis_period_l12m': l12m_period,
            'total_customers': len(customer_metrics),
            'total_l3m_sales': float(total_l3m),
            'total_l12m_sales': float(total_l12m)
        },
        'scorecard_kpis': scorecard_kpis,
        'top_15_customers': top_customers_list,
        'rfm_segments': segment_summary,
        'rfm_distribution': {
            'champions': len(rfm_df[rfm_df['segment'] == 'Champions']),
            'loyal_customers': len(rfm_df[rfm_df['segment'] == 'Loyal Customers']),
            'potential_loyalists': len(rfm_df[rfm_df['segment'] == 'Potential Loyalists']),
            'new_customers': len(rfm_df[rfm_df['segment'] == 'New Customers']),
            'at_risk': len(rfm_df[rfm_df['segment'] == 'At Risk']),
            'cannot_lose_them': len(rfm_df[rfm_df['segment'] == 'Cannot Lose Them']),
            'hibernating': len(rfm_df[rfm_df['segment'] == 'Hibernating']),
            'need_attention': len(rfm_df[rfm_df['segment'] == 'Need Attention']),
            'promising': len(rfm_df[rfm_df['segment'] == 'Promising']),
            'other': len(rfm_df[rfm_df['segment'] == 'Other'])
        },
        'customers_needing_attention': attention_list,
        'overdue_customers': overdue_list,
        'cross_sell_opportunities': cross_sell_list,
        'product_category_summary': product_categories,
        'category_heatmap': category_heatmap,
    }

    # Save to JSON
    output_file = os.path.join(output_dir, 'customer_dashboard_data.json')
    with open(output_file, 'w') as f:
        json.dump(dashboard_data, f, indent=2)

    print(f"[OK] Saved dashboard data to: {output_file}")
    print(f"[OK] {len(attention_list)} customers needing attention")
    print(f"[OK] {len(overdue_list)} overdue customers ({sum(1 for o in overdue_list if not o['has_backlog_order'])} truly overdue, {sum(1 for o in overdue_list if o['has_backlog_order'])} covered by backlog)")
    print(f"[OK] {len(cross_sell_list)} cross-sell opportunities")
    print(f"[OK] {len(product_categories)} product categories")
    print()

    print("=" * 80)
    print("CUSTOMER ANALYSIS COMPLETE")
    print("=" * 80)

    return dashboard_data
