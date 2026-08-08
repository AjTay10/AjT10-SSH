# Intake — what to request from a client

Send this verbatim. Ask for exports, never for dashboard access — read-only
access sounds helpful and creates a data-handling obligation you do not want.

---

## What I need

Whichever of these you have. Any one is enough to start; all three gives the
full picture. CSV exports, not screenshots.

**1. Page or item breakdown** — one row per page, post, or product.

| Column | Example |
|---|---|
| identifier | `/best-espresso-machines` |
| value | pageviews, sessions, or revenue for the period |
| publish date | `2022-04-11` — optional but this is what reveals decay |

*Where:* Google Analytics → Reports → Pages and screens → Export.
Search Console → Performance → Pages → Export.

**2. Revenue by source** — one row per advertiser, sponsor, affiliate
programme, or product.

| Column | Example |
|---|---|
| source | `Sponsor: BrewCo` |
| amount | period revenue |

**3. Monthly time series** — one row per month, at least 12 months, ideally 24.

| Column | Example |
|---|---|
| month | `2024-03-01` |
| value | sessions, revenue, or subscribers |

---

## Also tell me

- The period each export covers, and the timezone the analytics use
- Whether anything unusual happened in it — a migration, a redesign, a viral
  post, a Google update you noticed, a sponsor starting or ending
- One number from your own dashboard I can reconcile against (total sessions
  or total revenue for the period)

That last one matters more than it sounds. If my total doesn't match yours,
the export is filtered or windowed differently than I assume, and every number
downstream would be wrong without either of us noticing.

---

## What I will not ask for

Login credentials, ad-network passwords, or anything that identifies your
customers or subscribers. If a file contains personal data — email addresses,
names, IPs — strip those columns before sending. I don't need them and I don't
want to hold them.

---

## What you get back

A report covering concentration, decay, and trend reality, plus an explicit
list of what the data does not establish. Three business days.

It is not a valuation, an appraisal, or investment advice, and it cannot
verify that the numbers you send me are accurate — only what they imply if
they are.

---

# Internal checklist — before starting analysis

- [ ] At least one of the three inputs present
- [ ] Time series has ≥ 6 periods, or trend analysis is dropped and the client
      told *before* invoicing
- [ ] Item breakdown has ≥ 3 positive rows
- [ ] Reconciled one total against the client's stated figure
- [ ] Checked for a "Total" row appended to the export (inflates every sum ~2x)
- [ ] Checked for duplicate rows across pagination boundaries
- [ ] Confirmed which side of the transaction I am on, in writing
- [ ] Confirmed I am not already engaged by the other side
- [ ] Personal data absent, or deleted on receipt
