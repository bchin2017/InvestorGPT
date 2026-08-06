# InvestorGPT — How to Run

**Last updated:** 2026-08-06

---

## Folder Guide

| File / Folder | Purpose |
|---|---|
| `dashboard.py` | Streamlit dashboard — INTC + MU, Buffett scoring, signals, forecasts |
| `scripts/refresh_data.py` | Fetch/cache INTC + MU stock history from Yahoo Finance |
| `scripts/download_10k.py` | Download Intel & Micron 10-K HTML from SEC EDGAR |
| `scripts/generate_dashboard.py` | Regenerate static `webpage/index.html` from 10-K data |
| `start_investor.bat` | One-click launcher (port 8502) |
| `_keeper.bat` | Watchdog — auto-restarts Streamlit on crash |
| `stop_investor.bat` | One-click stop |
| `webpage/index.html` | Static HTML dashboard (no server required) |

---

## Starting the Streamlit Dashboard

Double-click **`start_investor.bat`**

What it does:
1. Runs `scripts/refresh_data.py` in background (refreshes INTC + MU data from Yahoo)
2. Logs refresh output to `refresh_startup.log`
3. Kills any existing process on port `8502`
4. Starts `_keeper.bat` minimized (watchdog loop)
5. Waits up to 40 seconds for port `8502` LISTENING
6. Opens browser at `http://localhost:8502`

## Stopping the Dashboard

Double-click **`stop_investor.bat`**

---

## Refreshing Stock Data Manually

```powershell
cd "c:\Users\bhoe\VS Code\InvestorGPT"
python scripts/refresh_data.py --force
```

Add tickers beyond INTC and MU:

```powershell
python scripts/refresh_data.py --tickers INTC MU AMD NVDA --force
```

## Re-downloading 10-K Filings

```powershell
python scripts/download_10k.py
```

Downloads latest Intel and Micron 10-K HTML files to `data/10k/`.

## Regenerating the Static Dashboard

```powershell
python scripts/generate_dashboard.py
```

Reads `data/10k/*.html`, fetches stock prices via yfinance, writes `webpage/index.html`.

---

## First-Time Setup

```powershell
cd "c:\Users\bhoe\VS Code\InvestorGPT"
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## Environment Variables

Create `.env` in the project root:

```
OPENAI_API_KEY=sk-...        # Optional — enables GPT-4o in the AI Advisor tab
FIRECRAWL_API_KEY=fc-...     # For firecrawl-practice/ scripts
```

---

## GitHub Actions Automation

Workflow: `.github/workflows/daily-market-data-refresh.yml`

- Runs automatically **Mon–Fri at 03:10 UTC** (11:10 MYT)
- Executes `python scripts/refresh_data.py --force --tickers INTC MU`
- Commits updated `data/stock_history/*.csv` and `.cache/market_data_meta.json`

To trigger manually: **GitHub → Actions → Daily Market Data Refresh → Run workflow**

---

## Port Reference

| Dashboard | Port |
|---|---|
| **InvestorGPT** | **8502** |
| intc-stock (desktop) | 8501 |
| intc-stock (phone) | 8503 |

---

## Troubleshooting: Python Not Found After PC Format

```powershell
python -m streamlit --version
.venv\Scripts\python.exe -m streamlit --version
```

If the first fails but the second works: PATH/venv mismatch.
The batch files auto-detect and fall back to system `python`.

### Known-good manual launch

```powershell
cd "c:\Users\bhoe\VS Code\InvestorGPT"
python -m streamlit run dashboard.py --server.port 8502 --server.headless true
```

---

## Git Sync

```powershell
cd "c:\Users\bhoe\VS Code\InvestorGPT"
git fetch origin
git pull --rebase origin main
git push origin main
```

### First-time git setup (new machine)

```powershell
git init
git branch -M main
git add .
git commit -m "initial investorgpt setup"
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```
