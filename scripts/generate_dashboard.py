"""
Generates webpage/index.html with the full InvestorGPT dashboard.
Features match dashboard.py: price+MAs, 10-factor signal, Buffett scorecard,
fundamentals (10-K), ARIMA+MC forecast, INTC vs MU compare.

All analytics computed here; results embedded as JSON in the HTML.
Opens directly in any browser — no server required.

Run:
    python scripts/generate_dashboard.py
Via bat:
    open_dashboard.bat
"""
from __future__ import annotations

import json
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT_DIR  = Path(__file__).parent.parent
DATA_DIR  = ROOT_DIR / "data" / "stock_history"
OUTPUT    = ROOT_DIR / "webpage" / "index.html"
META_PATH = ROOT_DIR / ".cache" / "market_data_meta.json"

TICKERS       = ["INTC", "MU"]
TICKER_NAMES  = {"INTC": "Intel Corporation", "MU": "Micron Technology"}
TICKER_COLORS = {"INTC": "#0071C5",           "MU": "#CC0000"}

FUNDAMENTALS = {
    "INTC": {
        "revenue_billions":    {2019:72.0,2020:77.9,2021:79.0,2022:63.1,2023:54.2,2024:53.1,2025:52.9},
        "net_income_billions": {2022:8.0,2023:1.7,2024:-16.6,2025:-0.4},
        "eps":  {2015:2.34,2016:2.11,2017:1.98,2018:4.48,2019:4.72,2020:4.94,
                 2021:4.86,2022:1.96,2023:0.39,2024:-4.38,2025:-0.08},
        "gross_margin_pct": {2022:42.6,2023:35.8,2024:32.7,2025:36.0},
        "roe_pct": {2015:20.5,2016:17.4,2017:13.8,2018:29.8,2019:27.2,2020:25.8,
                    2021:23.1,2022:7.9,2023:1.6,2024:-20.1,2025:-0.5},
        "debt_to_equity": {2015:0.33,2016:0.37,2017:0.36,2018:0.37,2019:0.37,
                           2020:0.45,2021:0.41,2022:0.41,2023:0.47,2024:0.50,2025:0.49},
        "moat": {"x86 Dominance":7,"Fab Capacity":8,"CHIPS Act":8,
                 "Patent Portfolio":7,"Brand":6,"Switching Costs":5},
        "fiscal_years": [2022,2023,2024],
        "narrative": ("Intel is navigating a multi-year turnaround: reclaiming fab leadership "
                      "via Intel 18A, leveraging $8.5B CHIPS Act grants, and rebuilding margins "
                      "after FY2024 restructuring."),
    },
    "MU": {
        "revenue_billions":    {2021:27.7,2022:30.8,2023:15.5,2024:25.1,2025:38.8},
        "net_income_billions": {2022:8.7,2023:-5.8,2024:0.8,2025:8.6},
        "eps":  {2020:3.98,2021:6.06,2022:7.75,2023:-5.36,2024:0.71,2025:7.88},
        "gross_margin_pct": {2022:36.5,2023:9.0,2024:22.6,2025:39.5},
        "roe_pct": {2020:9.5,2021:13.8,2022:18.1,2023:-14.2,2024:2.0,2025:19.8},
        "debt_to_equity": {2020:0.38,2021:0.30,2022:0.25,2023:0.36,2024:0.35,2025:0.31},
        "moat": {"HBM Leadership":9,"DRAM Market Share":8,"NAND Production":7,
                 "Manufacturing Scale":8,"R&D Pipeline":8},
        "fiscal_years": [2023,2024,2025],
        "narrative": ("Micron is a primary beneficiary of the AI memory supercycle: HBM3E "
                      "shipments to hyperscalers are driving record revenue and margins, with "
                      "FY2025 showing a strong recovery from the 2023 memory downcycle."),
    },
}


# ── data loading ──────────────────────────────────────────────
def load_stock_df(ticker: str) -> pd.DataFrame:
    csv_path = DATA_DIR / f"{ticker.lower()}_history.csv"
    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path)
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df = df.dropna(subset=["Date"]).sort_values("Date")
            if "Adj Close" in df.columns and df["Adj Close"].notna().any():
                df["Close"] = df["Adj Close"]
            for col in ["Open","High","Low","Close","Volume"]:
                if col not in df.columns: df[col] = np.nan
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df = df.dropna(subset=["Close"])
            if len(df) >= 60:
                df = df.set_index("Date")
                if df.index.tz is not None: df.index = df.index.tz_localize(None)
                return df
        except Exception:
            pass
    import yfinance as yf
    print(f"  {ticker}: CSV missing, fetching live...")
    stock = yf.Ticker(ticker)
    df = stock.history(start="1990-01-01", auto_adjust=True)
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None: df.index = df.index.tz_localize(None)
    return df


# ── signal logic ──────────────────────────────────────────────
def compute_signal_factors(ps: pd.Series) -> tuple[float, dict]:
    cur = float(ps.iloc[-1])
    _d = ps.diff()
    _g = _d.clip(lower=0).ewm(alpha=1/14,min_periods=14,adjust=False).mean()
    _l = (-_d.clip(upper=0)).ewm(alpha=1/14,min_periods=14,adjust=False).mean()
    f_rsi    = float(np.clip(100-100/(1+float(_g.iloc[-1])/max(float(_l.iloc[-1]),1e-10)),0,100))
    _rsi_s   = (100-100/(1+_g/_l.replace(0,1e-10))).clip(0,100)
    _r14     = _rsi_s.tail(14)
    f_stoch  = float(np.clip((_rsi_s.iloc[-1]-_r14.min())/max(float(_r14.max()-_r14.min()),1e-10)*100,0,100))
    _bm = float(ps.rolling(20).mean().iloc[-1]); _bs = max(float(ps.rolling(20).std().iloc[-1]),1e-10)
    f_bb     = float(np.clip((cur-(_bm-2*_bs))/(4*_bs)*100,0,100))
    _ps2y    = ps.tail(504) if len(ps)>=63 else ps
    _zm,_zs  = float(_ps2y.mean()),max(float(_ps2y.std()),1e-10)
    f_zscore = float(np.clip((cur-_zm)/_zs*20+50,0,100))
    _h52 = float(ps.tail(252).max() if len(ps)>=63 else ps.max())
    _l52 = float(ps.tail(252).min() if len(ps)>=63 else ps.min())
    f_pos52  = float(np.clip((cur-_l52)/max(_h52-_l52,1e-10)*100,0,100))
    _ma200   = float(ps.tail(200).mean() if len(ps)>=63 else ps.mean())
    f_ma200  = float(np.clip((cur/max(_ma200,1e-10)-1)*100*2+50,0,100))
    _ma50    = float(ps.tail(50).mean() if len(ps)>=22 else ps.mean())
    f_ma_conv= float(np.clip(-(_ma50/max(_ma200,1e-10)-1)*100*10+50,0,100))
    _e12=ps.ewm(span=12,min_periods=12,adjust=False).mean()
    _e26=ps.ewm(span=26,min_periods=26,adjust=False).mean()
    _mh=(_e12-_e26)-(_e12-_e26).ewm(span=9,min_periods=9,adjust=False).mean()
    _mstd=max(float(_mh.tail(126).std()),1e-10)
    f_macd   = float(np.clip((-float(_mh.iloc[-1])/(_mstd*2)+1)/2*100,0,100))
    _ret=ps.pct_change()
    _v20=float(_ret.tail(20).std()*np.sqrt(252)*100) if len(ps)>=20 else 15.0
    _v60=float(_ret.tail(60).std()*np.sqrt(252)*100) if len(ps)>=60 else 15.0
    _pdir=1.0 if cur>_ma200 else -1.0
    f_vol    = float(np.clip(50+_pdir*(_v20/max(_v60,1e-10)-1)*25,0,100))
    _roc10   = float((cur/float(ps.iloc[-11])-1)*100) if len(ps)>=11 else 0.0
    f_roc10  = float(np.clip((_roc10+10)/20*100,0,100))
    score = float(np.clip(
        f_rsi*0.12+f_stoch*0.07+f_bb*0.10+f_zscore*0.20+f_pos52*0.08+
        f_ma200*0.12+f_ma_conv*0.08+f_macd*0.08+f_vol*0.08+f_roc10*0.07,0,100))
    return score, {"rsi":f_rsi,"stoch_rsi":f_stoch,"bb":f_bb,"zscore":f_zscore,
                   "pos52":f_pos52,"ma200":f_ma200,"ma_conv":f_ma_conv,
                   "macd":f_macd,"vol_regime":f_vol,"roc10":f_roc10,
                   "raw_roc10":_roc10,"ma50_val":_ma50,"ma200_val":_ma200,
                   "golden_cross":bool(_ma50>_ma200)}


def compute_signal_series(ps: pd.Series, n: int = 0) -> list:
    if n > 0:
        ps=ps.tail(n)
    _d=ps.diff()
    _g=_d.clip(lower=0).ewm(alpha=1/14,min_periods=14,adjust=False).mean()
    _l=(-_d.clip(upper=0)).ewm(alpha=1/14,min_periods=14,adjust=False).mean()
    _rsi=(100-100/(1+_g/_l.replace(0,1e-10))).clip(0,100)
    _stoch=((_rsi-_rsi.rolling(14).min())/(_rsi.rolling(14).max()-_rsi.rolling(14).min()).replace(0,1e-10)*100).clip(0,100)
    _bm,_bs=ps.rolling(20).mean(),ps.rolling(20).std().replace(0,1e-10)
    _bb=((ps-(_bm-2*_bs))/(4*_bs)*100).clip(0,100)
    _zm=ps.rolling(252,min_periods=63).mean(); _zs=ps.rolling(252,min_periods=63).std().replace(0,1e-10)
    _zscore=((ps-_zm)/_zs*20+50).clip(0,100)
    _h52=ps.rolling(252,min_periods=63).max(); _l52=ps.rolling(252,min_periods=63).min()
    _pos52=((ps-_l52)/(_h52-_l52).replace(0,1e-10)*100).clip(0,100)
    _ma200=ps.rolling(200,min_periods=63).mean()
    _dev200=((ps/_ma200.replace(0,1e-10)-1)*100*2+50).clip(0,100)
    _ma50=ps.rolling(50,min_periods=22).mean()
    _conv=(-(_ma50/_ma200.replace(0,1e-10)-1)*100*10+50).clip(0,100)
    _e12=ps.ewm(span=12,min_periods=12,adjust=False).mean(); _e26=ps.ewm(span=26,min_periods=26,adjust=False).mean()
    _ml=_e12-_e26; _mh=_ml-_ml.ewm(span=9,min_periods=9,adjust=False).mean()
    _macd_s=((-_mh/_mh.rolling(126,min_periods=30).std().replace(0,1e-10)/2+1)/2*100).clip(0,100)
    _ret=ps.pct_change()
    _vr=(_ret.rolling(20).std()/_ret.rolling(60).std().replace(0,1e-10))
    _pdir=(ps>_ma200).astype(float)*2-1
    _vol_s=(50+_pdir*(_vr-1)*25).clip(0,100)
    _roc_s=(((ps/ps.shift(10)-1)*100+10)/20*100).clip(0,100)
    sig=(_rsi*0.12+_stoch*0.07+_bb*0.10+_zscore*0.20+_pos52*0.08+
         _dev200*0.12+_conv*0.08+_macd_s*0.08+_vol_s*0.08+_roc_s*0.07).clip(0,100)
    return [round(float(v),2) if not (isinstance(v,float) and np.isnan(v)) else None for v in sig.values]


# ── Buffett scorecard ─────────────────────────────────────────
def compute_buffett_scores(df: pd.DataFrame, ticker: str):
    fund=FUNDAMENTALS[ticker]; cur=df["Close"].iloc[-1]
    _52w=df["Close"].loc[df.index>=df.index[-1]-pd.DateOffset(weeks=52)]
    h52,l52=_52w.max(),_52w.min()
    pos_eps=[v for v in fund["eps"].values() if v>0]
    avg_eps=np.mean(pos_eps) if pos_eps else 0
    iv=avg_eps*1.03/0.07 if avg_eps>0 else 0
    mos=(iv-cur)/iv*100 if iv>0 else -100
    sc={}
    sc["Intrinsic Value"]    =9 if iv>cur*1.25 else(6 if iv>cur else(4 if iv>cur*0.8 else 2))
    sc["Margin of Safety"]   =9 if mos>=25 else(7 if mos>=10 else(5 if mos>=0 else 3))
    sc["Economic Moat"]      =round(np.mean(list(fund["moat"].values())))
    eps_vals=list(fund["eps"].values())
    cons=sum(1 for e in eps_vals if e>0)/len(eps_vals)
    sc["Consistent Earnings"]=9 if cons>=0.9 else(6 if cons>=0.7 else(4 if cons>=0.5 else 2))
    roe_vals=list(fund["roe_pct"].values()); pos_roe=[r for r in roe_vals if r>0]
    avg_roe=np.mean(pos_roe) if pos_roe else 0
    sc["Return on Equity"]   =9 if(avg_roe>=20 and roe_vals[-1]>=15) else(6 if avg_roe>=15 else(4 if avg_roe>=10 else 2))
    de=list(fund["debt_to_equity"].values())[-1]
    sc["Low Debt"]           =9 if de<0.3 else(7 if de<0.5 else(5 if de<0.8 else 3))
    sc["Management Quality"] =7 if ticker=="MU" else 6
    ten_yr=0.0
    if len(df)>252*10: ten_yr=((cur/df["Close"].iloc[-252*10])**(1/10)-1)*100
    sc["Long-term Value"]    =8 if ten_yr>10 else(6 if ten_yr>5 else(4 if ten_yr>0 else 3))
    pos_range=(cur-l52)/(h52-l52)*100 if(h52-l52)>0 else 50
    sc["Contrarian Signal"]  =9 if pos_range<30 else(7 if pos_range<50 else(5 if pos_range<70 else 3))
    _5y=df["Close"].loc[df.index>=df.index[-1]-pd.DateOffset(years=5)]
    dd=((_5y/_5y.cummax())-1).min()*100
    sc["Downside Protection"]=8 if abs(dd)<20 else(5 if abs(dd)<40 else 3)
    W={"Intrinsic Value":0.15,"Margin of Safety":0.15,"Economic Moat":0.12,
       "Consistent Earnings":0.10,"Return on Equity":0.10,"Low Debt":0.08,
       "Management Quality":0.08,"Long-term Value":0.08,
       "Contrarian Signal":0.07,"Downside Protection":0.07}
    bs=sum(sc[k]*W[k]*10 for k in sc)
    return sc,bs,iv,mos


def get_action(bs: float, sig: float) -> tuple[str,str,str]:
    q="excellent" if bs>=75 else"good" if bs>=60 else"average" if bs>=45 else"weak" if bs>=30 else"poor"
    t="strong_buy" if sig<=30 else"buy" if sig<=50 else"neutral" if sig<=65 else"caution" if sig<=80 else"sell"
    M={("excellent","strong_buy"):("BUY MAX","#00cc66","Best quality at cheapest entry"),
       ("excellent","buy"):       ("BUY, DCA","#88cc00","Great stock at good price"),
       ("excellent","neutral"):   ("Hold","#aaaaaa","Excellent quality but timing not ideal"),
       ("excellent","caution"):   ("Hold","#aaaaaa","Great stock but price trending high"),
       ("excellent","sell"):      ("Take Profit","#ffaa00","Excellent but overbought"),
       ("good","strong_buy"):     ("BUY","#00cc66","Good quality at low price"),
       ("good","buy"):            ("BUY, DCA","#88cc00","Good stock at reasonable price"),
       ("good","neutral"):        ("Hold","#aaaaaa","Hold — wait for better entry"),
       ("good","caution"):        ("Hold","#aaaaaa","Good stock but expensive"),
       ("good","sell"):           ("Reduce","#ff8800","Good stock overbought — trim"),
       ("average","strong_buy"):  ("Buy Small","#88cc00","Average quality at cheap price"),
       ("average","buy"):         ("Hold","#aaaaaa","Average quality — hold if owned"),
       ("average","neutral"):     ("Hold","#aaaaaa","No compelling action"),
       ("average","caution"):     ("Hold","#aaaaaa","No compelling reason to act"),
       ("average","sell"):        ("Reduce","#ff8800","Average stock at high price — trim"),
       ("weak","strong_buy"):     ("Do Not Buy","#ff4444","Weak fundamentals — value trap"),
       ("weak","buy"):            ("Do Not Buy","#ff4444","Weak fundamentals — avoid"),
       ("weak","neutral"):        ("Sell Partially","#ff8800","Start exiting"),
       ("weak","caution"):        ("Sell","#ff4444","Weak and overpriced — exit"),
       ("weak","sell"):           ("Sell","#ff4444","Weak and overbought — sell"),
       ("poor","strong_buy"):     ("Do Not Buy","#ff4444","Poor quality — do not buy"),
       ("poor","buy"):            ("Do Not Buy","#ff4444","Poor quality — avoid"),
       ("poor","neutral"):        ("Sell","#ff4444","Exit position"),
       ("poor","caution"):        ("Sell","#ff4444","Exit position"),
       ("poor","sell"):           ("Sell All","#ff0000","Worst combination — exit completely")}
    return M.get((q,t),("Hold","#aaaaaa","No clear signal"))


def compute_forecast(df: pd.DataFrame) -> dict:
    cur=float(df["Close"].iloc[-1]); target=pd.Timestamp("2027-06-30")
    try:
        from statsmodels.tsa.arima.model import ARIMA as _ARIMA
        monthly=df["Close"].resample("ME").last().dropna(); mlog=np.log(monthly)
        last_date=monthly.index[-1]
        m=max(1,(target.year-last_date.year)*12+(target.month-last_date.month))
        fitted=_ARIMA(mlog,order=(2,1,2)).fit()
        fc_p=np.exp(fitted.forecast(steps=m))
        ci=np.exp(fitted.get_forecast(steps=m).conf_int())
        fc_dates=pd.date_range(start=last_date+pd.DateOffset(months=1),periods=m,freq="ME")
        dr=df["Close"].pct_change().dropna()
        td=max(1,np.busday_count(df.index[-1].date(),target.date()))
        np.random.seed(42)
        paths=cur*np.cumprod(1+np.random.normal(dr.mean(),dr.std(),(5000,td)),axis=1)
        final=paths[:,-1]
        wa,wm=0.4,0.6
        return {"bear":round(wa*float(ci.iloc[-1,0])+wm*float(np.percentile(final,10)),2),
                "base":round(wa*float(fc_p.iloc[-1])+wm*float(np.mean(final)),2),
                "bull":round(wa*float(ci.iloc[-1,1])+wm*float(np.percentile(final,90)),2),
                "dates":[d.strftime("%Y-%m") for d in fc_dates],
                "arima":[round(float(v),2) for v in fc_p.values],
                "arima_lower":[round(float(v),2) for v in ci.iloc[:,0].values],
                "arima_upper":[round(float(v),2) for v in ci.iloc[:,1].values],
                "target":target.strftime("%B %Y"),"current":round(cur,2)}
    except Exception as e:
        print(f"  Forecast fallback ({e})")
        return {"bear":round(cur*0.75,2),"base":round(cur*1.1,2),"bull":round(cur*1.45,2),
                "dates":[],"arima":[],"arima_lower":[],"arima_upper":[],
                "target":target.strftime("%B %Y"),"current":round(cur,2)}


def build_ticker_data(ticker: str) -> dict:
    fund=FUNDAMENTALS[ticker]
    print(f"  {ticker}: loading...")
    df=load_stock_df(ticker)
    cur=float(df["Close"].iloc[-1]); prev=float(df["Close"].iloc[-2]) if len(df)>1 else cur
    df_p=df
    dates =[d.strftime("%Y-%m-%d") for d in df_p.index]
    prices=[round(float(v),2) for v in df_p["Close"].values]
    ma50  =[round(float(v),2) if not np.isnan(v) else None for v in df_p["Close"].rolling(50).mean().values]
    ma200 =[round(float(v),2) if not np.isnan(v) else None for v in df_p["Close"].rolling(200).mean().values]
    print(f"  {ticker}: signals...")
    sig_series=compute_signal_series(df["Close"])
    sig_score,factors=compute_signal_factors(df["Close"])
    fout={k:(round(float(v),2) if isinstance(v,(int,float,np.floating)) else bool(v)) for k,v in factors.items()}
    print(f"  {ticker}: Buffett...")
    scores,bs,iv,mos=compute_buffett_scores(df,ticker)
    action,action_color,action_desc=get_action(bs,sig_score)
    print(f"  {ticker}: forecast...")
    forecast=compute_forecast(df)
    fys=fund["fiscal_years"]; eps_fys=sorted(fund["eps"].keys())[-6:]
    return {"ticker":ticker,"name":TICKER_NAMES[ticker],"color":TICKER_COLORS[ticker],
            "current_price":round(cur,2),"day_change_pct":round((cur/prev-1)*100,2),
            "buffett_score":round(bs,1),"signal_score":round(sig_score,1),
            "intrinsic_value":round(iv,2),"action":action,"action_color":action_color,
            "action_desc":action_desc,"narrative":fund["narrative"],"moat":fund["moat"],
            "scores":scores,
            "score_weights":{"Intrinsic Value":15,"Margin of Safety":15,"Economic Moat":12,
                             "Consistent Earnings":10,"Return on Equity":10,"Low Debt":8,
                             "Management Quality":8,"Long-term Value":8,
                             "Contrarian Signal":7,"Downside Protection":7},
            "factors":fout,"dates":dates,"prices":prices,"ma50":ma50,"ma200":ma200,
            "signal_series":sig_series,"forecast":forecast,
            "norm_prices":[round(p/prices[0]*100,2) for p in prices],
            "fund":{"fiscal_years":fys,
                    "revenue":[fund["revenue_billions"].get(y) for y in fys],
                    "net_income":[fund["net_income_billions"].get(y) for y in fys],
                    "gross_margin":[fund["gross_margin_pct"].get(y) for y in fys],
                    "eps_years":eps_fys,
                    "eps":{str(y):fund["eps"].get(y) for y in eps_fys},
                    "roe":{str(y):fund["roe_pct"].get(y) for y in eps_fys},
                    "de":{str(y):fund["debt_to_equity"].get(y) for y in eps_fys}}}


# ── HTML template ─────────────────────────────────────────────

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>InvestorGPT</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"/>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js"></script>
<style>
:root{--bg:#f0f2f5;--card-bg:#fff;--text:#212529;--muted:#888;--shadow:rgba(0,0,0,.08);--shadow-sm:rgba(0,0,0,.07)}
[data-theme="dark"]{--bg:#1a1d23;--card-bg:#2d3139;--text:#e4e6ea;--muted:#aaa;--shadow:rgba(0,0,0,.3);--shadow-sm:rgba(0,0,0,.2)}
body{background:var(--bg);font-family:'Segoe UI',sans-serif;color:var(--text);transition:background .3s,color .3s}
.card{border:none;border-radius:12px;box-shadow:0 2px 10px var(--shadow);background:var(--card-bg);color:var(--text)}
.metric-card{border-radius:10px;padding:14px 18px;background:var(--card-bg);box-shadow:0 1px 6px var(--shadow-sm)}
.metric-val{font-size:1.4rem;font-weight:700}
.metric-lbl{font-size:.75rem;color:var(--muted);text-transform:uppercase;letter-spacing:.03em}
.tab-pane canvas{max-height:300px}
.factor-chip{display:inline-block;padding:4px 10px;border-radius:20px;font-size:.78rem;font-weight:600;margin:2px}
.action-box{border-radius:12px;padding:16px 20px;color:#fff}
.caveat{font-size:.78rem;color:var(--muted)}
.nav-pills .nav-link.active{background:#0d6efd}
.ticker-btn.active{background:#0d6efd!important;color:#fff!important;border-color:#0d6efd!important}
.theme-toggle{cursor:pointer;font-size:1.2rem;padding:4px 8px;border-radius:8px;border:1px solid #dee2e6;background:transparent}
.footer{text-align:center;padding:20px 0 10px;font-size:.8rem;color:var(--muted);border-top:1px solid rgba(128,128,128,.2);margin-top:30px}
</style>
</head>
<body>
<div class="container-fluid py-3 px-4">

<!-- header -->
<div class="d-flex align-items-center mb-3 gap-3">
  <div>
    <h4 class="mb-0 fw-bold">&#129302; InvestorGPT</h4>
    <small class="text-muted">AI-Powered Semiconductor Investment Advisor (INTC &amp; MU) &middot; Generated: <span id="genTs"></span></small>
  </div>
  <div class="ms-auto d-flex align-items-center gap-2">
    <div class="btn-group" role="group">
      <button class="btn btn-outline-primary ticker-btn active" onclick="switchTicker('INTC',this)">INTC</button>
      <button class="btn btn-outline-primary ticker-btn" onclick="switchTicker('MU',this)">MU</button>
      <button class="btn btn-outline-secondary ticker-btn" onclick="switchTicker('CMP',this)">Compare</button>
    </div>
    <button class="theme-toggle" onclick="toggleTheme()" title="Toggle dark mode">&#127763;</button>
  </div>
</div>

<!-- metric strip -->
<div class="row g-2 mb-3" id="metricStrip"></div>

<!-- single-ticker view -->
<div id="tickerView">
  <ul class="nav nav-pills mb-3" id="mainTabs">
    <li class="nav-item"><button class="nav-link active" data-tab="price">&#128200; Price &amp; Signal</button></li>
    <li class="nav-item"><button class="nav-link" data-tab="buffett">&#129658; Buffett Score</button></li>
    <li class="nav-item"><button class="nav-link" data-tab="fund">&#128196; Fundamentals</button></li>
    <li class="nav-item"><button class="nav-link" data-tab="forecast">&#128302; Forecast</button></li>
    <li class="nav-item"><button class="nav-link" data-tab="chat">&#129302; AI Chat</button></li>
  </ul>

  <!-- price tab -->
  <div id="tab-price">
    <div class="mb-2 d-flex align-items-center gap-3 flex-wrap">
      <div class="btn-group btn-group-sm" id="periodGroup">
        <button class="btn btn-outline-secondary" onclick="setPeriod(1)">1Y</button>
        <button class="btn btn-outline-secondary active" onclick="setPeriod(3)">3Y</button>
        <button class="btn btn-outline-secondary" onclick="setPeriod(5)">5Y</button>
        <button class="btn btn-outline-secondary" onclick="setPeriod(10)">10Y</button>
        <button class="btn btn-outline-secondary" onclick="setPeriod(20)">20Y</button>
        <button class="btn btn-outline-secondary" onclick="setPeriod(0)">All</button>
      </div>
      <div id="rangeSliderWrap" style="display:none;flex:1;min-width:250px">
        <div class="d-flex align-items-center gap-2">
          <input type="range" id="rangeStart" class="form-range" min="0" value="0" oninput="onRangeChange()" style="flex:1">
          <input type="range" id="rangeEnd" class="form-range" min="0" value="0" oninput="onRangeChange()" style="flex:1">
        </div>
        <div class="text-center"><small class="text-muted" id="rangeLbl"></small></div>
      </div>
    </div>
    <div class="card p-3 mb-3">
      <h6 class="fw-semibold">Price &amp; Moving Averages</h6>
      <canvas id="priceChart"></canvas>
    </div>
    <div class="card p-3 mb-3">
      <h6 class="fw-semibold">Buy/Sell Signal (0=Buy, 100=Sell)</h6>
      <canvas id="signalChart"></canvas>
    </div>
    <div class="card p-3">
      <h6 class="fw-semibold mb-2">Signal Factors</h6>
      <div id="factorTiles"></div>
    </div>
  </div>

  <!-- buffett tab -->
  <div id="tab-buffett" style="display:none">
    <div class="row g-3">
      <div class="col-lg-4">
        <div class="card p-3">
          <h6 class="fw-semibold mb-2">Scorecard</h6>
          <table class="table table-sm mb-0" style="font-size:12px;" id="buffettTable"></table>
        </div>
      </div>
      <div class="col-lg-4">
        <div class="card p-3 h-100">
          <h6 class="fw-semibold mb-2">Radar</h6>
          <canvas id="radarChart"></canvas>
        </div>
      </div>
      <div class="col-lg-4">
        <div class="card p-3 h-100" id="decisionMatrixCard"></div>
      </div>
    </div>
  </div>

  <!-- fundamentals tab -->
  <div id="tab-fund" style="display:none">
    <div class="row g-3">
      <div class="col-md-4"><div class="card p-3"><h6 class="fw-semibold">Revenue ($B)</h6>
        <canvas id="revChart"></canvas></div></div>
      <div class="col-md-4"><div class="card p-3"><h6 class="fw-semibold">Net Income ($B)</h6>
        <canvas id="niChart"></canvas></div></div>
      <div class="col-md-4"><div class="card p-3"><h6 class="fw-semibold">Gross Margin %</h6>
        <canvas id="gmChart"></canvas></div></div>
    </div>
    <div class="card p-3 mt-3">
      <h6 class="fw-semibold mb-2">Key Metrics Table</h6>
      <div class="table-responsive"><table class="table table-sm table-hover" id="fundTable"></table></div>
    </div>
    <div class="card p-3 mt-3"><p id="narrative" class="mb-0 fst-italic text-muted"></p></div>
  </div>

  <!-- forecast tab -->
  <div id="tab-forecast" style="display:none">
    <div class="row g-3">
      <div class="col-lg-9">
        <div class="card p-3"><h6 class="fw-semibold">18-Month Price Forecast (ARIMA + Monte Carlo)</h6>
          <canvas id="forecastChart"></canvas>
          <p class="caveat mt-2 mb-0">ARIMA(2,1,2) 40% + Monte Carlo 5000 sims 60% ensemble. Not investment advice.</p>
        </div>
      </div>
      <div class="col-lg-3">
        <div class="card p-3 h-100" id="forecastMetrics"></div>
      </div>
    </div>
  </div>

  <!-- ai chat tab -->
  <div id="tab-chat" style="display:none">
    <div class="row g-3">
      <div class="col-lg-8">
        <div class="card p-3 h-100 d-flex flex-column" style="min-height:520px">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <h6 class="fw-semibold mb-0">&#129302; InvestorGPT</h6>
            <div class="btn-group btn-group-sm" id="chatModeGroup">
              <button class="btn btn-outline-secondary" id="modeServer" onclick="setChatMode('server')">Server AI</button>
              <button class="btn btn-outline-secondary" id="modeDirect" onclick="setChatMode('direct')">Direct API</button>
              <button class="btn btn-outline-secondary" id="modeRag"    onclick="setChatMode('rag')">RAG Only</button>
            </div>
          </div>
          <div id="chatServerStatus" class="small mb-2"></div>
          <div id="chatHistory" style="flex:1;overflow-y:auto;background:#f8f9fa;border-radius:8px;padding:12px;min-height:320px;max-height:380px;" class="mb-3"></div>
          <div class="input-group">
            <input id="chatInput" type="text" class="form-control" placeholder="Ask about INTC or MU..." onkeydown="if(event.key==='Enter')sendChat()">
            <button class="btn btn-primary" onclick="sendChat()" id="chatSendBtn">Send</button>
            <button class="btn btn-outline-danger" onclick="clearChatSession()" title="Clear conversation memory">&#128465;</button>
          </div>
          <div class="mt-2">
            <span class="caveat">Suggested: </span>
            <span class="caveat" style="cursor:pointer;text-decoration:underline" onclick="setQ('What is Intel revenue trend 2022-2024?')">Intel revenue trend</span> &middot;
            <span class="caveat" style="cursor:pointer;text-decoration:underline" onclick="setQ('Compare INTC vs MU returns 2023 to 2024')">INTC vs MU returns</span> &middot;
            <span class="caveat" style="cursor:pointer;text-decoration:underline" onclick="setQ('What is Micron HBM strategy?')">Micron HBM strategy</span>
          </div>
        </div>
      </div>
      <div class="col-lg-4">
        <div class="card p-3 mb-3" style="max-height:280px;overflow-y:auto">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <h6 class="fw-semibold mb-0">&#128214; Chat History</h6>
            <button class="btn btn-outline-secondary btn-sm" onclick="newChatSession()">+ New</button>
          </div>
          <div id="sessionList" class="list-group list-group-flush" style="font-size:.82rem"></div>
          <div class="caveat mt-2">Sessions persist for 1 week</div>
        </div>
        <div class="card p-3">
          <h6 class="fw-semibold mb-3">&#9881; AI Settings</h6>
          <div id="directApiPanel" style="display:none">
            <label class="form-label small fw-semibold">Provider</label>
            <select id="aiProvider" class="form-select form-select-sm mb-2" onchange="saveAiSettings()">
              <option value="openai">OpenAI</option>
              <option value="gemini">Gemini</option>
            </select>
            <label class="form-label small fw-semibold">API Key</label>
            <div class="input-group input-group-sm mb-1">
              <input type="password" id="aiApiKey" class="form-control" placeholder="sk-..." oninput="debounceValidate()">
              <button class="btn btn-outline-secondary" onclick="clearApiKey()">Clear</button>
            </div>
            <div id="keyStatus" class="small mb-2"></div>
            <label class="form-label small fw-semibold">Model</label>
            <select id="aiModel" class="form-select form-select-sm mb-2" onchange="saveAiSettings()"></select>
          </div>
          <label class="form-label small fw-semibold">Temperature <span id="tempVal">0.7</span></label>
          <input type="range" id="aiTemp" class="form-range mb-2" min="0" max="2" step="0.1" value="0.7" oninput="document.getElementById('tempVal').textContent=this.value;saveAiSettings()">
          <label class="form-label small fw-semibold">Max Tokens</label>
          <select id="aiMaxTokens" class="form-select form-select-sm mb-2" onchange="saveAiSettings()">
            <option value="512">512</option><option value="1024">1024</option>
            <option value="2048" selected>2048</option><option value="4096">4096</option><option value="8192">8192</option>
          </select>
          <label class="form-label small fw-semibold">Top P <span id="topPVal">1.0</span></label>
          <input type="range" id="aiTopP" class="form-range mb-3" min="0" max="1" step="0.05" value="1.0" oninput="document.getElementById('topPVal').textContent=this.value;saveAiSettings()">
          <div id="serverModeInfo" class="alert alert-info p-2 small mb-0" style="display:none">
            &#127760; Using server-side API key. No browser key needed.
          </div>
          <div id="ragModeInfo" class="alert alert-secondary p-2 small mb-0" style="display:none">
            &#128196; RAG Only: FAISS retrieval without GPT synthesis.
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- compare view -->
<div id="cmpView" style="display:none">
  <div class="row g-3 mb-3" id="cmpCards"></div>
  <div class="row g-3">
    <div class="col-lg-6">
      <div class="card p-3"><h6 class="fw-semibold">Normalised Price (base=100)</h6>
        <canvas id="cmpChart"></canvas></div>
    </div>
    <div class="col-lg-3">
      <div class="card p-3"><h6 class="fw-semibold">Score Comparison</h6>
        <canvas id="cmpRadar"></canvas></div>
    </div>
    <div class="col-lg-3">
      <div class="card p-3"><h6 class="fw-semibold">Buffett vs Signal</h6>
        <canvas id="cmpBar"></canvas></div>
    </div>
  </div>
</div>

</div><!-- /container -->

<script>
const ALL = __DATA_JSON__;
const TICKERS = ['INTC','MU'];
let activeTicker = 'INTC';
let charts = {};

// ── utils ──────────────────────────────────────────────────────
function destroyChart(id){ if(charts[id]){ charts[id].destroy(); delete charts[id]; } }
function mkChart(id,cfg){ destroyChart(id); const c=document.getElementById(id); if(!c)return; charts[id]=new Chart(c,cfg); }
function pct(v){ return v==null?'N/A':(v>0?'+':'')+v.toFixed(2)+'%'; }
function dollar(v){ return v==null?'N/A':'$'+v.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2}); }
function scoreColor(s){ return s>=70?'#dc3545':s>=50?'#fd7e14':s>=35?'#ffc107':'#198754'; }
function sigLabel(s){ return s<=30?'Strong Buy':s<=50?'Buy':s<=65?'Neutral':s<=80?'Caution':'Sell'; }
function buffLabel(b){ return b>=75?'Excellent':b>=60?'Good':b>=45?'Average':b>=30?'Weak':'Poor'; }

// ── generate timestamp ─────────────────────────────────────────
document.getElementById('genTs').textContent = ALL.generated || 'N/A';

// ── metric strip ──────────────────────────────────────────────
function renderStrip(d){
  const strip = document.getElementById('metricStrip');
  const dc = d.day_change_pct >= 0 ? 'text-success' : 'text-danger';
  const iv_pct = d.intrinsic_value>0 ? ((d.intrinsic_value-d.current_price)/d.current_price*100).toFixed(1) : 'N/A';
  const cards = [
    {lbl:'Price', val: dollar(d.current_price), sub:`<span class="${dc}">${pct(d.day_change_pct)} today</span>`},
    {lbl:'Buffett Score', val:`${d.buffett_score.toFixed(1)}/100`, sub:`<span style="color:${d.action_color}">${buffLabel(d.buffett_score)}</span>`},
    {lbl:'Signal Score', val:`${d.signal_score.toFixed(1)}/100`, sub:`<span style="color:${scoreColor(d.signal_score)}">${sigLabel(d.signal_score)}</span>`},
    {lbl:'Intrinsic Value', val:dollar(d.intrinsic_value), sub:`${iv_pct!='N/A'?iv_pct+'% vs price':'DCF estimate'}`},
    {lbl:'Action', val:`<span style="color:${d.action_color}">${d.action}</span>`, sub:d.action_desc},
  ];
  strip.innerHTML = cards.map(c=>`
    <div class="col-6 col-md-4 col-lg">
      <div class="metric-card">
        <div class="metric-lbl">${c.lbl}</div>
        <div class="metric-val">${c.val}</div>
        <div class="caveat">${c.sub}</div>
      </div>
    </div>`).join('');
}

// ── period filter ─────────────────────────────────────────────
let activePeriod = 3;
let customRange = null; // [startIdx, endIdx] for range slider
function setPeriod(years){
  activePeriod = years;
  customRange = null;
  document.querySelectorAll('#periodGroup button').forEach(b=>b.classList.remove('active'));
  event.target.classList.add('active');
  const slider = document.getElementById('rangeSliderWrap');
  if(slider) slider.style.display = years===0 ? '' : 'none';
  renderPriceTab(ALL[activeTicker]);
}
function sliceByPeriod(arr, dates, years){
  if(customRange) return arr.slice(customRange[0], customRange[1]+1);
  if(!years || !arr) return arr;
  const total = dates.length;
  const tradingDaysPerYear = 252;
  const keep = Math.min(years * tradingDaysPerYear, total);
  return arr.slice(total - keep);
}
function onRangeChange(){
  const d = ALL[activeTicker];
  const lo = parseInt(document.getElementById('rangeStart').value);
  const hi = parseInt(document.getElementById('rangeEnd').value);
  if(lo >= hi) return;
  customRange = [lo, hi];
  document.getElementById('rangeLbl').textContent =
    d.dates[lo].split(' ')[0] + ' → ' + d.dates[hi].split(' ')[0];
  renderPriceTab(d);
}
function initRangeSlider(){
  const d = ALL[activeTicker];
  const n = d.dates.length - 1;
  const rs = document.getElementById('rangeStart');
  const re = document.getElementById('rangeEnd');
  if(!rs) return;
  rs.max = n; re.max = n;
  rs.value = 0; re.value = n;
  document.getElementById('rangeLbl').textContent =
    d.dates[0].split(' ')[0] + ' → ' + d.dates[n].split(' ')[0];
}

// ── price & signal charts ─────────────────────────────────────
function renderPriceTab(d){
  const dates = sliceByPeriod(d.dates, d.dates, activePeriod);
  const prices = sliceByPeriod(d.prices, d.dates, activePeriod);
  const ma50 = sliceByPeriod(d.ma50, d.dates, activePeriod);
  const ma200 = sliceByPeriod(d.ma200, d.dates, activePeriod);
  const signals = sliceByPeriod(d.signal_series, d.dates, activePeriod);
  const clr = d.color;
  mkChart('priceChart',{type:'line',data:{
    labels:dates,
    datasets:[
      {label:'Price',data:prices,borderColor:clr,backgroundColor:clr+'18',borderWidth:1.5,pointRadius:0,tension:.2,fill:true},
      {label:'MA 50',data:ma50,borderColor:'#f59e0b',borderWidth:1.2,pointRadius:0,tension:.2,borderDash:[4,2]},
      {label:'MA 200',data:ma200,borderColor:'#6366f1',borderWidth:1.2,pointRadius:0,tension:.2,borderDash:[6,3]},
    ]},options:{responsive:true,aspectRatio:4,interaction:{mode:'index',intersect:false},
      plugins:{legend:{position:'top'},tooltip:{callbacks:{label:ctx=>`${ctx.dataset.label}: $${ctx.parsed.y?.toFixed(2)}`}}},
      scales:{x:{ticks:{maxTicksLimit:12}},y:{ticks:{callback:v=>'$'+v}}}}});

  const sColors = signals.map(v=>v==null?'#ccc':scoreColor(v));
  mkChart('signalChart',{type:'line',data:{
    labels:dates,
    datasets:[{label:'Signal',data:signals,borderColor:'#6366f1',backgroundColor:sColors.map(c=>c+'44'),
               borderWidth:1.5,pointRadius:0,tension:.2,fill:true}]},
    options:{responsive:true,aspectRatio:4,interaction:{mode:'index',intersect:false},
      plugins:{legend:{display:false},
        tooltip:{callbacks:{label:ctx=>{const v=ctx.parsed.y; return v<=30?`Signal: ${v.toFixed(1)} (Buy)`:v<=50?`Signal: ${v.toFixed(1)} (Neutral-Buy)`:v<=70?`Signal: ${v.toFixed(1)} (Neutral-Sell)`:`Signal: ${v.toFixed(1)} (Sell)`;}}},
        annotation:{annotations:{b30:{type:'line',yMin:30,yMax:30,borderColor:'#198754',borderWidth:1,borderDash:[4,3]},
                                 b50:{type:'line',yMin:50,yMax:50,borderColor:'#ffc107',borderWidth:1,borderDash:[4,3]},
                                 b70:{type:'line',yMin:70,yMax:70,borderColor:'#dc3545',borderWidth:1,borderDash:[4,3]}}}},
      scales:{y:{min:0,max:100}}}});

  const FLABELS = ['RSI','Stoch RSI','BB %B','2Y Z-Score','52W Position','MA200 Dev','MA Conv','MACD Hist','Vol Regime','10d ROC'];
  const FKEYS   = ['rsi','stoch_rsi','bb','zscore','pos52','ma200','ma_conv','macd','vol_regime','roc10'];
  const tiles = document.getElementById('factorTiles');
  tiles.innerHTML = FKEYS.map((k,i)=>{
    const v = d.factors[k]; if(v==null) return '';
    const bg = scoreColor(v);
    return `<span class="factor-chip" style="background:${bg};color:#fff">${FLABELS[i]}: ${v.toFixed(1)}</span>`;
  }).join('');
  const gc = d.factors.golden_cross;
  tiles.innerHTML += `<span class="factor-chip" style="background:${gc?'#198754':'#dc3545'};color:#fff">
    ${gc?'Golden Cross':'Death Cross'}</span>`;
}

// ── buffett tab ───────────────────────────────────────────────
function renderBuffettTab(d){
  const tbl = document.getElementById('buffettTable');
  const W = d.score_weights;
  const rows = Object.entries(d.scores).map(([k,v])=>{
    const wt = W[k]||0; const contrib = (v*wt*10/100).toFixed(1);
    const bg = v>=8?'#198754':v>=6?'#ffc107':v>=4?'#fd7e14':'#dc3545';
    return `<tr><td style="padding:2px 4px;">${k}</td><td><span class="badge" style="background:${bg};font-size:10px;">${v}</span></td>
            <td class="text-muted" style="font-size:10px;">${wt}%</td><td class="text-end" style="font-size:10px;">${contrib}</td></tr>`;
  }).join('');
  tbl.innerHTML = `<thead><tr style="font-size:10px;color:#888;"><th>Principle</th><th>Score</th><th>Wt</th><th>Pts</th></tr></thead>
    <tbody>${rows}</tbody>
    <tfoot><tr class="fw-bold" style="font-size:11px;border-top:2px solid #ddd;"><td colspan="3">Total</td><td class="text-end">${d.buffett_score.toFixed(1)}</td></tr></tfoot>`;

  const labels = Object.keys(d.scores);
  const vals   = Object.values(d.scores);
  mkChart('radarChart',{type:'radar',data:{labels,datasets:[{label:d.ticker,data:vals,
    borderColor:d.color,backgroundColor:d.color+'33',pointBackgroundColor:d.color,pointRadius:2}]},
    options:{responsive:true,maintainAspectRatio:true,scales:{r:{min:0,max:10,ticks:{stepSize:2,font:{size:9}},pointLabels:{font:{size:9}}}},plugins:{legend:{display:false}}}});

  // 5x5 Decision Matrix
  const qZones = [['≥75 Excellent','excellent'],['≥60 Good','good'],['≥45 Average','average'],['≥30 Weak','weak'],['<30 Poor','poor']];
  const tZones = [['≤30 Strong Buy','strong_buy'],['≤50 Buy','buy'],['≤65 Neutral','neutral'],['≤80 Caution','caution'],['>80 Sell','sell']];
  const dmLookup = {
    'excellent_strong_buy':'BUY MAX','excellent_buy':'BUY, DCA','excellent_neutral':'Hold','excellent_caution':'Hold','excellent_sell':'Take Profit',
    'good_strong_buy':'BUY','good_buy':'BUY, DCA','good_neutral':'Hold','good_caution':'Hold','good_sell':'Reduce',
    'average_strong_buy':'Buy Small','average_buy':'Hold','average_neutral':'Hold','average_caution':'Hold','average_sell':'Reduce',
    'weak_strong_buy':'Do Not Buy','weak_buy':'Do Not Buy','weak_neutral':'Sell Partially','weak_caution':'Sell','weak_sell':'Sell',
    'poor_strong_buy':'Do Not Buy','poor_buy':'Do Not Buy','poor_neutral':'Sell','poor_caution':'Sell','poor_sell':'Sell All'
  };
  function cellIcon(act){
    if(act==='BUY MAX') return '✅';
    if(['BUY','BUY, DCA','Buy Small'].includes(act)) return '🟢';
    if(act==='Hold') return '⚪';
    if(['Take Profit','Reduce'].includes(act)) return '🟠';
    return '🔴';
  }
  function cellStyle(act, isCur){
    let bg,fg;
    if(['BUY MAX','BUY','BUY, DCA','Buy Small'].includes(act)){bg='#d4edda';fg='#155724';}
    else if(['Sell','Sell All','Do Not Buy','Sell Partially'].includes(act)){bg='#f8d7da';fg='#721c24';}
    else if(['Take Profit','Reduce'].includes(act)){bg='#fff3cd';fg='#856404';}
    else{bg='#f5f5f5';fg='#555';}
    const brd = isCur ? `2px solid ${fg}` : '1px solid #ccc';
    const fw = isCur ? '700' : '500';
    return `border:${brd};padding:2px 4px;background:${bg};color:${fg};font-weight:${fw};font-size:10px;text-align:center;line-height:1.3;white-space:nowrap;`;
  }
  const tHdrColors = ['#155724','#2d6a3f','#555','#856404','#721c24'];
  const qHdrColors = ['#155724','#2d6a3f','#555','#856404','#721c24'];
  const curQ = d.buffett_score>=75?'excellent':d.buffett_score>=60?'good':d.buffett_score>=45?'average':d.buffett_score>=30?'weak':'poor';
  const curT = d.signal_score<=30?'strong_buy':d.signal_score<=50?'buy':d.signal_score<=65?'neutral':d.signal_score<=80?'caution':'sell';

  let mHtml = '<div style="display:inline-block;"><table style="border-collapse:collapse;">';
  mHtml += '<tr><th style="border:1px solid #ccc;padding:3px 5px;background:#eef;color:#333;font-size:10px;font-weight:700;">Score\\Signal</th>';
  tZones.forEach(([lbl],i)=>{mHtml+=`<th style="border:1px solid #ccc;padding:2px 4px;background:#eef;color:${tHdrColors[i]};font-size:10px;font-weight:700;text-align:center;">${lbl}</th>`;});
  mHtml += '</tr>';
  qZones.forEach(([qLbl,qKey],qi)=>{
    mHtml += `<tr><th style="border:1px solid #ccc;padding:2px 5px;background:#eef;color:${qHdrColors[qi]};font-size:10px;font-weight:700;white-space:nowrap;">${qLbl}</th>`;
    tZones.forEach(([,tKey])=>{
      const act = dmLookup[qKey+'_'+tKey];
      const isCur = (qKey===curQ && tKey===curT);
      const icon = cellIcon(act);
      mHtml += `<td style="${cellStyle(act,isCur)}">${icon} ${act}${isCur?' ◀':''}</td>`;
    });
    mHtml += '</tr>';
  });
  mHtml += '</table></div>';

  const matrixDiv = document.getElementById('decisionMatrixCard');
  matrixDiv.innerHTML = `<div style="display:flex;flex-direction:column;height:100%;">
    <h6 class="fw-semibold mb-2">Decision Analysis</h6>
    <div style="flex:1;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;background:${d.action_color}18;border-radius:8px;padding:12px;margin-bottom:8px;">
      <div style="font-size:2rem;font-weight:900;color:${d.action_color};letter-spacing:1px;">${d.action}</div>
      <div style="font-size:12px;color:#555;margin-top:4px;">${d.action_desc}</div>
      <div style="font-size:11px;color:#777;margin-top:6px;">
        Buffett <b>${d.buffett_score.toFixed(1)}</b> · Signal <b>${d.signal_score.toFixed(1)}</b> · IV <b>${dollar(d.intrinsic_value)}</b>
      </div>
    </div>
    <div style="text-align:center;">${mHtml}</div>
  </div>`;
}

// ── fundamentals tab ──────────────────────────────────────────
function renderFundTab(d){
  const f=d.fund; const fys=f.fiscal_years.map(y=>'FY'+y);
  const clr=d.color; const clrA=clr+'cc'; const clrB=clr+'55';

  function barCfg(lbl,vals,fmt_fn){
    return {type:'bar',data:{labels:fys,datasets:[{label:lbl,data:vals,
      backgroundColor:vals.map(v=>v<0?'#dc354599':'#19875499'),borderRadius:4}]},
      options:{responsive:true,plugins:{legend:{display:false}},
        scales:{y:{ticks:{callback:v=>fmt_fn(v)}}}}};
  }
  mkChart('revChart',barCfg('Revenue $B',f.revenue,v=>'$'+v+'B'));
  mkChart('niChart', barCfg('Net Income $B',f.net_income,v=>'$'+v+'B'));
  mkChart('gmChart', barCfg('Gross Margin %',f.gross_margin,v=>v+'%'));

  const epsFys = f.eps_years;
  const ftbl = document.getElementById('fundTable');
  const hdr = `<thead class="table-light"><tr><th>Metric</th>${epsFys.map(y=>'<th>FY'+y+'</th>').join('')}</tr></thead>`;
  function metRow(lbl,obj,fmt){
    return `<tr><td>${lbl}</td>${epsFys.map(y=>{const v=obj[y];return '<td>'+(v==null?'N/A':fmt(v))+'</td>';}).join('')}</tr>`;
  }
  ftbl.innerHTML = hdr+'<tbody>'+
    metRow('EPS ($)',f.eps,v=>'$'+v.toFixed(2))+
    metRow('ROE %',f.roe,v=>v.toFixed(1)+'%')+
    metRow('D/E',f.de,v=>v.toFixed(2))+
    '</tbody>';

  document.getElementById('narrative').textContent = d.narrative;
}

// ── forecast tab ──────────────────────────────────────────────
function renderForecastTab(d){
  const fc=d.forecast; const cur=fc.current; const clr=d.color;
  const allDates = d.dates.concat(fc.dates);
  const histData = d.prices.concat(new Array(fc.dates.length).fill(null));
  const arimaData= new Array(d.dates.length).fill(null).concat(fc.arima);
  const lowerData= new Array(d.dates.length).fill(null).concat(fc.arima_lower);
  const upperData= new Array(d.dates.length).fill(null).concat(fc.arima_upper);
  mkChart('forecastChart',{type:'line',data:{labels:allDates,datasets:[
    {label:'History',data:histData,borderColor:clr,borderWidth:1.5,pointRadius:0,tension:.2},
    {label:'ARIMA',data:arimaData,borderColor:'#6366f1',borderWidth:1.5,borderDash:[5,3],pointRadius:0},
    {label:'Lower CI',data:lowerData,borderColor:'#6366f133',borderWidth:1,pointRadius:0,fill:false},
    {label:'Upper CI',data:upperData,borderColor:'#6366f133',borderWidth:1,pointRadius:0,fill:'-1',backgroundColor:'#6366f111'},
  ]},options:{responsive:true,interaction:{mode:'index',intersect:false},
    plugins:{legend:{position:'top'},tooltip:{callbacks:{label:ctx=>ctx.dataset.label+': $'+ctx.parsed.y?.toFixed(2)}}},
    scales:{x:{ticks:{maxTicksLimit:14}},y:{ticks:{callback:v=>'$'+v}}}}});

  const bearChg=((fc.bear-cur)/cur*100).toFixed(1); const baseChg=((fc.base-cur)/cur*100).toFixed(1); const bullChg=((fc.bull-cur)/cur*100).toFixed(1);
  document.getElementById('forecastMetrics').innerHTML = `
    <h6 class="fw-semibold">Target: ${fc.target}</h6>
    <div class="mt-3">
      <div class="mb-2"><span class="text-muted small">Current</span><div class="fw-bold">${dollar(cur)}</div></div>
      <div class="mb-2"><span class="text-muted small">Bear Case</span>
        <div class="fw-bold text-danger">${dollar(fc.bear)} <small>(${bearChg}%)</small></div></div>
      <div class="mb-2"><span class="text-muted small">Base Case</span>
        <div class="fw-bold text-primary">${dollar(fc.base)} <small>(${baseChg}%)</small></div></div>
      <div class="mb-2"><span class="text-muted small">Bull Case</span>
        <div class="fw-bold text-success">${dollar(fc.bull)} <small>(${bullChg}%)</small></div></div>
    </div>
    <p class="caveat mt-3">ARIMA(2,1,2) + Monte Carlo ensemble. Not financial advice.</p>`;
}

// ── compare view ──────────────────────────────────────────────
function renderCompare(){
  const [di,dm]=[ALL.INTC,ALL.MU];
  const cards = TICKERS.map(t=>{
    const d=ALL[t];
    return `<div class="col-md-6"><div class="card p-3">
      <h6 style="color:${d.color}">${d.name} (${t})</h6>
      <div class="row g-1 mt-1">
        <div class="col-6"><div class="metric-card"><div class="metric-lbl">Price</div>
          <div class="metric-val" style="font-size:1.1rem">${dollar(d.current_price)}</div></div></div>
        <div class="col-6"><div class="metric-card"><div class="metric-lbl">Action</div>
          <div class="fw-bold" style="color:${d.action_color}">${d.action}</div></div></div>
        <div class="col-6"><div class="metric-card"><div class="metric-lbl">Buffett</div>
          <div class="fw-bold">${d.buffett_score.toFixed(1)}</div></div></div>
        <div class="col-6"><div class="metric-card"><div class="metric-lbl">Signal</div>
          <div class="fw-bold" style="color:${scoreColor(d.signal_score)}">${d.signal_score.toFixed(1)}</div></div></div>
      </div>
    </div></div>`;
  });
  document.getElementById('cmpCards').innerHTML = cards.join('');

  const minLen = Math.min(di.norm_prices.length, dm.norm_prices.length);
  const dates = di.dates.slice(-minLen);
  mkChart('cmpChart',{type:'line',data:{labels:dates,datasets:[
    {label:'INTC',data:di.norm_prices.slice(-minLen),borderColor:di.color,borderWidth:1.5,pointRadius:0,tension:.2},
    {label:'MU',  data:dm.norm_prices.slice(-minLen),borderColor:dm.color, borderWidth:1.5,pointRadius:0,tension:.2},
  ]},options:{responsive:true,scales:{x:{ticks:{maxTicksLimit:12}},y:{ticks:{callback:v=>v+''}}},
    plugins:{legend:{position:'top'}}}});

  const radarLabels = Object.keys(di.scores);
  mkChart('cmpRadar',{type:'radar',data:{labels:radarLabels,datasets:[
    {label:'INTC',data:Object.values(di.scores),borderColor:di.color,backgroundColor:di.color+'33'},
    {label:'MU',  data:Object.values(dm.scores), borderColor:dm.color, backgroundColor:dm.color+'33'},
  ]},options:{scales:{r:{min:0,max:10,ticks:{stepSize:2}}},plugins:{legend:{position:'top'}}}});

  mkChart('cmpBar',{type:'bar',data:{labels:['Buffett Score','Signal Score'],datasets:[
    {label:'INTC',data:[di.buffett_score,di.signal_score],backgroundColor:di.color+'cc',borderRadius:4},
    {label:'MU',  data:[dm.buffett_score,dm.signal_score],backgroundColor:dm.color+'cc',  borderRadius:4},
  ]},options:{responsive:true,scales:{y:{max:100}},plugins:{legend:{position:'top'}}}});
}

// ── AI Chat ────────────────────────────────────────────────────
const RAG_SERVER = 'http://localhost:8503';
let chatMode = 'server';
let serverOnline = false;
let _validateTimer = null;
const _userPrefix = 'u_'+(localStorage.getItem('chat_user_id')||( ()=>{const id=Math.random().toString(36).slice(2,10); localStorage.setItem('chat_user_id',id); return id;})());
let _sessionId = localStorage.getItem('chat_active_session') || newSessionId();
function newSessionId(){ const id=_userPrefix+'_'+Date.now()+'_'+Math.random().toString(36).slice(2,6); localStorage.setItem('chat_active_session',id); return id; }

const OPENAI_MODELS  = ['gpt-4o','gpt-4o-mini','gpt-4-turbo','gpt-3.5-turbo'];
const GEMINI_MODELS  = ['gemini-2.0-flash','gemini-1.5-flash','gemini-1.5-pro'];

function loadAiSettings(){
  const saved = k => localStorage.getItem('ai_'+k);
  if(saved('provider')) document.getElementById('aiProvider').value = saved('provider');
  if(saved('apiKey'))   document.getElementById('aiApiKey').value   = saved('apiKey');
  if(saved('temp'))     { document.getElementById('aiTemp').value = saved('temp'); document.getElementById('tempVal').textContent = saved('temp'); }
  if(saved('tokens'))   document.getElementById('aiMaxTokens').value = saved('tokens');
  if(saved('topP'))     { document.getElementById('aiTopP').value = saved('topP'); document.getElementById('topPVal').textContent = saved('topP'); }
  updateModelList();
}
function saveAiSettings(){
  const s = (k,v) => localStorage.setItem('ai_'+k, v);
  s('provider', document.getElementById('aiProvider').value);
  s('temp',     document.getElementById('aiTemp').value);
  s('tokens',   document.getElementById('aiMaxTokens').value);
  s('topP',     document.getElementById('aiTopP').value);
  const key = document.getElementById('aiApiKey').value.trim();
  if(key) s('apiKey', key);
  updateModelList();
}
function updateModelList(){
  const prov = document.getElementById('aiProvider').value;
  const sel  = document.getElementById('aiModel');
  const saved = localStorage.getItem('ai_model');
  const list = prov==='gemini' ? GEMINI_MODELS : OPENAI_MODELS;
  sel.innerHTML = list.map(m=>`<option value="${m}"${m===saved?' selected':''}>${m}</option>`).join('');
  sel.onchange = ()=>{ localStorage.setItem('ai_model', sel.value); };
}
async function checkServer(){
  try{
    const r = await fetch(RAG_SERVER+'/health',{signal:AbortSignal.timeout(2000)});
    const j = await r.json();
    serverOnline = j.status==='ok';
    const el = document.getElementById('chatServerStatus');
    el.innerHTML = serverOnline
      ? '<span class="text-success">&#9679; Server online (port 8503)</span>'
      : '<span class="text-warning">&#9679; Server offline</span>';
    return serverOnline;
  } catch(e){
    serverOnline = false;
    document.getElementById('chatServerStatus').innerHTML = '<span class="text-danger">&#9679; Server offline &mdash; start rag_server.py</span>';
    return false;
  }
}
let _serverPoll = null;
async function initChat(){
  loadAiSettings();
  const online = await checkServer();
  const savedMode = localStorage.getItem('ai_chatMode');
  const key = localStorage.getItem('ai_apiKey');
  if(savedMode) setChatMode(savedMode);
  else if(online) setChatMode('server');
  else if(key) setChatMode('direct');
  else setChatMode('rag');
  if(!online && !_serverPoll){
    _serverPoll = setInterval(async ()=>{
      const ok = await checkServer();
      if(ok){ clearInterval(_serverPoll); _serverPoll=null; setChatMode('server'); }
    }, 5000);
  }
  loadSessionList();
}
function setChatMode(mode){
  chatMode = mode;
  localStorage.setItem('ai_chatMode', mode);
  ['server','direct','rag'].forEach(m=>{
    document.getElementById('mode'+m.charAt(0).toUpperCase()+m.slice(1))?.classList.toggle('active', m===mode);
  });
  document.getElementById('directApiPanel').style.display = mode==='direct' ? '' : 'none';
  document.getElementById('serverModeInfo').style.display  = mode==='server' ? '' : 'none';
  document.getElementById('ragModeInfo').style.display     = mode==='rag'    ? '' : 'none';
}
function setQ(q){ document.getElementById('chatInput').value=q; document.getElementById('chatInput').focus(); }
async function clearChatSession(){
  document.getElementById('chatHistory').innerHTML='';
  try{ await fetch(RAG_SERVER+'/chat/clear',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:_sessionId})}); }catch(e){}
  appendMsg('bot','Memory cleared. Starting fresh conversation.');
  loadSessionList();
}
function newChatSession(){
  _sessionId = newSessionId();
  document.getElementById('chatHistory').innerHTML='';
  appendMsg('bot','New session started. How can I help?');
  loadSessionList();
}
async function loadSessionList(){
  const el = document.getElementById('sessionList');
  if(!el) return;
  try{
    const r = await fetch(RAG_SERVER+'/chat/sessions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_prefix:_userPrefix})});
    const j = await r.json();
    if(!j.sessions||!j.sessions.length){ el.innerHTML='<div class="text-muted small">No sessions yet</div>'; return; }
    el.innerHTML = j.sessions.map(s=>{
      const active = s.session_id===_sessionId ? 'active fw-bold' : '';
      const age = s.age_hours<24 ? Math.round(s.age_hours)+'h ago' : Math.round(s.age_hours/24)+'d ago';
      return `<a href="#" class="list-group-item list-group-item-action py-1 px-2 ${active}" onclick="switchSession('${s.session_id}');return false;">
        <div class="d-flex justify-content-between"><span class="text-truncate" style="max-width:160px">${s.topic}</span><small class="text-muted">${age}</small></div>
        <small class="text-muted">${s.messages} msgs</small></a>`;
    }).join('');
  }catch(e){ el.innerHTML='<div class="text-muted small">Server offline</div>'; }
}
function switchSession(sid){
  _sessionId = sid;
  localStorage.setItem('chat_active_session', sid);
  document.getElementById('chatHistory').innerHTML='';
  appendMsg('bot','Switched to session. Your conversation context is restored on the server.');
  loadSessionList();
}
function appendMsg(role, html){
  const h = document.getElementById('chatHistory');
  const div = document.createElement('div');
  div.className = 'mb-2';
  div.innerHTML = role==='user'
    ? `<div class="text-end"><span class="badge bg-primary px-2 py-1" style="white-space:normal;max-width:80%;text-align:left">${html}</span></div>`
    : `<div><span style="background:#e9ecef;border-radius:8px;padding:8px 12px;display:inline-block;max-width:90%;font-size:.92rem">${html}</span></div>`;
  h.appendChild(div);
  h.scrollTop = h.scrollHeight;
}
function appendCite(txt){
  if(!txt) return;
  const h = document.getElementById('chatHistory');
  const div = document.createElement('div');
  div.className = 'mb-2';
  div.innerHTML = `<div class="caveat" style="padding-left:4px;color:#6c757d">${txt}</div>`;
  h.appendChild(div);
  h.scrollTop = h.scrollHeight;
}
async function sendChat(){
  const input = document.getElementById('chatInput');
  const q = input.value.trim();
  if(!q) return;
  input.value='';
  const btn = document.getElementById('chatSendBtn');
  btn.disabled=true; btn.textContent='...';
  appendMsg('user', q);
  const thinking = document.createElement('div');
  thinking.id='chatThinking'; thinking.className='mb-2';
  thinking.innerHTML='<span class="text-muted small"><em>Thinking...</em></span>';
  document.getElementById('chatHistory').appendChild(thinking);
  try{
    if(chatMode==='server')       await callServer(q);
    else if(chatMode==='rag')     await callRagOnly(q);
    else                          await callDirectApi(q);
  } catch(e){
    document.getElementById('chatThinking')?.remove();
    appendMsg('bot', '&#10060; Error: '+e.message);
  }
  btn.disabled=false; btn.textContent='Send';
  loadSessionList();
}
async function callServer(q){
  const r = await fetch(RAG_SERVER+'/chat/general',{
    method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({question:q, session_id:_sessionId, temperature:parseFloat(document.getElementById('aiTemp').value),
      max_tokens:parseInt(document.getElementById('aiMaxTokens').value)})
  });
  const j = await r.json();
  document.getElementById('chatThinking')?.remove();
  if(j.error){ appendMsg('bot','&#10060; '+j.error); return; }
  const meta = j.query_type ? `<br><span class="caveat">Route: ${j.query_type} | Tickers: ${(j.tickers_detected||[]).join(',')}</span>` : '';
  appendMsg('bot', j.answer.replace(/\\n/g,'<br>')+meta);
  if(j.citations) appendCite('&#128196; '+j.citations);
}
async function callRagOnly(q){
  const r = await fetch(RAG_SERVER+'/chat',{
    method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({question:q})
  });
  const j = await r.json();
  document.getElementById('chatThinking')?.remove();
  if(j.error){ appendMsg('bot','&#10060; '+j.error); return; }
  appendMsg('bot', j.answer.replace(/\\n/g,'<br>'));
  if(j.citations) appendCite('&#128196; '+j.citations);
}
async function callDirectApi(q){
  const key   = localStorage.getItem('ai_apiKey')||'';
  const prov  = document.getElementById('aiProvider').value;
  const model = document.getElementById('aiModel').value;
  const temp  = parseFloat(document.getElementById('aiTemp').value);
  const maxTok= parseInt(document.getElementById('aiMaxTokens').value);
  const topP  = parseFloat(document.getElementById('aiTopP').value);
  if(!key){ appendMsg('bot','&#128274; No API key saved. Paste your key in the settings panel.'); document.getElementById('chatThinking')?.remove(); return; }
  if(prov==='gemini'){
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${key}`;
    const r = await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({contents:[{parts:[{text:q}]}],generationConfig:{temperature:temp,maxOutputTokens:maxTok,topP}})});
    const j = await r.json();
    document.getElementById('chatThinking')?.remove();
    const ans = j.candidates?.[0]?.content?.parts?.[0]?.text || j.error?.message || 'No response';
    appendMsg('bot', ans.replace(/\\n/g,'<br>'));
  } else {
    const r = await fetch('https://api.openai.com/v1/chat/completions',{method:'POST',
      headers:{'Content-Type':'application/json','Authorization':'Bearer '+key},
      body:JSON.stringify({model,temperature:temp,max_tokens:maxTok,top_p:topP,
        messages:[{role:'system',content:'You are InvestorGPT, an expert semiconductor investment analyst specializing in Intel (INTC) and Micron (MU).'},
                  {role:'user',content:q}]})});
    const j = await r.json();
    document.getElementById('chatThinking')?.remove();
    if(j.error){ appendMsg('bot','&#10060; '+j.error.message); return; }
    appendMsg('bot', (j.choices?.[0]?.message?.content||'').replace(/\\n/g,'<br>'));
  }
}
function debounceValidate(){
  clearTimeout(_validateTimer);
  _validateTimer = setTimeout(async ()=>{
    const key = document.getElementById('aiApiKey').value.trim();
    const el  = document.getElementById('keyStatus');
    if(!key){ el.innerHTML=''; return; }
    localStorage.setItem('ai_apiKey', key);
    el.innerHTML='<em class="text-muted">Validating...</em>';
    try{
      const r = await fetch('https://api.openai.com/v1/models',{headers:{'Authorization':'Bearer '+key},signal:AbortSignal.timeout(5000)});
      el.innerHTML = r.ok ? '&#9989; Valid key' : '&#10060; Invalid key';
      if(r.ok) saveAiSettings();
    } catch(e){ el.innerHTML='&#10060; Could not validate'; }
  }, 400);
}
function clearApiKey(){
  document.getElementById('aiApiKey').value='';
  document.getElementById('keyStatus').innerHTML='';
  localStorage.removeItem('ai_apiKey');
  setChatMode(serverOnline ? 'server' : 'rag');
}

// ── tab switching ─────────────────────────────────────────────
document.querySelectorAll('#mainTabs button').forEach(btn=>{
  btn.addEventListener('click',()=>{
    document.querySelectorAll('#mainTabs button').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    ['price','buffett','fund','forecast','chat'].forEach(t=>document.getElementById('tab-'+t).style.display='none');
    document.getElementById('tab-'+btn.dataset.tab).style.display='';
    const d=ALL[activeTicker];
    if(btn.dataset.tab==='price') renderPriceTab(d);
    else if(btn.dataset.tab==='buffett') renderBuffettTab(d);
    else if(btn.dataset.tab==='fund') renderFundTab(d);
    else if(btn.dataset.tab==='forecast') renderForecastTab(d);
    else if(btn.dataset.tab==='chat') initChat();
  });
});

// ── ticker switching ──────────────────────────────────────────
function switchTicker(t, el){
  document.querySelectorAll('.ticker-btn').forEach(b=>b.classList.remove('active'));
  el.classList.add('active');
  if(t==='CMP'){
    document.getElementById('tickerView').style.display='none';
    document.getElementById('cmpView').style.display='';
    document.getElementById('metricStrip').innerHTML='';
    renderCompare();
  } else {
    activeTicker=t;
    document.getElementById('tickerView').style.display='';
    document.getElementById('cmpView').style.display='none';
    const d=ALL[t];
    renderStrip(d);
    initRangeSlider();
    const activeTab=document.querySelector('#mainTabs button.active')?.dataset?.tab||'price';
    if(activeTab==='price') renderPriceTab(d);
    else if(activeTab==='buffett') renderBuffettTab(d);
    else if(activeTab==='fund') renderFundTab(d);
    else if(activeTab==='forecast') renderForecastTab(d);
  }
}

// ── dark mode ─────────────────────────────────────────────────
function toggleTheme(){
  const t = document.documentElement.getAttribute('data-theme')==='dark' ? '' : 'dark';
  document.documentElement.setAttribute('data-theme', t);
  localStorage.setItem('theme', t);
}
(function loadTheme(){
  const t = localStorage.getItem('theme');
  if(t) document.documentElement.setAttribute('data-theme', t);
})();

// ── initial render ────────────────────────────────────────────
(function init(){
  const d=ALL[activeTicker];
  renderStrip(d);
  renderPriceTab(d);
  initRangeSlider();
})();
</script>

<div class="footer">
  <strong>InvestorGPT</strong> &mdash; AI-Powered Semiconductor Investment Advisor<br>
  Built with OpenAI GPT-4o &middot; FAISS Vector Search &middot; ARIMA + Monte Carlo Forecasting<br>
  <span style="font-size:.7rem">Capstone Project &middot; Data as of <span id="footerTs"></span> &middot; Not financial advice</span>
</div>
<script>document.getElementById('footerTs').textContent=ALL.generated||'N/A';</script>
</body>
</html>
"""


def main() -> None:
    print("=" * 50)
    print("InvestorGPT Dashboard Generator")
    print("=" * 50)
    payload: dict = {"generated": datetime.now().strftime("%Y-%m-%d %H:%M")}
    for ticker in TICKERS:
        try:
            payload[ticker] = build_ticker_data(ticker)
            d = payload[ticker]
            print(f"\n  [{ticker}] ${d['current_price']} | Buffett={d['buffett_score']:.1f} "
                  f"Signal={d['signal_score']:.1f} | {d['action']}")
        except Exception as e:
            print(f"  [{ticker}] ERROR: {e}")
            payload[ticker] = {"ticker": ticker, "name": TICKER_NAMES[ticker],
                                "color": TICKER_COLORS[ticker], "error": str(e)}
    html = HTML_TEMPLATE.replace("__DATA_JSON__", json.dumps(payload))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"\nDashboard written to: {OUTPUT.resolve()}")
    print("Open webpage/index.html in your browser (or run open_dashboard.bat)")


if __name__ == "__main__":
    main()
