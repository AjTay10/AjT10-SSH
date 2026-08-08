---
name: growth-loops
description: Design compounding growth loops instead of linear acquisition funnels, and instrument them so you can tell whether the loop actually closes. Use when the user asks how to grow, scale, get more users or followers, build a referral or viral mechanism, or reduce dependence on paid acquisition. Also use when growth is flat despite consistent effort, or when every new user requires the same effort as the last.
---

# Growth loops

A funnel is linear: effort in, users out, and next month you start over at
zero. A loop reinvests its output into its own input, so each turn makes the
next turn cheaper.

Almost all "we need to grow" problems are actually "we have a funnel and are
tired". The distinguishing question: **does today's user make tomorrow's user
cheaper to acquire?** If no, there is no loop, and more effort produces
proportionally more work forever.

## Anatomy

```
        ┌─────────────────────────────────────┐
        │                                     │
   new user ──▶ action ──▶ output ──▶ exposure ──▶ new user
        │                                     │
        └──────── the loop must close ────────┘
```

Four things to name, precisely:
1. **Trigger** — what makes an existing user act
2. **Action** — the specific thing they do
3. **Output** — what that produces, visible to others
4. **Exposure** — how a non-user encounters it

If any one is vague, the loop does not exist yet. "Users tell their friends"
is not an action; it is a hope. "Users share their result card because it
shows a number they are proud of" is an action with a mechanism.

## The four loop types

**Content loop.** Content → search or feed distribution → new audience → more
content (from demand signals) → more content.
*Closes when:* published content keeps working. Search-based content compounds;
feed-based content mostly does not — a TikTok is dead in 96 hours, a ranking
page works for years. This distinction determines whether you have a loop or a
treadmill.

**Viral loop.** User → invites or shares → new user → invites.
*Closes when:* k = invites sent × conversion rate > 1. In practice k > 1 is
rare and short-lived; a k of 0.4 is still enormously valuable because it cuts
effective acquisition cost by ~40%. Do not dismiss sub-1 loops.

**Paid loop.** Spend → user → revenue → more spend.
*Closes when:* LTV > CAC **and** payback is faster than your cash cycle. A
positive-LTV loop with a 14-month payback still kills you at month six.

**Product loop.** User → creates something → that thing attracts users →
those users create.
*Closes when:* the created artifact is publicly visible and valuable to
strangers. The strongest and slowest loop type.

## Instrument it or you do not have one

The most common failure is believing in a loop nobody measured. Three numbers,
non-negotiable:

```
k        outputs per user × conversion per output
cycle    time from new user to that user producing a new user
decay    how fast a unit of output stops producing exposure
```

**Cycle time matters as much as k and is almost always ignored.** A loop with
k = 0.5 and a 3-day cycle beats k = 0.9 with a 90-day cycle, decisively.
Halving cycle time is usually far easier than doubling k, and it is where the
leverage actually is.

**Decay determines whether the content loop is real.** Measure it directly:

```bash
python3 tools/metrics.py retention --csv events.csv --user user_id \
    --date date --period week --periods 12
python3 tools/metrics.py growth --csv daily.csv --date date --value signups
python3 tools/anomaly.py --csv daily.csv --date date --value signups --seasonal weekly
```

Retention flattening to a plateau means a core exists and the loop has
something to reinvest. Retention decaying to zero means every acquired user
is spent, and no loop can be built on top of it — fix retention first, always.

## Fix the leak before adding the loop

A loop built on a leaky product amplifies the leak. Order of work:

1. **Retention plateau exists?** If the curve goes to zero, stop. Nothing else
   matters and no growth tactic survives it.
2. **Is there a moment users would want to share?** If not, manufacture the
   *moment*, not the prompt. Asking harder does not work; giving people
   something worth sending does.
3. **Is the output visible to non-users?** A share that lands behind a login
   is not exposure.
4. **Only then optimize k.**

Most growth work happens at step 4 while step 1 is broken. That is why it
does not work.

## Why loops decay — plan for it

Every loop decays, and expecting otherwise is how teams get blindsided:

- **Saturation.** Early adopters share; the mainstream does not. k falls as
  you penetrate the market, and it falls exactly when leadership expects
  acceleration.
- **Channel closure.** Platforms shut down the exposure mechanism once it
  becomes noticeable. This has happened to every large viral loop eventually.
- **Novelty exhaustion.** The share becomes ordinary and stops earning
  attention.
- **Competitive copying.** The mechanism gets copied, splitting the same
  attention.

Treat a working loop as a depreciating asset. Have the next one in
development while the current one is at its peak, not after it declines.

## Second-order check — mandatory

Loops optimize hard for their own metric, which makes them the highest-risk
place for unintended consequences. Run `second-order` on any loop before
launching:

- A referral loop rewarded per signup imports users who wanted the reward,
  and they retain worse than organic — improving the growth number while
  degrading the business.
- A content loop rewarded per post degrades quality per post, which degrades
  distribution per post, which can make total reach *fall* while output rises.
- A viral loop with an aggressive share prompt trades long-term trust for
  short-term k, and trust does not come back.

## Honest expectations

- Most loops have k well under 1. That is fine and still worth building.
- A loop takes several cycles to be measurable. With a 30-day cycle, that is
  a quarter before you know anything.
- The loop that works is usually specific to your product and not on any
  list of tactics.
- Some businesses genuinely have no loop available. Saying so is more useful
  than manufacturing a fake one, which costs a quarter and teaches nothing.

## Related

- `second-order` — mandatory before launching any loop
- `metrics-lab` — measuring retention and cycle time
- `falsify-first` — testing loop mechanics cheaply before building them
