---
name: red-team
description: Attack a plan, claim, strategy, launch, or piece of content to find how it fails before reality does. Use when the user asks to "poke holes", "stress test", "what could go wrong", "play devil's advocate", "critique this", "review my strategy", or when they are about to commit to something expensive and irreversible. Also use unprompted before any launch, publish, migration, or public post that would be costly to retract.
---

# Red team

The job is not to be negative. It is to find the specific, mechanical way this
fails, early enough that finding it is cheap.

## Rule zero: steelman before you attack

Write the strongest version of the plan first, in the proponent's own terms,
including the best evidence for it. If you cannot state why a smart person
would do this, your critique will hit a strawman and get dismissed — correctly.

Only after the steelman is written do you attack.

## The five attacks

Run all five. Skipping one is how the miss happens.

**1. Mechanism attack.** For the plan to work, what has to be true? List each
assumption as a separate line. Mark each: *verified*, *assumed*, or *hoped*.
Anything in "hoped" that the whole plan rests on is the finding.

**2. Adversary attack.** Who is actively made worse off if this succeeds? A
competitor, a platform, a moderation team, an internal team losing budget,
a regulator. What is their cheapest counter-move? If a single person can
neutralize the plan in an afternoon, the plan is not a plan.

**3. Base-rate attack.** How often does this class of thing work? Not this
specific idea — the reference class. "New channel to 100k in 90 days",
"rebrand lifts conversion", "this feature drives retention". Compare the
plan's implicit success rate to the observed one. If the plan needs a p90
outcome to break even, say that in those words.

**4. Load attack.** What breaks at 10x? At 0.1x? Most plans are tuned for the
expected case and undefined at both edges. A campaign that works at 1000
comments/day may be unmoderatable at 50,000, and pointless at 12.

**5. Incentive attack.** Follow the money and the metric. If the plan makes
someone's number go up while the business's number goes down, it will be
gamed within one cycle. Name who games it and how.

## Output format

Findings only. No summary of what the plan is — the user wrote it.

```
SEVERITY  WHAT BREAKS                      TRIGGER                     COST IF IGNORED
critical  Assumption X is untested         first 500 users             rebuild, ~3 weeks
major     Competitor can copy in 2 days    they notice (~30 days)      margin gone
minor     Copy reads AI-generated          any reader                  trust, slow bleed
```

For every critical and major finding, give the **cheapest test that would
settle it** — ideally something doable today for under an hour. A criticism
without a disconfirming test attached is an opinion.

## Calibration

- Cap at 3 critical findings. More than three means you are pattern-matching,
  not analyzing. Rank and cut.
- Say explicitly what you *could not* attack for lack of information, and what
  you would need to see. Silence there reads as "no problems found".
- If the plan is genuinely sound, say so plainly and stop. Manufacturing a
  criticism to look rigorous is the failure mode of this skill. A short
  "the mechanism holds, the base rate supports it, here is the one thing I'd
  watch" is a complete and honest output.

## What this is not

Not a tone review, not a typo pass, not a list of everything that is merely
imperfect. Restrict findings to things that change a decision.

## Related

- `pre-mortem` — when the plan is already chosen and you need failure modes
- `falsify-first` — to design the cheapest test for a surviving assumption
- `base-rates` — when the argument turns on "how often does this work"
