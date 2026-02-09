"""
DuraBrake Financial Dashboard
Streamlit dashboard displaying monthly financial metrics with L3M comparison

To run: streamlit run financial_dashboard.py
"""

import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# Page config
st.set_page_config(
    page_title="DuraBrake Financial Dashboard",
    page_icon="📊",
    layout="wide"
)

# ============================================================================
# AUTHENTICATION
# ============================================================================
import hashlib

# Password configuration
# In Streamlit Cloud, credentials come from secrets
# Locally, use hardcoded values as fallback
try:
    DASHBOARD_USERNAME = st.secrets["auth"]["username"]
    DASHBOARD_PASSWORD = st.secrets["auth"]["password"]
    DASHBOARD_PASSWORD_HASH = hashlib.sha256(DASHBOARD_PASSWORD.encode()).hexdigest()
except (KeyError, FileNotFoundError):
    # Fallback for local development
    DASHBOARD_USERNAME = "durabrake"
    DASHBOARD_PASSWORD_HASH = hashlib.sha256("Dashboard2025!".encode()).hexdigest()

def check_password():
    """Returns True if the user has entered the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        # Check if both fields exist in session state
        if "username" not in st.session_state or "password" not in st.session_state:
            return

        entered_username = st.session_state.get("username", "")
        entered_password = st.session_state.get("password", "")

        # Only validate if both fields have values
        if not entered_username or not entered_password:
            return

        entered_hash = hashlib.sha256(entered_password.encode()).hexdigest()

        if entered_username == DASHBOARD_USERNAME and entered_hash == DASHBOARD_PASSWORD_HASH:
            st.session_state["password_correct"] = True
            # Don't store password
            if "password" in st.session_state:
                del st.session_state["password"]
            if "username" in st.session_state:
                del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    # Return True if password already validated
    if st.session_state.get("password_correct", False):
        return True

    # Show login form
    st.markdown("## 🔐 DuraBrake Dashboard Login")
    st.markdown("Please enter your credentials to access the financial dashboard.")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.text_input("Username", key="username", on_change=password_entered)
        st.text_input("Password", type="password", key="password", on_change=password_entered)

        if st.session_state.get("password_correct") is False:
            st.error("😕 Incorrect username or password")

        st.caption("Contact your administrator if you need access.")

    return False

# Check authentication before loading dashboard
if not check_password():
    st.stop()

# ============================================================================
# PERFORMANCE INDICATOR CONFIGURATION
# ============================================================================

# Working Capital Thresholds
WC_THRESHOLDS = {
    "dso": {"green": 30, "yellow": 45},      # Days Sales Outstanding
    "dio": {"green": 85, "yellow": 105},     # Days Inventory Outstanding
    "dpo": {"green": 30, "yellow": 20},      # Days Payable Outstanding (reversed - higher is better)
    "ccc": {"green": 30, "yellow": 60},      # Cash Conversion Cycle
    "nwc_pct": {"green": 15, "yellow": 25}   # NWC as % of Revenue
}

# Backlog Thresholds
BACKLOG_THRESHOLDS = {
    "avg_age": {"green": 45, "yellow": 60},  # Average order age in days
    "old_orders_pct": {"green": 10, "yellow": 20}  # % of orders > 90 days
}

# Helper functions for color coding
def get_color_for_metric(value, green_threshold, yellow_threshold, reverse=False):
    """
    Returns color for a metric based on thresholds.
    reverse=False: lower is better (e.g., DSO, DIO, CCC)
    reverse=True: higher is better (e.g., DPO, margins)
    """
    if not reverse:
        # Lower is better
        if value <= green_threshold:
            return 'background-color: #d4edda'  # Light green
        elif value <= yellow_threshold:
            return 'background-color: #fff3cd'  # Light yellow
        else:
            return 'background-color: #f8d7da'  # Light red
    else:
        # Higher is better
        if value >= green_threshold:
            return 'background-color: #d4edda'  # Light green
        elif value >= yellow_threshold:
            return 'background-color: #fff3cd'  # Light yellow
        else:
            return 'background-color: #f8d7da'  # Light red

def color_gp_margin(val, avg_margin):
    """Color code GP margin based on company average"""
    try:
        margin = float(val)
        if margin >= avg_margin:
            return 'background-color: #d4edda'  # Green - above average
        elif margin >= avg_margin - 5:
            return 'background-color: #fff3cd'  # Yellow - within 5% of average
        else:
            return 'background-color: #f8d7da'  # Red - more than 5% below average
    except:
        return ''

def color_sales_trend(l3m_sales, l12m_sales):
    """Color code based on sales trend (L3M vs L12M run rate)"""
    try:
        l3m_monthly = l3m_sales / 3
        l12m_monthly = l12m_sales / 12

        if l12m_monthly == 0:
            return ''

        change_pct = ((l3m_monthly - l12m_monthly) / l12m_monthly) * 100

        if change_pct > 10:
            return 'background-color: #d4edda'  # Green - growing >10%
        elif change_pct < -10:
            return 'background-color: #f8d7da'  # Red - declining >10%
        else:
            return 'background-color: #fff3cd'  # Yellow - stable ±10%
    except:
        return ''

# ============================================================================
# CONFIGURATION - Update this to match the period you want to view
# ============================================================================
PERIOD = "25.12"  # Format: YY.MM

# Load data
@st.cache_data(ttl=60)  # Cache for 60 seconds to allow for updates
def load_data(period):
    try:
        import os
        file_path = os.path.join('generated', period, 'dashboard_data.json')
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"dashboard_data.json not found for period {period}. Please run generate_dashboard.py first.")
        return None

@st.cache_data(ttl=60)
def load_customer_data(period):
    try:
        import os
        file_path = os.path.join('generated', period, 'customer_dashboard_data.json')
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

@st.cache_data(ttl=60)
def load_backlog_data(period):
    try:
        import os
        file_path = os.path.join('generated', period, 'backlog_dashboard_data.json')
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

# Helper function to get available periods
def get_available_periods():
    """Get list of available periods from generated folder"""
    import os
    generated_path = 'generated'
    if not os.path.exists(generated_path):
        return []
    periods = [d for d in os.listdir(generated_path)
               if os.path.isdir(os.path.join(generated_path, d)) and
               os.path.exists(os.path.join(generated_path, d, 'dashboard_data.json'))]
    # Sort periods in reverse chronological order (newest first)
    return sorted(periods, reverse=True)

data = load_data(PERIOD)
customer_data = load_customer_data(PERIOD)
backlog_data = load_backlog_data(PERIOD)

if data:
    # Header
    st.title("📊 DuraBrake Financial Dashboard")
    st.subheader(f"{data['metadata']['reporting_month']} {data['metadata']['reporting_year']}")
    st.caption(f"Data generated: {data['metadata']['generated_at']}")

    # Create tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📈 Summary", "🏭 Product Details", "💰 NWC Details", "👥 Customers", "📦 Order Backlog", "📚 Historicals"])

    with tab1:
        # ==================================================================
        # CURRENT MONTH SNAPSHOT
        # ==================================================================
        st.header("📈 Current Month Snapshot")

        cm = data['current_month']

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Revenue", f"${cm['revenue']:,.0f}")
            st.metric("Gross Profit", f"${cm['gross_profit']:,.0f}")

        with col2:
            st.metric("EBITDA", f"${cm['ebitda']:,.0f}")
            st.metric("Net Income", f"${cm['net_income']:,.0f}")

        with col3:
            st.metric("Gross Margin %", f"{cm['gross_margin_pct']:.1f}%")
            st.metric("EBITDA Margin %", f"{cm['ebitda_margin_pct']:.1f}%")

        with col4:
            st.metric("NWC", f"${cm['nwc']:,.0f}")
            st.metric("Operating CF", f"${cm['operating_cash_flow']:,.0f}")

        st.divider()

        # ==================================================================
        # CRITICAL NOTES & ACTION ITEMS
        # ==================================================================
        st.header("⚠️ Critical Notes & Action Items")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📝 Critical Notes")
            notes = st.text_area(
                "Add critical notes for this period",
                height=150,
                placeholder="Example:\n• Revenue declined due to seasonal slowdown\n• Major customer order delayed to next month\n• Supply chain issues affecting margins",
                key="critical_notes"
            )

        with col2:
            st.subheader("✅ Action Items")
            actions = st.text_area(
                "Add action items to address",
                height=150,
                placeholder="Example:\n• Follow up with top 3 customers on Q1 orders\n• Review pricing strategy for Rotors product line\n• Reduce inventory levels by 10%",
                key="action_items"
            )

        if notes or actions:
            st.info("💡 **Tip:** Copy these notes to a separate document for record-keeping. They are not automatically saved.")

        st.divider()

        # ==================================================================
        # L3M COMPARISON SECTION
        # ==================================================================
        st.header("🎯 Last 3 Months Comparison")
        st.markdown(f"**{data['metadata']['reporting_month']}** vs **Prior 3-Month Average**")

        l3m = data['l3m_comparison']

        # Create 3 columns for key metrics
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                label="Revenue",
                value=f"${l3m['revenue']['current']:,.0f}",
                delta=f"{l3m['revenue']['variance_pct']:.1f}%",
                delta_color="normal"
            )
            st.caption(f"L3M Avg: ${l3m['revenue']['l3m_avg']:,.0f}")

        with col2:
            st.metric(
                label="EBITDA",
                value=f"${l3m['ebitda']['current']:,.0f}",
                delta=f"{l3m['ebitda']['variance_pct']:.1f}%",
                delta_color="normal"
            )
            st.caption(f"L3M Avg: ${l3m['ebitda']['l3m_avg']:,.0f}")

        with col3:
            st.metric(
                label="Gross Margin %",
                value=f"{l3m['gross_margin_pct']['current']:.1f}%",
                delta=f"{l3m['gross_margin_pct']['variance_pts']:.1f} pts",
                delta_color="normal"
            )
            st.caption(f"L3M Avg: {l3m['gross_margin_pct']['l3m_avg']:.1f}%")

        # Additional L3M metrics
        col4, col5, col6 = st.columns(3)

        with col4:
            st.metric(
                label="Gross Profit",
                value=f"${l3m['gross_profit']['current']:,.0f}",
                delta=f"{l3m['gross_profit']['variance_pct']:.1f}%",
                delta_color="normal"
            )

        with col5:
            st.metric(
                label="EBITDA Margin %",
                value=f"{l3m['ebitda_margin_pct']['current']:.1f}%",
                delta=f"{l3m['ebitda_margin_pct']['variance_pts']:.1f} pts",
                delta_color="normal"
            )

        with col6:
            st.metric(
                label="Net Income",
                value=f"${l3m['net_income']['current']:,.0f}",
                delta=f"{l3m['net_income']['variance_pct']:.1f}%" if l3m['net_income']['variance_pct'] and abs(l3m['net_income']['variance_pct']) < 1000 else "N/A",
                delta_color="normal"
            )

        st.divider()

        # ==================================================================
        # MONTHLY TRENDS
        # ==================================================================
        st.header("📊 Monthly Trends")

        # Convert monthly series to DataFrame
        df_monthly = pd.DataFrame(data['monthly_series'])

        # Revenue & EBITDA chart
        fig = go.Figure()

        fig.add_trace(go.Bar(
            name='Revenue',
            x=df_monthly['month'],
            y=df_monthly['revenue'],
            yaxis='y',
            marker_color='#1f77b4'
        ))

        fig.add_trace(go.Scatter(
            name='EBITDA',
            x=df_monthly['month'],
            y=df_monthly['ebitda'],
            yaxis='y2',
            marker_color='#ff7f0e',
            line=dict(width=3)
        ))

        fig.update_layout(
            title='Revenue & EBITDA Trend',
            yaxis=dict(title='Revenue ($)', side='left'),
            yaxis2=dict(title='EBITDA ($)', side='right', overlaying='y'),
            hovermode='x unified',
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

        # Margins chart
        fig2 = go.Figure()

        fig2.add_trace(go.Scatter(
            name='Gross Margin %',
            x=df_monthly['month'],
            y=df_monthly['gross_margin_pct'],
            marker_color='#2ca02c',
            line=dict(width=2)
        ))

        fig2.add_trace(go.Scatter(
            name='EBITDA Margin %',
            x=df_monthly['month'],
            y=df_monthly['ebitda_margin_pct'],
            marker_color='#d62728',
            line=dict(width=2)
        ))

        fig2.update_layout(
            title='Margin Trends',
            yaxis=dict(title='Margin %'),
            hovermode='x unified',
            height=400
        )

        st.plotly_chart(fig2, use_container_width=True)

        st.divider()

        # ==================================================================
        # ROLLING L3M VARIANCE
        # ==================================================================
        st.header("🔄 Rolling 3-Month Variance")
        st.markdown("Each month compared to its prior 3-month average")

        if data['rolling_l3m']:
            df_rolling = pd.DataFrame(data['rolling_l3m'])

            fig3 = go.Figure()

            fig3.add_trace(go.Bar(
                name='Revenue vs L3M %',
                x=df_rolling['month'],
                y=df_rolling['revenue_vs_l3m_pct'],
                marker_color=['red' if x < 0 else 'green' for x in df_rolling['revenue_vs_l3m_pct']]
            ))

            fig3.update_layout(
                title='Revenue Variance vs Prior 3-Month Average',
                yaxis=dict(title='Variance %'),
                hovermode='x unified',
                height=300
            )

            st.plotly_chart(fig3, use_container_width=True)

        st.divider()

        # ==================================================================
        # YTD SUMMARY
        # ==================================================================
        st.header("📅 Year-to-Date Summary")

        ytd = data['ytd_summary']

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Revenue", f"${ytd['total_revenue']:,.0f}")
            st.metric("Avg Gross Margin %", f"{ytd['avg_gross_margin_pct']:.1f}%")

        with col2:
            st.metric("Total Gross Profit", f"${ytd['total_gross_profit']:,.0f}")
            st.metric("Avg EBITDA Margin %", f"{ytd['avg_ebitda_margin_pct']:.1f}%")

        with col3:
            st.metric("Total EBITDA", f"${ytd['total_ebitda']:,.0f}")
            st.metric("Total Net Income", f"${ytd['total_net_income']:,.0f}")

        with col4:
            st.metric("Avg NWC", f"${ytd['avg_nwc']:,.0f}")
            st.metric("Total Operating CF", f"${ytd['total_operating_cf']:,.0f}")

        st.divider()

        # ==================================================================
        # Q4 SUMMARY
        # ==================================================================
        st.header("Q4 2025 Summary")

        q4 = data['q4_summary']

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Q4 Revenue", f"${q4['total_revenue']:,.0f}")

        with col2:
            st.metric("Q4 Gross Profit", f"${q4['total_gross_profit']:,.0f}")
            st.caption(f"Avg GP%: {q4['avg_gross_margin_pct']:.1f}%")

        with col3:
            st.metric("Q4 EBITDA", f"${q4['total_ebitda']:,.0f}")
            st.caption(f"Avg EBITDA%: {q4['avg_ebitda_margin_pct']:.1f}%")

        with col4:
            st.metric("Q4 Net Income", f"${q4['total_net_income']:,.0f}")

        st.divider()

        # ==================================================================
        # DATA TABLE
        # ==================================================================
        with st.expander("📋 View Detailed Monthly Data"):
            st.dataframe(df_monthly, use_container_width=True)

        # Footer
        st.caption(f"Source: {data['metadata']['source_file']}")

    with tab2:
        # ==================================================================
        # PRODUCT DETAILS
        # ==================================================================
        st.header("🏭 Product Details")
        st.markdown(f"**{data['metadata']['reporting_month']}** vs **Prior 3-Month Average**")

        products = data.get('products', {})

        if products:
            # Create columns for products
            product_keys = ['cast_drums', 'steel_shell_drums', 'rotors', 'calipers', 'pads', 'hubs']

            for product_key in product_keys:
                if product_key in products:
                    prod = products[product_key]

                    st.subheader(prod['name'])

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric(
                            label="Sales",
                            value=f"${prod['current_month']['sales']:,.0f}" if prod['current_month']['sales'] else "N/A",
                            delta=f"{prod['l3m_comparison']['sales']['variance_pct']:.1f}%" if prod['l3m_comparison']['sales']['variance_pct'] else None,
                            delta_color="normal"
                        )
                        if prod['l3m_comparison']['sales']['l3m_avg']:
                            st.caption(f"L3M Avg: ${prod['l3m_comparison']['sales']['l3m_avg']:,.0f}")

                    with col2:
                        st.metric(
                            label="Gross Profit",
                            value=f"${prod['current_month']['gross_profit']:,.0f}" if prod['current_month']['gross_profit'] else "N/A",
                            delta=f"{prod['l3m_comparison']['gross_profit']['variance_pct']:.1f}%" if prod['l3m_comparison']['gross_profit']['variance_pct'] else None,
                            delta_color="normal"
                        )
                        if prod['l3m_comparison']['gross_profit']['l3m_avg']:
                            st.caption(f"L3M Avg: ${prod['l3m_comparison']['gross_profit']['l3m_avg']:,.0f}")

                    with col3:
                        st.metric(
                            label="Gross Margin %",
                            value=f"{prod['current_month']['gross_margin_pct']:.1f}%" if prod['current_month']['gross_margin_pct'] else "N/A",
                            delta=f"{prod['l3m_comparison']['gross_margin_pct']['variance_pts']:.1f} pts" if prod['l3m_comparison']['gross_margin_pct']['variance_pts'] else None,
                            delta_color="normal"
                        )
                        if prod['l3m_comparison']['gross_margin_pct']['l3m_avg']:
                            st.caption(f"L3M Avg: {prod['l3m_comparison']['gross_margin_pct']['l3m_avg']:.1f}%")

                    st.divider()

            # Product trend charts
            st.header("📊 Product Trends")

            # Sales trend by product
            fig_sales = go.Figure()
            for product_key in product_keys:
                if product_key in products:
                    prod = products[product_key]
                    df_prod = pd.DataFrame(prod['monthly_series'])
                    fig_sales.add_trace(go.Scatter(
                        name=prod['name'],
                        x=df_prod['month'],
                        y=df_prod['sales'],
                        mode='lines+markers'
                    ))

            fig_sales.update_layout(
                title='Monthly Sales by Product',
                yaxis=dict(title='Sales ($)'),
                hovermode='x unified',
                height=400
            )
            st.plotly_chart(fig_sales, use_container_width=True)

            # Gross margin % trend by product
            fig_gm = go.Figure()
            for product_key in product_keys:
                if product_key in products:
                    prod = products[product_key]
                    df_prod = pd.DataFrame(prod['monthly_series'])
                    fig_gm.add_trace(go.Scatter(
                        name=prod['name'],
                        x=df_prod['month'],
                        y=df_prod['gross_margin_pct'],
                        mode='lines+markers'
                    ))

            fig_gm.update_layout(
                title='Gross Margin % by Product',
                yaxis=dict(title='Gross Margin %'),
                hovermode='x unified',
                height=400
            )
            st.plotly_chart(fig_gm, use_container_width=True)

        else:
            st.warning("Product data not available. Please run export_dashboard_data.py to generate product-level metrics.")

        # Footer
        st.caption(f"Source: {data['metadata']['source_file']}")

    with tab3:
        # ==================================================================
        # NWC DETAILS
        # ==================================================================
        st.header("💰 Net Working Capital Details")
        st.markdown(f"**{data['metadata']['reporting_month']}** Analysis")

        cm = data['current_month']

        # Current month NWC components
        st.subheader("Current Month Components")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Accounts Receivable", f"${cm['accounts_receivable']:,.0f}")

        with col2:
            st.metric("Inventory", f"${cm['inventory']:,.0f}")

        with col3:
            st.metric("Accounts Payable", f"${cm['accounts_payable']:,.0f}")

        with col4:
            st.metric("Net Working Capital", f"${cm['nwc']:,.0f}")

        st.divider()

        # NWC as % of Revenue
        st.subheader("NWC Ratios")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            # Use YTD (annualized) revenue for more meaningful ratio
            ytd = data['ytd_summary']
            nwc_pct_revenue = (cm['nwc'] / ytd['total_revenue'] * 100) if ytd['total_revenue'] else 0

            # Determine color for NWC %
            if nwc_pct_revenue <= WC_THRESHOLDS['nwc_pct']['green']:
                nwc_color = "🟢"
            elif nwc_pct_revenue <= WC_THRESHOLDS['nwc_pct']['yellow']:
                nwc_color = "🟡"
            else:
                nwc_color = "🔴"

            st.metric("NWC as % of Revenue", f"{nwc_color} {nwc_pct_revenue:.1f}%")
            st.caption("Based on YTD revenue")

        with col2:
            # DSO = (A/R / Revenue) * 365
            ar_days = (cm['accounts_receivable'] / (cm['revenue'] / 30)) if cm['revenue'] else 0

            # Determine color for DSO (lower is better)
            if ar_days <= WC_THRESHOLDS['dso']['green']:
                dso_color = "🟢"
            elif ar_days <= WC_THRESHOLDS['dso']['yellow']:
                dso_color = "🟡"
            else:
                dso_color = "🔴"

            st.metric("Days Sales Outstanding", f"{dso_color} {ar_days:.0f} days")

        with col3:
            # DIO = (Inventory / COGS) * 365, approximating monthly COGS from revenue
            cogs_monthly = cm['revenue'] * (1 - cm['gross_margin_pct'] / 100) if cm['revenue'] and cm['gross_margin_pct'] else cm['revenue']
            inv_days = (cm['inventory'] / (cogs_monthly / 30)) if cogs_monthly else 0

            # Determine color for DIO (lower is better)
            if inv_days <= WC_THRESHOLDS['dio']['green']:
                dio_color = "🟢"
            elif inv_days <= WC_THRESHOLDS['dio']['yellow']:
                dio_color = "🟡"
            else:
                dio_color = "🔴"

            st.metric("Days Inventory Outstanding", f"{dio_color} {inv_days:.0f} days")

        with col4:
            # DPO = (A/P / COGS) * 365
            ap_days = (cm['accounts_payable'] / (cogs_monthly / 30)) if cogs_monthly else 0

            # Determine color for DPO (higher is better - reverse logic)
            if ap_days >= WC_THRESHOLDS['dpo']['green']:
                dpo_color = "🟢"
            elif ap_days >= WC_THRESHOLDS['dpo']['yellow']:
                dpo_color = "🟡"
            else:
                dpo_color = "🔴"

            st.metric("Days Payable Outstanding", f"{dpo_color} {ap_days:.0f} days")

        # Add Cash Conversion Cycle below the 4 main ratios
        st.divider()
        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            # CCC = DSO + DIO - DPO
            ccc = ar_days + inv_days - ap_days

            # Determine color for CCC (lower is better)
            if ccc <= WC_THRESHOLDS['ccc']['green']:
                ccc_color = "🟢"
            elif ccc <= WC_THRESHOLDS['ccc']['yellow']:
                ccc_color = "🟡"
            else:
                ccc_color = "🔴"

            st.metric("Cash Conversion Cycle", f"{ccc_color} {ccc:.0f} days")
            st.caption("DSO + DIO - DPO")

        # Add legend for thresholds
        st.caption(f"💡 Targets: DSO ≤{WC_THRESHOLDS['dso']['green']}d, DIO ≤{WC_THRESHOLDS['dio']['green']}d, DPO ≥{WC_THRESHOLDS['dpo']['green']}d, CCC ≤{WC_THRESHOLDS['ccc']['green']}d, NWC ≤{WC_THRESHOLDS['nwc_pct']['green']}% revenue")

        st.divider()

        # NWC Trends
        st.header("📊 NWC Trends")

        df_monthly = pd.DataFrame(data['monthly_series'])

        # NWC components chart
        fig_nwc = go.Figure()

        fig_nwc.add_trace(go.Scatter(
            name='Accounts Receivable',
            x=df_monthly['month'],
            y=df_monthly['accounts_receivable'],
            mode='lines+markers',
            marker_color='#1f77b4'
        ))

        fig_nwc.add_trace(go.Scatter(
            name='Inventory',
            x=df_monthly['month'],
            y=df_monthly['inventory'],
            mode='lines+markers',
            marker_color='#ff7f0e'
        ))

        fig_nwc.add_trace(go.Scatter(
            name='Accounts Payable',
            x=df_monthly['month'],
            y=df_monthly['accounts_payable'],
            mode='lines+markers',
            marker_color='#2ca02c'
        ))

        fig_nwc.update_layout(
            title='NWC Components Trend',
            yaxis=dict(title='Amount ($)'),
            hovermode='x unified',
            height=400
        )

        st.plotly_chart(fig_nwc, use_container_width=True)

        # Net Working Capital trend
        fig_nwc_total = go.Figure()

        fig_nwc_total.add_trace(go.Bar(
            name='Net Working Capital',
            x=df_monthly['month'],
            y=df_monthly['nwc'],
            marker_color='#9467bd'
        ))

        fig_nwc_total.update_layout(
            title='Net Working Capital Trend',
            yaxis=dict(title='NWC ($)'),
            hovermode='x unified',
            height=400
        )

        st.plotly_chart(fig_nwc_total, use_container_width=True)

        # NWC as % of Revenue trend (using YTD/annualized revenue)
        # Calculate cumulative YTD revenue for each month
        df_monthly['ytd_revenue'] = df_monthly['revenue'].cumsum()
        df_monthly['nwc_pct_revenue'] = (df_monthly['nwc'] / df_monthly['ytd_revenue'] * 100)

        fig_nwc_pct = go.Figure()

        fig_nwc_pct.add_trace(go.Scatter(
            name='NWC as % of YTD Revenue',
            x=df_monthly['month'],
            y=df_monthly['nwc_pct_revenue'],
            mode='lines+markers',
            marker_color='#8c564b',
            line=dict(width=3)
        ))

        fig_nwc_pct.update_layout(
            title='NWC as % of YTD Revenue',
            yaxis=dict(title='NWC % of YTD Revenue'),
            hovermode='x unified',
            height=400
        )

        st.plotly_chart(fig_nwc_pct, use_container_width=True)

        st.divider()

        # Data table
        with st.expander("📋 View Detailed NWC Data"):
            nwc_detail = df_monthly[['month', 'accounts_receivable', 'inventory', 'accounts_payable', 'nwc', 'nwc_pct_revenue']]
            nwc_detail.columns = ['Month', 'A/R', 'Inventory', 'A/P', 'NWC', 'NWC % of YTD Revenue']
            st.dataframe(nwc_detail, use_container_width=True)

        # Footer
        st.caption(f"Source: {data['metadata']['source_file']}")

    with tab4:
        # ==================================================================
        # CUSTOMER ANALYSIS
        # ==================================================================
        st.header("👥 Customer Analysis")

        if customer_data:
            # Display metadata
            st.markdown(f"**Analysis Period:** {customer_data['metadata']['analysis_period_l12m']}")
            st.markdown(f"**Total Customers:** {customer_data['metadata']['total_customers']:,}")
            st.caption(f"Data generated: {customer_data['metadata']['generated_at']}")
            st.divider()

            # ==================================================================
            # RFM ANALYSIS SUMMARY
            # ==================================================================
            st.subheader("🎯 RFM Segmentation Overview")
            st.markdown("Customer segments based on Recency, Frequency, and Monetary value")

            # RFM Distribution
            rfm_dist = customer_data['rfm_distribution']
            rfm_segments = customer_data['rfm_segments']

            # Create segment cards
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                champions = [s for s in rfm_segments if s['segment'] == 'Champions']
                if champions:
                    st.metric(
                        "Champions",
                        f"{rfm_dist['champions']} customers",
                        f"${champions[0]['total_revenue']:,.0f}"
                    )
                    st.caption(f"Avg: ${champions[0]['avg_revenue_per_customer']:,.0f}/customer")

            with col2:
                loyal = [s for s in rfm_segments if s['segment'] == 'Loyal Customers']
                if loyal:
                    st.metric(
                        "Loyal Customers",
                        f"{rfm_dist['loyal_customers']} customers",
                        f"${loyal[0]['total_revenue']:,.0f}"
                    )
                    st.caption(f"Avg: ${loyal[0]['avg_revenue_per_customer']:,.0f}/customer")

            with col3:
                at_risk = [s for s in rfm_segments if s['segment'] == 'At Risk']
                if at_risk:
                    st.metric(
                        "At Risk",
                        f"{rfm_dist['at_risk']} customers",
                        f"${at_risk[0]['total_revenue']:,.0f}"
                    )
                    st.caption(f"Avg {at_risk[0]['avg_recency_days']:.0f} days since last purchase")

            with col4:
                hibernating = [s for s in rfm_segments if s['segment'] == 'Hibernating']
                if hibernating:
                    st.metric(
                        "Hibernating",
                        f"{rfm_dist['hibernating']} customers",
                        f"${hibernating[0]['total_revenue']:,.0f}"
                    )
                    st.caption(f"Need reactivation")

            st.divider()

            # RFM Segment Distribution Chart
            st.subheader("📊 Customer Segment Distribution")

            # Prepare data for chart
            segment_chart_data = []
            for seg in rfm_segments:
                segment_chart_data.append({
                    'Segment': seg['segment'],
                    'Customers': seg['customer_count'],
                    'Revenue': seg['total_revenue']
                })

            df_segments = pd.DataFrame(segment_chart_data)

            # Create two columns for charts
            col1, col2 = st.columns(2)

            with col1:
                # Segment by customer count
                fig_seg_count = px.pie(
                    df_segments,
                    values='Customers',
                    names='Segment',
                    title='Customers by Segment',
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_seg_count.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_seg_count, use_container_width=True)

            with col2:
                # Segment by revenue
                fig_seg_rev = px.pie(
                    df_segments,
                    values='Revenue',
                    names='Segment',
                    title='Revenue by Segment',
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_seg_rev.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_seg_rev, use_container_width=True)

            st.divider()

            # ==================================================================
            # TOP 15 CUSTOMERS PERFORMANCE
            # ==================================================================
            st.subheader("🏆 Top 15 Customers Performance")
            st.markdown("Sales and Gross Profit over Last 3 Months (L3M) and Last 12 Months (L12M)")
            st.caption("Note: GP margins based on actual 2025 annual income by customer. L3M and L12M GP calculated using annual margin %.")

            # Prepare top customers data
            top_15 = customer_data['top_15_customers']
            df_top15 = pd.DataFrame(top_15)

            # Create tabs for L3M and L12M views
            l3m_tab, l12m_tab = st.tabs(["Last 3 Months (Oct-Dec)", "Last 12 Months (Full Year)"])

            with l3m_tab:
                st.markdown("### L3M Performance (Oct-Dec 2025)")

                # Display table - use styled dataframe with proper formatting
                display_l3m = df_top15.copy()

                # Rename columns for display
                display_l3m = display_l3m.rename(columns={
                    'customer': 'Customer',
                    'l3m_sales': 'Sales',
                    'l3m_gross_profit': 'Gross Profit',
                    'l3m_gp_margin': 'GP Margin %',
                    'l3m_pct_of_total': '% of Total Sales',
                    'rfm_segment': 'RFM Segment'
                })

                # Select columns to display
                display_cols = ['Customer', 'Sales', 'Gross Profit', 'GP Margin %', '% of Total Sales', 'RFM Segment']

                # Calculate company average GP margin for comparison (weighted average from top 15)
                top_15 = customer_data['top_15_customers']
                total_sales = sum(c['l12m_sales'] for c in top_15)
                weighted_gp = sum(c['l12m_sales'] * c['l12m_gp_margin'] for c in top_15)
                avg_gp_margin = weighted_gp / total_sales if total_sales else 53.9

                # Create formatted version for display using Pandas styling with color coding
                styled_l3m = display_l3m[display_cols].style.format({
                    'Sales': '${:,.0f}',
                    'Gross Profit': '${:,.0f}',
                    'GP Margin %': '{:.1f}%',
                    '% of Total Sales': '{:.1f}%'
                }).apply(lambda x: [color_gp_margin(v, avg_gp_margin) if x.name == 'GP Margin %' else '' for v in x], axis=0)

                st.dataframe(
                    styled_l3m,
                    use_container_width=True,
                    hide_index=True
                )

                st.caption(f"💡 GP Margin color coded: Green ≥ {avg_gp_margin:.1f}% (avg), Yellow ≥ {avg_gp_margin-5:.1f}%, Red < {avg_gp_margin-5:.1f}%")

                # L3M Chart
                fig_l3m = go.Figure()

                fig_l3m.add_trace(go.Bar(
                    name='Sales',
                    x=df_top15['customer'],
                    y=df_top15['l3m_sales'],
                    marker_color='#1f77b4'
                ))

                fig_l3m.update_layout(
                    title='L3M Sales by Top 15 Customers',
                    xaxis_title='Customer',
                    yaxis_title='Sales ($)',
                    xaxis_tickangle=-45,
                    height=500,
                    hovermode='x unified'
                )

                st.plotly_chart(fig_l3m, use_container_width=True)

                # Summary metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    top15_l3m_sales = df_top15['l3m_sales'].sum()
                    st.metric("Top 15 L3M Sales", f"${top15_l3m_sales:,.0f}")
                with col2:
                    top15_l3m_pct = (top15_l3m_sales / customer_data['metadata']['total_l3m_sales'] * 100)
                    st.metric("% of Total L3M Sales", f"{top15_l3m_pct:.1f}%")
                with col3:
                    avg_l3m_sales = df_top15['l3m_sales'].mean()
                    st.metric("Avg L3M Sales (Top 15)", f"${avg_l3m_sales:,.0f}")

            with l12m_tab:
                st.markdown("### L12M Performance (Jan-Dec 2025)")

                # Display table - use styled dataframe with proper formatting
                display_l12m = df_top15.copy()

                # Calculate sales trend (L3M vs L12M monthly run rate)
                display_l12m['Trend %'] = ((display_l12m['l3m_sales'] / 3) - (display_l12m['l12m_sales'] / 12)) / (display_l12m['l12m_sales'] / 12) * 100

                # Rename columns for display
                display_l12m = display_l12m.rename(columns={
                    'customer': 'Customer',
                    'l12m_sales': 'Sales',
                    'l12m_gross_profit': 'Gross Profit',
                    'l12m_gp_margin': 'GP Margin %',
                    'l12m_pct_of_total': '% of Total Sales',
                    'rfm_segment': 'RFM Segment'
                })

                # Select columns to display - now including Trend %
                display_cols = ['Customer', 'Sales', 'Gross Profit', 'GP Margin %', 'Trend %', 'RFM Segment']

                # Calculate company average GP margin for comparison (weighted average from top 15)
                top_15 = customer_data['top_15_customers']
                total_sales = sum(c['l12m_sales'] for c in top_15)
                weighted_gp = sum(c['l12m_sales'] * c['l12m_gp_margin'] for c in top_15)
                avg_gp_margin = weighted_gp / total_sales if total_sales else 53.9

                # Create formatted version for display using Pandas styling with color coding
                def apply_colors(row):
                    styles = [''] * len(row)
                    # Color GP Margin
                    if 'GP Margin %' in row.index:
                        idx = row.index.get_loc('GP Margin %')
                        styles[idx] = color_gp_margin(row['GP Margin %'], avg_gp_margin)
                    # Color Trend %
                    if 'Trend %' in row.index:
                        idx = row.index.get_loc('Trend %')
                        trend_val = row['Trend %']
                        if trend_val > 10:
                            styles[idx] = 'background-color: #d4edda'  # Green - growing
                        elif trend_val < -10:
                            styles[idx] = 'background-color: #f8d7da'  # Red - declining
                        else:
                            styles[idx] = 'background-color: #fff3cd'  # Yellow - stable
                    return styles

                styled_l12m = display_l12m[display_cols].style.format({
                    'Sales': '${:,.0f}',
                    'Gross Profit': '${:,.0f}',
                    'GP Margin %': '{:.1f}%',
                    'Trend %': '{:+.1f}%',  # Show + or - sign
                }).apply(apply_colors, axis=1)

                st.dataframe(
                    styled_l12m,
                    use_container_width=True,
                    hide_index=True
                )

                st.caption(f"💡 GP Margin: Green ≥ {avg_gp_margin:.1f}% (avg), Yellow ≥ {avg_gp_margin-5:.1f}%, Red < {avg_gp_margin-5:.1f}% | Trend %: L3M vs L12M monthly rate (Green >+10%, Yellow ±10%, Red <-10%)")

                # L12M Chart
                fig_l12m = go.Figure()

                fig_l12m.add_trace(go.Bar(
                    name='Sales',
                    x=df_top15['customer'],
                    y=df_top15['l12m_sales'],
                    marker_color='#2ca02c'
                ))

                fig_l12m.update_layout(
                    title='L12M Sales by Top 15 Customers',
                    xaxis_title='Customer',
                    yaxis_title='Sales ($)',
                    xaxis_tickangle=-45,
                    height=500,
                    hovermode='x unified'
                )

                st.plotly_chart(fig_l12m, use_container_width=True)

                # Summary metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    top15_l12m_sales = df_top15['l12m_sales'].sum()
                    st.metric("Top 15 L12M Sales", f"${top15_l12m_sales:,.0f}")
                with col2:
                    top15_l12m_pct = (top15_l12m_sales / customer_data['metadata']['total_l12m_sales'] * 100)
                    st.metric("% of Total L12M Sales", f"{top15_l12m_pct:.1f}%")
                with col3:
                    avg_l12m_sales = df_top15['l12m_sales'].mean()
                    st.metric("Avg L12M Sales (Top 15)", f"${avg_l12m_sales:,.0f}")

            st.divider()

            # ==================================================================
            # DETAILED RFM SEGMENTS
            # ==================================================================
            with st.expander("📋 View All RFM Segment Details"):
                df_rfm_segments = pd.DataFrame(rfm_segments)
                df_rfm_segments['Revenue'] = df_rfm_segments['total_revenue'].apply(lambda x: f'${x:,.0f}')
                df_rfm_segments['Avg Revenue/Customer'] = df_rfm_segments['avg_revenue_per_customer'].apply(lambda x: f'${x:,.0f}')
                df_rfm_segments['Avg Recency (days)'] = df_rfm_segments['avg_recency_days'].apply(lambda x: f'{x:.0f}')
                df_rfm_segments['Avg Frequency'] = df_rfm_segments['avg_frequency'].apply(lambda x: f'{x:.1f}')

                display_rfm = df_rfm_segments[['segment', 'customer_count', 'Revenue',
                                                'Avg Revenue/Customer', 'Avg Recency (days)', 'Avg Frequency']]
                display_rfm.columns = ['Segment', 'Customers', 'Total Revenue',
                                       'Avg Revenue/Customer', 'Avg Recency (days)', 'Avg Frequency']

                st.dataframe(display_rfm, use_container_width=True, hide_index=True)

            # Footer
            st.caption("Customer analysis based on RFM segmentation and sales data through December 2025")

        else:
            st.warning("Customer data not available. Please run the RFM analysis first.")
            st.markdown("""
            To generate customer analysis data:
            1. Navigate to: `Customer sales detail` folder
            2. Run: `python rfm_analysis.py`
            3. Run: `python customer_analysis_for_dashboard.py`
            4. Refresh this dashboard
            """)

    with tab5:
        # ==================================================================
        # ORDER BACKLOG ANALYSIS
        # ==================================================================
        st.header("📦 Order Backlog Analysis")

        if backlog_data:
            # Display metadata
            st.markdown(f"**Backlog as of:** {backlog_data['metadata']['analysis_date']}")
            st.caption(f"Data generated: {backlog_data['metadata']['generated_at']}")
            st.divider()

            # ==================================================================
            # SUMMARY METRICS
            # ==================================================================
            st.subheader("📊 Backlog Summary")

            summary = backlog_data['summary']

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Total Backlog Value",
                    f"${summary['total_backlog_value']:,.0f}"
                )

            with col2:
                st.metric(
                    "Total Orders",
                    f"{summary['total_orders']:,}"
                )

            with col3:
                st.metric(
                    "Average Order Value",
                    f"${summary['avg_order_value']:,.0f}"
                )

            with col4:
                # Color code average order age
                avg_age = summary['avg_age_days']

                if avg_age <= BACKLOG_THRESHOLDS['avg_age']['green']:
                    age_color = "🟢"
                elif avg_age <= BACKLOG_THRESHOLDS['avg_age']['yellow']:
                    age_color = "🟡"
                else:
                    age_color = "🔴"

                st.metric(
                    "Average Order Age",
                    f"{age_color} {avg_age:.0f} days"
                )

            # Show percentage of orders > 90 days
            age_dist = backlog_data['age_distribution']
            orders_90plus = age_dist.get('91-180 days', {}).get('count', 0) + age_dist.get('180+ days', {}).get('count', 0)
            total_orders = summary['total_orders']
            pct_old_orders = (orders_90plus / total_orders * 100) if total_orders else 0

            if pct_old_orders <= BACKLOG_THRESHOLDS['old_orders_pct']['green']:
                old_color = "🟢"
            elif pct_old_orders <= BACKLOG_THRESHOLDS['old_orders_pct']['yellow']:
                old_color = "🟡"
            else:
                old_color = "🔴"

            st.caption(f"{old_color} **{pct_old_orders:.1f}%** of orders are >90 days old (Target: ≤{BACKLOG_THRESHOLDS['old_orders_pct']['yellow']}%)")

            st.divider()

            # ==================================================================
            # AGE DISTRIBUTION
            # ==================================================================
            st.subheader("⏳ Backlog Age Distribution")

            age_dist = backlog_data['age_distribution']

            # Create two columns for charts
            col1, col2 = st.columns(2)

            with col1:
                # Age by order count
                age_count_df = pd.DataFrame([
                    {'Age Bucket': bucket, 'Order Count': count}
                    for bucket, count in age_dist['order_count'].items()
                ])

                fig_age_count = px.bar(
                    age_count_df,
                    x='Age Bucket',
                    y='Order Count',
                    title='Orders by Age',
                    color='Order Count',
                    color_continuous_scale='RdYlGn_r'
                )
                fig_age_count.update_layout(height=400)
                st.plotly_chart(fig_age_count, use_container_width=True)

            with col2:
                # Age by value
                age_value_df = pd.DataFrame([
                    {'Age Bucket': bucket, 'Total Value': value}
                    for bucket, value in age_dist['order_value'].items()
                ])

                fig_age_value = px.bar(
                    age_value_df,
                    x='Age Bucket',
                    y='Total Value',
                    title='Backlog Value by Age',
                    color='Total Value',
                    color_continuous_scale='RdYlGn_r'
                )
                fig_age_value.update_layout(height=400, yaxis_title='Value ($)')
                st.plotly_chart(fig_age_value, use_container_width=True)

            st.divider()

            # ==================================================================
            # EXPECTED SHIP DATE DISTRIBUTION
            # ==================================================================
            if backlog_data['ship_date_distribution']['order_count']:
                st.subheader("📅 Expected Ship Date Distribution")

                ship_dist = backlog_data['ship_date_distribution']

                col1, col2 = st.columns(2)

                with col1:
                    # Ship date by order count
                    ship_count_df = pd.DataFrame([
                        {'Ship Window': bucket, 'Order Count': count}
                        for bucket, count in ship_dist['order_count'].items()
                    ])

                    fig_ship_count = px.bar(
                        ship_count_df,
                        x='Ship Window',
                        y='Order Count',
                        title='Orders by Expected Ship Date',
                        color='Order Count',
                        color_continuous_scale='Blues'
                    )
                    fig_ship_count.update_layout(height=400)
                    st.plotly_chart(fig_ship_count, use_container_width=True)

                with col2:
                    # Ship date by value
                    ship_value_df = pd.DataFrame([
                        {'Ship Window': bucket, 'Total Value': value}
                        for bucket, value in ship_dist['order_value'].items()
                    ])

                    fig_ship_value = px.bar(
                        ship_value_df,
                        x='Ship Window',
                        y='Total Value',
                        title='Backlog Value by Expected Ship Date',
                        color='Total Value',
                        color_continuous_scale='Blues'
                    )
                    fig_ship_value.update_layout(height=400, yaxis_title='Value ($)')
                    st.plotly_chart(fig_ship_value, use_container_width=True)

                st.divider()

            # ==================================================================
            # TOP CUSTOMERS
            # ==================================================================
            st.subheader("🏆 Top 10 Customers by Backlog Value")

            top_customers = backlog_data['top_customers']
            df_top_customers = pd.DataFrame(top_customers)

            # Format for display
            display_customers = df_top_customers.copy()
            display_customers = display_customers.rename(columns={
                'customer': 'Customer',
                'order_count': 'Order Count',
                'total_value': 'Total Value'
            })

            # Create formatted version using Pandas styling
            styled_customers = display_customers.style.format({
                'Total Value': '${:,.0f}'
            })

            st.dataframe(
                styled_customers,
                use_container_width=True,
                hide_index=True
            )

            # Chart
            fig_customers = go.Figure()

            fig_customers.add_trace(go.Bar(
                name='Backlog Value',
                x=df_top_customers['customer'],
                y=df_top_customers['total_value'],
                marker_color='#1f77b4',
                text=df_top_customers['total_value'],
                texttemplate='$%{text:,.0f}',
                textposition='outside'
            ))

            fig_customers.update_layout(
                title='Top 10 Customers - Backlog Value',
                xaxis_title='Customer',
                yaxis_title='Total Value ($)',
                xaxis_tickangle=-45,
                height=500,
                hovermode='x unified'
            )

            st.plotly_chart(fig_customers, use_container_width=True)

            st.divider()

            # ==================================================================
            # BY SALES REP
            # ==================================================================
            st.subheader("👤 Backlog by Sales Rep")

            by_rep = backlog_data['by_sales_rep']
            df_by_rep = pd.DataFrame(by_rep)

            col1, col2 = st.columns(2)

            with col1:
                # Format for display
                display_rep = df_by_rep.copy()
                display_rep = display_rep.rename(columns={
                    'sales_rep': 'Sales Rep',
                    'order_count': 'Order Count',
                    'total_value': 'Total Value'
                })

                # Create formatted version using Pandas styling
                styled_rep = display_rep.style.format({
                    'Total Value': '${:,.0f}'
                })

                st.dataframe(
                    styled_rep,
                    use_container_width=True,
                    hide_index=True
                )

            with col2:
                # Pie chart
                fig_rep_pie = px.pie(
                    df_by_rep,
                    values='total_value',
                    names='sales_rep',
                    title='Backlog Value by Sales Rep',
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_rep_pie.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_rep_pie, use_container_width=True)

            st.divider()

            # ==================================================================
            # BY REGION
            # ==================================================================
            st.subheader("🌎 Backlog by Region")

            by_region = backlog_data['by_region']
            df_by_region = pd.DataFrame(by_region)

            col1, col2 = st.columns(2)

            with col1:
                # Format for display
                display_region = df_by_region.copy()
                display_region = display_region.rename(columns={
                    'region': 'Region',
                    'order_count': 'Order Count',
                    'total_value': 'Total Value'
                })

                # Create formatted version using Pandas styling
                styled_region = display_region.style.format({
                    'Total Value': '${:,.0f}'
                })

                st.dataframe(
                    styled_region,
                    use_container_width=True,
                    hide_index=True
                )

            with col2:
                # Pie chart
                fig_region_pie = px.pie(
                    df_by_region,
                    values='total_value',
                    names='region',
                    title='Backlog Value by Region',
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_region_pie.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_region_pie, use_container_width=True)

            # Footer
            st.caption(f"Backlog analysis as of {backlog_data['metadata']['analysis_date']}")

        else:
            st.warning("Backlog data not available. Please run the backlog analysis first.")
            st.markdown("""
            To generate backlog analysis data:
            1. Navigate to: `Backlog` folder
            2. Run: `python backlog_analysis.py`
            3. Refresh this dashboard
            """)

    with tab6:
        st.header("📚 Historical Dashboards")
        st.markdown("""
        View and compare dashboards from previous months. Select a period below to load that month's complete dashboard data.
        """)

        # Get available periods
        available_periods = get_available_periods()

        if len(available_periods) > 0:
            st.subheader("Available Periods")

            # Create a grid of period cards
            cols = st.columns(4)
            for idx, period in enumerate(available_periods):
                col_idx = idx % 4
                with cols[col_idx]:
                    # Parse period to display format
                    year = 2000 + int(period.split('.')[0])
                    month = int(period.split('.')[1])
                    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                    display_name = f"{month_names[month-1]} {year}"

                    # Highlight current period
                    if period == PERIOD:
                        st.info(f"**{display_name}** (Current)")
                    else:
                        st.success(f"**{display_name}**")

                    # Button to view this period
                    if st.button(f"View {display_name}", key=f"view_{period}"):
                        st.session_state['selected_period'] = period

            st.divider()

            # Load and display selected period
            if 'selected_period' in st.session_state:
                selected = st.session_state['selected_period']

                # Parse selected period
                year = 2000 + int(selected.split('.')[0])
                month = int(selected.split('.')[1])
                month_names = ["January", "February", "March", "April", "May", "June",
                               "July", "August", "September", "October", "November", "December"]
                display_month = month_names[month-1]

                st.subheader(f"Dashboard for {display_month} {year}")

                # Load historical data
                hist_data = load_data(selected)
                hist_customer = load_customer_data(selected)
                hist_backlog = load_backlog_data(selected)

                if hist_data:
                    # Show key metrics summary
                    st.markdown("### Key Metrics Summary")

                    cm = hist_data['current_month']
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("Revenue", f"${cm['revenue']:,.0f}")
                        st.metric("Gross Profit", f"${cm['gross_profit']:,.0f}")

                    with col2:
                        st.metric("EBITDA", f"${cm['ebitda']:,.0f}")
                        st.metric("Net Income", f"${cm['net_income']:,.0f}")

                    with col3:
                        st.metric("Gross Margin %", f"{cm['gross_margin_pct']:.1f}%")
                        st.metric("EBITDA Margin %", f"{cm['ebitda_margin_pct']:.1f}%")

                    with col4:
                        st.metric("NWC", f"${cm['nwc']:,.0f}")
                        st.metric("Operating CF", f"${cm['operating_cash_flow']:,.0f}")

                    st.divider()

                    # Revenue trend for this period
                    st.markdown("### Revenue Trend")
                    months = hist_data['monthly_data']['months'][:month]
                    revenue = hist_data['monthly_data']['revenue'][:month]

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=months,
                        y=revenue,
                        mode='lines+markers',
                        name='Revenue',
                        line=dict(color='#1f77b4', width=3),
                        marker=dict(size=8)
                    ))
                    fig.update_layout(
                        title=f"Monthly Revenue - {year}",
                        xaxis_title="Month",
                        yaxis_title="Revenue ($)",
                        height=400,
                        hovermode='x unified'
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Customer summary if available
                    if hist_customer:
                        st.divider()
                        st.markdown("### Top 10 Customers (L12M)")

                        customers = hist_customer['top_customers'][:10]
                        if customers:
                            df_top = pd.DataFrame([
                                {
                                    'Customer': c['customer'],
                                    'L12M Sales': c['l12m_sales'],
                                    'L12M GP': c['l12m_gross_profit'],
                                    'GP Margin %': c['l12m_gp_margin'],
                                    'Segment': c['rfm_segment']
                                }
                                for c in customers
                            ])

                            styled_df = df_top.style.format({
                                'L12M Sales': '${:,.0f}',
                                'L12M GP': '${:,.0f}',
                                'GP Margin %': '{:.1f}%'
                            })

                            st.dataframe(styled_df, use_container_width=True, hide_index=True)

                    # Backlog summary if available
                    if hist_backlog:
                        st.divider()
                        st.markdown("### Backlog Summary")

                        summary = hist_backlog['summary']
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.metric("Total Backlog", f"${summary['total_backlog_value']:,.0f}")
                        with col2:
                            st.metric("Total Orders", f"{summary['total_orders']:,}")
                        with col3:
                            st.metric("Avg Order Value", f"${summary['avg_order_value']:,.0f}")

                    st.divider()
                    st.caption(f"Data generated: {hist_data['metadata']['generated_at']}")

                else:
                    st.error(f"Unable to load data for period {selected}")

            else:
                st.info("Select a period above to view historical dashboard data")

        else:
            st.warning("No historical periods available yet. Historical data will appear here as you generate dashboards for each month.")
            st.markdown("""
            **To create historical data:**
            1. Copy input files to `inputs/YY.MM/` folder (e.g., `inputs/26.01/` for January 2026)
            2. Update `PERIOD` in `generate_dashboard.py` to the new period (e.g., "26.01")
            3. Run: `python generate_dashboard.py`
            4. The new period will appear in this historicals tab
            """)

else:
    st.error("Unable to load dashboard data.")
    st.markdown("""
    ### 📋 Setup Instructions

    This dashboard requires data files to be uploaded. If you're seeing this message:

    **For Local Development:**
    1. Ensure you have run `python generate_dashboard.py`
    2. Check that `generated/{PERIOD}/` folder exists with JSON files

    **For Streamlit Cloud:**
    1. Upload the `generated/` folder to your GitHub repository
    2. Make sure the folder structure is: `generated/YY.MM/*.json`
    3. Redeploy the app

    **Note:** Sensitive data files (`inputs/` folder) should NOT be uploaded to GitHub.
    Generate the dashboard data locally, then upload only the `generated/` folder.
    """)
