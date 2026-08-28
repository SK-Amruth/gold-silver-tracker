# Gold & Silver Price Tracker

A fully automated, **100% free** DevOps pipeline that:

- 📧 Sends a daily email with gold & silver prices (USD + INR)
- 🌐 Publishes a live-updating website with today's rates and a price trend chart
- ⚙️ Runs entirely on free-tier infrastructure — no servers, no paid APIs, no hosting bills

**Live site:** `https://<your-github-username>.github.io/gold-silver-tracker/`

---

## Architecture

```
                ┌─────────────────────────┐
                │   GitHub Actions (cron)  │   runs daily at 8:00 AM IST
                │   .github/workflows/     │
                └───────────┬─────────────┘
                            │
                            ▼
                ┌─────────────────────────┐
                │ scripts/fetch_and_notify│
                │ .py                     │
                └───────────┬─────────────┘
                            │
              ┌─────────────┼──────────────┐
              ▼             ▼              ▼
     gold-api.com     Gmail SMTP     data/history.csv
   (free, no key)    (email out)     docs/prices.json
                                      docs/history.csv
                            │
                            ▼
                 ┌─────────────────────┐
                 │   GitHub Pages       │
                 │   (docs/ folder)     │
                 └─────────────────────┘
```

Every day, GitHub Actions:
1. Fetches live gold (XAU) and silver (XAG) spot prices in USD and INR from [gold-api.com](https://gold-api.com) (free, no API key required).
2. Converts troy-ounce prices into price-per-gram and price-per-10-grams.
3. Emails a formatted price summary to the configured recipient list via Gmail SMTP.
4. Appends the day's prices to `data/history.csv` and updates `docs/prices.json` / `docs/history.csv`.
5. Commits the updated files back to the repo, which GitHub Pages automatically redeploys.

---

## DevOps concepts demonstrated

| Concept | Where |
|---|---|
| CI/CD | GitHub Actions workflow — scheduled + on-demand pipeline |
| Infrastructure as Code | The workflow YAML and Pages config are versioned in the repo |
| Secrets Management | Gmail credentials & recipient list stored as GitHub Actions Secrets |
| GitOps | `main` branch is the single source of truth for both data and the deployed site |
| Automation / Scheduling | Cron-based trigger, no manual intervention needed |
| Error Handling | Script degrades gracefully — a failed email doesn't block the site update |
| Static Hosting | GitHub Pages serves `docs/` with zero server management |
| Observability (basic) | Workflow run logs in the Actions tab act as a lightweight audit trail |

---

## Setup

### 1. Prerequisites
- Git
- Python 3.10+ (`pip install requests`)
- A GitHub account
- A Gmail account with an **App Password** (Google Account → Security → 2-Step Verification → App Passwords)

### 2. Clone & push to your own repo
```bash
git init
git add .
git commit -m "Initial commit: gold/silver price tracker"
git branch -M main
git remote add origin https://github.com/<your-username>/gold-silver-tracker.git
git push -u origin main
```

### 3. Add GitHub Actions Secrets
Go to **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value |
|---|---|
| `GMAIL_USER` | your Gmail address |
| `GMAIL_APP_PASSWORD` | 16-character Gmail App Password |
| `EMAIL_RECIPIENTS` | comma-separated emails, e.g. `a@x.com,b@y.com` |

### 4. Enable GitHub Pages
**Settings → Pages → Source** → select `Deploy from a branch` → branch `main`, folder `/docs`.

### 5. Trigger the first run
**Actions tab → Daily Gold & Silver Price Update → Run workflow** (manual trigger), or wait for the 8:00 AM IST schedule.

After the first run, `docs/prices.json` and `docs/history.csv` will be populated and the site will show live data.

---

## Local testing

```bash
pip install requests
export GMAIL_USER="you@gmail.com"
export GMAIL_APP_PASSWORD="xxxxxxxxxxxxxxxx"
export EMAIL_RECIPIENTS="you@gmail.com"
python scripts/fetch_and_notify.py
```

If the Gmail env vars are not set, the script still updates `data/history.csv` and `docs/prices.json` — it just skips sending the email.

---

## Project structure

```
gold-silver-tracker/
├── .github/workflows/daily-update.yml   # scheduled CI/CD pipeline
├── scripts/fetch_and_notify.py          # fetch prices, email, update data
├── docs/                                # served by GitHub Pages
│   ├── index.html
│   ├── prices.json                      # generated
│   └── history.csv                      # generated
├── data/
│   └── history.csv                      # generated (full history)
└── README.md
```

---

## Data source
Prices via the free [gold-api.com](https://gold-api.com) REST API (no key, no rate limit on the real-time endpoint).
