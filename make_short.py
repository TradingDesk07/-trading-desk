"""Roz ka Market Wrap Short (vertical video + awaaz) banata hai, news.json se.
Zaroori: ffmpeg, pillow, edge-tts  (GitHub Actions mein daily-short.yml ye sab laga deta hai)
Awaaz badalne ke liye environment variable VOICE set karo, jaise en-IN-NeerjaNeural, en-IN-PrabhatNeural,
hi-IN-SwaraNeural. Awaaz na bane to REQUIRE_VOICE=1 se script fail hogi, warna silent video banegi."""
import asyncio, json, os, shutil, subprocess, textwrap, sys
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
VOICE = os.environ.get("VOICE", "en-IN-NeerjaNeural")
NAME = os.environ.get("BRAND", "Trading Desk")
SITE = os.environ.get("SITE_URL", "https://tradingdesk07.github.io/-trading-desk/")
FFMPEG = shutil.which("ffmpeg")
if not FFMPEG:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def font(sz, bold=True):
    try:
        return ImageFont.truetype(FB if bold else FR, sz)
    except Exception:
        return ImageFont.load_default()

def bg():
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        d.line((0, y, W, y), fill=(int(10 + 5 * t), int(15 + 44 * t), int(30 + 20 * t)))
    return im

def wrap(d, text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        s = (cur + " " + w).strip()
        if d.textlength(s, font=f) > maxw and cur:
            lines.append(cur); cur = w
        else:
            cur = s
    return lines + ([cur] if cur else [])

def frame(kind, lines, accent="#3ddc9f"):
    im = bg(); d = ImageDraw.Draw(im)
    d.text((70, 90), NAME, font=font(48), fill="#3ddc9f")
    d.text((70, 160), datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y"), font=font(34, False), fill="#9fb0c8")
    if kind == "quotes":
        d.text((70, 330), "MARKETS (delayed)", font=font(52), fill="#e9eef8")
        y = 440
        for n, val, ch in lines:
            up = ch >= 0
            d.rounded_rectangle((70, y, 1010, y + 170), radius=30, fill="#111a2e", outline="#1e2a45", width=3)
            d.text((110, y + 22), n, font=font(44), fill="#9fb0c8")
            d.text((110, y + 90), val, font=font(54), fill="#e9eef8")
            t = ("\u25B2 +" if up else "\u25BC ") + "%.2f%%" % ch
            d.text((1010 - 40 - d.textlength(t, font=font(54)), y + 90), t, font=font(54), fill="#5fe0a0" if up else "#ff8a80")
            y += 195
    elif kind == "headline":
        label, text, src = lines
        d.text((70, 420), label, font=font(46), fill=accent)
        f = font(64); y = 520
        for ln in wrap(d, text, f, 940)[:9]:
            d.text((70, y), ln, font=f, fill="#e9eef8"); y += 86
        d.text((70, y + 40), "Source: " + src, font=font(38, False), fill="#9fb0c8")
    else:
        y = 520
        for t, sz, col in lines:
            f = font(sz, sz > 44)
            for ln in wrap(d, t, f, 940):
                d.text((70, y), ln, font=f, fill=col); y += sz + 22
            y += 30
    d.text((70, H - 150), "Sirf jaankari hai, investment salah nahi.", font=font(34, False), fill="#9fb0c8")
    return im

async def tts(text, path):
    import edge_tts
    await asyncio.wait_for(edge_tts.Communicate(text, VOICE).save(path), timeout=60)

def make_audio(text, path):
    try:
        asyncio.run(tts(text, path))
        return True
    except Exception as e:
        if os.environ.get("REQUIRE_VOICE") == "1":
            raise
        print("VOICE SKIP:", e)
        secs = max(3.0, len(text.split()) / 2.6)
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                        "-t", "%.2f" % secs, "-c:a", "libmp3lame", path], check=True)
        return False

def scene_video(img, audio, out):
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", img, "-i", audio,
                    "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-r", "30",
                    "-c:a", "aac", "-ar", "44100", "-ac", "2", "-af", "apad=pad_dur=0.6", "-shortest", out], check=True)

def spoken(q):
    return "%s %s, %s %.2f percent." % (q["n"].replace("/oz", ""), format(q["p"], ",.0f") if q["p"] > 1000 else "%.2f" % q["p"],
                                          "up" if q["c"] >= 0 else "down", abs(q["c"]))

def main():
    data = json.load(open("news.json", encoding="utf-8"))
    pick = ["Nifty 50", "Sensex", "Bank Nifty", "India VIX", "Bitcoin", "Gold /oz"]
    qs = [q for q in (data.get("quotes") or []) if q["n"] in pick]
    items = [i for i in data.get("items", []) if i["c"] != "hindi"][:3]
    scenes = [("title", [(NAME, 96, "#e9eef8"), ("Aaj ka Market Wrap", 60, "#3ddc9f")],
               "Hello! Here is today's market wrap from %s." % NAME)]
    if qs:
        rows = [(q["n"], "%s%s" % (q.get("cur", ""), format(q["p"], ",.2f")), q["c"]) for q in qs]
        scenes.append(("quotes", rows, "Market snapshot. " + " ".join(spoken(q) for q in qs)))
    for i, it in enumerate(items, 1):
        scenes.append(("headline", ("TOP KHABAR %d" % i, it["t"], it["s"]), "News %d. %s" % (i, it["t"])))
    scenes.append(("outro", [("Poori khabrein, scanner aur calculators", 58, "#e9eef8"), (NAME + " par. Link description mein.", 50, "#3ddc9f"),
                             ("Ye sirf jaankari hai, investment salah nahi.", 44, "#9fb0c8")],
                   "Full news, scanner and calculators are on %s. Link in the description. This is information only, not investment advice." % NAME))
    os.makedirs("out", exist_ok=True); os.makedirs("tmp", exist_ok=True)
    listf = open("tmp/list.txt", "w"); voice_ok = True
    for n, (kind, content, narration) in enumerate(scenes):
        img, aud, vid = "tmp/s%d.png" % n, "tmp/s%d.mp3" % n, "tmp/s%d.mp4" % n
        frame(kind, content).save(img)
        voice_ok = make_audio(narration, aud) and voice_ok
        scene_video(img, aud, vid)
        listf.write("file 's%d.mp4'\n" % n)
    listf.close()
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "tmp/list.txt", "-c", "copy",
                    "-movflags", "+faststart", "out/market-wrap-short.mp4"], check=True)
    cap = "Aaj ka Market Wrap | %s\nPoori news aur free tools: %s\nSirf jaankari, investment salah nahi.\n#StockMarketIndia #Nifty #Sensex #MarketNews" % (NAME, SITE)
    open("out/short_caption.txt", "w", encoding="utf-8").write(cap)
    print("Video ban gaya. Awaaz:", "haan" if voice_ok else "nahi (silent)")

if __name__ == "__main__":
    main()
