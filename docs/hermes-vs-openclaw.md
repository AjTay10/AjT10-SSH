# Hermes Agent vs OpenClaw — measured comparison

Both were installed in this container and driven, rather than compared from their
websites. Versions tested: **Hermes Agent v0.20.0 (2026.8.3)** and **OpenClaw
2026.7.1-2**. Everything in the tables below is something that was run here on
2026-08-07, except where marked *(claimed)*.

## The one-paragraph answer

They are the same *kind* of thing — a self-hosted gateway that connects messaging
platforms to an AI agent, with cron, memory and skills — and they know it. Hermes's
MCP server source says it "matches OpenClaw's 9-tool MCP channel bridge surface";
OpenClaw ships a first-class `openclaw migrate hermes`. OpenClaw is the larger, more
production-shaped system with roughly 2.5× the channels, real sandboxing and a
built-in security auditor. Hermes is lighter to operate, has more bundled skills, and
is the one already installed and wired into this repo. **Neither solves web or social
access on its own** — both want paid API keys for that, and the `reach` layer in this
repo is what actually makes either of them useful against the major platforms.

## Measured head-to-head

| Axis | Hermes Agent | OpenClaw |
|------|--------------|----------|
| Runtime | Python 3.11 | Node.js ≥22.22.3 |
| Install command | `install.sh` | `npm install -g openclaw` |
| Install time here | **92s** | **32s** (plus a Node upgrade, below) |
| Code footprint | **2.0 GB** | **395 MB** |
| Total added to disk | 2.0 GB + 63 MB state | 594 MB (bundle + its own Node runtime) |
| MCP channel-bridge tools | **10** (`+channels_list`) | **9** |
| Claude Code integration | generic stdio MCP server, unscoped | **`openclaw attach`** — mints a TTL-bounded grant, writes `.mcp.json`, can spawn Claude Code |
| Configurable chat channels | Telegram, Discord, WhatsApp, Weixin, Signal, iMessage (BlueBubbles), MS Teams, QQ, Yuanbao | **25** in the config schema, 47 channel doc pages — adds Matrix, IRC, SMS, Twitch, Nostr, Mattermost, Google Chat, Line, Feishu, Zalo, Synology Chat, Tlon… |
| Bundled skills | **71** `SKILL.md` files | **51** bundled, **18** usable without extra setup |
| Skill format | `SKILL.md` (agentskills.io) | `SKILL.md` (agentskills.io) — interchangeable |
| Built-in security audit | no (`hermes doctor` is health only) | **yes** — `openclaw security audit` |
| Agent sandboxing | not first-class | **`openclaw sandbox`** — Docker-based isolation |
| Migration between them | — | **`openclaw migrate hermes --dry-run`**, previewed and reversible |
| Last upstream commit | within hours of testing | within hours of testing |
| Stars *(claimed)* | — | ~385k, fastest-growing OSS project of 2026 |

### What works with no LLM credential

This matters because a model provider is the one thing neither has here.

| | Hermes | OpenClaw |
|---|--------|----------|
| MCP bridge serves tools | ✅ | ✅ |
| Skills list / inspect | ✅ | ✅ |
| Cron scheduling | ✅ | ✅ |
| Health check | ✅ `hermes doctor` | ✅ `openclaw doctor` |
| Security audit | — | ✅ |
| **Send a message with no gateway and no agent loop** | ✅ **`hermes send`** works off bot tokens alone for Telegram/Discord/Slack/Signal | needs the gateway running |
| Agent loop / autonomous work | ❌ needs a provider | ❌ needs a provider |

`hermes send` is the sharpest practical difference today: it is a working
notification channel the moment you add a bot token, with no daemon and no model.

## Friction each one actually caused

**OpenClaw needed a Node upgrade.** Its engine floor is `>=22.22.3`; this container
ships **22.22.2** — short by one patch release. Node 24.15.0 had to be installed
first, which is where most of its 594 MB went. On a machine with current Node this is
a non-issue; in a pinned environment it is a real prerequisite.

**OpenClaw is not secure by default.** `openclaw security audit` on a fresh install
self-reports **1 critical, 2 warnings**:

```
CRITICAL gateway.loopback_no_auth — gateway.bind is loopback but no gateway auth
         secret is configured. If the Control UI is exposed through a reverse
         proxy, unauthenticated access is possible.
WARN     gateway.http.no_auth — gateway.auth.mode="none" leaves /tools/invoke
         callable without a shared secret.
```

Credit where due: it ships the auditor that finds this, and states its trust model
plainly — *"personal assistant (one trusted operator boundary), not hostile
multi-tenant on one shared gateway."* Hermes has no equivalent self-audit. But you
must configure `gateway.auth` before exposing OpenClaw anywhere.

**OpenClaw's gateway expects a service manager.** `openclaw doctor` here: *"systemd
user services are unavailable… if you're in a container, run the gateway in the
foreground instead."* Fine on a VPS, awkward in an ephemeral container.

**Hermes is 5× the code for fewer channels.** 2.0 GB against 395 MB, and its
`hermes doctor` reports npm audit advisories in its own bundled web/ui workspaces plus
an AWS Bedrock IAM error from probing a provider nobody configured. Noisy.

**Both are blind to the web without paid keys.** Hermes wants
`EXA_API_KEY`/`TAVILY_API_KEY`/`FIRECRAWL_API_KEY` and `XAI_API_KEY` for X. OpenClaw
wants Brave Search or Perplexity keys, and defaults memory search to OpenAI. The
`reach-social` skill in this repo already fixes this for Hermes; the identical trick
works for OpenClaw, since both read the same `SKILL.md` format.

## Which to run

**Stay on Hermes if** you want notifications and scheduled digests on Telegram,
Discord, Slack or WhatsApp. It is installed, QA'd, wired into `.mcp.json`, and
`hermes send` gives you a working notification path as soon as you add one bot token.
Nothing further to build.

**Move to OpenClaw if** any of these is true:
- you want a channel Hermes does not have — **iMessage, Signal, SMS, Matrix, Teams,
  IRC, Twitch, WeChat**
- you want the agent executing in a **Docker sandbox** rather than directly on the host
- you want **several isolated agents** with separate workspaces and routing
- you are putting this on a **VPS as a real service**, where the security auditor,
  scoped MCP grants and TTL'd tokens start to matter

**Do not run both against the same accounts.** Two clients on one Telegram bot token
will fight over updates, and OpenClaw's own migration doc warns: *"After importing
Hermes OAuth, do not keep Hermes and OpenClaw using the same refresh grant;
reauthenticate one side before running both."*

## The cheap path

Switching later costs very little, which is the strongest argument for not
agonising now:

```bash
openclaw migrate hermes --dry-run     # preview; nothing is written
openclaw migrate apply hermes --yes   # imports model config, MCP servers, SOUL.md,
                                      # AGENTS.md, memories, and every SKILL.md
```

It previews every change, redacts secrets in the plan, writes a verified backup, and
asks before importing credentials. So: get value out of Hermes first, and if you hit
its channel ceiling, migrate — the skills and memory come with you.

## Current state in this container

- **Hermes** — installed, wired, QA'd. `.mcp.json`, session hook, `reach-social` skill,
  `./scripts/hermes-verify.sh`. See `docs/hermes.md`.
- **OpenClaw** — installed for this comparison at
  `~/.local/node24/lib/node_modules/openclaw`, **parked**: no gateway running, no
  channels linked, no credentials, not registered with Claude Code. It costs disk and
  nothing else.

Remove it with:

```bash
npm --prefix ~/.local/node24 uninstall -g openclaw && rm -rf ~/.openclaw ~/.local/node24
```
