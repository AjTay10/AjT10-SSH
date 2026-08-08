#!/usr/bin/env python3
"""build — regenerate the demo report from a real pipeline run.

Every figure and every terminal block in the finished page is captured from an
actual subprocess run of the tools. Nothing is typed into the template by hand,
which is the only way the claim "these numbers came from the tools" stays true
as the tools change.

    python3 demo/build.py                 # fixtures -> pipeline -> report.html
    python3 demo/build.py --check         # rebuild to a temp file and diff

`--check` is the CI-facing mode: it fails if the committed report no longer
matches what the current code produces, so the page cannot silently drift.

Stdlib only.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import html
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BREAK = "2026-05-12"


class BuildError(RuntimeError):
    pass


def run(args, expect_zero=True):
    """Run a tool and return combined output exactly as a user would see it."""
    p = subprocess.run([sys.executable] + args, cwd=ROOT, capture_output=True,
                       text=True, timeout=120)
    if expect_zero and p.returncode != 0:
        raise BuildError(f"{' '.join(args)} exited {p.returncode}\n{p.stderr}")
    return p


# --------------------------------------------------------------------------
# terminal rendering
# --------------------------------------------------------------------------

# Applied to *captured* output, never to hand-written text. Order matters:
# the first pattern that claims a line wins, so specific rules go first.
HIGHLIGHT = (
    (re.compile(r"^(verdict:.*|Do not rank platforms.*|.*may be worse.*)$", re.M), "bad"),
    (re.compile(r"^(note: .*|.*sustained level shift.*)$", re.M), "hit"),
    (re.compile(r"^(read: .*|Pass --platform.*|.*defined differently.*)$", re.M), "dim"),
)


def term(cmd, body, extra_rules=()):
    """One <div class="term"> block: the command, then its literal output."""
    out = html.escape(body.rstrip("\n"), quote=False)

    spans = []          # (start, end, cls) claimed regions, non-overlapping
    for pattern, cls in tuple(extra_rules) + HIGHLIGHT:
        for m in pattern.finditer(out):
            if not any(s < m.end() and m.start() < e for s, e, _ in spans):
                spans.append((m.start(), m.end(), cls))
    spans.sort()

    parts, pos = [], 0
    for s, e, cls in spans:
        parts.append(out[pos:s])
        parts.append(f'<span class="{cls}">{out[s:e]}</span>')
        pos = e
    parts.append(out[pos:])

    return (f'<div class="term"><pre><span class="cmd">{html.escape(cmd)}</span>\n'
            f'{"".join(parts)}</pre></div>')


# --------------------------------------------------------------------------

def split_by_platform(norm_csv, outdir):
    with open(norm_csv, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise BuildError(f"{norm_csv} is empty")
    paths = {}
    for plat in sorted({r["platform"] for r in rows}):
        sel = [r for r in rows if r["platform"] == plat]
        path = os.path.join(outdir, f"{plat}.csv")
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["date", "reach", "er_pct"])
            for r in sel:
                w.writerow([r["date"],
                            r["impressions"] or r["video_views"] or r["reach"],
                            r["er_pct"]])
        paths[plat] = path
    return paths


def before_after(path):
    """Median reach and ER either side of the break, plus post counts."""
    with open(path, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    pre = [r for r in rows if r["date"] < BREAK]
    post = [r for r in rows if r["date"] >= BREAK]
    if not pre or not post:
        raise BuildError(f"{path}: no rows on one side of {BREAK}")

    def med(rs, k):
        vals = [float(r[k]) for r in rs if r[k]]
        if not vals:
            raise BuildError(f"{path}: no usable {k} values")
        return statistics.median(vals)

    out = {"posts_before": len(pre), "posts_after": len(post)}
    for label, key in (("reach", "reach"), ("er", "er_pct")):
        a, b = med(pre, key), med(post, key)
        out[f"{label}_before"], out[f"{label}_after"] = a, b
        out[f"{label}_change"] = (b - a) / a * 100
    return out


def scale_svg(svg):
    """Let the grid size the chart; viewBox keeps the aspect ratio."""
    return re.sub(r'(<svg[^>]*?)width="\d+" height="(\d+)"',
                  r'\1width="100%" height="\2"', svg, count=1)


def build(outdir, report_path):
    exports = os.path.join(outdir, "exports")
    run(["demo/make_fixtures.py", "--out", exports])

    yt = os.path.join(exports, "youtube_studio_export.csv")
    tt = os.path.join(exports, "tiktok_export.csv")
    ig = os.path.join(exports, "instagram_export.csv")
    norm = os.path.join(outdir, "normalized.csv")

    # --- step 1: inspect -------------------------------------------------
    p = run(["tools/social_ingest.py", "--inspect", yt])
    t_inspect = term("python3 tools/social_ingest.py --inspect "
                     "youtube_studio_export.csv", p.stdout,
                     [(re.compile(r"^.*— dropped —.*$", re.M), "hit")])

    # --- step 2: normalize -----------------------------------------------
    p = run(["tools/social_ingest.py",
             "--csv", yt, "--platform", "youtube",
             "--csv", tt, "--platform", "tiktok",
             "--csv", ig, "--platform", "instagram",
             "--out", norm, "--summary"])
    # stderr carries the warnings and the summary table; stdout is empty here.
    body = re.sub(r"/\S+/", "", p.stderr)          # strip absolute temp paths
    t_normalize = term(
        "python3 tools/social_ingest.py \\\n"
        "    --csv youtube_studio_export.csv --platform youtube \\\n"
        "    --csv tiktok_export.csv         --platform tiktok \\\n"
        "    --csv instagram_export.csv      --platform instagram \\\n"
        "    --out normalized.csv --summary", body)

    # --- step 3: anomaly --------------------------------------------------
    per_plat = split_by_platform(norm, outdir)
    p = run(["tools/anomaly.py", "--csv", per_plat["youtube"],
             "--date", "date", "--value", "reach", "--window", "12"])
    t_anomaly = term("python3 tools/anomaly.py --csv youtube.csv "
                     "--date date --value reach --window 12", p.stdout,
                     [(re.compile(r"^\d{4}-\d\d-\d\d.*(drop|spike)$", re.M), "bad")])

    # --- step 4: the A/B result -------------------------------------------
    cmp_ = run(["tools/abtest.py", "compare", "--a", "41/1180", "--b", "58/1205"])
    bay = run(["tools/abtest.py", "bayes", "--a", "41/1180", "--b", "58/1205"])
    bayes_tail = "\n".join(bay.stdout.strip().split("\n")[-6:])
    t_abtest = (
        term("python3 tools/abtest.py compare --a 41/1180 --b 58/1205",
             cmp_.stdout,
             [(re.compile(r"^absolute difference.*$", re.M), "hit")])
        + term("python3 tools/abtest.py bayes --a 41/1180 --b 58/1205", bayes_tail))

    # --- charts -----------------------------------------------------------
    charts = {}
    for key, plat, col, title, sub, unit in (
        ("yt_reach", "youtube", "reach", "YouTube — impressions per post",
         "90 days · break on 12 May, no recovery", ""),
        ("tt_reach", "tiktok", "reach", "TikTok — video views per post",
         "same window · own volatility, nothing at 12 May", ""),
        ("yt_er", "youtube", "er_pct", "YouTube — engagement rate per post",
         "flat through the break — the content did not change", "%"),
    ):
        svg = os.path.join(outdir, f"{key}.svg")
        run(["tools/chartkit.py", "--type", "line", "--csv", per_plat[plat],
             "--x", "date", "--y", col, "--title", title, "--subtitle", sub,
             "--unit", unit, "--out", svg])
        charts[key] = scale_svg(open(svg, encoding="utf-8").read())

    # --- figures ----------------------------------------------------------
    f = before_after(per_plat["youtube"])
    with open(norm, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    platforms = sorted({r["platform"] for r in rows})

    # Does TikTok break at the same time? Answered properly, not by grepping for
    # the word "down" — TikTok has its own unrelated volatility, and a heuristic
    # that ignores *when* a shift happened would report a coincidence as a match.
    tt = json.loads(run(["tools/anomaly.py", "--csv", per_plat["tiktok"],
                         "--date", "date", "--value", "reach",
                         "--window", "12", "--json"]).stdout)
    break_day = datetime.date.fromisoformat(BREAK)
    near = [s for s in tt["changepoints"]
            if s["direction"] == "down"
            and abs((datetime.date.fromisoformat(s["date"]) - break_day).days) <= 7]
    tt_shift = "no break" if not near else f"{len(near)} nearby"
    tt_other = len([s for s in tt["changepoints"] if s["direction"] == "down"]) \
        - len(near)

    tools = len([x for x in os.listdir(os.path.join(ROOT, "tools"))
                 if x.endswith(".py")])

    values = {
        "TERM_INSPECT": t_inspect,
        "TERM_NORMALIZE": t_normalize,
        "TERM_ANOMALY": t_anomaly,
        "TERM_ABTEST": t_abtest,
        "YT_REACH_SVG": charts["yt_reach"],
        "TT_REACH_SVG": charts["tt_reach"],
        "YT_ER_SVG": charts["yt_er"],
        "REACH_BEFORE": f"{f['reach_before']:,.0f}",
        "REACH_AFTER": f"{f['reach_after']:,.0f}",
        # U+2212 minus, not a hyphen — it aligns with digits in tabular figures.
        "REACH_CHANGE": f"{f['reach_change']:.1f}%".replace("-", "−"),
        "REACH_DROP": f"{abs(f['reach_change']):.0f}%",   # for running prose
        "ER_BEFORE": f"{f['er_before']:.2f}%",
        "ER_AFTER": f"{f['er_after']:.2f}%",
        "ER_CHANGE": f"{f['er_change']:.1f}%".replace("-", "−"),
        "POSTS_BEFORE": str(f["posts_before"]),
        "POSTS_AFTER": str(f["posts_after"]),
        "TOTAL_POSTS": f"{len(rows):,}",
        "PLATFORM_COUNT": str(len(platforms)),
        "TOOL_COUNT": str(tools),
        "TT_VERDICT": tt_shift,
        "TT_OTHER": str(tt_other),
    }

    tpl = open(os.path.join(HERE, "report.template.html"), encoding="utf-8").read()
    missing = {m for m in re.findall(r"\{\{(\w+)\}\}", tpl)} - set(values)
    if missing:
        raise BuildError(f"template needs values not produced by the build: "
                         f"{', '.join(sorted(missing))}")
    for k, v in values.items():
        tpl = tpl.replace("{{" + k + "}}", v)

    left = re.findall(r"\{\{\w+\}\}", tpl)
    if left:
        raise BuildError(f"unfilled placeholders: {left}")

    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(tpl)
    return values


def main(argv=None):
    ap = argparse.ArgumentParser(prog="build", description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="verify the committed report matches a fresh build")
    a = ap.parse_args(argv)

    committed = os.path.join(HERE, "report.html")
    try:
        with tempfile.TemporaryDirectory() as work:
            target = os.path.join(work, "report.html") if a.check else committed
            values = build(work, target)

            if a.check:
                if not os.path.exists(committed):
                    raise BuildError("demo/report.html is missing")
                fresh = open(target, encoding="utf-8").read()
                have = open(committed, encoding="utf-8").read()
                if fresh != have:
                    raise BuildError(
                        "demo/report.html is stale — it no longer matches what "
                        "the current code produces. Run: python3 demo/build.py")
                print("demo/report.html matches a fresh build")
                return 0
    except BuildError as e:
        print(f"build: {e}", file=sys.stderr)
        return 2

    print(f"demo/report.html  ({os.path.getsize(committed):,} bytes)")
    print(f"  reach   {values['REACH_BEFORE']} -> {values['REACH_AFTER']}  "
          f"({values['REACH_CHANGE']})")
    print(f"  er      {values['ER_BEFORE']} -> {values['ER_AFTER']}  "
          f"({values['ER_CHANGE']})")
    print(f"  posts   {values['TOTAL_POSTS']} across "
          f"{values['PLATFORM_COUNT']} platforms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
