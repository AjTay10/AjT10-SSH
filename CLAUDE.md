# CLAUDE.md

## Internet access: Agent Reach

This repo has [Agent Reach](https://github.com/Panniantong/Agent-Reach) installed as a
Claude Code skill. The `.claude/hooks/session-start.sh` hook installs it and puts it on
PATH at the start of every session, so `agent-reach`, `yt-dlp`, `gh`, `bili` and
`mcporter` are available in Bash without any setup.

**Use these commands instead of guessing at scrapers or hand-rolled API calls.**
The `agent-reach` skill (`~/.claude/skills/agent-reach/SKILL.md`) carries the full
routing table; the table below is the subset that is verified working here.

## Social platforms and web pages: `reach`

Agent Reach's own routing assumes a desktop browser session and an unblocked
residential IP, and neither holds here. `reach` (see `.claude/skills/reach/SKILL.md`,
source `scripts/reach.py`) implements the paths that were measured to work, with a
fallback chain per platform. **Use it for every social platform and for reading any
web page.** `reach doctor` probes all 17 live in ~30s.

| Need | Command |
|------|---------|
| Read any web page/article | `reach web URL` |
| Semantic web search | `reach search "QUERY"` |
| X/Twitter post | `reach x URL_OR_ID` (search: `reach x "QUERY"`) |
| Reddit | `reach reddit "QUERY"` or `reach reddit URL` |
| Bluesky | `reach bluesky "QUERY"` / `--user HANDLE` |
| Mastodon | `reach mastodon TAG_OR_URL` |
| Telegram | `reach telegram CHANNEL` |
| TikTok / Instagram / Facebook | `reach tiktok\|instagram\|facebook URL_OR_QUERY` |
| LinkedIn / Threads / Pinterest | `reach linkedin\|threads\|pinterest URL_OR_QUERY` |
| YouTube | `reach youtube URL_OR_QUERY` |
| Wikipedia / HN / Stack Overflow | `reach wikipedia\|hn\|stackoverflow "QUERY"` |
| Platform status | `reach doctor` |

## Agent Reach's own channels

| Need | Command |
|------|---------|
| YouTube subtitles | `yt-dlp --write-sub --write-auto-sub --skip-download -o "/tmp/%(id)s" URL` |
| RSS/Atom | `~/.agent-reach-venv/bin/python -c "import feedparser; ..."` |
| V2EX | `curl -s https://www.v2ex.com/api/topics/hot.json -H 'User-Agent: agent-reach/1.0'` |
| Bilibili | `bili search "query" --type video -n 5` |
| GitHub repo/file/issues | `gh api repos/OWNER/REPO/...` — see limitation 2 below |
| Channel status | `agent-reach doctor` (config check only) |
| Real end-to-end check | `./scripts/agent-reach-verify.sh` (network check) |

### Two environment limitations — read before trusting `doctor`

1. **Jina Reader is blocked from this container's IP.** `curl https://r.jina.ai/URL`
   returns HTTP 401 `AuthenticationRequiredError: ... bad IP reputation`, and
   `agent-reach doctor` still reports the web channel green because
   `WebChannel.check()` deliberately never touches the network. **Use `reach web URL`**
   (direct fetch → Exa → Jina) or Claude Code's `WebFetch` tool. Anything in the
   agent-reach skill's `references/web.md` that says `curl r.jina.ai` does not work
   here. Same for V2EX *search*, which proxies through Jina; the V2EX topic/node APIs
   are direct and unaffected.

2. **The GitHub API is scoped to this session's repositories.** `gh api repos/OWNER/REPO`
   works for repos attached to the session; `gh search repos`, `gh search code` and any
   other cross-repo endpoint return `HTTP 403: ... sessions are bound to their
   configured repositories`. Use the `mcp__github__*` tools for GitHub work, and
   `mcp__Claude_Code_Remote__add_repo` to attach a repo first.

Two consequences of limitation 2 worth knowing, because the skill's own standing rules
tell you to run these:

- `agent-reach check-update` always fails here (`无法检查更新（GitHub 返回 403）`).
  Skip it; it is not a sign that anything is broken.
- `agent-reach doctor`'s green/amber marks are a *config* check, not a reachability
  check. It calls `web` green when it is blocked and refuses to call `exa` green when
  it works. Run `./scripts/agent-reach-verify.sh` when you need the truth.

Everything else in the table is verified live — see `docs/agent-reach.md` for the
per-channel test results and the full QA report.

### Platform coverage and its limits

`reach` reaches all 17 platforms anonymously, but not all of them yield full content.
Full text: web, Exa search, X posts, Bluesky, Mastodon, Telegram, YouTube, Wikipedia,
Hacker News, Stack Overflow. Metadata or search-index only: TikTok, Instagram,
Facebook, LinkedIn, Threads, Pinterest, Reddit. `reach` labels the degraded cases in
its output — **repeat that caveat to the user**; never present an Exa substitute as
"what Reddit said".

Agent Reach's own credentialed channels (Xiaohongshu, Xueqiu, Xiaoyuzhou, and the
cookie-based Twitter/Reddit backends) are still not installed: they need a cookie
export, a Groq key, or a desktop Chrome session. Do **not** try to log into any
platform or read a user's browser cookies. `docs/agent-reach.md` has the enable steps
if the user asks.

## Persistence, scheduling and messaging: Hermes Agent

[Hermes Agent](https://github.com/NousResearch/hermes-agent) v0.20.0 is installed
(`/usr/local/bin/hermes`, state in `~/.hermes/`). It is a separate agent runtime that
outlives this session. See `.claude/skills/hermes/SKILL.md`; `docs/hermes.md` has the
install record and QA report.

| Need | Use |
|------|-----|
| Read/send messages on Telegram, Discord, Slack, WhatsApp, Signal, Matrix | the `mcp__hermes__*` tools (registered via `.mcp.json`) |
| Work that must run with no session open | `hermes cron add ...` |
| Memory that outlives the session | `hermes memories ...`, `~/.hermes/SOUL.md` |
| A 70-skill library | `hermes skills list` / `search` / `install` |
| Move a skill between the two runtimes | `./scripts/hermes-sync-skills.sh --list` |
| Integration health | `./scripts/hermes-verify.sh` |

Two things to remember:

- **Hermes's own agent loop needs a model provider that is not configured.** The MCP
  bridge, skills, cron and memory all work without one. Do not run bare `hermes` or
  `hermes -z "..."` expecting output — check `hermes status` first. To enable it the
  *user* runs `hermes setup --portal` (or `hermes setup` for their own key); never
  handle their key yourself, and never read or write `~/.hermes/.env`.
- **Hermes's built-in `web` toolset is dead here** — it wants `EXA_API_KEY`,
  `TAVILY_API_KEY` or `FIRECRAWL_API_KEY`, and `x_search` wants `XAI_API_KEY`. The
  `reach-social` skill in `~/.hermes/skills/social-media/` points Hermes at the keyless
  `reach` CLI instead, so it has the same 17-platform coverage described above.

### Workspace hygiene

Agent Reach state lives in `~/.agent-reach/`, its venv in `~/.agent-reach-venv/`, and
scratch output belongs in `/tmp/`. Do not write tool output or cloned upstream repos
into this workspace.
