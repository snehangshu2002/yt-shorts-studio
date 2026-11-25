# Content types: picking moments and framing them

Identify the type from the title, channel, description, and the first contact sheet. Many
videos mix types (a podcast with B-roll, gameplay with a cut-in interview), so choose the
layout per clip, and per span with `fit_spans` or several keys.

## Contents
1. Gameplay with facecam
2. Gameplay without facecam / pure game footage
3. Podcast or interview, two people in one shot
4. Podcast or interview with camera cuts / single talking head / vlog
5. Tutorial, screen recording, slides
6. Reactions, commentary over footage
7. Sports, events, highlights
8. Moment-picking checklist (all types)

---

## 1. Gameplay with facecam (e.g. creator groups playing GTA, Minecraft)
**Moments:** chaos with a payoff (heist goes wrong, a crash, a clutch), creator reactions
("NO WAY"), funny banter, first-look "wow" features, money/score reveals. Narration lines
("over the next few hours…") make good openers because they set context fast.
**What to check:** facecams are often keyed cutouts (no box), so they blend into the game. The
number of people on camera can change, and the facecam may vanish for zooms or graphics.
**Layout:** `split`, with gameplay on top (`keys`, full source height) and the facecam group
below (`rect` covering all faces plus some headroom; measure it on a full-res frame). Use
`fit_spans` where the facecam is missing or a wide graphic would be cut. Keep the gameplay
centre on the action: the player and the NPC or event they're dealing with, biased away from
the facecam so less of it repeats in the top panel. Add the seam gradient and put the captions
on the seam (`--y 1116`).
Measured example (1920x1080, MrBeast Gaming): group rect `[0, 470, 820, 610]`, gameplay
centre about 900-1120.

## 2. Gameplay without facecam
**Layout:** `crop` with keys following the character, vehicle or crosshair. Game characters
aren't reliable for face detection, so take keys from the contact sheets. HUD elements at the
edges get cut; that's fine unless one matters (a score or money counter). In that case use
`fit` for that span.

## 3. Podcast or interview, two people in one shot
**Moments:** a strong claim or story with a clear ending, a surprising number or fact, a
disagreement, advice framed as "the one thing…", emotional beats, a laugh after a setup. Start
on the question or claim, not on "so, um".
**Layout:** `split`, with speaker A's `rect` on top and speaker B's below (face plus shoulders,
eyes about 40% down each panel). Captions on the seam. If the show cuts to close-ups, use
`crop` keys for those spans.
**Tracking:** `analyze_frames.py` gives face boxes per 0.5 s. Take rect centres from the
median face position of each person.

## 4. Camera cuts between people / single talking head / vlog
**Layout:** `crop`. Start from `suggested_crop_keys` (largest face, dead zone so the frame
doesn't wobble, jumps on scene cuts). Then check them against the sheets: when two people are
in a wide shot and a crop can't hold both, add a `fit_spans` entry or use `split` for that
span. For a static single-camera talking head, a slight zoom (`"zoom": 1.1`, `center_y` at
the face) gives tighter framing.
Captions go at about 1290 (lower third, above the platform UI); move them higher if a lower
third or subtitle is burned into the source.

## 5. Tutorial, screen recording, slides
**Moments:** one tip that works on its own, a before/after, "most people get this wrong".
**Layout:** `fit` keeps everything readable over a blurred fill. When the action is in one
small area (a menu, a code line), use `crop` with `zoom` 1.5-2.5 and keys on that area. Text
must stay readable at phone size. Put captions where they don't hide the UI being shown.

## 6. Reactions / commentary over footage
Treat as #1: the reactor in one panel, the footage in the other. Fair-use risk is higher
because the underlying footage often belongs to a third party, so flag it.

## 7. Sports, events, highlights
**Moments:** build-up plus the decisive play, then the celebration. Keep the 2-3 s before the
play. **Layout:** `crop` following the ball or player (keys from sheets); `fit` for wide plays.
Rights restrictions are strict (leagues file claims aggressively), so tell the user.

## 8. Moment-picking checklist (all types)
- Hook within 1-3 s: a question, claim, reaction, number, conflict, or visual surprise.
- One beat, one payoff; end on the payoff or a beat after it, not mid-thought.
- Understandable without the rest of the video. If it needs setup, start earlier or skip it.
- 30-60 s by default; spoken content can stretch to 90 s when the user allows it.
- Spread picks across the video so they don't all come from the intro.
- Rank them: top picks (strong hook and payoff) and backups. Use "most replayed" peaks when
  available.
- Avoid: age-restricted content (nudity, blurred scenes), spoilers the creator asked to avoid,
  sponsor reads, and moments that only work with visuals the vertical frame can't show.
