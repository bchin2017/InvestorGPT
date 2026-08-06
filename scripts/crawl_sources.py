"""
Crawl financial data sources using Firecrawl and save as markdown.
Outputs go to data/crawled/ with companion metadata JSON files.

Run:
    python scripts/crawl_sources.py
    python scripts/crawl_sources.py --source macrotrends
    python scripts/crawl_sources.py --source all
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from firecrawl import FirecrawlApp

load_dotenv()

ROOT_DIR = Path(__file__).parent.parent
OUTPUT_DIR = ROOT_DIR / "data" / "crawled"

# ── Source definitions ────────────────────────────────────────
SOURCES: list[dict] = [
    # Macrotrends — INTC
    {
        "url": "https://www.macrotrends.net/stocks/charts/INTC/intel/revenue",
        "company": "Intel", "ticker": "INTC",
        "doc_type": "financial_history", "section": "revenue",
        "source_name": "macrotrends",
    },
    {
        "url": "https://www.macrotrends.net/stocks/charts/INTC/intel/eps-earnings-per-share-diluted",
        "company": "Intel", "ticker": "INTC",
        "doc_type": "financial_history", "section": "eps",
        "source_name": "macrotrends",
    },
    {
        "url": "https://www.macrotrends.net/stocks/charts/INTC/intel/net-income",
        "company": "Intel", "ticker": "INTC",
        "doc_type": "financial_history", "section": "net_income",
        "source_name": "macrotrends",
    },
    {
        "url": "https://www.macrotrends.net/stocks/charts/INTC/intel/cash-flow-statement",
        "company": "Intel", "ticker": "INTC",
        "doc_type": "financial_history", "section": "cash_flow",
        "source_name": "macrotrends",
    },
    {
        "url": "https://www.macrotrends.net/stocks/charts/INTC/intel/balance-sheet",
        "company": "Intel", "ticker": "INTC",
        "doc_type": "financial_history", "section": "balance_sheet",
        "source_name": "macrotrends",
    },
    # Macrotrends — MU
    {
        "url": "https://www.macrotrends.net/stocks/charts/MU/micron-technology/revenue",
        "company": "Micron", "ticker": "MU",
        "doc_type": "financial_history", "section": "revenue",
        "source_name": "macrotrends",
    },
    {
        "url": "https://www.macrotrends.net/stocks/charts/MU/micron-technology/eps-earnings-per-share-diluted",
        "company": "Micron", "ticker": "MU",
        "doc_type": "financial_history", "section": "eps",
        "source_name": "macrotrends",
    },
    {
        "url": "https://www.macrotrends.net/stocks/charts/MU/micron-technology/net-income",
        "company": "Micron", "ticker": "MU",
        "doc_type": "financial_history", "section": "net_income",
        "source_name": "macrotrends",
    },
    # StockAnalysis
    {
        "url": "https://stockanalysis.com/stocks/intc/financials/",
        "company": "Intel", "ticker": "INTC",
        "doc_type": "financial_statements", "section": "financials",
        "source_name": "stockanalysis",
    },
    {
        "url": "https://stockanalysis.com/stocks/intc/financials/quarterly/",
        "company": "Intel", "ticker": "INTC",
        "doc_type": "financial_statements", "section": "financials_quarterly",
        "source_name": "stockanalysis",
    },
    {
        "url": "https://stockanalysis.com/stocks/mu/financials/",
        "company": "Micron", "ticker": "MU",
        "doc_type": "financial_statements", "section": "financials",
        "source_name": "stockanalysis",
    },
    {
        "url": "https://stockanalysis.com/stocks/mu/financials/quarterly/",
        "company": "Micron", "ticker": "MU",
        "doc_type": "financial_statements", "section": "financials_quarterly",
        "source_name": "stockanalysis",
    },
    # CompaniesMarketCap
    {
        "url": "https://companiesmarketcap.com/intel/marketcap/",
        "company": "Intel", "ticker": "INTC",
        "doc_type": "market_cap", "section": "market_cap_history",
        "source_name": "companiesmarketcap",
    },
    {
        "url": "https://companiesmarketcap.com/micron-technology/marketcap/",
        "company": "Micron", "ticker": "MU",
        "doc_type": "market_cap", "section": "market_cap_history",
        "source_name": "companiesmarketcap",
    },
    # Intel Investor Relations
    {
        "url": "https://www.intc.com/financial-info",
        "company": "Intel", "ticker": "INTC",
        "doc_type": "investor_relations", "section": "financial_info",
        "source_name": "intel_ir",
    },
    {
        "url": "https://www.intc.com/financial-info/sec-filings",
        "company": "Intel", "ticker": "INTC",
        "doc_type": "investor_relations", "section": "sec_filings",
        "source_name": "intel_ir",
    },
    {
        "url": "https://www.intc.com/news-events/press-releases",
        "company": "Intel", "ticker": "INTC",
        "doc_type": "investor_relations", "section": "press_releases",
        "source_name": "intel_ir",
    },
    # Micron Investor Relations
    {
        "url": "https://investors.micron.com/financial-information/quarterly-results",
        "company": "Micron", "ticker": "MU",
        "doc_type": "investor_relations", "section": "quarterly_results",
        "source_name": "micron_ir",
    },
    {
        "url": "https://investors.micron.com/news-releases",
        "company": "Micron", "ticker": "MU",
        "doc_type": "investor_relations", "section": "news_releases",
        "source_name": "micron_ir",
    },
    # Yahoo Finance summary pages
    {
        "url": "https://finance.yahoo.com/quote/INTC/",
        "company": "Intel", "ticker": "INTC",
        "doc_type": "stock_summary", "section": "quote",
        "source_name": "yahoo_finance",
    },
    {
        "url": "https://finance.yahoo.com/quote/MU/",
        "company": "Micron", "ticker": "MU",
        "doc_type": "stock_summary", "section": "quote",
        "source_name": "yahoo_finance",
    },
]


def safe_filename(url: str) -> str:
    """Derive a filesystem-safe name from a URL."""
    name = re.sub(r"https?://", "", url)
    name = re.sub(r"[^\w]", "_", name).strip("_")
    return name[:120]


def crawl_single(app: FirecrawlApp, source: dict) -> bool:
    """Scrape one URL and save markdown + metadata. Returns True on success."""
    url = source["url"]
    slug = safe_filename(url)
    md_path = OUTPUT_DIR / f"{slug}.md"
    meta_path = OUTPUT_DIR / f"{slug}.meta.json"

    print(f"  Scraping: {url}")
    try:
        result = app.scrape_url(url, formats=["markdown"])
    except Exception as e:
        print(f"  FAILED: {e}")
        return False

    markdown = (result.markdown or "").strip()
    if not markdown:
        print("  WARNING: Empty content returned (page may block scrapers)")
        return False

    md_path.write_text(markdown, encoding="utf-8")

    metadata = {
        "source": source["source_name"],
        "company": source["company"],
        "ticker": source["ticker"],
        "doc_type": source["doc_type"],
        "section": source["section"],
        "url": url,
        "date_crawled": datetime.now().isoformat(),
        "char_count": len(markdown),
    }
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"  Saved: {md_path.name} ({len(markdown):,} chars)")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl financial data sources")
    parser.add_argument(
        "--source", default="all",
        help="Source name filter (macrotrends, stockanalysis, companiesmarketcap, "
             "intel_ir, micron_ir, yahoo_finance) or 'all'",
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    app = FirecrawlApp()

    targets = SOURCES
    if args.source != "all":
        targets = [s for s in SOURCES if s["source_name"] == args.source]
        if not targets:
            print(f"Unknown source: {args.source}")
            print("Available:", sorted({s["source_name"] for s in SOURCES}))
            return

    print(f"Crawling {len(targets)} URLs...")
    ok, fail = 0, 0
    for src in targets:
        if crawl_single(app, src):
            ok += 1
        else:
            fail += 1
        time.sleep(1)  # rate-limit between requests

    print(f"\nDone. {ok} succeeded, {fail} failed.")
    print(f"Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
