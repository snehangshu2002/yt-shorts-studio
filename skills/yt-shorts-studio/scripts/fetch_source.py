"""Fetch a YouTube video's metadata and word-timed transcript WITHOUT downloading the video.

Writes into OUTDIR:
  src.info.json        full yt-dlp metadata
  words.json           [[seconds, word], ...]   (word-level timing)
  lines.json           [[start, end, text], ...] (caption lines)
  transcript.txt       "mm:ss.s text" per line, for reading/analysis
  heatmap.json         YouTube "most replayed" data when available
  source_summary.json  title, channel, duration, best height/fps, chapters, caption kind

Usage: python fetch_source.py URL OUTDIR [--langs en,en-orig,en-US,en-GB]
Exit code 3 = no usable captions (use transcribe.py as a fallback).
"""
import argparse, glob, json, os, shutil, subprocess, sys


def ytdlp_base():
    cmd = [sys.executable, "-m", "yt_dlp", "--no-warnings"]
    if shutil.which("node"):
        cmd += ["--js-runtimes", "node"]
    return cmd


def parse_json3(path):
    """YouTube json3 captions -> (words, lines). Creator captions often repeat every event
    (outline + fill pens), so identical (start, text) events are deduplicated."""
    d = json.load(open(path, encoding="utf-8"))
    seen, words, lines = set(), [], []
    for ev in d.get("events", []):
        if "segs" not in ev:
            continue
        key = (ev["tStartMs"], "".join(s.get("utf8", "") for s in ev["segs"]))
        if key in seen:
            continue
        seen.add(key)
        t0 = ev["tStartMs"] / 1000
        t1 = t0 + ev.get("dDurationMs", 0) / 1000
        lw = []
        for s in ev["segs"]:
            w = s.get("utf8", "").replace("​", "").strip()
            if not w or w == "\n":
                continue
            t = round(t0 + s.get("tOffsetMs", 0) / 1000, 3)
            words.append([t, w])
            lw.append([t, w])
        if lw:   # keep each line's own words: overlapping speakers stay separate
            lines.append([round(t0, 3), round(t1, 3), " ".join(x[1] for x in lw), lw])
    # auto-captions repeat the previous line as a rolling "context" event; drop exact repeats
    words.sort(key=lambda x: x[0])
    lines.sort(key=lambda x: x[0])
    return words, lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("outdir")
    ap.add_argument("--langs", default="en,en-orig,en-US,en-GB")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    # Explicit language codes only: wildcard/translated tracks trigger HTTP 429 quickly.
    subprocess.run(ytdlp_base() + ["--skip-download", "--write-info-json", "--write-subs", "--write-auto-subs",
                                   "--sub-langs", a.langs, "--sub-format", "json3", "-o", "src.%(ext)s", a.url],
                   cwd=a.outdir)
    info_p = os.path.join(a.outdir, "src.info.json")
    if not os.path.exists(info_p):  # a subtitle error can abort before the info json is written
        subprocess.run(ytdlp_base() + ["--skip-download", "--write-info-json", "-o", "src.%(ext)s", a.url],
                       cwd=a.outdir, check=True)
    info = json.load(open(info_p, encoding="utf-8"))

    manual = set((info.get("subtitles") or {}).keys())
    subs = sorted(glob.glob(os.path.join(a.outdir, "src.*.json3")))
    order = [l.strip() for l in a.langs.split(",")]
    pick = None
    for want_manual in (True, False):
        for lang in order:
            p = os.path.join(a.outdir, f"src.{lang}.json3")
            if p in subs and ((lang in manual) == want_manual):
                pick, kind = p, ("creator" if want_manual else "auto")
                break
        if pick:
            break

    heights = [f.get("height") or 0 for f in info.get("formats", []) if f.get("vcodec") not in (None, "none")]
    fps = max([f.get("fps") or 0 for f in info.get("formats", []) if (f.get("height") or 0) == max(heights or [0])] or [0])
    summary = {
        "title": info.get("title"), "channel": info.get("channel") or info.get("uploader"),
        "url": info.get("webpage_url"), "duration": info.get("duration"),
        "best_height": max(heights or [0]), "best_fps": fps,
        "width": info.get("width"), "height": info.get("height"),
        "chapters": info.get("chapters"), "has_heatmap": bool(info.get("heatmap")),
        "captions": None, "description": (info.get("description") or "")[:1500],
    }
    if info.get("heatmap"):
        hm = info["heatmap"]
        json.dump(hm, open(os.path.join(a.outdir, "heatmap.json"), "w"), indent=0)
        dur = info.get("duration") or hm[-1]["end_time"]
        # the last ~3% is usually the end-screen artefact and the first 1% the autoplay start
        body = [h for h in hm if dur * 0.01 < h["start_time"] < dur * 0.97]
        top = sorted(body, key=lambda h: -h["value"])[:8]
        summary_peaks = [f"{int(h['start_time'] // 60)}:{int(h['start_time'] % 60):02d} ({h['value']:.2f})"
                         for h in sorted(top, key=lambda h: h["start_time"])]
    else:
        summary_peaks = []
    summary["most_replayed_peaks"] = summary_peaks

    if not pick:
        json.dump(summary, open(os.path.join(a.outdir, "source_summary.json"), "w", encoding="utf-8"), indent=1)
        print(json.dumps(summary, indent=1))
        print("NO_CAPTIONS: run transcribe.py (faster-whisper) after asking the user.", file=sys.stderr)
        sys.exit(3)

    words, lines = parse_json3(pick)
    summary["captions"] = {"file": os.path.basename(pick), "kind": kind, "words": len(words), "lines": len(lines)}
    json.dump(words, open(os.path.join(a.outdir, "words.json"), "w", encoding="utf-8"))
    json.dump(lines, open(os.path.join(a.outdir, "lines.json"), "w", encoding="utf-8"))
    with open(os.path.join(a.outdir, "transcript.txt"), "w", encoding="utf-8") as f:
        for t0, t1, txt, _ in lines:
            f.write(f"{int(t0 // 60):02d}:{t0 % 60:04.1f} {txt}\n")
    json.dump(summary, open(os.path.join(a.outdir, "source_summary.json"), "w", encoding="utf-8"), indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
