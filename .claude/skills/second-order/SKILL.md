---
name: second-order
description: Trace the downstream consequences of a decision — and then what happens, and then what. Use when evaluating a policy, incentive, pricing change, metric, growth tactic, automation, or any decision whose obvious first effect is good. Especially use when a proposal sounds unambiguously positive, when setting a KPI or bonus, or when the user asks about unintended consequences, side effects, or long-term impact.
---

# Second-order thinking

First-order effects are the ones you intended and the ones everyone discusses.
Second- and third-order effects are the ones that determine whether the
decision was actually good — and they arrive later, attributed to something
else, usually after the decision is irreversible.

The method is embarrassingly simple and almost never done: ask *and then what?*
three times, and follow each branch even when it becomes uncomfortable.

## Procedure

**1. State the first-order effect.** The intended one. One sentence.

**2. Ask "and then what?" for each affected party — separately.** Effects
diverge by actor, and aggregating them hides the problem. Enumerate: users,
non-users, employees, competitors, the platform/algorithm, and the person
whose job the metric now measures.

**3. Go three rounds.** Second order is usually where the cost lives. Third
order is where the irreversible damage lives.

**4. Mark reversibility on every node.** A bad reversible effect is a cost.
A bad irreversible effect is a different category of decision entirely and
should be flagged in those terms.

## Worked example

Decision: pay the content team a bonus per published post.

```
1st  Output rises. 3 posts/week → 9. Intended, measurable, celebrated.

2nd  · Team optimizes for post count. Long-form research pieces disappear
       because they cost 4x a quick take. [reversible in ~1 quarter]
     · Feed frequency rises; per-post reach falls as the audience's
       attention is finite. Total reach roughly flat. [reversible]
     · The best writer, who wrote the pieces that built the brand, is now
       the lowest-paid on the team. [reversible, but they may leave first]

3rd  · Audience recalibrates: the account is now a volume feed, not a source.
       Open rate decays. The reputation that made the long pieces work is
       spent. [SLOW TO REVERSE — 12+ months]
     · Competitors' long-form now owns the authority position by default.
       [may be irreversible; positions are hard to reclaim]
     · The metric "posts/week" is now defended internally by everyone paid
       on it. Changing it is a political fight, not an analysis.
       [ORGANIZATIONALLY IRREVERSIBLE — this is the real cost]

Net: the first-order gain is real and small. The third-order loss is large,
slow, and structurally hard to undo. The decision is worse than doing nothing.
Fix: pay on a quality-weighted outcome, or cap volume and pay on reach per post.
```

That third-order political entrenchment is the effect people never model and
which most often makes a decision permanent.

## Patterns that reliably produce bad second-order effects

- **Any metric attached to compensation.** Goodhart's law is not a tendency,
  it is a schedule. Name how it will be gamed, in the first meeting.
- **Removing friction that was doing a job.** Some friction filters. Removing
  signup friction raises signups and lowers cohort quality — the number goes
  up and the business goes down.
- **Subsidizing a behavior.** You get more of it, including from people who
  were not the target and who arrive with different intent.
- **Automating a judgment call.** The automation handles the 90% and fails
  invisibly on the 10%, which is exactly where judgment was the value.
- **Optimizing one side of a two-sided system.** Feeding creators degrades
  the consumer feed; feeding consumers starves creators.
- **Winning attention with an escalation.** Louder thumbnails, bigger claims,
  more frequent notifications. Competitors escalate too; you end up at higher
  intensity and identical share, having spent the credibility.

## Where to stop

Three rounds, or when effects become genuinely unknowable — say which it is.
Speculating to round five produces confident nonsense; stopping at round one
produces confident mistakes. If a branch is unknowable, that is a finding:
it means the decision should be made reversible rather than analyzed harder.

## Output

The tree, reversibility marked, and one line naming the effect most likely
to be missed by the people making this decision. Close with the specific
modification that keeps the first-order gain while defusing the worst branch —
usually there is one, and it is usually small.

## Related

- `pre-mortem` — when you want failure modes rather than consequence chains
- `growth-loops` — for the two-sided-system version of this analysis
