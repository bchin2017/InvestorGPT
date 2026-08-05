"""
Parses downloaded 10-K HTML files for key financial metrics,
fetches stock price history via yfinance, and writes index.html.
"""

import json
import re
from pathlib import Path

import yfinance as yf

DATA_DIR = Path("data/10k")
OUTPUT = Path("index.html")


# ---------------------------------------------------------------------------
# Financial extraction — regex on raw HTML (reliable for XBRL inline filings)
# ---------------------------------------------------------------------------

# Matches comma-grouped numbers: 53,101 or (16,639)
_NUM_RE = re.compile(r"\((\d{1,3}(?:,\d{3})+)\)|(?<![.\d])(\d{1,3}(?:,\d{3})+)(?![,\d])")


def _parse_num(m: re.Match) -> int | None:
    neg, pos = m.group(1), m.group(2)
    n = int((neg or pos).replace(",", ""))
    if 2015 <= n <= 2030:   # reject bare year labels
        return None
    return -n if neg else n


def extract_after_label(
    html: str, label: str, count: int = 3, window: int = 5000,
    section_hint: str | None = None,
) -> list[int]:
    """Find label in html (optionally after section_hint), return first count financial integers."""
    start = 0
    if section_hint:
        hint_idx = html.lower().find(section_hint.lower())
        if hint_idx >= 0:
            start = hint_idx
    idx = html.lower().find(label.lower(), start)
    if idx < 0:
        return []
    block = html[idx: idx + window]
    results: list[int] = []
    seen: set[int] = set()
    for m in _NUM_RE.finditer(block):
        v = _parse_num(m)
        if v is None or abs(v) < 500:
            continue
        if v in seen:
            continue
        seen.add(v)
        results.append(v)
        if len(results) == count:
            break
    return results


# Each config uses only the most recent filing which contains 3 years of data
_CONFIGS = {
    "Intel": {
        "file": "Intel_10K_2025_2025-01-31.html",   # covers FY2024, FY2023, FY2022
        "fiscal_years": [2024, 2023, 2022],
        "labels": {
            "revenue":      ("Net revenue",  None),
            "net_income":   ("Net income",   None),
            "gross_margin": ("Gross margin", None),
        },
    },
    "Micron": {
        "file": "Micron_10K_2025_2025-10-03.html",  # covers FY2025, FY2024, FY2023
        "fiscal_years": [2025, 2024, 2023],
        "labels": {
            # section_hint skips XBRL metadata and finds income statement occurrence
            "revenue":      ("Revenue",      "statements of operations"),
            "net_income":   ("Net income",   "statements of operations"),
            "gross_margin": ("Gross margin", "statements of operations"),
        },
    },
}


def load_financials() -> dict:
    result = {}
    for company, cfg in _CONFIGS.items():
        path = DATA_DIR / cfg["file"]
        if not path.exists():
            print(f"  Missing: {path}")
            result[company] = {}
            continue
        html = path.read_text(encoding="utf-8", errors="ignore")
        print(f"  {company}: {path.name}")
        annual: dict[int, dict] = {}
        for key, (label, hint) in cfg["labels"].items():
            vals = extract_after_label(html, label, section_hint=hint)
            print(f"    {label}: {vals}")
            for i, fy in enumerate(cfg["fiscal_years"]):
                if fy not in annual:
                    annual[fy] = {}
                annual[fy][key] = vals[i] if i < len(vals) else None
        result[company] = annual
    return result


# ---------------------------------------------------------------------------
# Stock price history
# ---------------------------------------------------------------------------

def get_stock_prices(tickers: list[str], period: str = "3y") -> dict:
    prices = {}
    for ticker in tickers:
        try:
            hist = yf.Ticker(ticker).history(period=period)["Close"]
            prices[ticker] = {
                "dates": [d.strftime("%Y-%m-%d") for d in hist.index],
                "prices": [round(float(v), 2) for v in hist.values],
            }
        except Exception as e:
            print(f"  Stock fetch failed for {ticker}: {e}")
            prices[ticker] = {"dates": [], "prices": []}
    return prices


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>SemiconInvest AI – InvestorGPT Dashboard</title>
<link rel="stylesheet"
  href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"/>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<style>
  body {{ background:#f8f9fa; font-family:'Segoe UI',sans-serif; }}
  .card {{ border:none; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,.08); }}
  h1 {{ font-size:1.6rem; font-weight:700; }}
  .badge-source {{ font-size:.75rem; }}
  canvas {{ max-height:320px; }}
  .caveat {{ font-size:.8rem; color:#888; }}
</style>
</head>
<body>
<div class="container py-4">

  <div class="d-flex align-items-center mb-1 gap-2">
    <h1>SemiconInvest AI</h1>
    <span class="badge bg-primary badge-source">Intel &amp; Micron 10-K Filings</span>
  </div>
  <p class="text-muted mb-4">
    Data extracted from SEC EDGAR annual reports (10-K) · Stock prices via Yahoo Finance
  </p>

  <!-- Data availability notice -->
  <div class="card mb-4 p-3">
    <h6 class="mb-2 fw-semibold">What this dashboard shows</h6>
    <div class="row g-2">
      <div class="col-md-4">
        <div class="p-2 bg-success bg-opacity-10 rounded">
          <strong class="text-success">✓ From 10-K filings</strong>
          <ul class="mb-0 small mt-1">
            <li>Annual revenue</li>
            <li>Net income / loss</li>
            <li>Gross margin</li>
          </ul>
        </div>
      </div>
      <div class="col-md-4">
        <div class="p-2 bg-primary bg-opacity-10 rounded">
          <strong class="text-primary">✓ From Yahoo Finance</strong>
          <ul class="mb-0 small mt-1">
            <li>Stock price history (3 years)</li>
            <li>Real-time price</li>
          </ul>
        </div>
      </div>
      <div class="col-md-4">
        <div class="p-2 bg-secondary bg-opacity-10 rounded">
          <strong class="text-secondary">✗ Not available here</strong>
          <ul class="mb-0 small mt-1">
            <li>Analyst forecasts</li>
            <li>P/E ratio (needs live price)</li>
            <li>Quarterly earnings</li>
          </ul>
        </div>
      </div>
    </div>
  </div>

  <!-- Revenue & Net Income charts -->
  <div class="row g-3 mb-3">
    <div class="col-md-6">
      <div class="card p-3 h-100">
        <h6 class="fw-semibold">Annual Revenue (USD millions)</h6>
        <canvas id="revenueChart"></canvas>
        <p class="caveat mt-2 mb-0">Source: SEC 10-K filings</p>
      </div>
    </div>
    <div class="col-md-6">
      <div class="card p-3 h-100">
        <h6 class="fw-semibold">Net Income / Loss (USD millions)</h6>
        <canvas id="incomeChart"></canvas>
        <p class="caveat mt-2 mb-0">Source: SEC 10-K filings · Negative = net loss</p>
      </div>
    </div>
  </div>

  <!-- Stock price chart -->
  <div class="card p-3 mb-3">
    <h6 class="fw-semibold">Stock Price – 3 Year History (USD)</h6>
    <canvas id="stockChart"></canvas>
    <p class="caveat mt-2 mb-0">Source: Yahoo Finance · Prices are closing prices</p>
  </div>

  <!-- Metrics table -->
  <div class="card p-3">
    <h6 class="fw-semibold mb-3">Key Metrics Comparison</h6>
    <div class="table-responsive">
      <table class="table table-hover table-sm">
        <thead class="table-light">
          <tr>
            <th>Metric</th>
            <th>Intel FY2022</th>
            <th>Intel FY2023</th>
            <th>Intel FY2024</th>
            <th>Micron FY2023</th>
            <th>Micron FY2024</th>
            <th>Micron FY2025</th>
          </tr>
        </thead>
        <tbody id="metricsTable"></tbody>
      </table>
    </div>
    <p class="caveat mb-0">All figures in USD millions · Source: SEC 10-K annual filings</p>
  </div>

</div>

<script>
const DATA = {data_json};

// ---- helpers ----
function fmt(v) {{
  if (v == null) return 'N/A';
  var s = Math.abs(v).toLocaleString();
  return v < 0 ? '(' + s + ')' : s;
}}

// ---- revenue chart ----
const rCtx = document.getElementById('revenueChart');
new Chart(rCtx, {{
  type: 'bar',
  data: {{
    labels: DATA.revenue_labels,
    datasets: [
      {{ label:'Intel', data: DATA.intel_revenue,
         backgroundColor:'rgba(0,104,181,.75)', borderRadius:4 }},
      {{ label:'Micron', data: DATA.micron_revenue,
         backgroundColor:'rgba(0,162,145,.75)', borderRadius:4 }},
    ]
  }},
  options: {{ responsive:true, plugins:{{ legend:{{ position:'top' }} }},
    scales:{{ y:{{ beginAtZero:true }} }} }}
}});

// ---- income chart ----
const iCtx = document.getElementById('incomeChart');
new Chart(iCtx, {{
  type: 'bar',
  data: {{
    labels: DATA.income_labels,
    datasets: [
      {{ label:'Intel', data: DATA.intel_income,
         backgroundColor: DATA.intel_income.map(v => v < 0 ? 'rgba(220,53,69,.75)' : 'rgba(0,104,181,.75)'),
         borderRadius:4 }},
      {{ label:'Micron', data: DATA.micron_income,
         backgroundColor: DATA.micron_income.map(v => v < 0 ? 'rgba(255,153,0,.75)' : 'rgba(0,162,145,.75)'),
         borderRadius:4 }},
    ]
  }},
  options: {{ responsive:true, plugins:{{ legend:{{ position:'top' }} }} }}
}});

// ---- stock price chart ----
const sCtx = document.getElementById('stockChart');
new Chart(sCtx, {{
  type: 'line',
  data: {{
    labels: DATA.intc_stock.dates,
    datasets: [
      {{ label:'INTC', data: DATA.intc_stock.prices,
         borderColor:'rgb(0,104,181)', backgroundColor:'rgba(0,104,181,.05)',
         borderWidth:1.5, pointRadius:0, tension:.2, fill:true }},
      {{ label:'MU', data: DATA.mu_stock.prices,
         borderColor:'rgb(0,162,145)', backgroundColor:'rgba(0,162,145,.05)',
         borderWidth:1.5, pointRadius:0, tension:.2, fill:true }},
    ]
  }},
  options: {{ responsive:true, plugins:{{ legend:{{ position:'top' }} }},
    scales:{{ x:{{ ticks:{{ maxTicksLimit:12 }} }} }} }}
}});

// ---- metrics table ----
const rows = [
  ['Revenue', DATA.intel_rev_table, DATA.micron_rev_table],
  ['Net Income', DATA.intel_inc_table, DATA.micron_inc_table],
  ['Gross Margin', DATA.intel_gm_table, DATA.micron_gm_table],
];
const tbody = document.getElementById('metricsTable');
rows.forEach(([label, intel, micron]) => {{
  const tr = document.createElement('tr');
  tr.innerHTML = `<td><strong>${{label}}</strong></td>` +
    intel.map(v => `<td>${{fmt(v)}}</td>`).join('') +
    micron.map(v => `<td>${{fmt(v)}}</td>`).join('');
  tbody.appendChild(tr);
}});
</script>
</body>
</html>
"""


def build_dashboard() -> None:
    print("Extracting financials from 10-K files...")
    fin = load_financials()

    intel_years  = [2022, 2023, 2024]
    micron_years = [2023, 2024, 2025]

    def _v(company, metric, years):
        return [fin.get(company, {}).get(y, {}).get(metric) for y in years]

    labels = [f"Intel FY{y}" for y in intel_years] + [f"Micron FY{y}" for y in micron_years]

    print("\nFetching stock prices...")
    stocks = get_stock_prices(["INTC", "MU"])

    data_json = json.dumps({
        "revenue_labels":   labels,
        "income_labels":    labels,
        "intel_revenue":    _v("Intel",  "revenue",      intel_years),
        "micron_revenue":   _v("Micron", "revenue",      micron_years),
        "intel_income":     _v("Intel",  "net_income",   intel_years),
        "micron_income":    _v("Micron", "net_income",   micron_years),
        "intc_stock":       stocks.get("INTC", {"dates": [], "prices": []}),
        "mu_stock":         stocks.get("MU",   {"dates": [], "prices": []}),
        "intel_rev_table":  _v("Intel",  "revenue",      intel_years),
        "intel_inc_table":  _v("Intel",  "net_income",   intel_years),
        "intel_gm_table":   _v("Intel",  "gross_margin", intel_years),
        "micron_rev_table": _v("Micron", "revenue",      micron_years),
        "micron_inc_table": _v("Micron", "net_income",   micron_years),
        "micron_gm_table":  _v("Micron", "gross_margin", micron_years),
    })

    OUTPUT.write_text(HTML_TEMPLATE.format(data_json=data_json), encoding="utf-8")
    print(f"\nDashboard written to {OUTPUT.resolve()}")


if __name__ == "__main__":
    build_dashboard()
