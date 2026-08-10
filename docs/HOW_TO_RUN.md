# InvestorGPT — How to Run

**Last updated:** 2026-08-10

---

## Folder Guide

| File / Folder | Purpose |
|---|---|
| `dashboard.py` | Streamlit dashboard — INTC + MU, Buffett scoring, signals, forecasts |
| `scripts/refresh_data.py` | Fetch/cache INTC + MU stock history from Yahoo Finance |
| `scripts/download_10k.py` | Download Intel & Micron 10-K HTML from SEC EDGAR |
| `scripts/crawl_sources.py` | Firecrawl-based crawler for financial web sources |
| `scripts/build_index.py` | Chunk documents, embed, build FAISS vector index |
| `scripts/rag_chatbot.py` | RAG chatbot with citation-backed answers |
| `scripts/generate_dashboard.py` | Regenerate static `webpage/index.html` from 10-K data |
| `scripts/start_server_bg.ps1` | Start `rag_server.py` as a hidden detached background process |
| `install_autostart.bat` | **Run once as Admin** — installs Windows Scheduled Task to auto-start RAG server at login |
| `start_investor.bat` | One-click launcher (port 8502) |
| `_keeper.bat` | Watchdog — auto-restarts Streamlit on crash |
| `stop_investor.bat` | One-click stop |
| `webpage/index.html` | Static HTML dashboard (no server required) |

---

## Starting the Streamlit Dashboard

Double-click **`start_investor.bat`**

What it does:
1. Runs `scripts/refresh_data.py` in background (refreshes INTC + MU data from Yahoo)
2. Logs refresh output to `refresh_startup.log`
3. Kills any existing process on port `8502`
4. Starts `_keeper.bat` minimized (watchdog loop)
5. Waits up to 40 seconds for port `8502` LISTENING
6. Opens browser at `http://localhost:8502`

## Stopping the Dashboard

Double-click **`stop_investor.bat`**

---

## Refreshing Stock Data Manually

```powershell
cd "c:\Users\bhoe\VS Code\InvestorGPT"
python scripts/refresh_data.py --force
```

Add tickers beyond INTC and MU:

```powershell
python scripts/refresh_data.py --tickers INTC MU AMD NVDA --force
```

## Re-downloading 10-K Filings

```powershell
python scripts/download_10k.py
```

Downloads latest Intel and Micron 10-K HTML files to `data/10k/`.

## Regenerating the Static Dashboard

```powershell
python scripts/generate_dashboard.py
```

Reads `data/10k/*.html`, fetches stock prices via yfinance, writes `webpage/index.html`.

## Static Dashboard Launchers (HTML + AI Chat)

Use one of these two launcher files:

1. `open_dashboard.bat` (full mode)
	- Starts AI server on port 8503 if needed
	- Refreshes market data
	- Regenerates `webpage/index.html`
	- Opens a loading page and auto-redirects to dashboard when ready

2. `open_dashboard_fast.bat` (fast mode)
	- Starts AI server on port 8503 if needed
	- Skips refresh + generation
	- Opens existing dashboard snapshot quickly

If fast mode does not find `webpage/index.html`, it automatically falls back to full mode.

---

## First-Time Setup

```powershell
cd "c:\Users\bhoe\VS Code\InvestorGPT"
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## Environment Variables

Create `.env` in the project root:

```
OPENAI_API_KEY=sk-...        # Required for RAG chatbot + AI Advisor tab
FIRECRAWL_API_KEY=fc-...     # Required for crawl_sources.py
```

---

## GitHub Actions Automation

Workflow: `.github/workflows/daily-market-data-refresh.yml`

- Runs automatically **Mon–Fri at 03:10 UTC** (11:10 MYT)
- Executes `python scripts/refresh_data.py --force --tickers INTC MU`
- Commits updated `data/stock_history/*.csv` and `.cache/market_data_meta.json`

To trigger manually: **GitHub → Actions → Daily Market Data Refresh → Run workflow**

---

## RAG Chatbot Pipeline

### Step 1: Crawl financial web sources

```powershell
python scripts/crawl_sources.py               # crawl all 21 URLs
python scripts/crawl_sources.py --source macrotrends   # crawl one source
```

Available sources: `macrotrends`, `stockanalysis`, `companiesmarketcap`, `intel_ir`, `micron_ir`, `yahoo_finance`

Output: `data/crawled/*.md` + `data/crawled/*.meta.json`

### Step 2: Build FAISS vector index

```powershell
python scripts/build_index.py          # build index (skips if exists)
python scripts/build_index.py --rebuild # force rebuild
```

Indexes both crawled markdown and 10-K HTML files. Output: `data/rag_index/`

### Step 3: Chat

```powershell
python scripts/rag_chatbot.py                                          # interactive mode
python scripts/rag_chatbot.py --query "Compare Intel vs Micron revenue"  # single query
python scripts/rag_chatbot.py --query "EPS trend" --ticker INTC          # filtered
```

In interactive mode, use inline filters: `/ticker:INTC`, `/source:macrotrends`

---

## Port Reference

| Service | Port |
|---|---|
| **Streamlit Dashboard** | **8502** |
| **RAG AI Chat Server** | **8503** |

---

## AI Chat Server (RAG + Memory)

The AI Chat tab in the static dashboard requires `rag_server.py` running on port 8503.

### Why you see "Server offline" every day

The server is a process — it dies when you reboot or close the terminal that launched it. The bat file only starts it if port 8503 is not already listening, so a fresh boot always needs it restarted.

**Permanent fix (one-time setup):**  
Right-click `install_autostart.bat` → **Run as Administrator**  
This registers a Windows Scheduled Task that auto-starts the server on every login. Do this once and the issue is gone permanently.

### Architecture (as of 2026-08-10)

`open_dashboard.bat` now calls `scripts/start_server_bg.ps1` instead of a visible `cmd /k` window:
- Server runs as a **hidden, detached process** (no window to accidentally close)
- Stdout logged to `data/rag_server.log`, stderr to `data/rag_server_err.log`
- PID saved to `data/rag_server.pid`
- `open_dashboard.bat` polls port 8503 for up to 45 seconds before proceeding

### Normal start (via bat)

Just run `open_dashboard.bat` or `open_dashboard_fast.bat` — the server starts automatically if not already running.

### Manual start options

**Option A — Preferred (hidden background process, survives terminal close):**
```powershell
cd "c:\Users\bhoe\VS Code\InvestorGPT"
powershell -ExecutionPolicy Bypass -File "scripts\start_server_bg.ps1"
```

**Option B — Visible window (useful for live debugging):**
```powershell
cd "c:\Users\bhoe\VS Code\InvestorGPT"
python scripts/rag_server.py
```
> Keep this window open — closing it kills the server.

**Option C — Kill and restart:**
```powershell
Get-Content "c:\Users\bhoe\VS Code\InvestorGPT\data\rag_server.pid" | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
cd "c:\Users\bhoe\VS Code\InvestorGPT"
powershell -ExecutionPolicy Bypass -File "scripts\start_server_bg.ps1"
```

**Option D — Check crash logs:**
```powershell
Get-Content "c:\Users\bhoe\VS Code\InvestorGPT\data\rag_server_err.log"
```

The server:
- Loads FAISS index (754 vectors) on startup
- Exposes `/chat/general` endpoint with session memory
- Maintains conversation history per browser session (up to 100 messages / 50 turns)
- Remembers user introductions, preferences, and prior context across messages
- Asks clarifying questions only for ambiguous financial queries (not conversational ones)
- Detects conversational queries (greetings, name recall, "remember", "i am") and skips RAG
- Filters out low-confidence RAG results (score < 0.2) to avoid noise
- System prompt explicitly instructs GPT-4o to always check conversation history first

### Session Memory

Each browser gets a persistent user ID (stored in localStorage). Sessions are tracked per-user:
- **Chat History panel** (right side) shows all your past sessions with topic previews
- Click any session to switch back to it (server restores context)
- Click **"+ New"** to start a fresh session
- Click 🗑️ next to Send to clear current session memory
- Sessions persist for **1 week** (auto-expire after 7 days)
- Server keeps up to 100 messages (50 turns) per session
- Last 50 messages sent to GPT-4o for context on each request

**Clear memory**: Click the 🗑️ button next to Send in the chat, or call:
```powershell
curl -X POST http://localhost:8503/chat/clear -H "Content-Type: application/json" -d "{\"session_id\":\"your_session_id\"}"
```

**List sessions**:
```powershell
curl -X POST http://localhost:8503/chat/sessions -H "Content-Type: application/json" -d "{\"user_prefix\":\"u_\"}"
```

Memory resets when: user clicks clear button, session expires (7 days), or server restarts.

### Health check

```powershell
curl http://localhost:8503/health
```

Expected: `{"status": "ok", "has_api_key": true}`

---

## Troubleshooting: Python Not Found After PC Format

```powershell
python -m streamlit --version
.venv\Scripts\python.exe -m streamlit --version
```

If the first fails but the second works: PATH/venv mismatch.
The batch files auto-detect and fall back to system `python`.

### Known-good manual launch

```powershell
cd "c:\Users\bhoe\VS Code\InvestorGPT"
python -m streamlit run dashboard.py --server.port 8502 --server.headless true
```

---

## Git Sync

```powershell
cd "c:\Users\bhoe\VS Code\InvestorGPT"
git fetch origin
git pull --rebase origin main
git push origin main
```

### First-time git setup (new machine)

```powershell
git init
git branch -M main
git add .
git commit -m "initial investorgpt setup"
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```
