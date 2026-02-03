# DuraBrake KPI Dashboard - Complete Setup Guide

## Overview

This is a fully automated monthly financial dashboard system for DuraBrake. The system generates comprehensive financial analytics including:

- Monthly financial metrics with L3M comparisons
- Product-level analysis (6 product categories)
- Net Working Capital (NWC) details and ratios
- Customer RFM segmentation and analysis
- Order backlog tracking
- Historical dashboard archive

## Quick Start - Monthly Dashboard Generation

To generate a new monthly dashboard, follow these simple steps:

### 1. Prepare Input Files

Copy these 4 files to `inputs/YY.MM/` folder:

```
inputs/
└── 26.01/  (example for January 2026)
    ├── DuraBrake Monthly Financial Package.xlsx
    ├── DuraBrake_Sales by Customer Detail.xlsx
    ├── DuraBrake_Income by Customer Summary.xlsx
    └── Backlog_2026-01-31.xlsx
```

### 2. Update Period Configuration

Edit `generate_dashboard.py` - change line 14:

```python
PERIOD = "26.01"  # Format: YY.MM (26.01 for January 2026)
```

### 3. Run Dashboard Generator

```bash
cd "C:\Users\scull\Box\DuraParts\Finance\KPI Dashboard"
python generate_dashboard.py
```

This single command will:
- Generate financial dashboard data
- Run RFM analysis (customer segmentation)
- Run customer analysis (L3M/L12M metrics)
- Run backlog analysis
- Create all 5 output files in `generated/YY.MM/`

### 4. Launch Dashboard

```bash
python -m streamlit run financial_dashboard.py
```

Or update `PERIOD` in `financial_dashboard.py` line 18 to view a different month.

Dashboard will open at: http://localhost:8501

---

## Folder Structure

```
KPI Dashboard/
├── inputs/                           # Monthly input files
│   ├── 25.12/                       # December 2025
│   │   ├── DuraBrake Monthly Financial Package.xlsx
│   │   ├── DuraBrake_Sales by Customer Detail.xlsx
│   │   ├── DuraBrake_Income by Customer Summary.xlsx
│   │   └── Backlog_2025-12-31.xlsx
│   └── 26.01/                       # January 2026 (future)
│
├── generated/                        # Generated dashboard data
│   ├── 25.12/                       # December 2025 outputs
│   │   ├── dashboard_data.json
│   │   ├── customer_dashboard_data.json
│   │   ├── backlog_dashboard_data.json
│   │   ├── rfm_analysis_results.csv
│   │   └── rfm_summary.json
│   └── 26.01/                       # January 2026 outputs (future)
│
├── scripts/                          # Modular analysis scripts
│   ├── rfm_analysis.py              # Customer RFM segmentation
│   ├── customer_analysis.py         # Customer metrics (L3M/L12M)
│   └── backlog_analysis.py          # Order backlog analysis
│
├── generate_dashboard.py            # Master orchestration script
├── export_dashboard_data.py         # Financial data extraction
├── financial_dashboard.py           # Streamlit dashboard app
└── README.md                        # This file
```

---

## Dashboard Tabs

### Tab 1: 📈 Summary
- Current month snapshot (Revenue, EBITDA, Margins, NWC)
- L3M comparison (current vs prior 3-month average)
- Monthly trends (Revenue, EBITDA, Margins)
- Rolling L3M variance analysis
- YTD summary
- Q4 summary

### Tab 2: 🏭 Product Details
- Current month vs L3M for each product:
  - Cast Drums
  - Steel Shell Drums
  - Rotors
  - Calipers
  - Pads
  - Hubs
- Product trend charts (sales and margins)

### Tab 3: 💰 NWC Details
- Current month NWC components (A/R, Inventory, A/P)
- NWC ratios (DSO, DIO, DPO, CCC)
- NWC trend charts
- NWC as % of Revenue

### Tab 4: 👥 Customers
- RFM Segmentation Overview
- Customer segment distribution charts
- Top 15 customers performance (L3M and L12M)
- Sales, Gross Profit, GP Margin % by customer
- Actual GP margins from annual income data

### Tab 5: 📦 Order Backlog
- Backlog summary metrics
- Age distribution (0-30, 31-60, 61-90, 91-180, 180+ days)
- Expected ship date distribution
- Top 10 customers by backlog value
- Backlog by sales rep
- Backlog by region

### Tab 6: 📚 Historicals
- **NEW!** View prior months' dashboards
- Select any period from available history
- Compare key metrics across months
- Browse historical customer and backlog data
- Starting with 25.12, automatically archives each month going forward

---

## Input File Requirements

### 1. DuraBrake Monthly Financial Package.xlsx

**Required Sheets:**
- `PL YTD YYYY` (e.g., `PL YTD 2025`)
  - Revenue, COGS, Gross Profit, EBITDA, Net Income rows
  - Columns: Jan through Dec

- `BS YTD YYYY` (e.g., `BS YTD 2025`)
  - Total Accounts Receivable
  - Total 130 Inventory Asset
  - Total Accounts Payable
  - Total Current Assets
  - Total Current Liabilities

- `Cashflow YTD YYYY` (e.g., `Cashflow YTD 2025`)
  - Net Cash Provided by Operating Activities
  - Net Cash Provided by Investing Activities
  - Net Cash Provided by Financing Activities

- `GP by product`
  - Sales and COGS for each product category

### 2. DuraBrake_Sales by Customer Detail.xlsx

- Full year transaction history (Jan 1 - Month End)
- Must include Invoice transactions only
- Required columns: DocNumber, Date, Customer, Item, Amount

### 3. DuraBrake_Income by Customer Summary.xlsx

- Annual income statement by customer
- Required columns: Customer, Income, Expenses, Net Income
- Used to calculate actual GP margins per customer

### 4. Backlog_YYYY-MM-DD.xlsx

- Open orders as of month-end date
- Required columns: DocNumber, Order Date, Customer, SubTotal, Sales Rep, Region
- Optional: Estimated Invoice Date (recommended)

---

## One-Shot Automation

After copying input files to `inputs/YY.MM/`, you can generate the complete dashboard with a single prompt:

**"Create the YY.MM DuraBrake dashboard"**

This will:
1. Run `generate_dashboard.py` to create all data files
2. Launch the Streamlit dashboard
3. Make all 6 tabs accessible
4. Archive the data for historical viewing

---

## Key Metrics & Formulas

### Financial Metrics
- **Gross Margin %** = (Gross Profit / Revenue) × 100
- **EBITDA Margin %** = (EBITDA / Revenue) × 100
- **NWC** = Accounts Receivable + Inventory - Accounts Payable
- **DSO** = (A/R / Revenue) × 30 days
- **DIO** = (Inventory / COGS) × 30 days
- **DPO** = (A/P / COGS) × 30 days
- **CCC** = DSO + DIO - DPO

### Customer Metrics
- **L3M Period** = Last 3 months (e.g., Oct-Dec for December)
- **L12M Period** = Full year (Jan-Dec)
- **GP Margin per Customer** = (Net Income / Income) × 100 from annual income data
- **L3M/L12M Gross Profit** = Sales × (GP Margin % / 100)

### RFM Segmentation
- **Recency** = Days since last purchase (lower is better)
- **Frequency** = Number of transactions (higher is better)
- **Monetary** = Total purchase value (higher is better)
- **Scores** = 1-5 scale using quintiles

---

## Generated Output Files

Each period generates 5 files in `generated/YY.MM/`:

1. **dashboard_data.json** - Main financial metrics
2. **customer_dashboard_data.json** - Customer analysis
3. **backlog_dashboard_data.json** - Backlog analysis
4. **rfm_analysis_results.csv** - Detailed RFM scores
5. **rfm_summary.json** - RFM summary statistics

---

## Troubleshooting

### File Not Found Errors
- Verify file paths in scripts match actual file locations
- Ensure `inputs/YY.MM/` folder structure is correct
- Check that all 4 input files are present

### Date Parsing Errors
- Ensure dates in Excel are formatted as dates, not text
- Open Excel file and verify date columns show actual dates

### Missing Data in Charts
- Verify Excel sheets have correct row labels
- Compare row labels to search terms in `export_dashboard_data.py`

### Streamlit Cache Issues
- Press "C" then "Clear Cache" in Streamlit
- Or restart the dashboard

---

## Monthly Workflow

1. **Copy Input Files** → `inputs/YY.MM/`
2. **Update PERIOD** → Edit `generate_dashboard.py` line 14
3. **Run Generator** → `python generate_dashboard.py`
4. **Launch Dashboard** → `python -m streamlit run financial_dashboard.py`
5. **Review All Tabs** → Summary, Products, NWC, Customers, Backlog, Historicals
6. **Archive Complete** → Data automatically saved for historical viewing

---

## Version History

### Version 1.1 - January 2026
- Added Historicals tab for viewing prior months
- Reorganized to `/Finance/KPI Dashboard` structure
- Implemented one-shot automation with `generate_dashboard.py`
- Created modular analysis scripts in `scripts/` folder
- Parameterized all scripts to work with `inputs/YY.MM/` structure

### Version 1.0 - December 2025
- Initial dashboard with 5 tabs
- Financial summary with L3M comparisons
- Product-level analysis
- NWC details and ratios
- Customer RFM segmentation with actual GP margins
- Order backlog analysis

---

## Contact & Support

For questions about the dashboard, refer to:
- This README for setup and usage
- `DASHBOARD_MONTHLY_PROCESS.md` in `/Finance/Monthly Financials` for detailed process
- `MONTHLY_UPDATE_QUICK_REFERENCE.md` for quick reference

**Required Python Packages:**
- pandas
- numpy
- streamlit
- plotly
- openpyxl (for Excel file reading)
