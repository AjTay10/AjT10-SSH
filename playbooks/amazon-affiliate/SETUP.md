# Setup — start to finish

Everything to stand up before publishing anything. Total cash outlay to
start: under $100 (domain ~$12, Keepa free tier or ~€19/mo later, phone
camera you already own). Anyone selling you more setup than this is the
product.

## 1. Pick the niche first — the account applications depend on it

Score 3–5 candidate niches with this gate. A niche must pass ALL of these,
not most:

- [ ] **You own or use ≥10 products in it already** (Influencer onsite videos
      require products in hand; buying inventory to review inverts the
      economics on day one)
- [ ] **Purchase-intent search demand exists**: type "best <niche thing>"
      into Amazon's own search bar and YouTube — do autocomplete suggestions
      appear? No suggestions = no demand
- [ ] **Typical price $25–$150.** Below $25 the commission is pocket lint;
      above $150 buyers research for weeks and your 24-hour cookie dies first
- [ ] **Category commission ≥3%** on the current Commission Income Statement
      (check it — several categories were cut up to 50% in May 2026)
- [ ] **Demonstrable on camera in under 15 seconds** — a benefit you can
      show, not a spec you recite
- [ ] **Boring beats trendy.** Garage storage, pool maintenance, CPAP
      accessories, RV parts — low creator competition, durable demand.
      Whatever is on #TikTokMadeMeBuyIt this week is saturated by the time
      you film it

The skeptical-buyer test that decides ties: would you send this product to a
friend with your own money on the line? Your credibility is the only moat in
this business; one junk recommendation spends it.

## 2. Accounts, in this order

1. **One social account with real activity** — TikTok, YouTube, or Instagram,
   public, posting consistently (3+/month minimum; weekly is safer). Amazon
   checks this for Influencer eligibility, and private or dormant accounts
   are declined. If starting from zero: post niche short-form for 4–8 weeks
   BEFORE applying. There is no official follower minimum, but approvals
   below ~1,000 engaged followers are rare in practice.
2. **Amazon Associates** (affiliate-program.amazon.com) — apply with your
   channel/site URL. You are provisionally approved; the account is only
   confirmed after **3 qualifying sales within 180 days**. Sales from paid
   or boosted ads do not count (April 2026 rule), and neither do your own
   purchases or purchases made on your behalf. Plan the first 3 sales as an
   explicit milestone, not an afterthought.
3. **Amazon Influencer Program** (amazon.com/influencer) — apply with the
   social account; approval gets you a storefront (amazon.com/shop/yourname)
   and a single link that holds. After 3 qualifying sales, request the
   **onsite placement review** — that's what puts your videos on product
   pages, and it is where the money in model 1 lives.
4. **A one-page site** (optional but cheap): home for your storefront link,
   your disclosure, and later your YouTube embeds. Do not put "amazon" or
   "amzn" in the domain — trademark violation, bannable.
5. **Keepa account** (keepa.com) — free tier for price-history charts and
   deal alerts; the paid tier adds the Product Finder used in `SOURCING.md`.
6. **PA-API 5.0** (later): Amazon's Product Advertising API unlocks after
   your first 3 qualifying sales. It is the only compliant way to display
   prices programmatically and the way to automate the daily pull. Signed
   requests are plain HMAC — stdlib-only automation is possible when the
   time comes.

## 3. Compliance — the traps that get accounts closed

Amazon terminates first and answers support tickets never. Accumulated
commissions can be forfeit. These are the rules operators actually trip on:

- **No affiliate links in email. None.** Also no PDFs, eBooks, or anything
  offline. This single rule shapes strategy: it's why deal distribution runs
  on Telegram/Discord/broadcast channels and why your newsletter links to
  your site, which links to Amazon.
- **Disclosure is mandatory twice over.** Amazon requires the exact phrase
  "As an Amazon Associate I earn from qualifying purchases" on your site.
  The FTC separately requires a clear and conspicuous disclosure NEAR the
  links, before the reader acts — in the video description above the fold,
  said or shown in the video itself, in the pinned comment. "#ad" buried in
  hashtag soup does not meet the standard.
- **Never state a price in text or thumbnails.** Prices change hourly; a
  stale price is a violation. Only PA-API/SiteStripe-rendered dynamic prices
  are compliant. ("It was under $40 when I filmed this — link below for the
  current price" is the compliant phrasing.)
- **No link cloaking that hides the destination.** Pretty redirects on your
  own domain are tolerated only if it stays obvious the link goes to Amazon.
  When in doubt, use the raw `amzn.to` or tagged link.
- **No incentives to click or buy** ("support the channel by using my
  link" is over the line; "links in description" is fine), no claiming your
  own purchases, no bidding on Amazon trademark terms in search ads.
- **Don't fake deals.** Check Keepa's price history before calling anything
  a discount — "50% off" an inflated list price is the fastest way to burn
  the only asset you have (see step 1).

## 4. Production baseline

Phone camera, window light, and the product actually in your hands.
Onsite-style review videos have a proven skeleton — respect it, don't
reinvent it:

1. First 3 seconds: the product in use, mid-action, no intro.
2. The one problem it solves, stated as the buyer would phrase it.
3. Honest demo: what surprised you, what's worse than expected. One real
   flaw stated plainly outperforms ten superlatives — skeptical buyers can
   smell a shill, and Amazon's review team rejects pure hype for onsite.
4. Who it's for / who should skip it.
5. No outro. End on the last useful frame.

60–90 seconds. Batch-film 5–10 per session from the same setup. The long-form
YouTube version is the same material plus comparisons and 6-month-later
follow-ups.

## 5. Wire up the tracker

Copy `tracker-template.csv`, one row per published piece. Log clicks and
orders weekly from Associates Central reports. Convention (house rule):
blank means "not reported", 0 means "reported as none" — don't collapse
them, or every rate you compute drags down invisibly.
