#!/usr/bin/env bash
#
# Idempotent installer for Hermes Agent (https://github.com/NousResearch/hermes-agent)
# plus this repo's wiring: the reach-social skill and the Claude Code MCP
# registration.
#
#   ./scripts/install-hermes.sh            # install + wire
#   ./scripts/install-hermes.sh --check    # report state, change nothing
#   ./scripts/install-hermes.sh --wire-only  # skip the upstream install
#
# Deliberately does NOT run `hermes setup`: that wizard asks for a model
# provider credential, which is the user's to give. Everything this script
# installs works without one.
#
# Environment overrides:
#   HERMES_HOME        state dir (default ~/.hermes)
#   HERMES_INSTALLER   installer URL (default the official one)

set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_INSTALLER="${HERMES_INSTALLER:-https://hermes-agent.nousresearch.com/install.sh}"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

MODE="full"
for arg in "$@"; do
  case "$arg" in
    --check)     MODE="check" ;;
    --wire-only) MODE="wire" ;;
    -h|--help)   sed -n '2,18p' "$0"; exit 0 ;;
    *) echo "unknown flag: $arg" >&2; exit 2 ;;
  esac
done

log()  { printf '  %s\n' "$*"; }
step() { printf '\n== %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

if [ "$MODE" = "check" ]; then
  # `hermes --version` prints several lines; piping it into head kills it with
  # SIGPIPE, so the pipeline's status is non-zero even on success. Capture the
  # whole output first, then take a line — otherwise `||` fires and the report
  # claims "not installed" right under the version it just printed.
  if have hermes; then
    hermes_ver="$(hermes --version 2>/dev/null)"
    hermes_ver="${hermes_ver%%$'\n'*}"
  else
    hermes_ver="not installed"
  fi
  printf 'hermes      : %s\n' "${hermes_ver:-unknown}"
  printf 'state dir   : %s\n' "$([ -d "$HERMES_HOME" ] && echo "$HERMES_HOME" || echo 'absent')"
  printf 'reach skill : %s\n' "$([ -f "$HERMES_HOME/skills/social-media/reach-social/SKILL.md" ] && echo present || echo absent)"
  printf 'mcp config  : %s\n' "$([ -f "$REPO_DIR/.mcp.json" ] && echo present || echo absent)"
  printf 'model set   : %s\n' "$(grep -qE '^\s*(ANTHROPIC|OPENAI|OPENROUTER|NOUS)[A-Z_]*=.+' "$HERMES_HOME/.env" 2>/dev/null && echo yes || echo 'no — run: hermes setup --portal')"
  exit 0
fi

# Serialize with the session hook, which may call this concurrently.
LOCK="${TMPDIR:-/tmp}/hermes-install.lock"
if [ -z "${HERMES_LOCK_HELD:-}" ] && have flock; then
  export HERMES_LOCK_HELD=1
  exec flock "$LOCK" "$0" "$@"
fi

step "Hermes Agent installer (mode: $MODE)"

# ------------------------------------------------------------- 1. upstream
if [ "$MODE" != "wire" ]; then
  step "Hermes core"
  if have hermes; then
    log "already installed: $(hermes --version 2>/dev/null | head -1)"
  else
    # --skip-setup: never prompt for a credential during an automated install.
    # --skip-browser: this container already ships Chromium at
    #   $PLAYWRIGHT_BROWSERS_PATH; downloading another copy wastes ~300MB of a
    #   fixed disk allowance.
    log "downloading installer from $HERMES_INSTALLER"
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT
    if ! curl -sSLf -o "$tmp/install.sh" "$HERMES_INSTALLER"; then
      echo "  FATAL: could not download the Hermes installer" >&2
      exit 1
    fi
    # Refuse to pipe an empty or truncated download into bash.
    if [ "$(wc -c < "$tmp/install.sh")" -lt 10000 ] || ! head -1 "$tmp/install.sh" | grep -q '^#!'; then
      echo "  FATAL: downloaded installer looks wrong (truncated or not a script)" >&2
      exit 1
    fi
    log "running installer (skip-setup, skip-browser)"
    bash "$tmp/install.sh" --skip-setup --skip-browser --non-interactive >/tmp/hermes-install.log 2>&1 || {
      echo "  FATAL: Hermes install failed — see /tmp/hermes-install.log" >&2
      exit 1
    }
    hash -r
    log "installed: $(hermes --version 2>/dev/null | head -1)"
  fi
fi

if ! have hermes; then
  echo "  FATAL: hermes is not on PATH after install" >&2
  exit 1
fi

# ------------------------------------------------- 2. reach-social skill
# Hermes's own `web` toolset needs EXA/TAVILY/FIRECRAWL keys and `x_search`
# needs XAI_API_KEY. This skill routes it to the keyless `reach` CLI instead,
# giving Hermes the same 17-platform coverage the Claude session has.
step "reach-social skill"
SRC="$REPO_DIR/integrations/hermes/skills/social-media/reach-social/SKILL.md"
DST="$HERMES_HOME/skills/social-media/reach-social/SKILL.md"
if [ ! -f "$SRC" ]; then
  echo "  FATAL: $SRC is missing from the repo" >&2
  exit 1
fi
mkdir -p "$(dirname "$DST")"
if cmp -s "$SRC" "$DST"; then
  log "already current"
else
  cp "$SRC" "$DST"
  log "installed into $DST"
fi
if ! have reach; then
  log "WARNING: the reach CLI is not on PATH — run ./scripts/install-agent-reach.sh"
fi

# ------------------------------------------------- 3. skill prerequisites
# Hermes registers all 71 bundled skills as "enabled" regardless of whether
# their dependencies exist, so a skill fails on first import rather than at
# install time. These are every prerequisite that can be satisfied here without
# a user credential; ./scripts/hermes-skills-audit.py reports what is left.
# Installed into the system python3 on purpose — that is the interpreter a
# skill's `python script.py` actually runs, not any venv.
step "Skill prerequisites"
PY_PKGS="pyfiglet youtube-transcript-api defusedxml openpyxl pandas pypdf
         pdfplumber reportlab pdf2image pytesseract pymupdf pymupdf4llm
         python-docx python-pptx debugpy remote-pdb websocket-client nano-pdf
         semanticscholar arxiv habanero scipy numpy matplotlib SciencePlots
         pygount"
missing=""
for p in $PY_PKGS; do
  python3 -c "import importlib.metadata as m; m.distribution('$p')" 2>/dev/null || missing="$missing $p"
done
if [ -n "$missing" ]; then
  log "installing:$(echo "$missing" | tr '\n' ' ')"
  # --ignore-installed: the base image ships a Debian-managed `packaging` with
  # no RECORD file, which makes pip abort trying to uninstall it.
  # Status is captured directly: piping into `grep -v` under `set -o pipefail`
  # reports failure whenever grep filters every line away, which turned a
  # successful install into a spurious warning.
  if python3 -m pip install -q --ignore-installed $missing >/tmp/hermes-pip.log 2>&1; then
    log "installed $(echo "$missing" | wc -w) package(s)"
  else
    log "WARNING: some Python prerequisites failed — see /tmp/hermes-pip.log,"
    log "         then re-check with ./scripts/hermes-skills-audit.py"
  fi
else
  log "Python prerequisites already present"
fi

# pytesseract and pdf2image are thin wrappers; without these binaries they
# import fine and then fail at call time.
for pair in "tesseract:tesseract-ocr" "pdftoppm:poppler-utils"; do
  bin="${pair%%:*}"; pkg="${pair##*:}"
  if ! have "$bin"; then
    log "installing $pkg (provides $bin)"
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "$pkg" >/dev/null 2>&1 \
      || log "WARNING: could not install $pkg; OCR/PDF rasterising will not work"
  fi
done

# blogwatcher-cli (RSS/blog monitoring) needs no account, so it is worth having.
if ! have blogwatcher-cli; then
  log "installing blogwatcher-cli"
  curl -sL "https://github.com/JulienTant/blogwatcher-cli/releases/latest/download/blogwatcher-cli_linux_amd64.tar.gz" \
    | tar xz -C "$HOME/.local/bin" blogwatcher-cli 2>/dev/null || log "WARNING: blogwatcher-cli install failed"
fi
if ! have songsee && have go; then
  log "installing songsee (audio spectrograms)"
  GOBIN="$HOME/.local/bin" go install github.com/steipete/songsee/cmd/songsee@latest >/dev/null 2>&1 \
    || log "WARNING: songsee install failed"
fi
log "readiness: $("$REPO_DIR/scripts/hermes-skills-audit.py" --json 2>/dev/null | jq -r '"\(.counts.READY // 0)/\(.total) skills ready"' 2>/dev/null || echo 'run ./scripts/hermes-skills-audit.py')"

# ------------------------------------------------------ 4. MCP registration
step "Claude Code MCP registration"
if [ -f "$REPO_DIR/.mcp.json" ] && grep -q '"hermes"' "$REPO_DIR/.mcp.json"; then
  log "hermes present in .mcp.json"
else
  log "WARNING: .mcp.json does not register hermes — Claude Code will not see"
  log "         the messaging tools until it does"
fi

# ----------------------------------------------------------- 4. permissions
# ~/.hermes/.env holds provider credentials once the user runs `hermes setup`.
# Upstream creates it 0600; assert rather than assume, and never read it.
step "State directory permissions"
if [ -f "$HERMES_HOME/.env" ]; then
  mode="$(stat -c '%a' "$HERMES_HOME/.env")"
  if [ "$mode" != "600" ]; then
    chmod 600 "$HERMES_HOME/.env"
    log "tightened .env from $mode to 600"
  else
    log ".env is 600"
  fi
fi
chmod 700 "$HERMES_HOME" 2>/dev/null || true
log "$HERMES_HOME is $(stat -c '%a' "$HERMES_HOME")"

# `hermes doctor --fix` resolves the mechanical items (config migration, the
# ~/.local/bin symlink). It leaves credential and npm-audit items alone, which
# is why the fixed count is always short of the found count.
step "Health auto-fix"
timeout 300 hermes doctor --fix >/tmp/hermes-doctor-fix.log 2>&1 || true
grep -E "Fixed [0-9]+ issue|No issues" /tmp/hermes-doctor-fix.log | sed 's/^/  /' | head -2 || log "see /tmp/hermes-doctor-fix.log"

step "Status"
hermes status 2>&1 | sed 's/^/  /' | head -20 || true

cat <<EOF

Hermes Agent is installed and wired.
  Live check      : ./scripts/hermes-verify.sh
  Health          : hermes doctor
  Skills          : hermes skills list
  Claude Code MCP : .mcp.json -> hermes mcp serve

Not done, because it needs a credential only the user can give:
  hermes setup --portal     # model + web search + images + TTS + browser
  hermes setup              # or bring your own provider key
Without it, the MCP bridge, skills, cron scheduling and memory all work;
Hermes's own autonomous loop does not.
EOF
