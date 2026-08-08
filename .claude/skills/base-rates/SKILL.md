---
name: base-rates
description: Forecast using the outside view — find the reference class and its historical hit rate before reasoning about why this case is special. Use when the user asks "will this work", "how likely is", "how long will this take", "what should I expect", when estimating timelines or growth targets, or whenever a plan's projection sounds confident but has no comparison set. Also use to sanity-check any number presented as a forecast.
---

# Base rates

Almost every bad forecast is an inside-view forecast: reasoning from the
specifics of this case, which always feel more promising than average, while
ignoring how the reference class actually performs.

The fix is mechanical. Find the class, get its rate, then adjust — a little.

## Procedure

**1. Define the reference class before looking at this case.** Write it down
first, or you will gerrymander it to fit the answer you want.

Good classes are narrow enough to be relevant and wide enough to have data:
- Not "startups" → "seed-stage B2B SaaS reaching $1M ARR within 3 years"
- Not "YouTube channels" → "channels posting weekly in a saturated niche,
  first 12 months, from a standing start"
- Not "software projects" → "migrations touching auth, by a team that has
  not done one before"

**2. Get the rate.** In order of preference: the user's own historical data
(best — it already includes their execution quality), public data, published
studies, then honest estimate with the uncertainty stated.

When you estimate, say so in those words. "Roughly 1 in 10, and that is my
estimate, not a measurement" is useful. A fabricated-precise "11.3%" is not.

**3. Anchor on the base rate, then adjust.** Start at the class rate. Move it
only for factors with *demonstrated* predictive power, and move it less than
feels right. Typical honest adjustment is a factor of 2, not 20.

Legitimate adjusters: prior success by this exact team at this exact thing; a
structural advantage competitors cannot copy; a distribution channel already
owned. Illegitimate: enthusiasm, effort, "we care more", a better idea, and
the observation that the plan is well thought out — everyone's plan is.

**4. Report a range, not a point.** With the class, the rate, the adjustment,
and the reasoning visible.

## Reference points worth remembering

Use as rough anchors; verify against current data when the decision is large.

| Class | Approximate base rate |
|---|---|
| Social post materially outperforming an account's median | ~1 in 20 |
| New content channel reaching a self-sustaining audience in 12 mo | low single-digit % |
| A/B test on a mature funnel producing a real >5% lift | ~1 in 5 to 1 in 10 |
| Software project delivered on original estimate | ~1 in 3, and the miss skews long |
| Feature shipped that moves the metric it was justified by | ~1 in 3 |
| Ad creative beating the current control | ~1 in 10 |
| Viral outcome from a plan whose plan was "go viral" | rounds to zero |

The last row matters most: virality is a distribution outcome, never a
strategy input. Any plan whose success requires it has no base rate to stand on.

## Timelines specifically

Take the team's estimate and apply the reference class multiplier, which is
almost never 1.0. For work the team has not done before, 2–3x is standard and
not pessimistic. Then note that the *variance* is worse than the mean — the
question "what is the p90 completion date" is usually more decision-relevant
than the p50, and nobody asks it.

## Output

```
Reference class:  weekly-posting channels, saturated niche, first 12 months
Base rate:        ~4% reach 10k subs (public creator survey data, n≈2k)
Adjusters:        +  owns an existing email list of 8k (real distribution)
                  −  no prior video experience (execution risk)
Adjusted:         ~8–12%
Implication:      Plan for the 90% case. What is the outcome if this lands
                  at 2k subs? If that outcome is "wasted year", change the
                  plan now, not in month nine.
```

Always end on the implication for the 90% case. A forecast that does not
change a decision was entertainment.

## Related

- `pre-mortem` — turn the 90% case into tripwires and kill criteria
- `stat-guard` — when the base rate comes from a sample and needs an interval
