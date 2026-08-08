---
name: deal-diligence
description: Analyze whether a content site, newsletter, channel, or creator business is worth what is being asked — concentration, decay, trend reality, and the specific ways listing numbers mislead. Use when the user is buying or selling an online business, evaluating a listing, doing due diligence on an acquisition, checking whether a growth chart is real, or asking what a set of traffic or revenue numbers is actually worth. Also use to audit any asset whose value rests on a self-reported metric.
---

# Deal diligence

A listing shows you a chart that goes up. The chart is usually true and almost
always misleading. Your job is to find out what the number rests on and how
fast it is running down.

Everything here works from data the seller provides or that is public. It
computes descriptive statistics — **it is not a valuation, an appraisal, or
investment advice**, and it cannot tell you whether the inputs are honest.
Say that in writing on every engagement.

## Run these four, in order

**1. Is the total resting on everything, or on three things?**

```bash
python3 tools/concentration.py --csv pages.csv --item url --value pageviews --label pages
python3 tools/concentration.py --csv revenue.csv --item sponsor --value amount
```

Read `effective count` before anything else. "13.2 of 382" means that despite
382 pages, the asset behaves like thirteen. Then read `remove the top 1` —
that single line is usually the entire risk of the deal.

**2. Is the value being renewed or run down?**

```bash
python3 tools/concentration.py --csv posts.csv --item id --value revenue \
    --date published --decay --period year
```

The signal to look for is **production rising while yield falls**: more items
published each year, less earned per item. That is a business working harder
to stand still, and it is invisible in any total.

The replacement ratio is biased *in favour of old work*, because older items
have had longer to accumulate. So a ratio above 1.0 is strong evidence of
renewal; a ratio below 1.0 is suggestive but not conclusive, and needs
per-item performance at equal age to settle. The tool says this itself — do
not overstate it in your write-up.

**3. Is the growth trend real, or one spike being annualized?**

```bash
python3 tools/anomaly.py --csv monthly.csv --date date --value sessions --seasonal weekly
python3 tools/metrics.py growth --csv monthly.csv --date date --value sessions
```

`growth` explicitly flags the case where net growth is positive while the
recent window is negative — a chart that goes up and to the right describing
something that stopped working six weeks ago. `anomaly` separates a genuine
level shift from noise; a changepoint eight months ago that never recovered is
the most common hidden defect in a listing.

**4. Does any claimed improvement survive a significance test?**

```bash
python3 tools/abtest.py compare --a 41/1180 --b 58/1205
```

"Conversion improved 38% after the redesign" on a few hundred sessions is
noise with a story attached.

## The eight defects worth checking every time

1. **One-page dependency.** Top page over ~10% of traffic, and it ranks for one
   term. Check its position history and whether the SERP has changed shape.
2. **One-sponsor dependency.** Concentration on the revenue column. A single
   advertiser at 40% is a renegotiation away from halving the business.
3. **Annualized spike.** A launch, a viral post, or a seasonal peak projected
   forward as a run rate.
4. **Silent changepoint.** Traffic broke months ago; the trailing-twelve-month
   average still looks fine because the good months are still inside it.
5. **Vintage collapse.** Nothing published in the last 18 months performs.
6. **Metric substitution.** Email open rates have been structurally inflated
   since Apple's Mail Privacy Protection; a seller leading with open rate
   rather than click rate is either uninformed or counting on you being.
7. **Cross-platform blending.** Audience totals summed across platforms as if
   they were unique people, or engagement rates compared between platforms
   that count a "view" at different moments. See `social-analytics`.
8. **Founder dependency.** The face, the relationships, or the writing voice
   leaves with the seller. Not a number — ask what the asset is without them.

## Presenting findings

Buyers and sellers both need the same discipline, in different directions.

**For a buyer:** lead with the one finding that changes the price, then the
evidence, then explicitly what you could *not* determine and what data would
settle it. Never state a valuation. State what the numbers support and what
they do not.

**For a seller:** the counterintuitive move is that presenting the honest cut
with intervals beats presenting the flattering cut unverifiably. Buyer discount
is a function of *uncertainty*, not just of the headline. A seller who
pre-empts the concentration finding with context ("yes, one page is 20% — here
is its four-year position history") gets discounted less than one who leaves
the buyer to find it.

**Never serve both sides of the same transaction.** The only thing being sold
here is disinterest.

## Public analysis, private specifics

Publishing the *method* against anonymized examples is legitimate and is the
best marketing this work has. Publishing "this named listing is inflated" is a
defamation risk with your name on it, and accuracy is the entire product.
Analyze public claims as claims; keep specific verdicts to the client who paid.

## Related

- `social-analytics` — normalizing platform exports before any of this
- `anomaly-watch` — separating real breaks from noise
- `stat-guard` — before believing any claimed improvement
- `source-triage` — when the seller's numbers come with a case study attached
- `red-team` — before wiring money
