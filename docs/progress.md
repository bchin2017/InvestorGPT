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

### Phase 3 — Intelligent RAG System / SemiconInvest AI (Completed — 2026-08-06)

**Index & Crawling**
- [x] `scripts/crawl_sources.py` — Firecrawl crawler for 21 financial URLs (6 source types)
- [x] `scripts/build_index.py` — Chunking (500–800 tokens, overlap) + text-embedding-3-large + FAISS
- [x] 10-K HTML ingestion (BeautifulSoup) — 6 filings (Intel + Micron FY2022–FY2024)
- [x] All 21 sources crawled → `data/crawled/` (21 .md + 21 .meta.json)
- [x] FAISS index built: **754 vectors**, dim=3072 → `data/rag_index/`
- [x] Metadata: source, company, ticker, doc_type, fiscal_year, section, URL

**RAG Server (`scripts/rag_server.py`)**
- [x] Flask REST API on port 8503 with CORS
- [x] `/chat` — RAG-only (FAISS + GPT-4o)
- [x] `/chat/general` — Intelligent query router
- [x] `/analytics` — Direct CSV analytics (no LLM call)
- [x] `/health` — server status + API key check
- [x] `/data-sources` — full catalogue with chunk/row counts
- [x] `lookup_stock_price()` — date-regex → nearest-day CSV → OHLCV string

**Intelligent Query Router**
- [x] `classify_query()` → routes to `csv_price | csv_analytics | faiss | mixed`
- [x] `detect_tickers_in_query()` — INTC/MU from natural language
- [x] `detect_year_in_query()` — fiscal years 2019–2026 from question text
- [x] `compute_stock_analytics()` — Total Return, CAGR, Volatility, Max Drawdown, MA50/MA200
- [x] Multi-ticker side-by-side comparison from CSV (INTC vs MU example: −25% vs +67.1% in 2023–2024)
- [x] `/chat/general` response includes `query_type`, `tickers_detected`, `years_detected`

**RAG Chatbot (`scripts/rag_chatbot.py`)**
- [x] `retrieve(..., year=)` — fiscal year filter on FAISS chunk metadata
- [x] Over-fetch 5× when filters active to maintain top_k after filtering
- [x] Confidence scoring per chunk (high ≥ 0.70, medium ≥ 0.40, low < 0.40)
- [x] `format_context()` — Year, Section, Confidence label per chunk
- [x] Low-confidence caveat injected into GPT-4o system message (top score < 0.3)

**AI Chat Tab (`webpage/index.html`)**
- [x] 3-mode toggle: Server AI / Direct API / RAG Only
- [x] Provider: OpenAI / Gemini; Model selector
- [x] API Key auto-validate on paste (debounced), clear button with auto-fallback
- [x] Temperature, Max Tokens, Top P, CORS Relay (all in `localStorage`)
- [x] Network proxy auto-detection
- [x] Auto-connect: picks best mode on page load

**Pending — Next Phase**
- [ ] Add 10-Q filings to FAISS index (more granular quarterly data)
- [ ] Add earnings call transcripts as a crawled source
- [ ] Executive Summary generator (Bull/Bear/SWOT) from retrieved evidence only
- [ ] Trend analysis queries: "How has Intel AI strategy evolved 2022–2024?"
- [ ] Company comparison via RAG in Streamlit dashboard tab

### Phase 4 — Enhancements
- [ ] Add AMD, NVDA tickers to dashboard
- [ ] Quarterly earnings tracking
- [ ] P/E, P/S, EV/EBITDA valuation ratios
- [ ] Export report (PDF)

### Phase 5 — Data Retention & Crawling Strategy (Planned)

**Objective:** Optimize Firecrawl ingestion, FAISS indexing, retrieval quality, storage usage, and response performance.

#### Data Time Horizons

| Source | Horizon | Reason |
|---|---|---|
| Stock Price CSV (INTC 1980→, MU 1984→) | Full history | 11-12k rows, trivial for Pandas. Used for price lookup, returns, CAGR, volatility, drawdown. |
| SEC 10-K Filings | Latest 4-5 years (FY2022–FY2025+) | Investor focus on recent strategy, risks, AI, manufacturing. |
| Macrotrends Financials (Rev, EPS, NI, CF, BS) | Last 10 years | Long-term trend analysis without excessive volume. |
| StockAnalysis Financials (Annual + Quarterly) | Last 10 years | Trend and comparison analysis. |
| CompaniesMarketCap (Market cap, rankings) | Last 10 years | Long-term valuation context. |
| Investor Relations (Presentations, earnings, PR) | Latest 2 years | Older IR content adds retrieval noise. |

#### FAISS Best Practices

**Include in FAISS:**
- SEC 10-K filings, earnings materials, investor presentations
- Strategy documents, risk factors, financial summaries
- AI roadmap, foundry strategy, HBM market discussions

**Do NOT include in FAISS:**
- Daily stock prices, OHLCV records, large CSV datasets, raw time-series

**Target FAISS size:** 1,000–2,000 chunks (current: ~754)

#### Query Routing Improvements

| Query Type | Route | Examples |
|---|---|---|
| Stock price | CSV only | "Intel closing price 2025-01-06", "52-week high" |
| Business | FAISS only | "Intel AI strategy", "Micron risk factors" |
| Mixed | CSV + FAISS | "Stock after AI announcement", "HBM impact on price" |

#### Metadata per Chunk

```json
{
  "source": "SEC 10-K",
  "company": "Intel",
  "ticker": "INTC",
  "year": 2024,
  "section": "Risk Factors",
  "page": 42,
  "url": "...",
  "doc_type": "10-K"
}
```

#### Known Gaps
- [ ] 10-year stock price history missing from RAG context (CSV exists but not surfaced in all queries)
- [ ] SEC 10-Q filings not yet indexed
- [ ] SEC 8-K filings not yet indexed
- [ ] Earnings call transcripts not yet crawled
- [ ] Insider trading (Form 4) not tracked
- [ ] Dividend history not tracked

#### Future Enhancements
- [ ] Knowledge graph for entity relationships
- [ ] Financial analytics engine (structured queries)
- [ ] Bull/Bear case generation from retrieved evidence
- [ ] Automated investment thesis generation
- [ ] Hybrid architecture: CSV/SQL for numerical data + FAISS for documents + GPT-4o synthesis with citations

---

## Architecture — Current

```
start_investor.bat
  → scripts/refresh_data.py  (Yahoo Finance → data/stock_history/)
  → _keeper.bat
       → streamlit run dashboard.py (port 8502)
            Tabs: Price+Signal | Buffett Score | Fundamentals | Forecast | Compare | AI Advisor
```

## Architecture — Phase 3 RAG (Implemented)

```
User → rag_chatbot.py (interactive or CLI)
          ↓
       GPT-4o (OpenAI)
          ↓
    FAISS Retrieval (cosine similarity, top-k, metadata filters)
          ↓
    FAISS Vector DB  ←  build_index.py
       (text-embedding-3-large, 3072-dim)
          ↓
    Chunked Documents (500-800 tokens, overlap)
          ↓
    crawl_sources.py (Firecrawl → data/crawled/)
    +  10-K HTML (data/10k/)
```

---

## Data Sources

### SEC EDGAR 10-K Filings

| Company | Filing | Filed | Status |
|---|---|---|---|
| Intel | FY2022 10-K | Jan 2023 | Downloaded |
| Intel | FY2023 10-K | Jan 2024 | Downloaded |
| Intel | FY2024 10-K | Jan 2025 | Downloaded |
| Micron | FY2023 10-K | Oct 2023 | Downloaded |
| Micron | FY2024 10-K | Oct 2024 | Downloaded |
| Micron | FY2025 10-K | Oct 2025 | Downloaded |

### Firecrawl Web Sources (Phase 3)

| Source | URLs | Data | Companies |
|---|---|---|---|
| Macrotrends | 8 | Revenue, EPS, net income, cash flow, balance sheet | INTC, MU |
| StockAnalysis | 4 | Annual & quarterly financial statements | INTC, MU |
| CompaniesMarketCap | 2 | Market cap history & rankings | INTC, MU |
| Intel IR | 3 | Financial info, SEC filings, press releases | INTC |
| Micron IR | 2 | Quarterly results, news releases | MU |
| Yahoo Finance | 2 | Quote summaries | INTC, MU |
