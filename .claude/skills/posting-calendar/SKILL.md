---
name: posting-calendar
description: Build a posting schedule and cadence that survives contact with a bad week — including timing, frequency, batching, and exporting to CSV or ICS. Use when the user asks for a content calendar, posting schedule, how often to post, the best time to post, or help staying consistent. Also use when they are posting erratically, burning out, or planning a campaign's timeline.
---

# Posting calendar

A calendar's job is to remove the daily decision, not to fill every slot.
Most content calendars fail in week three because they were built for the
best week rather than the worst one.

## Set cadence from capacity, not ambition

Write down what is sustainable on your **worst** week — sick, travelling,
busy at work — and schedule that. Anything above it goes out as surplus when
it exists.

A missed slot costs more than a smaller commitment: erratic posting confuses
both the audience's expectation and the platform's categorization of the
account.

```
Sustainable floor:   2 posts/week      ← this is the calendar
Typical week:        4 posts/week      ← surplus, posted opportunistically
Good week:           6 posts/week
```

**Frequency is not free.** On ranked feeds, distribution is allocated per
post from the same finite pool of your audience's attention. Nine weak posts
can out-reach three strong ones or badly under-reach them, and the answer is
account-specific. Test it — see `contrarian-scan` on the daily-posting belief.

## Timing: use your own data, not a listicle

"Best time to post" articles are aggregate averages across millions of
accounts in unstated timezones. They are close to useless for any specific
account.

Find yours:

```bash
python3 tools/social_ingest.py --csv export.csv --platform instagram --out norm.csv
python3 tools/dashboard.py --csv norm.csv --out when.html
```

The dashboard's weekday heatmap shows when *your* audience is actually
reachable. Two cautions before acting on it:

- **You cannot see the counterfactual.** If you have only ever posted at 9am,
  9am will look best. Deliberately test other slots for a few weeks.
- **Timezone spread matters more than the hour.** An audience split across
  continents has no single good time; a global account should stagger rather
  than optimize.

Early velocity does matter — most systems test on a small audience first —
so posting into a dead hour caps the post. But the effect is smaller than the
content's quality by a wide margin. Do not spend more than an afternoon on this.

## Batch production, drip publication

The highest-leverage change available:

```
Monday      research + outline        (2h)   ← one context, one mode
Tuesday     produce, all of it        (4h)   ← batching kills switching cost
Wednesday   edit + cut variants       (3h)
Thursday    schedule everything       (1h)
Fri–Sun     engage only, produce nothing
```

Context-switching between research, production, and editing costs more than
any individual task. Batching by *mode* rather than by *piece* is where the
time is recovered.

Keep a two-week buffer of scheduled content. It is the difference between a
bad week costing nothing and a bad week breaking the streak.

## Structure the week, not each post

Fixed slots with fixed formats, so the daily decision is "what goes in the
Tuesday teardown slot", not "what should I post".

```
Tue 09:00   Teardown         (pillar format, the one people subscribe for)
Thu 09:00   Short clip       (atomized from the pillar)
Sat 11:00   Community post   (question, poll, or reply-driven)
```

## Export a real calendar

```bash
python3 tools/calendar_gen.py --start 2026-09-01 --weeks 8 \
    --slot "Tue 09:00 teardown" --slot "Thu 09:00 clip" \
    --slot "Sat 11:00 community" --tz America/New_York \
    --out schedule.csv --ics schedule.ics
```

The CSV is the working document; the ICS imports into any calendar app so
slots appear where you already look. A calendar in a tool you do not open
daily is not a calendar.

## Campaign overlay

Campaigns sit *on top of* the regular cadence, they do not replace it.
Dropping the normal rhythm during a campaign costs the audience that would
have carried it. See `social-command` for the T−21 sequencing.

## Reviewing the calendar

Monthly, ask three questions:

1. **What did I skip, and why?** A slot skipped three times in a row is not a
   discipline problem, it is a wrong slot. Delete it.
2. **Which slot produced the most capture?** Followers and owned contacts
   gained, not impressions. Give that slot more room.
3. **What am I doing out of obligation?** Content produced without interest
   reads that way and performs accordingly. Cut it; a smaller honest calendar
   beats a larger dutiful one.

## Anti-patterns

- **Scheduling a whole quarter.** Anything beyond four weeks goes stale, and
  the sunk-cost of a planned post gets it published past its relevance.
- **Filling every slot before the format is proven.** Prove one format over
  10 posts before scaling the calendar around it.
- **Automation that posts and leaves.** Early replies drive early velocity.
  Scheduling is fine; being absent for the first hour is not.
- **A calendar nobody can see.** Export it. Keep it where you look.

## Related

- `content-atomizer` — produces the pieces that fill the slots
- `social-analytics` — finds the timing from real data
- `social-command` — campaign sequencing above the weekly rhythm
