"""Fallback transcript when a video has no captions: faster-whisper with word timestamps.

Downloads the audio track only (no video), transcribes it, and writes the same files as
fetch_source.py (words.json, lines.json, transcript.txt). Needs `pip install faster-whisper`
and downloads a Whisper model on first use, so ask the user before running it.
CPU-only machines: "small.en" (~5-10x real time is slow; "base.en" is faster, less accurate).

Usage: python transcribe.py URL OUTDIR [--model small.en] [--language en]
"""
import argparse, json, os, shutil, subprocess, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("outdir")
    ap.add_argument("--model", default="small.en")
    ap.add_argument("--language", default=None)
    a = ap.parse_args()
    from faster_whisper import WhisperModel  # imported late so --help works without it

    os.makedirs(a.outdir, exist_ok=True)
    cmd = [sys.executable, "-m", "yt_dlp", "--no-warnings", "-f", "ba", "-x", "--audio-format", "wav",
           "--postprocessor-args", "ffmpeg:-ac 1 -ar 16000", "-o", "audio.%(ext)s", a.url]
    if shutil.which("node"):
        cmd[3:3] = ["--js-runtimes", "node"]
    subprocess.run(cmd, cwd=a.outdir, check=True)

    model = WhisperModel(a.model, device="auto", compute_type="int8")
    segs, info = model.transcribe(os.path.join(a.outdir, "audio.wav"), word_timestamps=True,
                                  language=a.language, vad_filter=True)
    words, lines = [], []
    for s in segs:
        ws = [w for w in (s.words or []) if w.word.strip()]
        lw = [[round(w.start, 3), w.word.strip()] for w in ws]
        words.extend(lw)
        if ws:
            lines.append([round(s.start, 3), round(s.end, 3), " ".join(x[1] for x in lw), lw])
        print(f"{s.start:7.1f}s {s.text.strip()[:80]}", flush=True)
    json.dump(words, open(os.path.join(a.outdir, "words.json"), "w", encoding="utf-8"))
    json.dump(lines, open(os.path.join(a.outdir, "lines.json"), "w", encoding="utf-8"))
    with open(os.path.join(a.outdir, "transcript.txt"), "w", encoding="utf-8") as f:
        for t0, t1, txt, _ in lines:
            f.write(f"{int(t0 // 60):02d}:{t0 % 60:04.1f} {txt}\n")
    print(f"done: {len(words)} words, language={info.language}")


if __name__ == "__main__":
    main()
