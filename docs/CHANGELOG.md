# Changelog

All notable changes to InvestorGPT are recorded here.

---

## [2026-08-06] Phase 3 Upgrade — Intelligent RAG System (SemiconInvest AI)

### Architecture Overview
Full hybrid retrieval system: **Intelligent Query Router → CSV Analytics OR FAISS RAG → GPT-4o synthesis**.
Server: `http://localhost:8503`. Front-end: `webpage/index.html` AI Chat tab.

---

### 1. AI Chat Tab — `webpage/index.html`

**3-Mode Toggle**

| Mode | Description |
|------|-------------|
| Server AI | Uses `.env` `OPENAI_API_KEY` on Flask server — no browser key needed |
| Direct API | User pastes key; calls OpenAI/Gemini directly from the browser |
| RAG Only | Uses `/chat` endpoint; pure FAISS retrieval, no LLM synthesis |

**Settings Panel** (all persisted to `localStorage`)
- Provider dropdown: OpenAI / Gemini
- API Key field with auto-validate (400 ms debounce) → ✅/❌ feedback + auto mode-switch on paste/clear
- Model selector, Temperature slider (0–2), Max Tokens, Top P slider
- Network Proxy auto-detect (read-only) + CORS Relay field

**Auto-connect logic**: On page load checks server → if up defaults to Server AI; if API key saved in localStorage defaults to Direct API.

---

### 2. Flask RAG Server — `scripts/rag_server.py`

**Endpoints**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat` | RAG-only (FAISS retrieval + GPT-4o, no routing logic) |
| POST | `/chat/general` | **Intelligent router** — routes query to correct data source |
| POST | `/analytics` | Direct CSV analytics, no LLM call required |
| GET | `/health` | Server status + API key presence flag |
| GET | `/data-sources` | Full catalogue of all sources with chunk/row counts |

**Intelligent Query Router (`classify_query()`)**

Three keyword sets score each incoming question:

| `query_type` | Trigger Keywords (examples) | Route | Benefit |
|---|---|---|---|
| `csv_price` | "close price", "stock price", "price on" + date | CSV lookup only | Exact OHLCV, zero FAISS cost |
| `csv_analytics` | "cagr", "drawdown", "volatility", "total return", "moving average", "outperform" | `compute_stock_analytics()` | Computed metrics, zero FAISS cost |
| `faiss` | "strategy", "risk factor", "r&d", "hbm", "foundry", "revenue", "net income" | FAISS retrieval only | No CSV noise in context |
| `mixed` | No strong signal | CSV price lookup + FAISS | Full context |

**Additional routing helpers**
- `detect_tickers_in_query()` — extracts INTC/MU from natural language (`\bmu\b` regex avoids false positives)
- `detect_year_in_query()` — extracts fiscal years 2019–2026 from question text

**Response JSON** — new fields added to `/chat/general`:
```json
{
  "answer": "...",
  "citations": "stock_history — Computed from CSV",
  "mode": "server",
  "query_type": "csv_analytics",
  "tickers_detected": ["INTC"],
  "years_detected": ["2022", "2024"]
}
```

---

### 3. Financial Analytics Layer — `compute_stock_analytics()`

Computed directly from stock CSVs, no LLM token cost:

| Metric | Formula |
|--------|---------|
| Total Return | `(end − start) / start × 100` |
| CAGR | `(end/start)^(1/n_years) − 1` |
| Annualized Volatility | `daily_returns.std() × √252 × 100` |
| Maximum Drawdown | `min((price − rolling_max) / rolling_max) × 100` |
| 50-day MA | Rolling 50-period mean (keyword-triggered) |
| 200-day MA | Rolling 200-period mean on full history (keyword-triggered) |

Year range auto-detected from question; defaults to last 3 years if not specified. Runs for each detected ticker and returns side-by-side.

**Example output (INTC vs MU 2023–2024):**
```
[Analytics] INTC (2023–2024):
  • Period: 2023-01-03 → 2024-12-31  (502 trading days)
  • Start: $26.73  →  End: $20.05 | Total Return: -25.0% | CAGR: -13.4%
  • Annualized Volatility: 45.6% | Maximum Drawdown: -62.8%

[Analytics] MU (2023–2024):
  • Period: 2023-01-03 → 2024-12-31  (502 trading days)
  • Start: $50.37  →  End: $84.16 | Total Return: +67.1% | CAGR: +29.4%
  • Annualized Volatility: 44.6% | Maximum Drawdown: -45.2%
```

**Direct endpoint (no GPT-4o call):**
```
POST /analytics
{ "tickers": ["INTC", "MU"], "years": ["2023", "2024"], "question": "compare return" }
```

---

### 4. FAISS Retrieval Improvements — `scripts/rag_chatbot.py`

**Year filtering** — new `year` parameter in `retrieve()`:
```python
chunks = bot.retrieve(query, ticker="INTC", year="2024")
# only returns chunks where metadata["fiscal_year"] == "2024"
```
Over-fetches 5× when filters are active to maintain `top_k` after filtering.

**Retrieval Confidence Score** — `format_context()` labels each chunk:
```
[1] Source: sec_edgar | Company: Intel (INTC) | Year: 2024 | Section: annual_report | Confidence: 0.72 (high)
[2] Source: macrotrends | Company: Intel (INTC) | Year: N/A  | Section: revenue     | Confidence: 0.41 (medium)
```
Thresholds: **high** ≥ 0.70 · **medium** ≥ 0.40 · **low** < 0.40

When top chunk score < 0.3, a caveat is appended to the GPT-4o system message:
> `[Note: Low retrieval confidence — answer may rely on general knowledge]`

---

### 5. Data Source Catalogue — `GET /data-sources`

| Source | Route | Tickers | Size |
|--------|-------|---------|------|
| SEC 10-K Filings (FY2022–FY2024) | faiss_rag | INTC, MU | 687 chunks |
| Macrotrends (revenue, EPS, net income, cash flow, balance sheet) | faiss_rag | INTC, MU | 27 chunks |
| StockAnalysis (annual + quarterly financials) | faiss_rag | INTC, MU | 17 chunks |
| CompaniesMarketCap (market cap history) | faiss_rag | INTC, MU | 8 chunks |
| Intel Investor Relations (SEC filings, press releases) | faiss_rag | INTC | 8 chunks |
| Yahoo Finance (quote summary) | faiss_rag | INTC, MU | 7 chunks |
| Stock Price CSV — INTC | structured_csv | INTC | 11,691 rows (1980–2026) |
| Stock Price CSV — MU | structured_csv | MU | 10,626 rows (1984–2026) |

Total FAISS: **754 vectors** · Model: `text-embedding-3-large` (dim 3072) · Similarity: cosine inner-product

---

### Files Changed

| File | Change | Summary |
|------|--------|---------|
| `scripts/rag_server.py` | Major rewrite | Added `classify_query`, `detect_tickers_in_query`, `detect_year_in_query`, `compute_stock_analytics`; refactored `/chat/general` with router; added `/analytics`, `/data-sources` |
| `scripts/rag_chatbot.py` | Updated | `year` filter in `retrieve()`; confidence score + fiscal year in `format_context()` |
| `webpage/index.html` | Major | Full AI Chat tab: 3-mode toggle, settings panel, auto-connect, proxy detection |
| `data/rag_index/` | Generated | 754-vector FAISS index + `chunks_meta.json` |
| `data/crawled/` | Generated | 21 markdown files + companion `.meta.json` |
| `data/stock_history/` | Data | `intc_history.csv` (11,691 rows), `mu_history.csv` (10,626 rows) |

---

## [2026-08-06] Phase 3 — Multi-Source RAG Pipeline

### Added
- `scripts/crawl_sources.py` — Firecrawl crawler for 21 financial URLs across 6 source types
  - Macrotrends (revenue, EPS, net income, cash flow, balance sheet — INTC + MU)
  - StockAnalysis (annual & quarterly financials — INTC + MU)
  - CompaniesMarketCap (market cap history — INTC + MU)
  - Intel IR (financial info, SEC filings, press releases)
  - Micron IR (quarterly results, news releases)
  - Yahoo Finance (quote summaries — INTC + MU)
- `scripts/build_index.py` — Document chunking (500-800 tokens, overlap) + OpenAI text-embedding-3-large + FAISS index builder
- `scripts/rag_chatbot.py` — Interactive RAG chatbot with metadata filtering (`/ticker:`, `/source:`) and citation-backed GPT-4o answers
- `data/crawled/` — Crawled markdown + metadata JSON storage
- `data/rag_index/` — FAISS index + chunk metadata

### Changed
- `requirements.txt` — Added tiktoken, faiss-cpu
- `docs/progress.md` — Phase 3 status updated to In Progress
- `docs/HOW_TO_RUN.md` — Added RAG pipeline usage instructions
- `.env` — OPENAI_API_KEY now required for RAG (was optional)

---

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
