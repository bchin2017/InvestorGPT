# InvestorGPT

Warren Buffett-style Streamlit dashboard for semiconductor investing — Intel (INTC) and Micron (MU).

## Quick Start

```powershell
cd "c:\Users\bhoe\VS Code\InvestorGPT"
.\start_investor.bat
```

Open: `http://localhost:8502`

## Dashboard Features

- **Price & Signal** — 3-year chart with MA50/MA200, 10-factor buy/sell signal time series
- **Buffett Score** — 10-principle scorecard (Intrinsic Value, Moat, ROE, D/E, etc.) + radar chart
- **Fundamentals** — Annual revenue, net income, gross margin from SEC 10-K filings
- **Forecast** — ARIMA + Monte Carlo ensemble (18-month horizon)
- **Compare** — INTC vs MU side-by-side: metrics, normalised performance, radar overlay
- **AI Advisor** — GPT-4o (or rule-based fallback) Buffett-style Q&A

## Documentation

- Run guide: [`docs/HOW_TO_RUN.md`](docs/HOW_TO_RUN.md)
- Signal/score logic: [`docs/SIGNAL_LOGIC.md`](docs/SIGNAL_LOGIC.md)
- Context restore: [`docs/CONTEXT_RESTORE.md`](docs/CONTEXT_RESTORE.md)
- Changelog: [`docs/CHANGELOG.md`](docs/CHANGELOG.md)

## Automation

- Daily workflow: `.github/workflows/daily-market-data-refresh.yml`
- Data refresh: `scripts/refresh_data.py` (INTC + MU, Yahoo Finance)
- 10-K download: `scripts/download_10k.py` (SEC EDGAR)

## Port

| App | Port |
|---|---|
| InvestorGPT | **8502** |
| intc-stock (desktop) | 8501 |
| intc-stock (phone) | 8503 |
