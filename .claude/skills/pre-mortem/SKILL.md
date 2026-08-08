---
name: pre-mortem
description: Run a pre-mortem — imagine the project already failed, then work backwards to the causes and the early-warning signals. Use when a plan is already chosen and the user wants risk analysis, contingency planning, "what would kill this", failure modes, or a launch readiness check. Different from red-team — this assumes failure as fact rather than arguing about whether it will happen.
---

# Pre-mortem

Prospective hindsight. People generate roughly 30% more, and far more
specific, causes when told a failure *already happened* versus asked whether
one *might*. The trick works because it removes the social cost of predicting
failure — you are no longer the pessimist, you are the historian.

## Procedure

**Step 1 — Set the scene concretely.** Not "the project failed" but:

> It is [specific date, 6–12 months out]. The project shipped. It is now
> unambiguously considered a failure inside the company. The postmortem
> meeting is tomorrow.

Pick the date and write the failure in past tense. Vagueness here produces
vague causes.

**Step 2 — Write the obituary.** Two paragraphs, past tense, as a colleague
who was there. What went wrong, in what order, and what everyone said
afterward. Write it before you analyze — narrative surfaces causes that
checklists miss.

**Step 3 — Extract causes into three buckets.**

| Bucket | Question | Example |
|---|---|---|
| **We knew** | What was visible on day one and got deprioritized? | "We knew the API rate limit was 100/min" |
| **We could have known** | What was findable but nobody looked? | "Three competitors had already tried this" |
| **Nobody could know** | Genuine uncertainty | "The platform changed its algorithm" |

The first bucket is negligence and is fixable today. The second is a research
task, usually under two hours. The third is what contingency budget is *for* —
if bucket three is empty, you are not being honest; if it is the biggest,
you are using it as an excuse.

**Step 4 — Find the tripwire for each cause.** For every cause in buckets one
and two, name the earliest observable signal and the threshold:

```
CAUSE            EARLIEST SIGNAL                  THRESHOLD        CHECK WHEN
Retention dies   D7 retention on first cohort     < 22%            day 14
Platform ban     reach drops with no content chg  −40% for 3 days  daily
Cost overrun     spend per acquisition            > $18            weekly
```

A cause without a tripwire is a worry. A cause with a tripwire is a plan.

**Step 5 — Set kill criteria.** The single most valuable output. Write, in
advance and in numbers, the condition under which you stop. Pre-committing
is the whole point: after money is spent, every number gets reinterpreted
as encouraging.

> "If D7 retention is under 18% on two consecutive cohorts, we stop and
> reallocate. Not 'reassess' — stop."

## Anti-patterns

- **Causes that are just the outcome restated.** "It failed because users
  didn't like it" is not a cause. Keep asking why until you hit something you
  could act on this week.
- **Only external causes.** If every cause is a competitor, a platform, or the
  market, the exercise was performed defensively and is worthless. At least
  half should be things the team controls.
- **Tripwires nobody owns or checks.** Assign a name and a date, or delete it.

## Output

The obituary, the three-bucket table, the tripwire table, and the kill
criteria. Lead with kill criteria if the user is about to commit spend.

## Related

- `red-team` — when the plan is still up for debate
- `decision-log` — to record the kill criteria where they will be found later
- `second-order` — when the failure comes from a downstream consequence
