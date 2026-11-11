"""Bade stocks ka data -> stocks.json (Yahoo Finance, delayed). Sirf standard library.
Ye list time ke saath badalti hai. Kisi ka ticker band ho to script use chhod deti hai.
Aap apne hisaab se ticker, naam aur sector badal sakte ho."""
import json, time, urllib.request, urllib.parse
from datetime import datetime, timezone

STOCKS = [
    ("HDFCBANK", "HDFC Bank", "Banking"), ("ICICIBANK", "ICICI Bank", "Banking"), ("SBIN", "SBI", "Banking"),
    ("KOTAKBANK", "Kotak Mahindra Bank", "Banking"), ("AXISBANK", "Axis Bank", "Banking"),
    ("BAJFINANCE", "Bajaj Finance", "Banking"), ("BAJAJFINSV", "Bajaj Finserv", "Banking"),
    ("TCS", "TCS", "IT"), ("INFY", "Infosys", "IT"), ("HCLTECH", "HCL Tech", "IT"),
    ("WIPRO", "Wipro", "IT"), ("TECHM", "Tech Mahindra", "IT"),
    ("MARUTI", "Maruti Suzuki", "Auto"), ("M&M", "Mahindra & Mahindra", "Auto"), ("BAJAJ-AUTO", "Bajaj Auto", "Auto"),
    ("EICHERMOT", "Eicher Motors", "Auto"), ("HEROMOTOCO", "Hero MotoCorp", "Auto"),
    ("SUNPHARMA", "Sun Pharma", "Pharma"), ("CIPLA", "Cipla", "Pharma"), ("DRREDDY", "Dr Reddy's", "Pharma"),
    ("APOLLOHOSP", "Apollo Hospitals", "Pharma"),
    ("TATASTEEL", "Tata Steel", "Metals"), ("JSWSTEEL", "JSW Steel", "Metals"), ("HINDALCO", "Hindalco", "Metals"),
    ("RELIANCE", "Reliance", "Energy"), ("ONGC", "ONGC", "Energy"), ("NTPC", "NTPC", "Energy"),
    ("POWERGRID", "Power Grid", "Energy"), ("COALINDIA", "Coal India", "Energy"),
    ("HINDUNILVR", "Hindustan Unilever", "FMCG"), ("ITC", "ITC", "FMCG"), ("NESTLEIND", "Nestle India", "FMCG"),
    ("BRITANNIA", "Britannia", "FMCG"), ("TATACONSUM", "Tata Consumer", "FMCG"),
    ("LT", "Larsen & Toubro", "Infra & Others"), ("ULTRACEMCO", "UltraTech Cement", "Infra & Others"),
    ("ADANIPORTS", "Adani Ports", "Infra & Others"), ("TITAN", "Titan", "Infra & Others"),
    ("BHARTIARTL", "Bharti Airtel", "Infra & Others"), ("ASIANPAINT", "Asian Paints", "Infra & Others"),
]

def rsi(c, n=14):
    if len(c) < n + 1:
        return None
    g = l = 0.0
    for i in range(1, n + 1):
        d = c[i] - c[i - 1]
        g += max(d, 0); l += max(-d, 0)
    ag, al = g / n, l / n
    for i in range(n + 1, len(c)):
        d = c[i] - c[i - 1]
        ag = (ag * (n - 1) + max(d, 0)) / n
        al = (al * (n - 1) + max(-d, 0)) / n
    return 100.0 if al == 0 else round(100 - 100 / (1 + ag / al), 1)

def analyse(res):
    q = res["indicators"]["quote"][0]
    rows = [(c, v, h, lo) for c, v, h, lo in zip(q["close"], q["volume"], q["high"], q["low"]) if c is not None]
    if len(rows) < 30:
        return None
    closes = [r[0] for r in rows]
    vols = [r[1] or 0 for r in rows]
    last, prev = closes[-1], closes[-2]
    h52 = max(r[2] for r in rows if r[2] is not None)
    l52 = min(r[3] for r in rows if r[3] is not None)
    avg20 = sum(vols[-21:-1]) / 20
    sma20 = sum(closes[-20:]) / 20
    sma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None
    return {
        "p": round(last, 2), "c": round((last - prev) / prev * 100, 2),
        "vr": round(vols[-1] / avg20, 2) if avg20 else None,
        "tv": round(last * vols[-1] / 1e7, 1),
        "fh": round((last / h52 - 1) * 100, 1), "fl": round((last / l52 - 1) * 100, 1),
        "rsi": rsi(closes),
        "d20": 1 if last > sma20 else 0,
        "d50": (1 if last > sma50 else 0) if sma50 else None,
    }

def main():
    items = []
    for sym, name, sec in STOCKS:
        try:
            u = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(sym) + ".NS?interval=1d&range=1y"
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=25) as r:
                res = json.loads(r.read())["chart"]["result"][0]
            a = analyse(res)
            if a:
                a.update({"s": sym, "n": name, "sec": sec})
                items.append(a)
                print("OK", sym)
            else:
                print("SKIP", sym, "kam data")
        except Exception as e:
            print("SKIP", sym, e)
        time.sleep(0.4)
    if not items:
        print("Koi data nahi mila, purani stocks.json waisi hi rakhi.")
        return
    with open("stocks.json", "w", encoding="utf-8") as f:
        json.dump({"updated": datetime.now(timezone.utc).isoformat(), "items": items}, f, ensure_ascii=False)
    print("Total", len(items))

if __name__ == "__main__":
    main()
