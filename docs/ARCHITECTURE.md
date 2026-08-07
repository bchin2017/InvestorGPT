# InvestorGPT — System Architecture

**Last updated:** 2026-08-07

---

## High-Level Architecture

```mermaid
graph TB
    subgraph User["👤 User"]
        Browser[Browser]
    end

    subgraph Frontend["🖥️ Frontend Layer"]
        HTML["webpage/index.html<br/>(Static Dashboard)"]
        Streamlit["dashboard.py<br/>(Streamlit App :8502)"]
    end

    subgraph Backend["⚙️ Backend Layer"]
        RAGServer["rag_server.py<br/>(Flask API :8503)"]
        Chatbot["rag_chatbot.py<br/>(CLI Chatbot)"]
    end

    subgraph AI["🤖 AI Services"]
        GPT4o["OpenAI GPT-4o<br/>(Chat Completion)"]
        Embed["text-embedding-3-large<br/>(3072-dim Embeddings)"]
    end

    subgraph Storage["💾 Data Layer"]
        FAISS["FAISS Vector Index<br/>(754 chunks, cosine)"]
        StockCSV["Stock History CSV<br/>(INTC 1980→, MU 1984→)"]
        Crawled["Crawled Markdown<br/>(21 sources + metadata)"]
        TenK["10-K HTML Filings<br/>(6 filings, Intel+Micron)"]
        Cache[".cache/<br/>(refresh metadata)"]
        Sessions["In-Memory Sessions<br/>(1-week TTL, 100 msgs)"]
    end

    subgraph DataSources["🌐 External Data Sources"]
        EDGAR["SEC EDGAR API"]
        Yahoo["Yahoo Finance API"]
        Firecrawl["Firecrawl SDK"]
        Macrotrends["Macrotrends"]
        StockAnalysis["StockAnalysis"]
        IR["Investor Relations"]
    end

    Browser --> HTML
    Browser --> Streamlit
    HTML -->|fetch /chat/general| RAGServer
    HTML -->|fetch /health| RAGServer
    HTML -->|fetch /chat/sessions| RAGServer
    Streamlit -->|yfinance| Yahoo

    RAGServer -->|embed query| Embed
    RAGServer -->|retrieve chunks| FAISS
    RAGServer -->|generate answer| GPT4o
    RAGServer -->|session memory| Sessions
    RAGServer -->|price lookup| StockCSV
    Chatbot -->|embed + retrieve| FAISS
    Chatbot -->|generate| GPT4o

    FAISS -.->|built from| Crawled
    FAISS -.->|built from| TenK
    StockCSV -.->|refreshed from| Yahoo
    Crawled -.->|scraped by| Firecrawl
    TenK -.->|downloaded from| EDGAR
```

---

## Data Pipeline Flow

```mermaid
flowchart LR
    subgraph Ingestion["1️⃣ Data Ingestion"]
        A1["crawl_sources.py<br/>Firecrawl → 21 URLs"]
        A2["download_10k.py<br/>SEC EDGAR → 6 filings"]
        A3["refresh_data.py<br/>Yahoo Finance → OHLCV"]
    end

    subgraph Processing["2️⃣ Processing"]
        B1["BeautifulSoup<br/>HTML → Plain Text"]
        B2["Chunking<br/>400-800 tokens<br/>100-token overlap"]
        B3["Embedding<br/>text-embedding-3-large<br/>3072 dimensions"]
    end

    subgraph Indexing["3️⃣ Indexing"]
        C1["FAISS IndexFlatIP<br/>754 vectors<br/>cosine similarity"]
        C2["chunks_meta.json<br/>source, ticker, year, URL"]
    end

    subgraph Query["4️⃣ Query & Answer"]
        D1["User Question"]
        D2["Query Classification<br/>csv_price | csv_analytics<br/>faiss | mixed | conversational"]
        D3["Retrieval<br/>top-8 chunks<br/>metadata filter"]
        D4["GPT-4o Synthesis<br/>+ session history<br/>+ citations"]
    end

    A1 -->|*.md + *.meta.json| B1
    A2 -->|*.html| B1
    A3 -->|*.csv| C2
    B1 --> B2
    B2 --> B3
    B3 --> C1
    B3 --> C2
    D1 --> D2
    D2 --> D3
    D3 -->|context| D4
    C1 -->|similarity search| D3
```

---

## AI Chat Memory Flow

```mermaid
sequenceDiagram
    participant U as User (Browser)
    participant JS as index.html (JS)
    participant S as rag_server.py
    participant GPT as GPT-4o

    U->>JS: Type "I am Dell" + Send
    JS->>S: POST /chat/general {question, session_id}
    S->>S: Detect conversational (skip RAG)
    S->>S: Load session history[]
    S->>GPT: [system + history + question]
    GPT-->>S: "Hello, Dell!"
    S->>S: Save to history: [user, assistant]
    S-->>JS: {answer, route: conversational}
    JS->>S: POST /chat/sessions {user_prefix}
    S-->>JS: {sessions: [{topic:"I am Dell...", msgs:2}]}
    JS->>JS: Update Chat History panel

    U->>JS: Type "What is my name?" + Send
    JS->>S: POST /chat/general {question, session_id}
    S->>S: Detect conversational
    S->>S: Load history: ["I am Dell", "Hello Dell!"]
    S->>GPT: [system + history + question]
    Note over GPT: System prompt: "ALWAYS check previous messages"
    GPT-->>S: "Your name is Dell"
    S-->>JS: {answer}
```

---

## File Structure

```
InvestorGPT/
├── dashboard.py              # Streamlit live dashboard (port 8502)
├── scripts/
│   ├── rag_server.py         # Flask REST API (port 8503) — AI Chat backend
│   ├── rag_chatbot.py        # CLI RAG chatbot (interactive + single-query)
│   ├── build_index.py        # Chunk → Embed → FAISS index builder
│   ├── crawl_sources.py      # Firecrawl web scraper (21 URLs, 6 source types)
│   ├── download_10k.py       # SEC EDGAR 10-K downloader
│   ├── refresh_data.py       # Yahoo Finance OHLCV data refresh
│   └── generate_dashboard.py # Static HTML dashboard generator
├── webpage/
│   ├── index.html            # Generated static dashboard (all data embedded)
│   ├── loading.html          # Loading/redirect page
│   └── startup_status.js     # Startup progress tracker
├── data/
│   ├── stock_history/        # INTC + MU daily OHLCV CSVs (11k+ rows each)
│   ├── crawled/              # Markdown + metadata from web scraping
│   ├── 10k/                  # Intel & Micron 10-K HTML filings
│   └── rag_index/            # FAISS index + chunk metadata JSON
├── docs/                     # Project documentation
├── .cache/                   # Refresh metadata
├── .env                      # API keys (OPENAI_API_KEY, FIRECRAWL_API_KEY)
├── requirements.txt          # Python dependencies
├── open_dashboard.bat        # Full mode: refresh → generate → open browser
├── open_dashboard_fast.bat   # Fast mode: skip refresh, open existing HTML
├── start_investor.bat        # Launch Streamlit dashboard
├── stop_investor.bat         # Stop Streamlit
└── _keeper.bat               # Watchdog — auto-restart on crash
```

---

## Component Details

### Frontend Components

| Component | Technology | Port | Purpose |
|-----------|-----------|------|---------|
| Static Dashboard | HTML + Chart.js + Bootstrap | file:// | Self-contained analytics (no server needed for charts) |
| AI Chat | HTML + fetch() → Flask | 8503 | RAG-powered conversational AI |
| Streamlit Dashboard | Streamlit + Plotly | 8502 | Live interactive dashboard |

### Backend Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Server status + API key check |
| `/chat/general` | POST | Main AI chat (routing + RAG + memory) |
| `/chat` | POST | RAG-only chat (no routing) |
| `/chat/clear` | POST | Clear session memory |
| `/chat/sessions` | POST | List user's session history |
| `/data-sources` | GET | FAISS + CSV source catalogue |
| `/analytics` | POST | Direct CSV analytics (no LLM) |

### Query Router

| Route | Trigger | Data Source | Example |
|-------|---------|-------------|---------|
| `csv_price` | Date + price keywords | Stock CSV | "Intel price on 2025-01-06" |
| `csv_analytics` | Returns, CAGR, volatility | Stock CSV | "INTC total return 2023-2024" |
| `faiss` | Strategy, risk, filings | FAISS index | "Intel AI strategy" |
| `mixed` | Price + context | CSV + FAISS | "Stock after HBM announcement" |
| `conversational` | Greetings, name, memory | Session only | "What is my name?" |

### Signal Engine (10 Factors)

| Factor | Weight | Range |
|--------|--------|-------|
| RSI (14-day) | 12% | 0-100 |
| Stochastic RSI | 7% | 0-100 |
| Bollinger Band %B | 10% | 0-100 |
| 2-Year Z-Score | 20% | 0-100 |
| 52-Week Position | 8% | 0-100 |
| MA200 Deviation | 12% | 0-100 |
| MA50/200 Convergence | 8% | 0-100 |
| MACD Histogram | 8% | 0-100 |
| Volatility Regime | 8% | 0-100 |
| 10-Day ROC | 7% | 0-100 |

**Score interpretation**: 0 = Strong Buy, 50 = Neutral, 100 = Strong Sell

---

## Deployment Modes

```mermaid
graph LR
    subgraph Mode1["Mode 1: Static HTML (Offline)"]
        G["generate_dashboard.py"] --> H["index.html"]
        H --> B1["Open in any browser"]
    end

    subgraph Mode2["Mode 2: Static + AI Chat"]
        H2["index.html"] --> R["rag_server.py :8503"]
        R --> O["OpenAI API"]
    end

    subgraph Mode3["Mode 3: Streamlit (Live)"]
        S["dashboard.py"] --> Y["yfinance (live)"]
        S --> P["Port 8502"]
    end
```

| Mode | Command | Needs Server | Needs Internet |
|------|---------|-------------|----------------|
| **Static (charts only)** | `open_dashboard_fast.bat` | No | No |
| **Static + AI Chat** | `open_dashboard.bat` | Yes (port 8503) | Yes (OpenAI) |
| **Streamlit Live** | `start_investor.bat` | No | Yes (yfinance) |

---

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| LLM | OpenAI GPT-4o | Latest |
| Embeddings | text-embedding-3-large | 3072-dim |
| Vector DB | FAISS (faiss-cpu) | 1.7.4+ |
| Tokenizer | tiktoken (cl100k_base) | 0.5+ |
| Web Scraping | Firecrawl SDK | Latest |
| HTML Parsing | BeautifulSoup + lxml | 4.x |
| Charts (Static) | Chart.js | 4.4.4 |
| Charts (Streamlit) | Plotly | 5.15+ |
| Dashboard | Streamlit | 1.35+ |
| API Server | Flask + flask-cors | 3.x |
| Forecasting | statsmodels ARIMA | 0.14+ |
| Data | pandas + numpy | 2.0+ |
| Stock Data | yfinance | 0.2.31+ |
| Python | CPython | 3.14 |
