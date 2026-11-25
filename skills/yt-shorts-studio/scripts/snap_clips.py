"""Snap rough clip picks to natural speech boundaries and check their lengths.

Input  OUTDIR/candidates.json: [{"id", "title", "start", "end", "tier"?}, ...]  (rough seconds)
Output OUTDIR/candidates.json rewritten with snapped start/end + a printed table.

Start snaps to the first word of a phrase near the rough start (after a pause >= 0.45 s or
sentence punctuation), searching -4..+2 s. End snaps to just after the last word of a phrase
near the rough end (-4..+3 s), plus a 0.35 s tail so the last word isn't clipped. Clips are then
nudged to fit --min/--max. words.json only has word START times, so a word is treated as
ending where the next word starts (capped at 0.8 s).

Usage: python snap_clips.py OUTDIR [--min 30] [--max 60] [--file candidates.json]
"""
import argparse, json, re


def mmss(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--min", type=float, default=30)
    ap.add_argument("--max", type=float, default=60)
    ap.add_argument("--file", default="candidates.json")
    a = ap.parse_args()
    words = sorted(json.load(open(f"{a.outdir}/words.json", encoding="utf-8")), key=lambda w: w[0])
    ts = [w[0] for w in words]
    ends = [min(ts[i + 1], ts[i] + 0.8) if i + 1 < len(ts) else ts[i] + 0.6 for i in range(len(ts))]

    def phrase_start(i):
        return i == 0 or ts[i] - ends[i - 1] >= 0.45 or re.search(r"[.!?]$", words[i - 1][1])

    def phrase_end(i):
        return i == len(ts) - 1 or ts[i + 1] - ends[i] >= 0.45 or re.search(r"[.!?]$", words[i][1])

    def snap_start(t):
        cand = [i for i in range(len(ts)) if t - 4 <= ts[i] <= t + 2 and phrase_start(i)]
        if not cand:
            cand = [i for i in range(len(ts)) if t - 4 <= ts[i] <= t + 2] or [min(range(len(ts)), key=lambda i: abs(ts[i] - t))]
        i = min(cand, key=lambda i: abs(ts[i] - t))
        return max(0.0, ts[i] - 0.15)

    def snap_end(t):
        cand = [i for i in range(len(ts)) if t - 4 <= ends[i] <= t + 3 and phrase_end(i)]
        if not cand:
            cand = [min(range(len(ts)), key=lambda i: abs(ends[i] - t))]
        i = min(cand, key=lambda i: abs(ends[i] - t))
        return ends[i] + 0.35

    path = f"{a.outdir}/{a.file}"
    clips = json.load(open(path, encoding="utf-8"))
    rows = []
    for c in clips:
        s, e = snap_start(c["start"]), snap_end(c["end"])
        if e - s > a.max:
            e = snap_end(s + a.max - 2)
            if e - s > a.max:
                e = s + a.max
        if e - s < a.min:
            e = snap_end(s + a.min + 1)
        c["start"], c["end"] = round(s, 2), round(e, 2)
        flag = "" if a.min <= e - s <= a.max else "  <-- out of range"
        rows.append(f"{c['id']:>3}  {mmss(s):>8} - {mmss(e):<8} {e - s:5.1f}s  {c.get('tier', ''):<4} {c.get('title', '')}{flag}")
    json.dump(clips, open(path, "w", encoding="utf-8"), indent=1)
    print("\n".join(rows))


if __name__ == "__main__":
    main()
