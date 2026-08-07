---
name: hermes
description: >
  Hermes Agent (Nous Research) is installed here as a persistent, self-hosted
  agent that survives between Claude Code sessions. Use it when the user wants
  something REMEMBERED across sessions, something to RUN ON A SCHEDULE while
  nobody is watching, or a MESSAGE read from or sent to Telegram, Discord,
  Slack, WhatsApp, Signal or Matrix.
  Triggers: "remember this", "keep track of", "every morning/day/week",
  "schedule", "cron", "recurring", "notify me", "message me on Telegram",
  "what did X say in Slack", "run this in the background", "check on this
  later", "hermes", "skills library", "install a skill".
  NOT for: reading web pages or social platforms — that is the `reach` skill.
  NOT for: writing code in this repo — do that directly.
---

# Hermes Agent

`hermes` is on PATH (`/usr/local/bin/hermes`, code in
`/usr/local/lib/hermes-agent`, state in `~/.hermes/`). It is a separate agent
runtime, not a library: think of it as a colleague that stays running after
this session ends.

## What it gives you that Claude Code alone does not

| Capability | Command |
|------------|---------|
| Cross-session memory | `hermes memories list`, and the `SOUL.md` profile in `~/.hermes/` |
| Scheduled/background work | `hermes cron list`, `hermes cron add ...` |
| Messaging in and out | the `hermes` MCP tools (see below), `hermes send ...` |
| A 70+ skill library | `hermes skills list`, `hermes skills search QUERY` |
| Health of all of the above | `hermes doctor` |

## MCP tools (already wired)

`.mcp.json` registers `hermes mcp serve`, so the messaging bridge is available
to you directly as MCP tools — no shell needed:

`conversations_list`, `conversation_get`, `messages_read`, `attachments_fetch`,
`events_poll`, `events_wait`, `messages_send`, `permissions_list_open`,
`permissions_respond`, `channels_list`.

Use these to read what someone said in a linked chat, or to send the user a
message where they actually are. They return empty until the user links a
platform (`hermes gateway install`, then e.g. `hermes whatsapp` / `hermes
slack`) — an empty conversation list means "not linked yet", not "broken".

## The one thing that needs the user

Hermes's own agent loop (`hermes`, `hermes -z "prompt"`, autonomous cron jobs)
needs a model provider, which needs a credential this container does not have.
Everything above — MCP bridge, skills, cron scheduling, memory storage, doctor
— works without it.

To enable the loop, the user runs **one** of:

```bash
hermes setup --portal          # Nous Portal OAuth: model + web search + images + TTS + browser
hermes setup                   # or bring your own key (Anthropic, OpenAI, OpenRouter, ...)
```

Offer this when a request actually needs autonomous execution. Do not ask for
or handle their key yourself — `hermes setup` prompts for it directly.

## Web and social access

Hermes's built-in `web` toolset wants `EXA_API_KEY` / `TAVILY_API_KEY` /
`FIRECRAWL_API_KEY`, and `x_search` wants `XAI_API_KEY`. None are configured.
A `reach-social` skill is installed into `~/.hermes/skills/social-media/` that
points Hermes at the keyless `reach` CLI instead, so Hermes has the same
17-platform coverage this session does.

## Rules

1. **Do not run `hermes` (bare) or `hermes -z`** expecting output until a model
   provider is configured — it will fail. Check with `hermes status` first.
2. **Never write to `~/.hermes/.env`** or echo its contents; it holds the
   user's API keys.
3. Scheduling: prefer `hermes cron` for work that must run when no session is
   open. For work that should wake *this* conversation, use Claude Code's own
   Routines instead.
4. Skills are interchangeable: both Hermes and Claude Code read `SKILL.md`.
   `scripts/hermes-sync-skills.sh --list` shows what each side has.
5. `hermes doctor` reports npm audit advisories in its bundled web/ui
   workspaces. They are upstream's, not something to fix in this repo.

## Verify

`./scripts/hermes-verify.sh` runs live checks: CLI, doctor, MCP handshake and
tool list, skill discovery, and state directory permissions.
