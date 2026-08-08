#!/usr/bin/env bash
#
# Live verification for the Hermes Agent integration.
#
# `hermes doctor` reports on Hermes's own config. This script checks the things
# THIS repo is responsible for: that the CLI runs, that the MCP server actually
# completes a handshake and lists its tools (the surface Claude Code consumes),
# that our reach-social skill is discovered, and that credential files are not
# world-readable.
#
#   ./scripts/hermes-verify.sh          # all checks
#   ./scripts/hermes-verify.sh cli mcp  # named checks only
#
# Exit codes: 0 = all passed (degraded allowed), 1 = a check FAILED, 2 = usage.

set -uo pipefail

export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TIMEOUT="${HERMES_VERIFY_TIMEOUT:-180}"
# Every skill that can be made ready on this host has been. Dropping below this
# means dependencies were lost, not that upstream shipped a new skill.
SKILLS_READY_FLOOR="${SKILLS_READY_FLOOR:-53}"

ALL_CHECKS=(cli doctor mcp skill reach-skill skills-ready mcpconfig perms claudeskill)

pass=0; fail=0; degraded=0
declare -a FAILED=() DEGRADED=()
ok()   { printf '  \033[32mPASS\033[0m  %-12s %s\n' "$1" "${2:-}"; pass=$((pass+1)); }
bad()  { printf '  \033[31mFAIL\033[0m  %-12s %s\n' "$1" "${2:-}"; fail=$((fail+1)); FAILED+=("$1"); }
warn() { printf '  \033[33mDEGR\033[0m  %-12s %s\n' "$1" "${2:-}"; degraded=$((degraded+1)); DEGRADED+=("$1"); }

SELECTED=("$@")
for n in ${SELECTED+"${SELECTED[@]}"}; do
  known=0
  for c in "${ALL_CHECKS[@]}"; do [ "$c" = "$n" ] && known=1 && break; done
  [ "$known" -eq 1 ] || { echo "unknown check: $n" >&2
                          echo "available: ${ALL_CHECKS[*]}" >&2; exit 2; }
done
want() { [ ${#SELECTED[@]} -eq 0 ] && return 0
         local s; for s in "${SELECTED[@]}"; do [ "$s" = "$1" ] && return 0; done; return 1; }

for dep in jq timeout; do
  command -v "$dep" >/dev/null 2>&1 || { echo "missing required tool: $dep" >&2; exit 2; }
done

printf '\nHermes Agent — integration verification\n'
printf '=======================================\n'

# ----------------------------------------------------------------------- cli
if want cli; then
  if ! command -v hermes >/dev/null 2>&1; then
    bad cli "hermes not on PATH — run ./scripts/install-hermes.sh"
  else
    v="$(timeout "$TIMEOUT" hermes --version 2>&1 | head -1)"
    case "$v" in
      *"Hermes Agent"*) ok cli "$v" ;;
      *)                bad cli "unexpected --version output: ${v:-<none>}" ;;
    esac
  fi
fi

# -------------------------------------------------------------------- doctor
# Upstream's doctor exits non-zero for advisories we do not control (npm audit
# findings in its bundled workspaces, unconfigured optional providers). Assert
# it RUNS and produces a report; treat outstanding issues as degraded.
if want doctor; then
  out="$(timeout "$TIMEOUT" hermes doctor 2>&1)"
  if [ -z "$out" ]; then
    bad doctor "no output"
  elif ! printf '%s' "$out" | grep -q "Hermes"; then
    bad doctor "report did not render"
  else
    n="$(printf '%s' "$out" | grep -oE 'Found [0-9]+ issue' | grep -oE '[0-9]+' | head -1)"
    if [ -z "$n" ] || [ "$n" = "0" ]; then
      ok doctor "no outstanding issues"
    else
      warn doctor "$n advisory issue(s) — mostly upstream npm audit + unset optional keys"
    fi
  fi
fi

# ----------------------------------------------------------------------- mcp
# This is the contract Claude Code depends on. Drive a real stdio handshake and
# require the messaging tools to be listed.
if want mcp; then
  req='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"hermes-verify","version":"1"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
  # `hermes mcp serve` tears down as soon as stdin hits EOF and can lose the
  # tools/list write on the way out (BrokenPipeError in the MCP SDK's
  # stdout_writer) — roughly one run in three. A real client holds the pipe
  # open, so this only affects short probes like this one. Hold stdin open
  # briefly and retry rather than reporting a flaky FAIL.
  init=""; tools=""
  for _ in 1 2 3; do
    out="$({ printf '%s\n' "$req"; sleep 2; } | timeout "$TIMEOUT" hermes mcp serve 2>/dev/null)"
    init="$(printf '%s' "$out" | jq -rs 'map(select(.id == 1)) | .[0].result.serverInfo.name // empty' 2>/dev/null)"
    tools="$(printf '%s' "$out" | jq -rs 'map(select(.id == 2)) | .[0].result.tools // [] | map(.name) | join(",")' 2>/dev/null)"
    [ -n "$tools" ] && break
  done
  if [ -z "$init" ]; then
    bad mcp "initialize did not return a serverInfo"
  else
    missing=""
    for t in conversations_list messages_read messages_send events_poll channels_list; do
      case ",$tools," in *",$t,"*) ;; *) missing="$missing $t" ;; esac
    done
    n_tools="$(printf '%s' "$tools" | tr ',' '\n' | grep -c . || true)"
    if [ -n "$missing" ]; then
      bad mcp "server '$init' is missing tools:$missing"
    else
      ok mcp "server '$init' handshook, $n_tools tools exposed"
    fi
  fi
fi

# --------------------------------------------------------------- reach-skill
if want reach-skill; then
  f="$HERMES_HOME/skills/social-media/reach-social/SKILL.md"
  src="$REPO_DIR/integrations/hermes/skills/social-media/reach-social/SKILL.md"
  if [ ! -f "$f" ]; then
    bad reach-skill "not installed — run ./scripts/install-hermes.sh"
  elif ! cmp -s "$f" "$src"; then
    warn reach-skill "installed copy differs from the repo source"
  elif ! command -v reach >/dev/null 2>&1; then
    warn reach-skill "skill installed but the reach CLI is not on PATH"
  else
    ok reach-skill "installed and reach CLI present"
  fi
fi

# --------------------------------------------------------------------- skill
# Discovery is the thing that actually matters: a file on disk Hermes does not
# index is not a skill.
if want skill; then
  out="$(timeout "$TIMEOUT" hermes skills list 2>/dev/null)"
  if [ -z "$out" ]; then
    bad skill "hermes skills list produced no output"
  elif printf '%s' "$out" | grep -q "reach-social"; then
    n="$(printf '%s' "$out" | grep -cE '^│ [a-z0-9]' || true)"
    ok skill "reach-social discovered among $n skills"
  else
    bad skill "reach-social is on disk but not discovered by hermes"
  fi
fi

# ------------------------------------------------------------- skills-ready
# Guards against silent regression: a container rebuild that loses the pip
# packages would leave the skills registered and enabled but broken on first
# import, which is exactly the failure `hermes skills list` cannot see.
if want skills-ready; then
  audit="$REPO_DIR/scripts/hermes-skills-audit.py"
  if [ ! -x "$audit" ]; then
    bad skills-ready "scripts/hermes-skills-audit.py missing"
  else
    j="$(timeout "$TIMEOUT" "$audit" --json 2>/dev/null)"
    ready="$(printf '%s' "$j" | jq -r '.counts.READY // 0' 2>/dev/null)"
    total="$(printf '%s' "$j" | jq -r '.total // 0' 2>/dev/null)"
    if [ "${total:-0}" -eq 0 ] 2>/dev/null; then
      bad skills-ready "audit produced no report"
    elif [ "$ready" -lt "$SKILLS_READY_FLOOR" ] 2>/dev/null; then
      bad skills-ready "$ready/$total ready — expected at least $SKILLS_READY_FLOOR (dependencies lost?)"
    else
      blocked="$(printf '%s' "$j" | jq -r '[.counts | to_entries[]
                  | select(.key != "READY") | "\(.value) \(.key)"] | join(", ")' 2>/dev/null)"
      ok skills-ready "$ready/$total ready (${blocked:-none blocked})"
    fi
  fi
fi

# ----------------------------------------------------------------- mcpconfig
if want mcpconfig; then
  f="$REPO_DIR/.mcp.json"
  if [ ! -f "$f" ]; then
    bad mcpconfig ".mcp.json missing"
  elif ! jq -e '.mcpServers.hermes.command' "$f" >/dev/null 2>&1; then
    bad mcpconfig ".mcp.json does not register a hermes server"
  else
    cmd="$(jq -r '.mcpServers.hermes.command' "$f")"
    if command -v "$cmd" >/dev/null 2>&1; then
      ok mcpconfig "registers '$cmd $(jq -r '.mcpServers.hermes.args | join(" ")' "$f")'"
    else
      bad mcpconfig ".mcp.json points at '$cmd', which is not on PATH"
    fi
  fi
fi

# --------------------------------------------------------------------- perms
# ~/.hermes/.env holds provider credentials once the user runs `hermes setup`.
if want perms; then
  problems=""
  if [ -d "$HERMES_HOME" ]; then
    m="$(stat -c '%a' "$HERMES_HOME")"
    [ "$m" = "700" ] || problems="$problems dir=$m"
  fi
  if [ -f "$HERMES_HOME/.env" ]; then
    m="$(stat -c '%a' "$HERMES_HOME/.env")"
    [ "$m" = "600" ] || problems="$problems .env=$m"
  fi
  if [ -n "$problems" ]; then
    bad perms "credential paths are too permissive:$problems"
  else
    ok perms "$HERMES_HOME 700, .env 600"
  fi
fi

# ---------------------------------------------------------------- claudeskill
if want claudeskill; then
  f="$REPO_DIR/.claude/skills/hermes/SKILL.md"
  if [ ! -f "$f" ]; then
    bad claudeskill "project skill .claude/skills/hermes/SKILL.md missing"
  elif ! head -1 "$f" | grep -q -- '---' || ! grep -q '^name: hermes' "$f"; then
    bad claudeskill "SKILL.md frontmatter is malformed"
  else
    ok claudeskill "registered for Claude Code"
  fi
fi

printf '\n---------------------------------------\n'
if [ $((pass + degraded + fail)) -eq 0 ]; then
  echo "no checks ran — refusing to report success" >&2; exit 2
fi
printf '%d passed, %d degraded, %d failed\n' "$pass" "$degraded" "$fail"
[ ${#DEGRADED[@]} -gt 0 ] && printf 'degraded: %s\n' "${DEGRADED[*]}"
[ ${#FAILED[@]}   -gt 0 ] && printf 'failed  : %s\n' "${FAILED[*]}"
printf '\n'
[ "$fail" -eq 0 ]
