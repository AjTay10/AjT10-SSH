---
name: decision-log
description: Record a decision with its reasoning, alternatives, confidence, and kill criteria so it can be reviewed honestly later. Use when the user makes a significant or hard-to-reverse choice, asks to "document this decision", wants an ADR, is choosing between options, or is about to commit budget or direction. Also use after any strategy discussion concludes, and to review past decisions against what actually happened.
---

# Decision log

Memory rewrites itself. Six months on, everyone remembers predicting the
outcome that occurred, and the reasoning that produced the decision is gone —
so the same mistake is available to be made again. A written decision, with
a confidence number attached before the outcome is known, is the only defense.

Store at `.claude/data/decisions/NNNN-slug.md`. Numbered, never deleted,
never edited except to append the review.

## Template

```markdown
# 0007 — Move the newsletter off Substack

- Date: 2026-03-14
- Status: accepted            # proposed | accepted | superseded by NNNN | reversed
- Reversible: partially — subscribers export, but the archive URLs break
- Decider: AJ

## Context
What is true right now that forces a choice. Facts and numbers, not
justification. If nothing has changed, there is no decision to make — say so
and stop.

## Options considered
| Option | Upside | Downside | Est. cost |
|---|---|---|---|
| Stay on Substack | zero work, network discovery | 10% rev share, no list control | $0 |
| Self-host (Ghost) | own the list, better margin | ops burden, lose discovery | ~$25/mo + 2 days |
| Beehiiv | middle ground | another platform to be locked into | ~$40/mo |

Every option a reasonable person would raise gets a row, including the one
being rejected. An options table with one real entry is a rationalization.

## Decision
Move to self-hosted Ghost.

## Reasoning
The actual reason, including the unflattering part. "Substack discovery has
never delivered more than 4% of signups for us, so we are paying 10% for a
channel we do not use."

## Confidence
65% this is right at the 12-month mark.

Write the number before the outcome. It is the single most valuable line in
the document, because it is the only one you can score later.

## What would change my mind
- Substack discovery exceeding 15% of new signups for two consecutive months
- Migration taking longer than 5 days of real work

## Kill criteria
If open rate drops more than 15% and has not recovered within 60 days of
migration, move back. Decided in advance, in numbers, before I am emotionally
invested in the migration having been correct.

## Review — 2026-09-14        # appended at the review date, never before
What actually happened. Was the reasoning right, or the outcome merely lucky?
Which specific input was wrong? Do not grade the outcome — grade the process.
```

## Rules that make this work

**Confidence before outcome, always.** A decision log without a pre-committed
confidence number cannot be scored, and an unscoreable log is a diary.

**Record the ones you got right, too.** A log containing only failures teaches
loss aversion, not calibration.

**Separate a good decision from a good outcome.** These are different axes and
conflating them is how teams learn superstition. Score all four cases:

|  | Good outcome | Bad outcome |
|---|---|---|
| **Good process** | deserved | bad luck — do not change the process |
| **Bad process** | lucky — this is the dangerous one | deserved |

The top-right and bottom-left cells are where all the learning is. The lucky
win is the most expensive box on this grid, because it gets promoted into
policy.

**Set the review date at write time.** An unscheduled review does not happen.

## Calibration review

When several decisions have been reviewed, check calibration across them:
of everything logged at ~70% confidence, roughly 70% should have worked out.
Systematically over 70% means you are underconfident and passing on good bets.
Systematically under means overconfident — and the fix is not "try harder",
it is to lower every stated number by the observed gap.

## Commands

```bash
ls .claude/data/decisions/                     # what has been decided
grep -l "Status: accepted" .claude/data/decisions/*.md
grep -A2 "^## Confidence" .claude/data/decisions/*.md   # calibration sweep
grep -L "^## Review" .claude/data/decisions/*.md        # never reviewed
```

That last one — decisions never reviewed — is usually the longest list, and
working through it is the highest-value hour in this whole skill.

## Related

- `pre-mortem` — generates the kill criteria this document records
- `base-rates` — to set the confidence number honestly
