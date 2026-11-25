---
name: yt-shorts-studio
description: 'Turn any YouTube video (gameplay with facecam, podcasts, interviews, talking-head/vlog, tutorials/screen recordings, reactions, sports) into vertical 9:16 Shorts/Reels/TikToks: find the most engaging 30-60 s moments from the transcript, download only those segments, reframe with subject/face tracking and split-screen layouts, add word-by-word highlighted captions, build editable timelines live in FilmCraft (or render with ffmpeg), export at any resolution/fps, and produce designed thumbnails plus titles, descriptions, tags, hashtags and an upload checklist. Use this whenever the user shares a YouTube link and wants clips, shorts, reels, highlights, "viral moments", vertical edits, repurposed content, or titles/thumbnails/descriptions for clips — even if they only say "make shorts from this" or "cut this podcast into reels".'
---

# YouTube → Shorts Studio

Turns one long YouTube video into several finished vertical clips plus everything needed to
post them. The workflow has two hard stops for the user's approval (clip list, previews),
because choosing moments and judging the edit are their calls and re-rendering is slow.

Scripts live in `scripts/` next to this file (call them as `python <skill>/scripts/x.py`).
Read the reference files when you reach the step that needs them:
- `references/content-types.md`: picking moments and choosing a layout for each kind of video
- `references/filmcraft.md`: FilmCraft live bridge, setup, commands and quirks
- `references/publishing.md`: titles, descriptions, tags, thumbnails, upload checklists

## 0. Set up the job

Collect from the request (ask only for what's missing and matters):
- URL; platforms (default YouTube Shorts + Instagram Reels); clip length (default 30-60 s);
  output resolution and fps (default 1080x1920 at the source frame rate). 4K output from a
  1080p source is an upscale: say so before promising "4K".
- Make a workspace folder per video, e.g. `<user's video folder>/<slug>_Shorts/`. All scripts
  take this folder as OUTDIR. Keep scratch out of unrelated projects.
- Tools: `python -m yt_dlp` (install with `pip install --user -U yt-dlp` if missing), ffmpeg,
  ffprobe, numpy, opencv-python, Pillow. Node on PATH helps yt-dlp with YouTube's JS checks.

## 1. Analyse the whole video without downloading it

```
python scripts/fetch_source.py URL OUTDIR
```
This gets metadata and the word-timed transcript (creator captions preferred over auto). It
prints title, channel, duration, best height/fps, chapters and whether "most replayed" data
exists. If it exits 3 (no captions), ask before running `scripts/transcribe.py`: it needs
`pip install faster-whisper`, downloads a model and the audio track, and is slow on CPU.

Read `transcript.txt` end to end (it is small enough). The summary's `most_replayed_peaks`
lists YouTube's rewatch peaks, with the end-screen and autoplay edges already left out: moments
near a peak are strong candidates, but the transcript decides where a clip starts and ends.
Auto captions (`"kind": "auto"`) misspell names and show bleeped swears as `[ __ ]`. Note the
names you'll need to fix later with `captions.py --replace`. Work out the content type (see
`references/content-types.md`) and pick segments that each:
- open on a hook in the first 1-3 s (a question, a claim, a reaction, a number, "wait…"),
- contain one complete beat with a payoff (punchline, result, reveal) and end right after it,
- stand alone without the rest of the video, and land in the requested length.
Write the rough picks to `OUTDIR/candidates.json`
(`[{"id": 1, "title": "...", "tier": "top", "start": 297, "end": 357}, ...]`), then run
`python scripts/snap_clips.py OUTDIR [--min 30 --max 60]`. It moves each start and end to a
phrase boundary so nobody is cut mid-word, checks the lengths, and prints the table you'll show.

## 2. STOP: present the breakdown and wait

Show a table: #, working title (what happens), start-end (mm:ss), duration, plus a top-picks
tier and a backups tier, and the total count. Mention what you deliberately skipped (too short,
age-restricted material, spoilers) and any caveats (source resolution, rights). Ask how many and
which to make. Don't download anything until they answer. Then copy the approved entries to
`OUTDIR/clips.json` (same format). Every later script reads `clips.json`. Layout decisions
(facecam or not, one or two speakers) wait until step 4, because they need the actual frames.

## 3. Download only the approved segments

```
python scripts/download_segments.py URL OUTDIR [--ids 1,2,3] [--max-height 2160]
```
It downloads each section, works out where the file really starts (stream copies begin at the
keyframe before the request, so it checks the audio against the transcript), and writes
frame-accurate `mezz/clipNN.mp4`. If the user says "stop", stop the job right away and report
which clips finished.

## 4. Look before you frame

```
python scripts/analyze_frames.py OUTDIR clipNN
```
This writes contact sheets (1 frame/s, the plain centre 9:16 window outlined), scene-cut times,
face boxes, and suggested crop keyframes from face tracking. The suggestions give one steady
framing per camera shot, with a hard reframe on each cut; that is right for podcasts and
interviews. `review_shots` lists shots where faces were rarely found, so set those keys by hand
from a full-res frame. **Open the contact sheets and look at them.** They show what a crop would cut: facecams, second speakers, on-screen graphics, and
moments with no facecam. Then write `OUTDIR/specs/clipNN.json` (format in `scripts/layout.py`):

| What's on screen | Layout |
|---|---|
| Gameplay + creator facecam overlay | `split`: top = gameplay with `keys`, bottom = facecam `rect`; `fit_spans` where the facecam disappears |
| Two people side by side (podcast/interview) | `split`: top = speaker A `rect`, bottom = speaker B `rect` |
| One person / camera cuts between people | `crop` with `keys` from face tracking (jump on cuts, glide in shot) |
| Screen recording, slides, wide shots, on-screen text | `fit` (whole frame over a blurred fill), or `crop` with zoom on the area of interest |

Keyframes are `[seconds_from_clip_start, source_x_centre]`. Put two keys one frame apart at a
scene cut for a hard jump, further apart for a smooth pan. Check that nobody important is cut
in any tile. If a crop can't hold both subjects, use split or fit for that span instead of
cutting someone in half. Measure facecam/speaker rectangles on a full-resolution frame
(`ffmpeg -ss T -i mezz/clipNN.mp4 -frames:v 1 frame.png`) rather than guessing from tiles.

## 5. Captions

```
python scripts/captions.py OUTDIR [--y 1116] [--accent #FFD23F] [--font Rubik]
```
`--y` is the caption centre in 1080x1920 space: 1116 sits on the split seam, about 1290 suits
`crop` or `fit`. Captions must stay above the bottom 20% (platform UI) and off faces. The
default style is minimal and modern: 2-3 word chunks, white with an outline, the spoken word
in the accent colour, and a soft pop-in. Fonts must be installed (check `C:\Windows\Fonts`).
For auto captions, fix misheard names with `--replace "wemby=Wemmbu;chief=Chiefxd"`.
Fillers (uh, um…), laughter and bleeped words (`[ __ ]`) are dropped automatically.
Proofread before building: read each clip's chunks from `subs/clipNN.json` (the `words` of the
`first` events) and fix names, numbers and obvious mishearings. Captions are the most-read text
in the video.

## 6. Build the edit (FilmCraft first, ffmpeg fallback)

Check the bridge: `python scripts/fc.py status`.
- **Bridge up**: build an editable sequence live in the user's FilmCraft window:
  `python scripts/build_filmcraft.py OUTDIR specs/clipNN.json --canvas 1080x1920` (use the
  final aspect; a 2160x3840 canvas also exports fine at 1080). Captions become native, editable
  text clips. Read `references/filmcraft.md` first: one project is open at a time, so save the
  user's work before `file.newProject`.
- **Bridge down but FilmCraft installed**: offer to set it up (`fc.py setup`, then the user
  closes FilmCraft, then `fc.py launch <project>`). Don't kill the user's FilmCraft window
  yourself, since it may hold unsaved work.
- **No FilmCraft, or the user wants speed**: `python scripts/render_ffmpeg.py OUTDIR specs/clipNN.json out.mp4`.

## 7. STOP: previews

Render previews small (540x960) unless the user asked for a specific size: with FilmCraft use `fc.py export <seq> previews/x.mp4 1080 1920 <fps> --scale 0.5`;
with ffmpeg use `render_ffmpeg.py … --size 540x960 --crf 26 --preset veryfast`. Spot-check a
few frames yourself (`file.exportFrame` or ffmpeg). Share the previews: use your agent's file-sharing tool if it has one
(Claude apps: SendUserFile, where files over 30 MB don't reach phone/web viewers, so also send a compressed copy);
otherwise give the full file paths. Then wait for approval or
changes. Edits are cheap: change the spec or captions and rebuild.

## 8. Finals

Export at the requested size and fps once approved: `fc.py export <seq> finals/NAME.mp4 W H FPS --kbps 20000`
(use 45-60 Mbps for 4K) or `render_ffmpeg.py … --size WxH --fps F --crf 16`. Run long exports
in the background. If the user changes the target mid-render (e.g. 4K → 1080p), cancel the job
(`fc.py exec jobs.list` / `jobs.cancel`) rather than letting it finish. Verify each output with
ffprobe (size, fps, duration, audio) and look at one frame.

## 9. Thumbnails, titles, descriptions, upload checklist

Follow `references/publishing.md`. In short:
- Designed covers: render a caption-free layout still
  (`render_ffmpeg.py OUTDIR spec cover_raw.png --still T`), then
  `thumbnail.py --video cover_raw.png --time 0 --text "2-5 WORD *HOOK*" --out covers/NN.jpg`
  (1080x1920). The text goes automatically to whichever band (top or bottom) has no face;
  override with `--place`. Add a 1280x720 version from the 16:9 mezzanine if they also post long-form or
  want a YouTube thumbnail. Pick peak-moment frames: faces with emotion, the payoff in view.
- Write `publish_metadata.md` in the workspace with, per clip: title (≤100 chars, front-load
  the hook), alternate titles, YouTube description, Instagram caption, hashtags, tags, cover
  file and timestamp, pinned comment, alt text, and the shared settings. Describe only what is
  actually in the clip: re-check the transcript window before claiming a detail.
- The user uploads. Give them the step-by-step checklist from `references/publishing.md`
  and offer to review their upload screen if they share a screenshot.

## Ground rules

- Say clearly when footage belongs to someone else. Credit the source in every post and note
  that reposting can draw Content ID claims. Never impersonate the creator.
- Download only what was approved. Never download the whole video unless the user agrees
  (e.g. for a transcription fallback).
- Report honestly: upscaled resolution, frames you couldn't fix, captions you couldn't verify.
