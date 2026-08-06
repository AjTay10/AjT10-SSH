# CLAUDE.md

## Internet access: Agent Reach

This repo has [Agent Reach](https://github.com/Panniantong/Agent-Reach) installed as a
Claude Code skill. The `.claude/hooks/session-start.sh` hook installs it and puts it on
PATH at the start of every session, so `agent-reach`, `yt-dlp`, `gh`, `bili` and
`mcporter` are available in Bash without any setup.

**Use these commands instead of guessing at scrapers or hand-rolled API calls.**
The `agent-reach` skill (`~/.claude/skills/agent-reach/SKILL.md`) carries the full
routing table; the table below is the subset that is verified working here.

| Need | Command |
|------|---------|
| Semantic web search | `mcporter call exa.web_search_exa query="..." numResults=5` |
| Read a web page | **the `WebFetch` tool** — see limitation 1 below |
| GitHub repo/file/issues | `gh api repos/OWNER/REPO/...` — see limitation 2 below |
| YouTube metadata | `yt-dlp --skip-download --dump-json URL` |
| YouTube subtitles | `yt-dlp --write-sub --write-auto-sub --skip-download -o "/tmp/%(id)s" URL` |
| RSS/Atom | `~/.agent-reach-venv/bin/python -c "import feedparser; ..."` |
| V2EX | `curl -s https://www.v2ex.com/api/topics/hot.json -H 'User-Agent: agent-reach/1.0'` |
| Bilibili | `bili search "query" --type video -n 5` |
| Channel status | `agent-reach doctor` (config check) |
| Real end-to-end check | `./scripts/agent-reach-verify.sh` (network check) |

### Two environment limitations — read before trusting `doctor`

1. **Jina Reader is blocked from this container's IP.** `curl https://r.jina.ai/URL`
   returns HTTP 401 `AuthenticationRequiredError: ... bad IP reputation`. Agent Reach
   has no other backend for generic web pages, and `agent-reach doctor` still reports
   the web channel green because `WebChannel.check()` deliberately never touches the
   network. **Use Claude Code's built-in `WebFetch` tool for arbitrary web pages.**
   Anything in the skill's `references/web.md` that says `curl r.jina.ai` does not work
   here. This also degrades the LinkedIn fallback and V2EX *search* (V2EX topic/node
   APIs are direct and unaffected).

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

### Channels that are deliberately NOT installed

Twitter/X, Reddit, Xiaohongshu, Facebook, Instagram, Xueqiu, Xiaoyuzhou and LinkedIn
all require either a user-supplied credential (cookie export, Groq API key) or a
desktop Chrome session via the OpenCLI extension, neither of which exists in a headless
container. Do **not** try to log into these platforms or scrape a user's cookies.
If the user wants one, `docs/agent-reach.md` has the enable steps.

### Workspace hygiene

Agent Reach state lives in `~/.agent-reach/`, its venv in `~/.agent-reach-venv/`, and
scratch output belongs in `/tmp/`. Do not write tool output or cloned upstream repos
into this workspace.
