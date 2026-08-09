#!/usr/bin/env python3
"""fixtures — deterministic sample CSVs for the studio test harness.

The parity check, the browser test, and anyone wanting to try the tool all need
the same input. Generating it here keeps studio/ self-contained rather than
reaching into a sibling directory for data.

    python3 studio/fixtures.py              # writes studio/fixtures/

Three files, each in a shape a real export actually arrives in, and each
deliberately flawed so the analysis has something true to find:

    pages.csv     power-law traffic; older cohorts far more productive
    revenue.csv   one source over half the total
    traffic.csv   a genuine sustained level shift 25 months in

Seeded, and it avoids random.choice — whose selection strategy is an
implementation detail — so the same numbers come out on every Python version
CI runs. parity_expected.json is derived from these, so drift here would
surface as a false parity failure.

Stdlib only.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 42


def write(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    return path


def build(outdir, rng):
    os.makedirs(outdir, exist_ok=True)

    # Pages: power-law traffic, older cohorts far more productive per item.
    pages = []
    era = {2021: 7.0, 2022: 5.5, 2023: 2.8, 2024: 1.3, 2025: 1.0}
    kinds = ["guide", "review", "best", "how-to"]
    for i in range(340):
        yr = rng.choices([2021, 2022, 2023, 2024, 2025],
                         [0.14, 0.16, 0.20, 0.22, 0.28])[0]
        v = int(rng.paretovariate(1.35) * 260 * era[yr])
        pages.append([f"/{kinds[i % 4]}-{i:03d}", v,
                      f"{yr}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"])
    pages.append(["/best-espresso-machines-2022", 210000, "2022-04-11"])
    p_pages = write(os.path.join(outdir, "pages.csv"),
                    ["url", "pageviews", "published"], pages)

    # Revenue: one source over half the total.
    p_rev = write(os.path.join(outdir, "revenue.csv"), ["source", "amount"], [
        ["Sponsor: BrewCo", 9800],
        ["Amazon Associates", 4120],
        ["Mediavine display", 2310],
        ["Sponsor: GrindTech", 980],
        ["Newsletter sponsorship", 640],
        ["Affiliate: KitchenPro", 420],
        ["Digital product", 260],
    ])

    # Monthly sessions with a genuine level shift 25 months in.
    traffic, d = [], datetime.date(2023, 1, 1)
    for i in range(34):
        base = 42000 + i * 900
        if i >= 25:
            base = int(base * 0.52)
        traffic.append([d.isoformat(), base + rng.randint(-2600, 2600)])
        d = (d.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
    p_traffic = write(os.path.join(outdir, "traffic.csv"),
                      ["month", "sessions"], traffic)

    return p_pages, p_rev, p_traffic


def main(argv=None):
    ap = argparse.ArgumentParser(prog="fixtures",
                                 description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=os.path.join(HERE, "fixtures"))
    a = ap.parse_args(argv)
    for path in build(a.out, random.Random(SEED)):
        print(f"{path}  ({os.path.getsize(path):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
