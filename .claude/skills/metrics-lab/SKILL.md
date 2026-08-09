---
name: metrics-lab
description: Compute funnels, cohort retention, and growth decomposition from event or daily CSV data using tools/metrics.py. Use when the user asks about conversion rates, drop-off, where users are lost, retention, churn, cohorts, growth rate, or wants to know which step in a process is leaking. Also use to turn a raw events export into an honest picture of what is actually happening.
---

# Metrics lab

Three questions cover most of what anyone needs from behavioral data:
where do people leave, do they come back, and is this growing. Everything
else is usually a dashboard nobody reads.

Backed by `tools/metrics.py` — stdlib only, reads CSV, prints tables or JSON.

## Funnel — where do people leave?

```bash
python3 tools/metrics.py funnel --csv events.csv --user user_id --step step \
    --order impression,click,signup,purchase
```

Strict by default: to count at step N you must have appeared at every prior
step. Use `--loose` to count each step independently — and know that loose
mode routinely reports conversion above 100% between steps, because people
enter mid-funnel. If you see that, you wanted strict.

**Read the `% prev` column, not `% top`.** The percentage of the top is
dominated by the first step and hides everything after it. The step with the
worst `% prev` is the leak, and it is very often not the one anyone is
working on.

**Then ask whether the leak is a bug or a filter.** Not every drop-off is
loss. A pricing page that removes people who were never going to pay is doing
its job, and "fixing" it moves the drop-off one step later where it is more
expensive. Before optimizing a step, check whether the people lost there
convert *at all* downstream.

## Retention — do they come back?

```bash
python3 tools/metrics.py retention --csv events.csv --user user_id \
    --date date --period week --periods 8
```

Cohorts by first-seen period, retention measured per subsequent period.

**Read down the columns, not across the rows.** Across a row is one cohort
decaying, which always looks bad and tells you nothing. Down a column — P1
retention for each successive cohort — tells you whether the product is
getting better or worse over time, which is the actual question.

**The shape matters more than the level.** A curve that flattens has a
retained core, and the flat asymptote is the real business. A curve that
decays to zero has no core, and acquiring more users into it is pouring water
into a bucket with no bottom. Look at P3–P8 for the flattening; P1 tells you
almost nothing.

**Watch for a small final cohort.** The most recent cohort is always partial
and always looks worst. Ignore its later columns entirely; they are censored,
not bad.

## Growth — is this real?

```bash
python3 tools/metrics.py growth --csv daily.csv --date date --value followers
```

Reports absolute and percentage change, average per day, annualized rate,
best and worst single periods, and the recent-window average.

It explicitly flags the case where **net growth is positive but the recent
window is negative** — the most common way a growth report misleads. A chart
that goes up and to the right can be describing something that stopped
working six weeks ago.

Treat the annualized figure with suspicion on short windows. Annualizing 30
days of a launch spike produces a number that is arithmetically correct and
epistemically worthless.

## Cohort value

```bash
python3 tools/metrics.py cohort --csv users.csv --user id \
    --date signup_date --value revenue --period month
```

Per-cohort size and per-user value. Rising per-user value across cohorts means
targeting improved; falling means growth is being bought at declining quality —
which shows up here months before it shows up in the top-line number.

## Concentration — what does the total rest on?

A total tells you the size of something, never its fragility. Two accounts with
identical revenue are different assets if one earns it from four hundred
sources and the other from three.

```bash
python3 tools/concentration.py --csv pages.csv --item url --value pageviews
python3 tools/concentration.py --csv revenue.csv --item source --value amount
python3 tools/concentration.py --csv posts.csv --item id --value revenue \
    --date published --decay --period year
```

Read `effective count` first — "13.2 of 382" means that despite 382 items the
total behaves like thirteen. Then read `remove the top 1`, which states the
dominant risk in one line.

`--decay` adds vintage analysis. The signal worth looking for is **production
rising while yield falls**: more items published each period, less earned per
item. That is an asset working harder to stand still, and no total reveals it.

The replacement ratio is biased *in favour of older items*, because they have
had longer to accumulate. A ratio above 1.0 despite that handicap is strong;
below 1.0 is suggestive but not conclusive, and needs per-item performance at
equal age to settle. The tool says so itself — do not overstate it.

## Chaining to charts

```bash
python3 tools/metrics.py retention --csv e.csv --user u --date d --json > r.json
python3 tools/metrics.py funnel --csv e.csv --user u --step s \
    --order a,b,c --json > f.json
python3 tools/chartkit.py --type hbar --csv funnel.csv --x step --y count \
    --title "Funnel" --out funnel.svg
```

## What these numbers cannot tell you

- **Why.** A funnel locates a leak; it never explains it. The explanation
  comes from watching a session or reading the support tickets from that step.
- **Causation.** A cohort that retains better may have been acquired from a
  better channel, in a better season, alongside three other changes.
- **Counterfactual.** "Retention improved after the redesign" needs a control
  group to mean anything. Without one, say "improved after", never "improved
  because".

## Data quality checks — run these first

Every one of these has silently corrupted a real analysis:

- **Duplicate user rows** inflate the top of a funnel and depress every rate
  below it
- **Timezone drift** in the date column smears cohorts across boundaries;
  `metrics.py` truncates to date, so mixed-timezone exports will misassign
- **Bot traffic** in impressions but not in conversions makes the first step
  the "leak" — check whether step one is 20x step two
- **A step renamed mid-period** silently truncates the funnel at that point.
  `funnel` prints unmatched step values it ignored; read that line
- **Users present in the events file but with an empty id** are dropped
  silently by design; confirm the count matches expectations

## Related

- `stat-guard` — before claiming any of these differences is real
- `anomaly-watch` — for when a metric breaks rather than trends
- `data-clean` — profile the export before trusting any of this
- `chart-forge` — to render the result
