"""
Multi-ticker market data refresh from Yahoo Finance.

Fetches daily OHLCV history for INTC and MU (configurable).
Saves CSVs to data/stock_history/ and metadata to .cache/market_data_meta.json.

Run:
    python scripts/refresh_data.py
    python scripts/refresh_data.py --force
    python scripts/refresh_data.py --tickers INTC MU AMD NVDA
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone

import pandas as pd
import requests

DEFAULT_TICKERS = ["INTC", "MU"]
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(ROOT_DIR, ".cache")
DATA_DIR = os.path.join(ROOT_DIR, "data", "stock_history")
META_PATH = os.path.join(CACHE_DIR, "market_data_meta.json")

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def load_meta() -> dict:
    if not os.path.exists(META_PATH):
        return {}
    try:
        with open(META_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_meta(meta: dict) -> None:
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def fetch_from_yahoo(ticker: str, timeout: int = 30) -> pd.DataFrame:
    """Fetch full daily OHLCV history from Yahoo Finance chart API."""
    url = YAHOO_CHART_URL.format(ticker=ticker)
    params = {
        "period1": "0",
        "period2": str(int(time.time()) + 86400),
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true",
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, params=params, headers=headers, timeout=timeout)
    r.raise_for_status()
    payload = r.json()

    result = (((payload or {}).get("chart") or {}).get("result") or [None])[0]
    if not result:
        raise RuntimeError(f"Yahoo response missing chart.result for {ticker}")

    timestamps = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [None])[0] or {}
    adjclose = ((result.get("indicators") or {}).get("adjclose") or [None])[0] or {}

    if not timestamps:
        raise RuntimeError(f"No timestamps in Yahoo response for {ticker}")

    df = pd.DataFrame({
        "Date": pd.to_datetime(timestamps, unit="s", utc=True).tz_convert(None),
        "Open": quote.get("open", []),
        "High": quote.get("high", []),
        "Low": quote.get("low", []),
        "Close": quote.get("close", []),
        "Adj Close": adjclose.get("adjclose", []),
        "Volume": quote.get("volume", []),
    })

    df = df.dropna(subset=["Date", "Close"]).copy()
    df = df.sort_values("Date").drop_duplicates(subset=["Date"], keep="last")
    for col in ["Open", "High", "Low", "Close", "Adj Close", "Volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Close"])

    if df.empty:
        raise RuntimeError(f"Yahoo returned empty history for {ticker}")
    return df


def refresh_ticker(ticker: str, force: bool = False) -> dict:
    """Refresh one ticker. Returns the new metadata dict."""
    meta = load_meta()
    today = datetime.now().strftime("%Y-%m-%d")
    csv_path = os.path.join(DATA_DIR, f"{ticker.lower()}_history.csv")
    ticker_meta = meta.get(ticker, {})

    if not force and os.path.exists(csv_path) and ticker_meta.get("fetched_on") == today:
        log(f"{ticker}: already refreshed today ({today}). Skipping.")
        return ticker_meta

    log(f"{ticker}: fetching from Yahoo Finance...")
    df = fetch_from_yahoo(ticker)
    df.to_csv(csv_path, index=False)

    new_meta = {
        "ticker": ticker,
        "source_api": YAHOO_CHART_URL.format(ticker=ticker),
        "fetched_on": today,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "rows": int(len(df)),
        "start_date": str(df["Date"].min().date()),
        "end_date": str(df["Date"].max().date()),
        "last_close": float(df["Close"].iloc[-1]),
        "csv_path": csv_path,
    }
    meta[ticker] = new_meta
    save_meta(meta)

    log(f"{ticker}: rows={new_meta['rows']}, "
        f"range={new_meta['start_date']} → {new_meta['end_date']}, "
        f"last_close=${new_meta['last_close']:.2f}")
    return new_meta


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh market data from Yahoo Finance.")
    parser.add_argument("--tickers", nargs="+", default=DEFAULT_TICKERS,
                        help="Tickers to refresh (default: INTC MU)")
    parser.add_argument("--force", action="store_true",
                        help="Refresh even if already fetched today")
    args = parser.parse_args()

    errors: list[str] = []
    for ticker in [t.upper() for t in args.tickers]:
        try:
            refresh_ticker(ticker, force=args.force)
        except Exception as e:
            log(f"{ticker}: ERROR — {e}")
            errors.append(ticker)

    if errors:
        log(f"Failed tickers: {errors}")
        return 1
    log("All tickers refreshed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
