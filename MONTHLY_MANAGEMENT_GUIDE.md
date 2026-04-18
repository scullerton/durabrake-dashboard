# DuraBrake Dashboard - Monthly Management Guide

## 🤖 Automated Monthly Process (Primary)

The dashboard now runs itself. Two Windows Task Scheduler jobs handle the full pipeline:

| Job | When | What it does |
|---|---|---|
| **A — Backlog Snapshot** | Last day of month, 11:45 PM | Pulls live backlog from FileMaker Cloud (required because it's a live view — can't be retrieved later) |
| **B — Monthly Dashboard** | Daily 6 AM from the 22nd | Pulls QBO Sales + Income reports, copies internal financial package from Box, runs pipeline, git-pushes; retries daily until internal report is ready |

**Where things live:**
- Logs: `logs/backlog_snapshot_{YY.MM}.log` and `logs/monthly_automation_{YY.MM}.log`
- Email drafts: `drafts/monthly_report_{YY.MM}.eml` (never auto-sent — review and send manually)
- Scheduler wrappers: `scheduler/job_a_backlog_snapshot.bat`, `scheduler/job_b_monthly_dashboard.bat`

**Re-running manually (if scheduler failed or you want to re-process):**
```bash
cd "C:\Users\scull\Box\DuraParts\Finance\KPI Dashboard"
python scripts\monthly_automation.py --period 26.02 --force
```

**Credential management (one-time setup or rotation):**
```bash
python scripts\qbo_client.py --setup    # QuickBooks Online OAuth
python scripts\fmp_client.py --setup    # FileMaker Cloud Data API
python scripts\secrets_helper.py list   # verify what's stored (no values shown)
```

---

## 📅 Manual Monthly Process (Fallback / Legacy)

If automation is broken or being reconfigured, follow the steps below.

---

## Step 1: Prepare Input Files

**Copy these 4 files to the inputs folder:**

```
C:\Users\scull\Box\DuraParts\Finance\KPI Dashboard\inputs\YY.MM\
```

**Example for January 2026:** Create folder `inputs\26.01\`

**Required files:**
1. `DuraBrake Monthly Financial Package.xlsx` (or similar name)
2. `DuraBrake_Sales by Customer Detail.xlsx`
3. `DuraBrake_Income by Customer Summary.xlsx`
4. `Backlog_YYYY-MM-DD.xlsx` (e.g., `Backlog_2026-01-31.xlsx`)

**Where to find them:**
- Monthly Financial Package: Usually in `\Finance\Monthly Financials\YYYY-MM - Month\`
- Sales by Customer: Exported from QuickBooks or accounting system
- Income by Customer: Annual report from accounting system
- Backlog: Exported from order management system

---

## Step 2: Update Configuration

**Edit:** `generate_dashboard.py`

**Change line 14:**
```python
PERIOD = "26.01"  # Update to current month (YY.MM format)
```

**Period Format Examples:**
- January 2026 → `"26.01"`
- February 2026 → `"26.02"`
- December 2026 → `"26.12"`

**Save the file.**

---

## Step 3: Generate Dashboard Data

**Open Command Prompt:**
1. Press `Windows Key + R`
2. Type `cmd` and press Enter

**Run these commands:**
```bash
cd "C:\Users\scull\Box\DuraParts\Finance\KPI Dashboard"
python generate_dashboard.py
```

**You should see:**
- ✅ Step 1: Financial dashboard data generated
- ✅ Step 2: RFM analysis complete (227 customers)
- ✅ Step 3: Customer analysis complete
- ✅ Step 4: Backlog analysis complete
- ✅ "DASHBOARD GENERATION COMPLETE"

**If you see errors:**
- Check that all 4 input files are in the correct `inputs\YY.MM\` folder
- Verify file names match what the scripts expect
- Check that PERIOD in `generate_dashboard.py` matches your folder name

---

## Step 4: Upload to Cloud (Streamlit)

**Push updated data to GitHub:**

```bash
git add generated/
git commit -m "Add dashboard data for [Month Year]"
git push
```

**Example:**
```bash
git add generated/
git commit -m "Add dashboard data for January 2026"
git push
```

**What happens next:**
- Streamlit Cloud automatically detects the change
- Dashboard redeploys in 1-2 minutes
- New data appears on the live dashboard
- New month appears in Historicals tab

---

## Step 5: Verify Update

**Check the live dashboard:**

1. Go to your dashboard URL: `https://[your-app].streamlit.app`
2. Login with username and password
3. Check the **Historicals tab** - you should now see both old and new months
4. Click on the new month to verify data loaded correctly
5. Check all 6 tabs to ensure everything works

---

## 🔐 Managing Access

### View Current Users

**Who has access:**
- Anyone with the dashboard URL AND username/password
- Track manually (Streamlit free tier doesn't have user management)

**Best practice:**
- Keep a list of who you've shared credentials with
- Update monthly or quarterly

---

### Change Password

**When to change:**
- Monthly (recommended)
- After someone leaves the company
- If password is compromised
- Quarterly at minimum

**How to change:**

1. **Go to:** [https://share.streamlit.io](https://share.streamlit.io)
2. **Sign in** with your GitHub account
3. **Click on** your app: `scullerton/durabrake-dashboard`
4. **Click** "Settings" (gear icon)
5. **Click** "Secrets"
6. **Update the password line:**
   ```toml
   [auth]
   username = "durabrake"
   password = "YourNewPassword123!"
   ```
7. **Click "Save"**
8. **Wait 1-2 minutes** for redeployment
9. **Test the new password** on the live dashboard

**Password Requirements:**
- Use a strong password (mix of letters, numbers, symbols)
- Don't reuse passwords from other services
- Store in a password manager (LastPass, 1Password, etc.)

---

### Share Access with New Users

**What to share:**
1. Dashboard URL
2. Username: `durabrake`
3. Current password

**How to share (secure methods):**

**Option 1: Password Manager (Best)**
- Share via LastPass, 1Password, or similar
- Most secure method

**Option 2: Encrypted Email**
- Send URL and username in one email
- Send password in a separate email
- Better than sending together

**Option 3: In Person**
- Write down credentials
- Hand to person directly
- Have them change password immediately

**❌ Don't:**
- Post in Slack or Teams channels
- Send in unencrypted email together
- Write in public documents
- Share in group emails

**Instructions to send:**
```
DuraBrake Financial Dashboard Access

URL: https://[your-app].streamlit.app
Username: durabrake
Password: [current password]

This dashboard contains sensitive financial data.
Please do not share these credentials.
```

---

### Revoke Access

**If someone should no longer have access:**

1. **Change the password** (see "Change Password" above)
2. **Share new password** only with authorized users
3. **Update your access list**

**Note:** Streamlit free tier doesn't have individual user accounts, so changing the password is the only way to revoke access.

---

## 🔗 Dashboard URL

**Your live dashboard:**
```
https://[your-app-name].streamlit.app
```

**To find it if you forget:**
1. Go to [https://share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Your app will be listed with its URL

**Private link (not on website):**
- Share directly with authorized personnel
- Do not post publicly
- Consider using a URL shortener if needed (e.g., bit.ly with password protection)

---

## 📊 Dashboard Features

**6 Tabs Available:**
1. **Summary** - Key metrics, L3M comparison, Critical Notes & Action Items
2. **Product Details** - 6 product categories analyzed
3. **NWC Details** - Working capital ratios
4. **Customers** - Scorecard + actionable customer intelligence (see below)
5. **Order Backlog** - Age distribution, top customers, by rep/region
6. **Historicals** - View any prior month's dashboard

### Customers Tab — Scorecard Layout

The Customers tab is structured as an action-oriented scorecard, not just informational charts.

**Scorecard KPI Header (top of tab):**
- **Orders (L3M)** — Total unique orders with delta vs L12M quarterly average
- **Active Customers (L3M)** — Unique customers who placed orders, with new customer count
- **Avg Order Size (L3M)** — Revenue per order with delta vs L12M average
- **Customers Overdue** — Count of customers past their expected order interval
- **Cross-Sell Gaps** — Count of customers buying fewer than 4 product categories

**How KPIs are calculated:**
- "Order" = unique (customer, date) pair — a single order with 10 line items counts as 1 order
- "New customer" = ordered in L3M but had NO orders in the 12 months prior to L3M start
- "Overdue" = days since last order exceeds expected interval x 1.3, with 3+ prior orders required
- L3M = last 3 calendar months; L12M = trailing 12 months (not calendar year)

**Action Sections (shown first):**
1. **Customers Needing Attention** — Flagged by: Order Overdue, At Risk (RFM), Declining (>25% drop), Low Margin (<15% GP). Includes Suggested Action and Sales Rep columns.
2. **Overdue to Order** — Customers past their expected purchase interval. Split into truly overdue vs covered by active backlog orders.
3. **Cross-Sell Opportunities** — Customers buying from fewer product categories (Drums, Rotors, ADB, Hubs). Includes category coverage heatmap for top 15 customers.

**Detail Sections (collapsed by default):**
4. **Customer Performance Details** — Top 15 customers (L3M/L12M sales, GP margin, trend), RFM segmentation overview with segment cards and pie charts
5. **Product Category Mix** — Revenue breakdown by product category (Brake Drums, Balanced Drums, Steel Shell Drums, Brake Rotors, ADB Components, Hub Assemblies, 3rd Party, Other)

### Data Pipeline Outputs

Running `generate_dashboard.py` produces these files in `generated/YY.MM/`:

| File | Contents |
|------|----------|
| `dashboard_data.json` | Financial metrics, L3M comparisons, monthly time series, YTD, critical notes |
| `customer_dashboard_data.json` | Scorecard KPIs, top 15 customers, RFM segments, attention list, overdue customers, cross-sell opportunities, product categories, category heatmap |
| `backlog_dashboard_data.json` | Backlog summary, customer backlog with sales rep, age/ship date distributions, by rep/region |
| `rfm_analysis_results.csv` | Per-customer RFM scores and segments |
| `rfm_summary.json` | RFM segment summary statistics |
| `dashboard_notes.json` | Auto-generated critical notes and action items |

---

## 🛠️ Troubleshooting

### Problem: Dashboard shows old data

**Solution:**
```bash
# Make sure you pushed to GitHub
cd "C:\Users\scull\Box\DuraParts\Finance\KPI Dashboard"
git status  # Check if you have uncommitted changes
git push    # Push any pending changes
```

Wait 2-3 minutes for Streamlit to redeploy.

---

### Problem: "Unable to load dashboard data" error

**Solution:**
1. Check that `generated/YY.MM/` folder exists locally
2. Verify 4-5 JSON files are in the folder
3. Make sure you ran `git add generated/` and `git push`
4. Check GitHub repository to confirm files uploaded

---

### Problem: Login not working

**Solution:**
1. Verify you're using the correct username: `durabrake`
2. Try typing password manually (don't copy/paste)
3. Check Streamlit Cloud secrets are configured correctly
4. Clear browser cache and try again

---

### Problem: Missing data in a specific tab

**Solution:**
1. Check that the corresponding input file was in `inputs/YY.MM/`
2. Re-run `python generate_dashboard.py`
3. Look for error messages during generation
4. Verify the JSON file exists in `generated/YY.MM/`

---

### Problem: Git push asks for password

**Solution:**
GitHub now requires Personal Access Token instead of password:

1. Go to [GitHub Settings](https://github.com/settings/tokens)
2. Click "Developer settings" → "Personal access tokens" → "Tokens (classic)"
3. Click "Generate new token (classic)"
4. Give it a name: "DuraBrake Dashboard"
5. Check "repo" scope
6. Click "Generate token"
7. **Copy the token** (you won't see it again!)
8. Use this token as your password when git asks

**Store the token securely** - you'll need it for future pushes.

---

## 📋 Monthly Checklist

Use this checklist each month:

- [ ] Copy 4 input files to `inputs/YY.MM/`
- [ ] Update PERIOD in `generate_dashboard.py`
- [ ] Run `python generate_dashboard.py`
- [ ] Verify "DASHBOARD GENERATION COMPLETE" message
- [ ] Run `git add generated/`
- [ ] Run `git commit -m "Add dashboard data for [Month Year]"`
- [ ] Run `git push`
- [ ] Wait 2 minutes for Streamlit redeployment
- [ ] Test live dashboard
- [ ] Verify new month in Historicals tab
- [ ] Check all 6 tabs load correctly
- [ ] Review auto-generated Critical Notes & Action Items (edit if needed)
- [ ] Share dashboard link with authorized users (if needed)

---

## 🔄 Quarterly Tasks

Every 3 months:

- [ ] Change dashboard password
- [ ] Review who has access
- [ ] Clean up old input files (archive)
- [ ] Verify backups exist
- [ ] Test disaster recovery process

---

## 📞 Support Resources

**Streamlit Cloud Issues:**
- Dashboard: [https://share.streamlit.io](https://share.streamlit.io)
- Documentation: [https://docs.streamlit.io](https://docs.streamlit.io)

**GitHub Issues:**
- Repository: [https://github.com/scullerton/durabrake-dashboard](https://github.com/scullerton/durabrake-dashboard)
- GitHub Docs: [https://docs.github.com](https://docs.github.com)

**Local Dashboard Issues:**
- Check `README.md` for setup instructions
- Check `DEPLOYMENT_GUIDE.md` for detailed deployment info
- Review error messages from `generate_dashboard.py`

---

## 💾 Backup Strategy

**What to backup:**
- `inputs/` folder (all monthly raw data)
- `generated/` folder (processed dashboard data)
- Python scripts (already backed up in GitHub)

**Where to backup:**
- Box: Already backed up automatically
- GitHub: `generated/` folder is automatically backed up
- Consider: Additional backup to external drive quarterly

**Important:** Raw input files (inputs/ folder) are NOT in GitHub for security. Keep them backed up in Box.

---

## 🎯 Quick Reference

**Common Commands:**

```bash
# Navigate to dashboard folder
cd "C:\Users\scull\Box\DuraParts\Finance\KPI Dashboard"

# Generate dashboard
python generate_dashboard.py

# Push to cloud
git add generated/
git commit -m "Update dashboard for [Month]"
git push

# Check status
git status

# View dashboard locally (optional)
python -m streamlit run financial_dashboard.py
```

**Key Files:**
- `generate_dashboard.py` - Update PERIOD here
- `inputs/YY.MM/` - Put monthly input files here
- `generated/YY.MM/` - Generated dashboard data
- `financial_dashboard.py` - Dashboard application (don't edit)

**Key URLs:**
- Live Dashboard: `https://[your-app].streamlit.app`
- Streamlit Cloud: [https://share.streamlit.io](https://share.streamlit.io)
- GitHub Repo: [https://github.com/scullerton/durabrake-dashboard](https://github.com/scullerton/durabrake-dashboard)

---

**Last Updated:** March 2026
**Dashboard Version:** 1.2
**Current Period:** 26.01
