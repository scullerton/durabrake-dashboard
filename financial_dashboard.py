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

def fmt_money(value, placeholder="—"):
    """Format a dollar value, gracefully handling None (e.g., draft months
    where Neil has filled in the P&L but not yet the Balance Sheet)."""
    if value is None:
        return placeholder
    return f"${value:,.0f}"


def fmt_pct(value, placeholder="—", decimals=1):
    """Format a percentage; returns placeholder when None."""
    if value is None:
        return placeholder
    return f"{value:.{decimals}f}%"


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
# DATA LOADING FUNCTIONS
# ============================================================================

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

# ============================================================================
# AUTO-DETECT CURRENT PERIOD - always displays most recent month
# ============================================================================
_available = get_available_periods()
PERIOD = _available[0] if _available else "26.01"

data = load_data(PERIOD)
customer_data = load_customer_data(PERIOD)
backlog_data = load_backlog_data(PERIOD)

MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]

# Load prior year data for LTM (Last Twelve Months) views
prior_year_data = None
current_year = data['metadata']['reporting_year'] if data else 2026
current_month_num = MONTH_NAMES.index(data['metadata']['reporting_month']) + 1 if data else 1
if data and current_month_num < 12:
    prior_period = f"{(current_year - 1) % 100:02d}.12"
    prior_year_data = load_data(prior_period)

# Build LTM (Last 12 Months) series combining prior year + current year
ltm_series = []
ltm_products = {}
if data:
    if prior_year_data:
        # Take months after current month from prior year (e.g., Feb-Dec 2025 for Jan 2026)
        prior_months = prior_year_data.get('monthly_series', [])
        for m in prior_months:
            if m['month_num'] > current_month_num:
                entry = m.copy()
                entry['label'] = f"{m['month']} {current_year - 1}"
                ltm_series.append(entry)
        # Append same-numbered month from prior year if needed to fill 12 months
        if current_month_num == prior_months[current_month_num - 1]['month_num']:
            pass  # current year has this month

    # Add current year months (up to current month)
    current_months = data.get('monthly_series', [])
    for m in current_months:
        if m['month_num'] <= current_month_num and m.get('revenue') is not None:
            entry = m.copy()
            entry['label'] = f"{m['month']} {current_year}"
            ltm_series.append(entry)

    # Build LTM product series
    if prior_year_data:
        prior_products = prior_year_data.get('products', {})
        current_products = data.get('products', {})
        for prod_key in current_products:
            ltm_prod_series = []
            if prod_key in prior_products:
                for m in prior_products[prod_key].get('monthly_series', []):
                    if m['month_num'] > current_month_num:
                        entry = m.copy()
                        entry['label'] = f"{m['month']} {current_year - 1}"
                        ltm_prod_series.append(entry)
            for m in current_products[prod_key].get('monthly_series', []):
                if m['month_num'] <= current_month_num and m.get('sales') is not None:
                    entry = m.copy()
                    entry['label'] = f"{m['month']} {current_year}"
                    ltm_prod_series.append(entry)
            ltm_products[prod_key] = ltm_prod_series

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
            st.metric("NWC", fmt_money(cm['nwc']))
            st.metric("Operating CF", fmt_money(cm['operating_cash_flow']))

        st.divider()

        # ==================================================================
        # CRITICAL NOTES & ACTION ITEMS
        # ==================================================================
        st.header("⚠️ Critical Notes & Action Items")

        # Read notes from the main dashboard data (injected by generate_notes.py)
        _notes_data = data.get('notes', {})
        _critical_notes = _notes_data.get("critical_notes", "")
        _action_items = _notes_data.get("action_items", "")

        if _critical_notes or _action_items:
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("📝 Critical Notes")
                st.markdown(_critical_notes)

            with col2:
                st.subheader("✅ Action Items")
                st.markdown(_action_items)
        else:
            st.info("No critical notes available. Run `generate_dashboard.py` to auto-generate insights from this period's data.")

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
        # MONTHLY TRENDS (LTM - Last Twelve Months)
        # ==================================================================
        st.header("📊 Monthly Trends (LTM)")

        # Use LTM series if available, otherwise fall back to current year data
        trend_source = ltm_series if ltm_series else data['monthly_series']
        df_trend = pd.DataFrame(trend_source)
        trend_x = df_trend['label'] if 'label' in df_trend.columns else df_trend['month']

        # Revenue & EBITDA chart
        fig = go.Figure()

        fig.add_trace(go.Bar(
            name='Revenue',
            x=trend_x,
            y=df_trend['revenue'],
            yaxis='y',
            marker_color='#1f77b4'
        ))

        fig.add_trace(go.Scatter(
            name='EBITDA',
            x=trend_x,
            y=df_trend['ebitda'],
            yaxis='y2',
            marker_color='#ff7f0e',
            line=dict(width=3)
        ))

        fig.update_layout(
            title='Revenue & EBITDA Trend (Last 12 Months)',
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
            x=trend_x,
            y=df_trend['gross_margin_pct'],
            marker_color='#2ca02c',
            line=dict(width=2)
        ))

        fig2.add_trace(go.Scatter(
            name='EBITDA Margin %',
            x=trend_x,
            y=df_trend['ebitda_margin_pct'],
            marker_color='#d62728',
            line=dict(width=2)
        ))

        fig2.update_layout(
            title='Margin Trends (Last 12 Months)',
            yaxis=dict(title='Margin %'),
            hovermode='x unified',
            height=400
        )

        st.plotly_chart(fig2, use_container_width=True)

        st.divider()

        # ==================================================================
        # ROLLING L3M VARIANCE (LTM)
        # ==================================================================
        st.header("🔄 Rolling 3-Month Variance (LTM)")
        st.markdown("Each month compared to its prior 3-month average")

        # Build rolling L3M from LTM series if available
        rolling_data = []
        if ltm_series and len(ltm_series) >= 4:
            for i in range(3, len(ltm_series)):
                m = ltm_series[i]
                prior_3 = ltm_series[i-3:i]
                avg_rev = sum(p.get('revenue', 0) or 0 for p in prior_3) / 3
                curr_rev = m.get('revenue', 0) or 0
                avg_gp = sum(p.get('gross_profit', 0) or 0 for p in prior_3) / 3
                curr_gp = m.get('gross_profit', 0) or 0
                rev_var = ((curr_rev - avg_rev) / avg_rev * 100) if avg_rev else 0
                gp_var = ((curr_gp - avg_gp) / avg_gp * 100) if avg_gp else 0
                rolling_data.append({
                    'month': m.get('label', m.get('month', '')),
                    'revenue_vs_l3m_pct': rev_var,
                    'gp_vs_l3m_pct': gp_var
                })
        elif data.get('rolling_l3m'):
            rolling_data = data['rolling_l3m']

        if rolling_data:
            df_rolling = pd.DataFrame(rolling_data)

            fig3 = go.Figure()

            fig3.add_trace(go.Bar(
                name='Revenue vs L3M %',
                x=df_rolling['month'],
                y=df_rolling['revenue_vs_l3m_pct'],
                marker_color=['#ef5350' if x < 0 else '#66bb6a' for x in df_rolling['revenue_vs_l3m_pct']],
                opacity=0.7
            ))

            if 'gp_vs_l3m_pct' in df_rolling.columns:
                fig3.add_trace(go.Scatter(
                    name='Gross Profit vs L3M %',
                    x=df_rolling['month'],
                    y=df_rolling['gp_vs_l3m_pct'],
                    mode='lines+markers',
                    marker_color='#ff9800',
                    line=dict(width=3)
                ))

            fig3.update_layout(
                title='Revenue & Gross Profit Variance vs Prior 3-Month Average (LTM)',
                yaxis=dict(title='Variance %'),
                hovermode='x unified',
                height=350
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
            st.metric("Total Revenue", fmt_money(ytd['total_revenue']))
            st.metric("Avg Gross Margin %", fmt_pct(ytd['avg_gross_margin_pct']))

        with col2:
            st.metric("Total Gross Profit", fmt_money(ytd['total_gross_profit']))
            st.metric("Avg EBITDA Margin %", fmt_pct(ytd['avg_ebitda_margin_pct']))

        with col3:
            st.metric("Total EBITDA", fmt_money(ytd['total_ebitda']))
            st.metric("Total Net Income", fmt_money(ytd['total_net_income']))

        with col4:
            st.metric("Avg NWC", fmt_money(ytd['avg_nwc']))
            st.metric("Total Operating CF", fmt_money(ytd['total_operating_cf']))

        st.divider()

        # ==================================================================
        # PRIOR QUARTER SUMMARY
        # ==================================================================
        # Use prior year Q4 data when current year Q4 is empty
        q4 = data['q4_summary']
        q4_has_data = q4['total_revenue'] != 0 or q4['total_gross_profit'] != 0

        if not q4_has_data and prior_year_data:
            q4 = prior_year_data.get('q4_summary', q4)
            q4_label = f"Q4 {current_year - 1}"
        else:
            q4_label = f"Q4 {current_year}"

        st.header(f"{q4_label} Summary")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Q4 Revenue", f"${q4['total_revenue']:,.0f}")

        with col2:
            st.metric("Q4 Gross Profit", f"${q4['total_gross_profit']:,.0f}")
            if q4.get('avg_gross_margin_pct') is not None:
                st.caption(f"Avg GP%: {q4['avg_gross_margin_pct']:.1f}%")

        with col3:
            st.metric("Q4 EBITDA", f"${q4['total_ebitda']:,.0f}")
            if q4.get('avg_ebitda_margin_pct') is not None:
                st.caption(f"Avg EBITDA%: {q4['avg_ebitda_margin_pct']:.1f}%")

        with col4:
            st.metric("Q4 Net Income", f"${q4['total_net_income']:,.0f}")

        st.divider()

        # ==================================================================
        # DATA TABLE
        # ==================================================================
        with st.expander("📋 View Detailed Monthly Data"):
            st.dataframe(df_trend, use_container_width=True)

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

            # Product trend charts (LTM)
            st.header("📊 Product Trends (LTM)")

            # Sales trend by product - use LTM data if available
            fig_sales = go.Figure()
            for product_key in product_keys:
                if product_key in products:
                    prod = products[product_key]
                    if product_key in ltm_products and ltm_products[product_key]:
                        df_prod = pd.DataFrame(ltm_products[product_key])
                        prod_x = df_prod['label'] if 'label' in df_prod.columns else df_prod['month']
                    else:
                        df_prod = pd.DataFrame(prod['monthly_series'])
                        prod_x = df_prod['month']
                    fig_sales.add_trace(go.Scatter(
                        name=prod['name'],
                        x=prod_x,
                        y=df_prod['sales'],
                        mode='lines+markers'
                    ))

            fig_sales.update_layout(
                title='Monthly Sales by Product (Last 12 Months)',
                yaxis=dict(title='Sales ($)'),
                hovermode='x unified',
                height=400
            )
            st.plotly_chart(fig_sales, use_container_width=True)

            # Gross margin % trend by product - use LTM data if available
            fig_gm = go.Figure()
            for product_key in product_keys:
                if product_key in products:
                    prod = products[product_key]
                    if product_key in ltm_products and ltm_products[product_key]:
                        df_prod = pd.DataFrame(ltm_products[product_key])
                        prod_x = df_prod['label'] if 'label' in df_prod.columns else df_prod['month']
                    else:
                        df_prod = pd.DataFrame(prod['monthly_series'])
                        prod_x = df_prod['month']
                    fig_gm.add_trace(go.Scatter(
                        name=prod['name'],
                        x=prod_x,
                        y=df_prod['gross_margin_pct'],
                        mode='lines+markers'
                    ))

            fig_gm.update_layout(
                title='Gross Margin % by Product (Last 12 Months)',
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
            st.metric("Accounts Receivable", fmt_money(cm['accounts_receivable']))

        with col2:
            st.metric("Inventory", fmt_money(cm['inventory']))

        with col3:
            st.metric("Accounts Payable", fmt_money(cm['accounts_payable']))

        with col4:
            st.metric("Net Working Capital", fmt_money(cm['nwc']))

        st.divider()

        # NWC as % of Revenue
        st.subheader("NWC Ratios")

        # Balance-sheet-derived ratios need all four BS fields. When any are
        # missing (draft months), show an info banner and use 0 so the existing
        # display logic doesn't crash. Ratios auto-populate when Final lands.
        _bs_missing = any(cm.get(k) is None for k in
                          ['nwc', 'accounts_receivable', 'inventory', 'accounts_payable'])
        if _bs_missing:
            st.info("ℹ️ Balance Sheet not yet available for this period — "
                    "NWC ratios below will populate once the Final reporting package is in place.")

        _nwc = cm.get('nwc') or 0
        _ar = cm.get('accounts_receivable') or 0
        _inv = cm.get('inventory') or 0
        _ap = cm.get('accounts_payable') or 0

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            # Use LTM (Last Twelve Months) revenue for more meaningful ratio
            ltm_total_revenue = sum(m.get('revenue', 0) or 0 for m in ltm_series) if ltm_series else data['ytd_summary']['total_revenue']
            nwc_pct_revenue = (_nwc / ltm_total_revenue * 100) if ltm_total_revenue else 0

            # Determine color for NWC %
            if nwc_pct_revenue <= WC_THRESHOLDS['nwc_pct']['green']:
                nwc_color = "🟢"
            elif nwc_pct_revenue <= WC_THRESHOLDS['nwc_pct']['yellow']:
                nwc_color = "🟡"
            else:
                nwc_color = "🔴"

            st.metric("NWC as % of Revenue", f"{nwc_color} {nwc_pct_revenue:.1f}%")
            st.caption("Based on LTM revenue")

        with col2:
            # DSO = (A/R / Revenue) * 365
            ar_days = (_ar / (cm['revenue'] / 30)) if cm['revenue'] else 0

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
            inv_days = (_inv / (cogs_monthly / 30)) if cogs_monthly else 0

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
            ap_days = (_ap / (cogs_monthly / 30)) if cogs_monthly else 0

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

        # NWC Trends (LTM)
        st.header("📊 NWC Trends (LTM)")

        # Use LTM series for NWC trends if available
        nwc_source = ltm_series if ltm_series else data['monthly_series']
        df_nwc_trend = pd.DataFrame(nwc_source)
        nwc_x = df_nwc_trend['label'] if 'label' in df_nwc_trend.columns else df_nwc_trend['month']

        # NWC components chart
        fig_nwc = go.Figure()

        if 'accounts_receivable' in df_nwc_trend.columns:
            fig_nwc.add_trace(go.Scatter(
                name='Accounts Receivable',
                x=nwc_x,
                y=df_nwc_trend['accounts_receivable'],
                mode='lines+markers',
                marker_color='#1f77b4'
            ))

        if 'inventory' in df_nwc_trend.columns:
            fig_nwc.add_trace(go.Scatter(
                name='Inventory',
                x=nwc_x,
                y=df_nwc_trend['inventory'],
                mode='lines+markers',
                marker_color='#ff7f0e'
            ))

        if 'accounts_payable' in df_nwc_trend.columns:
            fig_nwc.add_trace(go.Scatter(
                name='Accounts Payable',
                x=nwc_x,
                y=df_nwc_trend['accounts_payable'],
                mode='lines+markers',
                marker_color='#2ca02c'
            ))

        fig_nwc.update_layout(
            title='NWC Components Trend (Last 12 Months)',
            yaxis=dict(title='Amount ($)'),
            hovermode='x unified',
            height=400
        )

        st.plotly_chart(fig_nwc, use_container_width=True)

        # Net Working Capital trend
        if 'nwc' in df_nwc_trend.columns:
            fig_nwc_total = go.Figure()

            fig_nwc_total.add_trace(go.Bar(
                name='Net Working Capital',
                x=nwc_x,
                y=df_nwc_trend['nwc'],
                marker_color='#9467bd'
            ))

            fig_nwc_total.update_layout(
                title='Net Working Capital Trend (Last 12 Months)',
                yaxis=dict(title='NWC ($)'),
                hovermode='x unified',
                height=400
            )

            st.plotly_chart(fig_nwc_total, use_container_width=True)

        st.divider()

        # Data table
        with st.expander("📋 View Detailed NWC Data"):
            nwc_cols = [c for c in ['month', 'label', 'accounts_receivable', 'inventory', 'accounts_payable', 'nwc'] if c in df_nwc_trend.columns]
            nwc_detail = df_nwc_trend[nwc_cols].copy()
            # Use label column if available, otherwise month
            if 'label' in nwc_detail.columns:
                nwc_detail = nwc_detail.drop(columns=['month'], errors='ignore')
                nwc_detail = nwc_detail.rename(columns={'label': 'Month'})
            else:
                nwc_detail = nwc_detail.rename(columns={'month': 'Month'})
            nwc_detail = nwc_detail.rename(columns={
                'accounts_receivable': 'A/R', 'inventory': 'Inventory',
                'accounts_payable': 'A/P', 'nwc': 'NWC'
            })
            st.dataframe(nwc_detail, use_container_width=True)

        # Footer
        st.caption(f"Source: {data['metadata']['source_file']}")

    with tab4:
        # ==================================================================
        # CUSTOMER SCORECARD
        # ==================================================================
        st.header("👥 Customer Scorecard")

        if customer_data:
            _l3m_period = customer_data['metadata'].get('analysis_period_l3m', 'L3M')
            _l12m_period = customer_data['metadata'].get('analysis_period_l12m', 'L12M')

            # ==================================================================
            # SCORECARD KPI HEADER
            # ==================================================================
            scorecard = customer_data.get('scorecard_kpis', {})
            if scorecard:
                col1, col2, col3, col4, col5 = st.columns(5)

                # L3M orders vs L12M quarterly average
                l12m_quarterly_avg = scorecard.get('l12m_orders', 0) / 4
                order_delta = scorecard.get('l3m_orders', 0) - l12m_quarterly_avg if l12m_quarterly_avg > 0 else None
                with col1:
                    st.metric(
                        f"Orders ({_l3m_period})",
                        f"{scorecard.get('l3m_orders', 0):,}",
                        f"{order_delta:+,.0f} vs L12M avg" if order_delta is not None else None,
                    )

                # Active customers + new customers
                with col2:
                    new_ct = scorecard.get('new_customers_count', 0)
                    st.metric(
                        f"Active Customers ({_l3m_period})",
                        f"{scorecard.get('l3m_unique_customers', 0):,}",
                        f"{new_ct} new" if new_ct > 0 else None,
                    )

                # Avg order size vs L12M avg
                l3m_avg = scorecard.get('l3m_avg_order_size', 0)
                l12m_avg = scorecard.get('l12m_avg_order_size', 0)
                avg_delta = l3m_avg - l12m_avg if l12m_avg > 0 else None
                with col3:
                    st.metric(
                        f"Avg Order Size ({_l3m_period})",
                        f"${l3m_avg:,.0f}",
                        f"${avg_delta:+,.0f} vs L12M" if avg_delta is not None else None,
                    )

                # Customers overdue
                overdue_ct = len([o for o in customer_data.get('overdue_customers', []) if not o.get('has_backlog_order')])
                with col4:
                    st.metric("Customers Overdue", f"{overdue_ct}")

                # Cross-sell gaps
                cross_sell_ct = len(customer_data.get('cross_sell_opportunities', []))
                with col5:
                    st.metric("Cross-Sell Gaps", f"{cross_sell_ct}")

            st.caption(f"L3M: {_l3m_period} | L12M: {_l12m_period} | Generated: {customer_data['metadata']['generated_at'][:10]}")
            st.divider()

            # ==================================================================
            # CUSTOMERS NEEDING ATTENTION
            # ==================================================================
            attention_list = customer_data.get('customers_needing_attention', [])
            if attention_list:
                st.subheader("Customers Needing Attention")
                st.markdown("**Order Overdue** | **At Risk** (RFM) | **Declining** (>25% down) | **Low Margin** (<15% GP)")

                attention_rows = []
                for a in attention_list:
                    reason_tags = ', '.join(a['reasons'])
                    rep = a.get('sales_rep', '')
                    action = a.get('suggested_action', '')
                    attention_rows.append({
                        'Customer': a['customer'].split('/')[0].strip(),
                        'Flags': reason_tags,
                        'Action': action,
                        'Rep': rep if rep else '—',
                        'L3M Sales': a['l3m_sales'],
                        'L12M Sales': a['l12m_sales'],
                        'Trend %': a['trend_pct'],
                        'GP %': a['gp_margin'],
                        'Days Since': a['recency_days'],
                    })

                df_attention = pd.DataFrame(attention_rows)

                def color_attention_flags(val):
                    if 'Order Overdue' in str(val) and 'At Risk' in str(val):
                        return 'background-color: #f8d7da; font-weight: bold'
                    elif 'Order Overdue' in str(val) or 'At Risk' in str(val):
                        return 'background-color: #fff3cd'
                    elif 'Declining' in str(val):
                        return 'background-color: #fff3cd'
                    return ''

                styled_attention = df_attention.style.format({
                    'L3M Sales': '${:,.0f}',
                    'L12M Sales': '${:,.0f}',
                    'Trend %': '{:+.0f}%',
                    'GP %': '{:.1f}%',
                    'Days Since': '{:.0f}',
                }).map(color_attention_flags, subset=['Flags'])

                st.dataframe(styled_attention, use_container_width=True, hide_index=True)

            st.divider()

            # ==================================================================
            # OVERDUE CUSTOMERS
            # ==================================================================
            overdue_list = customer_data.get('overdue_customers', [])
            if overdue_list:
                st.subheader("Overdue to Order")
                st.markdown("Customers past their expected purchase interval (L12M). Minimum 3 prior orders required.")

                truly_overdue = [o for o in overdue_list if not o['has_backlog_order']]
                backlog_covered = [o for o in overdue_list if o['has_backlog_order']]

                if truly_overdue:
                    overdue_rows = []
                    for o in truly_overdue:
                        overdue_rows.append({
                            'Customer': o['customer'].split('/')[0].strip(),
                            'Last Order': o['last_purchase_date'],
                            'Avg Interval': o['expected_interval_days'],
                            'Days Since': o['recency_days'],
                            'Days Overdue': o['days_overdue'],
                            'L12M Sales': o['l12m_sales'],
                            'Segment': o['segment'],
                        })

                    df_overdue = pd.DataFrame(overdue_rows)
                    styled_overdue = df_overdue.style.format({
                        'Avg Interval': '{:.0f}',
                        'Days Since': '{:.0f}',
                        'Days Overdue': '{:.0f}',
                        'L12M Sales': '${:,.0f}',
                    })
                    st.dataframe(styled_overdue, use_container_width=True, hide_index=True)

                if backlog_covered:
                    with st.expander(f"{len(backlog_covered)} Overdue Customers Covered by Active Backlog"):
                        covered_rows = []
                        for o in backlog_covered:
                            covered_rows.append({
                                'Customer': o['customer'].split('/')[0].strip(),
                                'Last Order': o['last_purchase_date'],
                                'Days Overdue': o['days_overdue'],
                                'L12M Sales': o['l12m_sales'],
                                'Backlog Value': o['backlog_value'],
                            })
                        df_covered = pd.DataFrame(covered_rows)
                        styled_covered = df_covered.style.format({
                            'Days Overdue': '{:.0f}',
                            'L12M Sales': '${:,.0f}',
                            'Backlog Value': '${:,.0f}',
                        })
                        st.dataframe(styled_covered, use_container_width=True, hide_index=True)

            st.divider()

            # ==================================================================
            # CROSS-SELL OPPORTUNITIES
            # ==================================================================
            cross_sell = customer_data.get('cross_sell_opportunities', [])
            category_heatmap = customer_data.get('category_heatmap', [])
            if cross_sell:
                st.subheader("Cross-Sell Opportunities")
                st.markdown("Customers buying fewer than 4 categories: **Drums** | **Rotors** | **ADB** | **Hubs**")

                cross_rows = []
                for cs in cross_sell[:20]:
                    cross_rows.append({
                        'Customer': cs['customer'].split('/')[0].strip(),
                        'Buying': ', '.join(cs['categories_purchased']),
                        'Missing': ', '.join(cs['missing_categories']),
                        'L3M Sales': cs['l3m_sales'],
                        'Coverage': f"{cs['category_count']}/4",
                    })

                df_cross = pd.DataFrame(cross_rows)
                styled_cross = df_cross.style.format({
                    'L3M Sales': '${:,.0f}',
                })
                st.dataframe(styled_cross, use_container_width=True, hide_index=True)

            # Category heatmap for top 15
            if category_heatmap:
                st.markdown("#### Top 15 Customer Category Mix (L3M Revenue)")
                df_heatmap = pd.DataFrame(category_heatmap)
                cats_in_data = [c for c in ['Drums', 'Rotors', 'ADB', 'Hubs'] if c in df_heatmap.columns]

                if cats_in_data:
                    df_heatmap['_total'] = df_heatmap[cats_in_data].sum(axis=1)
                    df_heatmap = df_heatmap.sort_values('_total', ascending=True)

                    fig_heatmap = go.Figure()
                    colors = {'Drums': '#1f77b4', 'Rotors': '#ff7f0e', 'ADB': '#2ca02c', 'Hubs': '#d62728'}
                    for cat in cats_in_data:
                        fig_heatmap.add_trace(go.Bar(
                            name=cat,
                            y=df_heatmap['customer'],
                            x=df_heatmap[cat],
                            orientation='h',
                            marker_color=colors.get(cat, '#999999'),
                        ))

                    fig_heatmap.update_layout(
                        barmode='stack',
                        title='Product Category Mix by Customer (L3M)',
                        xaxis_title='Revenue ($)',
                        height=500,
                        legend=dict(orientation='h', yanchor='bottom', y=1.02),
                    )
                    st.plotly_chart(fig_heatmap, use_container_width=True)

            st.divider()

            # ==================================================================
            # CUSTOMER PERFORMANCE DETAILS (collapsed)
            # ==================================================================
            with st.expander("Customer Performance Details"):
                # Top 15 Customers
                st.subheader("Top 15 Customers Performance")
                st.caption(f"GP margins based on annual income by customer. L3M ({_l3m_period}) and L12M ({_l12m_period}).")

                top_15 = customer_data['top_15_customers']
                df_top15 = pd.DataFrame(top_15)

                l3m_tab, l12m_tab = st.tabs([f"Last 3 Months ({_l3m_period})", f"Last 12 Months ({_l12m_period})"])

                with l3m_tab:
                    display_l3m = df_top15.copy()
                    display_l3m = display_l3m.rename(columns={
                        'customer': 'Customer', 'l3m_sales': 'Sales',
                        'l3m_gross_profit': 'Gross Profit', 'l3m_gp_margin': 'GP Margin %',
                        'l3m_pct_of_total': '% of Total Sales', 'rfm_segment': 'RFM Segment'
                    })
                    display_cols = ['Customer', 'Sales', 'Gross Profit', 'GP Margin %', '% of Total Sales', 'RFM Segment']

                    total_sales = sum(c['l12m_sales'] for c in top_15)
                    weighted_gp = sum(c['l12m_sales'] * c['l12m_gp_margin'] for c in top_15)
                    avg_gp_margin = weighted_gp / total_sales if total_sales else 53.9

                    styled_l3m = display_l3m[display_cols].style.format({
                        'Sales': '${:,.0f}', 'Gross Profit': '${:,.0f}',
                        'GP Margin %': '{:.1f}%', '% of Total Sales': '{:.1f}%'
                    }).apply(lambda x: [color_gp_margin(v, avg_gp_margin) if x.name == 'GP Margin %' else '' for v in x], axis=0)
                    st.dataframe(styled_l3m, use_container_width=True, hide_index=True)

                    df_l3m_sorted = df_top15.sort_values('l3m_sales', ascending=False)
                    fig_l3m = go.Figure()
                    fig_l3m.add_trace(go.Bar(name='Sales', x=df_l3m_sorted['customer'], y=df_l3m_sorted['l3m_sales'], marker_color='#1f77b4'))
                    fig_l3m.update_layout(title='L3M Sales by Top 15 Customers', xaxis_title='Customer', yaxis_title='Sales ($)',
                                          xaxis_tickangle=-45, height=500, hovermode='x unified', xaxis={'categoryorder': 'total descending'})
                    st.plotly_chart(fig_l3m, use_container_width=True)

                with l12m_tab:
                    display_l12m = df_top15.copy()
                    display_l12m['Trend %'] = ((display_l12m['l3m_sales'] / 3) - (display_l12m['l12m_sales'] / 12)) / (display_l12m['l12m_sales'] / 12) * 100
                    display_l12m = display_l12m.rename(columns={
                        'customer': 'Customer', 'l12m_sales': 'Sales',
                        'l12m_gross_profit': 'Gross Profit', 'l12m_gp_margin': 'GP Margin %',
                        'l12m_pct_of_total': '% of Total Sales', 'rfm_segment': 'RFM Segment'
                    })
                    display_cols = ['Customer', 'Sales', 'Gross Profit', 'GP Margin %', 'Trend %', 'RFM Segment']

                    total_sales = sum(c['l12m_sales'] for c in top_15)
                    weighted_gp = sum(c['l12m_sales'] * c['l12m_gp_margin'] for c in top_15)
                    avg_gp_margin = weighted_gp / total_sales if total_sales else 53.9

                    def apply_colors(row):
                        styles = [''] * len(row)
                        if 'GP Margin %' in row.index:
                            styles[row.index.get_loc('GP Margin %')] = color_gp_margin(row['GP Margin %'], avg_gp_margin)
                        if 'Trend %' in row.index:
                            idx = row.index.get_loc('Trend %')
                            t = row['Trend %']
                            styles[idx] = 'background-color: #d4edda' if t > 10 else ('background-color: #f8d7da' if t < -10 else 'background-color: #fff3cd')
                        return styles

                    styled_l12m = display_l12m[display_cols].style.format({
                        'Sales': '${:,.0f}', 'Gross Profit': '${:,.0f}',
                        'GP Margin %': '{:.1f}%', 'Trend %': '{:+.1f}%',
                    }).apply(apply_colors, axis=1)
                    st.dataframe(styled_l12m, use_container_width=True, hide_index=True)

                    df_l12m_sorted = df_top15.sort_values('l12m_sales', ascending=False)
                    fig_l12m = go.Figure()
                    fig_l12m.add_trace(go.Bar(name='Sales', x=df_l12m_sorted['customer'], y=df_l12m_sorted['l12m_sales'], marker_color='#2ca02c'))
                    fig_l12m.update_layout(title='L12M Sales by Top 15 Customers', xaxis_title='Customer', yaxis_title='Sales ($)',
                                           xaxis_tickangle=-45, height=500, hovermode='x unified', xaxis={'categoryorder': 'total descending'})
                    st.plotly_chart(fig_l12m, use_container_width=True)

                st.divider()

                # RFM Segment Details
                st.subheader("RFM Segmentation")
                rfm_segments = customer_data['rfm_segments']
                rfm_dist = customer_data['rfm_distribution']

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    champions = [s for s in rfm_segments if s['segment'] == 'Champions']
                    if champions:
                        st.metric("Champions", f"{rfm_dist['champions']} customers", f"${champions[0]['total_revenue']:,.0f}")
                with col2:
                    loyal = [s for s in rfm_segments if s['segment'] == 'Loyal Customers']
                    if loyal:
                        st.metric("Loyal Customers", f"{rfm_dist['loyal_customers']} customers", f"${loyal[0]['total_revenue']:,.0f}")
                with col3:
                    at_risk = [s for s in rfm_segments if s['segment'] == 'At Risk']
                    if at_risk:
                        st.metric("At Risk", f"{rfm_dist['at_risk']} customers", f"${at_risk[0]['total_revenue']:,.0f}")
                with col4:
                    hibernating = [s for s in rfm_segments if s['segment'] == 'Hibernating']
                    if hibernating:
                        st.metric("Hibernating", f"{rfm_dist['hibernating']} customers", f"${hibernating[0]['total_revenue']:,.0f}")

                segment_chart_data = [{'Segment': s['segment'], 'Customers': s['customer_count'], 'Revenue': s['total_revenue']} for s in rfm_segments]
                df_segments = pd.DataFrame(segment_chart_data)
                col1, col2 = st.columns(2)
                with col1:
                    fig_seg_count = px.pie(df_segments, values='Customers', names='Segment', title='Customers by Segment', color_discrete_sequence=px.colors.qualitative.Set3)
                    fig_seg_count.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_seg_count, use_container_width=True)
                with col2:
                    fig_seg_rev = px.pie(df_segments, values='Revenue', names='Segment', title='Revenue by Segment', color_discrete_sequence=px.colors.qualitative.Set3)
                    fig_seg_rev.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_seg_rev, use_container_width=True)

                # Detailed RFM table
                df_rfm_segments = pd.DataFrame(rfm_segments)
                df_rfm_segments['Revenue'] = df_rfm_segments['total_revenue'].apply(lambda x: f'${x:,.0f}')
                df_rfm_segments['Avg Revenue/Customer'] = df_rfm_segments['avg_revenue_per_customer'].apply(lambda x: f'${x:,.0f}')
                df_rfm_segments['Avg Recency (days)'] = df_rfm_segments['avg_recency_days'].apply(lambda x: f'{x:.0f}')
                df_rfm_segments['Avg Frequency'] = df_rfm_segments['avg_frequency'].apply(lambda x: f'{x:.1f}')
                display_rfm = df_rfm_segments[['segment', 'customer_count', 'Revenue', 'Avg Revenue/Customer', 'Avg Recency (days)', 'Avg Frequency']]
                display_rfm.columns = ['Segment', 'Customers', 'Total Revenue', 'Avg Revenue/Customer', 'Avg Recency (days)', 'Avg Frequency']
                st.dataframe(display_rfm, use_container_width=True, hide_index=True)

            # ==================================================================
            # PRODUCT CATEGORY MIX (collapsed)
            # ==================================================================
            product_cats = customer_data.get('product_category_summary', [])
            if product_cats:
                with st.expander("Product Category Mix (L3M)"):
                    col1, col2 = st.columns(2)
                    with col1:
                        df_cats = pd.DataFrame(product_cats)
                        fig_pie = go.Figure(data=[go.Pie(
                            labels=df_cats['category'], values=df_cats['l3m_revenue'],
                            textinfo='label+percent',
                            hovertemplate='%{label}<br>Revenue: $%{value:,.0f}<br>%{percent}<extra></extra>',
                        )])
                        fig_pie.update_layout(title='Revenue by Product Category', height=400)
                        st.plotly_chart(fig_pie, use_container_width=True)
                    with col2:
                        cat_rows = [{'Category': pc['category'], 'L3M Revenue': pc['l3m_revenue'],
                                     'Transactions': pc['l3m_transactions'], 'Customers': pc['l3m_customers']} for pc in product_cats]
                        df_cat_table = pd.DataFrame(cat_rows)
                        styled_cats = df_cat_table.style.format({'L3M Revenue': '${:,.0f}'})
                        st.dataframe(styled_cats, use_container_width=True, hide_index=True)

            # Footer
            st.caption(f"L3M: {_l3m_period} | L12M: {_l12m_period}")

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
            age_counts = age_dist.get('order_count', {})
            orders_90plus = age_counts.get('91-180 days', 0) + age_counts.get('180+ days', 0)
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
                        st.metric("NWC", fmt_money(cm['nwc']))
                        st.metric("Operating CF", fmt_money(cm['operating_cash_flow']))

                    st.divider()

                    # Revenue trend for this period
                    st.markdown("### Revenue Trend")

                    # Support both old 'monthly_data' format and new 'monthly_series' format
                    if 'monthly_series' in hist_data:
                        hist_series = hist_data['monthly_series'][:month]
                        months = [m['month'] for m in hist_series]
                        revenue = [m['revenue'] for m in hist_series]
                    elif 'monthly_data' in hist_data:
                        months = hist_data['monthly_data']['months'][:month]
                        revenue = hist_data['monthly_data']['revenue'][:month]
                    else:
                        months, revenue = [], []

                    if months and revenue:
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
                    else:
                        st.info("Monthly revenue trend data not available for this period.")

                    # Customer summary if available
                    if hist_customer:
                        st.divider()
                        st.markdown("### Top 10 Customers (L12M)")

                        customers = hist_customer.get('top_15_customers', hist_customer.get('top_customers', []))[:10]
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
