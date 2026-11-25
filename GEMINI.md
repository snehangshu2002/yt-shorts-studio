# AGENTS.md

This repository ships one agent skill: **yt-shorts-studio**, which turns any YouTube video into
vertical Shorts/Reels with captions, reframing, thumbnails and publishing copy.

## If you are an AI agent

- The skill lives in `skills/yt-shorts-studio/`. Its entry point is
  `skills/yt-shorts-studio/SKILL.md`, in the standard Agent Skills format (YAML front matter
  with `name` and `description`, then Markdown instructions). Claude Code, OpenAI Codex, Google
  Antigravity and other agents that support skills load it natively once it is installed (see
  README → Install).
- If your agent has no skill system, follow the same workflow by hand: read `SKILL.md`, then
  the file under `references/` that the current step mentions, and run the Python scripts in
  `scripts/` exactly as `SKILL.md` describes. Every script prints `--help`-style usage in its
  docstring.
- The workflow has two stops where the user decides: the clip list (step 2) and the previews
  (step 7). Don't skip them unless the user's message already makes that decision.
- Scripts depend only on Python 3.9+, ffmpeg/ffprobe, `yt-dlp`, `numpy`, `opencv-python` and
  `Pillow` (`requirements.txt`). FilmCraft is optional: `scripts/fc.py status` says whether
  it's reachable. Otherwise use `scripts/render_ffmpeg.py`.

## Working on this repo

- Change the skill only in `skills/yt-shorts-studio/`. Keep `SKILL.md` under ~500 lines;
  detail goes in `references/`.
- `tools/make_assets.py` regenerates `assets/` (logo, demo GIF).
- Test cases live in `skills/yt-shorts-studio/evals/` (prompt, expected outcome, graders).
