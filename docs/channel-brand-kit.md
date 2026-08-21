# Channel brand kit: TayTested

The identity, built from the teardown's conclusion (`channel-teardown.md`):
the open slot in this niche is *the channel where every number is tested on
screen*. Everything below — name, voice, colors, thumbnails — exists to make
that one claim recognizable in half a second.

---

## The name: **TayTested** (@TayTested)

`youtube.com/@TayTested` returned "not found" on 2026-08-21, which means the
handle appears unclaimed — **verify and claim it at channel creation before
printing anything.**

Why it wins:

- **It IS the positioning.** The name makes the channel's promise. Every
  incumbent in the teardown is named like a person or a vibe; none is named
  like a claim.
- **Personal + durable.** It's you (Tay), so it survives any pivot — GTA
  today, GTA VI next year, Battlefield if the data says so. A game-bound
  name would cap the channel at one game's lifespan.
- **It conjugates.** "TayTested it" is a sentence viewers can use.
  Thumbnails get a natural stamp (TESTED ✓). Series names inherit it for
  free.
- **Clean for search.** No numbers, no underscores, spellable from hearing
  it once.

Rejected alternates, for the record (`decision-log` style):

| Candidate | Why not |
|---|---|
| Patch Math | Strong concept, but reads niche-utility, not a person; harder to love |
| The Grind Ledger | Good flavor, but abstract — no face, no claim |
| Worth It Weekly | Locks the brand to one series; kept as the *series* name instead |
| Los Santos Ledger | Builds the brand on Rockstar's trademark — legally fragile and blocks any pivot |

**Rule inherited from the alternates:** no game's name or trade dress in
your identity. The channel covers games; it isn't owned by one.

## Positioning statement

> **TayTested — tested numbers, ranked verdicts, no hype.** Every payout,
> per-hour rate, and "worth it" on this channel was measured on screen with
> the method shown. If it wasn't tested, it isn't claimed.

Channel one-liner (for the banner, About page, and your own discipline):
**"Tested numbers. Ranked verdicts. No hype."**

## Voice rules (per `brand-voice` — five rules, enforced)

1. **Verdict first, proof second.** Open with the answer; spend the video
   earning it. Never "let's find out together."
2. **Numbers are shown, not said.** Timer, payout screen, or math overlay
   on screen for every figure. A number without footage doesn't get spoken.
3. **"Skip" is said as plainly as "buy."** The willingness to say
   *don't spend* is the whole brand. One dishonest rave kills it.
4. **No hype vocabulary.** Banned: INSANE, OP, BROKEN, "game-changer",
   "you NEED". The green stamp does the excitement.
5. **Admit the untested.** "I haven't tested this yet" said out loud is a
   brand asset, not a weakness — it's what makes the tested claims land.

## Visual identity

**Palette**

| Role | Hex | Use |
|---|---|---|
| Ink | `#0B0F14` | backgrounds |
| Panel | `#131A22` / `#1F2A36` | cards, chips, gauge tracks |
| Paper | `#F5F7FA` | primary text |
| Steel | `#93A4B8` | secondary text |
| Verdict Green | `#2BD576` | BUY, the check, the brand accent |
| Alarm Red | `#FF4757` | SKIP |
| Test Amber | `#FFB020` | TESTED stamp, caveats |

**Type:** Archivo Black for display/wordmark, Inter for everything else —
both free under the SIL Open Font License, downloadable from Google Fonts,
usable commercially in thumbnails and video. Never use Pricedown (the
GTA-style font) — that look is Rockstar's trade dress and the "GTA-font
channel" is also the most generic possible costume in this niche.

**The motif:** the gauge arc + check. It appears in the avatar, banner, and
end screens. It means "measured."

## Thumbnail system (template: `assets/brand/thumbnail-template.svg`)

Every thumbnail is: **gameplay still + max 3 words + exactly one verdict
stamp + series chip.**

- Stamps: green **BUY**, red **SKIP**, amber **TESTED** — rotated ~9°,
  heavy outline. The stamp is the brand; a viewer should know your video
  in the suggested rail before reading a word.
- The 3 words must not repeat the title (`hook-craft`: the pair asks one
  question). Title says the topic; thumbnail says the verdict or the
  tension.
- Legibility check at 120px wide before every upload, no exceptions.

## Series architecture

| Series | Slot | Chip text | What it is |
|---|---|---|---|
| **Worth It This Week** | Thu | WORTH IT · THU | Ranked buy/skip verdicts on the weekly update — the second-opinion video, not the news race |
| **The Test Bench** | Wed | TEST BENCH | Per-hour money methods, timer on screen, methodology stated |
| **Day One** | Sat | DAY ONE | Beginner path videos (the confirmed video gap — Acid Lab first) |
| **PC Report** | monthly → weekly near launch | PC REPORT | The stranded-PC GTA VI lane: confirmed facts only, sources on screen |

## Channel description (paste-ready)

> Every number on this channel was tested on screen. TayTested runs the
> experiments GTA Online guides usually skip: real per-hour rates with the
> timer running, ranked buy/skip verdicts on every weekly update, and
> beginner paths that were actually replayed from level 1. If it wasn't
> tested here, it isn't claimed here. New guides Wednesday and Saturday,
> Worth It This Week every Thursday. On PC — covering what the GTA VI
> console launch means for PC players, facts only.

## Upload defaults (set once in YouTube Studio)

- Category Gaming; game title set per upload (drives the game hub page)
- Default tags: none needed beyond a few honest ones — tags barely matter;
  the title/thumbnail pair is the packaging
- End screen: one video (the next in series) + subscribe — built from the
  gauge motif
- Every description's first line: what was tested and the verdict; then
  chapters; then the affiliate disclosure line whenever a link appears
  ("I earn a commission if you buy through this link" — `compliance-guard`)

## Assets shipped (in `assets/brand/`)

| File | Size | Upload as |
|---|---|---|
| `avatar-taytested.png` (+`.svg` source) | 800×800 | Profile picture (YouTube crops it circular; artwork is safe inside the circle) |
| `banner-taytested.png` (+`.svg` source) | 2560×1440 | Banner — all text sits inside the 1546×423 universal safe area, so it survives every device crop |
| `thumbnail-template.png` (+`.svg` source) | 1280×720 | Not uploaded — the working template for every video's thumbnail |

The SVGs are the editable masters — any text editor changes the words, any
browser previews them. Re-render PNGs from this repo with headless Chromium
(the exact commands are in this file's git history) or any SVG→PNG
converter at the sizes above. Install Archivo Black + Inter locally before
rendering final thumbnails so the wordmark weight matches the design.

## Launch checklist

- [ ] Claim @TayTested at channel creation (verify availability live)
- [ ] Upload avatar + banner PNGs
- [ ] Paste channel description
- [ ] Install Archivo Black + Inter (Google Fonts, free)
- [ ] Make thumbnail #1 from the template (it ships pre-filled with the
      first video: ACID LAB FIRST / BUY)
- [ ] First upload: Day One #1 — "Best First Business in GTA Online" —
      per the teardown, the confirmed video gap goes first
