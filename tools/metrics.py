#!/usr/bin/env python3
"""metrics — funnels, cohorts, retention, and growth decomposition from CSV.

The point is to stop eyeballing spreadsheets. Every subcommand prints a table
and can emit JSON so the result feeds a chart or a dashboard.

    python3 tools/metrics.py funnel   --csv events.csv --user user_id --step step \\
        --order impression,click,signup,purchase
    python3 tools/metrics.py retention --csv events.csv --user user_id --date date \\
        --period week --periods 8
    python3 tools/metrics.py cohort   --csv users.csv --user id --date signup_date \\
        --value revenue --period month
    python3 tools/metrics.py growth   --csv daily.csv --date date --value followers

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import csvio  # noqa: E402

DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%b %d, %Y", "%d %b %Y")


class MetricError(ValueError):
    pass


def parse_date(v, field="date"):
    if isinstance(v, (date, datetime)):
        return v.date() if isinstance(v, datetime) else v
    s = str(v).strip()
    if not s:
        raise MetricError(f"{field}: empty date")
    if s.isdigit() and len(s) in (10, 13):  # epoch seconds / millis
        ts = int(s) / (1000 if len(s) == 13 else 1)
        return datetime.utcfromtimestamp(ts).date()
    for f in DATE_FORMATS:
        try:
            return datetime.strptime(s[:len(f) + 8], f).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        raise MetricError(f"{field}: cannot parse date {v!r}")


def num(v, field="value", default=0.0):
    s = str(v).strip().replace(",", "").replace("%", "").replace("$", "")
    if s == "":
        return default
    try:
        return float(s)
    except ValueError:
        raise MetricError(f"{field}: {v!r} is not a number")


def read_csv(path):
    return csvio.read_rows(path)


def require(rows, *cols):
    csvio.require(rows, *cols)


def bucket(d: date, period: str) -> str:
    if period == "day":
        return d.isoformat()
    if period == "week":
        start = d - timedelta(days=d.weekday())
        return start.isoformat()
    if period == "month":
        return f"{d.year:04d}-{d.month:02d}"
    raise MetricError(f"unknown period {period!r} (day|week|month)")


# --------------------------------------------------------------------------

def cmd_funnel(a):
    rows = read_csv(a.csv)
    require(rows, a.user, a.step)
    order = [s.strip() for s in a.order.split(",") if s.strip()]
    if len(order) < 2:
        raise MetricError("--order needs at least two steps")
    seen = {s: set() for s in order}
    unknown = set()
    for r in rows:
        st = (r.get(a.step) or "").strip()
        uid = (r.get(a.user) or "").strip()
        if not uid:
            continue
        if st in seen:
            seen[st].add(uid)
        elif st:
            unknown.add(st)

    # Strict funnel: to be counted at step N you must appear at every prior step.
    result, carried = [], None
    for i, s in enumerate(order):
        cur = seen[s] if carried is None else (seen[s] & carried)
        if not a.strict:
            cur = seen[s]
        carried = cur
        top = len(result[0]["users"]) if result else len(cur)
        prev = len(result[-1]["users"]) if result else len(cur)
        result.append({
            "step": s, "users": cur, "count": len(cur),
            "pct_of_top": (len(cur) / top * 100) if top else 0.0,
            "pct_of_prev": (len(cur) / prev * 100) if prev else 0.0,
            "dropoff": prev - len(cur),
        })

    out = [{k: v for k, v in r.items() if k != "users"} for r in result]
    if a.json:
        print(json.dumps({"funnel": out, "unknown_steps": sorted(unknown)}, indent=2))
        return 0
    print(f"{'step':<22}{'users':>10}{'% top':>9}{'% prev':>9}{'drop':>9}")
    print("-" * 59)
    for r in out:
        print(f"{r['step'][:21]:<22}{r['count']:>10,}{r['pct_of_top']:>8.1f}%"
              f"{r['pct_of_prev']:>8.1f}%{r['dropoff']:>9,}")
    worst = max(out[1:], key=lambda r: 100 - r["pct_of_prev"], default=None)
    if worst:
        print(f"\nbiggest leak: {worst['step']} "
              f"({100 - worst['pct_of_prev']:.1f}% lost from the prior step)")
    if unknown:
        print(f"note: {len(unknown)} step value(s) not in --order were ignored: "
              f"{', '.join(sorted(unknown)[:6])}")
    return 0


def cmd_retention(a):
    rows = read_csv(a.csv)
    require(rows, a.user, a.date)
    acts = defaultdict(set)
    for r in rows:
        uid = (r.get(a.user) or "").strip()
        if not uid:
            continue
        acts[uid].add(bucket(parse_date(r[a.date], a.date), a.period))

    cohorts = defaultdict(set)
    for uid, buckets in acts.items():
        cohorts[min(buckets)].add(uid)

    grid, labels = [], sorted(cohorts)
    for c in labels:
        members = cohorts[c]
        row = []
        for n in range(a.periods):
            target = _shift(c, n, a.period)
            kept = sum(1 for u in members if target in acts[u])
            row.append(round(kept / len(members) * 100, 1) if members else 0.0)
        grid.append(row)

    if a.json:
        print(json.dumps({
            "period": a.period, "cohorts": labels,
            "sizes": [len(cohorts[c]) for c in labels],
            "retention_pct": grid}, indent=2))
        return 0
    head = "".join(f"{'P'+str(i):>7}" for i in range(a.periods))
    print(f"{'cohort':<12}{'size':>7}{head}")
    print("-" * (19 + 7 * a.periods))
    for c, row in zip(labels, grid):
        cells = "".join(f"{v:>6.1f}%" if v else f"{'·':>7}" for v in row)
        print(f"{c:<12}{len(cohorts[c]):>7,}{cells}")
    if len(grid) and a.periods > 1:
        p1 = [g[1] for g in grid if len(g) > 1]
        if p1:
            print(f"\nmean P1 retention: {sum(p1)/len(p1):.1f}%  "
                  f"(best {max(p1):.1f}%, worst {min(p1):.1f}%)")
    return 0


def _shift(b: str, n: int, period: str) -> str:
    if period == "month":
        y, m = int(b[:4]), int(b[5:7])
        m += n
        y += (m - 1) // 12
        m = (m - 1) % 12 + 1
        return f"{y:04d}-{m:02d}"
    d = date.fromisoformat(b) + timedelta(days=n * (7 if period == "week" else 1))
    return d.isoformat()


def cmd_cohort(a):
    rows = read_csv(a.csv)
    require(rows, a.user, a.date)
    agg = defaultdict(lambda: {"n": 0, "sum": 0.0})
    for r in rows:
        b = bucket(parse_date(r[a.date], a.date), a.period)
        agg[b]["n"] += 1
        if a.value:
            agg[b]["sum"] += num(r.get(a.value, 0), a.value)
    labels = sorted(agg)
    out = [{"cohort": b, "users": agg[b]["n"],
            "total": round(agg[b]["sum"], 2),
            "per_user": round(agg[b]["sum"] / agg[b]["n"], 2) if agg[b]["n"] else 0.0}
           for b in labels]
    if a.json:
        print(json.dumps(out, indent=2))
        return 0
    print(f"{'cohort':<12}{'users':>9}{'total':>14}{'per user':>12}")
    print("-" * 47)
    for r in out:
        print(f"{r['cohort']:<12}{r['users']:>9,}{r['total']:>14,.2f}{r['per_user']:>12,.2f}")
    return 0


def cmd_growth(a):
    rows = read_csv(a.csv)
    require(rows, a.date, a.value)
    pts = sorted(((parse_date(r[a.date], a.date), num(r[a.value], a.value))
                  for r in rows), key=lambda p: p[0])
    if len(pts) < 2:
        raise MetricError("growth needs at least two dated rows")
    first, last = pts[0], pts[-1]
    days = max(1, (last[0] - first[0]).days)
    total = last[1] - first[1]
    cagr = ((last[1] / first[1]) ** (365.0 / days) - 1) * 100 if first[1] > 0 else None
    deltas = [(pts[i][0], pts[i][1] - pts[i - 1][1]) for i in range(1, len(pts))]
    best = max(deltas, key=lambda d: d[1])
    worst = min(deltas, key=lambda d: d[1])
    window = deltas[-7:]
    out = {
        "from": first[0].isoformat(), "to": last[0].isoformat(), "days": days,
        "start": first[1], "end": last[1], "absolute_change": round(total, 4),
        "pct_change": round((total / first[1] * 100), 2) if first[1] else None,
        "avg_per_day": round(total / days, 4),
        "annualized_pct": round(cagr, 2) if cagr is not None else None,
        "best_day": [best[0].isoformat(), round(best[1], 4)],
        "worst_day": [worst[0].isoformat(), round(worst[1], 4)],
        "last_7_pts_avg": round(sum(d[1] for d in window) / len(window), 4),
    }
    if a.json:
        print(json.dumps(out, indent=2))
        return 0
    for k, v in out.items():
        print(f"{k.replace('_',' '):<20} {v}")
    if out["annualized_pct"] is not None and out["last_7_pts_avg"] < 0 < out["absolute_change"]:
        print("\nflag: net growth is positive but the recent window is negative — "
              "the trend has turned. Do not report the headline number alone.")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="metrics", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("funnel", help="conversion by ordered step")
    f.add_argument("--csv", required=True)
    f.add_argument("--user", required=True)
    f.add_argument("--step", required=True)
    f.add_argument("--order", required=True, help="comma-separated step names, in order")
    f.add_argument("--strict", action="store_true", default=True,
                   help="require every prior step (default)")
    f.add_argument("--loose", dest="strict", action="store_false",
                   help="count each step independently")
    f.add_argument("--json", action="store_true")
    f.set_defaults(fn=cmd_funnel)

    r = sub.add_parser("retention", help="cohort retention grid")
    r.add_argument("--csv", required=True)
    r.add_argument("--user", required=True)
    r.add_argument("--date", required=True)
    r.add_argument("--period", default="week", choices=["day", "week", "month"])
    r.add_argument("--periods", type=int, default=8)
    r.add_argument("--json", action="store_true")
    r.set_defaults(fn=cmd_retention)

    c = sub.add_parser("cohort", help="cohort size and value")
    c.add_argument("--csv", required=True)
    c.add_argument("--user", required=True)
    c.add_argument("--date", required=True)
    c.add_argument("--value")
    c.add_argument("--period", default="month", choices=["day", "week", "month"])
    c.add_argument("--json", action="store_true")
    c.set_defaults(fn=cmd_cohort)

    g = sub.add_parser("growth", help="change, rate, and trend reversal check")
    g.add_argument("--csv", required=True)
    g.add_argument("--date", required=True)
    g.add_argument("--value", required=True)
    g.add_argument("--json", action="store_true")
    g.set_defaults(fn=cmd_growth)

    a = p.parse_args(argv)
    try:
        return a.fn(a)
    except (MetricError, csvio.CsvError, OSError) as e:
        print(f"metrics: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
