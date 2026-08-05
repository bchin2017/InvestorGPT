# InvestorGPT – Tool Use Registry

| Tool | Covered? | Notes |
|---|---|---|
| API calls | ✅ Partial | SEC EDGAR API (`download_10k.py`), Yahoo Finance API (`yfinance`) |
| Calculator / math | ❌ No | No ratio calculations (P/E, gross margin %) yet |
| Database query | ❌ No | No SQL/vector DB query yet — FAISS planned but not built |
| Web scraping | ✅ Partial | Firecrawl practice done (`practice.py`); not yet wired into main pipeline |
| Document parsing | ✅ Partial | Raw HTML regex extraction in `generate_dashboard.py`; Firecrawl `/parse` planned |
| Text chunking | ❌ No | Planned via LangChain or LlamaIndex |
| Embeddings | ❌ No | Planned — Azure OpenAI `text-embedding-3-large` |
| Vector store | ❌ No | Planned — FAISS (`faiss-cpu`) |
| LLM / RAG query | ❌ No | Planned — Azure OpenAI GPT-4o |
| Chat UI | ❌ No | Planned — Streamlit |

---

## Data Pipeline — Tool Mapping

```
SEC EDGAR API
    → download_10k.py
        → data/10k/*.html (raw)
            → Firecrawl /parse  (planned)
                → data/markdown/*.md (clean)
                    → LangChain chunking
                        → text-embedding-3-large
                            → FAISS index
                                → GPT-4o (RAG)
                                    → Streamlit chat UI
```

---

## Environment Variables

| Variable | Tool | Where set |
|---|---|---|
| `FIRECRAWL_API_KEY` | Firecrawl | `.env` + PowerShell profile |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI | `.env` (planned) |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI | `.env` (planned) |
| `AZURE_OPENAI_DEPLOYMENT` | GPT-4o deployment name | `.env` (planned) |
