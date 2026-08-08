#!/usr/bin/env python3
"""dashboard — one self-contained HTML page from normalized social data.

Takes the output of social_ingest.py and renders stat tiles, a trend line,
a platform comparison, and a posting-time heatmap. No CDN, no fonts, no
fetch — safe to publish as an Artifact under a strict CSP.

    python3 tools/social_ingest.py --csv yt.csv --platform youtube --out norm.csv
    python3 tools/dashboard.py --csv norm.csv --out dashboard.html --title "Q3"

Stdlib only; imports chartkit from the same directory.
"""

from __future__ import annotations

import argparse
import html
import os
import sys
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chartkit  # noqa: E402
import csvio  # noqa: E402


class DashError(ValueError):
    pass


def esc(s):
    return html.escape(str(s), quote=True)


def f(v):
    return chartkit._fmt(v)


def load(path):
    rows = csvio.read_rows(path)
    need = {"date", "platform"}
    missing = need - set(rows[0].keys())
    if missing:
        raise DashError(
            f"{path} is missing {', '.join(sorted(missing))}. Run it through "
            f"social_ingest.py first.")
    return rows


def n(r, k):
    v = (r.get(k) or "").strip()
    if not v:
        return 0.0
    try:
        return float(v.replace(",", ""))
    except ValueError:
        return 0.0


def tile(label, value, sub="", spark=""):
    return (f'<div class="tile"><div class="tl">{esc(label)}</div>'
            f'<div class="tv">{esc(value)}</div>'
            f'<div class="ts">{esc(sub)}</div>{spark}</div>')


CSS = """
:root{--bg:#ffffff;--card:#f6f7f9;--ink:#16181d;--muted:#5c6370;--line:#e4e7ec;
--accent:#3b6ef2}
:root:not([data-theme="light"]){}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
--bg:#14161a;--card:#1c1f25;--ink:#eef0f4;--muted:#9aa3b0;--line:#2b3038;
--accent:#79a0ff}}
:root[data-theme="dark"]{--bg:#14161a;--card:#1c1f25;--ink:#eef0f4;
--muted:#9aa3b0;--line:#2b3038;--accent:#79a0ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:32px 20px 64px}
h1{font-size:26px;margin:0 0 4px}
.lede{color:var(--muted);margin:0 0 28px;font-size:14px}
h2{font-size:15px;text-transform:uppercase;letter-spacing:.06em;
color:var(--muted);margin:36px 0 12px;font-weight:600}
.tiles{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(168px,1fr))}
.tile{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:14px 16px}
.tl{font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.tv{font-size:26px;font-weight:650;margin:4px 0 2px;font-variant-numeric:tabular-nums}
.ts{font-size:12px;color:var(--muted)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:8px;overflow-x:auto}
.card svg{display:block;max-width:100%;height:auto}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{text-align:right;padding:8px 10px;border-bottom:1px solid var(--line)}
th:first-child,td:first-child{text-align:left}
th{color:var(--muted);font-weight:600;font-size:11.5px;text-transform:uppercase;
letter-spacing:.04em}
.scroll{overflow-x:auto}
.note{background:var(--card);border-left:3px solid var(--accent);border-radius:0 8px 8px 0;
padding:12px 16px;font-size:13.5px;color:var(--muted);margin-top:12px}
footer{margin-top:44px;padding-top:16px;border-top:1px solid var(--line);
color:var(--muted);font-size:12px}
"""


def build(rows, title, generated):
    by_date = defaultdict(lambda: defaultdict(float))
    by_plat = defaultdict(lambda: defaultdict(float))
    for r in rows:
        d = (r.get("date") or "").strip()[:10]
        p = (r.get("platform") or "unknown").strip()
        for k in ("impressions", "engagements", "reach", "followers_delta",
                  "video_views", "likes", "comments", "shares", "saves"):
            v = n(r, k)
            if d:
                by_date[d][k] += v
            by_plat[p][k] += v
        if d:
            by_date[d]["posts"] += 1
        by_plat[p]["posts"] += 1

    dates = sorted(d for d in by_date if d)
    imps = [by_date[d]["impressions"] or by_date[d]["video_views"] for d in dates]
    engs = [by_date[d]["engagements"] for d in dates]

    total_imp = sum(imps)
    total_eng = sum(engs)
    total_posts = len(rows)
    er = (total_eng / total_imp * 100) if total_imp else 0.0
    followers = sum(by_plat[p]["followers_delta"] for p in by_plat)

    half = len(imps) // 2
    trend = ""
    if half >= 2:
        a1 = sum(imps[:half]) / max(1, half)
        a2 = sum(imps[half:]) / max(1, len(imps) - half)
        if a1:
            trend = f"{(a2-a1)/a1*100:+.0f}% vs first half"

    parts = [f'<h1>{esc(title)}</h1>',
             f'<p class="lede">{len(rows):,} posts across '
             f'{len(by_plat)} platform(s) · '
             f'{esc(dates[0] if dates else "—")} → {esc(dates[-1] if dates else "—")}</p>']

    parts.append('<div class="tiles">')
    parts.append(tile("Impressions", f(total_imp), trend,
                      chartkit.sparkline(imps) if len(imps) > 2 else ""))
    parts.append(tile("Engagements", f(total_eng), f"{er:.2f}% engagement rate",
                      chartkit.sparkline(engs) if len(engs) > 2 else ""))
    parts.append(tile("Posts", f"{total_posts:,}",
                      f"{total_posts/max(1,len(dates)):.1f}/day" if dates else ""))
    parts.append(tile("Net followers", f(followers),
                      f"{followers/max(1,total_posts):.1f} per post"))
    parts.append("</div>")

    if len(dates) > 1:
        parts.append("<h2>Reach over time</h2><div class='card'>")
        parts.append(chartkit.line(
            dates, {"impressions": imps, "engagements": engs},
            title="", w=1040, h=340))
        parts.append("</div>")

    if len(by_plat) > 1:
        plats = sorted(by_plat, key=lambda p: -by_plat[p]["impressions"])
        parts.append("<h2>Platform comparison</h2><div class='card'>")
        parts.append(chartkit.hbar(
            plats, [by_plat[p]["impressions"] or by_plat[p]["video_views"]
                    for p in plats], title="Impressions by platform", w=1040))
        parts.append("</div>")
        parts.append('<div class="note">Impression definitions differ per platform. '
                     'A TikTok view counts at 0 seconds; a YouTube view needs ~30. '
                     'Rank within a platform over time; do not read across bars as '
                     'a quality ranking.</div>')

    # weekday x week heatmap of impressions
    if len(dates) >= 14:
        try:
            weeks = defaultdict(lambda: [None] * 7)
            for d in dates:
                dt = datetime.fromisoformat(d)
                iso = dt.isocalendar()
                key = f"{iso[0]}-W{iso[1]:02d}"
                weeks[key][dt.weekday()] = by_date[d]["impressions"] or \
                    by_date[d]["video_views"]
            keys = sorted(weeks)[-12:]
            parts.append("<h2>When reach actually lands</h2><div class='card'>")
            parts.append(chartkit.heatmap(
                keys, ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                [weeks[k] for k in keys], title="Impressions by weekday", w=1040))
            parts.append("</div>")
        except (ValueError, chartkit.ChartError):
            pass

    top = sorted(rows, key=lambda r: -(n(r, "impressions") or n(r, "video_views")))[:12]
    if top:
        parts.append("<h2>Top posts</h2><div class='card scroll'><table>")
        parts.append("<tr><th>Post</th><th>Platform</th><th>Date</th>"
                     "<th>Impressions</th><th>Engagements</th><th>ER</th></tr>")
        for r in top:
            imp = n(r, "impressions") or n(r, "video_views")
            eng = n(r, "engagements")
            t = (r.get("title") or r.get("post_id") or "—")[:70]
            rate = f"{eng/imp*100:.2f}%" if imp else "—"
            parts.append(
                f"<tr><td>{esc(t)}</td><td>{esc(r.get('platform',''))}</td>"
                f"<td>{esc((r.get('date') or '')[:10])}</td><td>{esc(f(imp))}</td>"
                f"<td>{esc(f(eng))}</td><td>{esc(rate)}</td></tr>")
        parts.append("</table></div>")

        worst = [r for r in rows if (n(r, "impressions") or n(r, "video_views")) > 0]
        worst.sort(key=lambda r: n(r, "engagements") /
                   (n(r, "impressions") or n(r, "video_views")))
        if len(worst) >= 5:
            b = worst[0]
            parts.append(
                f'<div class="note">Lowest engagement rate: '
                f'<strong>{esc((b.get("title") or b.get("post_id") or "—")[:60])}</strong> '
                f'on {esc(b.get("platform",""))}. The bottom of this list teaches more '
                f'than the top of the last one — a viral post is usually luck, a dead '
                f'post is usually a repeatable mistake.</div>')

    parts.append(f'<footer>Generated {esc(generated)} · self-contained, no network '
                 f'calls · numbers are as-exported and inherit each platform\'s '
                 f'counting rules</footer>')
    return "".join(parts)


def main(argv=None):
    p = argparse.ArgumentParser(prog="dashboard", description=__doc__.split("\n")[0])
    p.add_argument("--csv", required=True, help="normalized CSV from social_ingest")
    p.add_argument("--out", help="write HTML here (default stdout)")
    p.add_argument("--title", default="Social performance")
    p.add_argument("--generated", default="", help="timestamp string to stamp")
    a = p.parse_args(argv)
    try:
        rows = load(a.csv)
        body = build(rows, a.title, a.generated or "on demand")
    except (DashError, csvio.CsvError, OSError, chartkit.ChartError) as e:
        print(f"dashboard: {e}", file=sys.stderr)
        return 2
    doc = (f'<!doctype html><html><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>{esc(a.title)}</title><style>{CSS}</style></head>'
           f'<body><div class="wrap">{body}</div></body></html>')
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(doc)
        print(a.out)
    else:
        sys.stdout.write(doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
