#!/usr/bin/env bash
# Install this configuration into ~/.claude by symlinking, so `git pull`
# updates everything in place and nothing is silently forked into a copy.
#
#   ./install.sh              symlink skills, agents, and commands
#   ./install.sh --copy       copy instead (for machines without symlinks)
#   ./install.sh --dry-run    show what would happen
#   ./install.sh --uninstall  remove only the links this script created
#
# Existing files are never overwritten. Anything already present is reported
# and skipped, so a pre-existing skill of the same name survives untouched.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${CLAUDE_HOME:-$HOME/.claude}"
MODE=link
DRY=0

for arg in "$@"; do
  case "$arg" in
    --copy)      MODE=copy ;;
    --dry-run)   DRY=1 ;;
    --uninstall) MODE=uninstall ;;
    -h|--help)   sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

say()  { printf '%s\n' "$*"; }
do_it() { if [ "$DRY" = 1 ]; then say "  would: $*"; else "$@"; fi; }

linked=0; skipped=0; removed=0

process_dir() {
  local kind="$1" src="$REPO/.claude/$1" dst="$DEST/$1"
  [ -d "$src" ] || return 0
  [ "$MODE" = uninstall ] || do_it mkdir -p "$dst"

  local entry base target
  for entry in "$src"/*; do
    [ -e "$entry" ] || continue
    base="$(basename "$entry")"
    target="$dst/$base"

    if [ "$MODE" = uninstall ]; then
      if [ -L "$target" ] && [ "$(readlink "$target")" = "$entry" ]; then
        do_it rm "$target"; removed=$((removed+1))
        say "  removed  $kind/$base"
      fi
      continue
    fi

    if [ -L "$target" ] && [ "$(readlink "$target")" = "$entry" ]; then
      say "  ok       $kind/$base (already linked)"
      continue
    fi
    if [ -e "$target" ] || [ -L "$target" ]; then
      say "  SKIP     $kind/$base — already exists, not overwriting"
      skipped=$((skipped+1))
      continue
    fi

    if [ "$MODE" = copy ]; then
      do_it cp -R "$entry" "$target"
    else
      do_it ln -s "$entry" "$target"
    fi
    linked=$((linked+1))
    say "  added    $kind/$base"
  done
}

say "repo: $REPO"
say "dest: $DEST"
[ "$DRY" = 1 ] && say "(dry run — nothing will be written)"
say ""

process_dir skills
process_dir agents
process_dir commands

say ""
if [ "$MODE" = uninstall ]; then
  say "removed $removed link(s). Files this script did not create were left alone."
  exit 0
fi

say "added $linked, skipped $skipped"

if [ "$skipped" -gt 0 ]; then
  say ""
  say "Skipped entries already existed in $DEST. Nothing was overwritten."
  say "Remove the existing one first if you want this repo's version."
fi

say ""
say "Project settings and hooks are NOT installed globally on purpose —"
say "they live in .claude/settings.json and apply when you work in this repo."
say ""
say "Verify with:"
say "  python3 $REPO/qa/validate.py"
say "  python3 $REPO/qa/selftest.py"
