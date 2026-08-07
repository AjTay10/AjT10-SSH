#!/usr/bin/env python3
"""
Audit every Hermes skill for whether it can actually run here.

`hermes skills list` shows enabled/disabled, which is about registration, not
readiness — a skill whose CLI is not installed still shows "enabled". This
walks every SKILL.md and answers the question that matters: can it run right
now, and if not, what is missing and who has to supply it?

Buckets:
  READY        every prerequisite is satisfied — declared or found in the body
  NEEDS-BIN    a command or package is missing but installable here
  NEEDS-CRED   an API key or account only the user can supply
  NEEDS-GPU    wants a multi-gigabyte ML stack this CPU container cannot serve
  INCOMPATIBLE declares platforms this machine is not (e.g. macOS-only)

  ./scripts/hermes-skills-audit.py            # summary + per-skill table
  ./scripts/hermes-skills-audit.py --json     # machine-readable
  ./scripts/hermes-skills-audit.py --bucket NEEDS-BIN
"""

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
SKILLS = HERMES_HOME / "skills"
PLATFORM = "linux" if sys.platform.startswith("linux") else (
    "macos" if sys.platform == "darwin" else "windows")

READY, NEEDS_BIN, NEEDS_CRED, NEEDS_GPU, INCOMPATIBLE = (
    "READY", "NEEDS-BIN", "NEEDS-CRED", "NEEDS-GPU", "INCOMPATIBLE")

# Commands a skill may reference that are always present in a POSIX shell, or
# that Hermes/this repo already provide. Treating these as missing would bury
# the real gaps.
ASSUMED = {
    "curl", "jq", "bash", "sh", "python", "python3", "pip", "git", "grep",
    "sed", "awk", "cat", "ls", "echo", "find", "hermes", "node", "npm", "npx",
    "ffmpeg", "rg", "reach", "yt-dlp", "gh",
}


def parse_frontmatter(path):
    """Minimal YAML front-matter reader — enough for the keys skills use, and
    dependency-free so the audit runs anywhere Hermes does."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}, ""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    raw, body = parts[1], parts[2]
    data = {}
    stack = [(0, data)]
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        m = re.match(r"^\s*([A-Za-z0-9_-]+)\s*:\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if val == "":
            child = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            if val.startswith("[") and val.endswith("]"):
                items = [i.strip().strip("'\"") for i in val[1:-1].split(",")]
                parent[key] = [i for i in items if i]
            else:
                parent[key] = val.strip("'\"")
    return data, body


# Packages a skill body tells you to install, but which are enormous ML stacks
# needing a GPU. Flagging them as a missing dependency is correct; pretending
# they are a quick `pip install` away on a CPU container is not.
HEAVY = {"marker-pdf", "vllm", "torch", "transformers", "lm-eval",
         "llama-cpp-python"}

_PIP_RE = re.compile(
    r"pip3?\s+install\s+((?:--[a-z-]+\s+)*)([A-Za-z0-9_.\[\]><=,-]+(?:\s+[A-Za-z0-9_.\[\]><=,-]+)*)")


def body_pip_packages(body):
    """Packages a skill's own instructions say to install.

    Only 8 of 71 skills declare `dependencies`, but plenty of others open with
    `pip install openpyxl`. Those are real prerequisites; ignoring them is how
    an audit reports READY for a skill that dies on its first import.
    """
    found = []
    for m in _PIP_RE.finditer(body or ""):
        for tok in m.group(2).split():
            if tok.startswith("-") or tok in ("install", "pip", "pip3"):
                continue
            pkg = re.split(r"[><=\[]", tok)[0].strip(",.")
            # The regex runs on prose, so it also catches shell fragments that
            # happen to follow `pip install` on the same line — redirections,
            # file arguments, URLs. Keep only things shaped like a package.
            if (not pkg or pkg in found
                    or pkg.isdigit()
                    or "/" in pkg or "\\" in pkg
                    or pkg.startswith("http")
                    or pkg.endswith((".txt", ".py", ".yaml", ".yml", ".json"))
                    or pkg in {"python", "python3", "which", "pip", "e", "."}):
                continue
            found.append(pkg)
    return found


def module_present(pkg):
    """Is a declared Python dependency importable by the interpreter Hermes
    uses? Distribution names and import names differ (SciencePlots ->
    scienceplots), so check the metadata first and fall back to the module."""
    import importlib.metadata as md
    import importlib.util

    try:
        md.distribution(pkg)
        return True
    except Exception:
        pass
    # Some "pip install X" packages are only ever used as a command (pygount,
    # comfy-cli). A CLI on PATH satisfies the skill even when the module is not
    # importable by this interpreter.
    if shutil.which(pkg):
        return True
    mod = pkg.replace("-", "_").lower()
    try:
        return importlib.util.find_spec(mod) is not None
    except (ImportError, ValueError):
        return False


def env_present(name):
    """A credential counts as present if it is exported or written into
    ~/.hermes/.env. The file is only tested for the key's presence — its value
    is never read, printed or returned."""
    if os.environ.get(name):
        return True
    envfile = HERMES_HOME / ".env"
    if envfile.exists():
        try:
            for line in envfile.read_text(errors="replace").splitlines():
                line = line.strip()
                if line.startswith(f"{name}=") and len(line) > len(name) + 1:
                    return True
        except OSError:
            pass
    return False


def audit_one(skill_md):
    fm, body = parse_frontmatter(skill_md)
    rel = skill_md.parent.relative_to(SKILLS)
    name = fm.get("name") or skill_md.parent.name
    entry = {
        "name": name,
        "path": str(rel),
        "category": rel.parts[0] if len(rel.parts) > 1 else "",
        "missing_commands": [],
        "missing_env": [],
        "platforms": fm.get("platforms") or [],
    }

    platforms = entry["platforms"]
    if platforms and PLATFORM not in [p.lower() for p in platforms]:
        entry["status"] = INCOMPATIBLE
        entry["detail"] = f"declares platforms {platforms}; this host is {PLATFORM}"
        return entry

    prereq = fm.get("prerequisites") or {}
    cmds = prereq.get("commands") or []
    envs = prereq.get("env_vars") or []
    deps = fm.get("dependencies") or []

    for c in cmds:
        if c in ASSUMED:
            continue
        if not shutil.which(c):
            entry["missing_commands"].append(c)
    for e in envs:
        if not env_present(e):
            entry["missing_env"].append(e)
    # Declared Python dependencies are as much a blocker as a missing CLI: a
    # skill that imports scipy on a host without scipy is not ready, however
    # green the registration looks.
    all_deps = list(deps) + [p for p in body_pip_packages(body) if p not in deps]
    entry["missing_deps"] = [d for d in all_deps if d and not module_present(d)]
    entry["heavy_deps"] = [d for d in entry["missing_deps"] if d in HEAVY]

    if entry["missing_env"]:
        entry["status"] = NEEDS_CRED
        entry["detail"] = "needs " + ", ".join(entry["missing_env"])
    elif (entry["missing_deps"] and not entry["missing_commands"]
          and all(d in HEAVY for d in entry["missing_deps"])):
        # Multi-gigabyte ML stacks that want a GPU. Listing these next to a
        # one-line `pip install` implies a parity that does not exist.
        entry["status"] = NEEDS_GPU
        entry["detail"] = ("needs a GPU/ML stack: "
                           + ", ".join(entry["missing_deps"]))
    elif entry["missing_commands"] or entry["missing_deps"]:
        entry["status"] = NEEDS_BIN
        bits = []
        if entry["missing_commands"]:
            bits.append("missing command(s): " + ", ".join(entry["missing_commands"]))
        if entry["missing_deps"]:
            bits.append("missing python package(s): " + ", ".join(entry["missing_deps"]))
        entry["detail"] = "; ".join(bits)
    else:
        entry["status"] = READY
        entry["detail"] = "no unmet prerequisites"
    return entry


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--bucket", choices=[READY, NEEDS_BIN, NEEDS_CRED, NEEDS_GPU, INCOMPATIBLE])
    args = ap.parse_args()

    if not SKILLS.is_dir():
        print(f"no skills directory at {SKILLS} — is Hermes installed?", file=sys.stderr)
        return 2

    results = sorted((audit_one(p) for p in SKILLS.rglob("SKILL.md")),
                     key=lambda r: (r["status"], r["path"]))
    if args.bucket:
        results = [r for r in results if r["status"] == args.bucket]

    if args.json:
        counts = {}
        for r in results:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        print(json.dumps({"host": PLATFORM, "total": len(results),
                          "counts": counts, "skills": results},
                         ensure_ascii=False, indent=2))
        return 0

    width = max((len(r["name"]) for r in results), default=10)
    current = None
    for r in results:
        if r["status"] != current:
            current = r["status"]
            print(f"\n{current}")
            print("-" * (width + 40))
        extra = "" if r["status"] == READY else f"  {r['detail']}"
        print(f"  {r['name'].ljust(width)}  {r['category']}{extra}")

    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("\n" + "=" * (width + 40))
    print(f"{len(results)} skills: " + ", ".join(
        f"{v} {k}" for k, v in sorted(counts.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
