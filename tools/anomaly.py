#!/usr/bin/env python3
"""anomaly — find the days that actually broke, not the ones that look spiky.

Rolling median + MAD instead of mean + stdev, because a single viral post
poisons a mean-based baseline and then hides every real problem after it.
Also does weekday-aware baselines (social data is violently weekly) and a
CUSUM changepoint pass for slow drifts that never trip a spike threshold.

    python3 tools/anomaly.py --csv daily.csv --date date --value views
    python3 tools/anomaly.py --csv daily.csv --date date --value views --seasonal weekly
    python3 tools/anomaly.py --csv daily.csv --date date --value er --window 14 --z 2.5

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import csvio  # noqa: E402

DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%b %d, %Y")


class AnomalyError(ValueError):
    pass


def parse_date(s):
    s = str(s).strip()
    for f in DATE_FORMATS:
        try:
            return datetime.strptime(s[:len(f) + 6], f)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        raise AnomalyError(f"cannot parse date {s!r}")


def num(v, field):
    s = str(v).strip().replace(",", "").replace("%", "").replace("$", "")
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        raise AnomalyError(f"{field}: {v!r} is not a number")


def mad(xs):
    """Median absolute deviation, scaled to be comparable to a stdev."""
    if not xs:
        return 0.0
    m = statistics.median(xs)
    return 1.4826 * statistics.median([abs(x - m) for x in xs])


def theil_sen(xs, ys, max_pairs=1200):
    """Robust slope: the median of all pairwise slopes.

    A least-squares fit would be dragged around by the single viral day this
    whole tool exists to find, so the baseline has to be as robust as the test.
    Pairs are strided (not sampled) past max_pairs so the result stays
    deterministic on long windows.
    """
    n = len(xs)
    if n < 2:
        return 0.0
    total = n * (n - 1) // 2
    stride = max(1, total // max_pairs)
    slopes, k = [], 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            if k % stride == 0:
                dx = xs[j] - xs[i]
                if dx:
                    slopes.append((ys[j] - ys[i]) / dx)
            k += 1
    return statistics.median(slopes) if slopes else 0.0


def _fit(hist, seasonal):
    """Fit level+trend (+weekday offsets) on a window. Returns (predict, resid)."""
    xs = list(range(len(hist)))
    ys = [v for _, v in hist]
    slope = theil_sen(xs, ys)
    intercept = statistics.median([y - slope * x for x, y in zip(xs, ys)])

    offsets = {}
    if seasonal == "weekly" and len(hist) >= 14:
        buckets = {}
        for x, (d, y) in zip(xs, hist):
            buckets.setdefault(d.weekday(), []).append(y - (intercept + slope * x))
        for wd, vals in buckets.items():
            # Two observations is not a weekly pattern, it is a coincidence.
            if len(vals) >= 3:
                offsets[wd] = statistics.median(vals)

    def predict(x, weekday):
        return intercept + slope * x + offsets.get(weekday, 0.0)

    resid = [y - predict(x, d.weekday()) for x, (d, y) in zip(xs, hist)]
    return predict, resid


def detect(points, window, zthresh, seasonal=None):
    """points = [(datetime, float)] sorted. Returns per-point diagnostics.

    The baseline is a trailing *local trend* fit, not a rolling median. On a
    growing account a median baseline sits permanently below the data and
    reports the growth itself as a run of spikes — the most common way this
    kind of tool gets ignored. Fitting slope first means a flag means "this
    broke from its own trajectory", which is the only useful definition.
    """
    out = []
    for i, (d, v) in enumerate(points):
        hist = points[max(0, i - window):i]
        if len(hist) < max(6, window // 3):
            out.append({"date": d.date().isoformat(), "value": v, "z": None,
                        "baseline": None, "spread": None, "flag": None})
            continue

        predict, resid = _fit(hist, seasonal)
        expected = predict(len(hist), d.weekday())
        spread = mad(resid)

        if not spread:
            # Perfectly flat history: any change at all is the signal. Cap the
            # score rather than emit inf, which breaks JSON and every downstream
            # comparison.
            z = 0.0 if v == expected else (8.0 if v > expected else -8.0)
        else:
            z = (v - expected) / spread

        flag = "spike" if z >= zthresh else ("drop" if z <= -zthresh else None)
        out.append({"date": d.date().isoformat(), "value": v, "z": round(z, 3),
                    "baseline": round(expected, 4), "spread": round(spread, 4),
                    "flag": flag})
    return out


def cusum(diag, k=0.5, h=5.0, gap=3):
    """Sustained level shifts, run on the *residuals* from the trend baseline.

    Running CUSUM on raw values is the classic mistake: on any trending series
    it fires on every point and tells you nothing. Consecutive fires are
    collapsed into one episode, because "the level dropped for nine days" is
    one event to investigate, not nine.
    """
    scored = [r for r in diag if r["z"] is not None]
    if len(scored) < 8:
        return []
    hi = lo = 0.0
    raw = []
    for idx, r in enumerate(scored):
        s = max(-10.0, min(10.0, r["z"]))
        hi = max(0.0, hi + s - k)
        lo = min(0.0, lo + s + k)
        if hi > h:
            raw.append((idx, r["date"], "up", hi))
            hi = lo = 0.0
        elif lo < -h:
            raw.append((idx, r["date"], "down", lo))
            hi = lo = 0.0

    episodes = []
    for idx, date_, direction, stat in raw:
        if (episodes and episodes[-1]["direction"] == direction
                and idx - episodes[-1]["_idx"] <= gap):
            ep = episodes[-1]
            ep["_idx"] = idx
            ep["until"] = date_
            ep["points"] += 1
            if abs(stat) > abs(ep["stat"]):
                ep["stat"] = round(stat, 2)
        else:
            episodes.append({"_idx": idx, "date": date_, "until": date_,
                             "direction": direction, "stat": round(stat, 2),
                             "points": 1})
    for ep in episodes:
        ep.pop("_idx", None)
    return episodes


def main(argv=None):
    p = argparse.ArgumentParser(prog="anomaly", description=__doc__.split("\n")[0])
    p.add_argument("--csv", required=True)
    p.add_argument("--date", required=True)
    p.add_argument("--value", required=True)
    p.add_argument("--window", type=int, default=28, help="baseline lookback")
    p.add_argument("--z", type=float, default=3.0, help="robust z threshold")
    p.add_argument("--seasonal", choices=["none", "weekly"], default="none")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    try:
        rows = csvio.read_rows(a.csv)
        csvio.require(rows, a.date, a.value, origin=a.csv)
        if a.window < 4:
            raise AnomalyError("--window must be at least 4")

        pts = []
        for r in rows:
            v = num(r[a.value], a.value)
            if v is None:
                continue
            pts.append((parse_date(r[a.date]), v))
        pts.sort(key=lambda t: t[0])
        if len(pts) < 6:
            raise AnomalyError(
                f"only {len(pts)} usable rows; anomaly detection needs at least 6")

        res = detect(pts, a.window, a.z,
                     None if a.seasonal == "none" else a.seasonal)
        shifts = cusum(res)
        flagged = [r for r in res if r["flag"]]

        if a.json:
            print(json.dumps({"points": res, "anomalies": flagged,
                              "changepoints": shifts}, indent=2))
            return 0

        print(f"{len(pts)} points  {pts[0][0].date()} → {pts[-1][0].date()}  "
              f"window={a.window} z={a.z} seasonal={a.seasonal}")
        if not flagged:
            print("\nno point-anomalies at this threshold.")
        else:
            print(f"\n{len(flagged)} anomal{'y' if len(flagged)==1 else 'ies'}:")
            print(f"{'date':<13}{'value':>14}{'baseline':>14}{'z':>8}  what")
            print("-" * 60)
            for r in flagged:
                print(f"{r['date']:<13}{r['value']:>14,.2f}{r['baseline']:>14,.2f}"
                      f"{r['z']:>8.2f}  {r['flag']}")
        if shifts:
            print(f"\n{len(shifts)} sustained level shift(s) — these matter more than "
                  f"spikes, and no daily-spike alert would have caught them:")
            for s in shifts:
                span = ("" if s["until"] == s["date"]
                        else f" → {s['until']} ({s['points']} pts)")
                print(f"  {s['date']}{span}  {s['direction']}  (cusum {s['stat']})")
        if not flagged and not shifts:
            print("\nThe series is boring. That is a finding: if you expected a "
                  "change here, the change did not happen.")
        return 0
    except (AnomalyError, csvio.CsvError, OSError) as e:
        print(f"anomaly: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
