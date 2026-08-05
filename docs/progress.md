# InvestorGPT – Project Progress

## Status: In Progress

---

## Completed

### Environment Setup
- [x] Created project workspace (`InvestorGPT.code-workspace`)
- [x] Added `requirements.txt` with `firecrawl-py`, `beautifulsoup4`, `lxml`, `yfinance`
- [x] Created `.env` for API keys (excluded from git via `.gitignore`)
- [x] Set `FIRECRAWL_API_KEY` in PowerShell profile for global access

### Data Pipeline
- [x] `scripts/download_10k.py` — downloads Intel & Micron 10-K HTML from SEC EDGAR (free, no API key)
- [x] Downloaded 6 filings: Intel FY2022/FY2023/FY2024, Micron FY2023/FY2024/FY2025
- [x] `data/10k/` excluded from git (large source files, re-downloadable)

### Dashboard
- [x] `scripts/generate_dashboard.py` — extracts financials from 10-K HTML using regex
- [x] `index.html` — static dashboard with Chart.js and Bootstrap
  - Revenue comparison chart (Intel vs Micron, 3 years each)
  - Net income/loss chart (color-coded for positive/negative)
  - Stock price chart (3-year history via Yahoo Finance)
  - Key metrics comparison table

### Firecrawl Practice
- [x] `firecrawl-practice/practice.py` — beginner exercise: scrape URL, count headings/links, keyword search

---

## Known Issues / Remaining Work

### Dashboard Data Quality
- [ ] Intel Gross Margin — label in XBRL filing not yet matched
- [ ] Micron Net Income FY2024 (778M) — regex picks up wrong value (5,833) before it
- [ ] Stock price chart — yfinance silent failure, needs debugging

### Core RAG Chatbot (Not Started)
- [ ] PDF ingestion pipeline (convert 10-K HTML/PDF → clean Markdown for RAG)
- [ ] Embedding + vector store setup (FAISS recommended)
- [ ] LLM integration (Azure OpenAI GPT-4o)
- [ ] Chat interface (Streamlit)
- [ ] Citation-backed answer generation
- [ ] Company comparison capability

---

## Architecture (Planned)

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
