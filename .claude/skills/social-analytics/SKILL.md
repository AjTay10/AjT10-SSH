---
name: social-analytics
description: Turn native platform analytics exports into one normalized dataset and a self-contained HTML dashboard, then read it honestly. Use when the user shares a YouTube, TikTok, Instagram, X, LinkedIn, or other platform export, asks what their numbers mean, wants a performance report or dashboard, asks which content worked, or wants to compare platforms. Also use before any strategy decision that claims to be data-driven.
---

# Social analytics

Every platform names the same number differently and counts it differently.
The work is to normalize honestly, then resist the comparisons the normalized
table invites you to make.

## Pipeline

```bash
# 1. See how a file's columns will map before trusting anything
python3 tools/social_ingest.py --inspect export.csv

# 2. Normalize one or many exports into one schema
python3 tools/social_ingest.py \
    --csv yt.csv --platform youtube \
    --csv tt.csv --platform tiktok \
    --csv ig.csv --platform instagram \
    --out norm.csv --summary

# 3. Dashboard — self-contained HTML, no network calls, publishable as an Artifact
python3 tools/dashboard.py --csv norm.csv --out dashboard.html --title "Q3"

# 4. Ask specific questions
python3 tools/anomaly.py --csv norm.csv --date date --value impressions --seasonal weekly
python3 tools/chartkit.py --type scatter --csv norm.csv --x video_views --y er_pct
python3 tools/social_ingest.py --list-platforms
```

`social_ingest` prints, to stderr, every column it dropped and a per-platform
caveat about what that platform's numbers actually mean. Read those lines —
they are the part that prevents the wrong conclusion.

## Unified schema

`date, platform, post_id, title, impressions, reach, engagements, likes,
comments, shares, saves, clicks, followers_delta, watch_time_sec,
video_views, er_pct`

Missing values stay **blank, never zero**. Blank means "this platform does not
report it"; zero means "reported as none". Collapsing the two drags every
average down and is the most common silent error in social reporting.

## The comparison you must not make

The normalized table makes it trivially easy to rank platforms by engagement
rate. Do not do it, and say why when someone asks:

- A TikTok view counts at 0 seconds; a YouTube view at ~30. Same word,
  different events.
- X impressions include scroll-past, so X's ER is structurally 5–10x lower
  than Instagram's. That is arithmetic, not quality.
- Reach is unique accounts; impressions are repeated. A rate mixing them is
  meaningless.
- Pinterest impressions accrue for months. Any calendar-window comparison
  favours older pins automatically.

**Compare within a platform over time. Compare across platforms only on
outcomes you actually own** — followers gained, clicks to your site, emails
captured. Those mean the same thing everywhere.

## Reading the dashboard

**Distribution beats averages.** Social performance is extremely
right-skewed: a handful of posts carry most of the reach. The mean is
dragged by outliers and describes no actual post. Look at the median, and
look at the shape.

**The bottom of the list teaches more than the top.** A viral post is mostly
luck and is not reproducible. A dead post usually has a specific, repeatable
cause — wrong hook, wrong time, wrong format, wrong audience. The dashboard
surfaces the lowest-ER post deliberately.

**Separate reach failure from resonance failure.** They need opposite fixes:

| Reach | ER | Diagnosis | Fix |
|---|---|---|---|
| low | high | Good content, no distribution | Hook, timing, categorization |
| high | low | Hook oversold it | Align the promise to the content |
| low | low | Wrong audience or wrong topic | Positioning, not tactics |
| high | high | It worked | Find the repeatable part |

**Watch capture, not reach.** Followers and owned contacts gained per post is
the number that compounds. Impressions are rented and reset to zero every day.

## Analysis order

1. **Reconcile.** Match one total against the platform's own dashboard before
   anything else. If they disagree, the export is windowed or filtered
   differently than you think and every downstream number is wrong. This
   single check catches more errors than the rest combined.
2. **Profile.** `--inspect`, then read the dropped-column warnings.
3. **Trend, per platform.** Is the direction real? Use `anomaly-watch` for
   breaks rather than eyeballing a line.
4. **Distribution.** Median and shape, not mean.
5. **Outliers, both ends.** What did the top 3 and bottom 3 have in common?
6. **Cross-platform, on owned outcomes only.**

## Sample size discipline

The base rate for a post materially outperforming an account's median is
roughly 1 in 20. Conclusions from fewer than 20 posts per format are noise
with a narrative attached.

Before saying "X works better than Y", run it:

```bash
python3 tools/abtest.py compare --a 4/50 --b 9/50
```

Most confident content conclusions do not survive that command. That is the
useful outcome, not a disappointing one — it prevents a quarter spent
optimizing a difference that was not there.

## Reporting

Lead with what changed and what to do. Never open with a wall of totals.

```
Reach fell 34% from 12 Mar and has not recovered. It is one platform, not all
three, and engagement rate is unchanged — so distribution changed, not the
content. Coincides with no content change on our side.
→ Next: check the platform's status/policy notes for that date; hold format
  constant for two more weeks before changing anything.
```

Flat ER with falling reach is a distribution story. Falling ER with flat reach
is a content story. Those lead to entirely different investigations, and
conflating them wastes the most time of any error in this domain.

## Related

- `data-clean` — before trusting any export
- `anomaly-watch` — detecting real breaks
- `stat-guard` — before claiming a difference is real
- `chart-forge` — custom charts beyond the dashboard
