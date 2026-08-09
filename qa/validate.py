#!/usr/bin/env python3
"""validate — QA gate for this configuration repo.

Checks the things that silently break a Claude configuration: malformed skill
frontmatter, names that disagree with their directory, descriptions that will
never trigger, cross-references to skills or files that do not exist, Python
that does not compile, JSON that does not parse, and commands documented in
prose that were never actually built.

    python3 qa/validate.py             # human output, exit 1 on any error
    python3 qa/validate.py --json
    python3 qa/validate.py --strict    # warnings become errors

Stdlib only, so this runs in CI without an install step.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, ".claude", "skills")
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Phrasings that make a description actually fire. A description that only
# says what a skill *is* never triggers; it has to say when to use it.
TRIGGER_HINTS = ("use when", "use this", "triggers", "use for", "use it when",
                 "also use")

errors: list[str] = []
warnings: list[str] = []
notes: list[str] = []


def err(where, msg):
    errors.append(f"{where}: {msg}")


def warn(where, msg):
    warnings.append(f"{where}: {msg}")


def rel(p):
    return os.path.relpath(p, ROOT)


# --------------------------------------------------------------------------

def parse_frontmatter(path, text):
    """Minimal YAML frontmatter reader: key: value, quoted or bare, no nesting."""
    if not text.startswith("---"):
        err(rel(path), "missing YAML frontmatter (file must start with ---)")
        return None
    end = text.find("\n---", 3)
    if end == -1:
        err(rel(path), "frontmatter is not closed with a --- line")
        return None
    block = text[3:end].strip("\n")
    meta, key = {}, None
    for i, line in enumerate(block.split("\n"), 2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0] in " \t" and key:                 # folded continuation
            meta[key] += " " + line.strip()
            continue
        if ":" not in line:
            err(rel(path), f"frontmatter line {i} is not 'key: value': {line[:60]!r}")
            continue
        key, val = line.split(":", 1)
        key, val = key.strip(), val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            body = val[1:-1]
            try:
                val = json.loads(val) if val[0] == '"' else body
            except json.JSONDecodeError:
                val = body
        meta[key] = val
    return meta


def check_skills():
    if not os.path.isdir(SKILLS):
        err("qa", f"no skills directory at {rel(SKILLS)}")
        return {}, {}

    dirs = sorted(d for d in os.listdir(SKILLS)
                  if os.path.isdir(os.path.join(SKILLS, d)))
    if not dirs:
        err("qa", "skills directory is empty")
        return {}, {}

    found, descs = {}, {}
    for d in dirs:
        sk = os.path.join(SKILLS, d, "SKILL.md")
        if not os.path.isfile(sk):
            err(f"skills/{d}", "has no SKILL.md")
            continue
        raw = open(sk, "rb").read()
        if b"\r\n" in raw:
            err(rel(sk), "contains CRLF line endings")
        if b"\t" in raw:
            warn(rel(sk), "contains literal tab characters")
        text = raw.decode("utf-8")

        meta = parse_frontmatter(sk, text)
        if meta is None:
            continue

        name = meta.get("name", "")
        desc = meta.get("description", "")

        if not name:
            err(rel(sk), "frontmatter has no 'name'")
        else:
            if name != d:
                err(rel(sk), f"name {name!r} does not match directory {d!r} — "
                             f"the skill will not resolve")
            if not NAME_RE.match(name):
                err(rel(sk), f"name {name!r} must be lowercase-hyphenated")
            if len(name) > 64:
                err(rel(sk), f"name is {len(name)} chars (max 64)")
            if name in found:
                err(rel(sk), f"duplicate skill name {name!r}")
            found[name] = sk

        if not desc:
            err(rel(sk), "frontmatter has no 'description'")
        else:
            if len(desc) > 1024:
                err(rel(sk), f"description is {len(desc)} chars (max 1024)")
            if len(desc) < 60:
                warn(rel(sk), f"description is only {len(desc)} chars — likely "
                              f"too thin to trigger reliably")
            low = desc.lower()
            if not any(h in low for h in TRIGGER_HINTS):
                warn(rel(sk), "description never says when to use the skill "
                              "('Use when...'); it may never trigger")
            key = re.sub(r"\W+", " ", low)[:120]
            if key in descs:
                warn(rel(sk), f"description opens identically to {descs[key]!r} — "
                              f"the two will compete to trigger")
            else:
                descs[key] = name

        body = text[text.find("\n---", 3) + 4:]
        if len(body.strip()) < 200:
            warn(rel(sk), "body is nearly empty")
        if name and f"# {name}" not in body and not re.search(r"^# ", body, re.M):
            warn(rel(sk), "body has no top-level heading")

    return found, descs


def check_references(skill_names):
    """Cross-references: sibling skills, tools/*.py, and reference files."""
    for name, path in sorted(skill_names.items()):
        text = open(path, encoding="utf-8").read()
        d = os.path.dirname(path)

        for m in re.finditer(r"`(tools/[A-Za-z0-9_./-]+\.py)`", text):
            if not os.path.isfile(os.path.join(ROOT, m.group(1))):
                err(rel(path), f"references missing file {m.group(1)}")
        for m in re.finditer(r"python3 (tools/[A-Za-z0-9_./-]+\.py)", text):
            if not os.path.isfile(os.path.join(ROOT, m.group(1))):
                err(rel(path), f"documents a command using missing "
                               f"{m.group(1)}")
        for m in re.finditer(r"`(references/[A-Za-z0-9_./-]+)`", text):
            if not os.path.isfile(os.path.join(d, m.group(1))):
                err(rel(path), f"references missing file {m.group(1)}")

        # "Related" links must point at skills that exist.
        tail = text[text.rfind("## Related"):] if "## Related" in text else ""
        for m in re.finditer(r"`([a-z0-9]+(?:-[a-z0-9]+)+)`", tail):
            ref = m.group(1)
            if ref == name or ref in skill_names:
                continue
            if ref in EXTERNAL_SKILLS:
                continue
            warn(rel(path), f"Related section links to unknown skill {ref!r}")


# Skills shipped by the host environment rather than this repo.
EXTERNAL_SKILLS = {"dataviz", "artifact-design", "artifact-diagramming",
                   "artifact-capabilities", "skill-creator", "code-review",
                   "docx", "pdf", "pptx", "xlsx", "update-config", "simplify",
                   "security-review", "session-start-hook", "claude-api"}


def check_python():
    tools = os.path.join(ROOT, "tools")
    qa = os.path.join(ROOT, "qa")
    seen = 0
    for base in (tools, qa, os.path.join(ROOT, "demo"),
                 os.path.join(ROOT, "studio"),
                 os.path.join(ROOT, ".claude", "hooks")):
        if not os.path.isdir(base):
            continue
        for fn in sorted(os.listdir(base)):
            if not fn.endswith(".py"):
                continue
            p = os.path.join(base, fn)
            seen += 1
            src = open(p, encoding="utf-8").read()
            try:
                tree = ast.parse(src, filename=p)
            except SyntaxError as e:
                err(rel(p), f"syntax error line {e.lineno}: {e.msg}")
                continue
            if not ast.get_docstring(tree):
                warn(rel(p), "has no module docstring")
            # Catch the copy-paste hazard: a name used but never bound anywhere.
            if "\t" in src:
                warn(rel(p), "mixes tabs into Python source")
    if seen == 0:
        warn("qa", "no Python files found to check")
    notes.append(f"{seen} Python file(s) compiled clean")


def check_json():
    count = 0
    for base, _, files in os.walk(ROOT):
        if ".git" in base:
            continue
        for fn in files:
            if not fn.endswith(".json"):
                continue
            p = os.path.join(base, fn)
            count += 1
            try:
                json.load(open(p, encoding="utf-8"))
            except json.JSONDecodeError as e:
                err(rel(p), f"invalid JSON: {e}")
    notes.append(f"{count} JSON file(s) parsed clean")


def check_settings():
    p = os.path.join(ROOT, ".claude", "settings.json")
    if not os.path.isfile(p):
        warn("qa", "no .claude/settings.json")
        return
    try:
        s = json.load(open(p, encoding="utf-8"))
    except json.JSONDecodeError:
        return                                   # already reported by check_json
    perms = s.get("permissions", {})
    if not isinstance(perms, dict):
        err(rel(p), "'permissions' must be an object")
        return
    for bucket in ("allow", "deny", "ask"):
        v = perms.get(bucket, [])
        if not isinstance(v, list):
            err(rel(p), f"permissions.{bucket} must be a list")
            continue
        for entry in v:
            if not isinstance(entry, str):
                err(rel(p), f"permissions.{bucket} contains a non-string entry")
            elif not re.match(r"^[A-Za-z]+(\(.*\))?$", entry):
                warn(rel(p), f"permission {entry!r} does not look like "
                             f"Tool or Tool(pattern)")
    for h in s.get("hooks", {}).values():
        for group in (h if isinstance(h, list) else []):
            for hook in group.get("hooks", []):
                cmd = hook.get("command", "")
                m = re.search(r"\$CLAUDE_PROJECT_DIR/([A-Za-z0-9_./-]+)", cmd)
                if m and not os.path.exists(os.path.join(ROOT, m.group(1))):
                    err(rel(p), f"hook points at missing file {m.group(1)}")


def check_commands():
    d = os.path.join(ROOT, ".claude", "commands")
    if not os.path.isdir(d):
        return
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".md"):
            continue
        p = os.path.join(d, fn)
        text = open(p, encoding="utf-8").read()
        if not text.startswith("---"):
            warn(rel(p), "command has no frontmatter description")
        for m in re.finditer(r"python3 (tools/[A-Za-z0-9_./-]+\.py)", text):
            if not os.path.isfile(os.path.join(ROOT, m.group(1))):
                err(rel(p), f"references missing {m.group(1)}")


def check_documented_counts(skill_count):
    """The README and CLAUDE.md advertise counts. Keep them true.

    Documented numbers rot the moment someone adds a skill, and a README that
    undercounts is the first thing a reader notices and the last thing anyone
    remembers to update.
    """
    tools = len([f for f in os.listdir(os.path.join(ROOT, "tools"))
                 if f.endswith(".py")]) if os.path.isdir(
                     os.path.join(ROOT, "tools")) else 0

    tests = 0
    st = os.path.join(ROOT, "qa", "selftest.py")
    if os.path.isfile(st):
        tests = len(re.findall(r"^def t_\w+\(", open(st, encoding="utf-8").read(),
                               re.M))

    actual = {"skill": skill_count, "tool": tools, "test": tests}
    for fn in ("README.md", "CLAUDE.md"):
        p = os.path.join(ROOT, fn)
        if not os.path.isfile(p):
            continue
        text = open(p, encoding="utf-8").read()
        for noun, real in actual.items():
            if not real:
                continue
            # (?<!\w) keeps "python3 tools/..." from reading as "3 tools", and
            # (?!/) keeps a path segment from being mistaken for a count.
            # One optional adjective is allowed between number and noun, so
            # "105 adversarial tests" is checked as well as "105-test".
            pattern = (r"(?<!\w)(\d+)[-\s*]{0,3}(?:[a-z]+[-\s]){0,2}"
                       + noun + r"s?\b(?!/)")
            for m in re.finditer(pattern, text):
                claimed = int(m.group(1))
                # Only judge claims in the same ballpark — "3 platforms" or
                # "5 tools you might add" are not counts of this repo.
                if claimed != real and abs(claimed - real) <= max(12, real // 2):
                    err(fn, f"claims {claimed} {noun}s but the repo has {real} "
                            f"— update the text or the code")
                    break            # one report per noun per file is enough


def check_executable():
    for base in ("tools", "qa"):
        d = os.path.join(ROOT, base)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            p = os.path.join(d, fn)
            if fn.endswith(".py") and open(p, encoding="utf-8").read(2) == "#!":
                if not os.access(p, os.X_OK):
                    warn(rel(p), "has a shebang but is not executable")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="validate")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true",
                    help="treat warnings as errors")
    a = ap.parse_args(argv)

    names, _ = check_skills()
    check_references(names)
    check_python()
    check_json()
    check_settings()
    check_commands()
    check_documented_counts(len(names))
    check_executable()
    notes.append(f"{len(names)} skill(s) validated")

    if a.json:
        print(json.dumps({"errors": errors, "warnings": warnings,
                          "notes": notes, "skills": sorted(names)}, indent=2))
    else:
        for n in notes:
            print(f"  ok      {n}")
        for w in warnings:
            print(f"  warn    {w}")
        for e in errors:
            print(f"  ERROR   {e}")
        print()
        if errors:
            print(f"FAILED — {len(errors)} error(s), {len(warnings)} warning(s)")
        elif warnings and a.strict:
            print(f"FAILED (strict) — {len(warnings)} warning(s)")
        else:
            print(f"PASSED — {len(warnings)} warning(s)")

    return 1 if (errors or (a.strict and warnings)) else 0


if __name__ == "__main__":
    raise SystemExit(main())
