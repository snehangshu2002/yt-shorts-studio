"""Download ONLY the approved segments, align them to the source timeline, and cut exact
edit-ready mezzanine files.

Reads OUTDIR/clips.json: [{"id": 1, "title": "...", "start": 0.0, "end": 59.3}, ...]
Writes:
  src/clipNN.mkv     the raw section as YouTube served it (stream copy, may start early)
  offsets.json       {"1": source_time_of_file_t0, ...}
  mezz/clipNN.mp4    frame-accurate H.264 (CRF 12, GOP 30) + AAC 48 kHz, exactly start..end

Why the alignment step: yt-dlp's --download-sections stream-copies from the keyframe before
the requested start, so a file can begin several seconds early. The true offset is
(requested_end - file_duration); when words.json exists it is confirmed by
cross-correlating the audio's speech-band loudness against the caption word timings.

Usage: python download_segments.py URL OUTDIR [--ids 1,2,3] [--max-height 2160] [--pad 1.0]
"""
import argparse, json, os, shutil, subprocess, sys
import numpy as np


def probe_dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", p], capture_output=True, text=True).stdout)


def envelope(p, sr=100):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", "1", "-ar", "8000",
                          "-af", "highpass=f=200,lowpass=f=3500", "-f", "s16le", "-"],
                         capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32)
    hop = 8000 // sr
    n = len(a) // hop
    e = np.log1p(np.sqrt((a[: n * hop].reshape(n, hop) ** 2).mean(1)))
    return (e - e.mean()) / (e.std() + 1e-6)


def refine(guess, env, wt, sr=100):
    best = (guess, -1e9)
    for lag in np.arange(-3, 3.001, 0.02):
        t0 = guess + lag
        act = np.zeros(len(env))
        for t in wt[(wt >= t0) & (wt < t0 + len(env) / sr)]:
            i = int((t - t0) * sr)
            act[i: i + 25] = 1
        if act.std() == 0:
            continue
        act = (act - act.mean()) / act.std()
        s = float((env * act).mean())
        if s > best[1]:
            best = (t0, s)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("outdir")
    ap.add_argument("--ids", default=None)
    ap.add_argument("--max-height", type=int, default=2160)
    ap.add_argument("--pad", type=float, default=1.0)
    a = ap.parse_args()
    O = a.outdir
    clips = json.load(open(f"{O}/clips.json", encoding="utf-8"))
    if a.ids:
        keep = {int(x) for x in a.ids.split(",")}
        clips = [c for c in clips if int(c["id"]) in keep]
    os.makedirs(f"{O}/src", exist_ok=True)
    os.makedirs(f"{O}/mezz", exist_ok=True)
    wt = np.array([w[0] for w in json.load(open(f"{O}/words.json"))]) if os.path.exists(f"{O}/words.json") else None
    offp = f"{O}/offsets.json"
    offsets = json.load(open(offp)) if os.path.exists(offp) else {}
    base = [sys.executable, "-m", "yt_dlp", "-q", "--no-warnings"]
    if shutil.which("node"):
        base += ["--js-runtimes", "node"]
    fmt = f"bv*[height<={a.max_height}]+ba/b[height<={a.max_height}]/b"
    for c in clips:
        cid = int(c["id"])
        rs, re_ = max(0.0, c["start"] - a.pad), c["end"] + a.pad
        raw = f"{O}/src/clip{cid:02d}.mkv"
        if not os.path.exists(raw):
            subprocess.run(base + ["-f", fmt, "--merge-output-format", "mkv", "--download-sections",
                                   f"*{rs:.2f}-{re_:.2f}", "-o", f"src/clip{cid:02d}.%(ext)s", a.url],
                           cwd=O, check=True)
        dur = probe_dur(raw)
        guess = re_ - dur
        off, score = (guess, None)
        if wt is not None and len(wt):
            off, score = refine(guess, envelope(raw), wt)
            if abs(off - guess) > 1.5 or score < 0.1:   # weak match: trust the arithmetic
                off = guess
        offsets[str(cid)] = round(off, 3)
        ss = max(0.0, c["start"] - off)
        mez = f"{O}/mezz/clip{cid:02d}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{ss:.3f}", "-i", raw, "-t", f"{c['end'] - c['start']:.3f}",
                        "-c:v", "libx264", "-preset", "fast", "-crf", "12", "-g", "30", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "320k", "-ar", "48000", mez], check=True)
        print(f"clip{cid:02d}: offset {off:.2f} (guess {guess:.2f}, r={score if score is None else round(score, 2)}) "
              f"-> {mez} {probe_dur(mez):.2f}s", flush=True)
        json.dump(offsets, open(offp, "w"), indent=1)


if __name__ == "__main__":
    main()
