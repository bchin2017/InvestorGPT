# Changelog

All notable changes to InvestorGPT are recorded here.

## [2026-08-06] Structural overhaul — adopted intc-stock conventions

### Added
- `dashboard.py` — Multi-company Streamlit dashboard (INTC + MU)
  - Buffett Scorecard (10 principles, per-company fundamentals)
  - 10-Factor Buy/Sell Signal (RSI, Z-Score, MACD, Bollinger, ROC, etc.)
  - Decision Matrix (quality × timing → action)
  - ARIMA(2,1,2) + Monte Carlo (10,000 sims) ensemble forecast
  - Compare tab: normalized price performance + radar overlay
  - AI Advisor tab: GPT-4o or rule-based Buffett-style responses
- `scripts/refresh_data.py` — Multi-ticker Yahoo Finance data refresh (INTC, MU, extensible)
- `.cache/market_data_meta.json` — Refresh metadata (rows, date range, last close)
- `data/stock_history/` — Stock history CSVs, tracked by GitHub Actions
- `start_investor.bat` / `stop_investor.bat` / `_keeper.bat` — One-click launch/stop with watchdog
- `.github/workflows/daily-market-data-refresh.yml` — Automated daily data refresh (Mon–Fri 11:10 MYT)
- `docs/CHANGELOG.md`, `docs/CONTEXT_RESTORE.md`, `docs/HOW_TO_RUN.md`, `docs/SIGNAL_LOGIC.md`

### Changed
- `requirements.txt` — Expanded with Streamlit, statsmodels, plotly, openai, dotenv
- `.gitignore` — Updated: tracks `data/stock_history/` + `.cache/market_data_meta.json`;
  excludes `data/10k/` (large SEC filings, re-downloadable)

### Notes
- Architecture mirrors `intc-stock` workspace conventions, generalized for multi-company analysis
- Retains all prior work: `scripts/download_10k.py`, `scripts/generate_dashboard.py`,
  `webpage/index.html`, `firecrawl-practice/`
- Port: **8502** (no conflict with intc-stock 8501/8503)

---

## Template

```md
## [YYYY-MM-DD] Short title
### Added
### Changed
### Fixed
### Removed
```
