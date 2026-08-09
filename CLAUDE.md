# Operating manual

This repo is a Claude configuration: 28 skills, 11 tools, a validation hook,
and a QA gate. It is meant to be used, not read.

## Before you change anything

```bash
python3 qa/validate.py      # config integrity — must exit 0
python3 qa/selftest.py      # 139 adversarial tests — must exit 0
```

Both run in CI. A pull request that fails either does not merge.

## Layout

```
.claude/
  skills/<name>/SKILL.md    28 skills; directory name MUST equal frontmatter name
  agents/                   subagent definitions
  commands/                 /audit /usage /numbers /attack /gap
  hooks/validate_on_edit.py PostToolUse guard — catches a broken skill instantly
  settings.json             permissions, env, hooks
  data/                     graph.json, usage/ — the accumulated asset
tools/                      stdlib-only Python; no install step, ever
qa/                         validate.py (config), selftest.py (tools),
                            no_deps.py (the stdlib-only guarantee)
demo/                       worked example; report.html is a built artifact
studio/                     Reportcraft — the single-file browser tool
```

## Tools

Every tool is stdlib-only, reads CSV, and prints a table or `--json`.

| Tool | For |
|---|---|
| `chartkit.py` | theme-aware SVG charts, no dependencies, CSP-safe |
| `metrics.py` | funnel, retention, cohort, growth |
| `abtest.py` | significance, sample size, Bayesian read, peeking cost |
| `anomaly.py` | trend-aware robust anomaly and changepoint detection |
| `kg.py` | persistent knowledge graph |
| `social_ingest.py` | normalize platform exports into one schema |
| `dashboard.py` | self-contained HTML dashboard |
| `calendar_gen.py` | posting schedule → CSV + ICS |
| `concentration.py` | fragility and decay: what does the total rest on? |
| `csvio.py` | shared CSV reader: encoding fallback, header checks |
| `usage.py` | which skills, commands, and tools actually get used |

## Rules this repo enforces

**Stdlib only in `tools/`.** No pip install, ever. These have to run in a
fresh container, in CI, and on someone else's laptop without setup. If a
dependency seems necessary, it is not.

**Blank is not zero.** Throughout the data tools, `""` means "not reported"
and `0` means "reported as none". Collapsing them drags every rate down and
is invisible. Preserve the distinction in any new transform.

**Errors name the fix.** Every tool raises a typed error with a message that
says what was wrong and what to do. A traceback reaching the user is a bug and
`selftest.py` asserts against it.

**Cross-platform metrics are not comparable.** A TikTok view counts at 0
seconds, a YouTube view at ~30, X impressions include scroll-past. Compare
within a platform over time; compare across platforms only on owned outcomes.
Several tools print this warning rather than letting the number stand alone.

**Never fabricate a number.** Not a statistic, not a benchmark, not a citation.
"I could not find a reliable figure" is always an acceptable output.

## Adding a skill

1. `.claude/skills/<name>/SKILL.md`, where `<name>` matches the frontmatter
   `name` exactly. A mismatch means the skill silently never loads — the hook
   and the validator both check this.
2. The `description` must say **when to use it**, in third person, with the
   phrasings a user would actually type. A description that only says what the
   skill *is* will never trigger.
3. Cross-reference siblings in a `## Related` section. The validator checks
   those names resolve.
4. Re-run both QA commands.

## Adding a tool

1. Stdlib only. Shebang, module docstring with a usage example, `--json`
   where output feeds another tool.
2. A typed error class, caught in `main()`, printed to stderr, exit 2.
3. Tests in `qa/selftest.py` covering: empty input, one row, all-identical
   values, a missing column, a malformed value, and one correctness assertion
   on a known answer. Exit-code tests alone are not enough — a tool that
   returns confidently wrong numbers passes those.
4. Reference it from at least one skill, or nothing will ever invoke it.

## Conventions

- Deterministic output. No `Math.random`, no unseeded ordering — `kg.py` sorts
  everywhere so two runs of `clusters` agree.
- Atomic writes for anything persistent (`kg.py` writes to `.tmp` then
  `os.replace`), so a crash mid-write never truncates the store.
- `utf-8-sig` on every CSV read. A BOM silently corrupts the first column name
  otherwise, and platform exports frequently carry one.
