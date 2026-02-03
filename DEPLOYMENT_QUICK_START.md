# Quick Start: Deploy to Streamlit Cloud

## 5-Minute Deployment Guide

### Step 1: Create GitHub Account & Repository (2 minutes)

1. Sign up at [github.com](https://github.com/signup)
2. Create new **PRIVATE** repository named `durabrake-dashboard`

### Step 2: Upload Files (2 minutes)

```bash
cd "C:\Users\scull\Box\DuraParts\Finance\KPI Dashboard"

git init
git add financial_dashboard.py requirements.txt .gitignore README.md generated/
git commit -m "Initial deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/durabrake-dashboard.git
git push -u origin main
```

**Note:** Replace `YOUR_USERNAME` with your GitHub username

### Step 3: Deploy to Streamlit Cloud (1 minute)

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click "New app"
4. Select your repository: `durabrake-dashboard`
5. Main file: `financial_dashboard.py`
6. Click "Advanced settings" → "Secrets" → Add:

```toml
[auth]
username = "durabrake"
password = "Dashboard2025!"
```

7. Click "Deploy!"

### Done! ✅

Your dashboard is live at: `https://durabrake-dashboard.streamlit.app`

**Login with:**
- Username: `durabrake`
- Password: `Dashboard2025!`

---

## Monthly Updates (30 seconds)

```bash
# After running generate_dashboard.py locally:
git add generated/
git commit -m "Update for [Month Year]"
git push
```

Streamlit Cloud auto-redeploys within 2 minutes!

---

## Need Help?

See full guide: `DEPLOYMENT_GUIDE.md`
