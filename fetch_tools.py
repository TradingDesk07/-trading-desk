"""Sectors, Pair Trading aur Logic Scanner ka data -> tools.json (Yahoo Finance, delayed). Sirf standard library.
fetch_stocks.py ki tarah chalta hai. Kisi ka ticker band ho to use chhod deta hai. Purana tools.json tab tak rehta hai jab tak naya sahi na bane."""
import json, time, urllib.request, urllib.parse
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from fetch_stocks import rsi

SECTORS = {  # equal-weight baskets, apne hisaab se badlo (NSE symbols, bina .NS)
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
PAIRS = [("HDFCBANK","ICICIBANK","Financial Services"),("AXISBANK","SBIN","Financial Services"),("MANAPPURAM","MUTHOOTFIN","Financial Services"),
 ("TCS","INFY","IT"),("SUNPHARMA","CIPLA","Pharma"),("TATASTEEL","JSWSTEEL","Metals"),("DLF","GODREJPROP","Realty"),("HAL","BEL","Defence")]
DAY = {}  # symbol -> {local day: close}, pairs ke liye

def get(tk, interval, rng):
    u = "https://query1.finance.yahoo.com/v8/finance/chart/%s?interval=%s&range=%s" % (urllib.parse.quote(tk), interval, rng)
    for _ in range(2):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=25) as r:
                return json.loads(r.read())["chart"]["result"][0]
        except Exception:
            time.sleep(1)

def calc(tk):
    try:
        i, d = get(tk, "5m", "5d"), get(tk, "1d", "1y")
        if not i or not d: return None
        off = i["meta"].get("gmtoffset", 19800); q = i["indicators"]["quote"][0]
        bars = [b for b in zip(i["timestamp"], q["open"], q["high"], q["low"], q["close"], q["volume"]) if b[4] is not None]
        day = (bars[-1][0] + off) // 86400
        t = [b for b in bars if (b[0] + off) // 86400 == day]
        dq = d["indicators"]["quote"][0]
        rows = [(ts, c, v or 0, h, l) for ts, c, v, h, l in zip(d["timestamp"], dq["close"], dq["volume"], dq["high"], dq["low"]) if c is not None and (ts + off) // 86400 < day]
        if len(t) < 2 or len(rows) < 50: return None
        DAY[tk] = {(r[0] + off) // 86400: r[1] for r in rows}
        pc = rows[-1][1]; cl = [r[1] for r in rows]; c = [b[4] for b in t]; ltp = c[-1]
        vs = sum(b[5] or 0 for b in t); vw = sum((b[2] + b[3] + b[4]) / 3 * (b[5] or 0) for b in t) / vs if vs else ltp
        oh, ol = max(b[2] for b in t[:3]), min(b[3] for b in t[:3])   # opening range = pehle 15 min
        av = sum(r[2] for r in rows[-20:]) / 20; vr = min(5, vs / (av * min(len(t), 75) / 75)) if av else 1.0
        hit = [b for b in t[3:] if (b[4] > oh if ltp > oh else b[4] < ol)] if (ltp > oh or ltp < ol) else []
        tm = datetime.fromtimestamp((hit[0] if hit else t[-1])[0] + off, timezone.utc).strftime("%H:%M")
        def snap(k):  # k bars (5 min) pehle ka day% aur 1h%
            j = len(c) - 1 - k
            return (0.0, 0.0) if j < 0 else ((c[j] / pc - 1) * 100, (c[j] / c[max(j - 12, 0)] - 1) * 100)
        pcg, ph = snap(12); r2 = lambda x: None if x is None else round(x, 2)
        return {"ltp": r2(ltp), "chg": r2((ltp / pc - 1) * 100), "h1": r2((ltp / c[max(len(c) - 13, 0)] - 1) * 100), "oh": r2(oh), "ol": r2(ol), "vw": r2(vw),
                "vol": r2(vr), "gap": r2((t[0][1] / pc - 1) * 100), "t": tm, "pcg": r2(pcg), "ph": r2(ph), "rsi": rsi(cl), "m20": r2(sum(cl[-20:]) / 20),
                "m50": r2(sum(cl[-50:]) / 50), "h52": r2(max(r[3] for r in rows[-252:] if r[3])), "l52": r2(min(r[4] for r in rows[-252:] if r[4]))}
    except Exception as e:
        print("SKIP", tk, e)

def main():
    syms = sorted({s for v in SECTORS.values() for s in v} | {s for p in PAIRS for s in p[:2]})
    with ThreadPoolExecutor(6) as ex:
        res = dict(zip(syms + ["^NSEI"], ex.map(calc, [s + ".NS" for s in syms] + ["^NSEI"])))
    nf = res.pop("^NSEI"); R = {k: v for k, v in res.items() if v}
    if not nf or len(R) < 10:
        print("Data kam mila, purani tools.json waisi hi rakhi."); return
    stocks, seen = [], set()
    for sec, L in SECTORS.items():
        for s in L:
            if s in R and s not in seen: seen.add(s); stocks.append({"s": s, "sec": sec, **R[s]})
    pairs = []
    for a, b, sec in PAIRS:
        A, B = DAY.get(a + ".NS"), DAY.get(b + ".NS")
        if not A or not B: continue
        days = sorted(set(A) & set(B))[-250:]
        if len(days) >= 100: pairs.append([a, b, sec, [round(A[x], 2) for x in days], [round(B[x], 2) for x in days]])
    tr = "UP" if nf["ltp"] > nf["m20"] > nf["m50"] else "DOWN" if nf["ltp"] < nf["m20"] < nf["m50"] else "SIDEWAYS"
    now = datetime.now(timezone.utc)
    out = {"meta": {"updated": now.isoformat(), "ist": now.astimezone(timezone(__import__("datetime").timedelta(hours=5, minutes=30))).strftime("%d %b %H:%M"), "source": "Yahoo Finance"},
           "nifty": {"chg": nf["chg"], "pcg": nf["pcg"], "tr": tr}, "stocks": stocks, "pairs": pairs}
    with open("tools.json", "w", encoding="utf-8") as f: json.dump(out, f, separators=(",", ":"), allow_nan=False)
    print("OK", len(stocks), "stocks", len(pairs), "pairs")

if __name__ == "__main__": main()
