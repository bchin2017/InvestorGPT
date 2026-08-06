"""
Lightweight HTTP server for the AI Chat tab in index.html.
Wraps rag_chatbot.py as a REST API on port 8503.
Provides RAG-only and general AI chat (using server-side API key from .env).

Run:
    python scripts/rag_server.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))
from rag_chatbot import RAGChatbot

app = Flask(__name__)
CORS(app)

ROOT_DIR = Path(__file__).parent.parent
STOCK_DIR = ROOT_DIR / "data" / "stock_history"

bot: RAGChatbot | None = None
client: OpenAI | None = None
_stock_cache: dict[str, pd.DataFrame] = {}

SYSTEM_MSG = (
    "You are SemiconInvest AI, an expert semiconductor investment analyst "
    "and general knowledge assistant. You specialize in Intel (INTC) and "
    "Micron (MU) but can answer ANY question the user asks. When financial "
    "context is provided, use it for data-backed answers with citations. "
    "When no relevant context is available, answer from your general knowledge. "
    "Be concise, accurate, and helpful."
)


def get_bot() -> RAGChatbot:
    global bot
    if bot is None:
        bot = RAGChatbot()
    return bot


def get_client() -> OpenAI:
    global client
    if client is None:
        client = OpenAI()
    return client


# Ticker → company name fragment used to match chunk metadata
_TICKER_COMPANY = {"INTC": "Intel", "MU": "Micron"}


def build_citations(chunks: list, tickers: list[str] | None = None, max_cites: int = 1) -> str:
    """Return a clean, deduplicated citation string from FAISS chunks."""
    allowed: set[str] | None = None
    if tickers:
        allowed = {_TICKER_COMPANY[t] for t in tickers if t in _TICKER_COMPANY}

    seen: set[tuple] = set()
    parts: list[str] = []
    for c in chunks:
        company = c.get("company", "")
        if allowed and not any(name in company for name in allowed):
            continue
        key = (c.get("source", ""), company)
        if key in seen:
            continue
        seen.add(key)
        score = c.get("score", 0)
        parts.append(f"{c.get('source', '')} — {company} ({c.get('section', '')}) [conf: {score:.2f}]")
        if len(parts) >= max_cites:
            break
    return " | ".join(parts)


def load_stock(ticker: str) -> pd.DataFrame | None:
    """Load and cache stock history CSV for a ticker."""
    t = ticker.upper()
    if t in _stock_cache:
        return _stock_cache[t]
    path = STOCK_DIR / f"{t.lower()}_history.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).sort_values("Date")
    _stock_cache[t] = df
    return df


def lookup_stock_price(question: str) -> str | None:
    """If the question asks about a stock price on a date, return the data."""
    # Detect date patterns in the question
    date_patterns = [
        r"(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+(\d{4})",
        r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+(\d{1,2}),?\s+(\d{4})",
        r"(\d{4})-(\d{2})-(\d{2})",
        r"(\d{1,2})/(\d{1,2})/(\d{4})",
    ]
    date_str = None
    for pat in date_patterns:
        m = re.search(pat, question, re.IGNORECASE)
        if m:
            date_str = m.group(0)
            break
    if not date_str:
        return None

    try:
        target_date = pd.to_datetime(date_str)
    except Exception:
        return None

    # Detect which ticker(s) the question refers to
    q_lower = question.lower()
    tickers = []
    if "intc" in q_lower or "intel" in q_lower:
        tickers.append("INTC")
    if "mu" in q_lower or "micron" in q_lower:
        tickers.append("MU")
    if not tickers:
        tickers = ["INTC", "MU"]

    results = []
    for ticker in tickers:
        df = load_stock(ticker)
        if df is None:
            continue
        # Find closest trading day
        df_dates = df["Date"].dt.normalize()
        mask = df_dates == target_date.normalize()
        if mask.any():
            row = df[mask].iloc[0]
        else:
            # Find nearest prior trading day
            prior = df[df_dates <= target_date.normalize()]
            if prior.empty:
                continue
            row = prior.iloc[-1]

        close = row.get("Close") or row.get("Adj Close")
        open_ = row.get("Open")
        high = row.get("High")
        low = row.get("Low")
        vol = row.get("Volume")
        actual_date = row["Date"].strftime("%Y-%m-%d")

        info = (
            f"{ticker} on {actual_date}: "
            f"Open=${float(open_):.2f}, High=${float(high):.2f}, "
            f"Low=${float(low):.2f}, Close=${float(close):.2f}"
        )
        if vol and not pd.isna(vol):
            info += f", Volume={int(vol):,}"
        results.append(info)

    return "\n".join(results) if results else None


# ── Query routing keywords ────────────────────────────────────────────────────
_CSV_PRICE_KW = frozenset({
    "stock price", "share price", "close price", "open price", "closing price",
    "opening price", "price on", "price at", "priced at", "price was", "trading price",
})
_ANALYTICS_KW = frozenset({
    "cagr", "compound annual", "annual return", "yearly return", "monthly return",
    "total return", "cumulative return", "stock performance", "market performance",
    "volatility", "standard deviation", "drawdown", "maximum drawdown", "max drawdown",
    "moving average", "ma50", "ma200", "50-day", "200-day", "50 day", "200 day",
    "outperform", "underperform", "compare return", "return since", "return on investment",
})
_FAISS_KW = frozenset({
    "strategy", "risk factor", "revenue", "net income", "gross margin", "cash flow",
    "r&d", "research and development", "product roadmap", "competition", "market share",
    "outlook", "guidance", "acquisition", "merger", "restructuring", "layoff",
    "artificial intelligence", "hbm", "foundry", "geopolitical", "supply chain",
    "manufacturing", "why did", "what caused", "management", "ceo", "cfo",
    "earnings call", "10-k", "annual report", "sec filing",
})


def classify_query(question: str) -> str:
    """Return retrieval route: csv_price | csv_analytics | faiss | mixed."""
    q = question.lower()
    has_date = bool(re.search(
        r"\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{4}"
        r"|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2},?\s+\d{4}"
        r"|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}",
        q, re.IGNORECASE,
    ))
    csv_score = sum(1 for kw in _CSV_PRICE_KW if kw in q)
    ana_score = sum(1 for kw in _ANALYTICS_KW if kw in q)
    fai_score = sum(1 for kw in _FAISS_KW if kw in q)

    if has_date and ("price" in q or "stock" in q or csv_score > 0):
        return "csv_price"
    if ana_score > 0:
        return "csv_analytics"
    if fai_score > 0 and csv_score == 0 and not has_date:
        return "faiss"
    return "mixed"


def detect_tickers_in_query(question: str) -> list[str]:
    """Return ticker symbols detected in the question."""
    q = question.lower()
    tickers = []
    if "intc" in q or "intel" in q:
        tickers.append("INTC")
    if re.search(r"\bmu\b", q) or "micron" in q:
        tickers.append("MU")
    return tickers or ["INTC", "MU"]


def detect_year_in_query(question: str) -> list[str]:
    """Extract fiscal years (2019–2026) mentioned in the question."""
    years = re.findall(r"\b(20[12]\d)\b", question)
    return list(dict.fromkeys(years))


def compute_stock_analytics(question: str, tickers: list[str], years: list[str]) -> str | None:
    """Compute returns, CAGR, volatility, drawdown from stock CSV data."""
    q = question.lower()
    int_years = [int(y) for y in years if y.isdigit()]
    if len(int_years) >= 2:
        start_year, end_year = min(int_years), max(int_years)
    elif len(int_years) == 1:
        start_year = end_year = int_years[0]
    else:
        end_year = 2024
        start_year = end_year - 2

    results = []
    for ticker in tickers:
        df = load_stock(ticker)
        if df is None:
            continue
        mask = (df["Date"].dt.year >= start_year) & (df["Date"].dt.year <= end_year)
        df_p = df[mask].copy()
        if len(df_p) < 2:
            continue

        close_col = "Close" if "Close" in df_p.columns else "Adj Close"
        close = df_p[close_col].dropna().reset_index(drop=True)
        if len(close) < 2:
            continue

        start_price = float(close.iloc[0])
        end_price = float(close.iloc[-1])
        start_date = df_p["Date"].iloc[0].strftime("%Y-%m-%d")
        end_date = df_p["Date"].iloc[-1].strftime("%Y-%m-%d")
        n_days = len(close)
        n_years_f = n_days / 252

        total_ret = (end_price - start_price) / start_price * 100
        cagr = ((end_price / start_price) ** (1 / n_years_f) - 1) * 100 if n_years_f > 0 else 0
        vol = float(close.pct_change().dropna().std() * (252 ** 0.5) * 100)
        rolling_max = close.cummax()
        max_dd = float(((close - rolling_max) / rolling_max).min() * 100)

        metrics = [
            f"Period: {start_date} \u2192 {end_date}  ({n_days} trading days)",
            f"Start: ${start_price:.2f}  \u2192  End: ${end_price:.2f}",
            f"Total Return: {total_ret:+.1f}%",
            f"CAGR: {cagr:+.1f}%",
            f"Annualized Volatility: {vol:.1f}%",
            f"Maximum Drawdown: {max_dd:.1f}%",
        ]
        if any(w in q for w in ["50-day", "50 day", "ma50", "moving average"]):
            metrics.append(f"50-day MA (period end): ${float(close.rolling(50).mean().iloc[-1]):.2f}")
        if any(w in q for w in ["200-day", "200 day", "ma200"]):
            df_full = load_stock(ticker)
            if df_full is not None:
                fc = df_full["Close" if "Close" in df_full.columns else "Adj Close"].dropna()
                metrics.append(f"200-day MA (full history): ${float(fc.rolling(200).mean().iloc[-1]):.2f}")

        results.append(
            f"[Analytics] {ticker} ({start_year}\u2013{end_year}):\n" +
            "\n".join(f"  \u2022 {m}" for m in metrics)
        )

    return "\n\n".join(results) if results else None


@app.route("/chat", methods=["POST"])
def chat():
    body = request.get_json(force=True)
    question = (body.get("question") or "").strip()
    if not question:
        return jsonify({"error": "No question provided"}), 400

    ticker = body.get("ticker") or None
    source = body.get("source") or None

    b = get_bot()
    chunks = b.retrieve(question, ticker=ticker, source=source)
    answer = b.ask(question, ticker=ticker, source=source)
    cites = [ticker.upper()] if ticker else []
    return jsonify({
        "answer": answer,
        "citations": build_citations(chunks, tickers=cites or None),
    })


@app.route("/health", methods=["GET"])
def health():
    has_key = bool(os.environ.get("OPENAI_API_KEY"))
    return jsonify({"status": "ok", "has_api_key": has_key})


@app.route("/data-sources", methods=["GET"])
def data_sources():
    """Return catalogue of all available data sources and their query route."""
    import json
    from collections import Counter

    # FAISS index stats
    meta_path = ROOT_DIR / "data" / "rag_index" / "chunks_meta.json"
    faiss_stats = {}
    if meta_path.exists():
        chunks = json.loads(meta_path.read_text(encoding="utf-8"))
        faiss_stats = {
            "total_chunks": len(chunks),
            "by_source": dict(Counter(c["metadata"].get("source", "?") for c in chunks)),
            "by_ticker": dict(Counter(c["metadata"].get("ticker", "?") for c in chunks)),
            "by_doc_type": dict(Counter(c["metadata"].get("doc_type", "?") for c in chunks)),
        }

    # Stock CSV stats
    stock_stats = {}
    for csv_path in sorted(STOCK_DIR.glob("*_history.csv")):
        ticker = csv_path.stem.replace("_history", "").upper()
        try:
            df = load_stock(ticker)
            if df is not None:
                stock_stats[ticker] = {
                    "rows": len(df),
                    "from": df["Date"].min().strftime("%Y-%m-%d"),
                    "to": df["Date"].max().strftime("%Y-%m-%d"),
                    "columns": list(df.columns),
                }
        except Exception:
            pass

    sources = [
        {
            "name": "SEC 10-K Filings",
            "source_key": "sec_edgar",
            "route": "faiss_rag",
            "tickers": ["INTC", "MU"],
            "years": ["FY2022", "FY2023", "FY2024"],
            "content": "Annual reports: risk factors, MD&A, financial statements, strategy",
            "chunks": faiss_stats.get("by_source", {}).get("sec_edgar", 0),
            "path": "data/10k/",
        },
        {
            "name": "Macrotrends",
            "source_key": "macrotrends",
            "route": "faiss_rag",
            "tickers": ["INTC", "MU"],
            "content": "Revenue, EPS, net income historical series (annual + quarterly)",
            "chunks": faiss_stats.get("by_source", {}).get("macrotrends", 0),
            "path": "data/crawled/www_macrotrends_net_*",
        },
        {
            "name": "StockAnalysis",
            "source_key": "stockanalysis",
            "route": "faiss_rag",
            "tickers": ["INTC", "MU"],
            "content": "Income statement, balance sheet, cash flow (annual + quarterly)",
            "chunks": faiss_stats.get("by_source", {}).get("stockanalysis", 0),
            "path": "data/crawled/stockanalysis_com_*",
        },
        {
            "name": "CompaniesMarketCap",
            "source_key": "companiesmarketcap",
            "route": "faiss_rag",
            "tickers": ["INTC", "MU"],
            "content": "Historical market cap data",
            "chunks": faiss_stats.get("by_source", {}).get("companiesmarketcap", 0),
            "path": "data/crawled/companiesmarketcap_com_*",
        },
        {
            "name": "Intel Investor Relations",
            "source_key": "intel_ir",
            "route": "faiss_rag",
            "tickers": ["INTC"],
            "content": "SEC filings index, press releases, financial info pages",
            "chunks": faiss_stats.get("by_source", {}).get("intel_ir", 0),
            "path": "data/crawled/www_intc_com_*",
        },
        {
            "name": "Yahoo Finance",
            "source_key": "yahoo_finance",
            "route": "faiss_rag",
            "tickers": ["INTC", "MU"],
            "content": "Quote summary, recent price, PE ratio, 52-week range",
            "chunks": faiss_stats.get("by_source", {}).get("yahoo_finance", 0),
            "path": "data/crawled/finance_yahoo_com_*",
        },
        {
            "name": "Stock Price History (INTC)",
            "source_key": "stock_history",
            "route": "structured_csv",
            "tickers": ["INTC"],
            "content": "Daily OHLCV prices",
            "rows": stock_stats.get("INTC", {}).get("rows"),
            "date_range": f"{stock_stats.get('INTC', {}).get('from', '?')} → {stock_stats.get('INTC', {}).get('to', '?')}",
            "path": "data/stock_history/intc_history.csv",
            "trigger": "Questions containing a specific date + INTC/Intel",
        },
        {
            "name": "Stock Price History (MU)",
            "source_key": "stock_history",
            "route": "structured_csv",
            "tickers": ["MU"],
            "content": "Daily OHLCV prices",
            "rows": stock_stats.get("MU", {}).get("rows"),
            "date_range": f"{stock_stats.get('MU', {}).get('from', '?')} → {stock_stats.get('MU', {}).get('to', '?')}",
            "path": "data/stock_history/mu_history.csv",
            "trigger": "Questions containing a specific date + MU/Micron",
        },
    ]

    return jsonify({
        "sources": sources,
        "faiss_total_chunks": faiss_stats.get("total_chunks", 0),
        "routing_rules": {
            "faiss_rag": "Semantic vector search → top-k chunks → GPT-4o synthesis",
            "structured_csv": "Regex date detection → direct CSV lookup → exact row returned",
            "general_knowledge": "Fallback when no relevant chunks found — GPT-4o general knowledge",
        },
    })


@app.route("/chat/general", methods=["POST"])
def chat_general():
    """Answer any question with intelligent query routing + server-side OpenAI key."""
    body = request.get_json(force=True)
    question = (body.get("question") or "").strip()
    if not question:
        return jsonify({"error": "No question provided"}), 400

    ticker = body.get("ticker") or None
    source = body.get("source") or None
    use_rag = body.get("use_rag", True)
    model = body.get("model", "gpt-4o")
    temperature = float(body.get("temperature", 0.7))
    max_tokens = int(body.get("max_tokens", 2048))

    # ── Intelligent query routing ─────────────────────────────
    query_type = classify_query(question)
    q_tickers = [ticker.upper()] if ticker else detect_tickers_in_query(question)
    q_years = detect_year_in_query(question)

    rag_context = ""
    citations = []

    # ── Route 1: CSV price lookup (specific date queries) ─────
    if query_type in ("csv_price", "mixed"):
        price_data = lookup_stock_price(question)
        if price_data:
            rag_context += f"\n\n[Stock Price Data — CSV]\n{price_data}"
            citations.append("stock_history — Local OHLCV CSV")

    # ── Route 2: Financial analytics (returns, CAGR, etc.) ────
    if query_type == "csv_analytics":
        analytics_data = compute_stock_analytics(question, q_tickers, q_years)
        if analytics_data:
            rag_context += f"\n\n[Financial Analytics — CSV]\n{analytics_data}"
            citations.append("stock_history — Computed from CSV")

    # ── Route 3: FAISS semantic retrieval ─────────────────────
    if use_rag and query_type in ("faiss", "mixed"):
        try:
            b = get_bot()
            year_filter = q_years[0] if len(q_years) == 1 else None
            chunks = b.retrieve(
                question,
                ticker=ticker or (q_tickers[0] if len(q_tickers) == 1 else None),
                source=source,
                year=year_filter,
            )
            if chunks:
                top_score = chunks[0].get("score", 0)
                rag_context += "\n\n[Financial Documents — FAISS RAG]\n" + b.format_context(chunks)
                cite_str = build_citations(chunks, tickers=q_tickers or None)
                if cite_str:
                    citations += cite_str.split(" | ")
                if top_score < 0.3:
                    rag_context += "\n\n[Note: Low retrieval confidence — answer may rely on general knowledge]"
        except Exception:
            pass

    messages = [
        {"role": "system", "content": SYSTEM_MSG + rag_context},
        {"role": "user", "content": question},
    ]

    try:
        c = get_client()
        resp = c.chat.completions.create(
            model=model, messages=messages,
            temperature=temperature, max_tokens=max_tokens,
        )
        answer = resp.choices[0].message.content or ""
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "answer": answer,
        "citations": " | ".join(citations),
        "mode": "server",
        "query_type": query_type,
        "tickers_detected": q_tickers,
        "years_detected": q_years,
    })


@app.route("/analytics", methods=["POST"])
def analytics():
    """Directly compute stock analytics from CSV without an LLM call."""
    body = request.get_json(force=True)
    question = (body.get("question") or "performance summary").strip()
    tickers_req = body.get("tickers") or []
    years_req = body.get("years") or []

    tickers = [t.upper() for t in tickers_req] if tickers_req else detect_tickers_in_query(question)
    years = [str(y) for y in years_req] if years_req else detect_year_in_query(question)

    data = compute_stock_analytics(question, tickers, years)
    if not data:
        return jsonify({"error": "No analytics available for the given tickers/years."}), 404

    return jsonify({"analytics": data, "tickers": tickers, "years": years})


if __name__ == "__main__":
    print("Starting RAG server on http://localhost:8503")
    print("Press Ctrl+C to stop.\n")
    get_bot()  # pre-load index
    app.run(host="127.0.0.1", port=8503, debug=False)
