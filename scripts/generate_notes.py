"""
Auto-generate Critical Notes and Action Items from dashboard data.
Analyzes the month's financial, customer, and backlog data to produce
actionable insights for the management dashboard.
"""

import json
import os


def run_generate_notes(period, year, month):
    """Generate critical notes and action items from dashboard data."""

    output_folder = os.path.join('generated', period)
    notes_file = os.path.join(output_folder, 'dashboard_notes.json')

    # Don't overwrite if notes already exist (user may have edited them)
    if os.path.exists(notes_file):
        with open(notes_file, 'r') as f:
            existing = json.load(f)
        if existing.get('critical_notes') or existing.get('action_items'):
            print(f"  Notes already exist for {period}, skipping auto-generation")
            return existing

    # Load all available data
    dashboard_data = _load_json(output_folder, 'dashboard_data.json')
    customer_data = _load_json(output_folder, 'customer_dashboard_data.json')
    backlog_data = _load_json(output_folder, 'backlog_dashboard_data.json')

    # Load prior year data for comparison
    prior_period = f"{(year - 1) % 100:02d}.12"
    prior_data = _load_json(os.path.join('generated', prior_period), 'dashboard_data.json')

    critical_notes = []
    action_items = []

    if dashboard_data:
        _analyze_financials(dashboard_data, prior_data, critical_notes, action_items)

    if customer_data:
        _analyze_customers(customer_data, critical_notes, action_items)

    if backlog_data:
        _analyze_backlog(backlog_data, critical_notes, action_items)

    notes_content = {
        "critical_notes": "\n".join(critical_notes),
        "action_items": "\n".join(action_items)
    }

    # Write standalone notes file
    with open(notes_file, 'w') as f:
        json.dump(notes_content, f, indent=2)

    # Also inject notes into dashboard_data.json so the dashboard can
    # read them via the same load_data() path that already works
    dashboard_file = os.path.join(output_folder, 'dashboard_data.json')
    if os.path.exists(dashboard_file):
        with open(dashboard_file, 'r') as f:
            dash = json.load(f)
        dash['notes'] = notes_content
        with open(dashboard_file, 'w') as f:
            json.dump(dash, f, indent=2)

    print(f"  Generated {len(critical_notes)} notes, {len(action_items)} action items")
    return notes_content


def _load_json(folder, filename):
    """Safely load a JSON file."""
    path = os.path.join(folder, filename)
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return None


def _analyze_financials(data, prior_data, notes, actions):
    """Analyze financial data for key insights."""
    cm = data.get('current_month', {})
    l3m = data.get('l3m_comparison', {})
    ytd = data.get('ytd_summary', {})
    month = data['metadata']['reporting_month']

    # Revenue vs L3M
    rev_var = l3m.get('revenue', {}).get('variance_pct', 0) or 0
    if rev_var > 20:
        notes.append(f"- Revenue of ${cm['revenue']:,.0f} is {rev_var:.0f}% above the prior 3-month average — strong performance")
    elif rev_var < -20:
        notes.append(f"- Revenue of ${cm['revenue']:,.0f} is {abs(rev_var):.0f}% below the prior 3-month average — significant decline")
        actions.append(f"- Investigate revenue decline drivers and review sales pipeline")
    elif rev_var < -5:
        notes.append(f"- Revenue of ${cm['revenue']:,.0f} is {abs(rev_var):.0f}% below L3M average — moderate softness")

    # Gross margin shift
    gm_var = l3m.get('gross_margin_pct', {}).get('variance_pts', 0) or 0
    gm_current = cm.get('gross_margin_pct', 0) or 0
    if gm_var < -3:
        notes.append(f"- Gross margin at {gm_current:.1f}% is {abs(gm_var):.1f} pts below L3M average — margin compression")
        actions.append(f"- Review product mix and pricing; identify margin erosion sources")
    elif gm_var > 3:
        notes.append(f"- Gross margin improved to {gm_current:.1f}%, up {gm_var:.1f} pts vs L3M average")

    # EBITDA margin
    ebitda_var = l3m.get('ebitda_margin_pct', {}).get('variance_pts', 0) or 0
    ebitda_current = cm.get('ebitda_margin_pct', 0) or 0
    if ebitda_var < -3:
        notes.append(f"- EBITDA margin at {ebitda_current:.1f}% declined {abs(ebitda_var):.1f} pts vs L3M — operating cost pressure")
        actions.append(f"- Review operating expenses for cost reduction opportunities")

    # Net income swing
    ni_current = cm.get('net_income', 0) or 0
    ni_l3m_avg = l3m.get('net_income', {}).get('l3m_avg', 0) or 0
    if ni_current > 0 and ni_l3m_avg < 0:
        notes.append(f"- Net income turned positive at ${ni_current:,.0f} after averaging ${ni_l3m_avg:,.0f} over prior 3 months")
    elif ni_current < 0:
        notes.append(f"- Net loss of ${abs(ni_current):,.0f} — profitability concern")
        actions.append(f"- Develop plan to return to profitability")

    # Operating cash flow
    ocf = cm.get('operating_cash_flow', 0) or 0
    if ocf < 0:
        notes.append(f"- Operating cash flow is negative at ${ocf:,.0f}")
        actions.append(f"- Monitor cash position; review AR collections and AP timing")

    # NWC level
    nwc = cm.get('nwc', 0) or 0
    revenue = cm.get('revenue', 0) or 0
    if revenue > 0:
        nwc_months = nwc / revenue
        if nwc_months > 2:
            notes.append(f"- Net working capital of ${nwc:,.0f} represents {nwc_months:.1f}x monthly revenue — elevated")

    # Inventory level
    inventory = cm.get('inventory', 0) or 0
    if revenue > 0 and inventory > 0:
        inv_days = inventory / (revenue * (1 - gm_current / 100) / 30) if gm_current < 100 else 0
        if inv_days > 90:
            notes.append(f"- Inventory at ${inventory:,.0f} represents ~{inv_days:.0f} days — above target")
            actions.append(f"- Review slow-moving inventory; consider reduction plan to target ≤85 days")

    # Compare to prior year same month if available
    if prior_data:
        prior_series = prior_data.get('monthly_series', [])
        prior_month_num = data['monthly_series'][0].get('month_num', 1) if data.get('monthly_series') else 1
        prior_month_data = None
        for m in prior_series:
            if m.get('month_num') == prior_month_num:
                prior_month_data = m
                break
        if prior_month_data and prior_month_data.get('revenue'):
            yoy_change = ((revenue - prior_month_data['revenue']) / prior_month_data['revenue']) * 100
            if abs(yoy_change) > 10:
                direction = "up" if yoy_change > 0 else "down"
                notes.append(f"- Year-over-year revenue is {direction} {abs(yoy_change):.0f}% vs {month} {data['metadata']['reporting_year'] - 1}")


def _analyze_customers(cust_data, notes, actions):
    """Analyze customer data for key insights."""
    rfm_dist = cust_data.get('rfm_distribution', {})
    rfm_segments = cust_data.get('rfm_segments', [])

    # At-risk customers
    at_risk_count = rfm_dist.get('at_risk', 0)
    if at_risk_count > 0:
        at_risk_seg = [s for s in rfm_segments if s['segment'] == 'At Risk']
        if at_risk_seg:
            at_risk_rev = at_risk_seg[0].get('total_revenue', 0)
            notes.append(f"- {at_risk_count} customers classified as 'At Risk' with ${at_risk_rev:,.0f} in historical revenue")
            actions.append(f"- Prioritize outreach to {at_risk_count} At Risk customers before they churn")

    # Hibernating customers
    hibernating_count = rfm_dist.get('hibernating', 0)
    if hibernating_count > 10:
        notes.append(f"- {hibernating_count} customers are Hibernating (no recent purchases)")
        actions.append(f"- Run targeted reactivation campaign for top Hibernating accounts")

    # Customer concentration
    top_15 = cust_data.get('top_15_customers', [])
    total_l3m = cust_data.get('metadata', {}).get('total_l3m_sales', 0)
    if top_15 and total_l3m:
        top5_l3m = sum(c.get('l3m_sales', 0) for c in top_15[:5])
        top5_pct = (top5_l3m / total_l3m * 100) if total_l3m else 0
        if top5_pct > 40:
            notes.append(f"- Top 5 customers represent {top5_pct:.0f}% of L3M sales — high concentration risk")
            actions.append(f"- Diversify customer base; develop pipeline of mid-tier accounts")

    # Low-margin top customers
    low_margin_customers = [c for c in top_15[:10] if (c.get('l3m_gp_margin', 100) or 100) < 15]
    if low_margin_customers:
        names = ", ".join(c['customer'].split('/')[0].strip() for c in low_margin_customers[:3])
        notes.append(f"- {len(low_margin_customers)} of top 10 customers have GP margin below 15%: {names}")
        actions.append(f"- Review pricing strategy for low-margin key accounts")

    # Overdue customers
    overdue = cust_data.get('overdue_customers', [])
    truly_overdue = [o for o in overdue if not o.get('has_backlog_order')]
    if truly_overdue:
        overdue_revenue = sum(o.get('l12m_sales', 0) for o in truly_overdue[:10])
        top_overdue = [o['customer'].split('/')[0].strip() for o in truly_overdue[:3]]
        notes.append(f"- {len(truly_overdue)} customers are overdue to order (${overdue_revenue:,.0f} L12M at risk): {', '.join(top_overdue)}")
        actions.append(f"- Contact {len(truly_overdue)} overdue customers — top accounts: {', '.join(top_overdue)}")

    # Cross-sell opportunities
    cross_sell = cust_data.get('cross_sell_opportunities', [])
    if cross_sell:
        top_cs = cross_sell[:3]
        cs_details = []
        for cs in top_cs:
            name = cs['customer'].split('/')[0].strip()
            missing = ', '.join(cs['missing_categories'])
            cs_details.append(f"{name} (missing: {missing})")
        notes.append(f"- {len(cross_sell)} customers have cross-sell opportunities across product categories")
        actions.append(f"- Top cross-sell targets: {'; '.join(cs_details)}")

    # Customers needing attention summary
    attention = cust_data.get('customers_needing_attention', [])
    if attention:
        multi_flag = [a for a in attention if len(a['reasons']) >= 2]
        if multi_flag:
            names = [a['customer'].split('/')[0].strip() for a in multi_flag[:3]]
            notes.append(f"- {len(multi_flag)} customers flagged with multiple attention signals: {', '.join(names)}")


def _analyze_backlog(backlog, notes, actions):
    """Analyze backlog data for key insights."""
    summary = backlog.get('summary', {})
    age_dist = backlog.get('age_distribution', {})

    total_value = summary.get('total_backlog_value', 0)
    total_orders = summary.get('total_orders', 0)
    avg_age = summary.get('avg_age_days', 0)

    notes.append(f"- Order backlog of ${total_value:,.0f} across {total_orders} orders (avg age: {avg_age:.0f} days)")

    # Aging concerns
    age_counts = age_dist.get('order_count', {})
    old_orders = age_counts.get('91-180 days', 0) + age_counts.get('180+ days', 0)
    if old_orders > 0 and total_orders > 0:
        old_pct = old_orders / total_orders * 100
        if old_pct > 15:
            notes.append(f"- {old_orders} orders ({old_pct:.0f}%) are over 90 days old — potential delivery risk")
            actions.append(f"- Review {old_orders} aged orders (>90 days) for delivery status and customer communication")

    # Average age threshold
    if avg_age > 60:
        actions.append(f"- Backlog average age of {avg_age:.0f} days exceeds 60-day target; review production schedule")

    # Ship date pipeline
    ship_dist = backlog.get('ship_date_distribution', {})
    ship_values = ship_dist.get('order_value', {})
    next_30_value = ship_values.get('0-30 days', 0)
    if next_30_value and total_value:
        next_30_pct = next_30_value / total_value * 100
        notes.append(f"- ${next_30_value:,.0f} ({next_30_pct:.0f}%) of backlog expected to ship within 30 days")
