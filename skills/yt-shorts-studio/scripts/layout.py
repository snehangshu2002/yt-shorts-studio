"""Shared layout maths for the FilmCraft builder and the ffmpeg renderer.

A clip spec (specs/clipNN.json) describes framing in SOURCE pixels, independent of the
output size, so the same spec renders identically at 1080x1920 or 2160x3840:

{
  "name": "Short 01 - Zero dollars",      # sequence / file title
  "clip": "clip01",                       # mezz/clip01.mp4, subs/clip01.(json|ass)
  "layout": "split" | "crop" | "fit",
  "split": 0.58125,                       # split: top panel height as a fraction of the canvas
  "top":    {"keys": [[t, x], ...]}       # split: top panel follows a horizontal centre (full source height)
            or {"rect": [x, y, w, h]},    #        or shows a fixed source region
  "bottom": {"rect": [x, y, w, h]}        # split: bottom panel region (facecam, second speaker...)
            or {"keys": [[t, x], ...], "band": [y0, y1]},   # or a tracked band of the source
  "keys": [[t, x], ...],                  # crop: horizontal centre of the 9:16 window over time
  "zoom": 1.0,                            # crop: >1 punches in (keeps centre y = "center_y")
  "center_y": null,                       # crop: vertical centre in source px when zoomed
  "fit_spans": [[a, b], ...],             # any layout: show the whole frame over a blurred fill here
  "gradient": true                        # split: dark gradient across the seam (captions sit on it)
}
Keys are [seconds_from_clip_start, source_x]. Two keys one frame apart make a hard jump (use on
scene cuts); keys further apart glide linearly.
"""
import json


def load_spec(path):
    s = json.load(open(path, encoding="utf-8"))
    s.setdefault("split", 0.58125)
    s.setdefault("fit_spans", [])
    s.setdefault("gradient", s.get("layout") == "split")
    s.setdefault("zoom", 1.0)
    return s


def interp(keys, t):
    if not keys:
        return None
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, x0), (t1, x1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            return x0 if t1 == t0 else x0 + (x1 - x0) * (t - t0) / (t1 - t0)
    return keys[-1][1]


def panels(spec, W, H, sw, sh):
    """Return the panels to draw, top to bottom, as dicts:
       {kind: 'keys'|'rect', y: panel_top, h: panel_height, scale: s (output px per source px),
        vw, vh: visible source size, keys | cx, cy}
    """
    out = []
    lay = spec["layout"]
    if lay == "crop":
        z = spec.get("zoom", 1.0)
        s = max(H / sh, W / sw) * z
        vw, vh = W / s, H / s
        cy = spec.get("center_y") or sh / 2
        cy = min(max(cy, vh / 2), sh - vh / 2)
        out.append({"kind": "keys", "y": 0, "h": H, "scale": s, "vw": vw, "vh": vh,
                    "keys": clamp_keys(spec.get("keys") or [[0, sw / 2]], vw, sw), "cy": cy})
    elif lay == "split":
        Ht = round(H * spec["split"])
        for part, y0, ph in (("top", 0, Ht), ("bottom", Ht, H - Ht)):
            p = spec[part]
            if "rect" in p:
                x, y, w, h = p["rect"]
                s = max(W / w, ph / h)
                vw, vh = W / s, ph / s
                cx = min(max(x + w / 2, vw / 2), sw - vw / 2)
                cy = min(max(y + h / 2, vh / 2), sh - vh / 2)
                out.append({"kind": "rect", "y": y0, "h": ph, "scale": s, "vw": vw, "vh": vh, "cx": cx, "cy": cy})
            else:
                b0, b1 = p.get("band", [0, sh])
                s = max(ph / (b1 - b0), W / sw)
                vw, vh = W / s, ph / s
                cy = min(max((b0 + b1) / 2, vh / 2), sh - vh / 2)
                out.append({"kind": "keys", "y": y0, "h": ph, "scale": s, "vw": vw, "vh": vh,
                            "keys": clamp_keys(p["keys"], vw, sw), "cy": cy})
    elif lay != "fit":
        raise ValueError(f"unknown layout {lay}")
    return out


def clamp_keys(keys, vw, sw):
    lo, hi = vw / 2, sw - vw / 2
    if lo > hi:
        lo = hi = sw / 2
    return [[t, min(max(x, lo), hi)] for t, x in keys]


def fit_transforms(W, H, sw, sh):
    """Blurred cover background + fitted foreground scales."""
    return {"bg_scale": max(W / sw, H / sh), "fg_scale": min(W / sw, H / sh)}
