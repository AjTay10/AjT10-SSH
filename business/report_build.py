#!/usr/bin/env python3
"""report_build — a client-ready diligence report from raw CSVs, in one command.

This is the delivery half of the practice. The analysis lives in tools/; this
arranges it into something a buyer or seller can read, and refuses to state
anything the data does not support.

    python3 business/report_build.py --client "Listing 12345" \\
        --pages pages.csv --page-item url --page-value pageviews \\
        --page-date published \\
        --revenue rev.csv --rev-item source --rev-value amount \\
        --traffic monthly.csv --traffic-date month --traffic-value sessions \\
        --out report.html

Only --client and --out are required; supply whichever inputs the client
actually has and the matching sections appear. Every section is omitted rather
than faked when its input is missing, and the report says which ones were
skipped — a gap the reader can see is worth more than a section you invented.

Self-contained HTML: no CDN, no fonts, no fetch. Stdlib only.
"""

from __future__ import annotations

import argparse
import html
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))

import anomaly            # noqa: E402
import chartkit           # noqa: E402
import concentration      # noqa: E402
import csvio              # noqa: E402


class ReportError(ValueError):
    pass


def esc(s):
    return html.escape(str(s), quote=True)


def fmt(v):
    return concentration.fmt(v)


# --------------------------------------------------------------------------
# analysis
# --------------------------------------------------------------------------

def load_items(path, item_col, value_col, date_col=None):
    rows = csvio.read_rows(path)
    cols = [item_col, value_col] + ([date_col] if date_col else [])
    csvio.require(rows, *cols, origin=path)

    items, dated, blank, negative = [], [], 0, 0
    for r in rows:
        v = concentration.num(r[value_col], value_col)
        if v is None:
            blank += 1
            continue
        if v < 0:
            negative += 1
            continue
        if v == 0:
            continue
        name = str(r[item_col]).strip() or "(unnamed)"
        items.append((name, v))
        if date_col:
            d = concentration.parse_date(r[date_col], date_col)
            if d:
                dated.append((name, v, d))
    if len(items) < 3:
        raise ReportError(
            f"{path}: only {len(items)} item(s) with a positive {value_col!r}. "
            f"Concentration is not a meaningful question below 3.")
    return items, dated, blank, negative


def load_series(path, date_col, value_col):
    rows = csvio.read_rows(path)
    csvio.require(rows, date_col, value_col, origin=path)
    pts = []
    for r in rows:
        v = anomaly.num(r[value_col], value_col)
        if v is None:
            continue
        pts.append((anomaly.parse_date(r[date_col]), v))
    pts.sort(key=lambda p: p[0])
    if len(pts) < 6:
        raise ReportError(
            f"{path}: only {len(pts)} usable rows. Trend analysis needs at "
            f"least 6 periods; ask the seller for a longer history.")
    return pts


def findings(page_res, page_vints, page_repl, rev_res, traffic):
    """Ranked, plain-language findings. Most price-relevant first."""
    out = []

    if rev_res:
        top1 = rev_res["shares"].get("top1", 0)
        if top1 > 0.30:
            out.append(("critical", "Revenue concentration",
                        f"One source is {top1*100:.0f}% of revenue. A "
                        f"renegotiation or non-renewal there halves the "
                        f"business. Establish contract length and history "
                        f"before anything else."))
        elif top1 > 0.15:
            out.append(("major", "Revenue concentration",
                        f"The largest revenue source is {top1*100:.0f}% of "
                        f"the total. Material, not yet existential."))

    if page_res:
        top1 = page_res["shares"].get("top1", 0)
        mult = page_res["top1_x_even_share"]
        if top1 > 0.10 or mult >= 10:
            out.append(("critical" if top1 > 0.20 else "major",
                        "Traffic concentration",
                        f"One page is {top1*100:.0f}% of traffic — "
                        f"{mult:.0f}x an even share. Removing the top 3 costs "
                        f"{page_res['fragility'].get('drop_top3', {}).get('pct_lost', 0):.0f}% "
                        f"of the total. This asset is its top pages."))
        if page_res["effective_pct"] < 0.25 and page_res["items"] >= 10:
            out.append(("major", "Effective inventory",
                        f"{page_res['items']:,} pages behave like "
                        f"{page_res['effective_n']:.0f}. The page count in the "
                        f"listing overstates what is actually working."))

    if page_vints and len(page_vints) >= 3:
        newest = page_vints[-1]
        if newest["share"] < 0.05:
            out.append(("major", "Recent output is not landing",
                        f"The newest cohort ({newest['period']}) contributes "
                        f"{newest['share']*100:.1f}% of the total across "
                        f"{newest['items']:,} items."))
        counts = [v["items"] for v in page_vints]
        meds = [v["median_per_item"] for v in page_vints]
        if counts[-1] > counts[0] and meds[-1] < meds[0] * 0.6:
            out.append(("critical", "Production up, yield down",
                        f"Output rose from {counts[0]:,} to {counts[-1]:,} "
                        f"items per period while median value per item fell "
                        f"from {fmt(meds[0])} to {fmt(meds[-1])}. The business "
                        f"is working harder to stand still — a pattern no "
                        f"total reveals."))

    if page_repl and page_repl["ratio"] < 0.5:
        out.append(("note", "Replacement ratio",
                    f"New work is at {page_repl['ratio']:.2f}x the median of "
                    f"old work. Older items have had longer to accumulate, so "
                    f"this is biased in their favour and is suggestive rather "
                    f"than conclusive."))

    if traffic:
        downs = [s for s in traffic["shifts"] if s["direction"] == "down"]
        if downs:
            last = downs[-1]
            span = "" if last["until"] == last["date"] else f" through {last['until']}"
            out.append(("critical", "Sustained decline detected",
                        f"A level shift down begins {last['date']}{span} and "
                        f"is not explained by normal variation. Any average "
                        f"spanning that date understates the current run rate."))
        if not downs and not traffic["flags"]:
            out.append(("clear", "Trend",
                        "No sustained level shift and no point anomalies at "
                        "the tested threshold. The series is stable — which is "
                        "a finding, not an absence of one."))

    if not out:
        out.append(("clear", "No material flag",
                    "Nothing in the supplied data meets the thresholds used "
                    "here. That is not the same as a clean business — see "
                    "what was not examined."))
    order = {"critical": 0, "major": 1, "note": 2, "clear": 3}
    out.sort(key=lambda f: order[f[0]])
    return out


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

CSS = """
:root{
  --ground:#fcfcfd;--surface:#f3f5f8;--sunk:#e9edf2;--ink:#151a21;
  --ink-2:#4b5563;--ink-3:#7a8595;--rule:#dee3ea;
  --accent:#2f5fd0;--accent-soft:#e8eefb;
  --critical:#b3402e;--critical-soft:#fbeae7;
  --major:#9a6414;--major-soft:#fbf1df;
  --clear:#1a7a55;--clear-soft:#e6f4ee;
  --serif:Charter,"Bitstream Charter","Sitka Text",Cambria,Georgia,serif;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
  --mono:ui-monospace,"SF Mono",SFMono-Regular,"Cascadia Mono",Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --ground:#0e1115;--surface:#161a20;--sunk:#1d232b;--ink:#e8ecf2;
  --ink-2:#a2acba;--ink-3:#79838f;--rule:#262d36;
  --accent:#7ea3f4;--accent-soft:#182234;
  --critical:#ef7f6d;--critical-soft:#2d1a16;
  --major:#d9a441;--major-soft:#2a2114;
  --clear:#4cbc90;--clear-soft:#12271f;
}}
:root[data-theme="dark"]{
  --ground:#0e1115;--surface:#161a20;--sunk:#1d232b;--ink:#e8ecf2;
  --ink-2:#a2acba;--ink-3:#79838f;--rule:#262d36;
  --accent:#7ea3f4;--accent-soft:#182234;
  --critical:#ef7f6d;--critical-soft:#2d1a16;
  --major:#d9a441;--major-soft:#2a2114;
  --clear:#4cbc90;--clear-soft:#12271f;
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);
font-family:var(--serif);font-size:16.5px;line-height:1.62}
.page{max-width:1060px;margin:0 auto;padding:0 26px 90px}
.col{max-width:648px}
header{padding:52px 0 30px;border-bottom:2px solid var(--ink)}
.eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.14em;
text-transform:uppercase;color:var(--ink-3);margin-bottom:16px}
h1{font-family:var(--sans);font-weight:670;letter-spacing:-.022em;
font-size:clamp(28px,4vw,40px);line-height:1.1;margin:0 0 14px;
text-wrap:balance;max-width:22ch}
.meta{display:flex;flex-wrap:wrap;gap:0 28px;margin-top:22px;
font-family:var(--mono);font-size:11.5px;letter-spacing:.04em;
text-transform:uppercase;color:var(--ink-3)}
.meta b{color:var(--ink-2);font-weight:500}
section{margin-top:56px}
h2{font-family:var(--sans);font-size:12px;font-weight:660;letter-spacing:.13em;
text-transform:uppercase;color:var(--ink-3);margin:0 0 18px;
padding-bottom:9px;border-bottom:1px solid var(--rule)}
h3{font-family:var(--sans);font-size:19px;font-weight:630;margin:0 0 8px;
letter-spacing:-.012em}
p{margin:0 0 15px}
.f{display:grid;grid-template-columns:96px 1fr;gap:0 20px;padding:19px 0;
border-bottom:1px solid var(--rule)}
.f:last-child{border-bottom:0}
.sev{font-family:var(--mono);font-size:10px;letter-spacing:.1em;
text-transform:uppercase;padding:4px 8px;border-radius:2px;
height:fit-content;text-align:center;border:1px solid}
.sev.critical{color:var(--critical);background:var(--critical-soft);
border-color:var(--critical)}
.sev.major{color:var(--major);background:var(--major-soft);border-color:var(--major)}
.sev.note{color:var(--ink-3);background:var(--sunk);border-color:var(--rule)}
.sev.clear{color:var(--clear);background:var(--clear-soft);border-color:var(--clear)}
.f .t{font-family:var(--sans);font-weight:640;font-size:16px;margin-bottom:5px}
.f .b{color:var(--ink-2);font-size:15.5px;max-width:74ch}
.readout{display:grid;gap:1px;background:var(--rule);border:1px solid var(--rule);
grid-template-columns:repeat(auto-fit,minmax(172px,1fr));margin-top:6px}
.cell{background:var(--ground);padding:16px 18px}
.cell .l{font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;
text-transform:uppercase;color:var(--ink-3);margin-bottom:6px}
.cell .v{font-family:var(--sans);font-size:25px;font-weight:640;
letter-spacing:-.02em;font-variant-numeric:tabular-nums;line-height:1.1}
.cell .d{font-family:var(--mono);font-size:11px;color:var(--ink-3);margin-top:4px}
.card{background:var(--surface);border:1px solid var(--rule);border-radius:4px;
padding:8px;overflow-x:auto;margin-top:16px}
.card svg{display:block;max-width:100%;height:auto}
.tw{overflow-x:auto;border:1px solid var(--rule);border-radius:4px;margin-top:16px}
table{width:100%;border-collapse:collapse;font-family:var(--mono);font-size:12.5px}
th,td{padding:10px 14px;text-align:right;border-bottom:1px solid var(--rule);
white-space:nowrap}
th:first-child,td:first-child{text-align:left}
tr:last-child td{border-bottom:0}
thead th{font-size:10px;letter-spacing:.1em;text-transform:uppercase;
color:var(--ink-3);font-weight:500;background:var(--surface)}
td{font-variant-numeric:tabular-nums}
.note{background:var(--surface);border-left:3px solid var(--accent);
border-radius:0 4px 4px 0;padding:13px 17px;font-size:15px;color:var(--ink-2);
margin-top:16px;max-width:76ch}
.gaps{background:var(--surface);border:1px solid var(--rule);border-radius:4px;
padding:20px 24px;margin-top:6px}
.gaps ul{margin:0;padding-left:20px;color:var(--ink-2);font-size:15.5px}
.gaps li{margin-bottom:8px}
footer{margin-top:64px;padding-top:20px;border-top:1px solid var(--rule);
font-family:var(--mono);font-size:11.5px;color:var(--ink-3);line-height:1.8}
"""


def tile(label, value, sub=""):
    return (f'<div class="cell"><div class="l">{esc(label)}</div>'
            f'<div class="v">{esc(value)}</div>'
            f'<div class="d">{esc(sub)}</div></div>')


def conc_section(title, res, vints, label, unit_label):
    parts = [f"<h2>{esc(title)}</h2>"]
    parts.append('<div class="readout">')
    parts.append(tile("Total", fmt(res["total"]), unit_label))
    parts.append(tile("Effective count",
                      f"{res['effective_n']:.1f}",
                      f"of {res['items']:,} {label}"))
    parts.append(tile("Largest item",
                      f"{res['shares'].get('top1', 0)*100:.0f}%",
                      f"{res['top1_x_even_share']:.0f}x an even share"))
    drop3 = res["fragility"].get("drop_top3", {}).get("pct_lost")
    parts.append(tile("Lose the top 3",
                      f"{drop3:.0f}%" if drop3 is not None else "—",
                      "of the total"))
    parts.append("</div>")

    top = res["top"][:10]
    parts.append('<div class="tw"><table><thead><tr><th>Rank</th>'
                 f'<th>{esc(label.title())}</th><th>Value</th><th>Share</th>'
                 '<th>Cumulative</th></tr></thead><tbody>')
    cum = 0.0
    for i, t in enumerate(top, 1):
        cum += t["share"]
        name = t["name"][:58] + ("…" if len(t["name"]) > 58 else "")
        parts.append(f'<tr><td>{i}</td><td>{esc(name)}</td>'
                     f'<td>{esc(fmt(t["value"]))}</td>'
                     f'<td>{t["share"]*100:.1f}%</td>'
                     f'<td>{cum*100:.1f}%</td></tr>')
    parts.append("</tbody></table></div>")

    if len(top) >= 3:
        parts.append('<div class="card">')
        parts.append(chartkit.hbar(
            [t["name"][:40] for t in top],
            [t["value"] for t in top],
            title=f"Top {len(top)} by share", w=1000))
        parts.append("</div>")

    parts.append(f'<div class="note">Gini {res["gini"]:.2f} — '
                 f'{esc(res["band"])}. Averages across these {esc(label)} '
                 f'describe no actual item and should not be used to project '
                 f'the effect of adding more.</div>')
    return "".join(parts)


def vintage_section(vints, repl):
    parts = ["<h2>Is the value being renewed?</h2>"]
    parts.append('<div class="tw"><table><thead><tr><th>Vintage</th>'
                 '<th>Items</th><th>Total</th><th>Share</th>'
                 '<th>Median / item</th></tr></thead><tbody>')
    for v in vints:
        parts.append(f'<tr><td>{esc(v["period"])}</td><td>{v["items"]:,}</td>'
                     f'<td>{esc(fmt(v["total"]))}</td>'
                     f'<td>{v["share"]*100:.1f}%</td>'
                     f'<td>{esc(fmt(v["median_per_item"]))}</td></tr>')
    parts.append("</tbody></table></div>")

    parts.append('<div class="card">')
    parts.append(chartkit.bar([v["period"] for v in vints],
                              [v["median_per_item"] for v in vints],
                              title="Median value per item, by publish cohort",
                              subtitle="falling bars mean new work earns less "
                                       "than old work did",
                              w=1000, color_by_label=False))
    parts.append("</div>")

    if repl:
        parts.append(
            f'<div class="note">Replacement ratio <b>{repl["ratio"]:.2f}x</b> '
            f'({fmt(repl["new_median"])} newest vs {fmt(repl["old_median"])} '
            f'oldest, per item). Older items have had longer to accumulate, so '
            f'this ratio is biased <i>in favour of old work</i>. '
            + ("A ratio above 1.0 despite that handicap is strong evidence the "
               "asset is being renewed."
               if repl["ratio"] >= 1.0 else
               "A ratio below 1.0 is suggestive but not conclusive — the age "
               "handicap alone could explain it. Settling this needs per-item "
               "performance at equal age, which cumulative totals cannot show.")
            + "</div>")
    return "".join(parts)


def traffic_section(pts, diag, shifts, flags, value_label):
    parts = ["<h2>Is the trend real?</h2>"]
    xs = [d.date().isoformat() for d, _ in pts]
    ys = [v for _, v in pts]

    first, last = ys[0], ys[-1]
    change = (last - first) / first * 100 if first else 0.0
    half = len(ys) // 2
    recent = sum(ys[half:]) / max(1, len(ys) - half)
    early = sum(ys[:half]) / max(1, half)

    parts.append('<div class="readout">')
    parts.append(tile("First → last", f"{change:+.0f}%",
                      f"{fmt(first)} → {fmt(last)}"))
    parts.append(tile("Second half vs first",
                      f"{(recent-early)/early*100:+.0f}%" if early else "—",
                      "period averages"))
    parts.append(tile("Level shifts", str(len(shifts)),
                      "sustained, not spikes"))
    parts.append(tile("Point anomalies", str(len(flags)), "outlier periods"))
    parts.append("</div>")

    parts.append('<div class="card">')
    parts.append(chartkit.line(xs, ys, title=value_label,
                               subtitle="per period as supplied", w=1000, h=340))
    parts.append("</div>")

    if shifts:
        parts.append('<div class="tw"><table><thead><tr><th>From</th>'
                     '<th>Through</th><th>Direction</th><th>Periods</th>'
                     '</tr></thead><tbody>')
        for s in shifts:
            parts.append(f'<tr><td>{esc(s["date"])}</td>'
                         f'<td>{esc(s["until"])}</td>'
                         f'<td>{esc(s["direction"])}</td>'
                         f'<td>{s["points"]}</td></tr>')
        parts.append("</tbody></table></div>")
        parts.append('<div class="note">A sustained level shift is a different '
                     'event from a spike. Any trailing average spanning one of '
                     'these dates blends two regimes and describes neither.</div>')
    else:
        parts.append('<div class="note">No sustained level shift detected. The '
                     'series moves, but not more than its own history predicts.'
                     '</div>')
    return "".join(parts)


def build(a):
    page_res = page_vints = page_repl = None
    rev_res = None
    traffic = None
    gaps = []
    quality = []

    if a.pages:
        items, dated, blank, neg = load_items(a.pages, a.page_item,
                                              a.page_value, a.page_date)
        page_res = concentration.analyze(items, top_n=10)
        if a.page_date:
            if len(dated) >= 4:
                page_vints = concentration.vintages(dated, a.period)
                page_repl = concentration.replacement(page_vints)
            else:
                gaps.append("Publish dates were supplied but fewer than four "
                            "rows carried a usable one, so no vintage analysis "
                            "was possible.")
        else:
            gaps.append("No publish-date column was supplied, so whether the "
                        "asset is being renewed or run down is unknown. This "
                        "is usually the most important open question.")
        if blank:
            quality.append(f"{blank} page row(s) had a blank "
                           f"{a.page_value!r} and were excluded — blank means "
                           f"'not reported', not zero.")
        if neg:
            quality.append(f"{neg} page row(s) were negative and excluded.")
    else:
        gaps.append("No per-page or per-item breakdown was supplied, so "
                    "traffic concentration could not be assessed.")

    if a.revenue:
        items, _, blank, neg = load_items(a.revenue, a.rev_item, a.rev_value)
        rev_res = concentration.analyze(items, top_n=10)
        if blank:
            quality.append(f"{blank} revenue row(s) were blank and excluded.")
        if neg:
            quality.append(f"{neg} revenue row(s) were negative and excluded. "
                           f"Net refunds against their line before re-running.")
    else:
        gaps.append("No revenue breakdown was supplied, so dependence on a "
                    "single advertiser, sponsor, or channel is unknown.")

    if a.traffic:
        pts = load_series(a.traffic, a.traffic_date, a.traffic_value)
        diag = anomaly.detect(pts, a.window, a.z, None)
        shifts = anomaly.cusum(diag)
        flags = [d for d in diag if d["flag"]]
        traffic = {"pts": pts, "diag": diag, "shifts": shifts, "flags": flags}
    else:
        gaps.append("No traffic or revenue time series was supplied, so "
                    "whether the trend is genuine could not be tested.")

    gaps.append("Nothing here verifies that the supplied numbers are truthful. "
                "Confirm them at source — analytics and ad-network access, "
                "read-only, granted by the seller.")

    fs = findings(page_res, page_vints, page_repl, rev_res, traffic)

    # ---- assemble ----
    p = [f'<div class="page"><header>',
         f'<div class="eyebrow">Metric diligence · prepared for {esc(a.prepared_for)}</div>',
         f'<h1>{esc(a.client)}</h1>',
         '<div class="meta">']
    p.append(f'<span><b>{esc(a.date)}</b></span>')
    if page_res:
        p.append(f'<span><b>{page_res["items"]:,}</b> items analyzed</span>')
    if traffic:
        p.append(f'<span><b>{len(traffic["pts"])}</b> periods</span>')
    p.append(f'<span><b>{len(fs)}</b> findings</span>')
    p.append("</div></header>")

    p.append('<section><h2>Findings</h2>')
    for sev, title, body in fs:
        p.append(f'<div class="f"><div class="sev {sev}">{esc(sev)}</div>'
                 f'<div><div class="t">{esc(title)}</div>'
                 f'<div class="b">{esc(body)}</div></div></div>')
    p.append("</section>")

    if rev_res:
        p.append("<section>" + conc_section(
            "What the revenue rests on", rev_res, None, "sources",
            "as supplied") + "</section>")
    if page_res:
        p.append("<section>" + conc_section(
            "What the traffic rests on", page_res, page_vints, "pages",
            "as supplied") + "</section>")
    if page_vints:
        p.append("<section>" + vintage_section(page_vints, page_repl)
                 + "</section>")
    if traffic:
        p.append("<section>" + traffic_section(
            traffic["pts"], traffic["diag"], traffic["shifts"],
            traffic["flags"], a.traffic_value) + "</section>")

    p.append('<section><h2>What this report does not establish</h2>'
             '<div class="gaps"><ul>')
    for g in gaps + quality:
        p.append(f"<li>{esc(g)}</li>")
    p.append("</ul></div></section>")

    p.append(
        '<footer>'
        'This report presents descriptive statistics computed from data '
        'supplied by the client. It is not a valuation, an appraisal, an audit, '
        'or investment advice, and no recommendation to buy, sell, or price at '
        'any figure is made or implied.<br>'
        'The analysis cannot establish whether the underlying figures are '
        'accurate or complete; verifying them at source remains the reader\'s '
        'responsibility.<br>'
        f'Generated {esc(a.date)} · self-contained, no network calls'
        '</footer></div>')
    return "".join(p)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="report_build",
                                 description=__doc__.split("\n")[0])
    ap.add_argument("--client", required=True, help="asset name or listing ref")
    ap.add_argument("--prepared-for", default="the prospective buyer")
    ap.add_argument("--out", required=True)
    ap.add_argument("--date", default="", help="report date; defaults to today")

    ap.add_argument("--pages", help="per-page or per-item CSV")
    ap.add_argument("--page-item", default="url")
    ap.add_argument("--page-value", default="pageviews")
    ap.add_argument("--page-date", help="publish date column, enables vintages")

    ap.add_argument("--revenue", help="revenue-by-source CSV")
    ap.add_argument("--rev-item", default="source")
    ap.add_argument("--rev-value", default="amount")

    ap.add_argument("--traffic", help="time series CSV")
    ap.add_argument("--traffic-date", default="date")
    ap.add_argument("--traffic-value", default="sessions")

    ap.add_argument("--period", default="year",
                    choices=["month", "quarter", "year"])
    ap.add_argument("--window", type=int, default=12)
    ap.add_argument("--z", type=float, default=3.0)
    a = ap.parse_args(argv)

    try:
        if not (a.pages or a.revenue or a.traffic):
            raise ReportError(
                "supply at least one of --pages, --revenue, or --traffic; "
                "there is nothing to analyze otherwise")
        if not a.date:
            a.date = datetime.now().strftime("%d %B %Y")
        body = build(a)
    except (ReportError, concentration.ConcentrationError,
            anomaly.AnomalyError, chartkit.ChartError,
            csvio.CsvError, OSError) as e:
        print(f"report_build: {e}", file=sys.stderr)
        return 2

    doc = (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>{esc(a.client)} — metric diligence</title>'
           f'<style>{CSS}</style></head><body>{body}</body></html>')
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(doc)
    print(f"{a.out}  ({os.path.getsize(a.out):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
