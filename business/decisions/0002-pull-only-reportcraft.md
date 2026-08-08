# 0002 — Pull-only distribution: Reportcraft

- Date: 2026-08-08
- Status: proposed
- Reversible: yes — the tool is built and costs nothing to leave sitting
- Supersedes: nothing. `0001` stays on file; it is not withdrawn, it is
  **blocked** by a constraint that arrived after it was written.

## Context

A hard constraint was set after `0001`: **no cold calls, no cold emails, no
mandatory outreach**, in this plan or any future one.

That blocks `0001` outright. Seller-side diligence reaches its first client
through contacting sellers; there is no version of it that does not. It stays
recorded because the verification work in `VERIFICATION.md` remains true and
would be needed again if the constraint ever lifts.

With outreach removed, customers must arrive on their own. That leaves
exactly three discovery mechanisms: search, a marketplace's own algorithm, and
users bringing other users. The first two were checked and are worse than they
look:

- **Shopify App Store** — ~13,000 apps, 7,000 added in two years, **median
  listed app under $1,000/month**, and top-tier apps take **70%+ of installs**.
  Below a 4.0 rating, install success drops 40–50%. That is a lottery.
- **Search from a zero-authority domain** — three to six months before a page
  settles, against AI answers that increasingly end the session without a click.

## Options considered

| Option | Verdict |
|---|---|
| Seller-side diligence (`0001`) | **Blocked** by the no-outreach constraint |
| Marketplace app listing | Lottery; median under $1k/mo, winner-take-most discovery |
| SEO-first free tool | Viable but slow; 3–6 months before any signal |
| **Shareable-artifact tool** | **Chosen** — the user distributes it, not me |
| Contract/freelance listing | Highest confidence (~55%) but it is a job, and it compounds nothing |
| Do nothing | The toolchain stays a hobby |

## Decision

Ship **Reportcraft**: a single self-contained HTML file that turns a CSV
export into a client-ready report, carrying a footer credit.

Distribution mechanism: **the output is the advertisement.** The person who
makes a report makes it *in order to send it to someone else* — a client, a
board, a buyer. Sharing is not a favour to request; it is the reason the tool
was opened.

## Reasoning

Including the part that argues against it: this is the *lowest-confidence*
plan considered, and it is chosen because the constraint eliminated the
higher-confidence ones rather than because it is better.

What supports it:

- Products with built-in sharing mechanisms convert **13–16% of visitors to
  signups**, against 7–8% for ordinary trials. Calendly reached 20 million
  users on exactly this loop.
- The recipient is qualified by construction. A freelancer sends the report to
  a **paying client** — a business that also needs reports. Contrast a creator
  sharing stats with fans, who never buy analytics tools.
- Removing someone else's branding from a document you hand a client is the
  most reliably paid-for upgrade in software.
- The machinery already existed. `report_build.py` and `dashboard.py` were
  built for `0001` and produce exactly this artifact.

## Confidence

**35%** that this produces a first paying customer within 6 months.
**20%** that it reaches $500/month within 12 months.

Recorded before the outcome. Deliberately lower than `0001`'s 55%, and the
gap is the price of the constraint, not a flaw in the execution.

## The honest weakness

**The loop needs volume, and the only source of volume is the loop.** That is
circular, and it is why this is 35% rather than 70%. Freemium converts
**2–5%**; one in four freemium products converts under 2.5% within six months.
Thousands of free users are needed to produce a few hundred dollars a month.

This fails quietly over a year rather than loudly in a month, which makes the
tripwire below the most important line in the document.

## Kill criteria

Committed before any promotion, while it is still easy to be honest.

- **90 days from first publication:** fewer than **50 distinct people** have
  built a report → the discovery assumption is wrong. Stop promoting it and
  either fix discoverability specifically or shelve it.
- **180 days:** more than 200 reports built and **zero** requests to remove
  the footer → the upgrade nobody asks for is not an upgrade. The monetization
  is wrong even if the tool is right.
- **Any point:** if maintaining it exceeds ~2 hours a month without revenue,
  it is a hobby. That is permitted, but it must be called one.

**Explicitly not a kill signal:** slow early growth. This model is expected to
look dead for months. That is why the thresholds are counted in reports built
rather than in weeks elapsed.

## What would change my mind

- Reports being built but never downloaded → the artifact is not the thing
  people want; the analysis is. That would point back toward a service.
- Anyone asking to pay before being asked → raise confidence sharply and build
  billing immediately.
- A competitor shipping the same thing free with better distribution → stop.

## Review

- **Scheduled: 2026-11-06**, alongside the `0001` review. Score the process,
  not the outcome.
