# FilmCraft: live editing through the bridge

FilmCraft is a Premiere-style editor. Its MCP server (`filmcraft`) and its CLI
(`filmcraft-cli`) drive it either **headless** (an invisible engine, so edits never appear in
the user's window) or **live** (`--bridge 127.0.0.1:PORT` to an app started with
`filmcraft --control PORT`, sharing a 64-hex `FILMCRAFT_CONTROL_TOKEN`).

How to tell which you have: the MCP `ui_inspect` tool errors with "this tool drives the live
app…" in headless mode. `python scripts/fc.py status` checks the bridge directly.

## Setup (once)
1. `python scripts/fc.py setup`: creates the token, port and a launcher in `~/.filmcraft_bridge/`.
   If Claude Code is installed, it also points the `filmcraft` MCP entry in `~/.claude.json` at
   the bridge (backing the file up first). For other agents it prints the MCP server snippet to
   add (Codex: `~/.codex/config.toml`; Antigravity/Gemini: their MCP settings). The MCP server is
   optional, since the scripts drive FilmCraft through the CLI bridge.
2. The user closes any FilmCraft window opened the normal way (it has no control port, and it
   may hold unsaved work, so don't kill it).
3. `python scripts/fc.py launch [project.fcproj]` starts FilmCraft with the control server.
4. An agent's MCP tools switch to live mode only after its FilmCraft MCP server restarts (Claude
   Code: `/mcp`, then Reconnect). Until then, use `fc.py exec/run`, which drive the live app straight
   away. That's also the efficient path for bulk work: a JSONL `run` script with hundreds of
   commands costs one call.

## Units and ids
- Time is in ticks: 254016000000 per second. Snap every time to the frame grid
  (`round(t*fps)*ticks_per_frame`) or adjacent clips collide ("V4 is not free here").
- Tracks: `track` index 0 = V1. `timeline.place` with `"audio": false` puts video only.
- `effects.setParam` takes `"effect": "motion"` or the effect's index. Effects added with
  `effects.apply` come after motion(0), opacity(1) and time_remap(2), so the first is index 3;
  read the index from the result.
- Motion: `position` is in sequence pixels, `anchor` in source pixels, `scale` in percent. To
  show source point (x, y) at canvas point P with scale s: anchor=(x, y), position=P.
- Keyframes: `effects.setParam … "time": ticks, "keyframe": true`. Two keys one frame apart
  give a hard jump.
- `timeline.razor` splits a clip and gives the right-hand part a new id, so run
  `sequence.inspect` afterwards to read the ids per track.

## Graphics (captions, gradients)
- `graphics.newText` → `graphics.set` (style) → `graphics.setCharStyle` (colour one word's
  character range). Commands without `"clip"` act on the graphic just created, so in a `run`
  script a failed `newText` would make the next lines restyle the previous caption. `fc.py run`
  stops at the first failure for this reason.
- Text `position` is the alignment point on the first baseline, so put it about 0.35 × font
  size below the visual centre you want.
- Shapes: `graphics.newShape` (rectangle); a gradient fill is `fill_kind: 1`,
  `gradient_angle: 90` (top→bottom), `gradient_start`/`gradient_end`. 8-digit colours must be
  **lowercase** (`#000000f0`); uppercase alpha is ignored.

## Projects
- One project is open at a time: `file.newProject` replaces it. Save first (`file.save`), and
  reopen the user's project afterwards (`file.open`).
- New projects have no path until `file.saveAs {"path": "…/name.fcproj"}` (forward slashes).
- Imported media keeps absolute paths, so keep mezzanine files where they are.

## Rendering
- `file.exportFrame {"path","format":"png","target":"program","sequence":id,"time":ticks}`:
  a single frame for checks (CLI `render` doesn't work in bridge mode).
- `file.exportMedia` (`fc.py export`): `width`/`height` set the frame, `scale` renders at a
  fraction (0.5 for previews), `fps` converts the rate (59.94 → 60 duplicates about one frame
  every 17 s; mention it). `bitrateMode` vbr2Pass + `bitrateKbps`. Jobs: `jobs.list`,
  `jobs.cancel {"job": id}`. A GT 730-class GPU renders 1080x1920 at about 9 fps, 4K slower.

## Useful command ids
file.newProject · file.open · file.save · file.saveAs · file.import · file.newSequence ·
timeline.place · timeline.razor · timeline.delete · timeline.move · effects.apply ·
effects.setParam · graphics.newText · graphics.set · graphics.setCharStyle · graphics.newShape ·
graphics.list · sequence.inspect · sequence.open · file.exportFrame · file.exportMedia ·
jobs.list · jobs.cancel. `filmcraft-cli commands <filter>` lists everything with params.
