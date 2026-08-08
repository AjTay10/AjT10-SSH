#!/usr/bin/env python3
"""make_fixtures — synthetic platform exports, in each platform's native format.

Deliberately not tidy. Each file carries the column vocabulary, date format, and
encoding that platform actually exports, because the point of the demo is that
the pipeline reconciles them — a clean uniform fixture would prove nothing.

    YouTube    utf-8 with BOM, watch time in HOURS, "Video publish time"
    TikTok     utf-8, US date format, video views and no impressions column
    Instagram  cp1252 (a spreadsheet round-trip), reach AND impressions

One story is embedded so the tools have something real to find:

    - YouTube impressions collapse on BREAK_DATE and never recover
    - engagement rate holds flat across that boundary  -> distribution, not content
    - TikTok keeps growing through it                  -> not a global event

Seeded, so the committed report and a fresh run agree. Stdlib only.

    python3 demo/make_fixtures.py --out demo/exports
"""

from __future__ import annotations

import argparse
import csv
import datetime
import os
import random
import sys

SEED = 20260808
START = datetime.date(2026, 3, 1)
DAYS = 90
BREAK_DATE = datetime.date(2026, 5, 12)

TITLES = [
    "The 3-second rule nobody follows",
    "Why your retention dies at 0:28",
    "I posted daily for 90 days",
    "Thumbnail teardown: 12 channels",
    "Stop making these edits",
    "The format that actually compounds",
]


def youtube(path, rng):
    """utf-8-sig: YouTube Studio exports carry a BOM. Watch time is in hours."""
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["Video publish time", "Video title", "Views", "Impressions",
                    "Impressions click-through rate (%)", "Likes",
                    "Comments added", "Shares", "Watch time (hours)",
                    "Subscribers gained"])
        for i in range(DAYS):
            d = START + datetime.timedelta(days=i)
            if i % 3:                                   # publishes every 3rd day
                continue
            base = 240_000 if d < BREAK_DATE else 96_000
            imp = int(base * rng.uniform(0.82, 1.18))
            ctr = rng.uniform(4.2, 6.4)
            views = int(imp * ctr / 100)
            er = rng.uniform(0.055, 0.075)              # unchanged by the break
            # Indexed, not rng.choice: uniform() is arithmetic on random() and
            # is stable across interpreter versions, while the selection helpers
            # are an implementation detail. CI diffs this output across 3.9 and
            # 3.12, so anything version-sensitive would read as a stale report.
            title = TITLES[(i // 3) % len(TITLES)]
            w.writerow([d.isoformat(), title, views, imp,
                        round(ctr, 2), int(views * er * 0.82),
                        int(views * er * 0.09), int(views * er * 0.09),
                        round(views * 3.1 / 3600, 1),
                        int(views * rng.uniform(0.004, 0.011))])


def tiktok(path, rng):
    """utf-8, US date format, and no impressions column — TikTok has no such metric."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Date", "Caption", "Video views", "Likes", "Comments",
                    "Shares", "Saves", "New followers"])
        for i in range(DAYS):
            d = START + datetime.timedelta(days=i)
            if i % 2:
                continue
            vv = int(rng.uniform(28_000, 190_000) * (1 + i * 0.011))
            w.writerow([d.strftime("%m/%d/%Y"), f"clip {i//2:02d}", vv,
                        int(vv * rng.uniform(0.06, 0.11)), int(vv * 0.004),
                        int(vv * rng.uniform(0.008, 0.02)),
                        int(vv * rng.uniform(0.01, 0.03)),
                        int(vv * rng.uniform(0.002, 0.006))])


def instagram(path, rng):
    """cp1252 with accented captions — what a spreadsheet round-trip produces."""
    rows = [["Post date", "Caption", "Reach", "Impressions", "Likes",
             "Comments", "Shares", "Saves", "Follows"]]
    for i in range(DAYS):
        d = START + datetime.timedelta(days=i)
        if i % 2:
            continue
        reach = int(rng.uniform(14_000, 46_000))
        rows.append([d.isoformat(), f"café series — part {i//2}", reach,
                     int(reach * rng.uniform(1.15, 1.4)),
                     int(reach * rng.uniform(0.03, 0.06)), int(reach * 0.002),
                     int(reach * rng.uniform(0.004, 0.012)),
                     int(reach * rng.uniform(0.008, 0.02)),
                     int(reach * rng.uniform(0.001, 0.004))])
    with open(path, "w", newline="", encoding="cp1252") as fh:
        csv.writer(fh).writerows(rows)


def main(argv=None):
    p = argparse.ArgumentParser(prog="make_fixtures",
                                description=__doc__.split("\n")[0])
    p.add_argument("--out", default="demo/exports")
    a = p.parse_args(argv)

    os.makedirs(a.out, exist_ok=True)
    # One generator, drawn in a fixed order, so the whole set is reproducible.
    rng = random.Random(SEED)
    for name, fn in (("youtube_studio_export.csv", youtube),
                     ("tiktok_export.csv", tiktok),
                     ("instagram_export.csv", instagram)):
        path = os.path.join(a.out, name)
        fn(path, rng)
        print(f"{path}  ({os.path.getsize(path):,} bytes)")
    print(f"\nseed={SEED}  window={START} +{DAYS}d  break={BREAK_DATE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
