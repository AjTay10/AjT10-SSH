# Starter kit: first 10 weeks of videos, ready to validate

Companion to `youtube-gaming-startup-plan.md`. That document is the strategy;
this one is the ammunition: 20 topic concepts with title + thumbnail pairs, a
validation worksheet, the OBS setup checklist, and a 90-day calendar
(`posting-schedule-90d.csv` / `.ics` — import the ICS into any calendar app;
regenerate for your timezone with the command at the bottom).

Built with `hook-craft` (titles and thumbnails), `posting-calendar` (the
schedule), and the plan's format-modeling method (section 5 there).

---

## How to use the 20 concepts — validate before you record

These are **candidates built from evergreen search demand patterns, not
verified winners**. Game metas shift with every patch, so before recording
any of them:

1. Search the title on YouTube. First page full of big channels answering it
   *well and recently*? Skip it. First page thin, outdated (pre-latest-patch),
   or low-effort? Green light.
2. Check the concept is still true in the current patch. A guide that's wrong
   for the current version earns the worst possible outcome: high clicks,
   instant exits, and the algorithm learning your thumbnails mislead.
3. Write your own numbers from your own gameplay. Never quote earnings/stats
   you haven't verified in-game — specificity only works when it's real.

Title rules applied throughout (from `hook-craft`): concrete noun first, no
windup, ~60 visible characters, and the thumbnail must NOT repeat the title —
the pair creates **one** question together. Thumbnail text is 3 words max,
legible at 120px.

## The 20 concepts (GTA Online guide niche)

Format: **Title** / thumbnail text / hook mechanism / your first line on
screen (deliver, don't greet).

**Money & progression (the perennial search demand)**

1. **Best First Business in GTA Online (Current Patch)** / "NOT the bunker?" /
   contradiction / "If you have under $2M, there's exactly one business worth
   buying first — here's the math."
2. **GTA Online Solo Money Guide — No Friends Needed** / "SOLO ONLY" / named
   enemy / "Every money guide assumes you have a full crew. This one doesn't."
3. **What To Buy This Week in GTA Online** (weekly series) / "THIS week" /
   immediate payoff / "This week's discounts, ranked: buy this, skip these."
   — The recurring series is the channel's backbone: same search, every week,
   forever.
4. **I Started a New GTA Online Account — Here's the Fastest Route to $10M** /
   "Day 1 → $10M" / specificity (your real numbers, tracked on screen) /
   "Fresh account, no shark cards, timer running."
5. **The GTA Online Businesses That Are a Waste of Money (Current Patch)** /
   "don't buy" / stakes / "These purchases look good and quietly cost you
   hours."
6. **GTA Online Beginner's Guide — What Actually Matters in Your First Week** /
   "start here" / immediate payoff / "Skip the tutorial trap: do these three
   things first."
7. **Cayo Perico in [current year]: Still Worth It? Tested.** / "still #1?" /
   information gap / "I ran it ten times this patch — here's the real
   per-hour number."
8. **Nightclub Guide: The Passive Income Setup Most Players Get Wrong** /
   "one wrong toggle" / information gap / "One settings mistake cuts your
   nightclub income — check yours now."

**Settings & fixes (highest intent, lowest supply)**

9. **Best GTA Online Settings for FPS on a Mid-Range PC** / "free FPS" /
   immediate payoff / "Change these five settings; here's the before/after
   on my machine."
10. **How To Fix [current common error/crash] in GTA Online** / "FIXED" /
    named enemy / "If you're getting this error, do this — takes two
    minutes." — Watch the game's subreddit for whatever breaks after each
    update; be first with the fix.
11. **GTA Online Keeps Loading Forever? Try This.** / "load faster" /
    named enemy / "Here's what actually shortens loading, tested."

**Skill & tactics**

12. **How To Win Every Gunfight in GTA Online (Aim Settings + Movement)** /
    "stop dying" / stakes / "You're losing fights before you shoot — here's
    why."
13. **GTA Online's Best Armored Vehicle for the Money, Tested** / "tested
    all" / information gap / "I took every contender against the same
    attacks. One clear winner."
14. **Things I Wish I Knew Before 1,000 Hours of GTA Online** / "1,000 hrs" /
    specificity / "Number one would have saved me a hundred hours on its own."
    — Record your real hours; don't claim 1,000 if it's 300. 300 works fine.

**Update & news-adjacent (demand spikes, be early)**

15. **New GTA Online Update: Everything Worth Doing (And What To Skip)** /
    "worth it?" / immediate payoff / "Here's what's actually new, in order
    of what it pays."
16. **GTA Online Weekly Update Breakdown** (companion to #3, stream-cut) /
    "patch notes, fast" / immediate payoff / "Everything that changed, in
    ninety seconds."

**GTA VI positioning (plant these before launch; verify the release date)**

17. **What GTA Online Players Should Do Before GTA VI** / "before VI" /
    stakes / "Some of your grind will matter after launch. Most won't.
    Here's the difference."
18. **GTA VI: What We Actually Know (No Rumors)** / "facts only" / named
    enemy / "Only confirmed information — everything here has a source on
    screen." — This one is your credibility flag in a niche drowning in
    fabricated leaks. Cite Rockstar's own posts only.

**Battlefield lane (if the recon shows a better gap there)**

19. **Best [Battlefield current title] Settings Nobody Changes** / "default =
    losing" / contradiction / "Three default settings are costing you fights."
20. **[Battlefield] Class Guide After the New Patch: What Changed** / "buffed
    or dead?" / information gap / "The patch quietly changed the best
    loadout — here it is."

## Validation worksheet (copy per concept)

```
Concept #: ____
YouTube search result, page 1:  [ ] saturated  [ ] outdated  [ ] thin  → verdict
Still true in current patch?    [ ] verified in-game on ____-__-__
My angle/improvement:           ______________________________
Title (≤60 chars visible):      ______________________________
Thumbnail (≤3 words, ≠ title):  ______________________________
First 15 seconds deliver:       ______________________________
```

## OBS setup checklist (once, ~20 minutes)

- [ ] Settings → Output → Recording: encoder = your GPU's hardware encoder
      (NVENC on NVIDIA / AMF on AMD / QSV on Intel), not x264
- [ ] Recording format MKV (survives a crash), remux to MP4 after — OBS does
      this under File → Remux Recordings
- [ ] 1920×1080; 60 FPS for shooters, 30 for everything else
- [ ] Audio: game and mic on **separate tracks** (Output → Recording →
      audio tracks; assign in the Audio Mixer). This makes every edit easier.
- [ ] Mic filters, in order: Noise Suppression → Gain → Compressor. Speak at
      normal volume; peaks should touch yellow, never red.
- [ ] **GTA specific: radio OFF or self-radio only, every session.** The
      licensed music is a Content ID claim on your first upload.
- [ ] Do a 2-minute test recording and watch it back with headphones *before*
      any real session. Every creator has lost a session to a muted mic once.

## Regenerate the calendar for your timezone

```bash
python3 tools/calendar_gen.py --start 2026-08-24 --weeks 13 \
  --slot "Mon 18:00 Record + rough edit (video 1)" \
  --slot "Tue 17:00 Publish Short" \
  --slot "Wed 17:00 Publish long-form video 1" \
  --slot "Thu 17:00 Publish Short" \
  --slot "Fri 18:00 Record + rough edit (video 2)" \
  --slot "Sat 11:00 Publish long-form video 2" \
  --slot "Sun 12:00 Publish Short" \
  --slot "Sun 19:00 Weekly review: retention graphs + pick next 2 topics" \
  --tz America/New_York --out docs/posting-schedule-90d.csv \
  --ics docs/posting-schedule-90d.ics
```

Swap the times to slots you can actually hold — the plan's rule stands:
consistency you can keep beats ambition you can't. The Sunday review slot is
the one that isn't optional; that's where the retention graphs turn into
next week's improvements.
