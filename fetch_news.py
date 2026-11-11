"""Market news fetcher: RSS -> news.json. Sirf standard library, kuch install nahi karna."""
import json, re, urllib.request, urllib.parse
from email.utils import format_datetime
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

SITE_URL = "https://tradingdesk07.github.io/-trading-desk/"
YT_CHANNEL_ID = "UCfg8cHXHAs-VXuVpv3fE-PQ"   # apne YouTube channel ki ID yahan daalo (UC se shuru hoti hai). Khali = videos section band.

def gn(q, hi=False):
    p = {"q": q + " when:2d", "hl": "hi" if hi else "en-IN", "gl": "IN", "ceid": "IN:hi" if hi else "IN:en"}
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(p)

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
    ("ipo", "", gn("IPO subscription listing NSE BSE")),
    ("ipo", "", gn("IPO allotment date India")),
    ("global", "", gn("Wall Street Dow Nasdaq S&P 500 stocks")),
    ("global", "", gn("Asian markets Nikkei Hang Seng Europe stocks")),
    ("economy", "", gn("RBI repo rate inflation India economy")),
    ("economy", "", gn("India GDP budget economy news")),
    ("hindi", "", gn("शेयर बाजार सेंसेक्स निफ्टी", True)),
    ("hindi", "", gn("कंपनी नतीजे शेयर", True)),
    ("hindi", "", gn("सोना चांदी भाव", True)),
    ("commodities", "", gn("gold price India")),
    ("commodities", "", gn("silver price India MCX")),
]

# Tips/recommendation wali headlines hata do: ye tool sirf news hai.
BLOCK = re.compile(r"stocks? to buy|buy or sell|to buy|target price|top picks?|should you buy|"
                   r"multibagger|stock tips?|buy rating|sell rating|price target|"
                   r"intraday pick|trading call|खरीदें|टारगेट|टिप्स|मल्टीबैगर", re.I)

TAGS = [
    ("Results", r"results?|net profit|earnings|\bq[1-4]\b|revenue|quarter"),
    ("Dividend / Bonus / Split", r"dividend|bonus|stock split|record date"),
    ("Board & Deals", r"board|acqui|merger|buyback|stake|order win|contract|\bipo\b|fund.?rais|\bqip\b|rights issue"),
]


QUOTES = [("Nifty 50", "^NSEI", ""), ("Sensex", "^BSESN", ""), ("Bank Nifty", "^NSEBANK", ""), ("India VIX", "^INDIAVIX", ""),
          ("Dow Jones", "^DJI", ""), ("Nasdaq", "^IXIC", ""), ("Nikkei 225", "^N225", ""), ("S&P 500", "^GSPC", ""), ("DAX", "^GDAXI", ""), ("FTSE 100", "^FTSE", ""), ("Hang Seng", "^HSI", ""),
          
          ("Bitcoin", "BTC-USD", "$"), ("Gold /oz", "GC=F", "$"), ("Silver /oz", "SI=F", "$"), ("Crude Oil", "CL=F", "$"), ("USD/INR", "USDINR=X", "")]

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

SECTORS = [
    ("Banking", r"bank|hdfc|icici|\bsbi\b|axis|kotak|nbfc|financ"),
    ("IT", r"infosys|\btcs\b|wipro|\bhcl|tech mahindra|\bIT (stocks?|sector|services|firm)|software"),
    ("Auto", r"\bauto|maruti|tata motors|bajaj auto|hero moto|eicher|\bev\b|mahindra"),
    ("Pharma", r"pharma|drug|cipla|dr reddy|hospital"),
    ("Metals", r"metal|steel|jsw|hindalco|vedanta|aluminium|copper"),
    ("Energy", r"\boil\b|\bgas\b|reliance|ongc|ntpc|power|coal|energy"),
]

def get_mood():
    try:
        req = urllib.request.Request("https://api.alternative.me/fng/?limit=1", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read())["data"][0]
        print("MOOD OK", d["value"])
        return {"v": int(d["value"]), "l": d["value_classification"]}
    except Exception as e:
        print("MOOD SKIP", e)
        return None

def get_videos():
    if not YT_CHANNEL_ID:
        return []
    try:
        root = fetch("https://www.youtube.com/feeds/videos.xml?channel_id=" + YT_CHANNEL_ID)
        ns = {"a": "http://www.w3.org/2005/Atom", "m": "http://search.yahoo.com/mrss/"}
        out = []
        for e in root.findall("a:entry", ns)[:6]:
            th = e.find(".//m:thumbnail", ns)
            out.append({"t": e.findtext("a:title", "", ns), "u": e.find("a:link", ns).get("href"),
                        "d": e.findtext("a:published", "", ns), "th": th.get("url") if th is not None else ""})
        print("VIDEOS OK", len(out))
        return out
    except Exception as e:
        print("VIDEOS SKIP", e)
        return []

def write_feed(items):
    rows = ""
    for x in [i for i in items if i["c"] != "hindi"][:20]:
        try:
            pub = format_datetime(datetime.fromisoformat(x["d"]))
        except Exception:
            pub = ""
        rows += ("<item><title>%s</title><link>%s</link><guid isPermaLink=\"false\">%s</guid><pubDate>%s</pubDate></item>"
                 % (escape(x["t"]), escape(x["u"]), escape(x["u"]), pub))
    xml = ('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Trading Desk</title><link>%s</link>'
           '<description>Market news headlines</description>%s</channel></rss>' % (escape(SITE_URL), rows))
    with open("feed.xml", "w", encoding="utf-8") as fh:
        fh.write(xml)

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
            sc = ""
            if cat in ("stocks", "results"):
                for name, pat in SECTORS:
                    if re.search(pat, title, re.I):
                        sc = name
                        break
            seen.add(key)
            items.append({"c": cat, "t": title, "u": link, "s": s or "News",
                          "d": dt.isoformat(), "g": tag, "sc": sc})
            n += 1
        print("OK", cat, s or "Google News", n)
    items.sort(key=lambda x: x["d"], reverse=True)
    out = {"updated": datetime.now(timezone.utc).isoformat(), "items": items[:400], "quotes": get_quotes(), "mood": get_mood(), "videos": get_videos()}
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    with open("news.js", "w", encoding="utf-8") as f:
        f.write("window.NEWS=" + json.dumps(out, ensure_ascii=False) + ";")
    write_feed(out["items"])
    print("Total", len(out["items"]))

main()
