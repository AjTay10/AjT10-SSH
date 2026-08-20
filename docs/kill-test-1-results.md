# Kill-test 1 results — niche search for the digital-product plan

Run 2026-08-20, per the gate defined in `passive-income-200.md`:

> Within ≤8 hours, identify a niche where ≥5 of the top 20 marketplace
> search results show recent-sale signals AND have a visible, specific,
> beatable flaw. Can't find one → stop. Do not broaden the search.

Method: three parallel research passes over live marketplace pages
(Gumroad product pages, Notion marketplace, Creative Market) plus
search-result snippets for Etsy, which blocks direct page fetches (HTTP
403) from this environment. Creative Fabrica also blocks (403). Gumroad
product pages turned out to be JS-rendered and yielded titles only. Every
number below is quoted from a fetched page or a search snippet; "not
visible" means not visible, and no figure is invented.

## Niche 1: Creator business trackers (brand-deal / rate / analytics)

**Verdict: 0 of 18 — definitive kill, on the demand side.**

The highest rating count found on any *paid* listing was 2. The only
listings above 5 ratings were free Notion templates (6 and 15 ratings —
free, so zero willingness-to-pay evidence; one of them had 17% two-star
ratings and a broken last-updated display). Gumroad's overall best-seller
chart contains no creator-business tracker at all; the nearest adjacent
product is a general Notion productivity bundle. Several "products" in the
niche are themselves PLR resale assets. Lots of sellers, no verifiable
buyers. This niche is dead regardless of measurement limitations.

## Niche 2: Wedding planning / budget spreadsheets

**Verdict: 1 of 20 — fails the threshold as measured.**

Demand is real: six or seven Etsy listings clear the 300–10,800 review
range per search snippets. But only one flaw was verifiable from
accessible listing material (a 1.4k-review seller shipping each colorway
as a separate listing). For the other high-review sellers, Etsy's 403
made flaw inspection impossible — "no flaw found" there means "not
inspectable", not "flawless". Independently bearish: the niche is
visibly flooded with master-resell-rights clones of the same spreadsheet,
and the free layer is dense (Tiller, gdoc.io, TheGoodocs, Notion's entire
201-template weddings category — all free).

## Niche 3: Small-business bookkeeping / income-expense spreadsheets

**Verdict: 1 of 16 — fails the threshold as measured; strongest residual signal.**

Demand confirmed at scale: one listing at ~12,500 reviews (attribution
probable, not certain) and one at ~3,100. The 12.5k-review market leader
has a verified, nameable flaw stated on its own listing: Google-Sheets-only
("will not function properly on Excel"), no Excel variant, and no visible
tax-category/Schedule-C mapping — a feature a smaller competitor
explicitly advertises. But that is one verified flaw-plus-signal pair,
not five; every other flaw check was blocked by the same 403 wall.

## Ruling

**As pre-committed: no niche passed. Do not build.** The threshold was
set before the data came in, and re-interpreting a 1-of-20 as
encouraging is exactly the failure mode the gate exists to prevent.

One honest qualification, which is about the instrument rather than the
market: in niches 2 and 3 the binding constraint was that Etsy — the
venue where the sales signals actually live — cannot be inspected from a
datacenter. Niche 1 failed with full measurement and is dead. Niches 2
and 3 are *fail-as-measured, demand-confirmed, flaws-unverified*.

The only legitimate re-run is manual: a human with a browser spends
under one hour on Etsy examining the top 20 results for
"bookkeeping spreadsheet small business" — recording review count,
last-review date, and one nameable flaw per listing (no Excel version,
no multi-currency, hardcoded row caps, no tax mapping, dated screenshots).
The threshold stays ≥5 of 20; the kill rule stays. Anything else —
new niches, softened thresholds, "one more variant" — is theatre.

If the manual re-run also fails: the plan's own next line applies. The
market is saying the shelf is full, and the capital route
(~$58–63k at ~4% for $200/month) remains the only proven passive option.
