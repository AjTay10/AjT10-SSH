#!/usr/bin/env bash
#
# Security audit for this workspace and the two agent runtimes installed in it.
#
# This is NOT a threat-intelligence feed. IOC feeds (MISP, OpenCTI, blocklists)
# answer "is this IP/hash known-bad", which is a question nothing here asks: this
# container has no inbound exposure and no network to defend. The real attack
# surface created by Agent Reach + reach + Hermes is different, and this audits
# that instead:
#
#   1. secrets  — a credential committed to git is the highest-severity, most
#                 common failure in a repo like this
#   2. deps     — known CVEs in the interpreters the skills and agents run on
#   3. perms    — credential files and agent state readable by other users
#   4. exposure — is an agent gateway listening on a port
#   5. skills   — 71 executable instruction files; detect drift from a baseline
#   6. injection— untrusted web/social/message content reaching the agent loop
#
#   ./scripts/security-audit.sh              # everything
#   ./scripts/security-audit.sh secrets deps # named checks
#   ./scripts/security-audit.sh --baseline   # re-record the skill baseline
#
# Exit codes: 0 clean (warnings allowed), 1 a finding needs action, 2 usage.

set -uo pipefail

export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
AR_HOME="${AR_HOME:-$HOME/.agent-reach}"
BASELINE="$REPO_DIR/.security/skills.sha256"
ALL_CHECKS=(secrets deps perms exposure skills injection)

pass=0; fail=0; warned=0
declare -a FAILED=() WARNED=()
ok()   { printf '  \033[32mOK  \033[0m  %-10s %s\n' "$1" "${2:-}"; pass=$((pass+1)); }
bad()  { printf '  \033[31mFAIL\033[0m  %-10s %s\n' "$1" "${2:-}"; fail=$((fail+1)); FAILED+=("$1"); }
warn() { printf '  \033[33mWARN\033[0m  %-10s %s\n' "$1" "${2:-}"; warned=$((warned+1)); WARNED+=("$1"); }

MODE=audit
ARGS=()
for a in "$@"; do
  case "$a" in
    --baseline) MODE=baseline ;;
    -h|--help)  sed -n '2,26p' "$0"; exit 0 ;;
    *)          ARGS+=("$a") ;;
  esac
done
SELECTED=("${ARGS[@]+"${ARGS[@]}"}")
for n in ${SELECTED+"${SELECTED[@]}"}; do
  known=0; for c in "${ALL_CHECKS[@]}"; do [ "$c" = "$n" ] && known=1 && break; done
  [ "$known" -eq 1 ] || { echo "unknown check: $n" >&2
                          echo "available: ${ALL_CHECKS[*]}" >&2; exit 2; }
done
want() { [ ${#SELECTED[@]} -eq 0 ] && return 0
         local s; for s in "${SELECTED[@]}"; do [ "$s" = "$1" ] && return 0; done; return 1; }

record_baseline() {
  mkdir -p "$(dirname "$BASELINE")"
  find "$HERMES_HOME/skills" -name 'SKILL.md' -print0 2>/dev/null \
    | sort -z | xargs -0 sha256sum 2>/dev/null \
    | sed "s|$HERMES_HOME/skills/||" > "$BASELINE"
  echo "recorded $(wc -l < "$BASELINE") skill hashes -> ${BASELINE#$REPO_DIR/}"
}

if [ "$MODE" = baseline ]; then record_baseline; exit 0; fi

printf '\nSecurity audit — workspace + agent runtimes\n'
printf '===========================================\n'

# --------------------------------------------------------------------- secrets
# Scans the working tree AND all history: a key removed in a later commit is
# still in the pack file and still compromised.
if want secrets; then
  if ! command -v gitleaks >/dev/null 2>&1; then
    warn secrets "gitleaks not installed — cannot scan for committed credentials"
  else
    out="$(cd "$REPO_DIR" && gitleaks detect --no-banner --redact --exit-code 9 2>&1)"
    rc=$?
    if [ "$rc" -eq 9 ]; then
      n="$(printf '%s' "$out" | grep -ci "^Finding:" || true)"
      bad secrets "$n potential credential(s) in the repo or its history — run: gitleaks detect -v"
    elif [ "$rc" -ne 0 ]; then
      warn secrets "gitleaks failed to run (exit $rc)"
    else
      ok secrets "no credentials in working tree or $(cd "$REPO_DIR" && git rev-list --count --all) commits of history"
    fi
  fi
fi

# ------------------------------------------------------------------------ deps
# Audits every interpreter that actually executes something here, not just the
# system one: a skill runs under python3, agent-reach under its venv, Hermes
# under its own.
if want deps; then
  auditor=""
  for p in "$HOME/.agent-reach-venv/bin/python" python3; do
    if "$p" -c "import pip_audit" 2>/dev/null; then auditor="$p"; break; fi
  done
  if [ -z "$auditor" ]; then
    warn deps "pip-audit not installed — cannot check for known CVEs"
  else
    total=0; detail=""
    for target in "system:" "agent-reach:$HOME/.agent-reach-venv/lib/python3.11/site-packages" \
                  "hermes:/usr/local/lib/hermes-agent/venv/lib/python3.11/site-packages"; do
      label="${target%%:*}"; path="${target#*:}"
      if [ -n "$path" ] && [ ! -d "$path" ]; then continue; fi
      if [ -z "$path" ]; then
        res="$(timeout 600 python3 -m pip_audit --progress-spinner off 2>/dev/null)"
      else
        res="$(timeout 600 "$auditor" -m pip_audit --progress-spinner off --path "$path" 2>/dev/null)"
      fi
      n="$(printf '%s' "$res" | grep -oE 'Found [0-9]+ known' | grep -oE '[0-9]+' | head -1)"
      n="${n:-0}"
      total=$((total + n))
      [ "$n" -gt 0 ] && detail="$detail $label=$n"
    done
    if [ "$total" -gt 0 ]; then
      bad deps "$total known vulnerabilit(ies):$detail — see docs/security.md"
    else
      ok deps "no known CVEs in system, agent-reach or hermes interpreters"
    fi
  fi
fi

# ----------------------------------------------------------------------- perms
# Anything holding a token, cookie or session must not be group/world readable.
if want perms; then
  problems=""
  for f in "$HERMES_HOME/.env" "$HERMES_HOME/config.yaml" "$HERMES_HOME/state.db" \
           "$AR_HOME/config.yaml"; do
    [ -e "$f" ] || continue
    m="$(stat -c '%a' "$f")"
    case "$m" in 600|400) ;; *) problems="$problems $(basename "$f")=$m" ;; esac
  done
  for d in "$HERMES_HOME" "$AR_HOME"; do
    [ -d "$d" ] || continue
    m="$(stat -c '%a' "$d")"
    [ "$m" = "700" ] || problems="$problems $(basename "$d")/=$m"
  done
  if [ -n "$problems" ]; then
    bad perms "world/group readable:$problems (fix: chmod 600 the file, 700 the dir)"
  else
    ok perms "agent state and credential files are owner-only"
  fi
fi

# -------------------------------------------------------------------- exposure
# An agent gateway bound to anything but loopback is remote code execution with
# extra steps. Report every listener so a new one is never a surprise.
if want exposure; then
  # Read /proc/net/tcp directly. `ss` and `netstat` are both absent from this
  # image, and the first version of this check piped their missing output into
  # awk, got nothing, and cheerfully reported "nothing listening" — a false
  # green over a socket bound to 0.0.0.0. If no enumeration method works, that
  # is a finding, never a pass.
  if [ ! -r /proc/net/tcp ]; then
    bad exposure "cannot enumerate listeners (/proc/net/tcp unreadable) — status unknown"
  else
    # state 0A = TCP_LISTEN. Address is little-endian hex; only the all-zeroes
    # and 0100007F (127.0.0.1) cases need distinguishing, so compare raw.
    listeners="$(awk 'NR>1 && $4=="0A" {split($2,a,":"); print a[1]" "a[2]}' \
                 /proc/net/tcp 2>/dev/null)"
    listeners6="$(awk 'NR>1 && $4=="0A" {split($2,a,":"); print a[1]" "a[2]}' \
                  /proc/net/tcp6 2>/dev/null)"
    all="$(printf '%s\n%s\n' "$listeners" "$listeners6" | grep -v '^$' || true)"
    external=""
    while read -r addr port; do
      [ -z "${addr:-}" ] && continue
      dec=$(( 16#$port ))
      case "$addr" in
        0100007F|0000000000000000FFFF00000100007F|00000000000000000000000001000000) ;;
        *) external="$external $dec" ;;
      esac
    done <<< "$all"
    # Ports owned by the Claude Code remote environment itself. They are bound
    # to 0.0.0.0 by the platform, not by anything in this repo, and lsof cannot
    # see their processes (different namespace). Reporting them as a hard
    # finding on every run would train the reader to ignore a red result — the
    # same reason the Hermes MCP probe was made non-flaky. They are still
    # surfaced, just attributed.
    PLATFORM_PORTS="${SECURITY_PLATFORM_PORTS:-2024 2025}"
    unowned=""; platform=""
    for p in $external; do
      case " $PLATFORM_PORTS " in
        *" $p "*) platform="$platform $p" ;;
        *)        unowned="$unowned $p" ;;
      esac
    done
    n="$(printf '%s' "$all" | grep -c . || true)"
    if [ -n "$unowned" ]; then
      bad exposure "listening on a non-loopback address, port(s):$unowned — bind to 127.0.0.1 or firewall it"
    elif [ -n "$platform" ]; then
      warn exposure "port(s)$platform bound to 0.0.0.0 by the Claude Code environment, not by this repo; nothing of ours is exposed"
    elif [ "$n" -gt 0 ]; then
      ok exposure "$n listener(s), all bound to loopback"
    else
      ok exposure "nothing listening on TCP"
    fi
  fi
fi

# ---------------------------------------------------------------------- skills
# Skills are executable instructions the agent follows. A modified skill is a
# code change with no diff review, so hash them and detect drift.
if want skills; then
  if [ ! -d "$HERMES_HOME/skills" ]; then
    warn skills "no Hermes skills directory"
  elif [ ! -f "$BASELINE" ]; then
    warn skills "no baseline — record one with: ./scripts/security-audit.sh --baseline"
  else
    cur="$(mktemp)"
    find "$HERMES_HOME/skills" -name 'SKILL.md' -print0 2>/dev/null \
      | sort -z | xargs -0 sha256sum 2>/dev/null \
      | sed "s|$HERMES_HOME/skills/||" > "$cur"
    changed="$(diff <(sort "$BASELINE") <(sort "$cur") 2>/dev/null | grep -cE '^[<>]' || true)"
    added="$(comm -13 <(awk '{print $2}' "$BASELINE" | sort) <(awk '{print $2}' "$cur" | sort) | wc -l)"
    removed="$(comm -23 <(awk '{print $2}' "$BASELINE" | sort) <(awk '{print $2}' "$cur" | sort) | wc -l)"
    rm -f "$cur"
    if [ "$changed" -gt 0 ]; then
      warn skills "$changed skill line(s) differ from baseline (+$added/-$removed) — review, then re-baseline"
    else
      ok skills "$(wc -l < "$BASELINE") skills match the recorded baseline"
    fi
  fi
fi

# ------------------------------------------------------------------- injection
# The genuinely novel risk here. `reach` pulls attacker-controlled text off 17
# platforms and Hermes relays messages from anyone who can reach a linked
# channel. Both land in an agent's context. There is no scanner for this — the
# control is a documented policy the agent follows, so assert it exists and is
# reachable rather than pretending to detect it.
if want injection; then
  missing=""
  grep -q "Untrusted content" "$REPO_DIR/CLAUDE.md" 2>/dev/null || missing="$missing CLAUDE.md"
  [ -f "$REPO_DIR/docs/security.md" ] || missing="$missing docs/security.md"
  grep -q "untrusted" "$REPO_DIR/.claude/skills/reach/SKILL.md" 2>/dev/null || missing="$missing reach/SKILL.md"
  if [ -n "$missing" ]; then
    bad injection "untrusted-content policy missing from:$missing"
  else
    linked="unknown"
    if command -v hermes >/dev/null 2>&1; then
      linked="$(timeout 60 hermes send --list 2>/dev/null | grep -c '^' || echo 0)"
    fi
    ok injection "policy present in CLAUDE.md, docs/security.md and the reach skill"
    if [ -f "$HERMES_HOME/channel_directory.json" ]; then
      warn injection "Hermes has linked channels — anyone who can message them can reach the agent; see docs/security.md"
    fi
  fi
fi

printf '\n-------------------------------------------\n'
if [ $((pass + warned + fail)) -eq 0 ]; then
  echo "no checks ran — refusing to report success" >&2; exit 2
fi
printf '%d ok, %d warning(s), %d finding(s)\n' "$pass" "$warned" "$fail"
[ ${#WARNED[@]} -gt 0 ] && printf 'warnings: %s\n' "${WARNED[*]}"
[ ${#FAILED[@]} -gt 0 ] && printf 'findings: %s\n' "${FAILED[*]}"
printf '\n'
[ "$fail" -eq 0 ]
