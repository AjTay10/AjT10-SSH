---
name: compliance-guard
description: Check content and tactics against disclosure rules, platform terms, and rights obligations before publishing — sponsored content labeling, AI disclosure, testimonials, music and image licensing, data scraping, and privacy. Use when the user plans sponsored or affiliate content, uses someone else's music, images, or footage, wants to collect data from a platform, runs a giveaway, or makes performance or health claims. Also use as a pre-publish check on anything commercial.
---

# Compliance guard

This is a practical checklist, not legal advice. Rules vary by jurisdiction
and change; anything with real exposure needs a lawyer. What this does is
catch the routine failures that are entirely avoidable and that account for
almost all enforcement actions against creators and small brands.

## Disclosure — sponsored, affiliate, gifted

The rule everywhere, in substance: a material connection between the endorser
and the seller must be disclosed **clearly and conspicuously**, close to the
claim, and understandable to an ordinary viewer.

Material connection includes: payment, free products, discounts, affiliate
commission, employment, family relationship, or an equity stake. Being given
something free counts even with no other agreement, and this is the most
commonly missed case.

**What fails, reliably:**
- Disclosure only in a description that requires expanding
- Disclosure at the end of a video
- `#ad` buried in a block of thirty hashtags
- Only a platform's built-in "paid partnership" toggle, with nothing in the
  content itself — regulators have said explicitly this is insufficient alone
- "Thanks to [brand] for making this possible" — ambiguous, not a disclosure
- "sp", "spon", "collab", "amb", or any abbreviation an ordinary person would
  not parse
- Disclosure in a language other than the content's language

**What works:** plain words, in the content, before or as the claim is made.
"This video is sponsored by X." "I get a commission if you buy through this
link." Say it in the audio *and* put it on screen for video. Put it in the
first line for text, above the fold.

**Affiliate links** need disclosure every time, including in comments, replies,
DMs, and bios.

**Your own product** still needs it if the connection is not obvious from
context.

## AI disclosure

Rapidly hardening across jurisdictions and platforms, and diverging:

- **Platforms** — most major platforms require labeling realistic AI-generated
  or AI-altered media, and apply automatic labels via content credentials.
  Removing or evading a label is itself a violation.
- **EU** — the AI Act imposes transparency obligations on synthetic media,
  including deepfakes.
- **Several jurisdictions** require disclosure in political and election
  advertising specifically, with real penalties.

Practical rule: **if a reasonable person could mistake it for a real
recording of real people or events, label it.** AI-assisted writing or
editing generally does not require labeling; synthetic likeness, voice, or
photorealistic imagery generally does.

Never synthesize a real person's voice or likeness without written
permission. This is the fastest route to genuine legal exposure in this
entire document, and it is increasingly criminal rather than merely civil.

## Testimonials and claims

- Testimonials must reflect **typical** results, or the atypical nature must
  be disclosed prominently. "Results not typical" in small print does not
  cure a headline that implies typicality.
- Never fabricate a review, a testimonial, a case study, or a screenshot of
  results. Fake reviews now carry direct civil penalties in multiple
  jurisdictions.
- Do not suppress negative reviews you solicited. Selective publication is
  treated as deception.
- **Health, financial, and earnings claims** are the highest-risk categories
  and are enforced most aggressively. "Cures", "guaranteed returns", and
  income claims without substantiation attract regulators regardless of
  audience size.
- Substantiation must exist **before** publishing, not after a complaint.

## Music, images, and footage

- **A platform's audio library licenses that platform only.** Using a TikTok
  trending sound in a video you reupload elsewhere is unlicensed there.
- **Commercial use is a separate license** from personal use in most
  libraries. A brand account is commercial use, including when the post is
  not an ad.
- **"No copyright" and "royalty free" are marketing terms**, not legal
  categories. Read the actual license.
- **Fair use / fair dealing is a defense, not a permission**, decided case by
  case after you are already in a dispute. Commentary and criticism have the
  strongest position; "I added my own edit" and "I credited them" have none.
- **Credit is not a license.** Attribution satisfies some Creative Commons
  terms and nothing else.
- **Stock licenses usually exclude** use in a logo, on merchandise, or in a
  way implying endorsement by a depicted person.
- **Recognizable people** in footage need a release for commercial use in
  most jurisdictions, regardless of where it was filmed.

## Scraping and data

- Automated collection against a platform's terms is a terms violation and,
  depending on jurisdiction and method, potentially more. Being technically
  possible is not permission.
- Personal data of EU/UK residents falls under GDPR **even when publicly
  posted**. Public does not mean unregulated.
- Do not build a dataset of individuals' posts, follower lists, or contact
  details without a lawful basis. "It was public" is not one.
- For competitive research, manual review of public content is legal,
  sufficient, and does not create this exposure. See `competitor-recon`.

## Giveaways and contests

Materially regulated, and routinely done wrong:
- Requiring purchase generally converts a sweepstakes into an illegal
  lottery. A free entry route is usually mandatory.
- Official rules, eligibility, odds, and end date must be stated.
- Excluded jurisdictions must be named. Rules differ sharply by country and
  by US state.
- Platform-specific promotion rules apply on top, and typically require
  stating that the platform does not sponsor or endorse the promotion.
- "Tag three friends to enter" violates several platforms' promotion policies.

## Minors, privacy, and consent

- Children's data is separately and strictly regulated nearly everywhere.
- Filming identifiable minors for commercial content needs guardian consent.
- Recording consent laws vary; some jurisdictions require all parties to
  consent to a recorded call.
- Do not publish anyone's private contact details, location, or workplace,
  including a critic's. This is a bright line, and platform enforcement of it
  is immediate and permanent.

## Platform terms — the ones actually enforced

- Engagement pods, bought followers, and bought engagement violate every
  major platform's terms and are detected.
- Multiple accounts to evade a restriction is ban evasion; it converts a
  temporary limit into a permanent one.
- Reposting others' content without permission or transformation triggers
  both platform enforcement and copyright claims.
- Automation of posting is usually allowed via official APIs; automation of
  engagement is usually not.

**Enforcement is uneven, retroactive, and unappealable in practice.**
Compliance with the letter of a policy is not protection. Keep an export of
content and audience, and assume any account can be lost without warning.

## Pre-publish check

```
[ ] Material connection disclosed, in-content, before the claim?
[ ] Every claim substantiated, with the substantiation held now?
[ ] Music and footage licensed for this platform and this commercial use?
[ ] Recognizable people released?
[ ] Synthetic media labeled if realistic?
[ ] Giveaway has free entry, rules, eligibility, and platform disclaimer?
[ ] No personal data of third parties?
[ ] Nothing that only works if the platform does not notice?
```

That last line catches most of what the others miss.

## Related

- `comment-ops` — disclosure applies in replies and DMs too
- `source-triage` — evaluating whether someone else's claims are substantiated
- `red-team` — before anything with real regulatory or reputational exposure
