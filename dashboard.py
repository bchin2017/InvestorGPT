"""
InvestorGPT — Buffett AI Advisor for Semiconductors
Multi-company analysis: Intel (INTC) and Micron (MU)
Run: streamlit run dashboard.py
"""
import warnings
warnings.filterwarnings('ignore')

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import datetime
from statsmodels.tsa.arima.model import ARIMA
import os
import json
from dotenv import load_dotenv

load_dotenv()

# ── Page Config ──────────────────────────────────────────────
st.set_page_config(
    page_title="InvestorGPT",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Constants ────────────────────────────────────────────────
TICKERS = ['INTC', 'MU']
TICKER_NAMES = {'INTC': 'Intel Corporation', 'MU': 'Micron Technology'}
TICKER_COLORS = {'INTC': '#0071C5', 'MU': '#CC0000'}

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(ROOT_DIR, '.cache')
DATA_DIR = os.path.join(ROOT_DIR, 'data', 'stock_history')
META_PATH = os.path.join(CACHE_DIR, 'market_data_meta.json')

FUNDAMENTALS = {
    'INTC': {
        'revenue_billions': {
            2019: 72.0, 2020: 77.9, 2021: 79.0, 2022: 63.1, 2023: 54.2, 2024: 53.1, 2025: 52.9
        },
        'net_income_billions': {2022: 8.0, 2023: 1.7, 2024: -16.6, 2025: -0.4},
        'eps': {
            2015: 2.34, 2016: 2.11, 2017: 1.98, 2018: 4.48, 2019: 4.72,
            2020: 4.94, 2021: 4.86, 2022: 1.96, 2023: 0.39, 2024: -4.38, 2025: -0.08
        },
        'gross_margin_pct': {2022: 42.6, 2023: 35.8, 2024: 32.7, 2025: 36.0},
        'roe_pct': {
            2015: 20.5, 2016: 17.4, 2017: 13.8, 2018: 29.8, 2019: 27.2,
            2020: 25.8, 2021: 23.1, 2022: 7.9, 2023: 1.6, 2024: -20.1, 2025: -0.5
        },
        'debt_to_equity': {
            2015: 0.33, 2016: 0.37, 2017: 0.36, 2018: 0.37, 2019: 0.37,
            2020: 0.45, 2021: 0.41, 2022: 0.41, 2023: 0.47, 2024: 0.50, 2025: 0.49
        },
        'moat': {
            'x86 Dominance': 7, 'Fab Capacity': 8, 'CHIPS Act': 8,
            'Patent Portfolio': 7, 'Brand': 6, 'Switching Costs': 5
        },
        'fiscal_years': [2022, 2023, 2024],
        'narrative': (
            'Intel is navigating a multi-year turnaround: reclaiming fab leadership via Intel 18A, '
            'leveraging $8.5B CHIPS Act grants, and rebuilding margins after FY2024 restructuring.'
        ),
    },
    'MU': {
        'revenue_billions': {2021: 27.7, 2022: 30.8, 2023: 15.5, 2024: 25.1, 2025: 38.8},
        'net_income_billions': {2022: 8.7, 2023: -5.8, 2024: 0.8, 2025: 8.6},
        'eps': {
            2020: 3.98, 2021: 6.06, 2022: 7.75, 2023: -5.36, 2024: 0.71, 2025: 7.88
        },
        'gross_margin_pct': {2022: 36.5, 2023: 9.0, 2024: 22.6, 2025: 39.5},
        'roe_pct': {2020: 9.5, 2021: 13.8, 2022: 18.1, 2023: -14.2, 2024: 2.0, 2025: 19.8},
        'debt_to_equity': {
            2020: 0.38, 2021: 0.30, 2022: 0.25, 2023: 0.36, 2024: 0.35, 2025: 0.31
        },
        'moat': {
            'HBM Leadership': 9, 'DRAM Market Share': 8, 'NAND Production': 7,
            'Manufacturing Scale': 8, 'R&D Pipeline': 8
        },
        'fiscal_years': [2023, 2024, 2025],
        'narrative': (
            'Micron is a primary beneficiary of the AI memory supercycle: HBM3E shipments to '
            'hyperscalers are driving record revenue and margins, with FY2025 showing a strong '
            'recovery from the 2023 memory downcycle.'
        ),
    },
}


# ── Data Loading ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_stock_data(ticker: str):
    """Load history CSV (priority) or fall back to live yfinance."""
    csv_path = os.path.join(DATA_DIR, f'{ticker.lower()}_history.csv')
    try:
        if os.path.exists(csv_path):
            cached = pd.read_csv(csv_path)
            if not cached.empty and 'Date' in cached.columns:
                cached['Date'] = pd.to_datetime(cached['Date'], errors='coerce')
                cached = cached.dropna(subset=['Date']).sort_values('Date')
                if 'Adj Close' in cached.columns and cached['Adj Close'].notna().any():
                    cached['Close'] = cached['Adj Close']
                for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                    if col not in cached.columns:
                        cached[col] = np.nan
                cached = cached[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
                for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                    cached[col] = pd.to_numeric(cached[col], errors='coerce')
                cached = cached.dropna(subset=['Close'])
                if len(cached) >= 60:
                    cached = cached.set_index('Date')
                    if cached.index.tz is not None:
                        cached.index = cached.index.tz_localize(None)
                    return cached
    except Exception:
        pass
    stock = yf.Ticker(ticker)
    df = stock.history(start='1990-01-01', end=datetime.now().strftime('%Y-%m-%d'), auto_adjust=True)
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df


def load_market_meta() -> dict:
    """Read refresh metadata written by scripts/refresh_data.py."""
    try:
        if os.path.exists(META_PATH):
            with open(META_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


@st.cache_data(ttl=3600)
def run_forecasts(df):
    """ARIMA(2,1,2) + Monte Carlo ensemble forecast (18-month horizon)."""
    current_price = df['Close'].iloc[-1]
    monthly = df['Close'].resample('ME').last().dropna()
    monthly_log = np.log(monthly)
    target_date = pd.Timestamp('2027-06-30')

    try:
        model = ARIMA(monthly_log, order=(2, 1, 2))
        fitted = model.fit()
        last_date = monthly.index[-1]
        months_ahead = max(1, (target_date.year - last_date.year) * 12 +
                           (target_date.month - last_date.month))
        forecast = fitted.forecast(steps=months_ahead)
        forecast_prices = np.exp(forecast)
        conf_int = fitted.get_forecast(steps=months_ahead).conf_int()
        conf_int_prices = np.exp(conf_int)
        forecast_dates = pd.date_range(
            start=last_date + pd.DateOffset(months=1), periods=months_ahead, freq='ME')
        arima_target = forecast_prices.iloc[-1]
        arima_lower = conf_int_prices.iloc[-1, 0]
        arima_upper = conf_int_prices.iloc[-1, 1]
    except Exception:
        arima_target = current_price * 1.10
        arima_lower, arima_upper = current_price * 0.70, current_price * 1.50
        forecast_dates = pd.date_range(
            start=monthly.index[-1] + pd.DateOffset(months=1), end=target_date, freq='ME')
        forecast_prices = pd.Series([arima_target] * len(forecast_dates), index=forecast_dates)
        conf_int_prices = pd.DataFrame(
            {'lower': [arima_lower] * len(forecast_dates), 'upper': [arima_upper] * len(forecast_dates)},
            index=forecast_dates)

    daily_returns = df['Close'].pct_change().dropna()
    mu_r, sigma_r = daily_returns.mean(), daily_returns.std()
    trading_days = max(1, np.busday_count(df.index[-1].date(), target_date.date()))
    n_sim = 10000
    np.random.seed(42)
    sims = np.random.normal(mu_r, sigma_r, (n_sim, trading_days))
    price_paths = current_price * np.cumprod(1 + sims, axis=1)
    final_prices = price_paths[:, -1]
    mc_mean = np.mean(final_prices)
    mc_p10 = np.percentile(final_prices, 10)
    mc_p90 = np.percentile(final_prices, 90)

    w_arima, w_mc = 0.4, 0.6
    return {
        'forecast_dates': forecast_dates,
        'forecast_prices': forecast_prices,
        'conf_int_prices': conf_int_prices,
        'price_paths': price_paths,
        'ensemble_base': w_arima * arima_target + w_mc * mc_mean,
        'ensemble_bear': w_arima * arima_lower + w_mc * mc_p10,
        'ensemble_bull': w_arima * arima_upper + w_mc * mc_p90,
        'target_date': target_date,
    }


# ── 10-Factor Signal Logic ───────────────────────────────────
def _compute_signal_factors(ps):
    """10-Factor Buy/Sell Signal. Score: 0=Strong Buy, 100=Strong Sell."""
    cur = float(ps.iloc[-1])
    _d = ps.diff()
    _g = _d.clip(lower=0).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    _l = (-_d.clip(upper=0)).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    f_rsi = float(np.clip(100 - 100 / (1 + float(_g.iloc[-1]) / max(float(_l.iloc[-1]), 1e-10)), 0, 100))
    _rsi_s = (100 - 100 / (1 + _g / _l.replace(0, 1e-10))).clip(0, 100)
    _r14 = _rsi_s.tail(14)
    f_stoch = float(np.clip((_rsi_s.iloc[-1] - _r14.min()) / max(float(_r14.max() - _r14.min()), 1e-10) * 100, 0, 100))
    _bm = float(ps.rolling(20).mean().iloc[-1])
    _bs = max(float(ps.rolling(20).std().iloc[-1]), 1e-10)
    f_bb = float(np.clip((cur - (_bm - 2*_bs)) / (4*_bs) * 100, 0, 100))
    _ps2y = ps.tail(504) if len(ps) >= 63 else ps
    _zm, _zs = float(_ps2y.mean()), max(float(_ps2y.std()), 1e-10)
    f_zscore = float(np.clip((cur - _zm) / _zs * 20 + 50, 0, 100))
    _h52 = float(ps.tail(252).max() if len(ps) >= 63 else ps.max())
    _l52 = float(ps.tail(252).min() if len(ps) >= 63 else ps.min())
    f_pos52 = float(np.clip((cur - _l52) / max(_h52 - _l52, 1e-10) * 100, 0, 100))
    _ma200 = float(ps.tail(200).mean() if len(ps) >= 63 else ps.mean())
    f_ma200 = float(np.clip((cur / max(_ma200, 1e-10) - 1) * 100 * 2 + 50, 0, 100))
    _ma50 = float(ps.tail(50).mean() if len(ps) >= 22 else ps.mean())
    f_ma_conv = float(np.clip(-(_ma50 / max(_ma200, 1e-10) - 1) * 100 * 10 + 50, 0, 100))
    _e12 = ps.ewm(span=12, min_periods=12, adjust=False).mean()
    _e26 = ps.ewm(span=26, min_periods=26, adjust=False).mean()
    _mh = (_e12 - _e26) - (_e12 - _e26).ewm(span=9, min_periods=9, adjust=False).mean()
    _mstd = max(float(_mh.tail(126).std()), 1e-10)
    f_macd = float(np.clip((-float(_mh.iloc[-1]) / (_mstd * 2) + 1) / 2 * 100, 0, 100))
    _ret = ps.pct_change()
    _v20 = float(_ret.tail(20).std() * np.sqrt(252) * 100) if len(ps) >= 20 else 15.0
    _v60 = float(_ret.tail(60).std() * np.sqrt(252) * 100) if len(ps) >= 60 else 15.0
    _pdir = 1.0 if cur > _ma200 else -1.0
    f_vol = float(np.clip(50 + _pdir * (_v20 / max(_v60, 1e-10) - 1) * 25, 0, 100))
    _roc10 = float((cur / float(ps.iloc[-11]) - 1) * 100) if len(ps) >= 11 else 0.0
    f_roc10 = float(np.clip((_roc10 + 10) / 20 * 100, 0, 100))

    signal_score = float(np.clip(
        f_rsi * 0.12 + f_stoch * 0.07 + f_bb * 0.10 + f_zscore * 0.20 +
        f_pos52 * 0.08 + f_ma200 * 0.12 + f_ma_conv * 0.08 + f_macd * 0.08 +
        f_vol * 0.08 + f_roc10 * 0.07, 0, 100))

    return signal_score, {
        'rsi': f_rsi, 'stoch_rsi': f_stoch, 'bb': f_bb, 'zscore': f_zscore,
        'pos52': f_pos52, 'ma200': f_ma200, 'ma_conv': f_ma_conv,
        'macd': f_macd, 'vol_regime': f_vol, 'roc10': f_roc10,
        'raw_roc10': _roc10, 'ma50_val': _ma50, 'ma200_val': _ma200,
        'golden_cross': _ma50 > _ma200,
    }


def _compute_signal_series(ps):
    """Vectorized 10-factor signal over full price history."""
    _d = ps.diff()
    _g = _d.clip(lower=0).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    _l = (-_d.clip(upper=0)).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    _rsi = (100 - 100 / (1 + _g / _l.replace(0, 1e-10))).clip(0, 100)
    _stoch = ((_rsi - _rsi.rolling(14).min()) /
              (_rsi.rolling(14).max() - _rsi.rolling(14).min()).replace(0, 1e-10) * 100).clip(0, 100)
    _bm, _bs = ps.rolling(20).mean(), ps.rolling(20).std().replace(0, 1e-10)
    _bb = ((ps - (_bm - 2*_bs)) / (4*_bs) * 100).clip(0, 100)
    _zm = ps.rolling(504, min_periods=63).mean()
    _zs = ps.rolling(504, min_periods=63).std().replace(0, 1e-10)
    _zscore = ((ps - _zm) / _zs * 20 + 50).clip(0, 100)
    _h52 = ps.rolling(252, min_periods=63).max()
    _l52 = ps.rolling(252, min_periods=63).min()
    _pos52 = ((ps - _l52) / (_h52 - _l52).replace(0, 1e-10) * 100).clip(0, 100)
    _ma200 = ps.rolling(200, min_periods=63).mean()
    _dev200 = ((ps / _ma200.replace(0, 1e-10) - 1) * 100 * 2 + 50).clip(0, 100)
    _ma50 = ps.rolling(50, min_periods=22).mean()
    _conv = (-(_ma50 / _ma200.replace(0, 1e-10) - 1) * 100 * 10 + 50).clip(0, 100)
    _e12 = ps.ewm(span=12, min_periods=12, adjust=False).mean()
    _e26 = ps.ewm(span=26, min_periods=26, adjust=False).mean()
    _ml = _e12 - _e26
    _mh = _ml - _ml.ewm(span=9, min_periods=9, adjust=False).mean()
    _macd_s = ((-_mh / _mh.rolling(126, min_periods=30).std().replace(0, 1e-10) / 2 + 1) / 2 * 100).clip(0, 100)
    _ret = ps.pct_change()
    _vr = (_ret.rolling(20).std() / _ret.rolling(60).std().replace(0, 1e-10))
    _pdir = (ps > _ma200).astype(float) * 2 - 1
    _vol_s = (50 + _pdir * (_vr - 1) * 25).clip(0, 100)
    _roc_s = (((ps / ps.shift(10) - 1) * 100 + 10) / 20 * 100).clip(0, 100)
    return (_rsi * 0.12 + _stoch * 0.07 + _bb * 0.10 + _zscore * 0.20 + _pos52 * 0.08 +
            _dev200 * 0.12 + _conv * 0.08 + _macd_s * 0.08 + _vol_s * 0.08 + _roc_s * 0.07).clip(0, 100)


def _get_decision_matrix_action(buffett_score, signal_score):
    """Combine quality (Buffett Score) + timing (Signal Score) → action."""
    if buffett_score >= 75: quality = 'excellent'
    elif buffett_score >= 60: quality = 'good'
    elif buffett_score >= 45: quality = 'average'
    elif buffett_score >= 30: quality = 'weak'
    else: quality = 'poor'

    if signal_score <= 30: timing = 'strong_buy'
    elif signal_score <= 50: timing = 'buy'
    elif signal_score <= 65: timing = 'neutral'
    elif signal_score <= 80: timing = 'caution'
    else: timing = 'sell'

    matrix = {
        ('excellent', 'strong_buy'): ('BUY MAX',       '#00cc66', 'Best quality at cheapest entry — rare opportunity'),
        ('excellent', 'buy'):        ('BUY, DCA',      '#88cc00', 'Great stock at good price — keep accumulating'),
        ('excellent', 'neutral'):    ('Hold',          '#aaaaaa', 'Excellent quality but timing not ideal — hold'),
        ('excellent', 'caution'):    ('Hold',          '#aaaaaa', 'Great stock but price trending high — hold'),
        ('excellent', 'sell'):       ('Take Profit',   '#ffaa00', 'Excellent stock but overbought — lock in gains'),
        ('good', 'strong_buy'):      ('BUY',           '#00cc66', 'Good quality at low price — confident entry'),
        ('good', 'buy'):             ('BUY, DCA',      '#88cc00', 'Good stock at reasonable price — DCA in'),
        ('good', 'neutral'):         ('Hold',          '#aaaaaa', 'Hold position — wait for better entry'),
        ('good', 'caution'):         ('Hold',          '#aaaaaa', 'Good stock but expensive — no new entries'),
        ('good', 'sell'):            ('Reduce',        '#ff8800', 'Good stock at overbought price — trim'),
        ('average', 'strong_buy'):   ('Buy Small',     '#88cc00', 'Average quality at cheap price — small entry OK'),
        ('average', 'buy'):          ('Hold',          '#aaaaaa', 'Average quality — hold if already owned'),
        ('average', 'neutral'):      ('Hold',          '#aaaaaa', 'No compelling action'),
        ('average', 'caution'):      ('Hold',          '#aaaaaa', 'No compelling reason to act'),
        ('average', 'sell'):         ('Reduce',        '#ff8800', 'Average stock at high price — trim'),
        ('weak', 'strong_buy'):      ('Do Not Buy',    '#ff4444', 'Weak fundamentals — cheap price is a value trap'),
        ('weak', 'buy'):             ('Do Not Buy',    '#ff4444', 'Weak fundamentals — avoid'),
        ('weak', 'neutral'):         ('Sell Partially','#ff8800', 'Start exiting before conditions worsen'),
        ('weak', 'caution'):         ('Sell',          '#ff4444', 'Weak and overpriced — exit'),
        ('weak', 'sell'):            ('Sell',          '#ff4444', 'Weak and overbought — sell'),
        ('poor', 'strong_buy'):      ('Do Not Buy',    '#ff4444', 'Poor quality — do not buy at any price'),
        ('poor', 'buy'):             ('Do Not Buy',    '#ff4444', 'Poor quality — avoid'),
        ('poor', 'neutral'):         ('Sell',          '#ff4444', 'Exit position'),
        ('poor', 'caution'):         ('Sell',          '#ff4444', 'Exit position'),
        ('poor', 'sell'):            ('Sell All',      '#ff0000', 'Worst combination — exit completely'),
    }
    return matrix.get((quality, timing), ('Hold', '#aaaaaa', 'No clear signal'))


def compute_buffett_scores(df, ticker: str):
    """Buffett Scorecard for the given ticker using per-company FUNDAMENTALS."""
    fund = FUNDAMENTALS[ticker]
    current_price = df['Close'].iloc[-1]
    _52w = df['Close'].loc[df.index >= df.index[-1] - pd.DateOffset(weeks=52)]
    high_52w, low_52w = _52w.max(), _52w.min()

    positive_eps = [v for v in fund['eps'].values() if v > 0]
    avg_eps = np.mean(positive_eps) if positive_eps else 0
    intrinsic_value = avg_eps * 1.03 / 0.07 if avg_eps > 0 else 0
    margin_of_safety = (intrinsic_value - current_price) / intrinsic_value * 100 if intrinsic_value > 0 else -100

    scores = {}
    scores['Intrinsic Value'] = (9 if intrinsic_value > current_price * 1.25 else
                                  6 if intrinsic_value > current_price else
                                  4 if intrinsic_value > current_price * 0.8 else 2)
    scores['Margin of Safety'] = (9 if margin_of_safety >= 25 else
                                   7 if margin_of_safety >= 10 else
                                   5 if margin_of_safety >= 0 else 3)
    scores['Economic Moat'] = round(np.mean(list(fund['moat'].values())))

    eps_vals = list(fund['eps'].values())
    consistency = sum(1 for e in eps_vals if e > 0) / len(eps_vals)
    scores['Consistent Earnings'] = (9 if consistency >= 0.9 else 6 if consistency >= 0.7 else
                                      4 if consistency >= 0.5 else 2)

    roe_vals = list(fund['roe_pct'].values())
    positive_roe = [r for r in roe_vals if r > 0]
    avg_roe = np.mean(positive_roe) if positive_roe else 0
    scores['Return on Equity'] = (9 if (avg_roe >= 20 and roe_vals[-1] >= 15) else
                                   6 if avg_roe >= 15 else
                                   4 if avg_roe >= 10 else 2)

    current_de = list(fund['debt_to_equity'].values())[-1]
    scores['Low Debt'] = (9 if current_de < 0.3 else 7 if current_de < 0.5 else
                           5 if current_de < 0.8 else 3)
    scores['Management Quality'] = 7 if ticker == 'MU' else 6

    ten_yr_return = 0.0
    if len(df) > 252 * 10:
        ten_yr_return = ((current_price / df['Close'].iloc[-252*10]) ** (1/10) - 1) * 100
    scores['Long-term Value'] = (8 if ten_yr_return > 10 else 6 if ten_yr_return > 5 else
                                  4 if ten_yr_return > 0 else 3)

    pos_in_range = ((current_price - low_52w) / (high_52w - low_52w) * 100
                    if (high_52w - low_52w) > 0 else 50)
    scores['Contrarian Signal'] = (9 if pos_in_range < 30 else 7 if pos_in_range < 50 else
                                    5 if pos_in_range < 70 else 3)

    _5y = df['Close'].loc[df.index >= df.index[-1] - pd.DateOffset(years=5)]
    recent_dd = ((_5y / _5y.cummax()) - 1).min() * 100
    scores['Downside Protection'] = (8 if abs(recent_dd) < 20 else 5 if abs(recent_dd) < 40 else 3)

    weights = {
        'Intrinsic Value': 0.15, 'Margin of Safety': 0.15, 'Economic Moat': 0.12,
        'Consistent Earnings': 0.10, 'Return on Equity': 0.10, 'Low Debt': 0.08,
        'Management Quality': 0.08, 'Long-term Value': 0.08,
        'Contrarian Signal': 0.07, 'Downside Protection': 0.07,
    }
    buffett_score = sum(scores[k] * weights[k] * 10 for k in scores)
    return scores, buffett_score, intrinsic_value, margin_of_safety


def generate_ai_response(user_question, ticker, scores, buffett_score,
                          current_price, ensemble_base, ensemble_bull, ensemble_bear,
                          intrinsic_value, signal_score=50.0, action='Hold',
                          action_desc='', factors=None):
    """Generate Buffett-style AI response via OpenAI (or rule-based fallback)."""
    fund = FUNDAMENTALS[ticker]
    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    eps_latest = list(fund['eps'].values())[-1]
    rev_latest = list(fund['revenue_billions'].values())[-1]
    roe_latest = list(fund['roe_pct'].values())[-1]
    de_latest = list(fund['debt_to_equity'].values())[-1]

    # Build signal factor summary for LLM context
    factor_summary = ''
    if factors:
        factor_summary = (f"RSI={factors['rsi']:.0f}, BB%={factors['bb']:.0f}, "
                          f"Z-Score={factors['zscore']:.0f}, 52W-Pos={factors['pos52']:.0f}, "
                          f"MA200-Dev={factors['ma200']:.0f}, MACD={factors['macd']:.0f}, "
                          f"Golden-Cross={'Yes' if factors.get('golden_cross') else 'No'}")

    system_prompt = f"""You are Warren Buffett. Answer the user's question about {TICKER_NAMES[ticker]} ({ticker}).
Use folksy, wisdom-filled style. Cite real numbers below. Keep response under 400 words.
End with a clear actionable recommendation matching the DECISION MATRIX output.
Note: educational only, not financial advice.

DATA:
- Price: ${current_price:.2f} | Intrinsic Value: ${intrinsic_value:.2f}
- Buffett Score: {buffett_score:.0f}/100 (Quality) | Signal Score: {signal_score:.0f}/100 (Timing, 0=buy 100=sell)
- EPS (latest): ${eps_latest:.2f} | Revenue: ${rev_latest:.1f}B | ROE: {roe_latest:.1f}% | D/E: {de_latest:.2f}
- Forecast (18mo): Bear ${ensemble_bear:.2f} / Base ${ensemble_base:.2f} / Bull ${ensemble_bull:.2f}
- Technical Factors: {factor_summary}
- Narrative: {fund['narrative']}

DECISION MATRIX OUTPUT:
- Action: {action}
- Rationale: {action_desc}

The Decision Matrix combines Quality (Buffett Score) and Timing (Signal Score).
Actions range from BUY MAX (best quality + cheapest entry) to SELL ALL (poor quality + overbought).
Always state the matrix action clearly and explain why, referencing both quality and timing scores."""

    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_question},
                ],
                max_tokens=600, temperature=0.7,
            )
            return resp.choices[0].message.content
        except Exception:
            pass

    # Rule-based fallback
    q = user_question.lower()
    upside = (ensemble_base / current_price - 1) * 100
    quality_label = ("excellent" if buffett_score >= 70 else
                     "good" if buffett_score >= 55 else
                     "average" if buffett_score >= 40 else "below average")
    timing_label = ("deeply oversold" if signal_score <= 30 else
                    "undervalued" if signal_score <= 50 else
                    "fairly valued" if signal_score <= 65 else
                    "overheated" if signal_score <= 80 else "overbought")

    # Decision matrix banner included in all responses
    matrix_banner = (f'\n\n📊 **Decision Matrix → {action}**\n'
                     f'> Quality: {buffett_score:.0f}/100 ({quality_label}) · '
                     f'Timing: {signal_score:.0f}/100 ({timing_label})\n'
                     f'> *{action_desc}*')

    if any(w in q for w in ['buy', 'invest', 'entry', 'accumulate', 'dca', 'worth']):
        verb = "accumulate" if buffett_score > 60 else ("be cautious about" if buffett_score > 40 else "avoid")
        return (f'*"Price is what you pay. Value is what you get."*\n\n'
                f'{TICKER_NAMES[ticker]} at **${current_price:.2f}**:\n'
                f'- Intrinsic Value (DCF): **${intrinsic_value:.2f}**\n'
                f'- Buffett Score: **{buffett_score:.0f}/100** ({quality_label})\n'
                f'- Signal Score: **{signal_score:.0f}/100** ({timing_label})\n'
                f'- Base Forecast (18mo): **${ensemble_base:.2f}** ({upside:+.1f}% implied)\n'
                f'{matrix_banner}\n\n'
                f'I would **{verb}** at this price. {fund["narrative"]}\n\n'
                f'⚠️ *Educational only — not financial advice.*')

    if any(w in q for w in ['sell', 'exit', 'reduce', 'trim']):
        return (f'*"Only when the tide goes out do you discover who\'s been swimming naked."*\n\n'
                f'At **${current_price:.2f}**, Buffett Score is **{buffett_score:.0f}/100**.\n'
                f'Signal Score: **{signal_score:.0f}/100** ({timing_label}).\n'
                f'Bear / Base / Bull: **${ensemble_bear:.2f} / ${ensemble_base:.2f} / ${ensemble_bull:.2f}**\n'
                f'{matrix_banner}\n\n'
                f'{"Consider partial profit-taking if this is an oversized position." if upside < 10 else "Hold unless your position size is uncomfortably large."}\n\n'
                f'⚠️ *Educational only — not financial advice.*')

    return (f'*"Rule No.1: Never lose money. Rule No.2: Never forget Rule No.1."*\n\n'
            f'**{TICKER_NAMES[ticker]} ({ticker})** — ${current_price:.2f}\n'
            f'- Intrinsic Value: **${intrinsic_value:.2f}** | Buffett Score: **{buffett_score:.0f}/100**\n'
            f'- Signal Score: **{signal_score:.0f}/100** ({timing_label})\n'
            f'- Forecast: Bear **${ensemble_bear:.2f}** / Base **${ensemble_base:.2f}** / Bull **${ensemble_bull:.2f}**\n'
            f'{matrix_banner}\n\n'
            f'{fund["narrative"]}\n\n'
            f'⚠️ *Educational only — not financial advice.*')


# ── Main Dashboard ───────────────────────────────────────────
def main():
    with st.sidebar:
        st.title("📊 InvestorGPT")
        st.caption("Buffett-style AI Advisor · Semiconductors")
        st.divider()

        ticker = st.selectbox(
            "Select Company",
            TICKERS,
            format_func=lambda t: f"{t} — {TICKER_NAMES[t]}",
        )
        show_compare = st.checkbox("Compare INTC vs MU", value=False)

        st.divider()
        meta = load_market_meta()
        ticker_meta = meta.get(ticker, {})
        if ticker_meta.get('fetched_on'):
            st.caption(f"📅 Refreshed: {ticker_meta['fetched_on']}")
            if ticker_meta.get('rows'):
                st.caption(f"📈 {ticker_meta['rows']:,} trading days")
        else:
            st.caption("⚠️ Run `scripts/refresh_data.py` to cache data")
        st.divider()
        st.caption("Data: Yahoo Finance · SEC EDGAR 10-K")
        st.caption("Scores: Buffett value principles · Not financial advice")

    with st.spinner(f"Loading {ticker}..."):
        df = load_stock_data(ticker)

    if df is None or df.empty:
        st.error(f"No data for {ticker}. Run `scripts/refresh_data.py` or check internet.")
        return

    fund = FUNDAMENTALS[ticker]
    current_price = df['Close'].iloc[-1]
    color = TICKER_COLORS[ticker]

    signal_score, factors = _compute_signal_factors(df['Close'])
    scores, buffett_score, intrinsic_value, margin_of_safety = compute_buffett_scores(df, ticker)
    action, action_color, action_desc = _get_decision_matrix_action(buffett_score, signal_score)

    # ── Header ────────────────────────────────────────────────
    st.markdown(f"## {TICKER_NAMES[ticker]} ({ticker})")
    c1, c2, c3, c4, c5 = st.columns(5)
    prev = float(df['Close'].iloc[-2]) if len(df) > 1 else current_price
    day_chg = (current_price / prev - 1) * 100
    c1.metric("Price", f"${current_price:.2f}", f"{day_chg:+.2f}%")
    c2.metric("Buffett Score", f"{buffett_score:.0f}/100")
    c3.metric("Signal Score", f"{signal_score:.0f}/100",
              delta="Buy" if signal_score < 40 else ("Sell" if signal_score > 65 else "Neutral"),
              delta_color="normal" if signal_score < 40 else ("inverse" if signal_score > 65 else "off"))
    c4.metric("Intrinsic Value", f"${intrinsic_value:.2f}")
    c5.metric("Action", action, help=action_desc)
    st.divider()

    # ── Tabs ──────────────────────────────────────────────────
    tab_labels = ["📈 Price & Signal", "🏛️ Buffett Score", "📋 Fundamentals", "🔮 Forecast"]
    if show_compare:
        tab_labels.append("⚖️ Compare")
    tab_labels.append("🤖 AI Advisor")
    tabs = st.tabs(tab_labels)

    # ── Tab 1: Price & Signal ─────────────────────────────────
    with tabs[0]:
        df_plot = df.tail(756)
        sig_series = _compute_signal_series(df['Close']).tail(756)

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.65, 0.35],
                            subplot_titles=[f"{ticker} Price (3Y)", "Signal Score (0=Buy · 100=Sell)"])
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['Close'], name="Price",
                                  line=dict(color=color, width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['Close'].rolling(50).mean(),
                                  name="MA50", line=dict(color='orange', width=1, dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['Close'].rolling(200).mean(),
                                  name="MA200", line=dict(color='red', width=1, dash='dash')), row=1, col=1)
        fig.add_trace(go.Scatter(x=sig_series.index, y=sig_series.values, name="Signal",
                                  fill='tozeroy', line=dict(color='purple', width=1)), row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        fig.add_hline(y=65, line_dash="dash", line_color="red", row=2, col=1)
        fig.update_layout(height=550, showlegend=True, template="plotly_white",
                          margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Signal Factor Breakdown")
        factor_labels = {
            'rsi': 'RSI(14)', 'stoch_rsi': 'Stoch RSI', 'bb': 'Bollinger %B',
            'zscore': '2Y Z-Score', 'pos52': '52W Position', 'ma200': '200d MA Dev',
            'ma_conv': 'MA Conv.', 'macd': 'MACD Hist', 'vol_regime': 'Vol Regime', 'roc10': '10d ROC',
        }
        cols_f = st.columns(5)
        for i, (k, lbl) in enumerate(factor_labels.items()):
            v = factors[k]
            icon = "🟢" if v < 35 else ("🔴" if v > 65 else "🟡")
            cols_f[i % 5].metric(f"{icon} {lbl}", f"{v:.0f}")

        gc = factors.get('golden_cross', False)
        st.info(f"{'🟢 Golden Cross' if gc else '🔴 Death Cross'} — "
                f"MA50=${factors['ma50_val']:.2f} {'>' if gc else '<'} MA200=${factors['ma200_val']:.2f}")

    # ── Tab 2: Buffett Score ──────────────────────────────────
    with tabs[1]:
        col_a, col_b = st.columns([1, 1])
        weights_map = {
            'Intrinsic Value': 0.15, 'Margin of Safety': 0.15, 'Economic Moat': 0.12,
            'Consistent Earnings': 0.10, 'Return on Equity': 0.10, 'Low Debt': 0.08,
            'Management Quality': 0.08, 'Long-term Value': 0.08,
            'Contrarian Signal': 0.07, 'Downside Protection': 0.07,
        }
        with col_a:
            st.markdown("#### Buffett Scorecard")
            rows = [{'Principle': f"{'🟢' if v >= 7 else '🟡' if v >= 5 else '🔴'} {k}",
                     'Score (1-10)': v,
                     'Weight': f"{weights_map[k]*100:.0f}%",
                     'Contribution': f"{v * weights_map[k] * 10:.1f}"}
                    for k, v in scores.items()]
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
            st.metric("Total Buffett Score", f"{buffett_score:.1f}/100",
                      delta="Strong" if buffett_score >= 70 else ("Moderate" if buffett_score >= 50 else "Weak"))
        with col_b:
            st.markdown("#### Score Radar")
            cats = list(scores.keys())
            fig_r = go.Figure(go.Scatterpolar(
                r=list(scores.values()) + [list(scores.values())[0]],
                theta=cats + [cats[0]], fill='toself',
                fillcolor=color, opacity=0.4, line=dict(color=color)))
            fig_r.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
                                 showlegend=False, height=350, template="plotly_white")
            st.plotly_chart(fig_r, use_container_width=True)

        st.markdown("#### Decision Matrix")
        c_dm1, c_dm2 = st.columns([1, 2])
        with c_dm1:
            st.markdown(f"""
<div style="background:{action_color}22;border-left:5px solid {action_color};padding:16px;border-radius:8px;">
<h3 style="color:{action_color};margin:0">{action}</h3>
<p style="margin:4px 0 0">{action_desc}</p>
<small>Buffett {buffett_score:.0f} · Signal {signal_score:.0f}</small>
</div>""", unsafe_allow_html=True)
        with c_dm2:
            st.info("**Economic Moat:** " + " · ".join(f"{k}: {v}/10" for k, v in fund['moat'].items()))
            st.info(f"**Narrative:** {fund['narrative']}")

        # Full 5x5 Decision Matrix table with colored cells
        st.markdown("#### Decision Matrix Detail")
        _q_zones = [('≥75 Excellent', 'excellent'), ('≥60 Good', 'good'),
                    ('≥45 Average', 'average'), ('≥30 Weak', 'weak'), ('<30 Poor', 'poor')]
        _t_zones = [('≤30 Strong Buy', 'strong_buy'), ('≤50 Buy', 'buy'),
                    ('≤65 Neutral', 'neutral'), ('≤80 Caution', 'caution'), ('>80 Sell', 'sell')]
        _dm_lookup = {
            ('excellent','strong_buy'):'BUY MAX',('excellent','buy'):'BUY, DCA',
            ('excellent','neutral'):'Hold',('excellent','caution'):'Hold',
            ('excellent','sell'):'Take Profit',
            ('good','strong_buy'):'BUY',('good','buy'):'BUY, DCA',
            ('good','neutral'):'Hold',('good','caution'):'Hold',
            ('good','sell'):'Reduce',
            ('average','strong_buy'):'Buy Small',('average','buy'):'Hold',
            ('average','neutral'):'Hold',('average','caution'):'Hold',
            ('average','sell'):'Reduce',
            ('weak','strong_buy'):'Do Not Buy',('weak','buy'):'Do Not Buy',
            ('weak','neutral'):'Sell Partially',('weak','caution'):'Sell',
            ('weak','sell'):'Sell',
            ('poor','strong_buy'):'Do Not Buy',('poor','buy'):'Do Not Buy',
            ('poor','neutral'):'Sell',('poor','caution'):'Sell',
            ('poor','sell'):'Sell All',
        }
        def _cell_color(act):
            if act in ('BUY MAX','BUY','BUY, DCA','Buy Small'):
                return '#00cc6633', '#00cc66'
            if act in ('Sell','Sell All','Do Not Buy','Sell Partially'):
                return '#ff444433', '#ff4444'
            if act in ('Take Profit','Reduce'):
                return '#ff880033', '#ff8800'
            return '#aaaaaa22', '#888888'

        # Determine which cell is the current position
        _cur_q = ('excellent' if buffett_score >= 75 else 'good' if buffett_score >= 60 else
                  'average' if buffett_score >= 45 else 'weak' if buffett_score >= 30 else 'poor')
        _cur_t = ('strong_buy' if signal_score <= 30 else 'buy' if signal_score <= 50 else
                  'neutral' if signal_score <= 65 else 'caution' if signal_score <= 80 else 'sell')

        _html = '<table style="width:100%;border-collapse:collapse;font-size:13px;text-align:center;">'
        _html += '<tr><th style="border:1px solid #444;padding:6px;background:#222;color:#fff;">Buffett Score ↓ \\ Signal →</th>'
        for t_lbl, _ in _t_zones:
            _html += f'<th style="border:1px solid #444;padding:6px;background:#222;color:#fff;">{t_lbl}</th>'
        _html += '</tr>'
        for q_lbl, q_key in _q_zones:
            _html += f'<tr><th style="border:1px solid #444;padding:6px;background:#333;color:#fff;text-align:left;">{q_lbl}</th>'
            for _, t_key in _t_zones:
                act_txt = _dm_lookup[(q_key, t_key)]
                bg, fg = _cell_color(act_txt)
                is_current = (q_key == _cur_q and t_key == _cur_t)
                border = f'3px solid {fg}' if is_current else '1px solid #444'
                marker = ' ⬅️' if is_current else ''
                _html += (f'<td style="border:{border};padding:8px;background:{bg};'
                          f'color:{fg};font-weight:{"bold" if is_current else "normal"};">'
                          f'{act_txt}{marker}</td>')
            _html += '</tr>'
        _html += '</table>'
        st.markdown(_html, unsafe_allow_html=True)
        st.caption(f"Current position: Buffett {buffett_score:.0f} ({_cur_q}) · Signal {signal_score:.0f} ({_cur_t}) → **{action}**")

    # ── Tab 3: Fundamentals ───────────────────────────────────
    with tabs[2]:
        st.markdown("#### Annual Financials (SEC 10-K Filings)")
        fys = fund['fiscal_years']
        rev = [fund['revenue_billions'].get(y, 0) for y in fys]
        ni = [fund['net_income_billions'].get(y, 0) for y in fys]
        gm = [fund['gross_margin_pct'].get(y, 0) for y in fys]
        fy_str = [str(y) for y in fys]

        fig_f = make_subplots(rows=1, cols=3,
                               subplot_titles=["Revenue (B$)", "Net Income (B$)", "Gross Margin (%)"])
        fig_f.add_trace(go.Bar(x=fy_str, y=rev,
                                marker_color=[color if v >= 0 else '#cc3300' for v in rev],
                                name="Revenue"), row=1, col=1)
        fig_f.add_trace(go.Bar(x=fy_str, y=ni,
                                marker_color=[color if v >= 0 else '#cc3300' for v in ni],
                                name="Net Income"), row=1, col=2)
        fig_f.add_trace(go.Bar(x=fy_str, y=gm, marker_color=color, name="Gross Margin"), row=1, col=3)
        fig_f.update_layout(height=320, showlegend=False, template="plotly_white",
                             margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_f, use_container_width=True)

        st.markdown("#### Per-Share & Ratio Metrics")
        eps_fys = sorted(fund['eps'].keys())[-6:]
        table_rows = [{'FY': str(y),
                        'EPS ($)': f"{fund['eps'][y]:+.2f}" if y in fund['eps'] else '—',
                        'ROE (%)': f"{fund['roe_pct'][y]:.1f}" if y in fund['roe_pct'] else '—',
                        'D/E': f"{fund['debt_to_equity'][y]:.2f}" if y in fund['debt_to_equity'] else '—'}
                       for y in eps_fys]
        st.dataframe(pd.DataFrame(table_rows), hide_index=True, use_container_width=True)
        st.caption("Source: SEC EDGAR 10-K filings")

    # ── Tab 4: Forecast ───────────────────────────────────────
    with tabs[3]:
        with st.spinner("Running ARIMA + Monte Carlo (10,000 sims)..."):
            fc = run_forecasts(df)

        c_fc1, c_fc2, c_fc3 = st.columns(3)
        c_fc1.metric("Bear Case", f"${fc['ensemble_bear']:.2f}",
                      f"{(fc['ensemble_bear']/current_price-1)*100:+.1f}%")
        c_fc2.metric("Base Case", f"${fc['ensemble_base']:.2f}",
                      f"{(fc['ensemble_base']/current_price-1)*100:+.1f}%")
        c_fc3.metric("Bull Case", f"${fc['ensemble_bull']:.2f}",
                      f"{(fc['ensemble_bull']/current_price-1)*100:+.1f}%")

        hist = df['Close'].tail(252)
        fig_fc = go.Figure()
        fig_fc.add_trace(go.Scatter(x=hist.index, y=hist.values, name="Historical",
                                     line=dict(color=color)))
        fig_fc.add_trace(go.Scatter(x=fc['forecast_dates'], y=fc['forecast_prices'].values,
                                     name="ARIMA", line=dict(color='orange', dash='dash')))
        conf = fc['conf_int_prices']
        fig_fc.add_trace(go.Scatter(
            x=list(fc['forecast_dates']) + list(fc['forecast_dates'])[::-1],
            y=list(conf.iloc[:, 1]) + list(conf.iloc[:, 0])[::-1],
            fill='toself', fillcolor='rgba(255,165,0,0.15)',
            line=dict(color='rgba(0,0,0,0)'), name="ARIMA CI"))

        n_show = min(20, fc['price_paths'].shape[0])
        mc_dates = pd.bdate_range(start=df.index[-1], periods=fc['price_paths'].shape[1] + 1)[1:]
        for i in range(n_show):
            fig_fc.add_trace(go.Scatter(
                x=mc_dates[:len(fc['price_paths'][i])], y=fc['price_paths'][i],
                line=dict(color='rgba(100,100,200,0.07)', width=1),
                showlegend=(i == 0), name="MC Paths" if i == 0 else ""))

        fig_fc.update_layout(height=430, template="plotly_white",
                              title=f"{ticker} Forecast → {fc['target_date'].strftime('%B %Y')}",
                              margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_fc, use_container_width=True)
        st.caption("ARIMA 40% + Monte Carlo 60% ensemble · Not financial advice")

    # ── Tab 5: Compare (optional) ─────────────────────────────
    if show_compare:
        with tabs[4]:
            other = 'MU' if ticker == 'INTC' else 'INTC'
            with st.spinner(f"Loading {other}..."):
                df_o = load_stock_data(other)

            if df_o is not None and not df_o.empty:
                sig_o, _ = _compute_signal_factors(df_o['Close'])
                sc_o, bs_o, iv_o, _ = compute_buffett_scores(df_o, other)
                act_o, ac_o, _ = _get_decision_matrix_action(bs_o, sig_o)
                pr_o = df_o['Close'].iloc[-1]
                fc_o = run_forecasts(df_o)

                st.markdown("#### Side-by-Side Comparison")
                c1_cmp, c2_cmp = st.columns(2)
                with c1_cmp:
                    st.markdown(f"##### {TICKER_NAMES[ticker]} ({ticker})")
                    st.metric("Price", f"${current_price:.2f}")
                    st.metric("Buffett Score", f"{buffett_score:.1f}/100")
                    st.metric("Signal Score", f"{signal_score:.0f}/100")
                    st.metric("Intrinsic Value", f"${intrinsic_value:.2f}")
                    fc_c = run_forecasts(df)
                    st.metric("Base Forecast (18mo)", f"${fc_c['ensemble_base']:.2f}",
                              f"{(fc_c['ensemble_base']/current_price-1)*100:+.1f}%")
                    st.markdown(f"**Action:** <span style='color:{action_color}'>{action}</span>",
                                unsafe_allow_html=True)
                with c2_cmp:
                    st.markdown(f"##### {TICKER_NAMES[other]} ({other})")
                    st.metric("Price", f"${pr_o:.2f}")
                    st.metric("Buffett Score", f"{bs_o:.1f}/100")
                    st.metric("Signal Score", f"{sig_o:.0f}/100")
                    st.metric("Intrinsic Value", f"${iv_o:.2f}")
                    st.metric("Base Forecast (18mo)", f"${fc_o['ensemble_base']:.2f}",
                              f"{(fc_o['ensemble_base']/pr_o-1)*100:+.1f}%")
                    st.markdown(f"**Action:** <span style='color:{ac_o}'>{act_o}</span>",
                                unsafe_allow_html=True)

                st.markdown("#### Normalized Price Performance (3Y, base=100)")
                common_start = max(df.index[0], df_o.index[0])
                s1 = df['Close'].loc[df.index >= common_start].tail(756)
                s2 = df_o['Close'].loc[df_o.index >= common_start].tail(756)
                norm1 = s1 / s1.iloc[0] * 100
                norm2 = s2 / s2.iloc[0] * 100
                fig_cmp = go.Figure()
                fig_cmp.add_trace(go.Scatter(x=norm1.index, y=norm1.values,
                                              name=ticker, line=dict(color=TICKER_COLORS[ticker])))
                fig_cmp.add_trace(go.Scatter(x=norm2.index, y=norm2.values,
                                              name=other, line=dict(color=TICKER_COLORS[other])))
                fig_cmp.update_layout(height=320, template="plotly_white",
                                       margin=dict(l=0, r=0, t=20, b=0))
                st.plotly_chart(fig_cmp, use_container_width=True)

                st.markdown("#### Buffett Scorecard Radar")
                cats = list(scores.keys())
                fig_cr = go.Figure()
                fig_cr.add_trace(go.Scatterpolar(
                    r=list(scores.values()) + [list(scores.values())[0]],
                    theta=cats + [cats[0]], fill='toself', opacity=0.4,
                    name=ticker, line=dict(color=TICKER_COLORS[ticker])))
                fig_cr.add_trace(go.Scatterpolar(
                    r=[sc_o.get(c, 5) for c in cats] + [sc_o.get(cats[0], 5)],
                    theta=cats + [cats[0]], fill='toself', opacity=0.4,
                    name=other, line=dict(color=TICKER_COLORS[other])))
                fig_cr.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
                                      height=380, template="plotly_white")
                st.plotly_chart(fig_cr, use_container_width=True)

    # ── Last Tab: AI Advisor ──────────────────────────────────
    with tabs[-1]:
        st.markdown("#### 🤖 Ask Warren Buffett")
        st.caption(f"About {TICKER_NAMES[ticker]} ({ticker}) · GPT-4o if OPENAI_API_KEY is set")

        fc_ai = run_forecasts(df)
        example_qs = [
            f"Should I buy {ticker} at the current price?",
            f"What is {ticker}'s economic moat?",
            f"What's the biggest risk for {ticker} investors?",
            f"Compare {ticker}'s EPS trend over recent years",
        ]
        q_sel = st.selectbox("Quick questions", [""] + example_qs, label_visibility="collapsed")
        user_q = st.text_input("Your question:", value=q_sel if q_sel else "",
                                placeholder=f"e.g. Should I buy {ticker} now?")

        if st.button("Ask Buffett") and user_q:
            with st.spinner("Channeling Warren Buffett..."):
                resp = generate_ai_response(
                    user_q, ticker, scores, buffett_score, current_price,
                    fc_ai['ensemble_base'], fc_ai['ensemble_bull'],
                    fc_ai['ensemble_bear'], intrinsic_value,
                    signal_score=signal_score, action=action,
                    action_desc=action_desc, factors=factors,
                )
            st.markdown(resp)
            if not os.getenv("OPENAI_API_KEY"):
                st.caption("💡 Add OPENAI_API_KEY to .env for GPT-4o responses")


if __name__ == "__main__":
    main()
