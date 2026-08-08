---
name: seo-aeo
description: Optimize content to be found by search engines and cited by AI answer engines — keyword and intent research, on-page structure, and the citation patterns that get content quoted by assistants. Use when the user asks about SEO, ranking in Google, being found in search, showing up in ChatGPT or AI answers, keyword research, or why their content gets no organic traffic. Also use when planning evergreen content.
---

# SEO and answer-engine optimization

Two audiences now: search engines that rank pages, and AI assistants that
synthesize an answer and cite a few sources. They reward overlapping but not
identical things, and the overlap is where evergreen content should live.

## The shift that matters

Search increasingly ends without a click — the answer is on the results page
or inside an assistant. That changes the goal:

- **Old goal:** rank #1, get the click.
- **Current goal:** be the source that gets *quoted*, and make the quote
  insufficient on its own.

Content that is a complete answer gets cited and not visited. Content that
answers the question *and* has an irreducible reason to visit — a tool, data,
a decision you have to make yourself — gets cited and visited. Build the
second.

## Intent before keywords

Volume is the wrong first question. Intent is:

| Intent | Query shape | What wins | Commercial value |
|---|---|---|---|
| Informational | "what is X", "how does X work" | Complete, structured answer | low, high volume |
| Comparative | "X vs Y", "best X for Y" | Honest table with a real recommendation | **highest** |
| Transactional | "buy X", "X pricing" | Clear pricing, no friction | high, low volume |
| Navigational | "X login" | You either are X or you are not | none |

**Comparative queries are the underpriced ones.** They have real commercial
intent, the existing results are usually vendor-written and useless, and
honest comparison is a genuine differentiator — see `competitor-recon` on why
a sponsored competitor structurally cannot write it.

## Finding the actual questions

Use the sources where people phrase questions in their own words, not the
ones that show you cleaned-up keyword strings:

- Autocomplete and "people also ask" — real phrasings
- Reddit and forum threads in the niche — the question *behind* the question,
  and Reddit ranks well and is heavily weighted by AI answer engines
- Your own comment section — proven demand from an assembled audience
- Support tickets and sales objections — the highest commercial intent
  questions that exist, and they are already written down
- The queries your existing content already gets impressions for but ranks
  poorly on — this is the fastest win available and almost nobody checks it

## On-page, in order of impact

1. **Answer in the first 100 words.** Directly, before context. This serves
   the impatient reader, the featured snippet, and the AI extractor
   simultaneously. Burying the answer under 600 words of preamble fails all
   three.
2. **One page, one question.** Pages covering five topics rank for none.
3. **Descriptive headings that are themselves questions** users ask. Nest
   them logically — the heading structure is the extraction map.
4. **Front-load specificity.** Numbers, dates, versions, named entities. This
   is what makes a passage quotable rather than paraphrasable.
5. **Structured data** where it applies — FAQ, HowTo, Product.
6. **Internal links** with descriptive anchors. Orphan pages do not rank.
7. **Freshness signals** where the topic is time-sensitive. State the review
   date visibly.

## Getting cited by AI assistants

Assistants extract self-contained factual passages. Optimize for extraction:

- **Write passages that stand alone.** A paragraph that requires the previous
  three to make sense will not be quoted. Each key claim should survive being
  lifted out.
- **State facts as complete sentences with their subject.** "The limit is
  100" is unusable; "TikTok's caption limit is 2,200 characters" is quotable.
- **Include the qualifier in the sentence.** Date, version, scope. Assistants
  favor passages that carry their own caveats because those are safer to cite.
- **Tables and definition lists extract cleanly.** Prose comparisons do not.
- **Be the primary source of something.** Original data, an original
  measurement, an original framework with a name. Synthesis of what everyone
  already says has no reason to be cited — the assistant already has it.
- **Consistency across the web** matters. If your claim about your own
  product differs across pages, none of them get trusted.

Being on Reddit, YouTube, and Wikipedia-adjacent sources matters more than it
used to, because those are weighted heavily in the sources assistants draw on.

## What does not work

- Keyword density and stuffing. Long solved, and now actively penalized.
- Publishing volume for its own sake. Thin pages drag down the whole domain.
- AI-generated bulk content with no primary input. It averages what already
  exists, which is precisely what does not earn a citation.
- Exact-match domains, link buying, and the rest of the 2012 playbook.
- Chasing high-volume head terms with no authority. Rank for the specific
  question you can genuinely answer best; volume follows authority, not the
  reverse.

## Measuring

Track impressions and average position, not just clicks — impressions rising
with flat clicks means you are being surfaced and not chosen, which is a
title and description problem, not a ranking one.

Also track, manually and periodically: does asking an assistant the target
question surface you? There is no dashboard for this yet. Ask it and look.

```bash
python3 tools/anomaly.py --csv gsc.csv --date date --value clicks --seasonal weekly
```

Organic traffic moves in steps, not smoothly — algorithm updates and indexing
create real changepoints. `anomaly-watch` separates those from noise.

## Time horizon

SEO compounds and is slow: three to six months before a new page's position
stabilizes. Any promise of fast organic results is either paid traffic
relabeled or a technique that will be penalized. Budget accordingly, and do
not judge a page before it has been indexed and settled.

## Related

- `deep-research` — for the primary material worth citing
- `competitor-recon` — finding the queries answered badly by everyone
- `platform-playbooks` — Pinterest and Reddit as search surfaces
