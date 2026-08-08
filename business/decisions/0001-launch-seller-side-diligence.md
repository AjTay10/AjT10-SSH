# 0001 — Launch metric diligence, seller side first

- Date: 2026-08-08
- Status: proposed
- Reversible: yes — the only sunk cost is time; no inventory, no capital, no contracts
- Decider: AJ

## Context

A working analytics toolchain exists (`tools/`, 10 tools, 118 tests) and a
one-command report generator sits on top of it (`business/report_build.py`).
The question is whether it converts to revenue.

Verification of deal volume (`business/VERIFICATION.md`) established three
things that constrain the answer:

1. **Flippa already sells buyer-side due diligence at $1,500–$2,000.** The
   incumbent is the marketplace, at my price point, inside the checkout flow.
2. Volume is barbell-shaped. ~$5M sold monthly across ~1,000 sales implies an
   average near **$5,000** — far below what supports a four-figure report.
   Empire Flippers sold roughly **70 content sites in a year**.
3. Median close time is **49 days in the $50k–250k band**, which is a workable
   window to sell into and deliver within.

The original recommendation — buyer-side one-off reports on marketplace
listings — is therefore contested by the house, on the house's turf. That plan
is withdrawn before any effort was spent on it.

## Options considered

| Option | Upside | Downside | Verdict |
|---|---|---|---|
| Buyer-side reports on Flippa listings | Clear intent, proven price | Marketplace sells this already, better placed | **Rejected** |
| **Seller-side pre-listing analysis** | Marketplace is structurally conflicted here and won't build it; sellers already spend to list | Sellers are optimistic and cheap; unproven willingness | **Chosen** |
| Buyer-side, off-marketplace only | Higher margin, no house competitor | Low volume, high trust barrier, slow start | Secondary |
| Benchmark data product | Only genuinely defensible asset | Needs ~50 engagements of corpus first | Destination, not start |
| Build SaaS | Scales | Sells for $49/mo to people who won't use it | Rejected |
| Do nothing | No downside | Toolchain stays a hobby | Rejected |

## Decision

Sell **seller-side metric diligence** at $1,200 fixed, to people preparing to
list a content site, newsletter, or creator business in the $50k+ band.
Buyer-side work off-marketplace is taken opportunistically at $1,800.

## Reasoning

Including the unflattering part: the buyer side was the better idea and it is
occupied, so this is the second choice, taken because the first was closed.

The seller side survives on a structural argument rather than a preference.
A marketplace earns commission on closing, not on accuracy. It will never
build a product whose output is "your numbers look weaker than you think."
That conflict is durable, which makes the gap durable.

The mechanism for the seller paying: in the $50k–250k band a listing endures
49 days of buyer scrutiny. Buyer discount is a function of *uncertainty*, not
only of the headline number. A seller who pre-empts the concentration finding
with context is discounted less than one who lets a buyer discover it. That is
a testable claim, not a slogan — and it is the claim the whole plan rests on.

## Confidence

**55%** that this reaches at least one paying client within 90 days of
starting real outreach.

Recorded before the outcome. Down from the ~70% I implied before the Flippa
finding; the entire reduction is that one fact.

Secondary: **25%** that it reaches $5k in cumulative revenue within 180 days.

## What would change my mind

- A broker states that most listings do sell → the seller's pain is smaller
  than assumed, and confidence should fall.
- A broker states most listings never sell → market is larger, confidence rises.
- Flippa launches a seller-facing analytics product → the gap closes; stop.
- Three sellers say "buyers never ask about concentration" → the mechanism is
  wrong and no amount of delivery quality fixes it.

## Kill criteria

Committed in advance, in numbers, before anything is invested.

**After 14 days of outreach (target: 40 sellers contacted, 5 free samples sent):**

- Fewer than **3 substantive replies** AND **zero** paid engagements → stop.
  Not "reframe and retry with new copy" — stop, and record why.
- Between 3 and 8 replies, zero paid → one price test at $600, 14 more days.
  If still zero → stop.
- Any paid engagement → continue to the 90-day mark and re-score.

**Additional hard stop:** if delivering a report takes more than 4 hours of
work by the third engagement, the economics do not survive and the product
must be narrowed before continuing.

## Review

- **Scheduled: 2026-11-06** (90 days). Set now, because an unscheduled review
  does not happen.
- Score the process, not only the outcome. A paid client from a bad process is
  the most expensive box on the grid — it gets promoted into policy.
