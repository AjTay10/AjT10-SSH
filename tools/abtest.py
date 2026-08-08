#!/usr/bin/env python3
"""abtest — significance, sample size, and a Bayesian read on A/B results.

Built to argue *against* calling a winner too early. Every command reports the
interval, not just the point estimate, and refuses to print a verdict when the
data cannot support one.

    python3 tools/abtest.py compare --a 120/4000 --b 151/4050
    python3 tools/abtest.py size --baseline 0.03 --lift 0.15
    python3 tools/abtest.py bayes --a 120/4000 --b 151/4050
    python3 tools/abtest.py peek --days 14 --checks 14

Stdlib only. Normal approximation for the frequentist path; a Beta-Binomial
grid for the Bayesian path (exact enough at any realistic n, no scipy).
"""

from __future__ import annotations

import argparse
import json
import math
import sys

Z = {0.80: 1.2816, 0.85: 1.4395, 0.90: 1.6449, 0.95: 1.9600, 0.99: 2.5758}


class ABError(ValueError):
    pass


def parse_arm(s, name):
    """'120/4000' or '120,4000' -> (conversions, trials)."""
    txt = str(s).replace(",", "/").strip()
    if "/" not in txt:
        raise ABError(f"--{name} must look like conversions/trials, got {s!r}")
    a, b = txt.split("/", 1)
    try:
        c, n = float(a), float(b)
    except ValueError:
        raise ABError(f"--{name}: {s!r} is not two numbers")
    if n <= 0:
        raise ABError(f"--{name}: trials must be > 0")
    if c < 0:
        raise ABError(f"--{name}: conversions cannot be negative")
    if c > n:
        raise ABError(f"--{name}: {c:g} conversions out of {n:g} trials is impossible")
    return c, n


def norm_cdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def wilson(c, n, z=1.96):
    """Wilson score interval — behaves at small n where normal-approx does not."""
    if n == 0:
        return 0.0, 0.0
    p = c / n
    d = 1 + z * z / n
    center = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, center - half), min(1.0, center + half)


def cmd_compare(a):
    ca, na = parse_arm(a.a, "a")
    cb, nb = parse_arm(a.b, "b")
    pa, pb = ca / na, cb / nb
    pool = (ca + cb) / (na + nb)
    se = math.sqrt(pool * (1 - pool) * (1 / na + 1 / nb))
    if se == 0:
        raise ABError("both arms have identical, degenerate rates — nothing to test")
    z = (pb - pa) / se
    p_two = 2 * (1 - norm_cdf(abs(z)))
    zc = Z.get(a.confidence, 1.96)
    se_diff = math.sqrt(pa * (1 - pa) / na + pb * (1 - pb) / nb)
    diff = pb - pa
    lo, hi = diff - zc * se_diff, diff + zc * se_diff
    lift = (diff / pa * 100) if pa > 0 else None

    small = min(ca, cb, na - ca, nb - cb) < 5
    out = {
        "a": {"rate": pa, "n": na, "conv": ca, "ci95": wilson(ca, na)},
        "b": {"rate": pb, "n": nb, "conv": cb, "ci95": wilson(cb, nb)},
        "abs_diff": diff, "abs_diff_ci": [lo, hi],
        "rel_lift_pct": lift, "z": z, "p_value": p_two,
        "significant": p_two < (1 - a.confidence),
        "small_counts_warning": small,
    }
    if a.json:
        print(json.dumps(out, indent=2, default=float))
        return 0

    print(f"A  {pa*100:7.3f}%   {int(ca):>7,}/{int(na):<9,} "
          f"[{out['a']['ci95'][0]*100:.2f}%, {out['a']['ci95'][1]*100:.2f}%]")
    print(f"B  {pb*100:7.3f}%   {int(cb):>7,}/{int(nb):<9,} "
          f"[{out['b']['ci95'][0]*100:.2f}%, {out['b']['ci95'][1]*100:.2f}%]")
    print(f"\nabsolute difference  {diff*100:+.3f} pp  "
          f"[{lo*100:+.3f}, {hi*100:+.3f}] at {a.confidence:.0%}")
    if lift is not None:
        print(f"relative lift        {lift:+.1f}%")
    print(f"two-sided p          {p_two:.4f}   (z = {z:+.3f})")
    if lo <= 0 <= hi:
        print("\nverdict: NOT significant. The interval contains zero — B may be worse. "
              "Do not ship on this.")
    else:
        print(f"\nverdict: significant at {a.confidence:.0%}. "
              f"Plausible true effect runs {lo*100:+.2f} to {hi*100:+.2f} pp — "
              "plan around the low end, not the point estimate.")
    if small:
        print("caution: a cell has fewer than 5 outcomes. The normal approximation "
              "is shaky here; prefer the `bayes` subcommand.")
    return 0


def cmd_size(a):
    p = a.baseline
    if not 0 < p < 1:
        raise ABError("--baseline must be a rate strictly between 0 and 1")
    if a.lift <= 0:
        raise ABError("--lift must be > 0 (as a fraction, e.g. 0.15 for +15%)")
    p2 = p * (1 + a.lift)
    if p2 >= 1:
        raise ABError(f"a {a.lift:.0%} lift on {p:.1%} exceeds 100% — pick a smaller lift")
    za = Z.get(a.confidence, 1.96)
    zb = Z.get(a.power, 0.8416)
    pbar = (p + p2) / 2
    n = ((za * math.sqrt(2 * pbar * (1 - pbar)) +
          zb * math.sqrt(p * (1 - p) + p2 * (1 - p2))) ** 2) / ((p2 - p) ** 2)
    n = math.ceil(n)
    out = {"per_arm": n, "total": n * 2, "baseline": p, "target": p2,
           "mde_rel": a.lift, "confidence": a.confidence, "power": a.power}
    if a.daily:
        out["days_needed"] = math.ceil(n * 2 / a.daily)
    if a.json:
        print(json.dumps(out, indent=2))
        return 0
    print(f"baseline {p:.3%} -> target {p2:.3%}  (relative MDE {a.lift:+.0%})")
    print(f"required per arm   {n:,}")
    print(f"required total     {n*2:,}")
    if a.daily:
        print(f"at {a.daily:,.0f}/day        {out['days_needed']:,} days")
        if out["days_needed"] > 60:
            print("\nflag: over two months of runtime. Either accept a larger MDE, "
                  "find a higher-traffic surface, or pick a different bet. Tests "
                  "this long get contaminated by seasonality and shipping.")
    return 0


def _beta_grid(alpha, beta, steps=4000):
    """Unnormalized log-density on a grid; avoids overflow at large n."""
    xs = [(i + 0.5) / steps for i in range(steps)]
    logs = [(alpha - 1) * math.log(x) + (beta - 1) * math.log(1 - x) for x in xs]
    m = max(logs)
    ws = [math.exp(l - m) for l in logs]
    s = sum(ws)
    return xs, [w / s for w in ws]


def cmd_bayes(a):
    ca, na = parse_arm(a.a, "a")
    cb, nb = parse_arm(a.b, "b")
    steps = 2000
    xa, wa = _beta_grid(ca + 1, na - ca + 1, steps)
    xb, wb = _beta_grid(cb + 1, nb - cb + 1, steps)

    # Everything below is one linear sweep using prefix sums over A's grid, so
    # this stays O(steps) instead of the naive O(steps^2) double integral.
    prefA = [0.0] * (steps + 1)     # cumulative probability mass of A
    prefAx = [0.0] * (steps + 1)    # cumulative first moment of A
    for i in range(steps):
        prefA[i + 1] = prefA[i] + wa[i]
        prefAx[i + 1] = prefAx[i] + xa[i] * wa[i]
    totA, totAx = prefA[steps], prefAx[steps]

    meanA = sum(x * w for x, w in zip(xa, wa))
    meanB = sum(x * w for x, w in zip(xb, wb))

    p_b_better, e_loss_b, e_gain_b = 0.0, 0.0, 0.0
    for j in range(steps):
        p_b_better += wb[j] * prefA[j]          # mass of A strictly below b_j
        b = xb[j]
        mass_above = totA - prefA[j + 1]
        x_above = totAx - prefAx[j + 1]
        e_loss_b += wb[j] * (x_above - b * mass_above)   # A beats B by this much
        mass_below, x_below = prefA[j + 1], prefAx[j + 1]
        e_gain_b += wb[j] * (b * mass_below - x_below)

    def hdi(xs, ws, cred=0.95):
        cum, lo, hi = 0.0, xs[0], xs[-1]
        lo_set = False
        for x, w in zip(xs, ws):
            cum += w
            if not lo_set and cum >= (1 - cred) / 2:
                lo, lo_set = x, True
            if cum >= 1 - (1 - cred) / 2:
                hi = x
                break
        return lo, hi

    out = {
        "p_b_beats_a": p_b_better,
        "mean_a": meanA, "mean_b": meanB,
        "ci_a": hdi(xa, wa), "ci_b": hdi(xb, wb),
        "expected_loss_if_ship_b": e_loss_b,
        "expected_gain_if_ship_b": e_gain_b,
    }
    if a.json:
        print(json.dumps(out, indent=2))
        return 0
    print(f"A posterior mean {meanA*100:.3f}%  95% CrI "
          f"[{out['ci_a'][0]*100:.2f}%, {out['ci_a'][1]*100:.2f}%]")
    print(f"B posterior mean {meanB*100:.3f}%  95% CrI "
          f"[{out['ci_b'][0]*100:.2f}%, {out['ci_b'][1]*100:.2f}%]")
    print(f"\nP(B > A)                 {p_b_better*100:.1f}%")
    print(f"expected loss if B ships {e_loss_b*100:.4f} pp")
    print(f"expected gain if B ships {e_gain_b*100:.4f} pp")
    if p_b_better > 0.95 and e_loss_b < 0.0005:
        print("\nread: ship B. High probability of improvement and a small "
              "downside if you are wrong.")
    elif p_b_better < 0.05:
        print("\nread: A is better. Stop the test.")
    else:
        print("\nread: inconclusive. The honest move is more data or a bigger swing — "
              "not a rerun with a new metric.")
    return 0


def cmd_peek(a):
    """How much a fixed-horizon test inflates false positives when you peek."""
    if a.checks < 1:
        raise ABError("--checks must be >= 1")
    alpha = 1 - a.confidence
    # Independent-checks upper bound; correlated in practice, so this is a
    # ceiling. The Pocock-style approximation gives the realistic middle.
    naive = 1 - (1 - alpha) ** a.checks
    pocock = min(0.95, alpha * (1 + 0.55 * math.log(max(1, a.checks))))
    out = {"checks": a.checks, "nominal_alpha": alpha,
           "upper_bound_false_positive": naive,
           "realistic_false_positive": pocock,
           "corrected_alpha_for_each_look": alpha / a.checks}
    if a.json:
        print(json.dumps(out, indent=2))
        return 0
    print(f"looking {a.checks} times at a nominal {alpha:.0%} threshold:")
    print(f"  realistic false-positive rate  ~{pocock:.1%}")
    print(f"  absolute worst case            {naive:.1%}")
    print(f"  Bonferroni alpha per look      {alpha/a.checks:.4f}")
    print("\nfix: pick the horizon before you start, or use a sequential test. "
          "Peeking daily and stopping on the first green day is how teams ship "
          "noise and then blame the metric.")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="abtest", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("compare", help="frequentist two-proportion test")
    c.add_argument("--a", required=True, help="conversions/trials for control")
    c.add_argument("--b", required=True, help="conversions/trials for variant")
    c.add_argument("--confidence", type=float, default=0.95)
    c.add_argument("--json", action="store_true")
    c.set_defaults(fn=cmd_compare)

    s = sub.add_parser("size", help="required sample size")
    s.add_argument("--baseline", type=float, required=True, help="e.g. 0.03")
    s.add_argument("--lift", type=float, required=True, help="relative MDE, e.g. 0.15")
    s.add_argument("--confidence", type=float, default=0.95)
    s.add_argument("--power", type=float, default=0.80)
    s.add_argument("--daily", type=float, help="subjects available per day")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_size)

    b = sub.add_parser("bayes", help="posterior P(B>A) and expected loss")
    b.add_argument("--a", required=True)
    b.add_argument("--b", required=True)
    b.add_argument("--json", action="store_true")
    b.set_defaults(fn=cmd_bayes)

    k = sub.add_parser("peek", help="false-positive cost of repeated looks")
    k.add_argument("--checks", type=int, required=True)
    k.add_argument("--days", type=int, default=0)
    k.add_argument("--confidence", type=float, default=0.95)
    k.add_argument("--json", action="store_true")
    k.set_defaults(fn=cmd_peek)

    a = p.parse_args(argv)
    try:
        return a.fn(a)
    except (ABError, OSError) as e:
        print(f"abtest: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
