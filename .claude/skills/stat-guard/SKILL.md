---
name: stat-guard
description: Check whether a result is real before acting on it — significance testing, sample size, confidence intervals, Bayesian read, and the cost of peeking at a test early. Use when the user compares two variants, asks if a difference is significant or "real", plans an A/B test, reports a lift or a percentage improvement, or says one thing outperformed another. Also use to size a test before running it.
---

# Stat guard

Most reported wins are noise that got promoted. This skill exists to make
that expensive to do accidentally.

Backed by `tools/abtest.py` — stdlib only.

## Before the test: size it

```bash
python3 tools/abtest.py size --baseline 0.03 --lift 0.15 --daily 1200
```

Run this *first*, every time. The result is usually shocking, and that is the
point: detecting a 15% relative lift on a 3% baseline needs about 32,000 per
arm. At 1,200/day that is 54 days.

If the required runtime is longer than you will actually wait, the test is
already decided — you will stop it early and call the noise a result. Change
something before starting: accept a larger minimum detectable effect, test a
bigger swing rather than a button color, find a higher-traffic surface, or
accept that this decision will be made on judgment and say so out loud.

**Test big swings.** A test that can only detect a 15% lift is wasted on a
change that could at most produce 2%.

## After the test: two readings, deliberately

```bash
python3 tools/abtest.py compare --a 120/4000 --b 151/4050   # frequentist
python3 tools/abtest.py bayes   --a 120/4000 --b 151/4050   # decision-oriented
```

Run both. They answer different questions and disagreement between them is
informative, not a problem:

- `compare` answers *"would this difference be surprising if the variants were
  identical?"* It reports the interval, and if that interval contains zero it
  refuses to call a winner.
- `bayes` answers *"what is the chance B is better, and what does it cost me
  if I ship B and I am wrong?"* That is the question a decision actually needs.

A very common and correct outcome: p = 0.07 (not significant) while
P(B > A) = 96% with an expected loss near zero. The frequentist test says
"you have not proven it"; the Bayesian read says "the downside of acting is
tiny". For a reversible change, ship. For an irreversible one, get more data.
The framework should follow the reversibility of the decision.

**Always read the interval, never the point estimate.** "+24% lift" with an
interval of [−2%, +52%] is not a 24% lift, and planning around 24% is how the
next quarter's forecast breaks. Plan around the low end.

## The peeking problem

```bash
python3 tools/abtest.py peek --checks 14
```

Checking a test daily for two weeks and stopping the first time it goes green
turns a nominal 5% false-positive rate into roughly 12%. Every "we saw a
significant lift" from a test that was watched daily is suspect.

Fixes, in order of preference: fix the horizon before starting and do not look;
use a sequential test designed for continuous monitoring; or apply the
correction `peek` prints. Do not look daily and then apply no correction.

## Refuse these, out loud

- **Ratios of small numbers.** 3/10 vs 6/10 is "doubled" and is nothing.
  `compare` warns when any cell is under five outcomes.
- **The metric changed after the result.** If the pre-registered metric
  did not move and a different one did, that is a hypothesis for the next
  test, not a finding from this one.
- **Multiple comparisons.** Twenty metrics at p<0.05 yields one "winner" by
  construction. State how many were examined; correct or say you did not.
- **Segment mining.** "It worked for mobile users in Canada" found by slicing
  after the fact is noise with a demographic attached.
- **Novelty effects.** Any UI change tests well for a week because it is
  different. Look at the second and third week separately.
- **Survivorship in the denominator.** Measuring engagement rate only among
  people who engaged.
- **Simpson's paradox.** A variant can win in every segment and lose overall
  when traffic mix differs. If the segments and the total disagree, the total
  is usually the artifact — check the mix before believing either.

## Practical significance ≠ statistical significance

With enough traffic, everything is significant. Before running the test, write
down the effect size that would change your behavior. If a lift below that
threshold comes back significant, the correct action is still nothing.

## Reporting format

```
A  3.000%  120/4,000  [2.51%, 3.58%]
B  3.728%  151/4,050  [3.19%, 4.36%]
difference  +0.73pp  [−0.06, +1.52]   p = 0.070   P(B>A) = 96%
n was fixed at 4,000/arm in advance; the test was not monitored.
Decision: ship B — reversible, expected loss 0.006pp. Plan on +0.2pp, not +0.73.
```

Always state whether the sample size was pre-committed and whether the test
was monitored. Without those two lines, the p-value is not interpretable.

## Related

- `metrics-lab` — computing the rates being compared
- `base-rates` — the prior on how often tests in this class win at all
- `red-team` — for the non-statistical reasons a result might be wrong
