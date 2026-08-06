# InvestorGPT – Project Progress

## Status: In Progress — Phase 2 (Streamlit Dashboard + Automation)

**Last updated:** 2026-08-06

---

## Completed

### Phase 1 — Environment & Static Dashboard
- [x] Project workspace (`InvestorGPT.code-workspace`)
- [x] `requirements.txt` — expanded with Streamlit, statsmodels, plotly, openai, dotenv
- [x] `.env` for API keys (gitignored)
- [x] `scripts/download_10k.py` — downloads Intel & Micron 10-K HTML from SEC EDGAR
- [x] Downloaded 6 filings: Intel FY2022/FY2023/FY2024, Micron FY2023/FY2024/FY2025
- [x] `scripts/generate_dashboard.py` — extracts financials from 10-K HTML
- [x] `webpage/index.html` — static dashboard (Chart.js, Bootstrap)
- [x] `firecrawl-practice/practice.py` — beginner firecrawl exercise

### Phase 2 — Streamlit Dashboard + intc-stock Architecture (2026-08-06)
- [x] `dashboard.py` — multi-company Streamlit dashboard (INTC + MU)
  - [x] 10-Factor Buy/Sell Signal (RSI, Bollinger, Z-Score, MACD, MA, Vol, ROC)
  - [x] Buffett Scorecard (10 principles, per-company FUNDAMENTALS)
  - [x] Decision Matrix (quality × timing → action with colour)
  - [x] ARIMA(2,1,2) + Monte Carlo ensemble forecast (18 months)
  - [x] Compare tab: normalised price + dual radar overlay
  - [x] AI Advisor tab: GPT-4o or rule-based Buffett responses
- [x] `scripts/refresh_data.py` — multi-ticker Yahoo Finance refresh (INTC, MU, extensible)
- [x] `.cache/market_data_meta.json` — refresh metadata pattern
- [x] `data/stock_history/` — CSV store for stock history (tracked by git)
- [x] `start_investor.bat` / `stop_investor.bat` / `_keeper.bat` — one-click launch with watchdog
- [x] `.github/workflows/daily-market-data-refresh.yml` — Mon–Fri 11:10 MYT auto-refresh
- [x] `docs/CHANGELOG.md`, `CONTEXT_RESTORE.md`, `HOW_TO_RUN.md`, `SIGNAL_LOGIC.md`

---

## Known Issues / Remaining Work

### Static Dashboard Data Quality (webpage/index.html)
- [ ] Intel Gross Margin — label in XBRL filing not yet matched
- [ ] Micron Net Income FY2024 — regex picks up wrong value
- [ ] Stock price chart — yfinance silent failure needs debugging

### Phase 3 — RAG Chatbot (Not Started)
- [ ] PDF/HTML ingestion → clean Markdown chunks
- [ ] Embedding + vector store (FAISS)
- [ ] LLM integration (Azure OpenAI GPT-4o)
- [ ] Chat UI (Streamlit tab or standalone page)
- [ ] Citation-backed answer generation
- [ ] Company comparison via RAG

### Phase 4 — Enhancements
- [ ] Add AMD, NVDA tickers to dashboard
- [ ] Quarterly earnings tracking
- [ ] P/E, P/S, EV/EBITDA valuation ratios
- [ ] Export report (PDF)

---

## Architecture — Current

```
start_investor.bat
  → scripts/refresh_data.py  (Yahoo Finance → data/stock_history/)
  → _keeper.bat
       → streamlit run dashboard.py (port 8502)
            Tabs: Price+Signal | Buffett Score | Fundamentals | Forecast | Compare | AI Advisor
```

## Architecture — Planned (Phase 3 RAG)

```
User → Streamlit Chat UI
          ↓
       GPT-4o (Azure OpenAI)
          ↓
    Retrieval Layer (LangChain / LlamaIndex)
          ↓
    FAISS Vector DB ← 10-K Markdown chunks
```

---

## Data Sources

| Company | Filing | Filed | Status |
|---|---|---|---|
| Intel | FY2022 10-K | Jan 2023 | Downloaded |
| Intel | FY2023 10-K | Jan 2024 | Downloaded |
| Intel | FY2024 10-K | Jan 2025 | Downloaded |
| Micron | FY2023 10-K | Oct 2023 | Downloaded |
| Micron | FY2024 10-K | Oct 2024 | Downloaded |
| Micron | FY2025 10-K | Oct 2025 | Downloaded |
