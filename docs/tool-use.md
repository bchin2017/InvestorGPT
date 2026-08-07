# InvestorGPT — Tool Use Registry (15 Categories)

## Tool Use Summary

| # | Category | Examples | Status | Implementation | Usage Example & Description |
|---|---|---|---|---|---|
| 1 | **Working Prototype** | Demo working prototype in class | ✅ Done | Full-stack system: `dashboard.py`, `rag_server.py`, `webpage/index.html`, `.bat` launchers | End-to-end working investment AI system demonstrated live. Includes: Streamlit dashboard with real-time stock analytics, static HTML dashboard (opens in any browser without server), Flask-based AI chatbot with RAG, one-click launch via `start_investor.bat` and `open_dashboard.bat`. The prototype covers data ingestion → vector indexing → retrieval → LLM answer → interactive visualization in a single cohesive application. |
| 2 | **RAG** | Vector DB, retrieval, citations | ✅ Done | FAISS vector store + GPT-4o in `rag_chatbot.py`, `rag_server.py` | Retrieval-Augmented Generation pipeline: (1) User question is embedded via `text-embedding-3-large` (3072-dim), (2) FAISS `IndexFlatIP` performs cosine similarity search returning top-8 relevant chunks, (3) Retrieved context is formatted with confidence scores and source metadata, (4) GPT-4o generates answers with mandatory inline citations `[Source: sec_edgar, annual_report]`. Supports metadata filtering by ticker, source, and fiscal year. Prevents hallucination by constraining answers to retrieved context only. |
| 3 | **Advanced Chunking** | Semantic, recursive, metadata-aware | ✅ Done | `build_index.py` — paragraph-aware, sentence-split, overlap, metadata-enriched | Metadata-aware chunking with multiple strategies: Documents are split into 400–800 token chunks using tiktoken `cl100k_base` encoder. The algorithm is paragraph-boundary-aware (splits at `\n\n`), applies recursive sentence splitting for oversized paragraphs (`re.split(r"(?<=[.!?])\s+")`), maintains 100-token overlap for context continuity, and discards fragments <50 tokens. Each chunk inherits rich metadata (source, company, ticker, doc_type, section, fiscal_year, URL, chunk_index) enabling filtered retrieval. |
| 4 | **Agent / LangGraph** | Multi-step workflow, state, planning | ✅ Done | Multi-step orchestration in `rag_server.py`, decision matrix in `dashboard.py` | Multi-step reasoning workflow with state management: The RAG server implements an agent-like pipeline — (1) Parse user intent and extract filter commands (`/ticker:INTC`, `/source:macrotrends`), (2) Route to RAG retrieval or general knowledge, (3) Maintain conversation state via `self.history` for multi-turn follow-ups, (4) The dashboard's Decision Matrix acts as a planning agent — combining 10-factor technical signal + Buffett quality score to produce actionable investment decisions (BUY MAX / DCA / HOLD / TRIM / EXIT) with reasoning explanations. |
| 5 | **Memory** | Session memory, long-term memory | ✅ Done | Server-side session memory in `rag_server.py`, `_chat_sessions` dict, localStorage session IDs, Chat History panel | **Session memory** (conversation context): `rag_server.py` maintains a `_chat_sessions` dictionary keyed by `session_id`. Each browser tab generates a unique persistent session ID stored in localStorage. The server stores up to 100 messages (50 turns) per session with 1-week TTL. Last 50 messages are sent to GPT-4o on each request for multi-turn context. System prompt explicitly instructs: "ALWAYS check previous messages first. If the user told you their name, remember and use it." **Conversational detection**: queries matching patterns like "my name", "i am", "remember", "you said" bypass RAG entirely to avoid polluting memory answers with irrelevant financial chunks. **Low-confidence filter**: FAISS results below 0.2 cosine score are discarded. **Chat History panel**: right-side UI shows all sessions with topic previews (first 50 chars of first question), age, message count. Users can switch sessions, create new ones ("+ New"), or clear memory (🗑️ button). **Long-term memory**: FAISS index persists knowledge on disk; market metadata in `.cache/` tracks refresh timestamps. |
| 6 | **Tool Use** | APIs, calculator, database query | ✅ Done | SEC EDGAR API, Yahoo Finance API, financial calculators, FAISS vector query | Multiple tool integrations: **API calls** — SEC EDGAR JSON API (`data.sec.gov/submissions/`) fetches 10-K filings by CIK; Yahoo Finance chart API pulls OHLCV price history. **Calculator/Math** — 10-factor signal scoring (RSI, MACD, Bollinger Bands, Z-score, etc.), ARIMA(2,1,2) fitting, Monte Carlo with 10,000 simulations, financial ratios (P/E, ROE, debt-to-equity, gross margin). **Database query** — FAISS vector similarity search replaces traditional SQL; supports filtered retrieval by ticker, source, fiscal year. |
| 7 | **Web Search** | Live search, source-aware answers | ✅ Done | Firecrawl (`crawl_sources.py`), 21+ live URLs, source-aware citations | Live web data collection with source attribution: `crawl_sources.py` uses Firecrawl SDK to scrape 21+ financial URLs from 6 source types — Macrotrends (revenue, EPS, net income, cash flow, balance sheet), StockAnalysis (annual + quarterly financials), Yahoo Finance (live quotes), CompaniesMarketCap (market cap history), Intel/Micron investor relations (press releases, SEC filings). Every answer includes source-aware citations with URL, company, section, and confidence score so users can verify claims. |
| 8 | **Local LLM** | Ollama, LM Studio, hybrid routing | ⭐ Partial | Hybrid routing in `rag_server.py` (RAG path vs general GPT-4o path) | Hybrid routing architecture: `rag_server.py` implements intelligent routing — if the question matches financial/semiconductor context, it routes through the RAG pipeline (retrieval + GPT-4o with context). If no relevant chunks are found or the question is general, it falls back to GPT-4o general knowledge mode. This dual-path approach mirrors hybrid routing patterns used with local/cloud LLM setups. (Local Ollama integration planned for cost reduction on general queries.) |
| 9 | **Data Pipeline** | Ingestion, parsing, cleaning | ✅ Done | `crawl_sources.py` → `download_10k.py` → `build_index.py` → `refresh_data.py` | Full ETL pipeline: **Ingestion** — Firecrawl scrapes web pages to markdown; SEC EDGAR downloads 10-K HTML filings; Yahoo Finance fetches OHLCV CSVs. **Parsing** — BeautifulSoup + lxml strips HTML tags, removes script/style elements, extracts clean text. **Cleaning** — Deduplication of stock history records, empty document filtering, token-limit truncation for embedding API. Pipeline orchestrated via batch scripts for one-click refresh. Each stage writes intermediate outputs (markdown, CSV, JSON) enabling debugging and re-runs from any stage. |
| 10 | **Multiple Data Sources** | Adding new data sources for RAG | ✅ Done | 6 source types: SEC EDGAR, Macrotrends, StockAnalysis, Yahoo Finance, CompaniesMarketCap, Investor Relations | RAG system ingests from 6 distinct data source types for comprehensive coverage: (1) **SEC EDGAR** — official 10-K annual reports (3 years × 2 companies), (2) **Macrotrends** — historical financials (revenue, EPS, net income, cash flow, balance sheet), (3) **StockAnalysis** — annual + quarterly financial statements, (4) **Yahoo Finance** — real-time quotes and price history, (5) **CompaniesMarketCap** — market cap timelines, (6) **Investor Relations** — press releases and filings from Intel/Micron corporate sites. New sources are added by appending to the `SOURCES` list in `crawl_sources.py` with metadata fields. |
| 11 | **Fine-tuning / PEFT** | LoRA, QLoRA, adapters | ❌ Not Used | N/A — uses prompt engineering + RAG instead of fine-tuning | Not implemented. InvestorGPT achieves domain-specific behavior through RAG (grounding answers in retrieved financial data) and prompt engineering (enforcing citation format, persona, and response constraints) rather than model fine-tuning. This approach avoids training costs while maintaining up-to-date knowledge via live data refresh. Future consideration: fine-tune a smaller model on semiconductor analysis patterns for cost reduction. |
| 12 | **Evaluation** | Metrics, test cases, failure analysis | ✅ Done | Confidence scoring, retrieval quality metrics, signal backtesting | Multi-level evaluation: **Retrieval quality** — each retrieved chunk gets a cosine similarity score classified as high (≥0.7), medium (≥0.4), or low confidence, displayed to users for transparency. **Signal backtesting** — 10-factor signal computed over full price history (`_compute_signal_series`) enables visual validation against actual price movements. **Failure handling** — system explicitly reports "No relevant documents found" when retrieval fails, flags outdated data, and suggests query broadening. Decision matrix outputs include reasoning explanations for each recommendation. |
| 13 | **Deployment** | Hugging Face Space, Public Server, GitHub | ✅ Done | Local deployment via Streamlit, Flask server, static HTML, batch launchers | Multiple deployment modes: (1) **Streamlit app** — `streamlit run dashboard.py` serves live interactive dashboard on localhost:8501, (2) **Flask API server** — `rag_server.py` runs on port 8503 for AI chat, (3) **Static HTML** — `generate_dashboard.py` produces a self-contained `webpage/index.html` with all data embedded as JSON (zero server required, opens in any browser), (4) **Batch automation** — `.bat` scripts for one-click launch on Windows. GitHub repo contains full source for reproducibility. |
| 14 | **Bonus Tech** | Speech, images, video, MCP | ✅ Done | Interactive Plotly charts, ARIMA+Monte Carlo forecasting, 10-factor quant signal | Advanced technical features beyond basic RAG: **Interactive visualizations** — Plotly candlestick charts with MA overlays, Bollinger Bands, signal heatmaps, Monte Carlo fan charts, radar charts for moat scoring. **Statistical ML** — ARIMA(2,1,2) time-series forecasting on log-prices, Monte Carlo simulation (10,000 paths, geometric Brownian motion), ensemble weighting (40/60). **Quantitative finance** — 10-factor signal engine (RSI, Stochastic RSI, BB, Z-score, 52-week position, MA200, MA convergence, MACD, volatility regime, ROC10) with custom weighting. |
| 15 | **Bonus — Real Use Cases** | Real factory/company use cases implemented | ✅ Done | Intel (INTC) & Micron (MU) semiconductor investment analysis | Real-world semiconductor investment analysis system for Intel and Micron: Analyzes actual SEC 10-K filings (FY2023–2025), real market data from Yahoo Finance, and live financial metrics. Generates actionable investment decisions using Buffett-style value investing principles. Covers real company narratives — Intel's fab turnaround and CHIPS Act; Micron's AI memory supercycle and HBM3E leadership. Decision matrix produces specific recommendations (BUY/HOLD/SELL) with price targets for a real 18-month horizon (target: June 2027). Used for actual investment research on semiconductor stocks. |

---

## Data Pipeline Flow

```
[9] Data Pipeline + [10] Multiple Data Sources
    SEC EDGAR (download_10k.py) → data/10k/*.html
    Firecrawl (crawl_sources.py) → data/crawled/*.md + *.meta.json
    Yahoo Finance (refresh_data.py) → data/stock_history/*.csv
        ↓
[3] Advanced Chunking
    BeautifulSoup parse → paragraph-aware split (400–800 tokens, 100 overlap)
        ↓
[2] RAG — Vector Store
    text-embedding-3-large (3072-dim) → FAISS IndexFlatIP
        ↓
[2] RAG — Retrieval + Generation
    User query → embed → top-k search → GPT-4o → cited answer
        ↓
[1] Working Prototype
    Streamlit dashboard + Flask AI chat + static HTML report
```

---

## Environment Variables

| Variable | Tool | Status |
|---|---|---|
| `OPENAI_API_KEY` | GPT-4o + text-embedding-3-large | Required |
| `FIRECRAWL_API_KEY` | `crawl_sources.py` | Required |

---

## Libraries & Frameworks

| Library | Category | Purpose |
|---|---|---|
| `openai` | RAG + Embeddings | GPT-4o chat, text-embedding-3-large |
| `faiss-cpu` | RAG (Vector Store) | Cosine similarity search index |
| `tiktoken` | Advanced Chunking | Token counting for chunk boundaries |
| `firecrawl-py` | Web Search | Live markdown extraction from URLs |
| `beautifulsoup4` + `lxml` | Data Pipeline | HTML→text parsing for 10-K filings |
| `yfinance` | Tool Use (API) | Stock price data |
| `pandas` + `numpy` | Data Pipeline | Dataframes, numerical computation |
| `statsmodels` | Bonus Tech | ARIMA time-series forecasting |
| `plotly` | Bonus Tech | Interactive financial charts |
| `streamlit` | Deployment | Live web dashboard UI |
| `flask` + `flask-cors` | Deployment | REST API server for AI chat |
| `python-dotenv` | Working Prototype | Environment variable configuration |
