#!/usr/bin/env bash
#
# SessionStart hook: make Agent Reach available to every Claude Code session
# in this repository.
#
# Fast path (already installed) is ~1s: it only re-exports PATH and prints a
# status line. The slow path runs the full installer, which the web container
# then caches.
set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
AR_BIN="$HOME/.local/bin"
AR_VENV="$HOME/.agent-reach-venv"

# Make agent-reach and the upstream CLIs (yt-dlp, gh, bili) visible to every
# Bash tool call for the rest of the session.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  printf 'export PATH="%s:$PATH"\n' "$AR_BIN" >> "$CLAUDE_ENV_FILE"
fi
export PATH="$AR_BIN:$PATH"

if [ ! -x "$AR_VENV/bin/agent-reach" ]; then
  echo "Agent Reach not present — installing (first run in this container)..."
  if ! bash "$PROJECT_DIR/scripts/install-agent-reach.sh" >/tmp/agent-reach-install.log 2>&1; then
    echo "Agent Reach install FAILED. Log: /tmp/agent-reach-install.log"
    echo "Re-run manually: ./scripts/install-agent-reach.sh"
    exit 0   # never block the session on this
  fi
fi

# The venv can survive while the skill directory does not (a stale container
# image, a manual `agent-reach skill --uninstall`). Re-register it rather than
# starting a session where Claude cannot see the routing table.
if [ ! -f "$HOME/.claude/skills/agent-reach/SKILL.md" ]; then
  "$AR_VENV/bin/agent-reach" skill --install >/dev/null 2>&1 \
    && echo "Re-registered the agent-reach skill."
fi

version="$("$AR_VENV/bin/agent-reach" --version 2>/dev/null || echo 'unknown')"

# Hermes Agent: installed separately because it is a ~90s install and a
# different upstream. Wire-only when the binary is already there, so a warm
# container pays only the skill/perms check.
hermes_line=""
if command -v hermes >/dev/null 2>&1; then
  bash "$PROJECT_DIR/scripts/install-hermes.sh" --wire-only >/tmp/hermes-wire.log 2>&1 || true
  hv="$(hermes --version 2>/dev/null)"; hv="${hv%%$'\n'*}"
  if grep -qE '^\s*[A-Z_]*(ANTHROPIC|OPENAI|OPENROUTER|NOUS)[A-Z_]*=.+' "$HOME/.hermes/.env" 2>/dev/null; then
    hermes_line="${hv} is installed; its MCP messaging tools are registered in .mcp.json."
  else
    hermes_line="${hv} is installed (MCP bridge, skills, cron, memory all work). Its own
agent loop needs a model provider — the user runs \`hermes setup --portal\`. Do not
run bare \`hermes\` or \`hermes -z\` until then."
  fi
elif [ -f "$PROJECT_DIR/scripts/install-hermes.sh" ]; then
  hermes_line="Hermes Agent is not installed — run ./scripts/install-hermes.sh (~90s)."
fi

# `agent-reach doctor` is a config check, not a reachability check, and it is
# wrong in both directions in this container: it calls `web` green even though
# Jina Reader 401s on our egress IP, and it will not call `exa` green because
# it refuses to start the remote MCP server. Correct both here rather than
# handing Claude a status line it cannot trust. Verified by
# scripts/agent-reach-verify.sh.
ok_list="$(timeout 60 "$AR_VENV/bin/agent-reach" doctor --json 2>/dev/null \
  | jq -r '[to_entries[] | select(.value.status == "ok") | .key
            | select(. != "web")] + ["exa"] | join(", ")' 2>/dev/null)"

echo "${version} is installed and on PATH. agent-reach channels: ${ok_list:-unknown}"
cat <<'EOF'
`reach` covers the social platforms and generic web reading: web, search, x,
reddit, bluesky, mastodon, telegram, tiktok, instagram, facebook, linkedin,
threads, pinterest, youtube, wikipedia, hn, stackoverflow. Use it instead of
hand-rolled scrapers, and instead of the agent-reach skill's own commands for
those platforms — `reach doctor` shows live status for all 17.

Two limits in this container:
  - Jina Reader (curl r.jina.ai) is IP-blocked with HTTP 401, so `agent-reach
    doctor` calling its web channel green is wrong. `reach web URL` routes
    around it.
  - The GitHub API is scoped to this session's repositories, so `gh search`
    and cross-repo endpoints 403. Prefer the mcp__github__* tools.
See CLAUDE.md for the routing table, and ./scripts/agent-reach-verify.sh for a
live end-to-end check.
EOF
[ -n "$hermes_line" ] && { echo; echo "$hermes_line"; }
exit 0
