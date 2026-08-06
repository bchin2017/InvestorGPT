# Context Restore — InvestorGPT (Full Recovery Spec)

**Updated:** 2026-08-06

---

## 1) Project Identity

- **Project root:** `c:\Users\bhoe\VS Code\InvestorGPT\`
- **Primary dashboard:** `dashboard.py` (Streamlit, port **8502**)
- **Static dashboard (legacy):** `webpage/index.html` (Chart.js, no server)
- **Tickers:** INTC (Intel Corporation), MU (Micron Technology)
- **Workspace file:** `InvestorGPT.code-workspace`

---

## 2) Canonical Folder/File Layout

```
InvestorGPT/
├─ .github/workflows/daily-market-data-refresh.yml
├─ .cache/market_data_meta.json          ← generated, tracked by git
├─ data/
│  ├─ stock_history/
│  │  ├─ intc_history.csv                ← generated, tracked by git
│  │  └─ mu_history.csv                  ← generated, tracked by git
│  └─ 10k/                               ← gitignored (large, re-downloadable)
│     ├─ Intel_10K_2023_2023-01-27.html
│     ├─ Intel_10K_2024_2024-01-26.html
│     ├─ Intel_10K_2025_2025-01-31.html
│     ├─ Micron_10K_2023_2023-10-06.html
│     ├─ Micron_10K_2024_2024-10-04.html
│     └─ Micron_10K_2025_2025-10-03.html
├─ docs/
│  ├─ README.md
│  ├─ HOW_TO_RUN.md
│  ├─ SIGNAL_LOGIC.md
│  ├─ CONTEXT_RESTORE.md     ← this file
│  ├─ CHANGELOG.md
│  └─ progress.md
├─ firecrawl-practice/
│  └─ practice.py
├─ scripts/
│  ├─ refresh_data.py        ← Yahoo Finance multi-ticker refresh
│  ├─ download_10k.py        ← SEC EDGAR 10-K downloader
│  └─ generate_dashboard.py  ← Static HTML generator
├─ webpage/
│  └─ index.html
├─ dashboard.py              ← Main Streamlit app
├─ start_investor.bat
├─ _keeper.bat
├─ stop_investor.bat
├─ requirements.txt
├─ .env                      ← gitignored
├─ .gitignore
└─ InvestorGPT.code-workspace
```

---

## 3) Startup Architecture

### `start_investor.bat`
1. Resolves valid Python (validates `.venv` or falls back to system `python`)
2. Runs `scripts/refresh_data.py` in background → logs to `refresh_startup.log`
3. Kills any existing process on port `8502`
4. Starts `_keeper.bat` minimized
5. Waits up to 40s for port `8502` LISTENING
6. Opens `http://localhost:8502`

### `_keeper.bat`
- Window title: `InvestorGPT Dashboard`
- Loops forever: runs `dashboard.py` on port 8502, restarts on exit

### `stop_investor.bat`
- Kills window `InvestorGPT Dashboard`
- Kills any process on port 8502

---

## 4) Environment Variables (`.env`)

```
OPENAI_API_KEY=sk-...        # GPT-4o responses in AI Advisor tab (optional)
FIRECRAWL_API_KEY=fc-...     # firecrawl-practice/ scripts
```

---

## 5) GitHub Actions

- **Workflow:** `.github/workflows/daily-market-data-refresh.yml`
- **Schedule:** Mon–Fri, 03:10 UTC (11:10 MYT)
- **What it does:** `python scripts/refresh_data.py --force --tickers INTC MU`
- **Commits:** `data/stock_history/*.csv` + `.cache/market_data_meta.json`
- **Manual trigger:** GitHub → Actions → Daily Market Data Refresh → Run workflow

---

## 6) Key Data Sources

| Source | What | How |
|---|---|---|
| Yahoo Finance Chart API | INTC, MU daily OHLCV | `scripts/refresh_data.py` |
| SEC EDGAR | Intel & Micron 10-K HTML | `scripts/download_10k.py` |
| OpenAI GPT-4o | AI Advisor responses | `.env OPENAI_API_KEY` |

---

## 7) Port Map (all workspaces)

| App | Port |
|---|---|
| **InvestorGPT** | **8502** |
| intc-stock desktop | 8501 |
| intc-stock phone | 8503 |

---

## 8) Dashboard Architecture (dashboard.py)

```
Sidebar: ticker selector (INTC / MU) + compare toggle + cache status
  ↓
Tabs:
  📈 Price & Signal  — 3Y price chart, MA50/MA200, 10-factor signal time series
  🏛️ Buffett Score   — 10-principle scorecard table, radar chart, decision matrix
  📋 Fundamentals    — Revenue/NI/GM bar charts, EPS/ROE/D-E table (10-K data)
  🔮 Forecast        — ARIMA + MC fan chart, bear/base/bull metrics
  ⚖️ Compare         — Side-by-side metrics, normalized performance, radar overlay
  🤖 AI Advisor      — GPT-4o or rule-based Buffett-style Q&A
```
