"""Build an editable vertical Short in the LIVE FilmCraft app from a clip spec.

Usage: python build_filmcraft.py OUTDIR specs/clipNN.json [--canvas 2160x3840] [--no-captions]
       python build_filmcraft.py OUTDIR specs/clipNN.json --captions-only   (rebuild captions)

Needs the bridge (python fc.py status). Uses whatever project is open in the app; open or
create the project first (fc.py exec file.newProject '{"name":"..."}' then file.save to a path).
Tracks: V1 main/top panel (+A1 audio), V2 bottom panel or fitted frame, V3 seam gradient,
V4 captions (one native text clip per word state, so every caption stays editable).
Writes OUTDIR/builds/clipNN.json: sequence id, media item, caption clip ids.
"""
import argparse, json, os, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fc
from layout import load_spec, panels, interp, fit_transforms

TPS = 254016000000


def probe(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate:format=duration", "-of", "json", p], capture_output=True, text=True)
    j = json.loads(r.stdout)
    s = j["streams"][0]
    n, d = s["r_frame_rate"].split("/")
    return int(s["width"]), int(s["height"]), float(n) / float(d), float(j["format"]["duration"])


def seq_fps(f):
    for std in (23.976, 24, 25, 29.97, 30, 50, 59.94, 60):
        if abs(f - std) < 0.02:
            return std
    return round(f, 3)


def caption_steps(events, W, H, fps, cap):
    k = W / 1080
    x, base_y, size = W / 2, cap["y"] * H / 1920 + 0.36 * cap["size"] * k, round(cap["size"] * 2 * k / 2)
    style = {"align": "center", "fill_color": "#ffffff", "stroke": True, "stroke_color": "#000000",
             "stroke_width": round(4.5 * k), "shadow": True, "shadow_color": "#000000", "shadow_opacity": 55,
             "shadow_distance": round(3 * k), "shadow_blur": round(7 * k), "tracking": 10, "position": [x, base_y]}
    tpf = TPS / fps
    steps = []
    for e in events:
        f0, f1 = round(e["start"] * fps), round(e["end"] * fps)
        if f1 <= f0:
            continue
        t0 = round(f0 * tpf)
        dur = (f1 - f0) / fps - 0.0005          # stay inside the frame grid: avoids "track not free"
        a = sum(len(w) + 1 for w in e["words"][: e["active"]])
        b = a + len(e["words"][e["active"]])
        steps.append({"id": "graphics.newText", "params": {"text": " ".join(e["words"]), "position": [x, base_y],
                      "size": size, "font": cap.get("font", "Rubik"), "fontStyle": "Bold",
                      "seconds": round(dur, 4), "track": 3, "time": t0}})
        steps.append({"id": "graphics.set", "params": {"layer": 0, "props": style}})
        steps.append({"id": "graphics.setCharStyle", "params": {"layer": 0, "start": a, "end": b,
                      "style": {"color": cap.get("accent", "#ffd23f").lower()}}})
        if e.get("first") and dur > 0.2:
            steps.append({"id": "graphics.set", "params": {"layer": 0, "props": {"scale": 86}, "time": t0, "keyframe": True}})
            steps.append({"id": "graphics.set", "params": {"layer": 0, "props": {"scale": 100},
                          "time": t0 + round(0.11 * TPS), "keyframe": True}})
    return steps


def add_captions(O, clip, W, H, fps, state):
    cap = json.load(open(f"{O}/subs/{clip}.json", encoding="utf-8"))
    steps = caption_steps(cap["events"], W, H, fps, cap)
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for s in steps:
            f.write(json.dumps(s) + "\n")
    res = fc.run_script(path)
    os.remove(path)
    state["caption_clips"] = [r["result"]["clip"] for r in res if r["id"] == "graphics.newText"]
    print(f"captions: {len(state['caption_clips'])} text clips")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("spec")
    ap.add_argument("--canvas", default="2160x3840")
    ap.add_argument("--no-captions", action="store_true")
    ap.add_argument("--captions-only", action="store_true")
    a = ap.parse_args()
    O = os.path.abspath(a.outdir)
    S = load_spec(a.spec)
    clip = S["clip"]
    W, H = map(int, a.canvas.lower().split("x"))
    src = os.path.join(O, "mezz", f"{clip}.mp4")
    sw, sh, sfps, dur = probe(src)
    fps = seq_fps(sfps)
    os.makedirs(f"{O}/builds", exist_ok=True)
    stp = f"{O}/builds/{clip}.json"

    if a.captions_only:
        state = json.load(open(stp))
        fc.exec_cmd("sequence.open", {"item": state["sequence"]})
        if state.get("caption_clips"):
            fc.exec_cmd("timeline.delete", {"clips": state["caption_clips"]})
        add_captions(O, clip, W, H, fps, state)
        json.dump(state, open(stp, "w"), indent=1)
        fc.exec_cmd("file.save", {})
        return

    item = fc.exec_cmd("file.import", {"paths": [src]})["items"][0]
    seq = fc.exec_cmd("file.newSequence", {"name": S["name"], "width": W, "height": H, "fps": fps,
                                           "video": 4, "audio": 1})["sequence"]
    fc.exec_cmd("timeline.place", {"item": item, "track": "V1", "audioTrack": "A1", "seconds": 0})
    fc.exec_cmd("timeline.place", {"item": item, "track": "V2", "seconds": 0, "audio": False})
    tpf = TPS / fps
    cuts = sorted({round(t * fps) for span in S["fit_spans"] for t in span if 0 < t < dur})
    for fr in cuts:
        for tr in ("V1", "V2"):
            fc.exec_cmd("timeline.razor", {"time": round(fr * tpf), "track": tr})
    sj = fc.exec_cmd("sequence.inspect", {"item": seq})
    v1, v2 = sj["video"][0]["items"], sj["video"][1]["items"]

    P = panels(S, W, H, sw, sh)
    ft = fit_transforms(W, H, sw, sh)

    def fitted(c):
        if S["layout"] == "fit":
            return True
        mid = (c["start"] + c["end"]) / 2 / TPS
        return any(x <= mid < y for x, y in S["fit_spans"])

    def set_motion(cid, scale, pos, anchor=None):
        fc.exec_cmd("effects.setParam", {"clip": cid, "effect": "motion", "param": "scale", "value": round(scale * 100, 3)})
        fc.exec_cmd("effects.setParam", {"clip": cid, "effect": "motion", "param": "position", "value": pos})
        if anchor:
            fc.exec_cmd("effects.setParam", {"clip": cid, "effect": "motion", "param": "anchor", "value": anchor})

    def apply_panel(cid, p, c0, c1):
        pos = [W / 2, p["y"] + p["h"] / 2]
        if p["kind"] == "rect":
            set_motion(cid, p["scale"], pos, [p["cx"], p["cy"]])
        else:
            set_motion(cid, p["scale"], pos)
            last = c1 - 1 / fps
            ks = [[c0, interp(p["keys"], c0)]] + [k for k in p["keys"] if c0 < k[0] < last] + [[last, interp(p["keys"], last)]]
            if len({round(x) for _, x in ks}) == 1:
                fc.exec_cmd("effects.setParam", {"clip": cid, "effect": "motion", "param": "anchor", "value": [ks[0][1], p["cy"]]})
            else:
                for t, x in ks:
                    fc.exec_cmd("effects.setParam", {"clip": cid, "effect": "motion", "param": "anchor", "value": [x, p["cy"]],
                                                     "time": round(round(t * fps) * tpf), "keyframe": True})
        if p["y"] > 0:   # lower panel: hide the part of the source that would cover the panel above
            top = max(0.0, p["cy"] - p["vh"] / 2) / sh * 100
            if top > 0.05:
                fx = fc.exec_cmd("effects.apply", {"clips": [cid], "effect": "crop"})["applied"][0]["index"]
                fc.exec_cmd("effects.setParam", {"clip": cid, "effect": fx, "param": "top", "value": round(top, 2)})

    for c in v1:
        cid, c0, c1 = c["clip"], c["start"] / TPS, c["end"] / TPS
        if fitted(c):
            set_motion(cid, ft["bg_scale"] * 1.02, [W / 2, H / 2])
            fx = fc.exec_cmd("effects.apply", {"clips": [cid], "effect": "gaussian_blur"})["applied"][0]["index"]
            fc.exec_cmd("effects.setParam", {"clip": cid, "effect": fx, "param": "blurriness", "value": 90})
        else:
            apply_panel(cid, P[0], c0, c1)
    for c in v2:
        cid, c0, c1 = c["clip"], c["start"] / TPS, c["end"] / TPS
        if fitted(c):
            set_motion(cid, ft["fg_scale"], [W / 2, H / 2])
        elif S["layout"] == "split":
            apply_panel(cid, P[1], c0, c1)
        else:
            fc.exec_cmd("timeline.delete", {"clips": [cid]})

    state = {"sequence": seq, "item": item, "name": S["name"], "canvas": [W, H], "fps": fps}
    if S["gradient"] and S["layout"] == "split":
        seam = P[0]["h"]
        band = round(H * 0.2)
        g = fc.exec_cmd("graphics.newShape", {"shape": "rectangle", "position": [W / 2, seam - band / 2],
                                              "size": [W, band], "seconds": dur, "track": 2, "time": 0})["clip"]
        # 8-digit hex colours must be lowercase or the alpha is ignored
        fc.exec_cmd("graphics.set", {"clip": g, "layer": 0, "props": {"fill": True, "fill_kind": 1, "gradient_angle": 90,
                                     "gradient_start": "#00000000", "gradient_end": "#000000f0"}})
        fc.exec_cmd("graphics.newShape", {"shape": "rectangle", "position": [W / 2, seam + band * 0.21], "size": [W, round(band * 0.42)], "clip": g})
        fc.exec_cmd("graphics.set", {"clip": g, "layer": 1, "props": {"fill": True, "fill_kind": 1, "gradient_angle": 90,
                                     "gradient_start": "#000000e0", "gradient_end": "#00000000"}})
        state["gradient"] = g
    if not a.no_captions and os.path.exists(f"{O}/subs/{clip}.json"):
        add_captions(O, clip, W, H, fps, state)
    json.dump(state, open(stp, "w"), indent=1)
    fc.exec_cmd("file.save", {})
    print(json.dumps(state if len(json.dumps(state)) < 400 else {k: v for k, v in state.items() if k != "caption_clips"}))


if __name__ == "__main__":
    main()
