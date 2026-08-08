#!/usr/bin/env bash
#
# Tests for the shell scripts' pure logic: argument handling, the guards that
# stop a run from reporting success it did not earn, and the path-traversal
# check in the skill bridge.
#
# Written against plain bash rather than bats so it runs in this container, in
# CI and on a developer machine with nothing installed. Only code paths that
# terminate before any network or runtime access are exercised, so the suite
# is fast and deterministic.
#
#   ./tests/bash/run.sh            # all
#   ./tests/bash/run.sh safe_name  # only matching test names

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FILTER="${1:-}"
pass=0; fail=0
declare -a FAILURES=()

# Keep the scripts away from the real Hermes/agent-reach state.
HERMES_HOME="$(mktemp -d)"; export HERMES_HOME
AR_HOME="$(mktemp -d)"; export AR_HOME
trap 'rm -rf "$HERMES_HOME" "$AR_HOME"' EXIT

check() {  # check <name> <expected-rc> <expected-substring> <cmd...>
  local name="$1" want_rc="$2" want_out="$3"; shift 3
  if [ -n "$FILTER" ] && [[ "$name" != *"$FILTER"* ]]; then return 0; fi
  local out rc
  out="$("$@" 2>&1)"; rc=$?
  local why=""
  # want_rc of "*" means "any exit code" — for checks that assert on output
  # alone, where the code legitimately varies with what is installed.
  [ "$want_rc" = "*" ] || [ "$rc" = "$want_rc" ] || why="exit $rc, wanted $want_rc"
  if [ -n "$want_out" ] && [[ "$out" != *"$want_out"* ]]; then
    why="${why:+$why; }output missing '$want_out'"
  fi
  if [ -z "$why" ]; then
    printf '  \033[32mPASS\033[0m  %s\n' "$name"; pass=$((pass+1))
  else
    printf '  \033[31mFAIL\033[0m  %s — %s\n' "$name" "$why"
    printf '        got: %s\n' "$(printf '%s' "$out" | head -3 | tr '\n' ' ')"
    fail=$((fail+1)); FAILURES+=("$name")
  fi
}

printf '\nShell script logic\n==================\n'

# ------------------------------------------------- unknown check names
# Silently running zero checks and exiting 0 would report a green build that
# verified nothing, so an unrecognised name must be a hard usage error.
for s in agent-reach-verify hermes-verify security-audit; do
  check "$s: unknown check exits 2" 2 "unknown check" \
    bash "$REPO/scripts/$s.sh" no-such-check
  check "$s: unknown check lists the real ones" 2 "available:" \
    bash "$REPO/scripts/$s.sh" no-such-check
done

# A valid name must NOT be rejected — otherwise the guard above would pass by
# rejecting everything. The check itself may pass or fail depending on what is
# installed; all that matters is that it ran.
check "agent-reach-verify: known check is accepted" "*" "cli" \
  bash "$REPO/scripts/agent-reach-verify.sh" cli

# --------------------------------------------------------------- --help
check "security-audit: --help exits 0" 0 "Security audit" \
  bash "$REPO/scripts/security-audit.sh" --help
check "install-agent-reach: --help exits 0" 0 "Idempotent installer" \
  bash "$REPO/scripts/install-agent-reach.sh" --help
check "hermes-sync-skills: no args prints usage" 0 "Skill bridge" \
  bash "$REPO/scripts/hermes-sync-skills.sh"
check "hermes-sync-skills: --help exits 0" 0 "Skill bridge" \
  bash "$REPO/scripts/hermes-sync-skills.sh" --help

# ------------------------------------------------------------ --check
# Read-only modes must not need the network or mutate anything.
check "install-agent-reach: --check exits 0" 0 "agent-reach" \
  bash "$REPO/scripts/install-agent-reach.sh" --check
check "install-security: --check exits 0" 0 "gitleaks" \
  bash "$REPO/scripts/install-security.sh" --check

# ---------------------------------------------------- path traversal
# `--to-hermes name ../../../tmp/evil` wrote outside the skills tree before the
# safe_name guard existed. These pin it.
for bad in "../../../tmp/evil" "../evil" ".." "." "a/b" 'a$(id)' 'a;id' "a b"; do
  check "hermes-sync-skills: safe_name rejects '$bad'" 1 "invalid" \
    bash "$REPO/scripts/hermes-sync-skills.sh" --to-hermes "$bad"
done
# An empty name is caught earlier, by the missing-argument check.
check "hermes-sync-skills: empty name is rejected" 1 "needs a skill name" \
  bash "$REPO/scripts/hermes-sync-skills.sh" --to-hermes ""
check "hermes-sync-skills: safe_name rejects a bad category" 1 "invalid" \
  bash "$REPO/scripts/hermes-sync-skills.sh" --to-hermes goodname "../../etc"

# A legal name must get past the guard and fail later, on the real lookup.
check "hermes-sync-skills: legal name passes the guard" 1 "no Claude Code skill" \
  bash "$REPO/scripts/hermes-sync-skills.sh" --to-hermes legal-name_1.0

check "hermes-sync-skills: unknown flag is rejected" 1 "unknown flag" \
  bash "$REPO/scripts/hermes-sync-skills.sh" --nope
check "hermes-sync-skills: --to-claude needs a name" 1 "needs a skill name" \
  bash "$REPO/scripts/hermes-sync-skills.sh" --to-claude
check "hermes-sync-skills: --list exits 0" 0 "" \
  bash "$REPO/scripts/hermes-sync-skills.sh" --list

# --------------------------------------------------- traversal is real
# Prove the guard actually prevents the write, not just prints a message.
traversal_is_blocked() {
  local victim="$HERMES_HOME/../pwned"
  rm -rf "$victim"
  bash "$REPO/scripts/hermes-sync-skills.sh" --to-hermes reach "../pwned" \
    >/dev/null 2>&1
  [ ! -e "$victim" ] || { echo "wrote to $victim"; return 1; }
  echo "no write outside the skills tree"
}
check "hermes-sync-skills: traversal writes nothing" 0 "no write" \
  traversal_is_blocked

# ------------------------------------------------------- syntax check
for f in "$REPO"/scripts/*.sh "$REPO"/.githooks/pre-commit \
         "$REPO"/.claude/hooks/session-start.sh "$REPO"/tests/bash/run.sh; do
  check "syntax: $(basename "$f")" 0 "" bash -n "$f"
done

# --------------------------------------------------------- shellcheck
# Optional locally, enforced in CI. Skipped rather than failed when absent so
# the suite still runs on a machine without it.
if command -v shellcheck >/dev/null 2>&1; then
  check "shellcheck: no warnings" 0 "" \
    shellcheck --severity=warning --exclude=SC1091,SC2181 \
      "$REPO"/scripts/*.sh "$REPO/.githooks/pre-commit" \
      "$REPO/.claude/hooks/session-start.sh" "$REPO/tests/bash/run.sh"
else
  printf '  \033[33mSKIP\033[0m  shellcheck: not installed (CI enforces it)\n'
fi

# ------------------------------------------------------ config sanity
check "mcp.json is valid JSON" 0 "" \
  python3 -c "import json;json.load(open('$REPO/.mcp.json'))"
check "settings.json is valid JSON" 0 "" \
  python3 -c "import json;json.load(open('$REPO/.claude/settings.json'))"

printf '\n------------------\n'
printf '%d passed, %d failed\n' "$pass" "$fail"
[ ${#FAILURES[@]} -gt 0 ] && printf 'failed: %s\n' "${FAILURES[*]}"
printf '\n'
[ "$fail" -eq 0 ]
