"""Roz ka 'Aaj ka concept' Short: Education ke topics mein se ek topic (din ke hisaab se) chun kar
graphics + awaaz ke saath vertical video banata hai. topics.json aur make_short.py isi folder mein chahiye.
Topic badalna ho: environment variable TOPIC=0..37. Awaaz ke liye make_short.py wali VOICE/REQUIRE_VOICE settings chalti hain."""
import json, os, subprocess
from datetime import date
from PIL import Image, ImageDraw
import make_short as ms
from make_short import W, H, font, wrap, make_audio, scene_video, NAME, SITE

UP, DN, MUTE, INK, ACC = "#5fe0a0", "#ff8a80", "#9fb0c8", "#e9eef8", "#3ddc9f"

def base(label, title):
    im = ms.bg(); d = ImageDraw.Draw(im)
    d.text((70, 90), NAME, font=font(48), fill=ACC)
    d.text((70, 160), label, font=font(34, False), fill=MUTE)
    if title:
        f = font(76)
        for i, ln in enumerate(wrap(d, title, f, 940)[:2]):
            d.text((70, 250 + i * 92), ln, font=f, fill=INK)
    d.text((70, H - 150), "Sirf shiksha ke liye, investment salah nahi.", font=font(34, False), fill=MUTE)
    return im, d

def fade(c, k=0.4):  # context candles ko dhundhla karo
    base_c = (10, 20, 40)
    return tuple(int(base_c[i] + (c[i] - base_c[i]) * k) for i in range(3))

def draw_candles(d, candles, k, box):
    x0, y0, x1, y1 = box
    n = len(candles); step = (x1 - x0) / n; bw = min(90, step * 0.5)
    vals = [v for c in candles for v in c]; lo, hi = min(vals) - 4, max(vals) + 4
    Y = lambda v: y1 - (v - lo) / (hi - lo) * (y1 - y0)
    for i, (o, h, l, c) in enumerate(candles):
        col = (95, 224, 160) if c >= o else (255, 138, 128)
        if i < n - k: col = fade(col)
        cx = x0 + step * (i + 0.5)
        d.line((cx, Y(h), cx, Y(l)), fill=col, width=8)
        d.rounded_rectangle((cx - bw / 2, Y(max(o, c)), cx + bw / 2, max(Y(min(o, c)), Y(max(o, c)) + 6)), radius=8, fill=col)

def draw_chart(d, pts, lines, bullish, box):
    x0, y0, x1, y1 = box
    P = lambda x, y: (x0 + x / 200 * (x1 - x0), y0 + y / 100 * (y1 - y0))
    for l in lines:
        a, b = P(l[0], l[1]), P(l[2], l[3])
        for t in range(0, 20, 2):  # dashed line
            s0 = (a[0] + (b[0] - a[0]) * t / 20, a[1] + (b[1] - a[1]) * t / 20)
            s1 = (a[0] + (b[0] - a[0]) * (t + 1) / 20, a[1] + (b[1] - a[1]) * (t + 1) / 20)
            d.line((s0, s1), fill=MUTE, width=4)
    seq = [P(*map(float, q.split(","))) for q in pts.split()]
    d.line(seq, fill=UP if bullish else DN, width=14, joint="curve")
    for q in (seq[0], seq[-1]):
        d.ellipse((q[0] - 9, q[1] - 9, q[0] + 9, q[1] + 9), fill=UP if bullish else DN)

def text_scene(label, title, head, body):
    im, d = base(label, title)
    d.text((70, 560), head.upper(), font=font(46), fill=ACC)
    y = 650; f = font(58, False)
    for ln in wrap(d, body, f, 940)[:12]:
        d.text((70, y), ln, font=f, fill=INK); y += 82
    return im

def main():
    topics = json.load(open("topics.json", encoding="utf-8"))
    i = int(os.environ["TOPIC"]) if os.environ.get("TOPIC") else date.today().toordinal() % len(topics)
    t = topics[i]; label = "Aaj ka concept | " + t["label"]
    scenes = []
    im, d = base(label, t["name"])
    d.text((70, 560), "Roz ek naya concept.", font=font(52, False), fill=MUTE)
    scenes.append((im, "Today's concept: %s." % t["name"]))
    if t["type"] in ("candle", "chart"):
        im, d = base(label, t["name"])
        box = (90, 520, 990, 1250)
        if t["type"] == "candle":
            draw_candles(d, t["candles"], t["k"], box)
            d.text((70, 1300), "Dhundhli candles pehle ka trend, gehri candles pattern", font=font(34, False), fill=MUTE)
        else:
            draw_chart(d, t["pts"], t["lines"], t["badge"] == "u", box)
        tag = {"u": "Bullish", "d": "Bearish", "n": "Neutral"}[t["badge"]]
        d.text((70, 1380), tag, font=font(60), fill={"u": UP, "d": DN, "n": MUTE}[t["badge"]])
        scenes.append((im, t["s1"]))
        scenes.append((text_scene(label, t["name"], t["h2"], t["s2"]), t["s2"]))
    else:
        scenes.append((text_scene(label, t["name"], t["h1"], t["s1"]), t["s1"]))
        scenes.append((text_scene(label, t["name"], t["h2"], t["s2"]), t["s2"]))
    scenes.append((text_scene(label, t["name"], t["h3"], t["s3"]), t["s3"]))
    im, d = base(label, "Roz seekho, free")
    y = 560
    for ln, f, c in [("Quiz, calculators aur paper trading", font(54, False), INK), (NAME + " par. Link description mein.", font(50), ACC)]:
        for l2 in wrap(d, ln, f, 940):
            d.text((70, y), l2, font=f, fill=c); y += 80
        y += 20
    scenes.append((im, "Free quiz, calculators and paper trading on %s. Link in the description. This is for learning only, not investment advice." % NAME))
    os.makedirs("out", exist_ok=True); os.makedirs("tmp_topic", exist_ok=True)
    lst = open("tmp_topic/list.txt", "w"); ok = True
    for n, (img, narr) in enumerate(scenes):
        png, mp3, mp4 = "tmp_topic/s%d.png" % n, "tmp_topic/s%d.mp3" % n, "tmp_topic/s%d.mp4" % n
        img.save(png); ok = make_audio(narr, mp3) and ok; scene_video(png, mp3, mp4); lst.write("file 's%d.mp4'\n" % n)
    lst.close()
    subprocess.run([ms.FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "tmp_topic/list.txt", "-c", "copy",
                    "-movflags", "+faststart", "out/topic-short.mp4"], check=True)
    cap = "Aaj ka concept: %s\n%s\nFree quiz, calculators aur education: %s\nSirf shiksha ke liye, investment salah nahi.\n#LearnTrading #StockMarketIndia #TradingEducation" % (t["name"], t["s2"], SITE)
    open("out/topic_caption.txt", "w", encoding="utf-8").write(cap)
    print("Topic video ban gaya:", t["name"], "| awaaz:", "haan" if ok else "nahi (silent)")

if __name__ == "__main__":
    main()
