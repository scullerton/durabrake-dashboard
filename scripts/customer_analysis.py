"""
Customer Analysis Module
Parameterized version for dashboard generation
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
import os
from file_utils import find_input_file


def parse_customer_sales_data(file_path):
    """Parse the customer sales detail Excel file and extract transactions"""
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

            if transaction_type == 'Invoice' and pd.notna(amount) and amount != 0:
                try:
                    if isinstance(transaction_date, str):
                        trans_date = pd.to_datetime(transaction_date)
                    else:
                        trans_date = transaction_date

                    transactions.append({
                        'customer': current_customer,
                        'date': trans_date,
                        'amount': float(amount)
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


def calculate_customer_metrics(transactions_df, customer_income_df, l3m_year, l3m_month, year, month):
    """Calculate L3M and L12M metrics for each customer"""
    l3m_start = datetime(l3m_year, l3m_month, 1)
    l12m_start = datetime(year, 1, 1)

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

    # Load and parse transaction data
    print("Loading customer sales data...")
    transactions_df = parse_customer_sales_data(sales_file)
    print(f"[OK] Loaded {len(transactions_df):,} transactions")
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

    # Get top 15 customers by L12M sales
    top_15_l12m = customer_metrics.nlargest(15, 'l12m_sales')

    # Load RFM data
    print("Loading RFM analysis results...")
    rfm_df = pd.read_csv(rfm_file)
    print(f"[OK] Loaded RFM data for {len(rfm_df)} customers")
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

    top_customers_list = []
    for idx, row in top_15_with_rfm.iterrows():
        top_customers_list.append({
            'customer': row['customer'],
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
            'recency_days': int(row['recency_days']) if pd.notna(row['recency_days']) else None
        })

    # RFM segment summary
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

    # Build output
    month_names = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
    l3m_period = f"{month_names[l3m_month-1][:3]}-{month_names[month-1][:3]} {year}"

    dashboard_data = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'analysis_period_l3m': l3m_period,
            'analysis_period_l12m': f'Jan-Dec {year}',
            'total_customers': len(customer_metrics),
            'total_l3m_sales': float(total_l3m),
            'total_l12m_sales': float(total_l12m)
        },
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
        }
    }

    # Save to JSON
    output_file = os.path.join(output_dir, 'customer_dashboard_data.json')
    with open(output_file, 'w') as f:
        json.dump(dashboard_data, f, indent=2)

    print(f"[OK] Saved dashboard data to: {output_file}")
    print()

    print("=" * 80)
    print("CUSTOMER ANALYSIS COMPLETE")
    print("=" * 80)

    return dashboard_data
