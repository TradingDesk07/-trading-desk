"""update_data.py: builds data.json for tools.html from Yahoo Finance (yfinance). Data is DELAYED, not real-time.
Run locally: pip install yfinance pandas numpy && python update_data.py
If anything fails it exits WITHOUT touching the old data.json (page then shows "stale")."""
import json, sys, math, datetime as dt
import numpy as np, pandas as pd, yfinance as yf

SECTORS = {  # equal-weight baskets, edit freely (NSE symbols without .NS)
 "PVT BANK": ["HDFCBANK","ICICIBANK","AXISBANK","KOTAKBANK","INDUSINDBK","FEDERALBNK"],
 "PSU BANK": ["SBIN","BANKBARODA","PNB","CANBK","UNIONBANK"],
 "NBFC": ["BAJFINANCE","MANAPPURAM","MUTHOOTFIN","CHOLAFIN","SHRIRAMFIN"],
 "IT": ["TCS","INFY","HCLTECH","WIPRO","PERSISTENT","TECHM"],
 "AUTO": ["MARUTI","M&M","BAJAJ-AUTO","EICHERMOT","TVSMOTOR"],
 "METAL": ["TATASTEEL","JSWSTEEL","HINDALCO","VEDL","JINDALSTEL"],
 "PHARMA": ["SUNPHARMA","CIPLA","DRREDDY","LUPIN","DIVISLAB"],
 "FMCG": ["ITC","HINDUNILVR","NESTLEIND","TATACONSUM","GODREJCP"],
 "ENERGY": ["RELIANCE","ONGC","NTPC","HINDPETRO","BPCL"],
 "REALTY": ["DLF","GODREJPROP","OBEROIRLTY","LODHA","PRESTIGE"],
 "CEMENT": ["ULTRACEMCO","AMBUJACEM","SHREECEM","DALBHARAT","ACC"],
 "HEALTHCARE": ["APOLLOHOSP","MAXHEALTH","FORTIS","LALPATHLAB"],
 "DEFENCE": ["HAL","BEL","BDL","MAZDOCK","COCHINSHIP"]}
INDICES = {"NIFTY 50":"^NSEI","BANK NIFTY":"^NSEBANK","SENSEX":"^BSESN","NIFTY IT":"^CNXIT","NIFTY AUTO":"^CNXAUTO",
 "NIFTY PHARMA":"^CNXPHARMA","NIFTY FMCG":"^CNXFMCG","NIFTY METAL":"^CNXMETAL","NIFTY PSU BANK":"^CNXPSUBANK"}  # tickers that fail are skipped
PAIRS = [("HDFCBANK","ICICIBANK","Financial Services"),("AXISBANK","SBIN","Financial Services"),("MANAPPURAM","MUTHOOTFIN","Financial Services"),
 ("TCS","INFY","IT"),("SUNPHARMA","CIPLA","Pharma"),("TATASTEEL","JSWSTEEL","Metals"),("DLF","GODREJPROP","Realty"),("HAL","BEL","Defence")]

clamp = lambda x, a, b: max(a, min(b, x))
def r(x, n=2): return round(float(x), n) if x is not None and np.isfinite(x) else None
def strength(chg, h1, br, vol, nf):  # same formula as tools.html
    return clamp(5 + clamp(chg-nf, -3, 3)*.8 + clamp(h1, -.4, .4)/.4 + (br-50)/50*1.5 + clamp(vol-1, -1, 1), 0, 10)
def rsi(c, n=14):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100/(1 + up.iloc[-1]/dn.iloc[-1]) if dn.iloc[-1] else None
def snap(c, pc, k):  # day% and 1h% as they were k bars (5 min each) ago
    j = len(c)-1-k
    return (0.0, 0.0) if j < 0 else ((c[j]/pc-1)*100, (c[j]/c[max(j-12, 0)]-1)*100)
def frame(df, tk, intraday=False):
    try: x = df[tk].dropna(how="all")
    except Exception: return None
    if not len(x): return None
    if intraday:
        x = x.copy(); x.index = (x.index.tz_localize("UTC") if x.index.tz is None else x.index).tz_convert("Asia/Kolkata")
    return x

def main():
    syms = sorted({s for v in SECTORS.values() for s in v} | {s for p in PAIRS for s in p[:2]})
    tks = [s+".NS" for s in syms] + list(INDICES.values())
    kw = dict(group_by="ticker", auto_adjust=True, progress=False, threads=True)
    daily = yf.download(tks, period="1y", interval="1d", **kw); intra = yf.download(tks, period="5d", interval="5m", **kw)
    if daily is None or intra is None or daily.empty or intra.empty: sys.exit("no data from Yahoo, keeping old data.json")
    nx = frame(intra, "^NSEI", True)
    if nx is None: sys.exit("no Nifty intraday")
    day = nx.index[-1].date()

    def calc(tk):
        i, d = frame(intra, tk, True), frame(daily, tk)
        if i is None or d is None: return None
        t = i[i.index.date == day].dropna(subset=["Close"]); prior = d[d.index.date < day].dropna(subset=["Close"])
        if len(t) < 2 or len(prior) < 50: return None
        pc = float(prior["Close"].iloc[-1]); c = t["Close"].values; ltp = float(c[-1]); v = t["Volume"].values
        tp = (t["High"]+t["Low"]+t["Close"])/3; vw = float((tp*t["Volume"]).sum()/v.sum()) if v.sum() > 0 else ltp
        oh, ol = float(t["High"].iloc[:3].max()), float(t["Low"].iloc[:3].min())  # opening range = first 15 min
        av = float(prior["Volume"].iloc[-20:].mean()); vr = min(5, v.sum()/(av*min(len(t), 75)/75)) if av > 0 else 1.0
        post = t.iloc[3:]; hit = post[post["Close"] > oh] if ltp > oh else post[post["Close"] < ol] if ltp < ol else post.iloc[0:0]
        cl = prior["Close"]
        return dict(chg=(ltp/pc-1)*100, h1=(ltp/c[max(len(c)-13, 0)]-1)*100, ltp=ltp, oh=oh, ol=ol, vw=vw, vol=vr, gap=(float(t["Open"].iloc[0])/pc-1)*100,
            t=(hit.index[0] if len(hit) else t.index[-1]).strftime("%H:%M"), rsi=rsi(cl), d20=cl.iloc[-20:].mean(), d50=cl.iloc[-50:].mean(),
            h52=prior["High"].iloc[-252:].max(), l52=prior["Low"].iloc[-252:].min(), _c=c, _pc=pc)

    R = {s: calc(s+".NS") for s in syms}; R = {k: v for k, v in R.items() if v}
    nf = calc("^NSEI"); nchg, nprev = nf["chg"], snap(nf["_c"], nf["_pc"], 12)[0]
    sectors, stocks, wt, seen = [], [], {}, set()
    for name, L in SECTORS.items():
        rows = [(s, R[s]) for s in L if s in R]
        if not rows: continue
        n = len(rows); pv = [snap(x["_c"], x["_pc"], 12) for _, x in rows]
        chg, h1 = np.mean([x["chg"] for _, x in rows]), np.mean([x["h1"] for _, x in rows])
        br, vol = 100*sum(x["chg"] > 0 for _, x in rows)/n, np.mean([x["vol"] for _, x in rows])
        prev = strength(np.mean([a for a, _ in pv]), np.mean([b for _, b in pv]), 100*sum(a > 0 for a, _ in pv)/n, vol, nprev)  # strength 1 hour ago
        sectors.append([name, "Stock basket", r(chg), r(h1), r(br, 0), r(vol), r(prev, 1)])
        wt[name] = [[s, round(100/n, 1), r(x["chg"])] for s, x in rows]  # equal weights, replace with real index weights if you have them
        for s, x in rows:
            if s in seen: continue
            seen.add(s); stocks.append({"s": s, "sec": name, "t": x["t"], **{k: r(x[k]) for k in ("chg","ltp","oh","ol","vw","vol","gap","rsi","d20","d50","h52","l52")}})
    indices = []
    for name, tk in INDICES.items():
        x = calc(tk)
        if x: indices.append([name, r(x["ltp"], 0), r(x["chg"]), r(x["h1"]), int(x["ltp"] > x["d20"]), int(x["ltp"] > x["d50"])])
    ps = sorted({s for p in PAIRS for s in p[:2]})
    cl = pd.concat({s: frame(daily, s+".NS")["Close"] for s in ps if frame(daily, s+".NS") is not None}, axis=1).dropna().tail(250)
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30)))
    out = {"meta": {"updated": dt.datetime.now(dt.timezone.utc).isoformat(), "ist": now.strftime("%d %b %H:%M"), "source": "Yahoo Finance"},
           "nifty": {"chg": r(nchg)}, "sectors": sectors, "stocks": stocks, "indices": indices, "wt": wt,
           "pairs": [list(p) for p in PAIRS if p[0] in cl and p[1] in cl], "prices": {s: [round(float(v), 2) for v in cl[s]] for s in cl.columns}}
    json.dump(out, open("data.json", "w"), separators=(",", ":"), allow_nan=False)
    print("ok", len(stocks), "stocks", len(sectors), "sectors", len(out["pairs"]), "pairs")

if __name__ == "__main__": main()
