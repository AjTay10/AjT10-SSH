#!/usr/bin/env python3
"""build — inline the sources into one self-contained index.html.

The product has to be a single file. Someone should be able to save it, open it
on a plane, drop in a client's export, and have nothing leave the laptop. That
rules out module imports, a bundler, and a CDN, so the parts are kept as
separate readable files here and stitched together at build time.

    python3 studio/build.py            # write studio/index.html
    python3 studio/build.py --check    # fail if index.html is stale

--check is the CI mode: editing engine.js without rebuilding would ship a tool
whose behaviour differs from its own source, which is the exact failure this
repo exists to prevent.
"""

from __future__ import annotations

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

PARTS = {
    "STYLE": "style.css",
    "REPORT_STYLE": "report.css",
    "ENGINE": "engine.js",
    "CHARTS": "charts.js",
    "APP": "app.js",
}

# A single file that phones home is not a single file. Checked on every build.
FORBIDDEN = ("http://", "https://", "//cdn.", "fetch(", "XMLHttpRequest",
             "WebSocket", "@import", "<link", "navigator.sendBeacon")


class BuildError(RuntimeError):
    pass


def read(name):
    path = os.path.join(HERE, name)
    if not os.path.isfile(path):
        raise BuildError(f"missing source file: studio/{name}")
    return open(path, encoding="utf-8").read()


def build():
    html = read("template.html")

    for key, fname in PARTS.items():
        token = "{{" + key + "}}"
        if token not in html:
            raise BuildError(f"template.html has no {token} placeholder")
        body = read(fname)
        # The node export shim is meaningless in a browser and `module` being
        # undefined there would throw, so strip it during inlining.
        body = re.sub(r"\nif \(typeof module[^\n]*\n?", "\n", body)
        if "</script" in body:
            raise BuildError(f"studio/{fname} contains a literal </script, "
                             f"which would terminate the inline block early")
        html = html.replace(token, body)

    left = re.findall(r"\{\{\w+\}\}", html)
    if left:
        raise BuildError(f"unfilled placeholders: {', '.join(left)}")

    scan = html.replace('xmlns="http://www.w3.org/2000/svg"', "")
    for bad in FORBIDDEN:
        if bad in scan:
            raise BuildError(
                f"output contains {bad!r} — the tool must not reach the network. "
                f"Remove it from the source, not from this check.")
    return html


def main(argv=None):
    ap = argparse.ArgumentParser(prog="studio/build",
                                 description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="verify index.html matches the sources")
    a = ap.parse_args(argv)

    out = os.path.join(HERE, "index.html")
    try:
        html = build()
        if a.check:
            if not os.path.isfile(out):
                raise BuildError("studio/index.html is missing — run "
                                 "python3 studio/build.py")
            if open(out, encoding="utf-8").read() != html:
                raise BuildError(
                    "studio/index.html is stale — it no longer matches its "
                    "sources. Run: python3 studio/build.py")
            print("studio/index.html matches its sources")
            return 0
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(html)
    except (BuildError, OSError) as e:
        print(f"studio/build: {e}", file=sys.stderr)
        return 2

    print(f"studio/index.html  ({os.path.getsize(out):,} bytes, "
          f"{len(PARTS)} sources inlined)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
