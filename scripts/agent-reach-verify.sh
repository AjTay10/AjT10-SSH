#!/usr/bin/env bash
#
# Live end-to-end verification for Agent Reach.
#
# `agent-reach doctor` is a *configuration* check: several channels report
# green purely because a binary exists or a config key is present, without
# ever touching the network. This script actually calls each channel and
# asserts on the content that comes back, which is the only way to catch
# "installed but blocked" states (see the Jina Reader case in
# docs/agent-reach.md).
#
#   ./scripts/agent-reach-verify.sh          # run every check
#   ./scripts/agent-reach-verify.sh web rss  # run named checks only
#
# Exit codes: 0 = all checks passed (degraded allowed), 1 = a check FAILED.

set -uo pipefail

export PATH="$HOME/.local/bin:$PATH"
TIMEOUT="${AR_VERIFY_TIMEOUT:-60}"
PY="${AR_VENV:-$HOME/.agent-reach-venv}/bin/python"

pass=0; fail=0; degraded=0
declare -a FAILED=() DEGRADED=()

ok()   { printf '  \033[32mPASS\033[0m  %-12s %s\n' "$1" "${2:-}"; pass=$((pass+1)); }
bad()  { printf '  \033[31mFAIL\033[0m  %-12s %s\n' "$1" "${2:-}"; fail=$((fail+1)); FAILED+=("$1"); }
warn() { printf '  \033[33mDEGR\033[0m  %-12s %s\n' "$1" "${2:-}"; degraded=$((degraded+1)); DEGRADED+=("$1"); }

ALL_CHECKS=(cli doctor web rss v2ex youtube github exa bilibili skill platforms)

want() {  # want <name> -> 0 if this check should run
  local n="$1"
  [ ${#SELECTED[@]} -eq 0 ] && return 0
  local s; for s in "${SELECTED[@]}"; do [ "$s" = "$n" ] && return 0; done
  return 1
}

SELECTED=("$@")

# An unrecognised name must be a hard error. Silently running zero checks and
# exiting 0 would report a green build that verified nothing.
for want_name in ${SELECTED+"${SELECTED[@]}"}; do
  known=0
  for c in "${ALL_CHECKS[@]}"; do [ "$c" = "$want_name" ] && known=1 && break; done
  if [ "$known" -eq 0 ]; then
    echo "unknown check: $want_name" >&2
    echo "available: ${ALL_CHECKS[*]}" >&2
    exit 2
  fi
done

# The checks below parse JSON and enforce timeouts. Without these the script
# would report confusing per-channel failures instead of one clear message.
missing=""
for dep in curl jq timeout; do
  command -v "$dep" >/dev/null 2>&1 || missing="$missing $dep"
done
if [ -n "$missing" ]; then
  echo "missing required tool(s):$missing" >&2
  exit 2
fi

printf '\nAgent Reach — live channel verification\n'
printf '=======================================\n'

# ---------------------------------------------------------------- cli present
if want cli; then
  if ! command -v agent-reach >/dev/null 2>&1; then
    bad cli "agent-reach not on PATH — run ./scripts/install-agent-reach.sh"
  else
    v="$(agent-reach --version 2>&1)"
    case "$v" in
      *"Agent Reach v"*) ok cli "$v" ;;
      *)                 bad cli "unexpected --version output: $v" ;;
    esac
  fi
fi

# -------------------------------------------------------------- doctor --json
if want doctor; then
  out="$(timeout "$TIMEOUT" agent-reach doctor --json 2>/dev/null)"
  if [ -z "$out" ]; then
    bad doctor "no output"
  elif ! printf '%s' "$out" | jq -e 'type == "object" and length > 0' >/dev/null 2>&1; then
    bad doctor "output is not a JSON object"
  else
    n_ok="$(printf '%s' "$out" | jq '[.[] | select(.status == "ok")] | length')"
    n_all="$(printf '%s' "$out" | jq 'length')"
    n_err="$(printf '%s' "$out" | jq '[.[] | select(.status == "error")] | length')"
    if [ "$n_err" -gt 0 ]; then
      bad doctor "$n_err channel(s) raised an exception during check"
    else
      ok doctor "$n_ok/$n_all channels report ok, 0 errors"
    fi
  fi
fi

# ----------------------------------------------------------------------- web
# Jina Reader is the only backend agent-reach has for generic web pages, and
# it rejects datacenter IPs with HTTP 401. Degraded, not failed: the container
# still has WebFetch, which is what CLAUDE.md tells Claude to use instead.
if want web; then
  code="$(timeout "$TIMEOUT" curl -sS -o /tmp/ar-web.$$ -w '%{http_code}' \
          "https://r.jina.ai/https://example.com" 2>/dev/null)"
  body="$(head -c 400 /tmp/ar-web.$$ 2>/dev/null)"; rm -f /tmp/ar-web.$$
  case "$code" in
    200)
      if printf '%s' "$body" | grep -qi "example domain"; then
        ok web "Jina Reader returned page content"
      else
        warn web "HTTP 200 but content looks wrong: $(printf '%s' "$body" | head -c 80)"
      fi ;;
    401|403|429)
      warn web "Jina Reader HTTP $code from this egress IP — routed around by \`reach web\`" ;;
    *)
      bad web "Jina Reader HTTP ${code:-<none>}" ;;
  esac
fi

# ----------------------------------------------------------------------- rss
if want rss; then
  n="$(timeout "$TIMEOUT" "$PY" - <<'EOF' 2>/dev/null
import feedparser
print(len(feedparser.parse("https://hnrss.org/frontpage").entries))
EOF
)"
  if [ "${n:-0}" -gt 0 ] 2>/dev/null; then ok rss "$n entries parsed"; else bad rss "0 entries"; fi
fi

# ---------------------------------------------------------------------- v2ex
if want v2ex; then
  n="$(timeout "$TIMEOUT" curl -sS -H 'User-Agent: agent-reach/1.0' \
       "https://www.v2ex.com/api/topics/hot.json" 2>/dev/null \
       | jq 'if type == "array" then length else 0 end' 2>/dev/null)"
  if [ "${n:-0}" -gt 0 ] 2>/dev/null; then ok v2ex "$n hot topics"; else bad v2ex "no topics returned"; fi
fi

# ------------------------------------------------------------------- youtube
if want youtube; then
  if ! command -v yt-dlp >/dev/null 2>&1; then
    bad youtube "yt-dlp not on PATH"
  else
    id="$(timeout "$TIMEOUT" yt-dlp --skip-download --dump-json \
          "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 2>/dev/null | jq -r '.id // empty')"
    if [ "$id" = "dQw4w9WgXcQ" ]; then ok youtube "metadata extracted"; else bad youtube "no metadata (got '${id:-<empty>}')"; fi
  fi
fi

# -------------------------------------------------------------------- github
# In a Claude Code session the proxy scopes the GitHub API to the repositories
# attached to the session, so cross-repo search legitimately 403s. Verify
# against the current repo instead.
if want github; then
  if ! command -v gh >/dev/null 2>&1; then
    bad github "gh not on PATH"
  else
    slug="$(git -C "$(dirname "$0")/.." remote get-url origin 2>/dev/null \
            | sed -E 's#^.*[:/]([^/]+/[^/]+?)(\.git)?$#\1#')"
    slug="${slug:-cli/cli}"
    name="$(timeout "$TIMEOUT" gh api "repos/$slug" --jq .full_name 2>/dev/null)"
    if [ -n "$name" ]; then
      ok github "gh api reached $name"
    else
      warn github "gh cannot read repos/$slug — session GitHub scope or auth"
    fi
  fi
fi

# ----------------------------------------------------------------------- exa
if want exa; then
  if ! command -v mcporter >/dev/null 2>&1; then
    bad exa "mcporter not on PATH"
  else
    out="$(timeout "$TIMEOUT" mcporter call exa.web_search_exa query="anthropic claude" numResults=2 2>/dev/null)"
    if [ "$(printf '%s' "$out" | wc -c)" -gt 100 ] && printf '%s' "$out" | grep -qi "http"; then
      ok exa "search returned $(printf '%s' "$out" | wc -l) lines"
    else
      bad exa "empty or unusable response"
    fi
  fi
fi

# ------------------------------------------------------------------ bilibili
if want bilibili; then
  if ! command -v bili >/dev/null 2>&1; then
    warn bilibili "bili-cli not installed (optional channel)"
  else
    out="$(timeout "$TIMEOUT" bili search "python" --type video 2>/dev/null)"
    if printf '%s' "$out" | grep -q '^ok: true'; then
      ok bilibili "search returned results"
    else
      bad bilibili "search failed"
    fi
  fi
fi

# ------------------------------------------------------------------ platforms
# `reach doctor` probes all 31 social/web platforms live. Treat a majority as
# the pass bar: individual platforms degrade (a login wall appears, a cached
# page expires) without the integration being broken, but a collapse means the
# egress IP or a shared backend died.
if want platforms; then
  if ! command -v reach >/dev/null 2>&1; then
    bad platforms "reach not on PATH — run ./scripts/install-agent-reach.sh"
  else
    out="$(timeout 300 reach doctor --json 2>/dev/null)"
    n_ok="$(printf '%s' "$out" | jq -r '.ok // 0' 2>/dev/null)"
    n_all="$(printf '%s' "$out" | jq -r '.total // 0' 2>/dev/null)"
    down="$(printf '%s' "$out" | jq -r '[.results | to_entries[]
             | select(.value.status != "ok") | .key] | join(", ")' 2>/dev/null)"
    if [ "${n_all:-0}" -eq 0 ] 2>/dev/null; then
      bad platforms "reach doctor produced no usable report"
    elif [ "$n_ok" -eq "$n_all" ]; then
      ok platforms "$n_ok/$n_all platforms reachable"
    elif [ "$n_ok" -ge $(( (n_all * 2 + 2) / 3 )) ] 2>/dev/null; then
      warn platforms "$n_ok/$n_all reachable — down: ${down:-unknown}"
    else
      bad platforms "only $n_ok/$n_all reachable — down: ${down:-unknown}"
    fi
  fi
fi

# ---------------------------------------------------------------------- skill
if want skill; then
  s="$HOME/.claude/skills/agent-reach/SKILL.md"
  if [ ! -f "$s" ]; then
    bad skill "SKILL.md missing — run: agent-reach skill --install"
  elif ! head -1 "$s" | grep -q -- '---'; then
    bad skill "SKILL.md has no YAML frontmatter"
  elif ! grep -q '^name: agent-reach' "$s"; then
    bad skill "SKILL.md frontmatter has no matching name"
  else
    refs="$(find "$HOME/.claude/skills/agent-reach/references" -name '*.md' 2>/dev/null | wc -l)"
    proj="$(dirname "$0")/../.claude/skills/reach/SKILL.md"
    if [ ! -f "$proj" ]; then
      bad skill "project skill .claude/skills/reach/SKILL.md is missing"
    else
      ok skill "agent-reach ($refs refs) + reach both registered"
    fi
  fi
fi

printf '\n---------------------------------------\n'
if [ $((pass + degraded + fail)) -eq 0 ]; then
  echo "no checks ran — refusing to report success" >&2
  exit 2
fi
printf '%d passed, %d degraded, %d failed\n' "$pass" "$degraded" "$fail"
[ ${#DEGRADED[@]} -gt 0 ] && printf 'degraded: %s\n' "${DEGRADED[*]}"
[ ${#FAILED[@]}   -gt 0 ] && printf 'failed  : %s\n' "${FAILED[*]}"
printf '\n'
[ "$fail" -eq 0 ]
