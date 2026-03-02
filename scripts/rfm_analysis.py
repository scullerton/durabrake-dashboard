"""
RFM Analysis Module
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


def calculate_rfm_metrics(transactions_df, analysis_date):
    """Calculate RFM metrics for each customer"""
    rfm_data = []

    for customer in transactions_df['customer'].unique():
        customer_trans = transactions_df[transactions_df['customer'] == customer]

        last_purchase_date = customer_trans['date'].max()
        recency_days = (analysis_date - last_purchase_date).days
        frequency = len(customer_trans)
        monetary_value = customer_trans['amount'].sum()

        rfm_data.append({
            'customer': customer,
            'recency_days': recency_days,
            'frequency': frequency,
            'monetary_value': monetary_value,
            'last_purchase_date': last_purchase_date,
            'first_purchase_date': customer_trans['date'].min()
        })

    return pd.DataFrame(rfm_data)


def assign_rfm_scores(rfm_df):
    """Assign RFM scores (1-5) for each dimension using quintiles"""
    try:
        rfm_df['r_score'] = pd.qcut(rfm_df['recency_days'], q=5, labels=[5, 4, 3, 2, 1], duplicates='drop')
    except ValueError:
        rfm_df['r_score'] = pd.cut(rfm_df['recency_days'], bins=5, labels=[5, 4, 3, 2, 1], duplicates='drop')

    try:
        rfm_df['f_score'] = pd.qcut(rfm_df['frequency'], q=5, labels=[1, 2, 3, 4, 5], duplicates='drop')
    except ValueError:
        rfm_df['f_score'] = pd.cut(rfm_df['frequency'].rank(pct=True), bins=5, labels=[1, 2, 3, 4, 5])

    try:
        rfm_df['m_score'] = pd.qcut(rfm_df['monetary_value'], q=5, labels=[1, 2, 3, 4, 5], duplicates='drop')
    except ValueError:
        rfm_df['m_score'] = pd.cut(rfm_df['monetary_value'].rank(pct=True), bins=5, labels=[1, 2, 3, 4, 5])

    rfm_df['r_score'] = rfm_df['r_score'].astype(int)
    rfm_df['f_score'] = rfm_df['f_score'].astype(int)
    rfm_df['m_score'] = rfm_df['m_score'].astype(int)

    rfm_df['rfm_score'] = rfm_df['r_score'].astype(str) + rfm_df['f_score'].astype(str) + rfm_df['m_score'].astype(str)
    rfm_df['rfm_total'] = rfm_df['r_score'] + rfm_df['f_score'] + rfm_df['m_score']

    return rfm_df


def segment_customers(rfm_df):
    """Segment customers based on RFM scores"""
    def get_segment(row):
        r, f, m = row['r_score'], row['f_score'], row['m_score']

        if r >= 4 and f >= 4 and m >= 4:
            return 'Champions'
        elif r >= 3 and f >= 3 and m >= 3:
            return 'Loyal Customers'
        elif r >= 4 and f <= 2:
            return 'New Customers'
        elif r >= 3 and f <= 3 and m >= 3:
            return 'Potential Loyalists'
        elif r <= 2 and f >= 3 and m >= 3:
            return 'At Risk'
        elif r <= 2 and f >= 4 and m >= 4:
            return 'Cannot Lose Them'
        elif r <= 2 and f <= 2:
            return 'Hibernating'
        elif r <= 3 and f <= 3:
            return 'Need Attention'
        elif r >= 3 and f <= 2 and m <= 3:
            return 'Promising'
        else:
            return 'Other'

    rfm_df['segment'] = rfm_df.apply(get_segment, axis=1)
    return rfm_df


def generate_summary_stats(rfm_df):
    """Generate summary statistics"""
    summary = {
        'total_customers': len(rfm_df),
        'total_revenue': float(rfm_df['monetary_value'].sum()),
        'avg_revenue_per_customer': float(rfm_df['monetary_value'].mean()),
        'avg_recency_days': float(rfm_df['recency_days'].mean()),
        'avg_frequency': float(rfm_df['frequency'].mean()),
        'top_10_customers': []
    }

    top_10 = rfm_df.nlargest(10, 'monetary_value')
    for _, row in top_10.iterrows():
        summary['top_10_customers'].append({
            'customer': row['customer'],
            'monetary_value': float(row['monetary_value']),
            'frequency': int(row['frequency']),
            'recency_days': int(row['recency_days']),
            'rfm_score': row['rfm_score'],
            'segment': row['segment']
        })

    return summary


def run_rfm_analysis(period, year, month, last_day, base_path="."):
    """Main function to run RFM analysis"""
    print("=" * 80)
    print("RFM ANALYSIS - DuraBrake Customer Base")
    print("=" * 80)

    analysis_date = datetime(year, month, last_day)
    print(f"Analysis Date: {analysis_date.strftime('%B %d, %Y')}")
    print()

    # File paths
    input_folder = os.path.join(base_path, f"inputs/{period}")
    input_file = find_input_file(input_folder, ["sales", "customer"])
    output_dir = os.path.join(base_path, f"generated/{period}")
    os.makedirs(output_dir, exist_ok=True)

    # Load and parse data
    print("Loading customer sales data...")
    transactions_df = parse_customer_sales_data(input_file)
    print(f"[OK] Loaded {len(transactions_df):,} transactions")
    print()

    # Calculate RFM metrics
    print("Calculating RFM metrics...")
    rfm_df = calculate_rfm_metrics(transactions_df, analysis_date)
    print(f"[OK] Analyzed {len(rfm_df)} unique customers")
    print()

    # Assign RFM scores
    print("Assigning RFM scores...")
    rfm_df = assign_rfm_scores(rfm_df)
    print("[OK] Scores assigned (1-5 scale)")
    print()

    # Segment customers
    print("Segmenting customers...")
    rfm_df = segment_customers(rfm_df)
    print("[OK] Customers segmented")
    print()

    # Generate summary
    summary = generate_summary_stats(rfm_df)

    # Segment summary
    segment_summary = []
    for segment, group in rfm_df.groupby('segment'):
        segment_summary.append({
            'segment': segment,
            'customer_count': len(group),
            'total_revenue': float(group['monetary_value'].sum()),
            'avg_revenue': float(group['monetary_value'].mean()),
            'avg_recency': float(group['recency_days'].mean()),
            'avg_frequency': float(group['frequency'].mean())
        })

    # Save outputs
    print("Saving results...")

    output_csv = os.path.join(output_dir, 'rfm_analysis_results.csv')
    rfm_df.to_csv(output_csv, index=False)
    print(f"[OK] Saved detailed results to: {output_csv}")

    summary['segment_summary'] = segment_summary

    # Convert datetime objects to strings
    for customer in summary['top_10_customers']:
        pass  # Already converted to basic types

    output_json = os.path.join(output_dir, 'rfm_summary.json')
    with open(output_json, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"[OK] Saved summary to: {output_json}")

    print()
    print("=" * 80)
    print("RFM ANALYSIS COMPLETE")
    print("=" * 80)

    return rfm_df, summary
