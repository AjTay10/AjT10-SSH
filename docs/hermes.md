# Hermes Agent integration — install record and QA report

[Hermes Agent](https://github.com/NousResearch/hermes-agent) v0.20.0 (Nous Research) is
installed and wired into Claude Code. This document records what was installed, how the
two runtimes connect, and what broke while trying to break it.

Note on naming: `hermes.ai` is a domain marketplace, not this product. The AI agent
called Hermes is Nous Research's, at `hermes-agent.nousresearch.com`.

## What Hermes adds that Claude Code does not have

Claude Code is a session: it starts, works, and ends. Hermes is a resident process with
its own state. The integration is worth having for three things:

1. **Messaging in and out** — a bridge to Telegram, Discord, Slack, WhatsApp, Signal
   and Matrix, exposed to Claude Code as MCP tools.
2. **Scheduling** — `hermes cron` runs work when no session is open. Claude Code's own
   Routines wake *a conversation*; Hermes cron runs *without* one.
3. **Persistent memory and a 70-skill library** that survive between sessions.

## What is installed

| Component | Location |
|-----------|----------|
| Hermes Agent v0.20.0 | code `/usr/local/lib/hermes-agent`, command `/usr/local/bin/hermes` |
| State, config, skills, cron, sessions | `~/.hermes/` (mode 700; `.env` mode 600) |
| 67 bundled skills | `~/.hermes/skills/<category>/<name>/SKILL.md` |
| `reach-social` skill | `~/.hermes/skills/social-media/reach-social/` |
| MCP registration | `.mcp.json` → `hermes mcp serve` |

| Repo file | Role |
|-----------|------|
| `scripts/install-hermes.sh` | idempotent, locked installer + wiring; `--check`, `--wire-only` |
| `scripts/hermes-verify.sh` | live integration checks, including a real MCP handshake |
| `scripts/hermes-sync-skills.sh` | moves a `SKILL.md` between Hermes and Claude Code |
| `scripts/hermes-skills-audit.py` | what each of the 71 skills actually needs to run |
| `integrations/hermes/skills/.../reach-social/SKILL.md` | source of truth for the skill installed into Hermes |
| `.claude/skills/hermes/SKILL.md` | tells Claude when to reach for Hermes |
| `.mcp.json` | registers the messaging bridge |

Installed with `--skip-setup` (never consume a credential in an automated install) and
`--skip-browser` (this container already ships Chromium at `$PLAYWRIGHT_BROWSERS_PATH`;
a second copy would waste ~300 MB of a fixed disk allowance).

## How the two runtimes connect

**Hermes → Claude Code, over MCP.** `hermes mcp serve` is a stdio MCP server exposing
10 tools: `conversations_list`, `conversation_get`, `messages_read`,
`attachments_fetch`, `events_poll`, `events_wait`, `messages_send`,
`permissions_list_open`, `permissions_respond`, `channels_list`. `.mcp.json` registers
it, so they appear in-session as `mcp__hermes__*`. **Verified live**: the tools showed
up in this session's tool list after registration.

They return empty until the user links a platform (`hermes gateway install`, then
`hermes whatsapp` / `hermes slack` / etc.). Empty means "not linked", not "broken".

**Claude Code → Hermes, over skills.** Both runtimes read the same `SKILL.md` format
(the agentskills.io convention), so a skill written for one is readable by the other.
`scripts/hermes-sync-skills.sh` makes that explicit. Syncing is deliberately manual and
one skill at a time: mirroring all 67 Hermes skills into Claude Code would flood the
skill list and change which skill wins a trigger.

**Both → the platforms.** Hermes's built-in `web` toolset needs `EXA_API_KEY`,
`PARALLEL_API_KEY`, `TAVILY_API_KEY` or `FIRECRAWL_API_KEY`, and `x_search` needs
`XAI_API_KEY`. None exist here, so Hermes shipped with no working web access at all.
The `reach-social` skill routes it to the keyless `reach` CLI instead, giving Hermes the
same 17-platform coverage as the Claude session. Its own social-media category
otherwise contains exactly one skill (`xurl`), which needs X API credentials.

## Skill readiness — 53 of 71 usable

Hermes registers all 71 bundled skills as `enabled` whether or not their
dependencies exist, so `hermes skills list` cannot tell you what actually runs.
`./scripts/hermes-skills-audit.py` answers that, and the installer now satisfies
everything that can be satisfied without a credential.

| Bucket | Count | Meaning |
|--------|-------|---------|
| **READY** | **53** | every prerequisite present |
| NEEDS-CRED | 4 | an API key only the user has |
| NEEDS-BIN | 8 | blocked on an account, hardware, or a build failure |
| NEEDS-GPU | 2 | wants a multi-GB ML stack |
| INCOMPATIBLE | 4 | macOS-only (`imessage`, `findmy`, `apple-notes`, `apple-reminders`) |

Installed to get there — into the **system `python3`**, because that is the
interpreter a skill's own `python script.py` runs, not any venv:

- documents: `pypdf`, `pdfplumber`, `reportlab`, `pymupdf`, `pymupdf4llm`,
  `python-docx`, `python-pptx`, `openpyxl`, `pandas`, `defusedxml`, `nano-pdf`
- OCR/raster: `pytesseract`, `pdf2image` + the `tesseract-ocr` and
  `poppler-utils` binaries they shell out to
- research: `semanticscholar`, `arxiv`, `habanero`, `scipy`, `numpy`,
  `matplotlib`, `SciencePlots`
- misc: `pyfiglet`, `youtube-transcript-api`, `debugpy`, `remote-pdb`,
  `websocket-client`, `pygount`, `blogwatcher-cli`, `songsee`

Verified functionally, not just by import: generate a PDF with reportlab → read
it back with pypdf → rasterise with pdf2image → OCR with pytesseract returns the
original string.

### What is still blocked, and why

| Skill | Blocker | Who can unblock it |
|-------|---------|--------------------|
| `notion`, `airtable`, `gif-search` | `NOTION_API_KEY`, `AIRTABLE_API_KEY`, `TENOR_API_KEY` | user (free keys) |
| `teams-meeting-pipeline` | `MSGRAPH_*` tenant/client/secret | user (Azure app registration) |
| `himalaya` | an IMAP/SMTP account | user — binary install is trivial once wanted |
| `xurl` | X API credentials | user — but `reach x` already reads X without them |
| `weights-and-biases` | a W&B account | user |
| `openhue` | a Philips Hue **bridge on the LAN** | nobody — no credential fixes a headless container |
| `comfyui`, `serving-llms-vllm`, `llama-cpp`, `evaluating-llms-harness` | GPU + multi-GB torch/vLLM stacks | needs different hardware |
| `ocr-and-documents` (partial) | only the optional `marker-pdf` ML path | the rest of the skill works |
| `manim-video` | `srt` wheel fails to build here | upstream packaging |
| 4 Apple skills | macOS-only APIs | needs a Mac |

Nothing above was papered over by installing a binary whose account is still
missing — that would flip the audit to READY while leaving the skill unusable.

`hermes-verify.sh` now fails if readiness drops below 53, so a container rebuild
that silently loses these packages is caught rather than discovered mid-task.

## The one thing that needs the user

Hermes's autonomous loop — `hermes`, `hermes -z "prompt"`, and cron jobs that actually
*think* — needs a model provider. That is a credential only the user can supply:

```bash
hermes setup --portal   # Nous Portal OAuth: model + web search + image gen + TTS + browser
hermes setup            # or bring your own key (Anthropic, OpenAI, OpenRouter, ...)
```

Everything else works without it. The installer deliberately does not run this, the
session hook says so on every start, and the Claude-side skill tells Claude not to
invoke the loop until `hermes status` says a model is set.

## QA findings

### 1. `install-hermes.sh --check` reported the version and "not installed" — FIXED

`$(have hermes && hermes --version | head -1 || echo 'not installed')`: `hermes`
prints several lines, `head -1` closes the pipe, `hermes` dies of SIGPIPE, the pipeline
exits non-zero, and `||` fires — so the report printed the version it had just found
followed by `not installed`. Now captured whole, then trimmed. The whole repo was
grepped for the same pattern; no other instance.

### 2. `hermes-sync-skills.sh` wrote outside the skills tree — FIXED (security)

`--to-hermes reach ../../../tmp/evil` exited **0** and created `/tmp/evil/reach/SKILL.md`.
The category argument was interpolated straight into the destination path, so any
caller-supplied string could escape `~/.hermes/skills`. Both the skill name and the
category are now validated against `[A-Za-z0-9._-]+` with leading dots rejected;
`/etc`, `.`, `../x` and the original payload are all refused with exit 1, and the
legitimate `--to-hermes reach social-media` still works.

### 3. Our skill name collided with a registry skill — FIXED

The skill was first installed as `reach`. `hermes skills inspect reach` resolved to a
*different* `reach` from the clawhub registry ("Agent web interface… solve CAPTCHAs"),
so anyone running `hermes skills install reach` would silently get the wrong one.
Renamed to `reach-social`, which resolves unambiguously.

### 4. `hermes mcp serve` drops its last response on an immediate stdin EOF — worked around

The MCP check failed intermittently: roughly one run in three, `initialize` came back
but `tools/list` did not, and stderr carried
`BrokenPipeError: [Errno 32] Broken pipe` from the MCP SDK's `stdout_writer`. The
server tears down the moment stdin reaches EOF and can lose an in-flight write on the
way out. Confirmed flaky by repetition — three consecutive `hermes-verify.sh mcp` runs
gave PASS, PASS, FAIL against an unchanged install.

This does not affect Claude Code, which holds the pipe open for the life of the
session; it only bites short-lived probes like this one. The verifier now holds stdin
open briefly and retries up to three times, and is stable across five consecutive runs.
Worth reporting upstream, but not worth a local patch.

A flaky check is worse than no check — it trains you to ignore a red result. That is
why this got run twenty times rather than re-run once and declared fine.

### 5. `hermes doctor` exits non-zero for things this repo does not own

Its report includes npm audit advisories in Hermes's own bundled `web`, `ui-tui` and
`agent-browser` workspaces, plus an AWS Bedrock `ListFoundationModels` IAM error from
probing a provider that is not configured. `hermes-verify.sh` therefore asserts that
doctor *runs and renders*, and grades outstanding issues as degraded rather than
failed — otherwise the check would be permanently red for upstream's reasons.
`hermes doctor --fix` is run by the installer and clears the mechanical items
(config migration, the `~/.local/bin` symlink); it does not touch the rest.

## Robustness checks (all passed)

| Scenario | Result |
|----------|--------|
| Full teardown (`~/.hermes`, `/usr/local/lib/hermes-agent`, the binary) then reinstall | clean install in 92s, verify identical (7 passed / 1 degraded / 0 failed) |
| Installer run twice | idempotent, 0.9s, no re-download |
| 3 concurrent `--wire-only` runs | all exit 0 (flock re-exec guard) |
| Unknown flag | exit 2 with a usage message |
| `.mcp.json` pointing at a non-existent binary | verify FAILs and names it |
| `.mcp.json` with the hermes server removed | verify FAILs |
| `reach-social` deleted from `~/.hermes/skills` | both `reach-skill` and `skill` checks FAIL |
| `.env` chmod 644 | verify FAILs; installer repairs it to 600 |
| `~/.hermes` chmod 755 | verify FAILs; installer repairs it to 700 |
| `hermes-verify.sh` with an unknown check name | exit 2, lists valid names |
| MCP stdio handshake | `initialize` returns serverInfo, `tools/list` returns all 10 |

## Security posture

- The official installer was **downloaded and reviewed before execution**, not piped
  straight into a shell. `scripts/install-hermes.sh` keeps that property: it fetches to
  a temp file, rejects a download that is truncated or lacks a shebang, and only then
  runs it.
- No credential was consumed, created or read. `hermes setup` is never invoked
  automatically, `~/.hermes/.env` is never read or written by this repo's scripts —
  only its mode is asserted.
- `~/.hermes` is 700 and `.env` is 600, enforced on every installer run and checked by
  the verifier.
- The skill-sync bridge validates every path component (finding #2).
- Upstream's own npm audit advisories are reported, not silently suppressed.
