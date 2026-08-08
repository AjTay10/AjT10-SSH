#!/usr/bin/env bash
#
# Skill bridge between Hermes Agent and Claude Code.
#
# Both runtimes read the same `SKILL.md` format (the agentskills.io convention),
# so a skill written for one can be read by the other. This script makes that
# explicit instead of leaving it as a coincidence.
#
#   ./scripts/hermes-sync-skills.sh --list                 # what each side has
#   ./scripts/hermes-sync-skills.sh --to-claude NAME       # Hermes -> Claude Code
#   ./scripts/hermes-sync-skills.sh --to-hermes NAME [CAT] # Claude Code -> Hermes
#   ./scripts/hermes-sync-skills.sh --dry-run --to-claude NAME
#
# Copies are one-directional and explicit: nothing is synced automatically,
# because silently mirroring 70+ Hermes skills into Claude Code would flood the
# skill list and change which skill wins a trigger.

set -euo pipefail

HERMES_SKILLS="${HERMES_HOME:-$HOME/.hermes}/skills"
CLAUDE_SKILLS="$HOME/.claude/skills"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DRY_RUN=false

die() { echo "hermes-sync-skills: $*" >&2; exit 1; }

# Skill and category names become path components, so anything containing a
# slash or a dot-segment would let an argument write outside the skills tree
# (`--to-hermes name ../../../tmp/evil` did exactly that before this guard).
safe_name() {
  case "$2" in
    *[!A-Za-z0-9._-]* | "" | .* ) die "invalid $1 '$2' — use letters, digits, dot, dash, underscore" ;;
  esac
}

list_hermes() {
  [ -d "$HERMES_SKILLS" ] || { echo "  (Hermes skills dir not found)"; return; }
  find "$HERMES_SKILLS" -name SKILL.md -printf '%h\n' 2>/dev/null | sort | while read -r d; do
    printf '  %-28s %s\n' "$(basename "$d")" "$(basename "$(dirname "$d")")"
  done
}

list_claude() {
  for root in "$CLAUDE_SKILLS" "$REPO_DIR/.claude/skills"; do
    [ -d "$root" ] || continue
    find "$root" -maxdepth 2 -name SKILL.md -printf '%h\n' 2>/dev/null | sort | while read -r d; do
      printf '  %-28s %s\n' "$(basename "$d")" "$([ "$root" = "$CLAUDE_SKILLS" ] && echo user || echo project)"
    done
  done
}

# Both finders print a path or nothing, and must always exit 0. "Not found" is
# a normal outcome the caller reports with die(); returning non-zero instead
# tripped `set -e` at the assignment, so the script exited 1 having printed
# nothing at all and the caller never learned the name was unknown.
find_hermes_skill() {
  find "$HERMES_SKILLS" -maxdepth 3 -type d -name "$1" 2>/dev/null | head -1
  return 0
}

find_claude_skill() {
  for root in "$REPO_DIR/.claude/skills" "$CLAUDE_SKILLS"; do
    [ -d "$root/$1" ] && { echo "$root/$1"; return 0; }
  done
  return 0
}

copy_tree() {
  local src="$1" dst="$2"
  if [ "$DRY_RUN" = true ]; then
    echo "would copy:"
    (cd "$src" && find . -type f | sed 's|^\./|  |')
    echo "to: $dst"
    return
  fi
  mkdir -p "$dst"
  cp -r "$src/." "$dst/"
  echo "copied -> $dst"
}

[ $# -gt 0 ] || { sed -n '2,18p' "$0"; exit 0; }

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    --list)
      echo "Hermes skills ($HERMES_SKILLS):"; list_hermes
      echo; echo "Claude Code skills:"; list_claude
      exit 0 ;;
    --to-claude)
      name="${2:-}"; [ -n "$name" ] || die "--to-claude needs a skill name"
      safe_name "skill name" "$name"
      src="$(find_hermes_skill "$name")"
      [ -n "$src" ] && [ -f "$src/SKILL.md" ] || die "no Hermes skill named '$name' (try --list)"
      dst="$CLAUDE_SKILLS/$name"
      [ -e "$dst" ] && [ "$DRY_RUN" = false ] && die "$dst already exists — remove it first"
      copy_tree "$src" "$dst"
      echo "note: Claude Code picks it up on the next session start."
      exit 0 ;;
    --to-hermes)
      name="${2:-}"; [ -n "$name" ] || die "--to-hermes needs a skill name"
      cat="${3:-productivity}"
      safe_name "skill name" "$name"
      safe_name "category" "$cat"
      src="$(find_claude_skill "$name")"
      [ -n "$src" ] && [ -f "$src/SKILL.md" ] || die "no Claude Code skill named '$name' (try --list)"
      dst="$HERMES_SKILLS/$cat/$name"
      [ -e "$dst" ] && [ "$DRY_RUN" = false ] && die "$dst already exists — remove it first"
      copy_tree "$src" "$dst"
      echo "note: verify with 'hermes skills list | grep $name'."
      exit 0 ;;
    -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
    *) die "unknown flag: $1" ;;
  esac
done
