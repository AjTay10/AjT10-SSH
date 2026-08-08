---
name: falsify-first
description: Design the cheapest test that could prove an idea wrong, and run that before building anything. Use when the user wants to validate an idea, is about to invest significant time or money, asks "should I build this", "how do I test this", "is this worth doing", or is planning a project whose core assumption has never been checked. Also use when a plan's success depends on an untested belief about users, platforms, or demand.
---

# Falsify first

Confirmation is cheap and almost worthless. You can always find a supporter,
a positive comment, a cherry-picked case. Disconfirmation is expensive to
obtain and enormously valuable, which is exactly why nobody looks for it.

The discipline: before building, write down what would prove you wrong, then
go looking for that specific thing.

## Procedure

**1. Extract the load-bearing belief.** Every plan rests on one assumption
that, if false, makes the rest pointless. Find it by asking: *if this one
thing turned out false, would we still do this?* Iterate until the answer is
a firm no. That is the load-bearing belief.

Most people test the second- or third-most important assumption because it is
the easiest one to test. Notice when you are doing this.

**2. Write it as a falsifiable claim.** With a number and a deadline.

- Bad: "people want this"
- Bad: "there is demand in the market"
- Good: "at least 8 of 40 people in [specific group] will give an email
  address for early access within 7 days"

If no observation could falsify the statement, it is not a belief about the
world, and no amount of building will resolve it.

**3. Design the cheapest disconfirming test.** Rank by cost, pick the cheapest
that could actually produce a *no*.

| Cost | Test | Good for |
|---|---|---|
| minutes | Search whether it already exists and failed | "nobody has done this" |
| an hour | Read 30 real complaints/reviews in the space | "users have this problem" |
| an hour | Post the hook alone; measure click-through | "this angle is interesting" |
| a day | Landing page + real traffic, measure signups | "people want this" |
| a day | Manually do the thing for 3 users, by hand | "this is valuable" |
| a week | Concierge version, no product, real money | "people will pay" |

The manual-by-hand test is the most underused item on this list. If doing it
by hand for three people is unbearable, automating it will not save the idea.

**4. Pre-commit to the threshold.** Before running, state the number that
means stop. Written down, in advance. Without this, every result gets
reinterpreted as encouraging, and the test becomes theatre.

> "If fewer than 8 of 40 sign up, I drop this and do not run a variant."

**5. Run it. Report the result as it landed.** Including the failures. A test
that killed a bad idea in a day is the highest-return work available.

## The tells that a test is fake

- It cannot produce a "no" — only degrees of yes
- The threshold was set after seeing the data
- It surveys intent instead of observing behavior ("would you use this?"
  is answered yes by everyone and predicts nothing)
- It samples friends, followers, or anyone who wants you to succeed
- A failing result triggers "let's try a different framing" rather than a stop
- It measures something adjacent because the real thing was hard to measure

## Behavior beats intent, always

Rank evidence by what it cost the respondent:

```
money paid            > strongest
email + verified      >
click through         >
"yes I would use it"  > worthless
```

A stranger's click outweighs a friend's enthusiasm.

## Output

```
Load-bearing belief:  Short-form clips will drive newsletter signups
Falsifiable form:     ≥ 2% of clip viewers who click the bio link subscribe,
                      measured over 10 clips in 14 days
Cheapest test:        Post 3 clips with a tracked link. Cost: ~4 hours.
Kill threshold:       < 0.7% → the channel is not a signup channel; stop.
Confounders:          Clip topic varies; hold topic constant across the 3.
What a "yes" earns:   Permission to spend 4 weeks, not permission to skip
                      the next test.
```

Note the last line. A passed test buys the next increment of investment, never
the whole plan.

## Related

- `red-team` — to surface which assumptions exist at all
- `stat-guard` — to size the test so the result means something
- `base-rates` — for the prior before the test moves it
