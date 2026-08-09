#!/usr/bin/env python3
"""parity_expected — freeze what the Python tools compute, for the JS port to match.

studio/engine.js is a second implementation of statistics that already exist in
tools/. Two implementations drift, and the drift is silent: the browser tool
would quietly report different numbers than the CLI on the same file, and the
first person to notice would be a client.

This writes the Python answers to parity_expected.json; studio/parity.mjs runs
engine.js under node against the same fixtures and compares. Either they agree
or CI fails.

    python3 studio/parity_expected.py

Fixtures come from studio/fixtures.py, which is seeded — so this whole chain is
reproducible.
"""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import anomaly          # noqa: E402
import concentration    # noqa: E402
import csvio            # noqa: E402

FIXTURES = os.path.join(HERE, "fixtures")


def load_items(path, item_col, value_col, date_col=None):
    rows = csvio.read_rows(path, quiet=True)
    items, dated = [], []
    for r in rows:
        v = concentration.num(r[value_col], value_col)
        if v is None or v <= 0:
            continue
        name = str(r[item_col]).strip() or "(unnamed)"
        items.append((name, v))
        if date_col:
            d = concentration.parse_date(r[date_col], date_col)
            if d:
                dated.append((name, v, d))
    return items, dated


def main():
    if not os.path.isdir(FIXTURES):
        print("studio/parity_expected: fixtures missing — run "
              "python3 studio/fixtures.py first", file=sys.stderr)
        return 2

    out = {}

    # --- concentration + vintages on the page fixture --------------------
    items, dated = load_items(os.path.join(FIXTURES, "pages.csv"),
                              "url", "pageviews", "published")
    res = concentration.analyze(items, top_n=10)
    vints = concentration.vintages(dated, "year")
    repl = concentration.replacement(vints)

    out["pages"] = {
        "items": res["items"],
        "total": res["total"],
        "hhi": res["hhi"],
        "hhi_normalized": res["hhi_normalized"],
        "effective_n": res["effective_n"],
        "effective_pct": res["effective_pct"],
        "top1_x_even_share": res["top1_x_even_share"],
        "gini": res["gini"],
        "band": res["band"],
        "shares": res["shares"],
        "fragility": {k: v["pct_lost"] for k, v in res["fragility"].items()},
        "top_names": [t["name"] for t in res["top"]],
        "top_values": [t["value"] for t in res["top"]],
    }
    out["vintages"] = vints
    out["replacement"] = repl

    # --- concentration on revenue ----------------------------------------
    ritems, _ = load_items(os.path.join(FIXTURES, "revenue.csv"), "source", "amount")
    rres = concentration.analyze(ritems, top_n=10)
    out["revenue"] = {
        "items": rres["items"], "total": rres["total"], "gini": rres["gini"],
        "effective_n": rres["effective_n"], "shares": rres["shares"],
        "top_names": [t["name"] for t in rres["top"]],
    }

    # --- trend detection --------------------------------------------------
    rows = csvio.read_rows(os.path.join(FIXTURES, "traffic.csv"), quiet=True)
    pts = []
    for r in rows:
        v = anomaly.num(r["sessions"], "sessions")
        if v is not None:
            pts.append((anomaly.parse_date(r["month"]), v))
    pts.sort(key=lambda p: p[0])
    diag = anomaly.detect(pts, 12, 3.0, None)
    out["trend"] = {
        "points": [{"date": d["date"], "z": d["z"], "baseline": d["baseline"],
                    "flag": d["flag"]} for d in diag],
        "changepoints": anomaly.cusum(diag),
    }

    # --- primitives, on values chosen to catch off-by-one and tie handling -
    out["primitives"] = {
        "median_even": __import__("statistics").median([1, 2, 3, 4]),
        "median_odd": __import__("statistics").median([5, 1, 3]),
        "mad_flat": anomaly.mad([7, 7, 7, 7]),
        "mad_mixed": anomaly.mad([1, 2, 3, 4, 100]),
        "gini_equal": concentration.gini([10, 10, 10, 10]),
        "gini_extreme": concentration.gini([100, 1, 1, 1]),
        "hhi_equal": concentration.hhi([10, 10, 10, 10]),
        "theil_sen_clean": anomaly.theil_sen(list(range(20)),
                                             [2 * x + 1 for x in range(20)]),
        "theil_sen_outlier": anomaly.theil_sen(
            list(range(20)),
            [10000 if x == 10 else 2 * x + 1 for x in range(20)]),
    }

    path = os.path.join(HERE, "parity_expected.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, sort_keys=True, default=float)
        fh.write("\n")
    print(f"{path}  ({os.path.getsize(path):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
