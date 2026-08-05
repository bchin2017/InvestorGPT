"""
Downloads 10-K annual reports from SEC EDGAR for Intel and Micron.
Saves each filing as an HTML file under data/10k/.
"""

import json
import time
import urllib.request
from pathlib import Path

COMPANIES = {
    "Intel": "0000050863",
    "Micron": "0000723125",
}

# Fiscal years to collect (filing date range filter)
TARGET_YEARS = {2023, 2024, 2025}

OUTPUT_DIR = Path("data/10k")
HEADERS = {"User-Agent": "InvestorGPT research@example.com"}


def edgar_get(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get_10k_filings(cik: str) -> list[dict]:
    padded = cik.lstrip("0").zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{padded}.json"
    data = edgar_get(url)
    filings = data.get("filings", {}).get("recent", {})

    results = []
    forms = filings.get("form", [])
    dates = filings.get("filingDate", [])
    accessions = filings.get("accessionNumber", [])
    primary_docs = filings.get("primaryDocument", [])

    for form, date, accession, doc in zip(forms, dates, accessions, primary_docs):
        if form == "10-K" and int(date[:4]) in TARGET_YEARS:
            results.append({
                "form": form,
                "date": date,
                "accession": accession.replace("-", ""),
                "accession_raw": accession,
                "primary_doc": doc,
            })

    return results


def download_filing(company: str, cik: str, filing: dict) -> Path:
    cik_num = cik.lstrip("0")
    acc = filing["accession"]
    doc = filing["primary_doc"]
    url = f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{acc}/{doc}"

    year = filing["date"][:4]
    filename = f"{company}_10K_{year}_{filing['date']}.html"
    output_path = OUTPUT_DIR / filename

    if output_path.exists():
        print(f"  Already downloaded: {filename}")
        return output_path

    print(f"  Downloading: {filename}")
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        output_path.write_bytes(resp.read())

    time.sleep(0.5)  # respect EDGAR rate limit
    return output_path


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for company, cik in COMPANIES.items():
        print(f"\n{company} (CIK {cik})")
        filings = get_10k_filings(cik)

        if not filings:
            print("  No 10-K filings found for target years.")
            continue

        for filing in sorted(filings, key=lambda f: f["date"]):
            print(f"  Found: 10-K filed {filing['date']}")
            path = download_filing(company, cik, filing)
            print(f"  Saved: {path}")

    print("\nDone. Files saved to", OUTPUT_DIR)


if __name__ == "__main__":
    main()
