#!/usr/bin/env python3
"""PostToolUse hook: validate a skill or tool immediately after it is edited.

A broken SKILL.md fails silently — the skill simply stops being offered, and
you find out weeks later. This catches it at the moment of the edit.

Scope is deliberately narrow: it only looks at the single file that was just
written, and only at files inside this repo's .claude/skills, tools/, or qa/.
Everything else exits 0 without comment, because a hook that talks during
unrelated work gets disabled.

Reads the hook payload as JSON on stdin. Exit 2 sends stderr back to Claude
as feedback; any other non-zero would be treated as an unexpected failure,
so every other path exits 0.
"""

from __future__ import annotations

import json
import os
import re
import sys

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def read_payload():
    try:
        raw = sys.stdin.read()
    except Exception:
        return {}
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def target_path(payload):
    ti = payload.get("tool_input") or {}
    for key in ("file_path", "path", "notebook_path"):
        v = ti.get(key)
        if isinstance(v, str) and v:
            return v
    return ""


def check_skill(path):
    """Return a list of problems with a SKILL.md."""
    problems = []
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as e:
        return [f"cannot read: {e}"]

    if not text.startswith("---"):
        return ["missing YAML frontmatter — the skill will not load at all"]
    end = text.find("\n---", 3)
    if end == -1:
        return ["frontmatter is never closed with a --- line"]

    meta = {}
    for line in text[3:end].strip("\n").split("\n"):
        if ":" in line and not line.startswith((" ", "\t")):
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip("\"'")

    name = meta.get("name", "")
    desc = meta.get("description", "")
    expected = os.path.basename(os.path.dirname(path))

    if not name:
        problems.append("frontmatter has no 'name'")
    elif name != expected:
        problems.append(
            f"name is {name!r} but the directory is {expected!r} — "
            f"they must match or the skill will not resolve")
    elif not NAME_RE.match(name):
        problems.append(f"name {name!r} must be lowercase-hyphenated")

    if not desc:
        problems.append("frontmatter has no 'description'")
    elif len(desc) > 1024:
        problems.append(f"description is {len(desc)} chars (max 1024)")
    elif "use when" not in desc.lower() and "use this" not in desc.lower():
        problems.append(
            "description never says when to use the skill; it will rarely "
            "trigger. Add an explicit 'Use when ...' clause.")
    return problems


def check_python(path):
    try:
        src = open(path, encoding="utf-8").read()
    except OSError as e:
        return [f"cannot read: {e}"]
    try:
        compile(src, path, "exec")
    except SyntaxError as e:
        return [f"syntax error line {e.lineno}: {e.msg}"]
    return []


def check_json(path):
    try:
        json.load(open(path, encoding="utf-8"))
    except OSError as e:
        return [f"cannot read: {e}"]
    except json.JSONDecodeError as e:
        return [f"invalid JSON: {e}"]
    return []


def main():
    payload = read_payload()
    path = target_path(payload)
    if not path:
        return 0

    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        abs_path = os.path.abspath(path)
        rel = os.path.relpath(abs_path, os.path.abspath(root))
    except ValueError:
        return 0
    if rel.startswith("..") or not os.path.isfile(abs_path):
        return 0

    parts = rel.replace("\\", "/").split("/")
    problems = []

    if os.path.basename(abs_path) == "SKILL.md" and ".claude" in parts:
        problems = check_skill(abs_path)
    elif abs_path.endswith(".py") and parts[0] in ("tools", "qa", ".claude"):
        problems = check_python(abs_path)
    elif abs_path.endswith(".json") and parts[0] in ("tools", "qa", ".claude"):
        problems = check_json(abs_path)
    else:
        return 0

    if problems:
        print(f"{rel} has problems that will break it at runtime:",
              file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:                       # never break the session
        print(f"validate_on_edit: {e}", file=sys.stderr)
        raise SystemExit(0)
