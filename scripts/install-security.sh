#!/usr/bin/env bash
#
# Install and enable this repo's security tooling. Idempotent.
#
#   ./scripts/install-security.sh          # install + enable the pre-commit hook
#   ./scripts/install-security.sh --check  # report state, change nothing
#
# Installs: gitleaks (secret scanning), pip-audit (known CVEs), the pre-commit
# hook, and the skill-integrity baseline. Patches any CVE it can fix without
# breaking a runtime, then leaves the rest for ./scripts/security-audit.sh to
# report.

set -euo pipefail

BIN="${AR_BIN:-$HOME/.local/bin}"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
GITLEAKS_VERSION="${GITLEAKS_VERSION:-8.30.0}"

log()  { printf '  %s\n' "$*"; }
step() { printf '\n== %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

if [ "${1:-}" = "--check" ]; then
  printf 'gitleaks    : %s\n' "$(have gitleaks && gitleaks version 2>/dev/null | head -1 || echo 'not installed')"
  printf 'pip-audit   : %s\n' "$(python3 -c 'import pip_audit' 2>/dev/null && echo present || echo 'not installed')"
  printf 'pre-commit  : %s\n' "$(cd "$REPO_DIR" && [ "$(git config core.hooksPath 2>/dev/null)" = ".githooks" ] && echo enabled || echo 'not enabled')"
  printf 'baseline    : %s\n' "$([ -f "$REPO_DIR/.security/skills.sha256" ] && echo "$(wc -l < "$REPO_DIR/.security/skills.sha256") skills" || echo 'not recorded')"
  exit 0
fi

mkdir -p "$BIN"

step "gitleaks (secret scanning)"
if have gitleaks; then
  log "already installed: $(gitleaks version 2>/dev/null | head -1)"
else
  tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
  url="https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz"
  if curl -sSLf -o "$tmp/gl.tgz" "$url" && tar xzf "$tmp/gl.tgz" -C "$tmp" gitleaks 2>/dev/null; then
    install -m 0755 "$tmp/gitleaks" "$BIN/gitleaks"
    log "installed: $("$BIN/gitleaks" version 2>/dev/null | head -1)"
  else
    log "WARNING: gitleaks install failed — secret scanning will be skipped"
  fi
fi

step "pip-audit (known CVEs)"
if python3 -c "import pip_audit" 2>/dev/null; then
  log "already installed"
else
  python3 -m pip install -q --ignore-installed pip-audit >/tmp/security-pip.log 2>&1 \
    && log "installed" || log "WARNING: pip-audit install failed — see /tmp/security-pip.log"
fi

# Patch the CVEs that were found in this container and are safe to bump. Pinned
# as floors, not exact versions, so a newer fixed release is accepted.
step "Patching known-vulnerable packages"
patched=0
for spec in "idna>=3.15" "pyjwt>=2.13.0" "setuptools>=83.0.0" "wheel>=0.46.2" "httplib2>=0.32.0"; do
  pkg="${spec%%>=*}"; floor="${spec##*>=}"
  cur="$(python3 -c "import importlib.metadata as m; print(m.version('$pkg'))" 2>/dev/null || echo "")"
  [ -z "$cur" ] && continue
  if [ "$(printf '%s\n%s\n' "$floor" "$cur" | sort -V | head -1)" != "$floor" ]; then
    python3 -m pip install -q --upgrade --force-reinstall "$spec" >>/tmp/security-pip.log 2>&1 \
      && patched=$((patched+1)) || log "WARNING: could not upgrade $pkg"
  fi
done
# Hermes pins its own aiohttp/cryptography; both had advisories. `hermes update`
# can revert this, which is why security-audit.sh re-checks rather than trusting
# that this ran once.
HV=/usr/local/lib/hermes-agent/venv/bin/python
if [ -x "$HV" ] && have uv; then
  for spec in "aiohttp>=3.14.3" "cryptography>=50.0.0"; do
    pkg="${spec%%>=*}"; floor="${spec##*>=}"
    cur="$("$HV" -c "import importlib.metadata as m; print(m.version('$pkg'))" 2>/dev/null || echo "")"
    [ -z "$cur" ] && continue
    if [ "$(printf '%s\n%s\n' "$floor" "$cur" | sort -V | head -1)" != "$floor" ]; then
      uv pip install --quiet --python "$HV" "$spec" >/dev/null 2>&1 \
        && patched=$((patched+1)) || log "WARNING: could not upgrade $pkg in the Hermes venv"
    fi
  done
fi
log "$patched package(s) upgraded"

step "Credential file permissions"
for f in "$HOME/.hermes/.env" "$HOME/.hermes/config.yaml" "$HOME/.hermes/state.db" \
         "$HOME/.agent-reach/config.yaml"; do
  [ -e "$f" ] || continue
  m="$(stat -c '%a' "$f")"
  case "$m" in 600|400) ;; *) chmod 600 "$f"; log "tightened $(basename "$f") $m -> 600" ;; esac
done
for d in "$HOME/.hermes" "$HOME/.agent-reach"; do
  [ -d "$d" ] || continue
  [ "$(stat -c '%a' "$d")" = "700" ] || { chmod 700 "$d"; log "tightened $(basename "$d")/ -> 700"; }
done
log "done"

step "Pre-commit secret scan"
cd "$REPO_DIR"
if [ "$(git config core.hooksPath 2>/dev/null)" = ".githooks" ]; then
  log "already enabled"
else
  git config core.hooksPath .githooks
  log "enabled (git config core.hooksPath .githooks)"
fi
chmod +x "$REPO_DIR/.githooks/pre-commit" 2>/dev/null || true

step "Skill integrity baseline"
if [ -f "$REPO_DIR/.security/skills.sha256" ]; then
  log "already recorded ($(wc -l < "$REPO_DIR/.security/skills.sha256") skills) — refresh with security-audit.sh --baseline"
else
  "$REPO_DIR/scripts/security-audit.sh" --baseline | sed 's/^/  /'
fi

step "Audit"
"$REPO_DIR/scripts/security-audit.sh" || true

cat <<'EOF'

Security tooling is installed and enabled.
  Full audit        : ./scripts/security-audit.sh
  Re-baseline skills: ./scripts/security-audit.sh --baseline
  What this does and does not cover: docs/security.md
EOF
