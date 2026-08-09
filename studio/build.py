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


def to_fragment(html):
    """Strip the outer document so a host that supplies its own <head>/<body>
    can wrap this. Published Artifacts do exactly that, and leaving a second
    <html> element inside their body produces a page browsers silently repair
    in inconsistent ways."""
    # Index-based, not regex-matched. app.js builds a standalone document as a
    # string, so the source legitimately contains "</body></html>" inside a
    # template literal — a non-greedy /<body>(.*?)<\/body>/ matches THAT and
    # truncates the fragment mid-script. Anchor on the last closing tag instead.
    hs, he = html.find("<head"), html.find("</head>")
    bs, be = html.find("<body"), html.rfind("</body>")
    if min(hs, he, bs, be) < 0:
        raise BuildError("cannot find <head>/<body> to unwrap")
    head = html[html.index(">", hs) + 1:he]
    body = html[html.index(">", bs) + 1:be]

    # Keep <title> and the styles; drop the meta tags the host controls.
    keep = "".join(re.findall(r"<title>.*?</title>", head, re.S))
    keep += "".join(re.findall(r"<style[^>]*>.*?</style>", head, re.S))
    frag = keep + body

    # The truncation above was silent, so assert the shape rather than trust it.
    if frag.count("<script>") != frag.count("</script>"):
        raise BuildError(
            f"fragment has {frag.count('<script>')} <script> tags but "
            f"{frag.count('</script>')} closing tags — it was truncated")
    return frag


def main(argv=None):
    ap = argparse.ArgumentParser(prog="studio/build",
                                 description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="verify the built files match the sources")
    ap.add_argument("--artifact", action="store_true",
                    help="also write artifact.html (no outer document tags)")
    a = ap.parse_args(argv)

    out = os.path.join(HERE, "index.html")
    frag_out = os.path.join(HERE, "artifact.html")
    # GitHub Pages serves /docs from the branch. Keeping a byte-identical copy
    # there means the hosted URL cannot drift from the source, and --check
    # enforces it rather than trusting anyone to remember.
    pages_out = os.path.join(os.path.dirname(HERE), "docs", "index.html")
    try:
        html = build()
        frag = to_fragment(html)
        if a.check:
            for path, want, hint in ((out, html, "index.html"),
                                     (frag_out, frag, "artifact.html"),
                                     (pages_out, html, "../docs/index.html")):
                if not os.path.isfile(path):
                    raise BuildError(f"studio/{hint} is missing — run "
                                     f"python3 studio/build.py --artifact")
                if open(path, encoding="utf-8").read() != want:
                    raise BuildError(
                        f"studio/{hint} is stale — it no longer matches its "
                        f"sources. Run: python3 studio/build.py --artifact")
            print("studio/index.html and artifact.html match their sources")
            return 0
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(html)
        with open(frag_out, "w", encoding="utf-8") as fh:
            fh.write(frag)
        os.makedirs(os.path.dirname(pages_out), exist_ok=True)
        with open(pages_out, "w", encoding="utf-8") as fh:
            fh.write(html)
        # Tell Pages not to run Jekyll — it would ignore files starting with _
        # and there is nothing here for it to build.
        open(os.path.join(os.path.dirname(pages_out), ".nojekyll"), "w").close()
    except (BuildError, OSError) as e:
        print(f"studio/build: {e}", file=sys.stderr)
        return 2

    print(f"studio/index.html     ({os.path.getsize(out):,} bytes, "
          f"{len(PARTS)} sources inlined)")
    print(f"studio/artifact.html  ({os.path.getsize(frag_out):,} bytes, "
          f"document tags removed for embedding)")
    print(f"docs/index.html       ({os.path.getsize(pages_out):,} bytes, "
          f"GitHub Pages copy)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
