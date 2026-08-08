# Playbook

Everything needed to run an engagement. Read `VERIFICATION.md` first for why
the business is shaped this way, and `decisions/0001` for the kill criteria.

## The offer

**Metric diligence** — a fixed-price analysis of what an online business's
numbers actually rest on, delivered as a report the client can hand to the
other side of the deal.

| | Seller side | Buyer side |
|---|---|---|
| Price | **$1,200** | **$1,800** |
| Turnaround | 3 business days | 2 business days |
| For | Preparing to list, $50k+ | Off-marketplace or broker deals |
| Deliverable | HTML + PDF report | Same, plus a 30-min call |

**Why $1,200 seller / $1,800 buyer.** Flippa sells buyer-side diligence at
$1,500–$2,000, which establishes the price is real rather than my guess. Buyer
side is priced at par because competing below an incumbent on price signals
inferiority. Seller side is priced under it because the seller is buying an
advantage rather than avoiding a loss, and loss aversion is the stronger
motivator — the discount buys the objection away.

**Do not discount below $600.** The kill criteria include one price test at
$600. Below that the engagement cannot pay for the hours and a "yes" teaches
you nothing except that free things are popular.

## Scope — what is in and out

**In:** concentration of traffic and revenue, vintage and decay analysis,
trend reality and changepoint detection, statistical significance of any
claimed improvement, and a written list of what the data does *not* establish.

**Out, explicitly and in writing:**

- Valuation, appraisal, or a suggested price
- Investment advice or a recommendation to transact
- Verification that the client's numbers are truthful
- Legal, tax, or accounting opinion
- Traffic-source authenticity, backlink audit, or SEO forecasting

That "out" list is not defensive boilerplate. It is the thing that keeps the
work honest and keeps you out of regulated territory. Say it on the call, put
it in the engagement note, print it in the report footer.

## The rule that cannot be broken

**Never serve both sides of the same transaction.** Not sequentially, not with
disclosure, not for double the fee. The only thing being sold here is
disinterest; sell it once and it is gone permanently.

If a buyer approaches you about a listing you prepared for the seller, say so
immediately and decline. That sentence is worth more than the engagement.

## Running an engagement

**1. Intake (15 min).** Send `intake.md`. You need, at minimum, one of:
per-page or per-item breakdown, revenue by source, or a monthly time series.
All three is ideal. Fewer than 6 periods of history means no trend analysis and
you should say so before taking money.

**2. Analysis (60–90 min).**

```bash
python3 business/report_build.py \
    --client "Client name or listing ref" \
    --prepared-for "the prospective buyer" \
    --pages pages.csv   --page-item url --page-value pageviews --page-date published \
    --revenue rev.csv   --rev-item source --rev-value amount \
    --traffic month.csv --traffic-date month --traffic-value sessions \
    --out report.html
```

Then read every finding and delete any you cannot defend out loud. The
generator is a first draft with statistics attached, not a deliverable.

**3. Sanity pass (20 min).** Reconcile one number against the client's own
dashboard. If they disagree, stop and ask — an export that is filtered or
windowed differently makes every downstream number wrong, invisibly.

**4. Delivery (15 min).** Send the report with a three-sentence email: the one
finding that matters, what you could not determine, and the offer of a call.

**Target: under 3 hours by the third engagement.** If it is not trending there,
the kill criteria say narrow the product.

## Positioning, in the client's words

Not "statistical due diligence." Sellers do not wake up wanting that.

- To a seller: *"Buyers are going to find the concentration in your traffic.
  Better that you find it first and have an answer ready — listings that
  pre-empt the obvious objection get discounted less."*
- To a buyer: *"You're about to wire six figures against a chart. I'll tell
  you what that chart rests on and what it can't tell you."*

## What generates leads

Ranked by what actually works from a standing start:

1. **Published teardowns.** Weekly, anonymized, method-first. This is
   simultaneously the marketing, the credential, and the falsification test.
   You have no track record — the work *is* the track record.
2. **Broker relationships.** They see every deal and have no statistical
   capability. One relationship beats a hundred cold emails. They will want
   revenue share; take it, their deal flow is worth more than your margin now.
3. **Direct outreach to active listings.** Templates in `outreach/`.
4. **Answering diligence questions in public** where buyers ask them.

Cold outreach is third for a reason. It converts worst and is the first thing
people reach for.

## Legal and reputational guardrails

- **Never name a specific listing publicly.** Analyze public claims as claims;
  keep verdicts to the client who paid. A wrong public accusation is
  defamation with your name on it, and accuracy is the entire product.
- **Anonymize every published teardown.** Change the niche, round the numbers,
  never link the listing.
- **No scraping against terms.** Everything here works on client-supplied data
  or manually reviewed public pages. There is no technical need to scrape and
  the exposure is real.
- **Client data is confidential.** State the retention period, and delete on
  request. The benchmark corpus uses aggregates only — never a client's
  identifiable figures.
- **You are not a licensed advisor.** Nothing in the deliverable states or
  implies a price. If asked "what's it worth", the answer is: *"That's not
  what I do. Here's what the numbers support and what they don't."*

## The destination

Per-engagement work is the means, not the end. After roughly 50 engagements
you own something nobody else has: a private dataset of what listings claimed
versus what their numbers showed. Benchmarks — *"median effective count for
content sites in this range is 18; this one is 13"* — are the only asset here
that cannot be copied by someone reading your method, and no marketplace will
ever publish them because it is against their interest.

Start logging every engagement's aggregate stats from the first one.
`tracker.csv` has the columns.
