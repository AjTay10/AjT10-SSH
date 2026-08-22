# Video #1 — full production script and walkthrough

**"Best First Business in GTA Online (Current Patch)"** · Day One #1
Thumbnail: ACID LAB FIRST / BUY (already built) · Target runtime 6–8 min

This is the demonstration of the whole pipeline: prep → capture → fill-in →
voiceover → edit → publish. Videos 2–20 reuse this exact process with their
skeletons. Time budget for this first one, honestly: **capture ~2–3 h,
edit ~3–4 h, publish ~30 min.** It gets faster; the first one is the slow one.

Two marker types, per the repo's never-fabricate rule:
- `[TEST: …]` — a number you must measure on screen before the line is spoken.
- `[VERIFY: …]` — a game mechanic that patches change; confirm in-game the
  day you record. If reality differs from this document, reality wins and
  the script bends to it.

---

## Stage 1 — Pre-flight (30 min, day before)

- [ ] Re-run the supply check: search the title on YouTube. Still no strong,
      current video on page one? Proceed. (If a good one appeared this month,
      your angle becomes "tested on the current patch" — proceed anyway.)
- [ ] OBS: hardware encoder, 1080p60, MKV, **separate tracks** for game and
      mic, 2-minute test recording watched back with headphones.
- [ ] In-game: radio **off** ([VERIFY] it stays off per session), HUD on —
      viewers need to see menus and payouts. Note the patch/update name; it
      goes on screen in the first 30 seconds.
- [ ] Fill-in sheet (Stage 3) printed or on second screen.

## Stage 2 — Capture session (2–3 h): the shot list

Record everything below; narration comes later, so play silently or mute
your mic track in the edit. Over-record — cutting is cheap, re-capturing
isn't.

| # | Shot | What must be visible |
|---|---|---|
| S1 | **The money shot first**: a completed acid sell, payout on screen | The payout figure popping — this is your cold open, so frame it clean |
| S2 | Full sell run, start to finish, with a stopwatch overlay or visible clock | Leaving the lab → delivery → payout. One continuous take; you'll speed-ramp it |
| S3 | The Acid Lab interior: production, equipment, stash | Slow pans; b-roll for the "what it is" beat |
| S4 | [VERIFY] the acquisition path: the First Dose mission set completion screen and the Brickade/lab purchase menu with prices | Every price legible for 2+ seconds |
| S5 | The equipment upgrade purchase screen [VERIFY: unlock requirement — the Dax side-jobs — and current price] | Requirement text + price |
| S6 | Resupply loop: one full supply run with timer | For the honest "what the grind feels like" beat |
| S7 | Comparison menus: bunker price screen, nightclub price screen | For the "why not these first" beat — prices legible |
| S8 | Your bank balance before/after the sell | Continuity proof |
| S9 | 30 s of generic driving/ambient gameplay | Filler b-roll for VO-heavy moments |

While capturing, run the actual tests on the fill-in sheet:

## Stage 3 — The fill-in sheet (complete BEFORE voiceover)

```
F1  Total cost to own the lab, all-in ............ $[TEST]   [VERIFY components]
F2  Equipment upgrade cost ....................... $[TEST]
F3  Time to complete acquisition missions ........ [TEST] min (your real time)
F4  One full sell: payout ........................ $[TEST]
F5  One full sell: minutes, lab door to payout ... [TEST] min
F6  Production time for a full batch ............. [TEST] h  [VERIFY mechanic]
F7  Supply run: minutes .......................... [TEST] min
F8  Effective $/hr of active time (F4 ÷ active min × 60) ... $[TEST]/hr
F9  Sells to recoup F1+F2 (math from your numbers) [TEST]
F10 Bunker all-in starter cost (menu screens) .... $[TEST]
F11 Nightclub all-in starter cost ................ $[TEST]
```

If a test result surprises you — the payout is worse than the community
says, the recoup is longer — **the script keeps your number and says so.**
That moment is the brand.

## Stage 4 — The script (SAY / SHOW)

Read it aloud twice before recording VO. Cut any sentence you stumble on —
if it doesn't fit your mouth, it isn't your voice yet. Record VO in OBS or
DaVinci against the rough cut, one section at a time.

### COLD OPEN — 0:00–0:15
| SAY | SHOW |
|---|---|
| "If you have under [F1+F2, rounded] dollars in GTA Online, there's exactly one business worth buying first. It's the Acid Lab — and I tested every number in this video on screen, this patch." | S1: the payout popping at 0:01. Patch name in corner. Result-card overlay slides in at 0:10. |

*No logo, no greeting, no music sting before the payout lands.*

### STAKES — 0:15–0:45
| SAY | SHOW |
|---|---|
| "New players get told to save for a bunker or a nightclub. That advice costs you about [F10 − (F1+F2), rounded] dollars you don't have and weeks you don't need to spend. Here's the math, in order: what the lab costs, what one sell actually pays, and how fast it pays for itself. Timer's on screen the whole way." | S7 comparison menus flashing prices → cut to S3 lab interior. Chapter markers appear. |

### CHAPTER 1 — What it really costs — 0:45–2:00
| SAY | SHOW |
|---|---|
| "[VERIFY/adapt:] The lab comes from the First Dose missions — took me [F3] minutes, and you can start them from [VERIFY: current entry point]. Finishing them unlocks the lab vehicle at [price on screen], and the one upgrade that matters — the equipment upgrade — runs [F2]. All-in: [F1+F2]. That's the real number, not the sticker." | S4 mission completion + purchase menus, prices held on screen. Running "ALL-IN" counter accumulating in the corner as each cost lands. |
| "One honest warning: the upgrade needs [VERIFY: unlock requirement]. Budget [TEST: your time] for that. Everyone skips this caveat; it's real time." | S5 upgrade screen with requirement text. |

### CHAPTER 2 — What one sell pays — 2:00–4:00
| SAY | SHOW |
|---|---|
| "Full batch, solo lobby, no help. Lab door to payout: [F5] minutes. Payout: [F4]." | S2 the sell run, speed-ramped, real elapsed-time stopwatch pinned top-right. The payout moment plays at full speed. |
| "Production ran [F6] hours in the background while I did other things — the active time you actually spend is the sell plus a [F7]-minute supply run. Do that math and the lab pays about [F8] per hour of *your* time. That's the only number that matters, and most guides never show it." | S6 supply run compressed; then the result-card: $/run · min/run · $/hr, held for a slow 8 seconds. |

### CHAPTER 3 — Payback — 4:00–5:00
| SAY | SHOW |
|---|---|
| "So: [F1+F2] all-in, [F4] a sell — the lab pays for itself in [F9] sells. At a casual pace that's [your honest framing from F6 production time], and everything after that is profit that funds the next business." | Simple payback bar chart filling sell by sell (build in DaVinci or as an SVG frame). |

### CHAPTER 4 — Why not the bunker or nightclub FIRST — 5:00–6:15
| SAY | SHOW |
|---|---|
| "The bunker's a great business. It's also [F10] before it produces efficiently — [multiple] of the lab's all-in. Same story for the nightclub at [F11]: it's the best *passive* money in the game, but it needs other businesses running to earn, which is exactly what a new player doesn't have. Buy them — later, out of acid money, in that order. First business? There's one answer." | S7 menus with the three all-in figures side by side. End on the BUY stamp over the lab. |

*(If your F-numbers don't support these lines, rewrite the verdict to match
the data. The stamp follows the math, never the script.)*

### RECEIPTS + CTA — 6:15–6:45
| SAY | SHOW |
|---|---|
| "Every number from this video, one screen — screenshot it. [Beat — say nothing for 5 seconds.] Next Saturday: your entire first week, in order — what to claim free, what to grind, and the two purchases that waste your first million. Tested." | Full receipts table (all F-numbers). Then end screen: Day One #2 slot + subscribe, gauge motif. |

**Total narration ≈ 700–800 words. If your VO runs past 8 minutes, cut
Chapter 1's mission detail first — the payback math is the video.**

## Stage 5 — Edit walkthrough (DaVinci Resolve, 3–4 h first time)

1. **Import** MKV (remux to MP4 in OBS first: File → Remux). Drop on
   timeline; game audio track 1, mic track 2.
2. **Rough cut to the script**: lay S1 at 0:00, then assemble per the SHOW
   column. Don't polish yet.
3. **Record VO** against the rough cut (Fairlight page → record into track
   3), section by section. Re-take any stumble immediately.
4. **Build the result-card once**: Text+ node, ink `#0B0F14` panel, Paper
   text, Verdict Green accents (hex codes in the brand kit). Save as a
   **Power Bin asset** — every future video reuses it. Same for the
   stopwatch (Timecode generator or a screen-recorded stopwatch cropped in).
5. **Tighten**: cut every second that doesn't earn its runtime. First-video
   rule of thumb: your "done" cut is still 20% too long — cut again.
6. **Chapters**: note the final timecodes of each chapter for the
   description.
7. **Audio pass**: mic track through Noise Reduction → Compressor; VO peaks
   around −6 dB, game audio ducked ~−18 dB under narration.
8. **Export**: 1080p, high-bitrate H.264. Watch the whole export once,
   headphones on, before upload. Non-negotiable.

## Stage 6 — Publish checklist (30 min)

- **Title:** `Best First Business in GTA Online ([Month year] — Tested)`
  ≤100 chars; front-loads the search phrase.
- **Thumbnail:** the template PNG is ready (ACID LAB FIRST / BUY); swap the
  placeholder for your best S3 frame, check legibility at 120px.
- **Description, first lines:**
  > Tested on [patch, date]: the Acid Lab costs $[F1+F2] all-in and pays
  > $[F4] per sell — payback in [F9] sells. Every number measured on
  > screen. Chapters: [timecodes].
- **Chapters** from step 6. **End screen**: Day One #2 + subscribe.
- **Pinned comment:** "All numbers tested [date], patch [name]. If a patch
  changes them, this comment gets updated first. What should the Test Bench
  measure next?"
- **Shorts cut** (before you close the project): S1 payout → result card →
  "full math on the channel," 35 s vertical, publish next calendar Short slot.
- **Log it:** fill the row in `posting-schedule-90d.csv`, and check the
  retention graph 48 h later — first 30 seconds especially (`hook-craft`
  diagnosis table).

## What this video is not allowed to contain

No greeting. No channel intro. No "smash that like button." No number
without its footage. No claim the fill-in sheet doesn't back. No music bed
you don't have a license for (YouTube's own Audio Library is licensed for
YouTube — fine here). If the Acid Lab loses to something else in your
testing — publish that video instead, same structure, honest title. The
verdict follows the data. That's the channel.
