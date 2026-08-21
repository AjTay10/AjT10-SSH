# Launch playbook — from this repo to a live product

The step-by-step implementation of the whole process. Companion to
[pdf-product-business.md](pdf-product-business.md) (the strategy and research)
and [passive-income-teardown.md](passive-income-teardown.md) (why this model).
Everything referenced already exists in `products/budget-reset-planner/`.

Time budget for phases 1–5: one focused weekend. Nothing here requires
spending money except the Etsy listing fee (currently a fraction of a dollar
per listing — check the current fee when you sign up).

---

## Phase 0 — Get the assets (30 min)

1. Clone the repo (or download the three product files):
   - `The-Budget-Reset-Planner.pdf` — the 14-page printable (base product)
   - `interactive/The-Budget-Reset-Interactive.html` — the browser app
     (premium tier; verified on desktop and mobile)
   - `LISTING.md` — paste-ready title, 13 tags, description
2. Open both products yourself. Print two pages of the PDF at 100% scale;
   open the HTML on your phone and your computer, enter fake numbers, close
   and reopen it to confirm your data persisted. Never sell a file you
   haven't used.
3. Optional edits: change wording or pages in `generate_planner.py`, then
   `pip install reportlab && python3 generate_planner.py` to rebuild the PDF.

## Phase 1 — Accounts (1–2 hrs, mostly waiting on verification)

1. **Etsy seller account** at etsy.com/sell — pick a shop name that is a
   brand, not a keyword ("BudgetResetStudio"-style beats
   "BestBudgetPlannersPDF"). Complete identity and bank verification.
2. **Pinterest business account** — same brand name. This is your only
   social channel at launch; ignore the rest for now.
3. Skip for now (deliberately): your own website, email tool, Gumroad, paid
   ads, an LLC. Each becomes worth doing only after strangers buy (phase 8).

## Phase 2 — Package the products (1 hr)

1. **Base listing file:** the PDF as-is. Etsy digital listings take up to
   5 files, 20 MB each — you are nowhere near the limit.
2. **Premium tier:** zip the HTML together with a one-page
   `START-HERE.pdf` you make from a short doc that says: "Unzip. Double-tap
   the .html file — it opens in your browser. Works offline. Your numbers
   save on your device only. Use Export backup before switching devices."
   Buyers who don't get an instructions page leave "it doesn't work"
   reviews.
3. Add a license line to both (last PDF page footer already covers it):
   personal use only, no resale or redistribution.

## Phase 3 — Listing photos (2–3 hrs, the highest-leverage hours in this plan)

Buyers judge printables entirely by the listing images. Make the six shots
specified at the bottom of `LISTING.md`:

1. Cover flat-lay in a mockup scene (search "free device/paper mockup" —
   Canva's free tier covers this).
2. "What's inside" grid of all 14 pages (export page images from the PDF).
3. Close-up: Monthly Budget page.
4. Close-up: Debt Payoff Tracker, half shaded in — show it *used*.
5. For the interactive tier: phone + laptop mockup showing the app's
   Overview screen.
6. Format infographic: US Letter · instant download · print or use in
   browser.

Rule: every image answers a buyer question; none is decoration.

## Phase 4 — Create the base listing (1 hr)

1. New listing → type **Digital download**. Upload the PDF.
2. Paste the title, all 13 tags, and the description from `LISTING.md`
   verbatim.
3. **Price by evidence, not feeling:** search Etsy for "budget planner
   printable", note the price of the top 10 results with the most reviews,
   and price in the middle of that band. Never the cheapest — cheapest
   reads as worthless in this category.
4. Publish. The listing fee is the only launch cost.

## Phase 5 — Create the premium listing (30 min)

Second listing: "Interactive Budget Planner" using the zip from phase 2,
the mockup shots, and a description that leads with the differences —
auto-calculating, tracks itself, works on phone, no app or subscription,
data stays on the buyer's device. Price it 2–3× the PDF. Link each
listing to the other in their descriptions ("prefer paper? / prefer
automatic?").

## Phase 6 — Launch week (2 hrs total, spread out)

1. Create 5–10 Pinterest pins from your listing images (vertical 2:3
   crops), each linking to a listing. Pin over several days, not in one
   burst. Printables are one of the few niches where Pinterest still
   compounds; boards to target: budgeting, debt free, money saving.
2. Tell nobody you know to buy it. Friends' purchases pollute your only
   early signal (phase 8 needs *stranger* sales).
3. Optional demand probe: a small, hard-capped Pinterest or Etsy Ads
   budget treated purely as paid information about whether the listing
   converts — set the cap before you start and stop at the cap regardless.

## Phase 7 — Operate (≈2 hrs/week)

- Answer Etsy messages twice a week — response time affects search rank.
- One new Pinterest pin a week reusing existing images.
- Month 2 onward: one niche variant a month via `generate_planner.py`
  (couples · irregular-income freelancer · college student). Each variant
  is a new listing = a new search surface for near-zero marginal work.
- Quarterly: refresh listing photos and re-check competitor pricing.

## Phase 8 — Measure against the pre-committed kill criteria

Written before launch so they can't be negotiated with later:

- **60-day rule:** zero stranger purchases after 60 days of the listing
  being live and getting impressions (Etsy stats show these) falsifies the
  niche variant. Change the niche served, not the fonts.
- **Day-90 ledger:** total revenue ÷ total hours (including everything
  above). If the trajectory can't plausibly beat "index the money and work
  overtime instead" within a year, stop — that comparison is the whole
  discipline.
- First stranger sale = proceed signal: build the next rung, not more
  marketing for the current one.

## Phase 9 — Scale only what worked (after proof, not before)

In order, each gated on the previous one paying for itself:

1. **More variants** in the winning niche (the script makes these an
   afternoon each).
2. **The bundle listing** (PDF + all variants + interactive) at the top
   price point — bundles raise average order value with zero new product.
3. **Email capture:** add a "companion pack" insert page to the PDF
   pointing at a simple landing page with an email signup; the list is the
   one channel no platform can repossess.
4. **Second storefront** (Gumroad or your own site) once Etsy sales are
   steady — platform diversification after product-market fit, not
   instead of it.
5. Sweep profits to index funds monthly. The business is the engine; the
   portfolio is where "passive" becomes literally true.

## What can go wrong (read once, then launch anyway)

- Zero traffic for weeks at first is normal — new Etsy listings crawl
  before search trusts them. That is why the kill clock is 60 days of
  impressions, not 60 days of existence.
- One-star review risk on the interactive tier: buyers who lose data by
  clearing their browser. The START-HERE page and the in-app backup
  banner exist for exactly this; answer any such review politely with the
  export instructions.
- Copycats: expected, unavoidable, mostly harmless. Your defenses are
  review count, photo quality, and shipping variants faster than they
  copy — never a race to the lowest price.
