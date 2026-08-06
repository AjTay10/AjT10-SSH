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

# `agent-reach doctor` is a config check, not a reachability check, and it is
# wrong in both directions in this container: it calls `web` green even though
# Jina Reader 401s on our egress IP, and it will not call `exa` green because
# it refuses to start the remote MCP server. Correct both here rather than
# handing Claude a status line it cannot trust. Verified by
# scripts/agent-reach-verify.sh.
ok_list="$(timeout 60 "$AR_VENV/bin/agent-reach" doctor --json 2>/dev/null \
  | jq -r '[to_entries[] | select(.value.status == "ok") | .key
            | select(. != "web")] + ["exa"] | join(", ")' 2>/dev/null)"

echo "${version} is installed and on PATH."
[ -n "$ok_list" ] && echo "Working channels: ${ok_list}"
cat <<'EOF'
Use these instead of hand-rolled scrapers. Two limits in this container:
  - Generic web pages: Jina Reader (curl r.jina.ai) is IP-blocked with HTTP
    401, so use the WebFetch tool. `agent-reach doctor` reports this channel
    green anyway; do not believe it.
  - GitHub: the API is scoped to this session's repositories, so `gh search`
    and cross-repo endpoints 403. Prefer the mcp__github__* tools.
See CLAUDE.md for the full routing table, and run
./scripts/agent-reach-verify.sh for a live end-to-end check.
EOF
exit 0
