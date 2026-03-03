"""
Backlog Analysis Module
Parameterized version for dashboard generation
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
import os
from file_utils import find_input_file


def load_backlog_data(file_path):
    """Load and clean backlog data from Excel or CSV file"""
    _, ext = os.path.splitext(file_path)
    if ext.lower() == '.csv':
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)

    df['InvoicesCustomers::DisplayName'] = df['InvoicesCustomers::DisplayName'].str.strip()
    df['Order Date'] = pd.to_datetime(df['Order Date'])
    df['Estimated Invoice Date'] = pd.to_datetime(df['Estimated Invoice Date'])

    df['SubTotal_c for Reports'] = df['SubTotal_c for Reports'].fillna(0)
    df['OrderGrossProfit'] = df['OrderGrossProfit'].fillna(0)
    df['OrderOtherCosts'] = df['OrderOtherCosts'].fillna(0)
    df['GM'] = df['GM'].fillna(0)

    return df


def calculate_backlog_metrics(df, analysis_date):
    """Calculate key backlog metrics"""
    total_backlog_value = df['SubTotal_c for Reports'].sum()
    total_orders = len(df)
    avg_order_value = df['SubTotal_c for Reports'].mean() if total_orders > 0 else 0

    orders_by_customer = df.groupby('InvoicesCustomers::DisplayName').agg({
        'DocNumber': 'count',
        'SubTotal_c for Reports': 'sum'
    }).reset_index()
    orders_by_customer.columns = ['customer', 'order_count', 'total_value']
    orders_by_customer = orders_by_customer.sort_values('total_value', ascending=False)

    orders_by_rep = df.groupby('SalesRep').agg({
        'DocNumber': 'count',
        'SubTotal_c for Reports': 'sum'
    }).reset_index()
    orders_by_rep.columns = ['sales_rep', 'order_count', 'total_value']
    orders_by_rep = orders_by_rep.sort_values('total_value', ascending=False)

    orders_by_region = df.groupby('ShippingAddressRegion').agg({
        'DocNumber': 'count',
        'SubTotal_c for Reports': 'sum'
    }).reset_index()
    orders_by_region.columns = ['region', 'order_count', 'total_value']
    orders_by_region = orders_by_region.sort_values('total_value', ascending=False)

    df['days_old'] = (analysis_date - df['Order Date']).dt.days

    age_buckets = {
        '0-30 days': len(df[df['days_old'] <= 30]),
        '31-60 days': len(df[(df['days_old'] > 30) & (df['days_old'] <= 60)]),
        '61-90 days': len(df[(df['days_old'] > 60) & (df['days_old'] <= 90)]),
        '91-180 days': len(df[(df['days_old'] > 90) & (df['days_old'] <= 180)]),
        '180+ days': len(df[df['days_old'] > 180])
    }

    age_value_buckets = {
        '0-30 days': float(df[df['days_old'] <= 30]['SubTotal_c for Reports'].sum()),
        '31-60 days': float(df[(df['days_old'] > 30) & (df['days_old'] <= 60)]['SubTotal_c for Reports'].sum()),
        '61-90 days': float(df[(df['days_old'] > 60) & (df['days_old'] <= 90)]['SubTotal_c for Reports'].sum()),
        '91-180 days': float(df[(df['days_old'] > 90) & (df['days_old'] <= 180)]['SubTotal_c for Reports'].sum()),
        '180+ days': float(df[df['days_old'] > 180]['SubTotal_c for Reports'].sum())
    }

    future_orders = df[df['Estimated Invoice Date'].notna()].copy()
    if len(future_orders) > 0:
        future_orders['days_to_ship'] = (future_orders['Estimated Invoice Date'] - analysis_date).dt.days

        ship_date_buckets = {
            'Past due': len(future_orders[future_orders['days_to_ship'] < 0]),
            '0-30 days': len(future_orders[(future_orders['days_to_ship'] >= 0) & (future_orders['days_to_ship'] <= 30)]),
            '31-60 days': len(future_orders[(future_orders['days_to_ship'] > 30) & (future_orders['days_to_ship'] <= 60)]),
            '61-90 days': len(future_orders[(future_orders['days_to_ship'] > 60) & (future_orders['days_to_ship'] <= 90)]),
            '90+ days': len(future_orders[future_orders['days_to_ship'] > 90])
        }

        ship_value_buckets = {
            'Past due': float(future_orders[future_orders['days_to_ship'] < 0]['SubTotal_c for Reports'].sum()),
            '0-30 days': float(future_orders[(future_orders['days_to_ship'] >= 0) & (future_orders['days_to_ship'] <= 30)]['SubTotal_c for Reports'].sum()),
            '31-60 days': float(future_orders[(future_orders['days_to_ship'] > 30) & (future_orders['days_to_ship'] <= 60)]['SubTotal_c for Reports'].sum()),
            '61-90 days': float(future_orders[(future_orders['days_to_ship'] > 60) & (future_orders['days_to_ship'] <= 90)]['SubTotal_c for Reports'].sum()),
            '90+ days': float(future_orders[future_orders['days_to_ship'] > 90]['SubTotal_c for Reports'].sum())
        }
    else:
        ship_date_buckets = {}
        ship_value_buckets = {}

    return {
        'total_backlog_value': float(total_backlog_value),
        'total_orders': int(total_orders),
        'avg_order_value': float(avg_order_value),
        'orders_by_customer': orders_by_customer,
        'orders_by_rep': orders_by_rep,
        'orders_by_region': orders_by_region,
        'age_buckets': age_buckets,
        'age_value_buckets': age_value_buckets,
        'ship_date_buckets': ship_date_buckets,
        'ship_value_buckets': ship_value_buckets,
        'avg_age_days': float(df['days_old'].mean())
    }


def run_backlog_analysis(period, year, month, last_day, base_path="."):
    """Main function to run backlog analysis"""
    print("=" * 80)
    print("BACKLOG ANALYSIS FOR DASHBOARD")
    print("=" * 80)
    print()

    analysis_date = datetime(year, month, last_day)

    # File paths
    input_folder = os.path.join(base_path, f"inputs/{period}")
    backlog_file = find_input_file(input_folder, ["backlog"], extensions=[".xlsx", ".csv"])
    output_dir = os.path.join(base_path, f"generated/{period}")
    os.makedirs(output_dir, exist_ok=True)

    # Load backlog data
    print("Loading backlog data...")
    df = load_backlog_data(backlog_file)
    print(f"[OK] Loaded {len(df)} orders")
    print()

    # Calculate metrics
    print("Calculating backlog metrics...")
    metrics = calculate_backlog_metrics(df, analysis_date)
    print(f"[OK] Total backlog value: ${metrics['total_backlog_value']:,.2f}")
    print(f"[OK] Total orders: {metrics['total_orders']}")
    print(f"[OK] Average order value: ${metrics['avg_order_value']:,.2f}")
    print(f"[OK] Average order age: {metrics['avg_age_days']:.0f} days")
    print()

    # Build output data
    dashboard_data = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'analysis_date': f'{year}-{month:02d}-{last_day:02d}',
            'source_file': os.path.basename(backlog_file)
        },
        'summary': {
            'total_backlog_value': metrics['total_backlog_value'],
            'total_orders': metrics['total_orders'],
            'avg_order_value': metrics['avg_order_value'],
            'avg_age_days': metrics['avg_age_days']
        },
        'top_customers': [
            {
                'customer': row['customer'],
                'order_count': int(row['order_count']),
                'total_value': float(row['total_value'])
            }
            for _, row in metrics['orders_by_customer'].head(10).iterrows()
        ],
        'backlog_by_customer': [
            {
                'customer': row['customer'],
                'order_count': int(row['order_count']),
                'total_value': float(row['total_value'])
            }
            for _, row in metrics['orders_by_customer'].iterrows()
        ],
        'by_sales_rep': [
            {
                'sales_rep': row['sales_rep'] if pd.notna(row['sales_rep']) else 'Unassigned',
                'order_count': int(row['order_count']),
                'total_value': float(row['total_value'])
            }
            for _, row in metrics['orders_by_rep'].iterrows()
        ],
        'by_region': [
            {
                'region': row['region'] if pd.notna(row['region']) else 'Unknown',
                'order_count': int(row['order_count']),
                'total_value': float(row['total_value'])
            }
            for _, row in metrics['orders_by_region'].iterrows()
        ],
        'age_distribution': {
            'order_count': metrics['age_buckets'],
            'order_value': metrics['age_value_buckets']
        },
        'ship_date_distribution': {
            'order_count': metrics['ship_date_buckets'],
            'order_value': metrics['ship_value_buckets']
        }
    }

    # Save to JSON
    output_file = os.path.join(output_dir, 'backlog_dashboard_data.json')
    with open(output_file, 'w') as f:
        json.dump(dashboard_data, f, indent=2)

    print(f"[OK] Saved dashboard data to: {output_file}")
    print()

    print("=" * 80)
    print("BACKLOG ANALYSIS COMPLETE")
    print("=" * 80)

    return dashboard_data
