"""Regenerate the README artwork: assets/logo.png, assets/logo.svg, assets/demo.gif.
Usage: python tools/make_assets.py   (needs Pillow; uses JetBrains Mono if installed)
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "assets")
os.makedirs(A, exist_ok=True)


def font(names, size):
    dirs = [os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts"), r"C:\Windows\Fonts",
            "/usr/share/fonts/truetype/jetbrains-mono", "/usr/share/fonts/truetype/dejavu", "/Library/Fonts"]
    for n in names:
        for d in dirs:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
    return ImageFont.load_default()


MONO = ["JetBrainsMono-Regular.ttf", "consola.ttf", "DejaVuSansMono.ttf"]
MONO_B = ["JetBrainsMono-Bold.ttf", "consolab.ttf", "DejaVuSansMono-Bold.ttf"]
SANS_B = ["Rubik-Bold.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"]

RED, ORANGE, YELLOW = (255, 59, 48), (255, 140, 40), (255, 210, 63)


# ---------------------------------------------------------------- logo
def logo(size=512):
    s = size / 512
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    # background tile: dark rounded square
    bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(bg).rounded_rectangle((0, 0, size - 1, size - 1), radius=int(112 * s), fill=(18, 18, 24, 255))
    im.alpha_composite(bg)
    # vertical 9:16 "phone" with red->orange gradient
    pw, ph = int(220 * s), int(360 * s)
    px, py = (size - pw) // 2, int(64 * s)
    grad = Image.new("RGBA", (pw, ph))
    gd = ImageDraw.Draw(grad)
    for y in range(ph):
        t = y / ph
        c = tuple(int(RED[i] + (ORANGE[i] - RED[i]) * t) for i in range(3)) + (255,)
        gd.line((0, y, pw, y), fill=c)
    mask = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, pw - 1, ph - 1), radius=int(38 * s), fill=255)
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle((px, py, px + pw, py + ph), radius=int(38 * s), fill=(255, 90, 40, 140))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(28 * s)))
    im.paste(grad, (px, py), mask)
    d = ImageDraw.Draw(im)
    # play triangle
    cx, cy, r = size // 2 + int(8 * s), py + int(150 * s), int(62 * s)
    d.polygon([(cx - r * 0.75, cy - r), (cx - r * 0.75, cy + r), (cx + r, cy)], fill=(255, 255, 255, 255))
    # caption bar: white - yellow - white words
    by = py + int(262 * s)
    bh = int(26 * s)
    segs = [(int(30 * s), int(62 * s), (255, 255, 255, 255)), (int(70 * s), int(150 * s), YELLOW + (255,)),
            (int(158 * s), int(190 * s), (255, 255, 255, 255))]
    for x0, x1, c in segs:
        d.rounded_rectangle((px + x0, by, px + x1, by + bh), radius=bh // 2, fill=c)
    d.rounded_rectangle((px + int(60 * s), by + int(40 * s), px + int(160 * s), by + int(40 * s) + int(16 * s)),
                        radius=int(8 * s), fill=(255, 255, 255, 150))
    return im


def logo_svg():
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FF3B30"/><stop offset="1" stop-color="#FF8C28"/>
    </linearGradient>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="28"/></filter>
  </defs>
  <rect width="512" height="512" rx="112" fill="#121218"/>
  <rect x="146" y="64" width="220" height="360" rx="38" fill="#FF5A28" opacity="0.55" filter="url(#glow)"/>
  <rect x="146" y="64" width="220" height="360" rx="38" fill="url(#g)"/>
  <polygon points="217.5,152 217.5,276 326,214" fill="#fff"/>
  <rect x="176" y="326" width="32" height="26" rx="13" fill="#fff"/>
  <rect x="216" y="326" width="80" height="26" rx="13" fill="#FFD23F"/>
  <rect x="304" y="326" width="32" height="26" rx="13" fill="#fff"/>
  <rect x="206" y="366" width="100" height="16" rx="8" fill="#fff" opacity="0.6"/>
</svg>
"""


# ---------------------------------------------------------------- demo gif
STEPS = [
    ("fetch", "yt-dlp · metadata + word-timed captions · no video download"),
    ("plan", "20 moments ranked · hooks + rewatch peaks"),
    ("approve", "you pick 3 → only those segments are downloaded"),
    ("frame", "face tracking · split facecam · nobody cropped"),
    ("caption", "word-by-word · active word highlighted"),
    ("edit", "FilmCraft live timeline  (or ffmpeg fallback)"),
    ("export", "1080×1920 · 60 fps · H.264 high"),
    ("publish", "covers · titles · descriptions · tags"),
]
CLIPS = [("01_cold_open.mp4", "0:59"), ("02_clerk_faints.mp4", "0:48"), ("03_cops_arrive.mp4", "0:57")]
PROMPT = "make shorts from https://youtu.be/…"

W, H = 1120, 520
BG, PANEL, BORDER = (13, 13, 17), (22, 22, 28), (44, 44, 54)
TXT, DIM, GREEN = (236, 236, 240), (130, 130, 145), (52, 211, 153)
f_mono = font(MONO, 17)
f_mono_b = font(MONO_B, 17)
f_small = font(MONO, 14)
f_title = font(MONO, 14)
SPIN = "|/-\\"


def frame(typed, done, active, spin_i, clips_shown, cursor):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((20, 20, W - 20, H - 20), radius=16, fill=PANEL, outline=BORDER, width=2)
    for i, c in enumerate([(255, 95, 87), (254, 188, 46), (40, 200, 64)]):
        d.ellipse((42 + i * 24, 40, 56 + i * 24, 54), fill=c)
    t = "yt-shorts-studio · agent skill"
    d.text(((W - d.textlength(t, font=f_title)) / 2, 38), t, font=f_title, fill=DIM)
    # prompt
    d.text((48, 86), "›", font=f_mono_b, fill=(255, 90, 60))
    d.text((72, 86), PROMPT[:typed] + ("▌" if cursor else " "), font=f_mono_b, fill=TXT)
    # steps
    y = 132
    for i, (name, detail) in enumerate(STEPS):
        if i < done:
            d.text((48, y), "✓", font=f_mono_b, fill=GREEN)
            d.text((76, y), name, font=f_mono_b, fill=TXT)
            d.text((190, y), detail, font=f_small, fill=DIM)
        elif i == active:
            d.text((48, y), SPIN[spin_i % len(SPIN)] if spin_i >= 0 else "·", font=f_mono_b, fill=YELLOW)
            d.text((76, y), name, font=f_mono_b, fill=YELLOW)
        y += 34
    # clips panel
    x0 = 790
    if clips_shown:
        d.text((x0, 132), "shorts/", font=f_small, fill=DIM)
    for i in range(clips_shown):
        cy = 158 + i * 56
        d.rounded_rectangle((x0, cy, W - 44, cy + 44), radius=8, fill=(30, 30, 38), outline=BORDER)
        d.rounded_rectangle((x0 + 10, cy + 10, x0 + 46, cy + 34), radius=4, fill=(232, 80, 50))
        d.polygon([(x0 + 23, cy + 15), (x0 + 23, cy + 29), (x0 + 35, cy + 22)], fill=(255, 255, 255))
        name, dur = CLIPS[i]
        d.text((x0 + 56, cy + 13), name, font=f_small, fill=TXT)
        d.text((W - 58 - d.textlength(dur, font=f_small), cy + 13), dur, font=f_small, fill=DIM)
    return im


def demo():
    frames, durs = [], []

    def add(im, ms):
        frames.append(im)
        durs.append(ms)

    for k in range(0, len(PROMPT) + 1, 2):
        add(frame(k, 0, -1, -1, 0, True), 45)
    add(frame(len(PROMPT), 0, -1, -1, 0, False), 400)
    for i in range(len(STEPS)):
        for s in range(5):
            add(frame(len(PROMPT), i, i, s, 0, False), 80)
        if STEPS[i][0] == "export":
            pass
    # finish: all done, clips appear one by one
    for c in range(1, len(CLIPS) + 1):
        add(frame(len(PROMPT), len(STEPS), -1, -1, c, False), 420)
    add(frame(len(PROMPT), len(STEPS), -1, -1, len(CLIPS), False), 2800)
    pal = [f.convert("P", palette=Image.ADAPTIVE, colors=64) for f in frames]
    pal[0].save(os.path.join(A, "demo.gif"), save_all=True, append_images=pal[1:], duration=durs, loop=0,
                optimize=True, disposal=2)


if __name__ == "__main__":
    logo(512).save(os.path.join(A, "logo.png"))
    logo(128).save(os.path.join(A, "logo-128.png"))
    open(os.path.join(A, "logo.svg"), "w").write(logo_svg())
    demo()
    print("assets written:", sorted(os.listdir(A)))
