# Platform reference

Reviewed 2026-08. Specs and especially ranking behavior change without
notice — verify anything load-bearing against current platform documentation.
Ranking notes are inferred models, not published fact.

Machine-readable version: `specs.json`.

---

## YouTube — long-form

**Discovery:** interest graph (browse/suggested) + search. The only major
platform where search and recommendation both carry real weight.

**What it optimizes:** satisfaction-weighted watch time. Click-through rate
and average view duration together — CTR gets the impression, retention keeps
the distribution. A high-CTR video with poor retention is suppressed *and*
teaches the system to stop showing your thumbnails.

**Levers, in order of impact:**
1. Title and thumbnail as a *pair* — they must create one question, not two
2. First 30 seconds — the steepest drop-off on the retention graph is here
3. Packaging the topic itself — a topic nobody searches or clicks cannot be
   rescued by editing
4. Suggested-video pull — being adjacent to something already popular

**Read the retention graph, not the view count.** The shape tells you where
the video failed: a cliff in the first 30s is a packaging mismatch (the title
promised something else); a slow steady decline is normal; a mid-video cliff
is a specific segment to cut next time.

**Notes:** Shorts and long-form share a channel but not an algorithm — never
blend their retention numbers. Views count after roughly 30 seconds (or full
watch on Shorts). "Impressions" in YouTube analytics means thumbnail
impressions, which is not what any other platform means by the word.

---

## TikTok

**Discovery:** interest graph, near-pure. Follower count barely affects
distribution — a first post can outreach an established account, which cuts
both ways.

**What it optimizes:** completion rate and rewatch, then shares. Short videos
have a structural advantage because completion is easier to achieve; this is
why the platform trends short even as it raises length limits.

**Levers:**
1. First 1–2 seconds — visual and audio change on frame one, no intro
2. Completion — cut anything that does not earn its runtime
3. Rewatch — loops, a detail that rewards a second viewing
4. Comment bait that is honest — an obvious gap someone will fill in

**Notes:** a "view" counts at 0 seconds (autoplay), so TikTok view counts are
not comparable to YouTube's and must never share an axis. Trending audio
still gives a measurable boost but decays fast. Text on screen must clear the
UI safe areas — captions in the bottom third get covered.

---

## Instagram — Reels, Feed, Stories

**Discovery:** mixed. Reels are interest graph; Feed leans social graph;
Stories are followers-only and ordered by relationship strength.

**What it optimizes:** Reels — watch time and sends. **Sends per reach** is
the metric Instagram itself has pointed to as the strongest signal, and it is
the one to build for: content someone forwards to a specific person.

**Levers:** first frame, a reason to send, and saves for reference content
(carousels perform here). Carousels get a second impression when a user does
not swipe the first time.

**Notes:** "Reach" is unique accounts; "impressions" can be several per
account — do not mix them in a rate. Reels plays start at ~1 second.
Cross-posted TikToks with a visible watermark are demoted; this is confirmed
behavior, not folklore.

---

## X / Twitter

**Discovery:** following feed plus an algorithmic "For You" tab.

**What it optimizes:** dwell time and reply depth. Conversation is the
product, and the ranking reflects that.

**Levers:** the first line (the rest is truncated), a claim specific enough to
be disagreed with, and replying to your own replies to sustain a thread.

**Notes:** external links suppress reach — put the link in a reply, which is
the standard workaround and still costs some distribution. Impressions include
scroll-past, so engagement rate on X is structurally 5–10x lower than
Instagram; comparing the two as a quality measure is meaningless. Early
velocity matters intensely — the first 15–30 minutes largely decide the
outcome.

---

## LinkedIn

**Discovery:** social graph, weighted by professional relevance and dwell.

**What it optimizes:** dwell time — specifically the "see more" expansion —
and comments with substance. Comment *length* appears to matter more than
count.

**Levers:** the first two lines before the fold, a personal specific over a
general abstraction, and genuinely replying to every early comment.

**Notes:** external links suppress reach here too. Document/carousel posts
generate high dwell. Posting frequency above roughly one per day cannibalizes
sharply. The platform's culture rewards a specific confessional register that
reads as parody elsewhere — match it or accept lower reach; it is a real
tradeoff, not a rule.

---

## Facebook

**Discovery:** social graph, plus Groups as a distinct high-engagement surface.

**What it optimizes:** meaningful social interaction — comments and replies
between people, weighted above passive consumption.

**Notes:** organic Page reach is very low and has been for years; Groups and
paid are the realistic surfaces. Video views default to 3-second counting.
Daily "reach" is deduplicated per day, so summing daily reach across a month
substantially overcounts unique people — a very common reporting error.
Still the largest platform globally by users, and dominant in demographics
that the US tech-press narrative treats as absent.

---

## Reddit

**Discovery:** community-first, then site-wide via r/all. Search visibility is
excellent and long-lived — Reddit threads rank highly in Google and are
heavily weighted by AI answer engines.

**What it optimizes:** early upvote velocity within the subreddit, then
comment activity.

**Levers:** subreddit choice above all else, title as the entire pitch, and
comment participation from the author.

**Notes:** each subreddit has its own rules, enforced by human moderators who
are unpaid and unsympathetic. Self-promotion norms are strict and violation
is punished by removal and often a ban. Vote counts are deliberately fuzzed —
treat them as rank order, not measurement. High value for `seo-aeo` because
of durable search presence.

---

## Pinterest

**Discovery:** search and interest, almost entirely. Functionally a visual
search engine rather than a social network.

**What it optimizes:** saves, then outbound clicks. Keyword relevance in
titles, descriptions, and board names matters more than on any other social
platform.

**Notes:** impressions accrue for *months* after publishing — a pin's totals
are never final. Any comparison must be at fixed content age, never at a
calendar cutoff, or older pins win automatically. Underrated for evergreen
and commercial intent traffic. Strongly female-skewed audience in most markets.

---

## Threads

**Discovery:** interest graph, aggressive — heavily recommends accounts a user
does not follow.

**What it optimizes:** replies and time-in-app. Currently distributes new
accounts unusually generously compared to X.

**Notes:** views count at render, comparable to X impressions rather than to
Instagram reach. Tightly coupled to an Instagram account. Link suppression is
less severe than X.

---

## Snapchat

**Discovery:** friends first, plus Spotlight (interest graph) and Discover
(publisher).

**Notes:** overwhelmingly a private-messaging product with a public layer
attached, not the reverse. Story views expire and exports cover only the
retention window. Very young skew. Spotlight is the only realistic organic
discovery surface for a new account.

---

## Twitch

**Discovery:** category browse and raids; almost no algorithmic push.

**What it optimizes:** concurrent viewers and time watched. Discovery is
genuinely weak — growth comes from consistency of schedule, raids, and
off-platform clips (TikTok/YouTube) feeding back in.

**Notes:** average concurrent viewers is the metric that matters, not total
views. Schedule consistency matters more here than anywhere else because the
audience must show up live.

---

## Discord

**Discovery:** none. Purely invite and community.

**Notes:** this is a retention and depth surface, not an acquisition one.
Engagement is message volume; do not compute an engagement rate — there is no
impression denominator and any number you produce will be fiction. Best used
as the owned-adjacent destination for an audience acquired elsewhere. Note it
is *not* owned: Discord can remove a server.

---

## Telegram

**Discovery:** forwarding and directories. No ranked feed.

**Notes:** channel view counts are *cumulative and permanent* — a running
total, not a daily figure. Difference them before charting or every day looks
like a spike. Enormous in Eastern Europe, Central Asia, Iran, and among
crypto and news communities. Forwarding is the entire distribution mechanism,
so the content must be worth sending to a specific person.

---

## WhatsApp

**Discovery:** none — Channels are subscribe-only, and the real mechanism is
person-to-person forwarding.

**Notes:** the largest messaging platform globally and the dominant
distribution channel in India, Brazil, Indonesia, Nigeria, and much of the
Middle East. Broadcast metrics are limited to views and reactions. Business
API messaging is template-gated and paid. For much of the world this is the
platform that matters most and the one Western strategy decks omit entirely.

---

## Bluesky / Mastodon

**Discovery:** chronological plus user-chosen custom feeds; no central
algorithm to optimize against.

**Notes:** small but high-signal in technical and journalism communities. No
native analytics export — any numbers are third-party estimates. Growth is
genuinely linear here; there is no distribution lottery to win.

---

## Chinese platforms — Douyin, Xiaohongshu, WeChat, Weibo, Kuaishou

Structurally different: commerce is integrated from the ground up rather than
bolted onto an advertising product. Content that would read as overtly
transactional elsewhere is native here.

- **Douyin** — TikTok's domestic sibling; separate app, separate algorithm,
  far deeper commerce integration. Live commerce is the dominant format.
- **Xiaohongshu (RED)** — search-heavy discovery, review and recommendation
  culture, dominant for beauty/lifestyle/travel purchase decisions. Behaves
  more like a search engine with a social layer.
- **WeChat** — closed ecosystem: Official Accounts, Moments, Mini Programs.
  Almost no public discovery; distribution is via sharing into private
  networks. Effectively the whole internet for many users.
- **Weibo** — public broadcast, celebrity and news driven, trending-topic led.
- **Kuaishou** — strong in lower-tier cities, more community-oriented and
  less polished than Douyin.

All require domestic entity registration for commercial accounts, and content
moderation is strict, political, and enforced pre-publication. Do not plan a
China strategy from outside without local counsel — this is a legal question
before it is a marketing one.

---

## Cross-platform metric traps

| Trap | Detail |
|---|---|
| "Views" means different events | TikTok 0s, Facebook 3s, YouTube ~30s. Never share an axis. |
| Reach vs impressions | Reach is unique; impressions are repeated. Never mix in one rate. |
| Daily reach does not sum | Deduplicated per day; monthly reach ≠ sum of daily reach. |
| Cumulative counters | Telegram views, some subscriber exports. Difference first. |
| Accrual windows differ | Pinterest accrues for months; X is done in a day. Compare at equal age. |
| ER denominators differ | X ER is structurally ~5–10x lower than Instagram. Not a quality signal. |
| Fuzzed counts | Reddit deliberately fuzzes votes. Rank order only. |
