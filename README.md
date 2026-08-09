# Claude configuration — research, analytics, and social

A working Claude setup: **28 skills**, **10 dependency-free tools**, a
validation hook, and a **126-test adversarial QA suite**. No pip install, no
build step, no API keys.

The skills cover three things that compound: thinking that resists being
wrong, analysis that resists fooling you, and social distribution across the
platforms that actually have global reach.

## Install

```bash
git clone <this repo> && cd <repo>
./install.sh              # symlinks skills/agents/commands into ~/.claude
```

Or use it per-project by keeping the `.claude/` directory in the repo you are
working in — that is what it is designed for, and it means the configuration
travels with the project.

Verify:

```bash
python3 qa/validate.py    # config integrity
python3 qa/selftest.py    # 126 adversarial tests
```

## The skills

**Thinking — built to catch you being wrong**

| | |
|---|---|
| `red-team` | Steelman, then attack five ways. Cheapest test attached to every finding. |
| `pre-mortem` | Assume it failed. Work backwards to tripwires and kill criteria. |
| `inversion` | How would I *guarantee* failure? Then stop doing those. |
| `base-rates` | Reference class first, enthusiasm never. |
| `falsify-first` | The cheapest test that could produce a "no", before building. |
| `second-order` | And then what happens. Three rounds, reversibility marked. |
| `decision-log` | Confidence recorded *before* the outcome — the only scoreable line. |
| `contrarian-scan` | Where consensus is inherited rather than true. |

**Research**

| | |
|---|---|
| `deep-research` | Source tiering, contradiction log, fact/inference/speculation kept apart. |
| `source-triage` | Citation laundering, AI filler, astroturf, study quality. |
| `knowledge-graph` | Persistent entity graph with centrality, clusters, and bridges. |

**Analytics**

| | |
|---|---|
| `chart-forge` | Chart chosen by the question, not by the data's shape. |
| `metrics-lab` | Funnels, cohorts, retention, growth, concentration. |
| `stat-guard` | Significance, sample size, Bayesian read, the cost of peeking. |
| `anomaly-watch` | Trend-aware robust detection. Changepoints, not just spikes. |
| `data-clean` | The specific ways platform exports lie. |

**Social**

| | |
|---|---|
| `social-command` | Strategy layer and router. |
| `platform-playbooks` | 20+ platforms, incl. WhatsApp, Telegram, and the Chinese platforms. |
| `hook-craft` | First three seconds, titles, thumbnails, subject lines. |
| `content-atomizer` | One pillar → ~15 native cuts. Never cross-post. |
| `posting-calendar` | Cadence built for your worst week. Exports ICS. |
| `social-analytics` | Exports → normalized dataset → dashboard → honest read. |
| `competitor-recon` | Public sources only. Finds what they *abandoned*. |
| `comment-ops` | Reply triage, moderation, crisis response. |
| `brand-voice` | Extract a voice guide; detect the AI-written tells. |
| `seo-aeo` | Search *and* getting cited by AI answer engines. |
| `growth-loops` | Compounding loops, instrumented — k, cycle time, decay. |
| `compliance-guard` | Disclosure, licensing, scraping, giveaways, AI labeling. |

## The tools

Stdlib-only Python. Each reads CSV and prints a table or `--json`.

```bash
# Charts — self-contained SVG, adapts to light/dark, safe under a strict CSP
python3 tools/chartkit.py --type line --csv d.csv --x date --y views --out c.svg

# Where are people leaving?
python3 tools/metrics.py funnel --csv events.csv --user user_id --step step \
    --order impression,click,signup,purchase

# Is this difference real? (run both — they answer different questions)
python3 tools/abtest.py compare --a 120/4000 --b 151/4050
python3 tools/abtest.py bayes   --a 120/4000 --b 151/4050
python3 tools/abtest.py size --baseline 0.03 --lift 0.15 --daily 1200

# Did the metric actually break, or is it just moving?
python3 tools/anomaly.py --csv daily.csv --date date --value views --seasonal weekly

# What does this total actually rest on?
python3 tools/concentration.py --csv pages.csv --item url --value pageviews
python3 tools/concentration.py --csv posts.csv --item id --value revenue \
    --date published --decay --period year

# Social exports → one schema → dashboard
python3 tools/social_ingest.py --csv yt.csv --platform youtube \
    --csv tt.csv --platform tiktok --out norm.csv --summary
python3 tools/dashboard.py --csv norm.csv --out dashboard.html

# Knowledge graph that survives the session
python3 tools/kg.py link --from mkbhd --to studio_quality --rel uses \
    --note "capex is the moat"
python3 tools/kg.py central --top 20
python3 tools/kg.py mermaid --focus mkbhd --depth 2 > map.mmd

# Posting schedule → CSV + calendar import
python3 tools/calendar_gen.py --start 2026-09-01 --weeks 8 \
    --slot "Tue 09:00 teardown" --slot "Thu 09:00 clip" \
    --tz America/New_York --out schedule.csv --ics schedule.ics
```

## See it run

[`demo/`](demo/) is a complete worked example: three raw platform exports in
their native formats — different column names, different date formats, one in
cp1252 — put through the whole pipeline to a finished report.

```bash
python3 demo/build.py            # regenerate demo/report.html from a real run
python3 demo/build.py --check    # fail if the committed page is stale
```

Every number and terminal block on that page is captured from a live subprocess
run, so nothing in the copy can disagree with what the tools actually output.

## The browser tool

[`studio/`](studio/) is Reportcraft: one self-contained HTML file that turns
a CSV export into a client-ready report. No install, no server, no network —
files are read in the tab and never transmitted.

```bash
python3 studio/build.py --artifact   # rebuild index.html, artifact.html, docs/
python3 studio/build.py --check      # fail if any built copy is stale
node studio/parity.mjs               # prove the JS matches the Python tools
node studio/browsertest.mjs          # drive it in a real browser
```

**Hosting.** `docs/index.html` is a byte-identical copy served by GitHub Pages.
Enable it once — *Settings → Pages → Source: GitHub Actions* — and every push
republishes at `https://<owner>.github.io/<repo>/`. The deploy workflow refuses
to publish a stale build or one that could reach the network.

The statistics are a second implementation of what lives in `tools/`, so
**214 values are compared against the Python original** on every check. Two
implementations drift silently otherwise.

## Commands

`/audit` — validate everything · `/numbers` — exports to dashboard ·
`/attack` — stress-test a plan · `/gap` — niche teardown

## What makes this different

**It argues with you.** `abtest.py` refuses to call a winner when the interval
contains zero. `anomaly.py` reports that a series is boring — because if you
expected a change, its absence is the finding. `social_ingest.py` prints why
its own output should not be used to rank platforms.

**The QA suite tests for wrong answers, not just crashes.** It asserts that a
strict funnel excludes step-skippers, that swapping A/B arms gives the
complementary posterior, that 2 hours of watch time becomes 7200 seconds, that
a Theil–Sen slope survives a 10,000x outlier, and that the validator itself
fails a deliberately broken skill.

**Nothing phones home.** Charts and dashboards are self-contained — no CDN, no
fonts, no fetch. They publish as Artifacts under a strict CSP and render in
light or dark without configuration.

**It respects platform terms.** `competitor-recon` uses public sources only and
says so; `compliance-guard` covers disclosure, licensing, and scraping limits.
No tool here touches a network.

## Requirements

Python 3.9+. That is the entire list. `tzdata` is optional — `calendar_gen`
falls back to `--utc-offset` without it.
