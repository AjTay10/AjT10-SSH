#!/usr/bin/env python3
"""sample — generate fixtures and a worked report, so the deliverable is real.

Run this once before the first client call. Seeing the output is the fastest
way to know what you are selling, and it doubles as an end-to-end check that
the toolchain works on this machine.

    python3 business/sample.py                 # writes business/sample/
    python3 business/sample.py --out /tmp/x

The generated business is synthetic and deliberately flawed: one dominant
sponsor, a power-law traffic distribution, output rising while yield falls,
and a genuine level shift in the trend. Every flaw is one a real listing
routinely carries.

Stdlib only.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SEED = 42

# Fixed date so a rerun produces a byte-identical report and the committed
# sample never drifts from the code that generates it.
REPORT_DATE = "8 August 2026"


def write(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    return path


def make_fixtures(outdir, rng):
    os.makedirs(outdir, exist_ok=True)

    # Pages: power-law traffic, older cohorts far more productive.
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

    # Revenue: one sponsor over half the total.
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
    ap = argparse.ArgumentParser(prog="sample",
                                 description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=os.path.join(HERE, "sample"))
    a = ap.parse_args(argv)

    rng = random.Random(SEED)
    pages, rev, traffic = make_fixtures(a.out, rng)
    report = os.path.join(a.out, "report.html")

    cmd = [sys.executable, os.path.join(HERE, "report_build.py"),
           "--client", "Coffee content site — listing #A-2291",
           "--prepared-for", "a prospective buyer",
           "--pages", pages, "--page-item", "url",
           "--page-value", "pageviews", "--page-date", "published",
           "--revenue", rev, "--rev-item", "source", "--rev-value", "amount",
           "--traffic", traffic, "--traffic-date", "month",
           "--traffic-value", "sessions",
           "--date", REPORT_DATE, "--out", report]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        print(p.stderr.strip() or "report_build failed", file=sys.stderr)
        return 2

    print(f"fixtures  {a.out}/")
    print(p.stdout.strip())
    print()
    print("Open the report and read the findings before your first client "
          "call. That page is the product.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
