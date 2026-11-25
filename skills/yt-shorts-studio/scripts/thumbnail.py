"""Designed thumbnail / cover: a strong frame + a big hook line.

Usage:
  python thumbnail.py --video FILE --time 56.9 --text "TWENTY *BUCKS?!*" --out covers/s01.jpg
                      [--size 1080x1920] [--focus-x 0.5] [--zoom 1.0] [--place top|middle|bottom]
                      [--accent #FFD23F] [--font PATH]
--video can be the finished Short (cover for Shorts/Reels, 1080x1920) or the 16:9 mezzanine
(long-form thumbnail, --size 1280x720). Words wrapped in *asterisks* get the accent colour.
--focus-x (0-1 of the frame width) picks the centre when the frame is cropped to fit,
--zoom > 1 punches in on that point. Keep hook text to 2-5 words: it must read at phone size.
"""
import argparse, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\Rubik-Bold.ttf", r"C:\Windows\Fonts\ariblk.ttf", r"C:\Windows\Fonts\impact.ttf",
    "/Library/Fonts/Arial Black.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def grab(video, t):
    fd, p = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", video, "-frames:v", "1", p], check=True)
    im = Image.open(p).convert("RGB")
    os.remove(p)
    return im


def cover(im, W, H, fx, zoom):
    s = max(W / im.width, H / im.height) * zoom
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    cx = min(max(fx * im.width, W / 2), im.width - W / 2)
    cy = im.height / 2
    return im.crop((round(cx - W / 2), round(cy - H / 2), round(cx - W / 2) + W, round(cy - H / 2) + H))


def auto_place(im, vertical):
    """Put the hook text where the faces aren't: find faces (OpenCV Haar) and pick the band
    (top / bottom) farthest from them. Falls back to top for vertical, bottom for 16:9."""
    try:
        import cv2, numpy as np
        g = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2GRAY)
        casc = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml"))
        f = casc.detectMultiScale(g, 1.1, 6, minSize=(im.height // 12,) * 2)
        if len(f):
            top = min(y for x, y, w, h in f)
            bottom = max(y + h for x, y, w, h in f)
            room_top, room_bottom = top, im.height - bottom
            if vertical:
                room_bottom -= im.height * 0.14     # the platform UI covers the bottom
            return "top" if room_top >= room_bottom else "bottom"
    except Exception:
        pass
    return "top" if vertical else "bottom"


def tokens(text):
    # thumbnail fonts have no emoji glyphs; drop astral-plane chars and variation selectors
    text = "".join(ch for ch in text if ord(ch) < 0x2190 or 0x2E80 <= ord(ch) < 0xFE00)
    out = []
    for w in text.split():
        acc = w.startswith("*") or w.endswith("*")
        out.append((w.strip("*"), acc))
    return out


def layout_lines(toks, font, maxw, draw):
    lines, cur = [], []
    for t in toks:
        trial = " ".join(x[0] for x in cur + [t])
        if cur and draw.textlength(trial, font=font) > maxw:
            lines.append(cur)
            cur = []
        cur.append(t)
    if cur:
        lines.append(cur)
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--time", type=float, required=True)
    ap.add_argument("--text", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--focus-x", type=float, default=0.5)
    ap.add_argument("--zoom", type=float, default=1.0)
    ap.add_argument("--place", default=None, choices=["top", "middle", "bottom"])
    ap.add_argument("--accent", default="#FFD23F")
    ap.add_argument("--font", default=None)
    a = ap.parse_args()
    W, H = map(int, a.size.lower().split("x"))
    im = cover(grab(a.video, a.time), W, H, a.focus_x, a.zoom)
    im = ImageEnhance.Contrast(ImageEnhance.Color(im).enhance(1.25)).enhance(1.08)

    if a.text:
        vertical = H > W
        place = a.place or auto_place(im, vertical)
        fpath = a.font or next(p for p in FONT_CANDIDATES if os.path.exists(p))
        draw = ImageDraw.Draw(im)
        maxw = W * (0.86 if vertical else 0.9)
        size = int(H * (0.085 if vertical else 0.16))
        toks = tokens(a.text.upper())
        while True:
            font = ImageFont.truetype(fpath, size)
            lines = layout_lines(toks, font, maxw, draw)
            if len(lines) <= (4 if vertical else 2) and all(
                    draw.textlength(" ".join(x[0] for x in l), font=font) <= maxw for l in lines) or size < 40:
                break
            size = int(size * 0.92)
        lh = int(size * 1.08)
        block = lh * len(lines)
        y0 = {"top": int(H * 0.08), "middle": (H - block) // 2, "bottom": H - block - int(H * (0.14 if vertical else 0.07))}[place]
        # soft dark band behind the text for contrast on any frame
        band = Image.new("L", (W, H), 0)
        bd = ImageDraw.Draw(band)
        pad = int(size * 0.6)
        bd.rectangle((0, max(0, y0 - pad), W, min(H, y0 + block + pad)), fill=150)
        band = band.filter(ImageFilter.GaussianBlur(size * 0.6))
        im = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), im, band)
        draw = ImageDraw.Draw(im)
        stroke = max(4, size // 11)
        for i, l in enumerate(lines):
            widths = [draw.textlength(w + " ", font=font) for w, _ in l]
            x = (W - (sum(widths) - draw.textlength(" ", font=font))) / 2
            y = y0 + i * lh
            for (w, acc), ww in zip(l, widths):
                draw.text((x + size * 0.05, y + size * 0.07), w, font=font, fill=(0, 0, 0))   # drop shadow
                draw.text((x, y), w, font=font, fill=a.accent if acc else "#FFFFFF",
                          stroke_width=stroke, stroke_fill="#000000")
                x += ww
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    im.save(a.out, quality=92)
    print("wrote", a.out, im.size)


if __name__ == "__main__":
    main()
