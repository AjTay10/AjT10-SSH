---
name: competitor-recon
description: Analyze competitors, creators, or a whole niche from public information — what they do, what actually works for them, and where the gap is. Use when the user asks to analyze a competitor, study a creator, research a niche, find what is working in a space, or figure out how to differentiate. Also use before entering a new platform or market.
---

# Competitor recon

The goal is not to copy. Copying puts you second at someone else's game, on
their format, against their head start. The goal is to find the **gap** — what
the whole space is structurally unable or unwilling to do.

## Sourcing rules — read first

Use only what is publicly visible and accessible without circumvention:
published posts, public analytics, public pricing, public job listings, public
filings, archived pages.

Do not scrape in violation of a platform's terms, do not use fake accounts to
access non-public material, do not attempt to obtain private analytics, and
do not automate collection against a site that prohibits it. Manual review of
public content is both legal and sufficient — the analysis below needs
judgment, not volume, and volume is what creates the legal problem.

If a question genuinely requires non-public data, say so and stop.

## What to record, per competitor

Record it in the graph so it accumulates across sessions:

```bash
python3 tools/kg.py add --id competitor_x --type brand --name "Competitor X" \
    --attr platform=youtube --attr size=180k --attr posting=2x_week
python3 tools/kg.py link --from competitor_x --to teardown_format --rel uses \
    --note "every video is one teardown; consistent since 2024"
python3 tools/kg.py clusters      # who is actually doing the same thing
python3 tools/kg.py central --top 20
```

Per competitor:

| Field | Why it matters |
|---|---|
| Format and cadence | What they have committed to; hardest thing to change |
| Top 10 posts by engagement | What their audience rewards |
| Bottom posts | What they keep doing that does not work — the tell |
| Monetization | Determines what content they *cannot* make |
| Positioning claim | The sentence they repeat |
| Audience composition | Who actually responds, from public replies |
| Trajectory | Growing, plateaued, or coasting on an old peak |

## Read the pattern, not the posts

**Sort their content by engagement rate, not by likes.** Their biggest post is
usually an outlier or a collaboration. Their *consistent* performers show what
the audience reliably wants — that is the reproducible signal.

**Find what they stopped doing.** Scroll back 12–18 months. Formats they
abandoned were tested and failed, and you get that result for free. This is the
single most valuable and least-performed step in competitive analysis.

**Find what they repeat despite mediocre results.** Usually a strategic or
contractual commitment — a sponsor's requirement, a founder's preference, a
platform bet. It marks something they cannot stop doing, which means it is
territory they will keep occupying badly.

**Estimate the production cost of each format.** A format requiring a studio,
an editor, and three days is one you cannot compete with head-on, but it is
also one they cannot make more of. Their cost structure is their constraint.

**Check the comments, not the counts.** The questions their audience asks and
that they never answer are content you can make immediately, addressed to an
audience already assembled and already interested.

## Where the gaps are

Structural gaps, in rough order of how defensible they are:

1. **What their monetization forbids.** An account sponsored by a vendor
   cannot honestly evaluate that vendor's competitors. That review is yours,
   permanently, and they cannot respond.
2. **What their format cannot hold.** A 60-second account cannot do a nuanced
   argument. A studio account cannot do fast reactive coverage.
3. **What their scale prevents.** Large accounts cannot answer individual
   questions, cannot be specific to a narrow segment, cannot take a position
   that alienates 10% of a large audience. Small is a real advantage here and
   it is the one most often left unused.
4. **The audience they have outgrown.** Successful accounts drift upmarket and
   abandon beginners. That audience is large, underserved, and continuously
   replenished.
5. **The platform they neglect.** Everyone in a niche piles onto one platform.
   Check the search-based ones — Pinterest, Reddit, YouTube search — that
   nobody in the space bothers with.
6. **The question everyone answers badly.** Search the niche's core question
   and read the top ten results. If they are all vague, that is a gap with
   demand already proven.

## The teardown output

```
WHO            Competitor X — 180k YouTube, 2 videos/week, since 2023
FORMAT         Single-topic teardown, 12-18 min, studio, high production cost
WORKS          Teardowns of well-known products. Median 40k views.
               Consistent, not outlier-driven.
DOESN'T        Interviews (median 9k, still posts monthly — likely a
               relationship commitment they cannot drop)
ABANDONED      Shorts, stopped Q2 2025 after ~30 attempts. They tested it.
CONSTRAINT     Sponsored by [vendor]; has never covered [vendor]'s
               competitors and structurally cannot.
TRAJECTORY     Plateaued ~9 months. Views flat, upload rate flat.
AUDIENCE ASKS  "How do I do this myself" — asked constantly in comments,
               never answered. Their format cannot hold a tutorial.
GAP            (a) Honest comparison including [vendor] — they are barred.
               (b) The self-serve tutorial their audience keeps requesting.
               (c) Search-facing content; they publish nothing for search.
OUR MOVE       Tutorial series answering the comment question directly,
               optimized for search rather than browse. Low production cost,
               addresses proven demand, and sits where they cannot follow.
```

The last two lines are the deliverable. A teardown that stops at description
is a report; one that names the move is analysis.

## Guardrails

- **Do not benchmark against a different weight class.** An account 50x your
  size operates under different mechanics. Study accounts 2–5x your size —
  their recent history is your next 18 months and is actually transferable.
- **Follower counts are noisy and partly purchasable.** Engagement rate at a
  given size is far more informative.
- **You see their output, never their economics.** A channel with huge reach
  may be losing money; one with modest reach may be highly profitable. Do not
  infer success from visibility.
- **Survivorship.** You are studying the ones who are visible. The identical
  strategy failed for others you cannot see, so "they do X and are big" is
  weak evidence that X works.

## Related

- `knowledge-graph` — accumulating the map across sessions
- `contrarian-scan` — finding where the whole niche's consensus is wrong
- `source-triage` — before believing a competitor's published case study
