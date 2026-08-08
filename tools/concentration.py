#!/usr/bin/env python3
"""concentration — how fragile is this revenue, traffic, or audience?

Two questions a headline number never answers:

  1. CONCENTRATION — does the total rest on everything, or on three things?
     A site doing $10k/mo across 400 pages and one doing $10k/mo where a single
     page carries 60% are not the same asset, and only one of them survives a
     ranking change.

  2. DECAY — is the value being renewed or run down? If most of today's total
     comes from work published three years ago and nothing recent performs, the
     business is a melting asset with a growth chart on top of it.

    python3 tools/concentration.py --csv pages.csv --item url --value pageviews
    python3 tools/concentration.py --csv rev.csv --item sponsor --value amount
    python3 tools/concentration.py --csv posts.csv --item id --value views \\
        --date published --decay --period quarter
    python3 tools/concentration.py --csv p.csv --item id --value rev --json

Stdlib only. Reads only what you give it — no network, no scraping.

This computes descriptive statistics. It is not a valuation, an appraisal, or
investment advice, and it cannot tell you whether the underlying numbers are
truthful — only what they imply if they are.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import csvio  # noqa: E402

DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y", "%b %d, %Y",
                "%d %b %Y", "%Y-%m", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S")

# Banded on Gini, and neither of the obvious alternatives survived testing.
#
# Raw Herfindahl thresholds come from merger review, where they describe a
# market of a handful of firms. Its floor is 1/n, so across 400 pages a raw HHI
# of 0.08 sits 30x above the minimum and still reads "diversified" on that
# scale. Normalizing to (H - 1/n)/(1 - 1/n) fixes the floor but not the ceiling:
# reaching 1.0 requires a single item holding everything, so at large n any
# realistic power law still scores near zero.
#
# Gini is scale-invariant in n and is the standard measure for exactly this
# shape. HHI and its normalized form stay in --json for anyone who wants them;
# they are just not what the headline should be banded on.
GINI_BANDS = ((0.40, "evenly spread"), (0.60, "unequal"),
              (1.01, "steeply unequal — a power law"))


class ConcentrationError(ValueError):
    pass


def num(v, field):
    s = str(v).strip().replace(",", "").replace("$", "").replace("%", "")
    if s == "" or s.lower() in {"n/a", "na", "-", "--", "null", "none"}:
        return None                     # blank is "not reported", never zero
    mult = 1.0
    if s and s[-1] in "kKmMbB":
        mult = {"k": 1e3, "m": 1e6, "b": 1e9}[s[-1].lower()]
        s = s[:-1]
    try:
        return float(s) * mult
    except ValueError:
        raise ConcentrationError(f"{field}: {v!r} is not a number")


def parse_date(v, field):
    s = str(v).strip()
    if not s:
        return None
    for f in DATE_FORMATS:
        try:
            return datetime.strptime(s[:len(f) + 6], f).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        raise ConcentrationError(f"{field}: cannot parse date {v!r}")


# --------------------------------------------------------------------------
# statistics
# --------------------------------------------------------------------------

def hhi(values):
    """Herfindahl index on shares. 1/n (perfectly even) to 1.0 (one item)."""
    total = sum(values)
    if total <= 0:
        raise ConcentrationError("values sum to zero — nothing to concentrate")
    return sum((v / total) ** 2 for v in values)


def gini(values):
    """0 = every item identical, approaching 1 = one item holds everything."""
    xs = sorted(values)
    n = len(xs)
    total = sum(xs)
    if n == 0 or total <= 0:
        return 0.0
    if n == 1:
        return 0.0
    weighted = sum((i + 1) * x for i, x in enumerate(xs))
    return (2 * weighted) / (n * total) - (n + 1) / n


def top_share(sorted_desc, k, total):
    return sum(sorted_desc[:k]) / total if total else 0.0


def band(g):
    for edge, label in GINI_BANDS:
        if g < edge:
            return label
    return "steeply unequal — a power law"


def analyze(items, top_n=10):
    """items = [(name, value)] with value > 0. Returns the concentration read."""
    values = [v for _, v in items]
    total = sum(values)
    if total <= 0:
        raise ConcentrationError(
            "all values are zero or blank — check the --value column")

    ranked = sorted(items, key=lambda p: (-p[1], str(p[0])))
    desc = [v for _, v in ranked]
    n = len(desc)
    h = hhi(desc)

    # "Effective count": the number of equally-sized items that would produce
    # this much concentration. Far more legible than the index itself — "you
    # have 400 pages but effectively 13 of them" lands where 0.0755 does not.
    effective_n = 1.0 / h

    # Normalized: (H - 1/n) / (1 - 1/n). Zero when every item is identical, one
    # when a single item holds everything, and comparable across portfolios of
    # different sizes — which raw HHI is not.
    h_norm = (h - 1.0 / n) / (1.0 - 1.0 / n) if n > 1 else 1.0

    # How many times its fair share the largest item holds. This is the line
    # that communicates: "top page is 76x an even slice" needs no statistics
    # background to act on.
    even_share = 1.0 / n
    top1_multiple = (desc[0] / total) / even_share if total else 0.0

    out = {
        "items": n,
        "total": total,
        "hhi": h,
        "hhi_normalized": h_norm,
        "effective_n": effective_n,
        "effective_pct": effective_n / n,
        "top1_x_even_share": top1_multiple,
        "gini": gini(desc),
        "band": band(gini(desc)),
        "top": [{"name": str(name), "value": v, "share": v / total}
                for name, v in ranked[:top_n]],
        "shares": {},
        "fragility": {},
    }
    for k in (1, 3, 5, 10):
        if k <= n:
            out["shares"][f"top{k}"] = top_share(desc, k, total)
    if n >= 20:
        out["shares"]["top10pct"] = top_share(desc, max(1, n // 10), total)

    # Leave-one-out: the number a buyer actually needs. "Remove the single best
    # page and the asset loses X%" is the whole risk in one sentence.
    for k in (1, 3):
        if k < n:
            lost = sum(desc[:k]) / total
            out["fragility"][f"drop_top{k}"] = {
                "remaining": total - sum(desc[:k]),
                "pct_lost": lost * 100,
            }
    return out


def vintages(rows, period):
    """Group by publish period: how much of today's total each vintage carries."""
    buckets = defaultdict(lambda: {"n": 0, "total": 0.0, "values": []})
    for name, value, d in rows:
        key = bucket_key(d, period)
        b = buckets[key]
        b["n"] += 1
        b["total"] += value
        b["values"].append(value)

    grand = sum(b["total"] for b in buckets.values())
    out = []
    for key in sorted(buckets):
        b = buckets[key]
        vals = sorted(b["values"])
        out.append({
            "period": key,
            "items": b["n"],
            "total": b["total"],
            "share": b["total"] / grand if grand else 0.0,
            "median_per_item": vals[len(vals) // 2],
        })
    return out


def bucket_key(d: date, period: str) -> str:
    if period == "year":
        return f"{d.year:04d}"
    if period == "quarter":
        return f"{d.year:04d}-Q{(d.month - 1) // 3 + 1}"
    if period == "month":
        return f"{d.year:04d}-{d.month:02d}"
    raise ConcentrationError(f"unknown --period {period!r} (month|quarter|year)")


def replacement(vints):
    """Is new work performing like old work did?

    Compares median value per item in the newest quarter of vintages against
    the oldest quarter. Returns None when there are too few vintages for the
    comparison to mean anything.
    """
    if len(vints) < 4:
        return None
    k = max(1, len(vints) // 4)
    old = [v["median_per_item"] for v in vints[:k]]
    new = [v["median_per_item"] for v in vints[-k:]]
    old_med = sorted(old)[len(old) // 2]
    new_med = sorted(new)[len(new) // 2]
    if old_med <= 0:
        return None
    return {"old_median": old_med, "new_median": new_med,
            "ratio": new_med / old_med,
            "old_periods": [v["period"] for v in vints[:k]],
            "new_periods": [v["period"] for v in vints[-k:]]}


# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------

def fmt(v):
    a = abs(v)
    if a >= 1e9:
        return f"{v/1e9:,.2f}B"
    if a >= 1e6:
        return f"{v/1e6:,.2f}M"
    if a >= 1e3:
        return f"{v/1e3:,.1f}k"
    return f"{v:,.2f}".rstrip("0").rstrip(".") if a % 1 else f"{v:,.0f}"


def report(res, label, vints=None, repl=None, period="quarter"):
    print(f"{res['items']:,} {label} · total {fmt(res['total'])}")
    print()
    print(f"{'distribution':<26}{res['gini']:.3f} gini  ({res['band']})")
    print(f"{'effective count':<26}{res['effective_n']:.1f} of {res['items']:,} "
          f"({res['effective_pct']*100:.1f}%)")
    print(f"{'largest item':<26}{res['top1_x_even_share']:.0f}x an even share")
    print(f"{'herfindahl':<26}{res['hhi']:.4f} raw · "
          f"{res['hhi_normalized']:.3f} normalized")
    print()

    for k, v in res["shares"].items():
        pretty = k.replace("top10pct", "top 10%").replace("top", "top ")
        print(f"{pretty + ' share':<26}{v*100:>6.1f}%")

    print()
    print(f"{'rank':<6}{'share':>8}  {'value':>12}  item")
    print("-" * 64)
    for i, t in enumerate(res["top"], 1):
        name = t["name"][:34] + ("…" if len(t["name"]) > 34 else "")
        print(f"{i:<6}{t['share']*100:>7.1f}%  {fmt(t['value']):>12}  {name}")

    if res["fragility"]:
        print()
        for k, v in res["fragility"].items():
            n = k.replace("drop_top", "")
            print(f"remove the top {n:<3} → lose {v['pct_lost']:>5.1f}% "
                  f"({fmt(v['remaining'])} remains)")

    if vints:
        print()
        print(f"{'vintage':<12}{'items':>8}{'total':>14}{'share':>9}"
              f"{'median/item':>14}")
        print("-" * 57)
        for v in vints:
            print(f"{v['period']:<12}{v['items']:>8,}{fmt(v['total']):>14}"
                  f"{v['share']*100:>8.1f}%{fmt(v['median_per_item']):>14}")

        if repl:
            print()
            print(f"newest vintages ({', '.join(repl['new_periods'])}) median "
                  f"{fmt(repl['new_median'])} per item")
            print(f"oldest vintages ({', '.join(repl['old_periods'])}) median "
                  f"{fmt(repl['old_median'])} per item")
            print(f"replacement ratio          {repl['ratio']:.2f}x")
            print()
            print("  Read this carefully: older items have had longer to")
            print("  accumulate, so this ratio is biased IN FAVOUR of old work.")
            if repl["ratio"] >= 1.0:
                print("  New work still wins despite that handicap — that is a")
                print("  strong signal the asset is being renewed.")
            else:
                print("  New work loses, but the age handicap alone could explain")
                print("  it. This is suggestive, not conclusive: settle it with")
                print("  per-item performance at equal age, not cumulative totals.")

    # The verdict is deliberately about what to ask next, not a score.
    print()
    print("what this means")
    print("-" * 64)
    flags = []
    # Thresholds are scale-aware. A fixed "top1 > 25%" cutoff passes a 400-item
    # portfolio whose best item holds 20% — which is 80x an even slice and
    # plainly the dominant risk. Judge against the even share, not a constant.
    top1 = res["shares"].get("top1", 0)
    if top1 > 0.10 or res["top1_x_even_share"] >= 10:
        flags.append(f"One item is {top1*100:.0f}% of the total — "
                     f"{res['top1_x_even_share']:.0f}x an even share. Its loss "
                     f"is the dominant risk; establish how durable it is before "
                     f"anything else.")
    if res["effective_pct"] < 0.25 and res["items"] >= 10:
        flags.append(f"Effective count is {res['effective_n']:.1f} of "
                     f"{res['items']:,} ({res['effective_pct']*100:.0f}%). "
                     f"Despite the item count, this behaves like a handful.")
    if res["gini"] > 0.6 and res["items"] >= 10:
        flags.append(f"Gini {res['gini']:.2f}: the distribution is steeply "
                     f"unequal, so averages across these {label} describe no "
                     f"actual item and should not be used for projection.")
    if res["shares"].get("top10", 0) > 0.5 and res["items"] > 30:
        flags.append(f"The top 10 of {res['items']:,} carry "
                     f"{res['shares']['top10']*100:.0f}%. The long tail is "
                     f"decorative — buying it is buying the top 10.")
    if vints and vints[-1]["share"] < 0.05 and len(vints) >= 4:
        flags.append(f"The newest vintage contributes "
                     f"{vints[-1]['share']*100:.1f}% of the total. Recent work "
                     f"is not moving the number.")
    if repl and repl["ratio"] < 0.5:
        flags.append(f"New work is at {repl['ratio']:.2f}x the median of old "
                     f"work, before correcting for the age handicap.")
    if not flags:
        flags.append("No concentration flag at these thresholds. The total is "
                     "spread widely enough that no single loss dominates.")
    for f in flags:
        print(f"  · {f}")
    print()
    print("  Descriptive statistics only. This says nothing about whether the")
    print("  input numbers are truthful — verify those at the source.")


def main(argv=None):
    p = argparse.ArgumentParser(prog="concentration",
                                description=__doc__.split("\n")[0])
    p.add_argument("--csv", required=True)
    p.add_argument("--item", required=True, help="column naming each item")
    p.add_argument("--value", required=True, help="column holding the amount")
    p.add_argument("--date", help="publish date column (required for --decay)")
    p.add_argument("--decay", action="store_true",
                   help="add vintage analysis: is value being renewed?")
    p.add_argument("--period", default="quarter",
                   choices=["month", "quarter", "year"])
    p.add_argument("--top", type=int, default=10, help="rows to list")
    p.add_argument("--label", default="items", help="noun for the output")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    try:
        if a.decay and not a.date:
            raise ConcentrationError("--decay needs --date to group by vintage")
        if a.top < 1:
            raise ConcentrationError("--top must be at least 1")

        rows = csvio.read_rows(a.csv)
        cols = [a.item, a.value] + ([a.date] if a.date else [])
        csvio.require(rows, *cols, origin=a.csv)

        items, dated, skipped, negative = [], [], 0, 0
        for r in rows:
            v = num(r[a.value], a.value)
            if v is None:
                skipped += 1
                continue
            if v < 0:
                negative += 1
                continue
            if v == 0:
                continue                # reported as none: real, but no weight
            name = str(r[a.item]).strip() or "(unnamed)"
            items.append((name, v))
            if a.date:
                d = parse_date(r[a.date], a.date)
                if d:
                    dated.append((name, v, d))

        if not items:
            raise ConcentrationError(
                f"no usable rows: every {a.value!r} was blank, zero, or negative")
        if len(items) < 3:
            raise ConcentrationError(
                f"only {len(items)} item(s) with a positive value — "
                f"concentration is not a meaningful question below 3")

        res = analyze(items, a.top)
        vints = repl = None
        if a.decay:
            if len(dated) < 4:
                raise ConcentrationError(
                    f"only {len(dated)} row(s) carried a usable date; "
                    f"--decay needs at least 4")
            vints = vintages(dated, a.period)
            repl = replacement(vints)

        if a.json:
            print(json.dumps({"concentration": res, "vintages": vints,
                              "replacement": repl, "skipped_blank": skipped,
                              "skipped_negative": negative},
                             indent=2, default=float))
            return 0

        report(res, a.label, vints, repl, a.period)
        if skipped or negative:
            print()
            if skipped:
                print(f"note: {skipped} row(s) had a blank {a.value!r} and were "
                      f"excluded — blank is 'not reported', not zero.")
            if negative:
                print(f"note: {negative} row(s) were negative and were excluded. "
                      f"Net refunds against their line before running this.")
        return 0
    except (ConcentrationError, csvio.CsvError, OSError) as e:
        print(f"concentration: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
