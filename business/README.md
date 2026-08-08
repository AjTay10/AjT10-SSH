# Metric diligence — the complete kit

Everything needed to start. Nothing here needs building; the remaining
decision is when.

## Read in this order

| File | What it settles |
|---|---|
| [`VERIFICATION.md`](VERIFICATION.md) | Is there enough deal volume? Sourced, with the finding that killed the original plan |
| [`decisions/0001-launch-seller-side-diligence.md`](decisions/0001-launch-seller-side-diligence.md) | The decision, confidence recorded before the outcome, and the kill criteria |
| [`PLAYBOOK.md`](PLAYBOOK.md) | Pricing, scope, how to run an engagement, guardrails |
| [`intake.md`](intake.md) | What to request from a client, and the pre-analysis checklist |
| [`terms.md`](terms.md) | Engagement note — send before any work starts |
| [`outreach/templates.md`](outreach/templates.md) | The seven messages you will actually send |
| [`sprint.csv`](sprint.csv) / [`sprint.ics`](sprint.ics) | The 14-day test, importable into a calendar |
| [`tracker.csv`](tracker.csv) | Log every contact — this becomes the benchmark corpus |

## Deliver a report

```bash
python3 business/report_build.py \
    --client "Listing #A-2291" \
    --prepared-for "a prospective buyer" \
    --pages   pages.csv   --page-item url    --page-value pageviews --page-date published \
    --revenue rev.csv     --rev-item source  --rev-value  amount \
    --traffic monthly.csv --traffic-date month --traffic-value sessions \
    --out report.html
```

Supply whichever inputs the client has — sections appear for the data present
and are **omitted rather than faked** when it is missing. The report lists
what it could not establish, which is usually the most credible page in it.

Self-contained HTML: no CDN, no fonts, no network calls. Renders in light or
dark. Print to PDF for clients who want one.

Try it end to end:

```bash
python3 business/sample.py          # generates fixtures and a sample report
```

## The one-paragraph version

Buyers and sellers of online businesses transact against self-reported growth
charts. Those charts are usually true and usually misleading, because the
total hides what it rests on. Four analyses — concentration, decay, trend
reality, significance — surface that in about three hours, and the output is
worth four figures because it lands on a decision worth six.

The marketplace already sells the buyer-side version at $1,500–$2,000, which
is why this starts on the **seller side**, where the marketplace has a
structural conflict it will not resolve: it earns commission on closing, not
on accuracy.

## The economics, honestly

| | |
|---|---|
| Seller-side fee | $1,200 |
| Buyer-side fee | $1,800 |
| Target time per engagement | under 3 hours by the third |
| Qualifying deals per year, whole market | **1,000–2,000, estimated** |
| Confidence in a paying client within 90 days | **55%** |

The deal-count figure is the weakest number in this kit and it is an estimate,
not a measurement — see `VERIFICATION.md` for how it was derived and why it
could be wrong.

Per-engagement work is not the destination. After ~50 engagements the
`tracker.csv` corpus becomes benchmarks, which is the only asset here that
cannot be copied by someone reading the method, and which no marketplace will
ever publish because it runs against their interest.

## Before the first outreach

- [ ] Read the kill criteria in `decisions/0001` and accept them
- [ ] Decide the start date and put `sprint.ics` in your calendar
- [ ] Pick the publishing surface for teardowns
- [ ] Have `terms.md` ready to paste
- [ ] Run `business/sample.py` once so you have seen the deliverable

## What this kit deliberately does not do

It does not scrape, it does not name a listing publicly, it does not quote a
price, and it does not serve both sides of a transaction. Each of those is a
constraint that costs revenue in the short run and is the entire product in
the long run.
