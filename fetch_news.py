"""Market news fetcher: RSS -> news.json. Sirf standard library, kuch install nahi karna."""
import json, re, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

def gn(q):
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": q + " when:2d", "hl": "en-IN", "gl": "IN", "ceid": "IN:en"})

FEEDS = [
    ("stocks", "Economic Times", "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms"),
    ("stocks", "Moneycontrol", "https://www.moneycontrol.com/rss/marketreports.xml"),
    ("stocks", "Mint", "https://www.livemint.com/rss/markets"),
    ("stocks", "Business Standard", "https://www.business-standard.com/rss/markets-106.rss"),
    ("stocks", "", gn("NSE BSE company board meeting dividend announcement")),
    ("results", "Moneycontrol", "https://www.moneycontrol.com/rss/results.xml"),
    ("results", "", gn("quarterly results net profit NSE company")),
    ("crypto", "Cointelegraph", "https://cointelegraph.com/rss"),
    ("crypto", "CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("commodities", "", gn("gold price India")),
    ("commodities", "", gn("silver price India MCX")),
]

# Tips/recommendation wali headlines hata do: ye tool sirf news hai.
BLOCK = re.compile(r"stocks? to buy|buy or sell|to buy|target price|top picks?|should you buy|"
                   r"multibagger|stock tips?|buy rating|sell rating|price target|"
                   r"intraday pick|trading call", re.I)

TAGS = [
    ("Results", r"results?|net profit|earnings|\bq[1-4]\b|revenue|quarter"),
    ("Dividend / Bonus / Split", r"dividend|bonus|stock split|record date"),
    ("Board & Deals", r"board|acqui|merger|buyback|stake|order win|contract|\bipo\b|fund.?rais|\bqip\b|rights issue"),
]


QUOTES = [("Nifty 50", "^NSEI", ""), ("Sensex", "^BSESN", ""), ("Bank Nifty", "^NSEBANK", ""),
          ("Bitcoin", "BTC-USD", "$"), ("Gold", "GC=F", "$"), ("Silver", "SI=F", "$"), ("USD/INR", "USDINR=X", "")]

def get_quotes():
    out = []
    for name, sym, cur in QUOTES:
        try:
            u = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(sym) + "?interval=1d&range=5d"
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                res = json.loads(r.read())["chart"]["result"][0]
            m = res["meta"]
            p = float(m["regularMarketPrice"])
            closes = [c for c in res["indicators"]["quote"][0]["close"] if c is not None]
            # pichhle session ka close (5 din purana nahi): last bar aaj/latest session ka hota hai
            prev = float(closes[-2]) if len(closes) >= 2 else float(m.get("previousClose") or p)
            out.append({"n": name, "p": round(p, 2), "c": round((p - prev) / prev * 100, 2), "cur": cur})
            print("QUOTE OK", name)
        except Exception as e:
            print("QUOTE SKIP", name, e)
    return out

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 NewsRadar"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return ET.fromstring(r.read())

def main():
    items, seen = [], set()
    for cat, src, url in FEEDS:
        try:
            root = fetch(url)
        except Exception as e:
            print("SKIP", url[:70], e)
            continue
        n = 0
        for it in root.iter("item"):
            title = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            if not title or not link:
                continue
            s = src
            gs = it.find("source")
            if gs is not None and gs.text:
                s = gs.text.strip()
                title = re.sub(r"\s+-\s+" + re.escape(s) + r"$", "", title)
            key = re.sub(r"\W+", "", title.lower())[:80]
            if key in seen or BLOCK.search(title):
                continue
            try:
                dt = parsedate_to_datetime(it.findtext("pubDate")).astimezone(timezone.utc)
            except Exception:
                dt = datetime.now(timezone.utc)
            tag = ""
            if cat in ("stocks", "results"):
                for name, pat in TAGS:
                    if re.search(pat, title, re.I):
                        tag = name
                        break
            seen.add(key)
            items.append({"c": cat, "t": title, "u": link, "s": s or "News",
                          "d": dt.isoformat(), "g": tag})
            n += 1
        print("OK", cat, s or "Google News", n)
    items.sort(key=lambda x: x["d"], reverse=True)
    out = {"updated": datetime.now(timezone.utc).isoformat(), "items": items[:400], "quotes": get_quotes()}
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    with open("news.js", "w", encoding="utf-8") as f:
        f.write("window.NEWS=" + json.dumps(out, ensure_ascii=False) + ";")
    print("Total", len(out["items"]))

main()
