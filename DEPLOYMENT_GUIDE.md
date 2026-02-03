# DuraBrake Dashboard - Streamlit Cloud Deployment Guide

## Overview

This guide will help you deploy the DuraBrake Financial Dashboard to Streamlit Cloud, making it accessible from anywhere with a secure login.

**Final Result:** Your dashboard will be available at a URL like:
- `https://durabrake-dashboard.streamlit.app`
- Accessible from anywhere with username/password
- Can be linked from durabrake.com with a secret URL

---

## Prerequisites

Before you begin, you'll need:

1. ✅ **GitHub Account** (free) - [Sign up at github.com](https://github.com/signup)
2. ✅ **Streamlit Cloud Account** (free) - [Sign up at streamlit.io/cloud](https://streamlit.io/cloud)
3. ✅ **Dashboard data files** - Already generated in `generated/25.12/`

---

## Step 1: Create a GitHub Repository

### 1.1 Create New Repository

1. Go to [github.com](https://github.com) and log in
2. Click the **"+"** button (top right) → **"New repository"**
3. Fill in the details:
   - **Repository name:** `durabrake-dashboard`
   - **Description:** "DuraBrake Financial KPI Dashboard"
   - **Visibility:** ⚠️ **PRIVATE** (important for security)
   - ✅ Check "Add a README file"
4. Click **"Create repository"**

### 1.2 Install Git (if needed)

**Windows:**
- Download from [git-scm.com](https://git-scm.com/download/win)
- Install with default settings

**Verify installation:**
```bash
git --version
```

---

## Step 2: Prepare Files for Upload

### 2.1 Files That WILL Be Uploaded ✅

These files are safe to upload (no sensitive data):

```
durabrake-dashboard/
├── financial_dashboard.py          # Main dashboard app
├── requirements.txt                # Python dependencies
├── .gitignore                      # Files to exclude
├── .streamlit/
│   └── secrets.toml.example       # Example secrets (not actual secrets)
├── README.md                       # Documentation
└── generated/                      # Generated dashboard data
    └── 25.12/
        ├── dashboard_data.json
        ├── customer_dashboard_data.json
        ├── backlog_dashboard_data.json
        └── rfm_summary.json
```

### 2.2 Files That Will NOT Be Uploaded ❌

These files contain sensitive data and are excluded by `.gitignore`:

```
❌ inputs/                          # Raw Excel files with financial data
❌ *.xlsx                          # All Excel files
❌ scripts/                        # Analysis scripts (not needed for cloud)
❌ export_dashboard_data.py       # Data extraction script (local only)
❌ generate_dashboard.py          # Generation script (local only)
❌ .streamlit/secrets.toml        # Your actual password (will be configured in cloud)
```

---

## Step 3: Upload to GitHub

### 3.1 Initialize Git Repository

Open Command Prompt or Terminal and navigate to the KPI Dashboard folder:

```bash
cd "C:\Users\scull\Box\DuraParts\Finance\KPI Dashboard"
```

Initialize Git:

```bash
git init
git add financial_dashboard.py
git add requirements.txt
git add .gitignore
git add README.md
git add .streamlit/secrets.toml.example
git add generated/
```

**Important:** Do NOT add `inputs/` folder or `.xlsx` files!

### 3.2 Commit Files

```bash
git commit -m "Initial commit - DuraBrake dashboard for Streamlit Cloud"
```

### 3.3 Connect to GitHub

Replace `YOUR_GITHUB_USERNAME` with your actual GitHub username:

```bash
git branch -M main
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/durabrake-dashboard.git
git push -u origin main
```

You'll be prompted for your GitHub username and password.

**Note:** GitHub now requires a Personal Access Token instead of password:
1. Go to GitHub.com → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a name like "Streamlit Dashboard"
4. Check "repo" scope
5. Generate and copy the token
6. Use this token as your password when pushing

---

## Step 4: Deploy to Streamlit Cloud

### 4.1 Connect Streamlit to GitHub

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub (authorize Streamlit to access your repositories)
3. Click **"New app"**

### 4.2 Configure Deployment

Fill in the deployment settings:

- **Repository:** `YOUR_GITHUB_USERNAME/durabrake-dashboard`
- **Branch:** `main`
- **Main file path:** `financial_dashboard.py`
- **App URL:** Choose a custom URL like `durabrake-dashboard` (optional)

### 4.3 Configure Secrets (Password)

**IMPORTANT:** Before deploying, add your password to Streamlit secrets:

1. Click **"Advanced settings"** → **"Secrets"**
2. Add the following (copy/paste):

```toml
[auth]
username = "durabrake"
password = "Dashboard2025!"
```

3. Click **"Save"**

### 4.4 Deploy

1. Click **"Deploy!"**
2. Wait 2-3 minutes for deployment
3. Your dashboard will be live!

---

## Step 5: Test Your Dashboard

### 5.1 Access the Dashboard

Your dashboard will be available at:
- `https://durabrake-dashboard.streamlit.app` (or your custom URL)

### 5.2 Test Login

1. Open the URL in your browser
2. Enter credentials:
   - **Username:** `durabrake`
   - **Password:** `Dashboard2025!`
3. Verify all 6 tabs load correctly

### 5.3 Test from Different Devices

- Try accessing from your phone
- Try from another computer
- Share the link with a colleague to test

---

## Step 6: Add to DuraBrake.com Website

### Option A: Hidden Link (Recommended)

Add a non-obvious link to your website navigation or footer:

**Example URL structure:**
```
https://www.durabrake.com/internal-metrics
```

This page should redirect to:
```
https://durabrake-dashboard.streamlit.app
```

### Option B: Direct Link in Private Area

If you have a password-protected section on durabrake.com:
- Add the dashboard link there
- Example: "View Financial Dashboard →"

### Option C: Email Distribution

- Don't link publicly
- Email the Streamlit URL directly to authorized personnel
- Change password monthly for security

---

## Step 7: Update Dashboard Monthly

### 7.1 Generate New Data Locally

```bash
cd "C:\Users\scull\Box\DuraParts\Finance\KPI Dashboard"

# Update PERIOD in generate_dashboard.py
# Then run:
python generate_dashboard.py
```

### 7.2 Upload New Data to GitHub

```bash
git add generated/
git commit -m "Add dashboard data for [Month Year]"
git push
```

### 7.3 Automatic Redeployment

- Streamlit Cloud automatically detects the change
- Dashboard redeploys within 1-2 minutes
- New data appears in the Historicals tab

---

## Security Best Practices

### ✅ DO:

- ✅ Keep the GitHub repository **PRIVATE**
- ✅ Use strong, unique passwords
- ✅ Change passwords monthly
- ✅ Only share the URL with authorized personnel
- ✅ Upload only the `generated/` folder (no raw Excel files)
- ✅ Monitor who has access to the GitHub repo

### ❌ DON'T:

- ❌ Make the GitHub repository public
- ❌ Upload `inputs/` folder or raw Excel files
- ❌ Share passwords via email (use secure password manager)
- ❌ Post the dashboard URL on public websites
- ❌ Commit `.streamlit/secrets.toml` to GitHub

---

## Troubleshooting

### Problem: "Unable to load dashboard data"

**Solution:**
- Make sure `generated/25.12/` folder is in your GitHub repo
- Check that JSON files exist in the folder
- Verify PERIOD variable matches the folder name

### Problem: Login not working

**Solution:**
- Check Streamlit Cloud secrets are configured correctly
- Verify username/password in secrets match what you're entering
- Try clearing browser cache

### Problem: App shows old data

**Solution:**
- Make sure you pushed new data to GitHub (`git push`)
- Wait 1-2 minutes for automatic redeployment
- Try forcing a reboot in Streamlit Cloud dashboard

### Problem: Deployment failed

**Solution:**
- Check `requirements.txt` is in the repository
- Verify `financial_dashboard.py` is in the root folder
- Check Streamlit Cloud logs for error messages

---

## Changing Your Password

### Method 1: Update in Streamlit Cloud (Recommended)

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click on your app → **"Settings"** → **"Secrets"**
3. Update the password in the secrets
4. Click **"Save"**
5. App will automatically redeploy

### Method 2: Update in Code (Not Recommended)

If you don't use secrets, you can update the password in `financial_dashboard.py`:

```python
DASHBOARD_PASSWORD_HASH = hashlib.sha256("YourNewPassword".encode()).hexdigest()
```

Then commit and push to GitHub.

---

## Cost

**Streamlit Cloud Free Tier:**
- ✅ Free forever
- ✅ 1 private app
- ✅ Unlimited viewers
- ✅ Community support

**If you need more:**
- Streamlit Cloud Pro: $20/month per creator
- Multiple private apps
- Custom domain (dashboard.durabrake.com)
- Better performance

---

## Support

**Streamlit Documentation:**
- [Streamlit Cloud Docs](https://docs.streamlit.io/streamlit-community-cloud)
- [Deployment Tutorial](https://docs.streamlit.io/streamlit-community-cloud/get-started)

**GitHub Help:**
- [GitHub Docs](https://docs.github.com)

**For Dashboard Issues:**
- Check `README.md` in the repository
- Review Streamlit Cloud logs
- Contact your IT department

---

## Summary Checklist

Before going live, verify:

- [ ] GitHub repository is **PRIVATE**
- [ ] `.gitignore` excludes sensitive files
- [ ] Streamlit Cloud secrets configured with password
- [ ] Dashboard loads and shows data
- [ ] Login works with correct credentials
- [ ] All 6 tabs functional
- [ ] Tested from multiple devices
- [ ] Password shared securely with authorized users
- [ ] URL added to durabrake.com (if applicable)
- [ ] Monthly update process documented

---

**Your dashboard is now live and accessible from anywhere! 🎉**

Access it at: `https://durabrake-dashboard.streamlit.app` (or your custom URL)
