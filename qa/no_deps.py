#!/usr/bin/env python3
"""no_deps — prove that tools/ imports nothing that needs installing.

The whole promise of tools/ is that it runs in a fresh container, in CI, and on
someone else's laptop with no setup step. This walks every module in tools/ and
fails the build the moment an import cannot be satisfied by the standard
library or by a sibling in tools/ itself.

    python3 qa/no_deps.py
    python3 qa/no_deps.py --json

Exit 0 clean, 1 on a third-party import, 2 on a bad invocation.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import os
import sys
import sysconfig

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")


class DepError(ValueError):
    pass


def local_modules(tools_dir=TOOLS):
    """Sibling modules in tools/, derived from the directory.

    Derived rather than listed. A hardcoded allowlist silently goes stale the
    moment a tool is added — which is how `usage` came to be missing from the
    old copy of this check.
    """
    if not os.path.isdir(tools_dir):
        raise DepError(f"{tools_dir}: no such directory")
    return {fn[:-3] for fn in os.listdir(tools_dir)
            if fn.endswith(".py") and not fn.startswith("_")}


def _stdlib_by_location(mod):
    """Fallback for Python 3.9, where sys.stdlib_module_names does not exist.

    Added in 3.10. The previous version of this check read it through
    getattr(..., ()) and so, on 3.9 — the exact floor version the matrix exists
    to protect — every stdlib import fell through an empty set and was reported
    as third-party. The check did not merely miss things there; it failed
    outright on `import os`. Resolving the module and asking where it lives
    works on every version.
    """
    try:
        spec = importlib.util.find_spec(mod)
    except (ImportError, ValueError, ModuleNotFoundError):
        return False
    if spec is None:
        return False
    origin = spec.origin or ""
    if origin in ("built-in", "frozen"):
        return True
    stdlib = sysconfig.get_paths().get("stdlib") or ""
    # site-packages lives *under* stdlib on some layouts, so exclude it
    # explicitly rather than trusting the prefix alone.
    return bool(stdlib) and origin.startswith(stdlib) \
        and "site-packages" not in origin


def classify(mod, local):
    if mod in local:
        return "local"
    if mod in sys.builtin_module_names:
        return "stdlib"
    names = getattr(sys, "stdlib_module_names", None)
    if names is not None:
        return "stdlib" if mod in names else "third-party"
    return "stdlib" if _stdlib_by_location(mod) else "third-party"


def imports_of(path):
    """Top-level package name of every import in a file."""
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=path)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            # A relative import (level > 0) resolves inside this package and
            # can never be a third-party dependency.
            mods = [(node.module or "").split(".")[0]]
        else:
            continue
        out.extend(m for m in mods if m)
    return out


def scan(tools_dir=TOOLS):
    local = local_modules(tools_dir)
    offenders, seen = [], set()
    for fn in sorted(os.listdir(tools_dir)):
        if not fn.endswith(".py"):
            continue
        for mod in imports_of(os.path.join(tools_dir, fn)):
            if classify(mod, local) == "third-party":
                offenders.append({"file": f"tools/{fn}", "module": mod})
            seen.add(mod)
    return {"files": sum(1 for f in os.listdir(tools_dir) if f.endswith(".py")),
            "modules": sorted(seen), "offenders": offenders}


def main(argv=None):
    p = argparse.ArgumentParser(prog="no_deps", description=__doc__.split("\n")[0])
    p.add_argument("--tools", default=TOOLS, help="directory to scan")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    try:
        res = scan(a.tools)
    except (DepError, SyntaxError, OSError) as e:
        print(f"no_deps: {e}", file=sys.stderr)
        return 2

    if a.json:
        print(json.dumps(res, indent=2, sort_keys=True))
    elif res["offenders"]:
        for o in res["offenders"]:
            print(f"{o['file']}: imports {o['module']!r}", file=sys.stderr)
        print("tools/ must be stdlib-only — no pip install, ever.", file=sys.stderr)
    else:
        print(f"tools/ is stdlib-only "
              f"({res['files']} files, {len(res['modules'])} distinct imports)")
    return 1 if res["offenders"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
