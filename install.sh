#!/usr/bin/env bash
# Install the yt-shorts-studio skill for every AI coding agent found on this machine.
#   ./install.sh                 auto-detect agents (always also installs to ~/.agents/skills)
#   ./install.sh --agent codex   one agent: claude | codex | antigravity | agents | all
#   ./install.sh --project DIR   install into a project instead (DIR/.agents/skills + DIR/.claude/skills)
#   ./install.sh --deps          also pip-install the Python dependencies
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/skills/yt-shorts-studio"
NAME="yt-shorts-studio"
AGENT="auto"; PROJECT=""; DEPS=0
while [ $# -gt 0 ]; do
  case "$1" in
    --agent) AGENT="$2"; shift 2 ;;
    --project) PROJECT="$2"; shift 2 ;;
    --deps) DEPS=1; shift ;;
    -h|--help) sed -n '2,7p' "$0"; exit 0 ;;
    *) echo "unknown option $1"; exit 2 ;;
  esac
done

targets=()
if [ -n "$PROJECT" ]; then
  targets+=("$PROJECT/.agents/skills" "$PROJECT/.claude/skills")
else
  add() { targets+=("$1"); }
  want() { [ "$AGENT" = "all" ] || [ "$AGENT" = "$1" ] || { [ "$AGENT" = "auto" ] && [ -d "$2" ]; }; }
  want claude "$HOME/.claude"        && add "$HOME/.claude/skills"
  want codex "$HOME/.codex"          && add "$HOME/.codex/skills"
  if want antigravity "$HOME/.gemini"; then
    add "$HOME/.gemini/config/skills"          # Antigravity (current docs)
    add "$HOME/.gemini/antigravity/skills"     # Antigravity (earlier releases)
  fi
  { [ "$AGENT" = "auto" ] || [ "$AGENT" = "all" ] || [ "$AGENT" = "agents" ] || [ "$AGENT" = "codex" ]; } \
    && add "$HOME/.agents/skills"            # shared location read by Codex and other agents
fi

for t in "${targets[@]}"; do
  mkdir -p "$t"
  rm -rf "${t:?}/$NAME"
  cp -R "$SRC" "$t/$NAME"
  rm -rf "$t/$NAME/scripts/__pycache__"
  echo "installed -> $t/$NAME"
done

if [ "$DEPS" = 1 ]; then
  python3 -m pip install --user -r "$HERE/requirements.txt"
fi
command -v ffmpeg >/dev/null || echo "note: ffmpeg not found on PATH (needed for cutting and rendering)"
echo "Restart your agent so it picks up the new skill."
