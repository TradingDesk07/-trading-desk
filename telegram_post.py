"""news.json se top headlines Telegram channel par bhejta hai.
GitHub repo ke Settings > Secrets and variables > Actions mein 2 secrets banao:
  TELEGRAM_BOT_TOKEN  (BotFather se mila token)
  TELEGRAM_CHAT_ID    (channel ka @username, jaise @tradingdeskwithsuraj, ya numeric id)
Bot ko channel ka admin banana zaroori hai."""
import json, os, urllib.parse, urllib.request

SITE_URL = os.environ.get("SITE_URL", "https://tradingdesk07.github.io/-trading-desk/")

def build(data):
    pick = ["Nifty 50", "Sensex", "Bank Nifty", "India VIX", "Bitcoin", "Gold /oz"]
    lines = ["Trading Desk | Market Wrap", ""]
    for q in data.get("quotes") or []:
        if q["n"] in pick:
            lines.append("%s: %s%s (%+.2f%%)" % (q["n"], q.get("cur", ""), format(q["p"], ",.2f"), q["c"]))
    items = [i for i in data.get("items", []) if i["c"] != "hindi"][:6]
    if items:
        lines += ["", "Top khabrein:"]
        for i, x in enumerate(items, 1):
            lines.append("%d. %s\n%s" % (i, x["t"], x["u"]))
    lines += ["", "Zyada: " + SITE_URL, "Sirf news hai, investment salah nahi."]
    return "\n".join(lines)[:4000]

def main():
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("Telegram secrets set nahi hain, kuch nahi bheja.")
        return
    with open("news.json", encoding="utf-8") as f:
        text = build(json.load(f))
    body = urllib.parse.urlencode({"chat_id": chat, "text": text, "disable_web_page_preview": "true"}).encode()
    with urllib.request.urlopen("https://api.telegram.org/bot%s/sendMessage" % token, data=body, timeout=30) as r:
        print("Telegram:", r.status)

if __name__ == "__main__":
    main()
