# Agent Reach integration — install record and QA report

[Agent Reach](https://github.com/Panniantong/Agent-Reach) v1.5.0 is installed as a
Claude Code skill in this repository. This document records what was installed, how it
was verified, and what broke while trying to break it.

## What is installed

| Component | Location | Purpose |
|-----------|----------|---------|
| `agent-reach` v1.5.0 | `~/.agent-reach-venv`, linked into `~/.local/bin` | installer / doctor / router |
| `yt-dlp` 2026.07.04 | bundled in the venv, linked into `~/.local/bin` | YouTube channel |
| `gh` 2.95.0 | `~/.local/bin/gh` (checksum-verified download) | GitHub channel |
| `mcporter` 0.9.0 | npm global | MCP bridge; serves the Exa search channel |
| `bili-cli` | `~/.local/bin/bili` (installed by agent-reach via `uv`) | Bilibili channel |
| skill | `~/.claude/skills/agent-reach/` (SKILL.md + 7 reference docs) | routing table Claude reads |
| runtime state | `~/.agent-reach/` (mode 700, `config.yaml` mode 600) | config and tokens |

Nothing is installed into the workspace — the repo only carries the scripts that
reproduce the above.

| File | Role |
|------|------|
| `scripts/install-agent-reach.sh` | idempotent, locked, checksum-verifying installer |
| `scripts/reach.py` | the platform coverage layer (see below); installed as `reach` |
| `scripts/agent-reach-verify.sh` | live end-to-end channel checks (real network calls) |
| `.claude/hooks/session-start.sh` | installs on first run, self-heals, reports honest status |
| `.claude/settings.json` | registers the hook, pre-allows the read-only CLI commands |
| `.claude/skills/reach/SKILL.md` | tells Claude which command serves which platform |
| `CLAUDE.md` | routing table + the environment limits Claude must know |

## The `reach` layer — coverage for the major platforms

Agent Reach alone reaches 5 channels here. Its routing assumes a desktop Chrome
session (OpenCLI) or an unblocked residential IP, and neither exists in this
container, so the platforms most people actually mean by "social media" were all
dark. `scripts/reach.py` closes that gap by implementing, per platform, the access
path that was **measured** to work, with an explicit fallback chain.

| Platform | Primary backend | Fallback | Content |
|----------|-----------------|----------|---------|
| any web page | direct fetch + HTML→text | Exa fetch → Jina | full |
| web search | Exa `web_search_exa` | — | full |
| X / Twitter | `cdn.syndication.twimg.com` tweet-result | oEmbed → Exa | full post |
| Reddit | Exa index (search) | reworded query | thread text |
| Bluesky | `api.bsky.app` XRPC | — | full |
| Mastodon | instance public API | web reader | full |
| Telegram | `t.me/s/<channel>` preview | — | full |
| TikTok | oEmbed | Exa | title/author |
| YouTube | yt-dlp | Exa | full metadata |
| Facebook | yt-dlp (public video) | Exa | video metadata |
| Instagram | Exa | — | search index |
| LinkedIn | Exa fetch | Exa search | public profile/company |
| Threads | direct fetch | Exa | partial |
| Pinterest | Exa | — | search index |
| Wikipedia | MediaWiki API | — | full |
| Hacker News | Algolia API | — | full |
| Stack Overflow | StackExchange API | — | full |
| RSS/Atom | direct feed + autodiscovery | — | full |
| Snapchat | direct (og: metadata) | Exa | profile metadata |
| Discord | invite + widget API | Exa | server metadata |
| Twitch | direct (og: metadata) | yt-dlp, Exa | channel/VOD metadata |
| Tumblr | feed, then direct page | Exa | full |
| VK | direct | Exa | search index (JS shell) |
| Vimeo | oEmbed | yt-dlp, Exa | full metadata |
| Weibo | m.weibo.cn API | Exa | search index (API login-walled) |
| Quora | Exa | — | search index |
| Douyin | Exa | — | search index |
| Xiaohongshu | Exa | — | search index |
| Bilibili | bili CLI | Exa | full metadata |
| Medium | feed | page, Exa | full |
| Substack | feed | page, Exa | full |

`reach doctor` probes all 31 live in ~60s — **31/31 reachable**. It is the only
status command in this repo that is true by construction, because every probe
fetches real content and asserts it is non-empty.

Backends were chosen by probing this container, not by reading vendor docs. The
notable results: Discord's invite/widget APIs and Vimeo's oEmbed are fully open;
Twitch and Snapchat serve JavaScript shells whose `og:` tags still carry the
title and description; Tumblr's classic `/api/read/json` answers 429 from a
datacenter IP while `www.tumblr.com/<blog>` renders fine; Weibo's mobile API
returns `ok:-100` with an SSO redirect for anonymous clients; and Bilibili's web
API answers 412 without the signing the `bili` CLI carries.

`reach` parsers are covered offline by `tests/contract/`, which replays recorded
payloads from `tests/fixtures/`. That separates "our parser broke" from "the
site is down" — `reach doctor` alone cannot tell those apart.

### Access paths that do NOT work here (measured, not assumed)

Documented so nobody re-litigates them:

- **Reddit direct** — `www.reddit.com/*.json` 403, `old.reddit.com` 403,
  `.rss` 429, `/oembed` 404. Every public redlib/teddit mirror tried
  (`redlib.catsarch.com`, `redlib.freedit.eu`, `rl.bloat.cat`,
  `redlib.privacyredirect.com`, `safereddit.com`, `eu.safereddit.com`,
  `teddit.net`) returned 403, 503, a Cloudflare interstitial, or a TLS error.
  Exa's *fetcher* is blocked too; only Exa's cached index gets through.
- **TikTok via yt-dlp** — `Your IP address is blocked from accessing this post`.
  oEmbed is unaffected.
- **Instagram via yt-dlp** — `Instagram sent an empty media response`, i.e. a
  login wall. The deprecated `api.instagram.com/oembed` returns 429.
- **Bluesky `searchPosts` on `public.api.bsky.app`** — 403. The same call on
  `api.bsky.app` works; the host matters.
- **X with a placeholder syndication token** — old post ids are served with any
  token, but modern ids 404 unless the token is the real derived value (see
  finding #11).

## Channel status (verified live, not from `doctor`)

| Channel | `doctor` says | Actually | Evidence |
|---------|---------------|----------|----------|
| Exa search | ⚠️ unverified | **works** | `mcporter call exa.web_search_exa` returns results |
| YouTube | ✅ | **works** | `yt-dlp --dump-json` extracts metadata |
| RSS | ✅ | **works** | 20 entries parsed from hnrss.org |
| V2EX | ✅ | **works** | topics API returns hot topics |
| Bilibili | ✅ | **works** | `bili search` returns videos |
| GitHub | ⚠️ unverified | **partial** | in-scope repos only; see finding #2 |
| Web (Jina) | ✅ | **BLOCKED** | HTTP 401 from this egress IP; see finding #1 |
| Twitter, Reddit, Xiaohongshu, Facebook, Instagram, Xueqiu, Xiaoyuzhou, LinkedIn | ❌ | not installed | need credentials or a desktop browser |

Reproduce with `./scripts/agent-reach-verify.sh` — current result **9 passed, 1
degraded (web), 0 failed**.

## QA findings

Bugs found by adversarial testing, in severity order. Findings 1–4 are in the
integration or the environment; 5–7 are upstream defects.

> **Update after the build:** Jina Reader began answering HTTP 200 from this IP again
> (6/6 consecutive probes). The block is reputation-based and flips, so the finding
> below stands as written for the period it was measured, and the architecture — never
> depend on Jina, always have a fallback — is the right one regardless. What does *not*
> change is that `agent-reach doctor` calls the channel green without testing it, so its
> verdict is uninformative in both directions. `scripts/agent-reach-verify.sh` grades
> this channel degraded-not-failed for exactly this reason.

### 1. `doctor` reports the web channel green while it is hard-blocked — FIXED (worked around)

`curl https://r.jina.ai/https://example.com` returns:

```
HTTP 401 {"name":"AuthenticationRequiredError",
          "message":"You have been blocked from performing anonymous queries
                     due to bad IP reputation. Please authenticate."}
```

Jina Reader is agent-reach's *only* backend for generic web pages, so the flagship
"read any webpage" capability does not work from this container. `agent-reach doctor`
still prints it green because `WebChannel.check()` returns `ok` unconditionally and
never touches the network (a deliberate zero-overhead choice upstream — see
`agent_reach/channels/web.py`).

Worse, the failure is silent in the shape the skill recommends: `WebChannel.read()`
raises on the 401, but `references/web.md` tells the agent to run `curl -s
"https://r.jina.ai/URL"`, which exits 0 and prints the error JSON as if it were page
content. `_is_antibot_page()` only recognises Cloudflare and captcha pages, not this
auth error.

Worked around by routing generic web reads to Claude Code's `WebFetch` tool in
`CLAUDE.md`, and by having the session hook and the verify script both contradict
`doctor` explicitly. agent-reach has no Jina API-key setting, so there is no
in-tool fix.

### 2. The GitHub API is scoped to the session's repositories — documented

`gh api repos/AjTay10/AjT10-SSH` works. `gh search repos "..."` returns
`HTTP 403: This GitHub API path is not available: sessions are bound to their
configured repositories`. The skill's `references/dev.md` leads with `gh search`, so
`CLAUDE.md` redirects GitHub work to the `mcp__github__*` tools. Same root cause makes
`agent-reach check-update` fail permanently with a 403.

### 3. Concurrent fresh installs raced and aborted — FIXED

Two `install-agent-reach.sh` runs starting within 1s of each other on a clean
container: the first succeeded, the second failed both install sources and exited 1
with `FATAL: could not install agent-reach from any source`. Realistic because the
SessionStart hook runs the same script a user may run by hand. Fixed with an `flock`
re-exec guard; three concurrent fresh runs now all exit 0.

### 4. `agent-reach-verify.sh` reported success after running zero checks — FIXED

`./scripts/agent-reach-verify.sh bogus-name` printed `0 passed, 0 degraded, 0 failed`
and exited **0** — a typo in CI would have produced a green build that verified
nothing. Now validates names against the known set (exit 2) and refuses to report
success when no check ran. A `curl`/`jq`/`timeout` preflight was added at the same
time, since their absence previously surfaced as confusing per-channel failures.

Also fixed while testing the same script: the SessionStart hook was echoing `doctor`'s
channel list verbatim, which advertised the blocked `web` channel as working and
omitted the working `exa` channel. It now corrects both.

### 5. Upstream: `agent-reach install` prints raw Rich markup

`doctor.format_report()` returns Rich markup. `_cmd_doctor()` renders it with
`rich.print` (`cli.py:1988`), but the install path uses a plain `print()`
(`cli.py:427`), so `agent-reach install` dumps literal `[bold cyan]…[/bold cyan]`,
`[green]✅[/green]` and `[red][X][/red]` at the user. Cosmetic, reproducible on every
`install` run. One-line fix upstream: use the same `rich_print` in both paths.

### 6. Upstream: environment-dependent test failure

`tests/test_config.py::TestConfig::test_get_configured_features` fails whenever
`GITHUB_TOKEN` is set in the environment:

```
assert all(v is False for v in features.values())
E   assert False
```

`Config.get()` intentionally falls back to `os.environ[KEY.upper()]`, so a temp-dir
`Config` still reports `github_token: True`. Claude Code sets `GITHUB_TOKEN`, so the
suite is red here. The other **585 tests pass**. The test needs to clear the env, not
just the config path.

Side effect worth knowing: agent-reach considers a GitHub token configured because the
proxy sets `GITHUB_TOKEN=proxy-injected`, which is a placeholder rather than a usable
token.

### 7. Upstream: `agent-reach install`'s recommended source is unreachable here

`docs/install.md` recommends `pipx install
https://github.com/Panniantong/agent-reach/archive/main.zip`. That URL returns **403**
through this container's egress proxy, while `git+https://…agent-reach.git` clones
fine. The installer tries git first and falls back to the zip.

### 8. `reach` render crashed on Telegram output — FIXED

`render()` called `item.get()` before its `isinstance(item, str)` guard, so every
Telegram result raised `AttributeError: 'str' object has no attribute 'get'`. The
guard now comes first. Telegram was the only platform returning a list of strings
rather than dicts, which is exactly why it slipped through the doctor probe — the
probe checked the return value, not the rendering.

### 9. `reach doctor` reported working platforms as EMPTY — FIXED

The probe called any result under 40 serialised chars empty. The canonical X probe
is Jack Dorsey's `"just setting up my twttr"` (24 chars) and the Facebook probe's
description is 31 chars, so both healthy backends were reported broken. Threshold
dropped to 5 chars. A status check that cries wolf is worse than no status check.

### 10. Reddit fallback presented a block page as the thread — FIXED

For URLs Exa had only cached Reddit's *"You've been blocked by network security"*
page for, `reach reddit` returned that text as if it were the discussion. Now every
result block is screened, blocked ones are dropped, a reworded `site:reddit.com`
query is retried, and if only non-Reddit sources survive the output is prefixed with
an explicit `[note: … these are OTHER sites, not Reddit]` banner. Handing an agent a
block page as "what Reddit said" is a correctness bug, not a cosmetic one.

### 11. X returned 404 for every modern post — FIXED

The syndication endpoint needs a `token` query parameter. A placeholder works for
old ids (the 2006 test post) but modern ids 404, which made the backend look healthy
in the probe while failing on every real URL. `_x_token()` now reproduces the value
X's own embed script derives — `((id / 1e15) * π)` in base 36 with zeros and the
decimal point stripped — and falls back to the placeholder. Verified: post
`1587498907336118274` resolves with the derived token and 404s without it.

Deleted and restricted posts return HTTP 200 carrying a `TweetTombstone` rather than
an error, which produced a result with every field null. Those now raise with the
platform's own explanation ("This Post is unavailable").

## Security checks (all passed)

- **SSRF in `reach`**: `reach` accepts URLs, so it re-implements the same guard
  rather than trusting callers. `_validate_url()` rejects non-http(s) schemes,
  embedded credentials, `localhost`/`.internal`/`.local`, and — after resolving the
  host — any private, loopback, link-local, reserved, multicast or unspecified
  address. All 10 hostile URLs replayed against `reach web` (`file:///etc/passwd`,
  `127.0.0.1:22`, `169.254.169.254`, `[::1]`, `0x7f000001`,
  `metadata.google.internal`, `user:pass@`, `javascript:`, RFC1918) were rejected
  with exit 5.
- **Command injection**: `reach` shells out to `mcporter` and `yt-dlp`. Both use
  `subprocess.run` with an argument list and never a shell, verified with a canary
  file against `"; rm -f …`, `$(rm -f …)` and backtick payloads passed as search
  queries — the canary survived all three.
- **SSRF in agent-reach**: `normalize_public_http_url()` was fuzzed with 19 hostile inputs — `file://`,
  `gopher://`, `javascript:`, `localhost`, `127.0.0.1`, `[::1]`, RFC1918 ranges,
  `0.0.0.0`, the `169.254.169.254` cloud-metadata address,
  `metadata.google.internal`, decimal (`2130706433`) and hex (`0x7f000001`) encodings
  of loopback, embedded credentials, and CRLF header injection. **Every one was
  rejected.** Only ordinary public HTTP(S) URLs pass.
- **Secret handling**: `~/.agent-reach` is mode 700 and `config.yaml` mode 600.
  Passing a secret as a positional arg prints a deprecation warning pointing at
  `--stdin`. `doctor --json` does not echo stored secrets. A 2 MiB value via `--stdin`
  is rejected with `Configure value exceeds the 1 MiB safety limit`. A value containing
  newlines is YAML-quoted rather than injected as new config keys.
- **Non-destructive paths**: `agent-reach uninstall --dry-run` left `config.yaml`
  intact. `install --env=auto` (the default) made no system changes; `--system` was
  used only after the explicit request to install.
- **No credential harvesting**: no browser-cookie extraction was run and no platform
  login was attempted, per the upstream guide's auth boundaries.

## Robustness checks (all passed after the fixes above)

| Scenario | Result |
|----------|--------|
| Full teardown then reinstall from the committed script | clean install in 27s, verify identical (9/1/0) |
| Installer run twice | idempotent, ~11s, no re-download |
| 3 concurrent fresh installs | all exit 0 (post-lock) |
| Installer with a bogus `GH_CLI_VERSION` | aborts with exit 22, leaves no partial `gh` binary |
| Installer with an unknown flag | exit 2 with a usage message |
| Network outage (dead proxy) | all network checks fail in 3.4s, no hangs |
| `agent-reach skill --uninstall` then session start | hook re-registers the skill automatically |
| Verify script with a failing channel | exit 1, names the failure |
| Verify script without `jq` | exit 2 with a clear message |
| SessionStart hook, warm path | 5s, writes PATH into `$CLAUDE_ENV_FILE` |
| SessionStart hook when the installer fails | prints the log path, exits 0, never blocks the session |
| `reach --json` on all 12 content commands + doctor | every one emits valid JSON |
| `reach` with a dead proxy | falls through to Exa and still returns the page |
| `reach` with the whole network and Exa gone | exit 5, listing every backend it tried |
| `reach` unicode/emoji queries, 3 KB query | handled; the 3 KB query surfaces the API's own limit message |
| `reach` on missing channels/handles/posts | exit 5 with the platform's own reason ("Profile not found") |

## Enabling the credentialed channels

Not installed, because each needs something a headless container cannot supply. If the
user wants one, they must provide the credential themselves — do not attempt a login
or read their browser cookies.

| Channel | What the user must provide |
|---------|---------------------------|
| Twitter/X, Xueqiu | Cookie-Editor "Header String" export → `agent-reach configure twitter-cookies` |
| Xiaoyuzhou podcasts | free Groq API key → `agent-reach configure groq-key` (also needs `ffmpeg`) |
| Reddit, Facebook, Instagram, Xiaohongshu | a desktop Chrome session with the OpenCLI extension |
| LinkedIn | `mcporter config add linkedin …` plus an interactive browser login |

Then run `agent-reach install --env=auto --system --channels=<name>` and re-run
`./scripts/agent-reach-verify.sh`.
