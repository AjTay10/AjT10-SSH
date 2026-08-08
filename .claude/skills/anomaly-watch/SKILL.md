---
name: anomaly-watch
description: Detect real breaks in a time series — spikes, drops, and slow sustained shifts — using tools/anomaly.py with a trend-aware robust baseline. Use when the user asks why a metric changed, whether a drop is real, what happened on a date, when reach or traffic suddenly fell, or wants monitoring and alerting on a number. Also use before attributing any change to a cause.
---

# Anomaly watch

The question is almost never "did the number move" — numbers always move.
It is "did the number move more than it normally does, given its own trend
and its own weekly rhythm."

Backed by `tools/anomaly.py`.

## Run it

```bash
python3 tools/anomaly.py --csv daily.csv --date date --value views
python3 tools/anomaly.py --csv daily.csv --date date --value views --seasonal weekly
python3 tools/anomaly.py --csv d.csv --date date --value er --window 14 --z 2.5
python3 tools/anomaly.py --csv d.csv --date date --value views --json > a.json
```

Use `--seasonal weekly` for anything human-scheduled — social, traffic,
support tickets, sales. Weekday effects are large enough that without it,
every Saturday looks like an incident.

## Why the baseline is built the way it is

Three deliberate choices, each fixing a way this kind of tool usually fails:

**Median and MAD, not mean and standard deviation.** One viral day poisons a
mean-based baseline and inflates the variance so much that every subsequent
real problem hides inside the widened band. The robust version ignores the
outlier instead of absorbing it.

**A trailing local trend fit, not a rolling average.** A growing account
sits permanently above a lagging flat baseline, so a naive detector reports
the growth itself as a continuous run of spikes and gets muted within a week.
`anomaly.py` fits slope (Theil–Sen, itself robust) before scoring, so a flag
means "this broke from its own trajectory".

**Additive weekday offsets learned from the same window**, requiring at least
three observations of a weekday before believing in it. Two Tuesdays is a
coincidence, not a pattern.

## Read the two outputs differently

**Point anomalies** — a single day far from expectation. Usually a spike
(one post landed, a link was shared somewhere big) or an outage.

**Changepoints (CUSUM)** — a *sustained* shift in level, reported as an
episode with a start, an end, and a duration. These are the important ones
and the ones nobody notices: a 20% reach decline that starts on a Tuesday and
never recovers never trips a spike threshold, and shows up three months later
as "growth stalled". CUSUM runs on residuals from the trend fit, so it fires
only when the level departs from what the recent past predicted.

If you only look at one section of the output, look at the changepoints.

## Tuning

| Symptom | Change |
|---|---|
| Too many flags | raise `--z` to 4; add `--seasonal weekly`; widen `--window` |
| Missing obvious breaks | lower `--z` to 2.5; shorten `--window` to react faster |
| Everything flags near the start | expected — the first `window/3` points have no baseline and are scored `None` |
| Flags every weekend | you forgot `--seasonal weekly` |

Default `--z 3.0` is deliberately conservative. An alert that fires weekly
gets muted, and a muted alert has negative value: it costs attention and
provides a false sense of coverage.

## After a flag: attribute carefully

A detected break is a question, not an answer. Work through the causes in
this order, because the boring ones are far more common than the interesting
ones:

1. **Instrumentation.** Did tracking break, a tag get removed, a rename
   happen, an export change format? This is the single most common cause of a
   dramatic metric drop and it is checked last by almost everyone.
2. **Composition.** Did the mix change? Traffic shifting between platforms or
   devices moves a blended rate with no underlying behavior change at all.
3. **Calendar.** Holiday, seasonality the weekly model does not capture,
   a competitor's launch, a news event.
4. **Platform.** Algorithm change, policy enforcement, a shadow-limit. Check
   whether the break is confined to one platform — if reach fell everywhere at
   once, it is not the algorithm.
5. **Your own change.** What shipped that day? Correlating a break to a deploy
   or a content change is the *last* hypothesis, not the first, because it is
   the one you are motivated to find.

Then check the negative control: did a metric that *should not* have been
affected also move? If it did, the cause is upstream of both.

## For social data specifically

- Compare posts at **equal age**, never at a calendar cutoff. A post published
  yesterday has not finished accruing. Pinterest accrues for months.
- A reach drop with flat engagement rate means distribution changed. A reach
  drop *with* an ER drop usually means the content changed. Those lead to
  completely different investigations.
- Cumulative counters (Telegram channel views, some subscriber exports) must
  be differenced before this tool sees them, or every day is a "spike".

## Related

- `social-analytics` — normalizing exports before running this
- `metrics-lab` — for trend and cohort questions rather than break detection
- `stat-guard` — before claiming the change had a cause
