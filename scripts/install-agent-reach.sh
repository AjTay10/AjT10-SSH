#!/usr/bin/env bash
#
# Idempotent installer for Agent Reach (https://github.com/Panniantong/Agent-Reach)
# in a Claude Code container.
#
# Safe to re-run: every step checks before it acts, and nothing outside
# $AR_VENV, $AR_BIN and ~/.agent-reach is touched.
#
#   ./scripts/install-agent-reach.sh              # full install (core + bilibili)
#   ./scripts/install-agent-reach.sh --core-only  # skip optional channels
#   ./scripts/install-agent-reach.sh --check      # report state, change nothing
#
# Environment overrides:
#   AGENT_REACH_REF   git ref/zip to install from (default: main)
#   GH_CLI_VERSION    gh release to install when gh is missing (default: 2.95.0)
#   AR_VENV           venv location (default: ~/.agent-reach-venv)
#   AR_BIN            where CLI shims are linked (default: ~/.local/bin)

set -euo pipefail

AR_VENV="${AR_VENV:-$HOME/.agent-reach-venv}"
AR_BIN="${AR_BIN:-$HOME/.local/bin}"
AGENT_REACH_REF="${AGENT_REACH_REF:-main}"
GH_CLI_VERSION="${GH_CLI_VERSION:-2.95.0}"
# Two install sources, tried in order. Upstream's docs recommend the archive
# zip, but Claude Code's egress proxy answers 403 on GitHub's codeload/archive
# endpoint while allowing plain git-over-HTTPS, so git+https goes first.
AGENT_REACH_GIT="git+https://github.com/Panniantong/agent-reach.git@${AGENT_REACH_REF}"
AGENT_REACH_ZIP="https://github.com/Panniantong/agent-reach/archive/${AGENT_REACH_REF}.zip"

MODE="full"
for arg in "$@"; do
  case "$arg" in
    --core-only) MODE="core" ;;
    --check)     MODE="check" ;;
    -h|--help)   sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown flag: $arg" >&2; exit 2 ;;
  esac
done

log()  { printf '  %s\n' "$*"; }
step() { printf '\n== %s\n' "$*"; }

have() { command -v "$1" >/dev/null 2>&1; }

# ---------------------------------------------------------------- check mode
if [ "$MODE" = "check" ]; then
  printf 'agent-reach : %s\n' "$( [ -x "$AR_VENV/bin/agent-reach" ] && "$AR_VENV/bin/agent-reach" --version || echo 'not installed')"
  for t in agent-reach yt-dlp gh mcporter bili; do
    printf '%-11s: %s\n' "$t" "$(command -v "$t" || echo 'not on PATH')"
  done
  exit 0
fi

# Serialize concurrent runs. The SessionStart hook calls this script, so a user
# running it by hand at the same time would otherwise race pip inside the same
# venv and the loser would abort with a spurious FATAL.
LOCK="${TMPDIR:-/tmp}/agent-reach-install.lock"
if [ -z "${AR_LOCK_HELD:-}" ] && command -v flock >/dev/null 2>&1; then
  export AR_LOCK_HELD=1
  exec flock "$LOCK" "$0" "$@"
fi

step "Agent Reach installer (mode: $MODE)"
log "venv : $AR_VENV"
log "bin  : $AR_BIN"
mkdir -p "$AR_BIN"

# ------------------------------------------------------- 1. agent-reach core
step "Python package"
if [ ! -x "$AR_VENV/bin/python" ]; then
  log "creating venv"
  python3 -m venv "$AR_VENV"
  "$AR_VENV/bin/pip" install --quiet --upgrade pip
fi
if [ -x "$AR_VENV/bin/agent-reach" ]; then
  log "already installed: $("$AR_VENV/bin/agent-reach" --version)"
else
  installed=0
  for src in "$AGENT_REACH_GIT" "$AGENT_REACH_ZIP"; do
    log "installing agent-reach from $src"
    if "$AR_VENV/bin/pip" install --quiet "$src"; then installed=1; break; fi
    log "source failed, trying next"
  done
  if [ "$installed" -ne 1 ]; then
    echo "  FATAL: could not install agent-reach from any source" >&2
    exit 1
  fi
  log "installed: $("$AR_VENV/bin/agent-reach" --version)"
fi

# agent-reach bundles yt-dlp; both need to be on PATH for the YouTube channel
# to be detected by `agent-reach doctor`.
ln -sf "$AR_VENV/bin/agent-reach" "$AR_BIN/agent-reach"
[ -x "$AR_VENV/bin/yt-dlp" ] && ln -sf "$AR_VENV/bin/yt-dlp" "$AR_BIN/yt-dlp"
log "linked agent-reach + yt-dlp into $AR_BIN"

# ------------------------------------------------------------- 2. gh CLI
step "GitHub CLI"
if have gh; then
  log "already installed: $(gh --version | head -1)"
else
  # The GitHub REST API is not reachable from every container (session-scoped
  # proxies block /repos/cli/cli), so pin a version instead of querying
  # /releases/latest, and verify the download against the published checksum.
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  tarball="gh_${GH_CLI_VERSION}_linux_amd64.tar.gz"
  base="https://github.com/cli/cli/releases/download/v${GH_CLI_VERSION}"
  log "downloading $tarball"
  curl -sSLf -o "$tmp/$tarball" "$base/$tarball"
  if curl -sSLf -o "$tmp/checksums.txt" "$base/gh_${GH_CLI_VERSION}_checksums.txt"; then
    expected="$(awk -v f="$tarball" '$2 == f {print $1}' "$tmp/checksums.txt")"
    actual="$(sha256sum "$tmp/$tarball" | awk '{print $1}')"
    if [ -z "$expected" ]; then
      log "WARNING: no checksum entry for $tarball; skipping verification"
    elif [ "$expected" != "$actual" ]; then
      echo "  FATAL: checksum mismatch for $tarball" >&2
      echo "    expected $expected" >&2
      echo "    actual   $actual" >&2
      exit 1
    else
      log "checksum verified"
    fi
  else
    log "WARNING: checksum file unavailable; skipping verification"
  fi
  tar xzf "$tmp/$tarball" -C "$tmp"
  install -m 0755 "$tmp/gh_${GH_CLI_VERSION}_linux_amd64/bin/gh" "$AR_BIN/gh"
  log "installed: $("$AR_BIN/gh" --version | head -1)"
fi

# ------------------------------------------------------------- 3. mcporter
step "mcporter (MCP bridge for Exa search)"
if have mcporter; then
  log "already installed: mcporter $(mcporter --version 2>/dev/null | head -1)"
elif have npm; then
  log "installing via npm"
  npm install -g mcporter >/dev/null 2>&1
  log "installed: mcporter $(mcporter --version 2>/dev/null | head -1)"
else
  log "WARNING: npm unavailable; Exa semantic search will stay offline"
fi

# ------------------------------------------- 4. agent-reach's own install pass
# Wires yt-dlp's JS runtime, registers Exa with mcporter, and installs the
# skill into ~/.claude/skills/agent-reach.
export PATH="$AR_BIN:$PATH"
step "agent-reach install --system"
if [ "$MODE" = "core" ]; then
  agent-reach install --env=auto --system >/dev/null
else
  agent-reach install --env=auto --system --channels=bilibili >/dev/null
fi
log "done"

# The other optional channels (twitter, reddit, xiaohongshu, facebook,
# instagram, xueqiu, xiaoyuzhou, linkedin) all need either a browser session or
# a user-supplied credential, so they are deliberately NOT installed here.
# See docs/agent-reach.md for how to enable them.

# ------------------------------------------- 5. reach (platform coverage layer)
step "reach — social platform + web reader layer"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
# BeautifulSoup gives the HTML reader correct extraction; reach falls back to a
# regex stripper without it, so a failed install degrades rather than breaks.
"$AR_VENV/bin/pip" install --quiet beautifulsoup4 || log "WARNING: bs4 unavailable, using the regex HTML fallback"
cat > "$AR_BIN/reach" <<EOF
#!/usr/bin/env bash
# Generated by install-agent-reach.sh — edit scripts/reach.py, not this shim.
REACH_PY="\${REACH_PY:-$REPO_DIR/scripts/reach.py}"
if [ ! -f "\$REACH_PY" ]; then
  echo "reach: \$REACH_PY is missing (repo moved?). Re-run install-agent-reach.sh." >&2
  exit 127
fi
exec "$AR_VENV/bin/python" "\$REACH_PY" "\$@"
EOF
chmod +x "$AR_BIN/reach"
log "installed: $("$AR_BIN/reach" --version)"

step "Skill registration"
agent-reach skill --install 2>&1 | sed 's/^/  /'

step "Status"
agent-reach doctor 2>&1 | sed 's/^/  /'

cat <<EOF

Agent Reach is installed.
  Platform status       : reach doctor      (31 platforms, live probes)
  Channel status        : agent-reach doctor (config only — see docs/agent-reach.md)
  Live end-to-end check : ./scripts/agent-reach-verify.sh
  Skills                : ~/.claude/skills/agent-reach/ and .claude/skills/reach/
EOF
