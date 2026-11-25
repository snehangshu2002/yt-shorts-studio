"""Look at a mezzanine clip so framing decisions are grounded in what is on screen.

Produces for OUTDIR/mezz/clipNN.mp4:
  sheets/clipNN_K.jpg     contact sheets, 1 frame/sec, 6x5 tiles, timestamp in each tile,
                          the centred 9:16 window outlined in yellow (what a plain crop keeps)
  analysis/clipNN.json    {source:[w,h], fps, duration, scenes:[t...],
                           faces:[{t, boxes:[[x,y,w,h],...]}...] (source pixels),
                           suggested_crop_keys:[[t, x_center],...]}   (for the "crop" layout)

Faces use OpenCV's bundled Haar cascade (no downloads). It finds real faces well (podcasts,
talking heads, facecams) and is noisy on game characters, so treat suggestions as a draft
and confirm them against the contact sheets.

Usage: python analyze_frames.py OUTDIR clipNN [--face-fps 4] [--no-faces]
"""
import argparse, json, os, subprocess
import numpy as np


def probe(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate:format=duration", "-of", "json", p],
                       capture_output=True, text=True)
    j = json.loads(r.stdout)
    s = j["streams"][0]
    n, d = s["r_frame_rate"].split("/")
    return int(s["width"]), int(s["height"]), float(n) / float(d), float(j["format"]["duration"])


def sheets(O, name, w, h):
    tw = 400
    th = round(tw * h / w)
    cw = round(th * 9 / 16)
    x0 = (tw - cw) // 2
    font = "C\\:/Windows/Fonts/arialbd.ttf" if os.name == "nt" else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    vf = (f"fps=1,scale={tw}:{th},drawbox=x={x0}:y=0:w={cw}:h={th}:color=yellow@0.9:t=1,"
          f"drawtext=fontfile='{font}':text='%{{eif\\:t\\:d}}':x=5:y=5:fontsize=20:fontcolor=white:borderw=2,"
          "tile=6x5:padding=2")
    os.makedirs(f"{O}/sheets", exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{O}/mezz/{name}.mp4", "-vf", vf, "-q:v", "4",
                    f"{O}/sheets/{name}_%d.jpg"], check=True)
    return sorted(f for f in os.listdir(f"{O}/sheets") if f.startswith(name + "_"))


def scenes(O, name):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", f"{O}/mezz/{name}.mp4", "-an", "-vf",
                        "scale=320:-2,select='gt(scene,0.18)',metadata=print:file=-", "-f", "null", "-"],
                       capture_output=True, text=True)
    out, last = [], -1
    for line in r.stdout.splitlines():
        if "pts_time:" in line:
            t = float(line.split("pts_time:")[1].split()[0])
            if t - last > 0.4:    # collapse flash/transition bursts
                out.append(round(t, 2))
            last = t
    return out


def faces(O, name, w, h, ffps):
    import cv2
    casc = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml"))
    prof = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, "haarcascade_profileface.xml"))
    sw = 640
    sh = round(sw * h / w / 2) * 2
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", f"{O}/mezz/{name}.mp4", "-vf", f"fps={ffps},scale={sw}:{sh},format=gray",
                          "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
    k, res, sc = 0, [], w / sw
    while True:
        buf = p.stdout.read(sw * sh)
        if len(buf) < sw * sh:
            break
        img = np.frombuffer(buf, np.uint8).reshape(sh, sw)
        ms = (int(sh * 0.08),) * 2
        det = list(casc.detectMultiScale(img, scaleFactor=1.1, minNeighbors=6, minSize=ms))
        if not det:   # three-quarter / side views: profile cascade, both directions
            det = list(prof.detectMultiScale(img, scaleFactor=1.1, minNeighbors=6, minSize=ms))
            det += [(sw - x - bw, y, bw, bh) for x, y, bw, bh in prof.detectMultiScale(img[:, ::-1].copy(), 1.1, 6, minSize=ms)]
        boxes = [[int(x * sc), int(y * sc), int(bw * sc), int(bh * sc)] for x, y, bw, bh in det]
        res.append({"t": round(k / ffps, 2), "boxes": boxes})
        k += 1
    return res


def suggest_keys(fs, scenes_t, w, h, dur, fps, ffps=4.0):
    """Face boxes -> sparse crop keyframes, decided shot by shot.

    Per shot (between scene cuts): keep only face-sized detections (>= 35% of the shot's
    largest box, which drops hands, logos and background false positives), take each sample's
    largest face, and use the shot's MEDIAN centre: one steady framing per camera angle, a hard
    jump on every cut. If the subject really moves within a shot (spread > 15% of the crop
    width), glide between 2-second medians instead."""
    crop_w = h * 9 / 16
    lo, hi = crop_w / 2, w - crop_w / 2
    clampx = lambda x: round(min(max(x, lo), hi))
    bounds = [0.0] + [c for c in scenes_t if 0.2 < c < dur - 0.2] + [dur]
    keys, last_x, review = [], w / 2, []
    for a, b in zip(bounds, bounds[1:]):
        m = 0.15 if b - a > 0.6 else 0.0   # samples right at a cut belong to the neighbouring shot
        shot = [f for f in fs if a + m <= f["t"] < b - m and f["boxes"]]
        biggest = max([bx[2] * bx[3] for f in shot for bx in f["boxes"]] or [0])
        pts = []
        for f in shot:
            good = [bx for bx in f["boxes"] if bx[2] * bx[3] >= 0.5 * biggest]
            if good:
                bx = max(good, key=lambda q: q[2] * q[3])
                pts.append((f["t"], bx[0] + bx[2] / 2))
        xs = np.array([p[1] for p in pts]) if pts else None
        mad = float(np.median(np.abs(xs - np.median(xs)))) if pts else 0
        if len(pts) < max(1, 0.3 * (b - a) * ffps):  # faces in under ~30% of samples: unreliable
            review.append([round(a, 2), round(b, 2)])
        if not pts:
            x = last_x                        # no face found: hold, and flag it for review
            seg = [[a, x]]
        elif (b - a) < 4 or mad <= 0.12 * crop_w:
            x = float(np.median([p[1] for p in pts]))
            seg = [[a, x]]
        else:                                 # real movement inside the shot: 2 s medians
            seg = []
            t = a
            while t < b:
                win = [p[1] for p in pts if t <= p[0] < min(b, t + 2)]
                if win:
                    seg.append([t + min(1.0, (b - t) / 2), float(np.median(win))])
                t += 2
            x = seg[-1][1]
        if keys:                              # hold the old framing until the frame before the cut
            keys.append([round(a - 1 / fps, 3), keys[-1][1]])
        keys.extend([[round(t, 3), clampx(v)] for t, v in seg])
        last_x = x
    # drop redundant holds (same value as the key before and after)
    out = []
    for i, k in enumerate(keys):
        if 0 < i < len(keys) - 1 and keys[i - 1][1] == k[1] == keys[i + 1][1]:
            continue
        out.append(k)
    return out, review


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("clip")
    ap.add_argument("--face-fps", type=float, default=4.0)
    ap.add_argument("--no-faces", action="store_true")
    a = ap.parse_args()
    O, name = a.outdir, a.clip
    w, h, fps, dur = probe(f"{O}/mezz/{name}.mp4")
    sh = sheets(O, name, w, h)
    sc = scenes(O, name)
    fs = [] if a.no_faces else faces(O, name, w, h, a.face_fps)
    keys, review = suggest_keys(fs, sc, w, h, dur, fps, a.face_fps) if fs else ([], [])
    os.makedirs(f"{O}/analysis", exist_ok=True)
    res = {"source": [w, h], "fps": fps, "duration": dur, "scenes": sc, "faces": fs, "suggested_crop_keys": keys, "review_shots": review}
    json.dump(res, open(f"{O}/analysis/{name}.json", "w"), indent=0)
    with_face = sum(1 for f in fs if f["boxes"])
    print(json.dumps({"clip": name, "source": [w, h], "fps": round(fps, 3), "duration": round(dur, 2),
                      "sheets": [f"sheets/{s}" for s in sh], "scene_cuts": sc,
                      "face_samples": f"{with_face}/{len(fs)}",
                      "max_faces_in_a_frame": max([len(f["boxes"]) for f in fs] or [0]),
                      "suggested_crop_keys": keys[:40],
                      "review_shots (few/no faces: check sheets, set keys by hand)": review}, indent=1))


if __name__ == "__main__":
    main()
