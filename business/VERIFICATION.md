# Deal volume verification

Run 2026-08-08. The load-bearing question: **is there enough transaction
volume in the $50k+ band to support a diligence practice?**

Short answer: **yes, but the plan I recommended was wrong.** The buyer-side
one-off report is already sold by the marketplace itself, at the same price,
from inside the checkout flow. That finding kills the original wedge and
moves the business to the seller side.

Source tiers per `source-triage`: **A** primary/measured, **B** credentialed
secondary, **C** practitioner report, **D** content marketing. Marketplace
self-reported figures are **C at best** — they are marketing their own
liquidity and have every incentive to round up. Treated accordingly.

---

## What the numbers say

| Figure | Value | Tier | Note |
|---|---|---|---|
| Flippa sales per year | ~12,000 (~1,000/mo) | C | self-reported |
| Flippa new listings | 2,000+/mo, ~100/day | C | self-reported |
| Flippa value listed | ~$41M/mo | C | self-reported |
| Flippa value sold | ~$5M/mo | C | different source than the above |
| Empire Flippers, content sites | **~70 in 2023** | C | curated broker |
| Content-site transactions studied | 145 over 2023–2025 | C | ~48/yr in that sample |
| Flippa lifetime sales | ~$375M | C | |
| Empire Flippers lifetime | ~$280M | C | |
| Flippa registered buyers | 600k+ (one source says 1.5M) | C | sources disagree |
| Flippa searches | ~1M/mo | C | |

### Contradiction log

**Buyer count: 600,000 vs 1.5M.** Two marketplace-adjacent sources disagree
by 2.5x. Unresolved. Both are self-reported and neither defines "registered".
Do not cite either as a number; the only safe claim is "buyers vastly
outnumber deals", which both support.

**$41M listed vs $5M sold monthly.** Different sources, possibly different
periods, possibly different definitions. If both were true and comparable it
would imply ~12% sell-through — a striking figure that would make the seller
problem enormous. **I could not confirm they are comparable, so I am not
using it.** Flippa's stated ">90% success rate" appears to describe
*completion of agreed transactions*, not the share of listings that find a
buyer. The share of listings that never sell is the single most valuable
unknown in this memo and I could not source it.

---

## The finding that changes the plan

**Flippa already sells due diligence at $1,500 (standard) and $2,000
(enhanced).** Independent reviews note that because most Flippa listings are
under $10,000, those services are *"unrealistic for many buyers"*.

Three consequences, in order of severity:

1. **The buyer-side one-off report is an occupied position.** The incumbent
   is the marketplace, at my exact price point, placed at the moment of
   maximum intent. Competing there cold, with no track record, is the losing
   half of a distribution fight. My earlier recommendation was wrong on this
   and I am withdrawing it as the primary wedge.
2. **It also validates the price.** $1,500–2,000 is an established, paid,
   non-hypothetical price for exactly this deliverable. That is worth more
   than it costs — the pricing question is now settled by evidence rather
   than by my estimate.
3. **The volume is barbell-shaped.** ~$5M sold across ~1,000 monthly sales
   implies an average around **$5,000** — far below the level that supports
   a four-figure report. The deals that can carry the fee are the thin tail,
   not the fat body.

## Sizing the band that can actually pay

Deals under roughly $30k cannot justify a $1,500 report; the fee would be 5%+
of the purchase price. So the addressable set is:

- **Flippa, $50k+**: unknown share of 12,000/yr. On a power-law distribution
  with a ~$5k average, a few percent is a reasonable guess → very roughly
  **250–600/yr**. This is an estimate, not a measurement, and it is the
  weakest number in this memo.
- **Empire Flippers**: ~70 content/yr, plus other categories.
- **Everyone else** — Motion Invest, Investors Club, Acquire, Quiet Light,
  FE International, Website Closers, plus off-market: no figures found.

**Working estimate: 1,000–2,000 qualifying deals per year across the whole
market.** Stated as an estimate. It is enough for a one-person practice
needing 2–4 engagements a month; it is not enough for a venture-scale
business, and nobody should plan as though it is.

## The timing window

Median time to close: **sub-$50k in 15 days, $50k–250k in 49 days, $250k+ in
73 days.**

This is operationally decisive. Seven weeks in the target band is ample room
to sell into, deliver, and be paid before the deal closes. Below $50k the
15-day window is too tight for a considered engagement — which is a second,
independent reason to ignore the small end.

---

## What survives, and what replaces it

**Dead:** buyer-side one-off reports on Flippa listings. Occupied by the
house, at the same price, with better placement.

**Alive, and now the primary wedge — the seller side.** The reasoning:

- Marketplace diligence exists to serve *buyers*. Sellers are sold listing
  upgrades, not scrutiny.
- The marketplace is **structurally conflicted** about telling a seller their
  numbers look weak: it earns commission on closing, not on accuracy. It will
  never build this product properly. That is a durable gap, not a temporary one.
- ~2,000 new listings a month on Flippa alone. Sellers already pay to list and
  pay ~10% commission — the budget exists and the willingness is proven.
- In the $50k–250k band a seller has 49 days of buyer scrutiny to survive.
  Reducing uncertainty *before* it is discovered is worth more than defending
  it afterwards.

**Alive — buyer side off-marketplace.** Private and off-market deals, Empire
Flippers, and the smaller brokers have no house diligence product. Lower
volume, higher trust requirement, better margin.

**Strengthened — the benchmark corpus.** Buyers outnumber deals by orders of
magnitude (hundreds of thousands of registered buyers against ~1,000
qualifying deals a year). That inverts the model I proposed last: deal count
is the binding constraint, buyer attention is abundant. So the durable asset
is not per-deal work at all — it is the accumulated dataset of what listings
claimed versus what their numbers showed. No marketplace will publish that,
because it is against their interest. **This moves from "layer 3, someday" to
the actual destination.**

---

## Honest confidence

**55%** that a seller-side diligence practice reaches paying clients within
90 days of real outreach. Down from the ~70% implied by my earlier
recommendation, and the reduction is entirely due to the Flippa finding.

The number is recorded before the outcome, in
`business/decisions/0001-launch-seller-side-diligence.md`, so it can be
scored later rather than remembered favourably.

## What would change this answer

- **Listing sell-through rate.** If most listings genuinely fail to sell, the
  seller-side market is far larger than sized here and confidence should rise.
  Unsourced; worth an hour with a broker who will answer honestly.
- **Whether sellers currently buy anything analytical.** If no seller-facing
  paid analytics product exists anywhere in this market, that is either a gap
  or a graveyard, and the two look identical from outside. The 14-day test in
  the decision record is designed to tell them apart.
- **Flippa extending diligence to sellers.** They have the distribution to
  end this overnight. Watch for it; it is the main platform risk.

## Sources

- [Flippa — Digital M&A Insights H1 2026](https://flippa.com/lps/insights-report-h12026)
- [Flippa — online business data insights](https://flippa.com/blog/online-business-data-insights/)
- [Investors Club — Flippa statistics](https://investors.club/flippa-statistics/)
- [Investors Club — Flippa due diligence](https://investors.club/flippa-due-diligence/)
- [The Website Flip — Flippa review, 152+ transactions](https://thewebsiteflip.com/review/flippa/)
- [The Website Flip — Empire Flippers vs Flippa](https://thewebsiteflip.com/review/empire-flippers-vs-flippa/)
- [Empire Flippers — marketplace](https://empireflippers.com/marketplace/)
- [ExitBid — Flippa fees explained 2026](https://exitbid.io/blog/flippa-fees-explained-2026)
- [Flippa — broker commission rates](https://flippa.com/blog/how-much-do-brokers-typically-charge-to-sell-a-business/)

Every marketplace figure above is self-reported by a party with an interest in
appearing liquid. None of it is audited.
