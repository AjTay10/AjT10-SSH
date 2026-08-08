---
name: deep-research
description: Run structured multi-source research that tracks source quality, hunts for disconfirming evidence, and separates fact from inference. Use when the user asks to research, investigate, "find out about", "look into", compare options, do a deep dive, or produce a briefing or literature review. Also use whenever an answer will be acted on and being wrong would be expensive.
---

# Deep research

Ordinary research finds what you expected. This process is built to notice
when the expectation was wrong, and to make the reader able to check you.

## The loop

**1. Convert the question into decisions.** What will change based on the
answer? Research that cannot change an action is trivia. Write the decisions
first; they set the required confidence and the stopping point.

**2. Write your prior.** Before searching: what do you currently believe and
how confident are you? One line. Everything after is compared against it, and
if nothing moved, that is itself worth reporting.

**3. Search across modes, not just more queries.** Running five variations of
one query returns five copies of the same document set. Vary the *mode*:

- Direct terms — what the thing is called
- Insider terms — what practitioners call it, which is different
- The opposition — "X is overrated", "why we stopped using X", "X failure"
- Primary sources — filings, docs, changelogs, court records, datasets
- Adjacent fields that solved the same structural problem
- Time-shifted — how was this discussed 3 years ago, and what changed?

The opposition search is mandatory and it is the one people skip.

**4. Tier every source as you collect it.** Never mix tiers in a conclusion
without saying so.

| Tier | What | Weight |
|---|---|---|
| A | Primary: raw data, official docs, filings, direct measurement | decisive |
| B | Credentialed secondary: peer review, established outlets with a correction policy | strong |
| C | Practitioner report: case study, forum post from someone who did it | useful, unrepresentative |
| D | Content marketing, SEO listicles, AI-generated summary | evidence of what is *said*, not of what is true |

Tier D dominates search results on any commercial topic. Treat a wall of
agreeing tier-D pages as one weak source, not twenty strong ones: they all
copied each other.

**5. Keep a contradiction log.** Every disagreement between sources gets a row
rather than being silently averaged away. Contradictions are where the real
finding usually is.

```
CLAIM              SOURCE A SAYS   SOURCE B SAYS   WHO IS BETTER POSITIONED   RESOLUTION
API rate limit     100/min (docs)  20/min (forum)  docs, but dated 2024       tested: 20/min now
```

**6. Separate the three registers, visibly.** The single highest-value habit
in this skill:

- **Fact** — stated by a tier A/B source, cited
- **Inference** — your reasoning from facts, marked as yours
- **Speculation** — plausible, unsupported, labeled

Blending them produces confident-sounding work that cannot be audited. Keep
them in separate sentences and label the last two in-line.

**7. Actively seek disconfirmation.** Before writing: what is the strongest
evidence *against* the emerging conclusion, and did you look for it with the
same energy you spent supporting it? If the answer is no, go back to step 3.

**8. Stop deliberately.** Stop when new sources stop changing the answer
(saturation), or when remaining uncertainty no longer affects the decision.
Not when tired, and not when you have enough to sound authoritative.

## Output

```markdown
## Answer
Two or three sentences. The actual answer, up front.

## Confidence
Moderate. Rests on two tier-A sources that agree; the third contradicts and
I could not resolve it. See contradictions.

## What I found
Fact, inference, and speculation kept apart and labeled.

## Contradictions and what is still open
The rows that did not resolve, and what evidence would settle each.

## What would change this answer
Concrete and specific. "If the 2026 pricing page shows per-seat billing,
the cost conclusion reverses."

## Sources
Tier, link, date accessed, and one line on why this source is or is not
well positioned to know.
```

## Failure modes

- **Answering from memory.** Model knowledge has a cutoff and drifts on
  anything versioned, priced, or recently changed. Verify anything with a
  number, a date, a version, or a price.
- **Citation laundering.** Five blogs citing one another is one source.
  Follow every chain to its origin before counting it.
- **Recency blindness.** The top result is often the best-SEO'd, not the most
  current. Check dates and prefer the changelog to the article about it.
- **Fabricated specificity.** Never invent a statistic, study, or quote to
  fill a gap. "I could not find a reliable figure for this" is a finding and
  is always acceptable to write.
- **Confirmation stop.** Stopping at the first source that agrees with the
  prior. The step-7 check exists to catch this.

## Tools

Record entities and their relationships as you go — sources, claims, actors —
so the second research task on the same topic starts from the first:

```bash
python3 tools/kg.py add --id anthropic --type org --name "Anthropic"
python3 tools/kg.py link --from anthropic --to claude --rel builds
python3 tools/kg.py central --top 15      # who actually matters here
python3 tools/kg.py mermaid --focus anthropic --depth 2 > map.mmd
```

## Related

- `source-triage` — deeper credibility assessment of a single source
- `knowledge-graph` — for research that accumulates across sessions
- `base-rates` — when the question is "how often does this work"
