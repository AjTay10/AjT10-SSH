# Daily product sourcing — where products come from, every day

The pipeline answers one question each morning: *what do I publish today?*
It pulls candidates from live demand signals, filters them through a
skeptical-buyer gate, and leaves you with 1–3 products worth an hour of
production. Time box: 30–45 minutes. If sourcing takes longer than
production, you're browsing, not operating.

## The pull list (bookmark all of these)

**Amazon's own surfaces — the primary source, free, updated continuously:**

| Surface | URL pattern | What it tells you |
|---|---|---|
| Movers & Shakers | `amazon.com/gp/movers-and-shakers/<category>` | Biggest sales-rank gainers in 24h, updated hourly — demand spiking NOW |
| Best Sellers | `amazon.com/gp/bestsellers/<category>` | Proven perennial demand; your evergreen review backlog |
| Hot New Releases | `amazon.com/gp/new-releases/<category>` | New ASINs with few or no review videos yet — the onsite land-grab |
| Today's Deals | `amazon.com/gp/goldbox` | Real time-boxed discounts; fuel for deal-channel posts |
| Your niche's search bar | autocomplete on "best …", "… for …" | The exact phrasings buyers use — these become video titles |

Drill every one of these into your niche's category, not the homepage.
Homepage lists are dominated by electronics and viral junk with commission
rates of 1–2.5% and a thousand competing videos.

**Price-drop data (feeds the deal channel and keeps you honest):**

- **Keepa** — set deal alerts for your niche: price drop ≥20% vs 90-day
  average, rating ≥4.3, review count ≥500. The paid Product Finder can run
  this as a stored daily query. Also your fact-checker: never call something
  a deal without looking at its price-history chart.
- **CamelCamelCamel** — free second opinion on price history.

**Off-Amazon demand signals (weekly, not daily — they find the niche's next
wave before the Amazon rank moves):**

- **Google Trends** — rising queries containing your niche terms; "breakout"
  labels are early demand.
- **Reddit** — your niche's subreddits plus r/BuyItForLife: threads asking
  "what should I buy for X" are videos waiting to be filmed, in the buyer's
  own words.
- **TikTok/Shorts search** for your niche — note which products have
  momentum but no *good* review (comments full of unanswered questions =
  your angle).
- **Seasonality** — work 4–6 weeks ahead of Q4, Prime Day(s), back-to-school,
  Mother's/Father's Day. Rank lists lag the season; the calendar doesn't.

**Automation (once unlocked):** after your first 3 qualifying sales, PA-API
5.0 can pull `SearchItems` for your niche daily and diff against yesterday —
new entrants and rank jumps land in a CSV before you've had coffee. Until
then, the manual pull is genuinely 15 minutes.

## The filter — 20 candidates in, 3 survivors out

Score each candidate. Reject on any hard fail:

| Gate | Pass | Hard fail |
|---|---|---|
| Price | $25–$150 | under $15 (commission ≈ $0.50) |
| Rating | ≥4.3 with recent reviews still ≥4★ | ≥4.5 overall but recent reviews cratering — dying product |
| Review velocity | reviews growing month over month | flat for a year (unless evergreen best-seller) |
| Commission category | ≥3% on current rate card | 0–1% categories |
| Demonstrability | benefit visible on camera in 15s | spec-sheet products (RAM, thread count) |
| Competition | few/no onsite videos, weak YouTube results | 40 polished reviews already live |
| Your edge | you own it or can say something a listing can't | you'd be narrating the bullet points |
| Deal honesty (deal posts only) | Keepa confirms real drop vs 90-day avg | discount off inflated list price |

Two deliberate biases, both contrarian on purpose: prefer the **boring
best-seller with no good video** over the trending product with twenty; and
prefer **Hot New Releases in a niche you know** over anything on the
homepage. Everyone fights over the spike; the compounding money is in
unsexy items that sell every day and had no decent review until yours.

## The daily SOP

1. **(10 min)** Sweep Movers & Shakers + Hot New Releases + Keepa alerts in
   your niche. Collect ~20 candidates into the tracker with `status=candidate`.
2. **(10 min)** Run the filter. Kill to 3. Log the kills too — `status=rejected`
   with the reason; rejection patterns are how the filter gets sharper.
3. **(20 min)** For the survivors: read the 3-star reviews (that's where the
   truth lives and where your video's honest-flaw beat comes from), note the
   buyer's phrasing for the title, check who else has covered it.
4. Hand off to production: film/publish 1–2, queue the rest.
5. **Weekly, not daily:** pull clicks/orders from Associates Central into
   the tracker and re-read it. Double down on what earns, not on what was
   fun to make.

## Related repo machinery

- `tools/anomaly.py` — run over your weekly clicks column to tell a real
  break from noise before "fixing" a strategy that isn't broken.
- `tools/concentration.py` — monthly: what share of commissions comes from
  the top 1–3 products? A total resting on one ASIN is fragility, and ASINs
  die (stock-outs, listing changes, competitors).
- `tools/metrics.py` — funnel from published → clicks → orders once the
  tracker has a few weeks of rows.
- The `base-rates`, `red-team`, and `decision-log` skills apply before any
  scale-up decision.
