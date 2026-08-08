---
name: brand-voice
description: Extract a voice guide from existing writing and enforce it across new content, or diagnose why copy sounds generic or AI-written. Use when the user asks for help with tone of voice, brand voice, making content sound like them, editing to match a style, or says their content sounds bland, corporate, or AI-generated. Also use before producing content at volume, so it does not all drift to the same average.
---

# Brand voice

Voice is not adjectives. "Friendly, professional, approachable" describes
almost every brand and constrains nothing — it is unfalsifiable and therefore
useless as a guide.

A real voice guide is a set of **decisions**: specific words used and banned,
sentence structures preferred, positions taken, and things this voice will
never say. It should be possible to fail it.

## Extracting a voice from existing writing

Take 10–20 samples the user considers *most like them* — not their best
performing, not their most polished. Then extract mechanically:

**1. Sentence rhythm.** Measure it, do not describe it. Average length,
variance, and how often a sentence runs under five words. Short-sentence
frequency is the single most distinguishing rhythmic feature and it is easy
to count.

**2. Vocabulary fingerprint.** Words used far more often than baseline, and
words conspicuously absent. Every real voice has both.

**3. Structural habits.** Does it open with a claim or with context? Use
questions? Second person? Lists or prose? Where does the point land — first
sentence or last?

**4. Positions.** What does this voice reliably assert or reject? A voice
without positions is a template. This is usually the part that makes writing
sound like a specific person rather than a category.

**5. Humor and register.** Present or absent; dry, warm, absurd. Absent is a
legitimate and often correct answer — forced humor is worse than none.

**6. What it refuses.** The banned list is more useful than the preferred
list, because it is enforceable.

Quick mechanical pass:

```python
import re, collections
text = open("samples.txt", encoding="utf-8").read()
sents = [s for s in re.split(r"[.!?]+", text) if s.strip()]
lens = [len(s.split()) for s in sents]
print(f"avg {sum(lens)/len(lens):.1f} words, "
      f"min {min(lens)}, max {max(lens)}, "
      f"short(<5w) {sum(1 for l in lens if l<5)/len(lens):.0%}")
words = re.findall(r"[a-z']+", text.lower())
print(collections.Counter(words).most_common(40))
```

## The guide format

```markdown
# Voice

## Sentence
Average 14 words. High variance. About 1 in 6 sentences under 5 words.
Fragments allowed. Never two long sentences in a row.

## Always
- Second person, present tense
- The specific number over the rounded one — "$4,270" not "about $4k"
- Name the thing: "Instagram" not "the platform", "editing" not "post-production"
- Concede the counterargument before making the point

## Never
- "Delve", "leverage", "unlock", "seamless", "game-changer", "in today's
  landscape", "it's important to note", "let's dive in"
- Rhetorical question as an opener
- Three-item lists where two would do (the third is almost always filler)
- Em-dash-heavy construction stacked in one paragraph
- Exclamation marks (max one per piece, and it should feel earned)
- "We're excited to announce"

## Positions
- Consistency beats intensity
- Most tools are not the bottleneck
- Say the number or do not make the claim

## Opening pattern
Claim first, context second. Never warm up.

## Test
If a competitor could publish this sentence unchanged, rewrite it.
```

That last test is the most useful line in the document.

## The AI-generated tell

If content sounds "bland" or "AI-written", it is usually these, in order:

1. **Uniform sentence length.** Real writing varies violently. This is the
   strongest single tell.
2. **Balanced structure everywhere.** Every section the same length, every
   list exactly three items.
3. **Hedged into meaninglessness.** "Can be a powerful tool for many
   businesses" asserts nothing and cannot be wrong.
4. **No specifics.** No names, no numbers, no dates, no dollar amounts.
5. **Symmetric both-sides framing** on questions where the writer actually
   has a view.
6. **Transitional throat-clearing.** "It's worth noting", "that said",
   "ultimately", "in conclusion".
7. **No failures.** Real experience includes something that did not work.

The fix for all seven is the same: **add specifics and take a position.**
One real number, one real name, one thing you actually think. Everything else
follows from that.

## Enforcing at volume

- Run the banned-word list as a literal grep before publishing.
- Read it aloud. Anything you would not say aloud, cut.
- Check the opening sentence against the opening pattern — drift starts there.
- Spot-check one in five pieces fully rather than skimming all of them.

```bash
grep -n -iE "delve|leverage|unlock|seamless|game.chang|in today's|it's important to note|let's dive|we're excited to announce" draft.md
```

## Voice versus platform

Voice stays constant; register adapts. LinkedIn is more formal than TikTok,
and the same voice can be both — the vocabulary and structure hold while the
length and formality shift. If the voice has to change entirely to work on a
platform, that is real information: it may not be your platform.

## When not to have a strong voice

Documentation, error messages, legal and safety copy, and anything where the
reader is stressed or in a hurry. Personality there is friction. Clarity is
the voice.

## Related

- `hook-craft` — openings must still sound like you
- `content-atomizer` — voice drift shows up fastest at volume
- `comment-ops` — replies are where voice is most visible and least managed
