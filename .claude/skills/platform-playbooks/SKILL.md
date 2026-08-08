---
name: platform-playbooks
description: Per-platform mechanics for the major global social platforms — YouTube, TikTok, Instagram, X/Twitter, LinkedIn, Facebook, Reddit, Pinterest, Threads, Snapchat, Discord, Telegram, WhatsApp, Twitch, Bluesky, and the major Chinese platforms. Use when the user asks how a specific platform works, what its algorithm rewards, what format or specs to use, why reach dropped on one platform, or how to adapt content for a particular network. Also use when writing or scheduling anything platform-specific.
---

# Platform playbooks

Every platform is a different medium. The craft does not transfer as cleanly
as it looks, and content that is merely reposted reads as reposted — which
most ranking systems detect and demote directly.

Detailed per-platform notes: `references/platforms.md`
Machine-readable specs: `references/specs.json`

```bash
python3 -c "import json;d=json.load(open('.claude/skills/platform-playbooks/references/specs.json'));print(json.dumps(d['youtube'],indent=2))"
```

## Verify specs before relying on them

Character limits, aspect ratios, and especially ranking behavior change
without announcement. `specs.json` carries a `_reviewed` date. Anything
load-bearing — an ad spend decision, a production commitment — should be
checked against the platform's current documentation. Treat the reference as
a strong prior, not as truth.

Ranking behavior in particular is never officially published in full. What
follows is inferred from platform statements, creator-visible analytics, and
widely reproduced observation. It is a model, and models drift.

## What every ranked feed actually optimizes

Underneath the differences, ranked feeds are all predicting the same thing:
*will this person keep using the app if we show them this?* The proxies vary,
but the hierarchy is remarkably consistent:

```
1. Watch time / dwell time         ← dominates everywhere it can be measured
2. Completion or read-through rate
3. Costly engagement (share, save, DM-forward) — signals value, hard to fake
4. Cheap engagement (like) — weak signal, cheaply gamed
5. Follower count                  ← the weakest input, and the one everyone chases
```

**Shares and saves outrank likes almost everywhere**, and by a wide margin.
A save says "I will need this again". A share says "this makes me look good
to send". Both are costly, which is exactly why they are trusted. Optimizing
for likes is optimizing for the cheapest signal in the stack.

**Early velocity matters more than total volume.** Most systems test content
on a small audience and expand or stop based on the first minutes to hours.
This is why the first hour's replies matter, and why posting into a dead hour
caps a post before it starts.

## The dimension that actually separates platforms

Not the format — the **discovery mechanism**. It determines everything about
how content should be built:

| Mechanism | Platforms | Consequence |
|---|---|---|
| **Interest graph** — shown to strangers who might care | TikTok, YouTube, Reels, Shorts | followers barely matter; every post starts near zero; a beginner can outreach an incumbent |
| **Social graph** — shown to your connections and theirs | Facebook, LinkedIn, WhatsApp | network quality is the ceiling; growth is compounding but slow |
| **Following feed** — shown to people who chose you | X, Threads, Bluesky, Telegram | consistency and volume compound; hard cold start |
| **Search / intent** — found when someone is looking | YouTube search, Pinterest, Reddit, Google | slow start, long tail, content keeps working for years |
| **Community** — inside a chosen space | Discord, Reddit, Slack, Telegram groups | reach is small, depth is high, rules are local and enforced by humans |

An interest-graph platform rewards a strong opening to strangers. A search
platform rewards answering a question completely. A community platform
punishes anything that reads as broadcast. The same content cannot serve all
three, and the attempt produces the flat, everywhere-at-once posts that
perform nowhere.

## Adapting across platforms

Never cross-post. Re-cut. See `content-atomizer` for the full process.

What must change per platform:
- **The opening** — three seconds on TikTok, a headline on LinkedIn, a title
  and thumbnail on YouTube, the first line before "see more" on Facebook
- **Aspect ratio and safe areas** — a vertical video with a caption baked into
  the bottom third is unusable when the platform's own UI sits there
- **The ask** — "comment below" belongs where comments drive ranking, not
  where saves do
- **Length** — the same idea is 30 seconds, 800 words, or 12 minutes
- **Visible platform artifacts** — a TikTok watermark on a Reel is demoted
  outright, and this is one of the few penalties platforms confirm

## The platform-neutral rules

1. **Own the destination.** Every platform audience is rented. Convert to
   email, always.
2. **Assume the account can vanish.** No appeal, no explanation, no warning.
   Export followers and content on a schedule.
3. **Read the platform's own analytics before any third-party tool.** The
   platform knows what it is optimizing; a third-party dashboard is guessing.
4. **Rules are enforced unevenly and retroactively.** Compliance with the
   letter of a policy is not protection. See `compliance-guard`.
5. **When reach drops, check instrumentation before blaming the algorithm.**
   See `anomaly-watch` — it is almost always something more boring.

## Regional reality

Global reach is not one market. The platforms that dominate outside the
US/EU are structurally different — Chinese platforms are commerce-integrated
from the ground up rather than advertising-supported, which changes what
content is rewarded. WhatsApp and Telegram dominate distribution across
India, Brazil, Indonesia, and much of Africa and the Middle East, and neither
has a ranked public feed at all: distribution there is forwarding, which
means the content has to be worth *sending to a specific person*.

See `references/platforms.md` for regional detail.

## Related

- `social-command` — strategy layer above this
- `content-atomizer` — the re-cutting process
- `posting-calendar` — cadence and timing per platform
