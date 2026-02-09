# Performance Indicators Analysis - Green/Yellow/Red Opportunities

## Overview

This document identifies opportunities to add visual performance indicators (🟢 Green / 🟡 Yellow / 🔴 Red) throughout the DuraBrake dashboard to make it easier to spot issues and opportunities at a glance.

---

## Current Dashboard Review

### Tab 1: 📈 Summary

#### **Current Month Snapshot**
- Revenue, Gross Profit, EBITDA, Net Income (absolute values)
- Gross Margin %, EBITDA Margin %
- NWC, Operating Cash Flow

#### **L3M Comparison**
- Shows variance % between current month and L3M average
- Currently shows delta in st.metric() but no color coding

---

## 🎯 Recommended Performance Indicators

### **PRIORITY 1: High-Impact Indicators (Implement First)**

#### **1.1 Margin Performance vs. Budget/Target**
**Location:** Tab 1 (Summary) - Current Month Snapshot

**Metrics to color code:**
- **Gross Margin %**
  - 🟢 Green: >= Target GP% (e.g., 55%)
  - 🟡 Yellow: Target GP% -3% to Target GP% (e.g., 52-54.9%)
  - 🔴 Red: < Target GP% -3% (e.g., <52%)

- **EBITDA Margin %**
  - 🟢 Green: >= Target EBITDA% (e.g., 15%)
  - 🟡 Yellow: Target EBITDA% -3% to Target EBITDA% (e.g., 12-14.9%)
  - 🔴 Red: < Target EBITDA% -3% (e.g., <12%)

**Data needed:**
- Target/Budget Gross Margin %
- Target/Budget EBITDA Margin %

**Implementation:** Background color on metric cards or colored indicators next to values

---

#### **1.2 Revenue Performance vs. Budget**
**Location:** Tab 1 (Summary) - Current Month Snapshot

**Metrics to color code:**
- **Revenue vs. Budget**
  - 🟢 Green: >= 95% of budget
  - 🟡 Yellow: 85-94% of budget
  - 🔴 Red: < 85% of budget

**Data needed:**
- Monthly revenue budget by month

**Display:** Add "vs. Budget: XX%" below revenue metric with color

---

#### **1.3 Customer Gross Margin Performance**
**Location:** Tab 4 (Customers) - Top 15 Customers tables

**Metrics to color code:**
- **GP Margin % for each customer**
  - 🟢 Green: >= Company average GP% (currently 53.9%)
  - 🟡 Yellow: Company average -5% to Company average (e.g., 48.9-53.9%)
  - 🔴 Red: < Company average -5% (e.g., <48.9%)

**Data needed:**
- Already have company average GP margin (53.9%)
- Already have customer-specific GP margins

**Implementation:**
- Add colored background to GP Margin % column in customer tables
- Or add colored dot/icon next to GP% values
- This helps identify unprofitable customers at a glance

---

#### **1.4 Customer Sales Volume Trend (L3M vs. L12M)**
**Location:** Tab 4 (Customers) - Top 15 Customers tables

**Metrics to color code:**
- **L3M vs. L12M Sales Rate**
  - Calculate: (L3M Sales / 3) vs. (L12M Sales / 12) = monthly run rate comparison
  - 🟢 Green: L3M run rate > L12M run rate +10% (growing)
  - 🟡 Yellow: L12M run rate ±10% (stable)
  - 🔴 Red: L3M run rate < L12M run rate -10% (declining)

**Data needed:**
- Already have L3M and L12M sales for each customer

**Implementation:** Add new column "Trend" with colored indicator

**Example calculation:**
- Customer A: L3M = $150k, L12M = $400k
- L3M monthly rate = $150k / 3 = $50k/month
- L12M monthly rate = $400k / 12 = $33k/month
- L3M rate is 50% higher → 🟢 Green (growing customer)

---

#### **1.5 Working Capital Ratios**
**Location:** Tab 3 (NWC Details) - NWC Ratios section

**Metrics to color code:**

- **Days Sales Outstanding (DSO)**
  - 🟢 Green: <= 30 days (excellent)
  - 🟡 Yellow: 31-45 days (acceptable)
  - 🔴 Red: > 45 days (needs attention)

- **Days Inventory Outstanding (DIO)**
  - 🟢 Green: <= 45 days (lean inventory)
  - 🟡 Yellow: 46-60 days (acceptable)
  - 🔴 Red: > 60 days (excess inventory)

- **Days Payable Outstanding (DPO)**
  - 🟢 Green: >= 30 days (good cash management)
  - 🟡 Yellow: 20-29 days (acceptable)
  - 🔴 Red: < 20 days (paying too quickly)

- **Cash Conversion Cycle (CCC)**
  - 🟢 Green: <= 30 days
  - 🟡 Yellow: 31-60 days
  - 🔴 Red: > 60 days

**Data needed:**
- Already calculated in dashboard
- Need to define target thresholds (suggested above)

---

#### **1.6 Backlog Age Distribution**
**Location:** Tab 5 (Order Backlog) - Summary metrics

**Metrics to color code:**

- **Average Order Age**
  - 🟢 Green: <= 45 days (healthy)
  - 🟡 Yellow: 46-60 days (monitor)
  - 🔴 Red: > 60 days (concerning)

- **% of Orders > 90 days old**
  - 🟢 Green: < 10% of total backlog value
  - 🟡 Yellow: 10-20% of total backlog value
  - 🔴 Red: > 20% of total backlog value

**Data needed:**
- Already have order ages
- Need to calculate % over 90 days

---

### **PRIORITY 2: Medium-Impact Indicators**

#### **2.1 Product-Level Margin Performance**
**Location:** Tab 2 (Product Details) - Current Month vs L3M

**Metrics to color code:**
- **GP Margin % for each product vs. product-specific target**
  - 🟢 Green: >= Product target margin
  - 🟡 Yellow: Product target -3% to target
  - 🔴 Red: < Product target -3%

**Data needed:**
- Target GP margin for each product line:
  - Cast Drums: X%
  - Steel Shell Drums: X%
  - Rotors: X%
  - Calipers: X%
  - Pads: X%
  - Hubs: X%

---

#### **2.2 Product Sales Growth (Current Month vs. L3M)**
**Location:** Tab 2 (Product Details)

**Metrics to color code:**
- **Variance % already shown in dashboard**
  - 🟢 Green: > +5% growth
  - 🟡 Yellow: -5% to +5% (flat)
  - 🔴 Red: < -5% (declining)

**Data needed:**
- Already calculated variance percentages

---

#### **2.3 NWC as % of Revenue**
**Location:** Tab 3 (NWC Details)

**Metrics to color code:**
- **NWC as % of YTD Revenue**
  - 🟢 Green: <= 15% (efficient)
  - 🟡 Yellow: 15-25% (acceptable)
  - 🔴 Red: > 25% (too much capital tied up)

**Data needed:**
- Already calculated
- Need target threshold (industry varies, suggested 15-25%)

---

#### **2.4 RFM Customer Segments**
**Location:** Tab 4 (Customers) - Segment Distribution

**Visual indicators:**
- **Champions segment** - 🟢 Show % of total revenue
  - Goal: Maximize this percentage
- **At Risk segment** - 🟡 Show trend (growing/shrinking)
  - Goal: Minimize movement into this segment
- **Hibernating segment** - 🔴 Show % of former revenue
  - Goal: Minimize this percentage

**Data needed:**
- Already have segment data
- Would benefit from historical comparison (month-over-month segment changes)

---

### **PRIORITY 3: Advanced Indicators**

#### **3.1 Operating Cash Flow Performance**
**Location:** Tab 1 (Summary)

**Metrics to color code:**
- **Operating CF vs. EBITDA ratio**
  - 🟢 Green: Op CF >= 90% of EBITDA (strong cash generation)
  - 🟡 Yellow: Op CF 70-89% of EBITDA (acceptable)
  - 🔴 Red: Op CF < 70% of EBITDA (cash flow issues)

**Data needed:**
- Already have both metrics
- This ratio indicates how well EBITDA converts to cash

---

#### **3.2 Backlog Coverage Ratio**
**Location:** Tab 5 (Order Backlog)

**Metrics to color code:**
- **Backlog / Avg Monthly Revenue**
  - 🟢 Green: >= 1.5x (healthy pipeline)
  - 🟡 Yellow: 1.0-1.4x (adequate)
  - 🔴 Red: < 1.0x (weak pipeline)

**Data needed:**
- Already have backlog total
- Already have monthly revenue
- Simple calculation

---

#### **3.3 Customer Concentration Risk**
**Location:** Tab 4 (Customers)

**Metrics to color code:**
- **Top Customer % of Total Sales**
  - 🟢 Green: < 15% (well diversified)
  - 🟡 Yellow: 15-25% (monitor)
  - 🔴 Red: > 25% (concentration risk)

- **Top 5 Customers % of Total Sales**
  - 🟢 Green: < 40% (well diversified)
  - 🟡 Yellow: 40-60% (moderate risk)
  - 🔴 Red: > 60% (high concentration risk)

**Data needed:**
- Already have customer sales data
- Need to calculate concentration percentages

---

## 📊 Implementation Requirements

### **Required Budget/Target Data (to enable indicators)**

Create a new configuration file or add to dashboard:

```python
# Budget and Target Configuration
TARGETS = {
    "margins": {
        "gross_margin_pct": 55.0,      # Target GP%
        "ebitda_margin_pct": 15.0,      # Target EBITDA%
    },
    "revenue": {
        "monthly_budget": {
            "01": 850000,  # January
            "02": 900000,  # February
            "03": 950000,  # March
            # ... etc for all 12 months
        }
    },
    "products": {
        "Cast Drums": {"target_margin": 58.0},
        "Steel Shell Drums": {"target_margin": 52.0},
        "Rotors": {"target_margin": 55.0},
        "Calipers": {"target_margin": 60.0},
        "Pads": {"target_margin": 48.0},
        "Hubs": {"target_margin": 54.0},
    },
    "working_capital": {
        "dso_target": 30,      # Days
        "dio_target": 45,      # Days
        "dpo_target": 30,      # Days
        "nwc_pct_target": 20,  # % of revenue
    },
    "backlog": {
        "max_age_days": 60,
        "min_coverage_ratio": 1.5,  # Backlog / Monthly Revenue
    }
}
```

---

## 🎨 Visual Implementation Options

### **Option A: Colored Metric Cards**
- Use Streamlit's built-in metric with colored background
- Most prominent, good for key metrics

### **Option B: Colored Icons/Indicators**
- Add 🟢 🟡 🔴 emoji or colored dots next to values
- Subtle, works well in tables
- Easy to implement

### **Option C: Colored Table Cells**
- Use pandas Styler to color cell backgrounds
- Great for customer and product tables
- Already using Styler for formatting

### **Option D: Progress Bars**
- Show actual vs. target with colored progress bar
- Good for budget attainment visualization

---

## 📋 Implementation Priority Order

### **Phase 1: Quick Wins (1-2 hours)**
1. Customer GP Margin color coding (already have data)
2. Customer Sales Trend (L3M vs L12M) indicator
3. Product Sales Growth variance colors
4. Working Capital ratio thresholds

### **Phase 2: With Budget Data (2-3 hours)**
5. Revenue vs. Budget indicator
6. Margin vs. Target indicators
7. Product margin vs. Target

### **Phase 3: Advanced Analytics (3-4 hours)**
8. Customer concentration risk
9. Backlog coverage ratio
10. Operating CF quality indicator
11. Historical trend indicators (month-over-month changes)

---

## 🔄 Ongoing Maintenance

### **Monthly Review:**
- Check if thresholds still make sense
- Adjust targets based on seasonal patterns
- Review which indicators are most useful

### **Quarterly Update:**
- Update budget/target values
- Reassess threshold ranges
- Add new indicators based on business needs

---

## ❓ Questions to Answer Before Implementation

1. **Budget/Target Data:**
   - Do you have monthly revenue budget by month?
   - What are your target GP and EBITDA margins?
   - Do different products have different target margins?

2. **Working Capital Thresholds:**
   - What are acceptable DSO/DIO/DPO ranges for your business?
   - Industry standard or based on your experience?

3. **Priority:**
   - Which indicators would be most valuable to you first?
   - Which metrics do you review most frequently?

4. **Visual Preference:**
   - Do you prefer subtle indicators (dots/icons) or prominent ones (colored backgrounds)?
   - Should we use emojis (🟢🟡🔴) or custom colors?

---

## 💡 Example Mockups

### **Customer Table with Indicators:**

```
Customer         | L3M Sales  | L12M Sales | GP Margin % | Trend
----------------|-----------|-----------|------------|-------
ABC Company     | $125,000  | $400,000  | 58.2% 🟢   | 🟢 +15%
XYZ Industries  | $98,000   | $420,000  | 52.1% 🟡   | 🔴 -22%
DEF Corp        | $85,000   | $280,000  | 45.3% 🔴   | 🟡 +2%
```

### **Margin Performance Card:**

```
Gross Margin %: 54.2% 🟢
Target: 55.0% | Variance: -0.8%
```

### **Working Capital Ratios:**

```
DSO: 28 days 🟢
DIO: 52 days 🟡
DPO: 25 days 🟡
CCC: 55 days 🟡
```

---

**Next Step:** Review this analysis and let me know:
1. Which indicators are highest priority for you?
2. What budget/target data do you have available?
3. Visual preference for the indicators?
