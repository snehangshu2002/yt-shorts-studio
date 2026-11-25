"""Render a clip spec straight to a finished vertical video with ffmpeg (no editor needed).

Same spec and same framing as build_filmcraft.py; captions are burned from subs/clipNN.ass.
Usage: python render_ffmpeg.py OUTDIR specs/clipNN.json OUT.mp4 [--size 1080x1920] [--fps 60]
                               [--crf 17] [--preset slow] [--no-captions]
Preview: --size 540x960 --crf 26 --preset veryfast
"""
import argparse, json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from layout import load_spec, panels, fit_transforms


def probe(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate:format=duration", "-of", "json", p], capture_output=True, text=True)
    j = json.loads(r.stdout)
    s = j["streams"][0]
    n, d = s["r_frame_rate"].split("/")
    return int(s["width"]), int(s["height"]), float(n) / float(d), float(j["format"]["duration"])


def even(v):
    return max(2, int(round(v / 2)) * 2)


def x_expr(keys, vw, sw):
    """Piecewise-linear crop-x(t) expression from [t, centre_x] keys."""
    def lim(x):
        return min(max(x - vw / 2, 0), sw - vw)
    if len(keys) == 1:
        return f"{lim(keys[0][1]):.2f}"
    expr = f"{lim(keys[-1][1]):.2f}"
    for (t0, x0), (t1, x1) in reversed(list(zip(keys, keys[1:]))):
        a, b = lim(x0), lim(x1)
        seg = f"{a:.2f}" if t1 <= t0 or abs(b - a) < 0.01 else f"({a:.2f}+({b - a:.2f})*(t-{t0:.4f})/{t1 - t0:.4f})"
        expr = f"if(lt(t,{t1:.4f}),{seg},{expr})"
    return f"if(lt(t,{keys[0][0]:.4f}),{lim(keys[0][1]):.2f},{expr})"


def gradient_png(path, W, H, seam):
    from PIL import Image
    import numpy as np
    a = np.zeros((H, W, 4), np.uint8)
    up, down = round(H * 0.2), round(H * 0.084)
    for y in range(max(0, seam - up), seam):
        a[y, :, 3] = int(240 * ((y - (seam - up)) / up) ** 1.2)
    for y in range(seam, min(H, seam + down)):
        a[y, :, 3] = int(224 * (1 - (y - seam) / down))
    Image.fromarray(a, "RGBA").save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("spec")
    ap.add_argument("out")
    ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--fps", type=float, default=None)
    ap.add_argument("--crf", type=int, default=17)
    ap.add_argument("--preset", default="slow")
    ap.add_argument("--no-captions", action="store_true")
    ap.add_argument("--still", type=float, default=None,
                    help="write one caption-free PNG of the layout at this time (for covers) instead of a video")
    a = ap.parse_args()
    if a.still is not None:
        a.no_captions = True
    O = os.path.abspath(a.outdir)
    S = load_spec(a.spec)
    clip = S["clip"]
    W, H = map(int, a.size.lower().split("x"))
    src = os.path.join(O, "mezz", f"{clip}.mp4")
    sw, sh, sfps, dur = probe(src)
    P = panels(S, W, H, sw, sh)
    ft = fit_transforms(W, H, sw, sh)

    inputs = ["-i", src]
    g = []
    need_fit = S["layout"] == "fit" or S["fit_spans"]
    n_split = len(P) + (1 if need_fit else 0)
    g.append(f"[0:v]split={n_split}" + "".join(f"[s{i}]" for i in range(n_split)))
    labels = []
    for i, p in enumerate(P):
        vw, vh = even(p["vw"]), even(p["vh"])
        y = max(0, min(sh - vh, p["cy"] - vh / 2))
        if p["kind"] == "rect":
            x = f"{max(0, min(sw - vw, p['cx'] - vw / 2)):.2f}"
        else:
            x = x_expr(p["keys"], vw, sw)
        g.append(f"[s{i}]crop=w={vw}:h={vh}:x='{x}':y={y:.2f},scale={W}:{p['h']}:flags=lanczos,setsar=1[p{i}]")
        labels.append(f"[p{i}]")
    cur = None
    if len(labels) == 2:
        g.append(f"{labels[0]}{labels[1]}vstack=inputs=2[main]")
        cur = "[main]"
    elif len(labels) == 1:
        cur = labels[0]
    if S["layout"] == "split" and S["gradient"]:
        gp = os.path.join(O, "builds", f"gradient_{W}x{H}.png")
        os.makedirs(os.path.dirname(gp), exist_ok=True)
        gradient_png(gp, W, H, P[0]["h"])
        inputs += ["-i", gp]
        g.append(f"{cur}[1:v]overlay=0:0[mg]")
        cur = "[mg]"
    if need_fit:
        k = n_split - 1
        bw, bh = even(sw * ft["bg_scale"] * 1.02), even(sh * ft["bg_scale"] * 1.02)
        fw, fh = even(sw * ft["fg_scale"]), even(sh * ft["fg_scale"])
        g.append(f"[s{k}]split=2[fa][fb]")
        g.append(f"[fa]scale={bw}:{bh},crop={W}:{H},boxblur=40:3[bg]")
        g.append(f"[fb]scale={fw}:{fh}:flags=lanczos[fg]")
        g.append(f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[fit]")
        if cur is None:
            cur = "[fit]"
        else:
            en = "+".join(f"between(t,{x:.3f},{y:.3f})" for x, y in S["fit_spans"])
            g.append(f"{cur}[fit]overlay=0:0:enable='{en}'[mf]")
            cur = "[mf]"
    if not a.no_captions and os.path.exists(os.path.join(O, "subs", f"{clip}.ass")):
        fonts = "fontsdir='C\\:/Windows/Fonts'" if os.name == "nt" else ""
        g.append(f"{cur}ass=subs/{clip}.ass{(':' + fonts) if fonts else ''}[cap]")
        cur = "[cap]"
    g.append(f"{cur}format=yuv420p[vout]")
    fps = a.fps or sfps
    if a.still is not None:   # seek on the output side so the t-based crop expressions stay correct
        cmd = ["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", ";".join(g), "-map", "[vout]",
                                                          "-ss", f"{a.still:.3f}", "-frames:v", "1", os.path.abspath(a.out)]
        subprocess.run(cmd, cwd=O, check=True)
        print("wrote", a.out)
        return
    cmd = ["ffmpeg", "-v", "error", "-y"] + inputs + [
        "-filter_complex", ";".join(g), "-map", "[vout]", "-map", "0:a?", "-r", f"{fps}",
        "-c:v", "libx264", "-preset", a.preset, "-crf", str(a.crf), "-profile:v", "high",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-t", f"{dur:.3f}",
        os.path.abspath(a.out)]
    subprocess.run(cmd, cwd=O, check=True)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
