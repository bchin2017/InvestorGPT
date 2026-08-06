# InvestorGPT — Signal & Buffett Score Logic

**Last updated:** 2026-08-06  
**Source:** `dashboard.py`

---

## Overview

Three analytical engines run per company (INTC, MU):

1. **Buffett Scorecard (Quality)** — `compute_buffett_scores(df, ticker)`
2. **10-Factor Buy/Sell Signal (Timing)** — `_compute_signal_factors(ps)`
3. **Decision Matrix** — `_get_decision_matrix_action(buffett_score, signal_score)`

---

## 1) Buffett Scorecard (Quality Score)

Scores each principle 1–10, combines with weighted sum × 10 → final score out of 100.

| Principle | Weight | Key Inputs |
|---|---:|---|
| Intrinsic Value | 0.15 | DCF: avg positive EPS × 1.03 / 0.07 |
| Margin of Safety | 0.15 | (IV − Price) / IV × 100 |
| Economic Moat | 0.12 | Average of per-company moat factor scores |
| Consistent Earnings | 0.10 | % of years with positive EPS |
| Return on Equity | 0.10 | Average ROE (positive years), recent ROE |
| Low Debt | 0.08 | Latest Debt/Equity ratio |
| Management Quality | 0.08 | Qualitative (MU=7, INTC=6) |
| Long-term Value | 0.08 | 10-year annualised price return |
| Contrarian Signal | 0.07 | 52-week range position (lower = more contrarian) |
| Downside Protection | 0.07 | Max drawdown over 5 years |

**Intrinsic Value (simplified DCF):**

```python
avg_eps = mean(eps values > 0)
intrinsic_value = avg_eps * 1.03 / 0.07   # Graham: 3% growth, 7% discount
```

---

## 2) 10-Factor Buy/Sell Signal (Timing Score)

Score range: **0 = Strong Buy → 100 = Strong Sell**  
The 2-Year Z-Score carries the highest weight (20%) — the Buffett value anchor.

| Factor | Weight | Description |
|---|---:|---|
| RSI(14) | 0.12 | Wilder's EWM-smoothed RSI |
| Stochastic RSI | 0.07 | RSI position within its own 14-period range |
| Bollinger %B | 0.10 | Price position within 20d, 2σ Bollinger bands |
| 2-Year Z-Score | 0.20 | How far price is from its 2-year rolling mean |
| 52-Week Position | 0.08 | Price position in the 52-week high-low range |
| 200-Day MA Dev. | 0.12 | % deviation from 200-day moving average |
| MA Convergence | 0.08 | 50-day vs 200-day gap (Golden/Death Cross proxy) |
| MACD Histogram | 0.08 | MACD line minus signal line, normalised |
| Volatility Regime | 0.08 | 20d vs 60d vol ratio × price direction |
| 10-Day ROC | 0.07 | 10-day rate of change |

**Signal formula:**

```python
signal_score = clip(
    rsi*0.12 + stoch_rsi*0.07 + bb*0.10 + zscore*0.20 +
    pos52*0.08 + ma200*0.12 + ma_conv*0.08 + macd*0.08 +
    vol_regime*0.08 + roc10*0.07, 0, 100)
```

---

## 3) Decision Matrix (Quality × Timing)

|  | Strong Buy ≤30 | Buy 30–50 | Neutral 50–65 | Caution 65–80 | Sell >80 |
|---|---|---|---|---|---|
| **Excellent ≥75** | BUY MAX | BUY, DCA | Hold | Hold | Take Profit |
| **Good 60–74** | BUY | BUY, DCA | Hold | Hold | Reduce |
| **Average 45–59** | Buy Small | Hold | Hold | Hold | Reduce |
| **Weak 30–44** | Do Not Buy | Do Not Buy | Sell Partially | Sell | Sell |
| **Poor <30** | Do Not Buy | Do Not Buy | Sell | Sell | Sell All |

---

## 4) ARIMA + Monte Carlo Forecast

- **ARIMA(2,1,2)** fit on monthly log-prices → 18-month forecast
- **Monte Carlo** 10,000 simulations from daily return μ/σ
- **Ensemble**: 40% ARIMA + 60% Monte Carlo

Bear / Base / Bull from ARIMA lower/mean/upper + MC P10/mean/P90 blended by weights.

---

## 5) Moat Factors by Company

### Intel (INTC)

| Factor | Score /10 |
|---|---:|
| x86 Dominance | 7 |
| Fab Capacity | 8 |
| CHIPS Act | 8 |
| Patent Portfolio | 7 |
| Brand | 6 |
| Switching Costs | 5 |

### Micron (MU)

| Factor | Score /10 |
|---|---:|
| HBM Leadership | 9 |
| DRAM Market Share | 8 |
| NAND Production | 7 |
| Manufacturing Scale | 8 |
| R&D Pipeline | 8 |

---

## 6) Fundamental Data Sources

All hardcoded in `dashboard.py → FUNDAMENTALS` dict.  
Raw values extracted from SEC 10-K filings using `scripts/generate_dashboard.py`.

| Company | Fiscal Years Available | Key Note |
|---|---|---|
| Intel | 2015–2025 (EPS/ROE/D-E), 2022–2024 (revenue/NI/GM) | FY ends December |
| Micron | 2020–2025 (EPS/ROE/D-E), 2022–2025 (revenue/NI/GM) | FY ends August |
