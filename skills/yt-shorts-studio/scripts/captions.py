"""Word-by-word highlighted captions for every clip in clips.json.

Input: OUTDIR/words.json + OUTDIR/clips.json (+ OUTDIR/src.*.json3 or lines.json for line grouping)
Output per clip:
  subs/clipNN.ass   libass script (PlayRes 1080x1920) for the ffmpeg renderer
  subs/clipNN.json  [{start, end, words[], active, first}] for the FilmCraft builder
Times are relative to the clip start.

Style: 2-3 word chunks, all words white with a dark outline and soft shadow, the word being
spoken in the accent colour, each chunk pops in (scale 86->100%). Laughter tokens ("hahaha")
are dropped; stretched words are capped ("WHOOOOOA" -> "WHOOOA").

Usage: python captions.py OUTDIR [--y 1116] [--accent #FFD23F] [--font Rubik] [--size 84]
                                 [--max-words 3] [--max-chars 16] [--case upper|asis] [--ids 1,2]
--y is the vertical centre in 1080x1920 space: ~1116 sits on a split-screen seam,
~1290 (67%) for full-frame layouts (clear of the Shorts/Reels bottom UI).
"""
import argparse, json, os, re

LAUGH = re.compile(r"(a?h+[aeiou]+h*|a+h+)+")


FILLERS = {"uh", "um", "uhh", "umm", "uhm", "er", "erm", "hmm", "mm", "mhm"}


def clean(w, case):
    w = w.replace("​", "").strip()
    core = re.sub(r"[^A-Za-z]", "", w).lower()
    if not core:
        return w if re.search(r"\d", w) else None
    if core in FILLERS:
        return None
    if (len(core) >= 3 and LAUGH.fullmatch(core)) or core in ("ha", "hah"):
        return None
    w = re.sub(r"(\w)\1{3,}", r"\1\1\1", w).replace("--", "").replace("…", "...")
    if w.startswith("[") and w.endswith("]"):   # [Music], [Applause]
        return None
    return w.upper() if case == "upper" else w


def ass_color(hexc):
    h = hexc.lstrip("#")
    return f"&H{h[4:6]}{h[2:4]}{h[0:2]}&".upper()


def ts(t):
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--y", type=int, default=1116)
    ap.add_argument("--accent", default="#FFD23F")
    ap.add_argument("--font", default="Rubik")
    ap.add_argument("--size", type=int, default=84)
    ap.add_argument("--max-words", type=int, default=3)
    ap.add_argument("--max-chars", type=int, default=16)
    ap.add_argument("--case", default="upper", choices=["upper", "asis"])
    ap.add_argument("--ids", default=None)
    ap.add_argument("--replace", default="",
                    help='fix auto-caption errors, e.g. "wemby=Wemmbu;siren had=Siren Head" (single words, case-insensitive)')
    a = ap.parse_args()
    fixes = {}
    for pair in filter(None, a.replace.split(";")):
        k, v = pair.split("=", 1)
        fixes[k.strip().lower()] = v.strip()
    O = a.outdir
    clips = json.load(open(f"{O}/clips.json", encoding="utf-8"))
    if a.ids:
        keep = {int(x) for x in a.ids.split(",")}
        clips = [c for c in clips if int(c["id"]) in keep]
    lines = json.load(open(f"{O}/lines.json", encoding="utf-8"))
    words = json.load(open(f"{O}/words.json", encoding="utf-8"))

    # per-line word lists with end times (a word ends where the next one starts)
    groups = []
    words.sort(key=lambda x: x[0])
    for li, ln in enumerate(lines):
        t0, t1 = ln[0], ln[1]
        if len(ln) > 3:
            ws = [list(w) for w in ln[3]]
        else:   # older lines.json without per-line words: assign by time window
            nxt_line = lines[li + 1][0] if li + 1 < len(lines) else t1 + 1
            ws = [list(w) for w in words if t0 - 1e-3 <= w[0] < max(t1, nxt_line) - 1e-3]
        cw = []
        for w in ws:
            m = re.match(r"^(\W*)(.*?)(\W*)$", w[1])
            if m and m.group(2).lower() in fixes:
                w[1] = m.group(1) + fixes[m.group(2).lower()] + m.group(3)
            c = clean(w[1], a.case)
            if c:
                cw.append([w[0], c])
        for i, w in enumerate(cw):
            w.append(cw[i + 1][0] if i + 1 < len(cw) else max(t1, w[0] + 0.25))
        if cw:
            groups.append(cw)

    def chunks_for(s, e):
        """Chunk only the words that fall inside this clip, so a caption line straddling the
        clip start or end neither loses its in-window words nor shows out-of-window ones."""
        out = []
        for ws in groups:
            ws = [w for w in ws if s - 0.05 <= w[0] < e - 0.12]
            cur = []
            for w in ws:
                txt = " ".join(x[1] for x in cur + [w])
                if cur and (len(cur) >= a.max_words or len(txt) > a.max_chars):
                    out.append(cur)
                    cur = []
                cur.append(w)
                if re.search(r"[.!?,]$", w[1]) and len(cur) >= 2:
                    out.append(cur)
                    cur = []
            if cur:
                out.append(cur)
        return sorted(out, key=lambda c: c[0][0])

    acc, white = ass_color(a.accent), "&HFFFFFF&"
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Word,{a.font},{a.size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H78000000,1,0,0,0,100,100,1,0,1,4.5,3,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    pos = f"\\pos(540,{a.y})"
    os.makedirs(f"{O}/subs", exist_ok=True)
    for c in clips:
        cid, s, e = int(c["id"]), c["start"], c["end"]
        sel = chunks_for(s, e)
        out_ass, out_json = [], []
        for k, ch in enumerate(sel):
            nxt = sel[k + 1][0][0] if k + 1 < len(sel) else e
            ch_end = min(nxt, max(ch[-1][2], ch[-1][0] + 0.35) + 0.25, e)
            for i, w in enumerate(ch):
                w_s = w[0]
                w_e = min(ch[i + 1][0] if i + 1 < len(ch) else ch_end, nxt)
                if w_e - w_s < 0.02:
                    continue
                parts = [f"{{\\c{acc if j == i else white}}}{x[1].replace('{', '(').replace('}', ')')}"
                         for j, x in enumerate(ch)]
                pop = r"\fscx86\fscy86\t(0,110,\fscx100\fscy100)" if i == 0 else ""
                out_ass.append(f"Dialogue: 0,{ts(w_s - s)},{ts(w_e - s)},Word,,0,0,0,,{{{pos}{pop}}}" + " ".join(parts))
                out_json.append({"start": round(w_s - s, 3), "end": round(w_e - s, 3),
                                 "words": [x[1] for x in ch], "active": i, "first": i == 0})
        open(f"{O}/subs/clip{cid:02d}.ass", "w", encoding="utf-8").write(header + "\n".join(out_ass) + "\n")
        json.dump({"y": a.y, "accent": a.accent, "font": a.font, "size": a.size, "events": out_json},
                  open(f"{O}/subs/clip{cid:02d}.json", "w", encoding="utf-8"), indent=0)
        print(f"clip{cid:02d}: {len(sel)} chunks, {len(out_json)} word states")


if __name__ == "__main__":
    main()
