# InvestorGPT — Tool Use Registry

| Tool | Status | Implementation |
|---|---|---|
| API calls | ✅ Done | SEC EDGAR (`download_10k.py`), Yahoo Finance (`refresh_data.py`) |
| Web scraping | ✅ Done | Firecrawl — `crawl_sources.py` (21 URLs, 6 source types) |
| Document parsing | ✅ Done | BeautifulSoup HTML→text in `build_index.py` |
| Text chunking | ✅ Done | 500–800 token chunks with overlap in `build_index.py` |
| Embeddings | ✅ Done | `text-embedding-3-large` (3072-dim) via OpenAI |
| Vector store | ✅ Done | FAISS (`faiss-cpu`) — `data/rag_index/` |
| LLM / RAG query | ✅ Done | GPT-4o via `rag_chatbot.py` with citation-backed answers |
| Chat UI | ⭐ Planned | Streamlit tab — Phase 3 remaining |
| Calculator / math | ✅ Done | Financial ratios, signal scores in `dashboard.py` |
| Database query | ❌ No | No SQL — FAISS covers vector search needs |

---

## Data Pipeline

```
Firecrawl (crawl_sources.py)
    → data/crawled/*.md + *.meta.json
        ↓
SEC EDGAR (download_10k.py)
    → data/10k/*.html
        ↓
build_index.py
    → BeautifulSoup parse → chunk (500–800 tokens)
    → text-embedding-3-large
    → FAISS index (data/rag_index/)
        ↓
rag_chatbot.py
    → top-k retrieval + metadata filter
    → GPT-4o → citation-backed answer
```

---

## Environment Variables

| Variable | Tool | Status |
|---|---|---|
| `OPENAI_API_KEY` | GPT-4o + text-embedding-3-large | Required |
| `FIRECRAWL_API_KEY` | `crawl_sources.py` | Required |
