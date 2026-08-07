# InvestorGPT — Troubleshooting Cheatsheet

## RAG Server (AI Chat "Server AI" mode)

### "Server offline — start rag_server.py" in AI Chat tab

**Symptoms:** AI Chat tab shows red "Server offline" even after running `open_dashboard.bat`.

**Root cause (race condition):** The bat file starts `rag_server.py` in a background window and waits for port 8503. However:
1. Original bat used `cmd /c` — if the server crashed, the window closed silently with no error visible.
2. The server takes several seconds to load 754 FAISS vectors + initialize OpenAI client.
3. The browser opens `index.html` and JS calls `/health` once. If the server isn't ready yet, it shows "offline" permanently (no retry).

**Fixes applied (2026-08-07):**
1. **`open_dashboard.bat`**: Changed `cmd /c` → `cmd /k` so the server window stays open (errors visible). Increased wait timeout 30s → 45s.
2. **`webpage/index.html` + `scripts/generate_dashboard.py`**: Added `_serverPoll` — a `setInterval(5000)` retry that polls `/health` every 5s. Once server responds, it auto-switches to "Server online" mode and clears the interval.

**Manual fix if server still offline:**
```powershell
cd "c:\Users\bhoe\VS Code\InvestorGPT"
python scripts/rag_server.py
```
Then refresh the browser — the 5s polling will pick it up automatically.

**Key facts:**
- Server runs on `http://localhost:8503`
- Loads FAISS index (754 vectors) from `data/rag_index/`
- Requires `OPENAI_API_KEY` in `.env` for GPT-4o synthesis
- Health endpoint: `GET /health` → `{"status": "ok"}`
- The `generate_dashboard.py` regenerates `index.html` — polling fix lives in BOTH files

### No .venv — use system Python
- There is NO `.venv` in this workspace
- System Python: `C:\Program Files\Python314\python.exe`
- The `open_dashboard.bat` checks for `.venv` first then falls back to `python`
- In PowerShell, `.venv\Scripts\python.exe` triggers module autoload error — always use `python` directly

## Loading Page (webpage/loading.html)

### Stuck on "Ready — Redirecting now..."
**Root cause:** `startup_status.js` writes `ready: 1` (number) but JS checked `status.ready === true` (strict boolean). `1 === true` is `false`.
**Fix:** Use truthy check: `if (status.ready)` instead of `if (status.ready === true)`.

### Two cards / duplicate page rendering
**Root cause:** `loading.html` had two complete `<html>` documents concatenated. Browser renders both.
**Fix:** Delete the duplicate — keep only the version with dynamic `readStatus()` polling.

## Static Dashboard (webpage/index.html)

### index.html gets overwritten on `open_dashboard.bat`
- `scripts/generate_dashboard.py` regenerates `webpage/index.html` on every full run
- Any manual edits to the JS inside `index.html` will be lost
- To persist changes, edit `scripts/generate_dashboard.py` instead
- Fast mode (`open_dashboard_fast.bat`) skips regeneration — safe for manual edits

## Dashboard Bat Files

| File | Mode | What it does |
|---|---|---|
| `open_dashboard.bat` | full | Refresh data → generate dashboard → open browser |
| `open_dashboard_fast.bat` | fast | Skip refresh/generate → open existing snapshot |
| `start_investor.bat` | streamlit | Start Streamlit `dashboard.py` on port 8502 |

## Decision Matrix Table

### Edits to index.html get overwritten
- `scripts/generate_dashboard.py` regenerates `webpage/index.html` on every `open_dashboard.bat` full run
- **All UI changes (including decision matrix) must go in `scripts/generate_dashboard.py`**, not `webpage/index.html`
- HTML template: search for `tab-buffett` in `generate_dashboard.py`
- JS rendering: search for `renderBuffettTab` in `generate_dashboard.py`

### Decision matrix is in `renderBuffettTab()`
- Layout: 3 equal `col-lg-4` columns — Scorecard | Radar | Decision Analysis
- Top half of Decision Analysis card: large action text (e.g. "Hold") with colored background
- Bottom half: 5×5 matrix table with colored cells + emoji icons
- Current position marked with ◀ and bold border

### Unicode / emoji in generate_dashboard.py
- Python `HTML_TEMPLATE` is a triple-quoted string — backslash-u escapes like `\u00b7` get interpreted by Python, not JS
- Use actual Unicode characters (✅ 🟢 ⚪ 🟠 🔴 · ≥ ≤ ◀) directly in the template
- Surrogate pairs (`\ud83d\udfe2`) cause `UnicodeEncodeError` — never use them
- `\u{1F7E2}` syntax fails in Python strings — not supported

## Port Assignments
- **8502** — Streamlit dashboard (`dashboard.py`)
- **8503** — RAG Flask server (`scripts/rag_server.py`)
