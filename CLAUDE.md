# Operating manual

This repo is a Claude configuration: 28 skills, 11 tools, a validation hook,
and a QA gate — plus Reportcraft, a single-file browser port of the analysis
tools. It is meant to be used, not read.

## Before you change anything

```bash
python3 qa/validate.py      # config integrity — must exit 0
python3 qa/selftest.py      # 139 adversarial tests — must exit 0
```

Both run in CI on **Python 3.9 and 3.12** — 3.9 is the floor the tools claim
to support, so nothing newer than 3.9 syntax/stdlib in `tools/` or `qa/`.
A pull request that fails either does not merge.

CI (`.github/workflows/qa.yml`) also gates on:

```bash
python3 qa/no_deps.py           # tools/ imports nothing that needs installing
python3 demo/build.py --check   # committed demo/report.html is not stale
python3 studio/build.py --check # committed studio builds match their sources
node studio/parity.mjs          # studio engine.js agrees with tools/ (214 values)
```

If you change a tool's arithmetic or any `studio/` source, regenerate the
built artifacts (`python3 demo/build.py`, `python3 studio/build.py --artifact`,
`python3 studio/fixtures.py`, `python3 studio/parity_expected.py`) and commit
them, or CI fails on freshness.

## Layout

```
.claude/
  skills/<name>/SKILL.md    28 skills; directory name MUST equal frontmatter name
  agents/                   subagent definitions (contrarian, social-analyst)
  commands/                 /audit /usage /numbers /attack /gap
  hooks/validate_on_edit.py PostToolUse guard — catches a broken skill instantly
  settings.json             permissions, env, hooks
  data/                     graph.json (kg.py store, via KG_STORE), usage/
tools/                      stdlib-only Python; no install step, ever
qa/                         validate.py (config), selftest.py (tools),
                            no_deps.py (the stdlib-only guarantee)
demo/                       worked example; report.html is a built artifact
studio/                     Reportcraft — the single-file browser tool
docs/                       byte-identical copy of studio/index.html for Pages
install.sh                  symlink the config into ~/.claude; idempotent,
                            never overwrites, --copy/--dry-run/--uninstall
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
dependency seems necessary, it is not. `qa/no_deps.py` fails the build on
any import the standard library (or a sibling in `tools/`) cannot satisfy.

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

**Built artifacts are committed and checked, never hand-edited.**
`demo/report.html`, `studio/index.html`, `studio/artifact.html`, and
`docs/index.html` are build outputs. Edit the sources and rebuild; every
number in the demo page is captured from a live subprocess run, so no figure
in the copy can disagree with what the tools output.

**Nothing reaches the network.** Reportcraft's promise is that data never
leaves the machine. The studio build refuses to emit anything containing
`http://`, `fetch(`, `@import`, or `<link>`; the Pages deploy re-checks; the
browser test fails on any attempted request. Do not add external references.

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

1. Stdlib only, Python 3.9-compatible. Shebang, module docstring with a usage
   example, `--json` where output feeds another tool.
2. A typed error class, caught in `main()`, printed to stderr, exit 2.
3. Tests in `qa/selftest.py` covering: empty input, one row, all-identical
   values, a missing column, a malformed value, and one correctness assertion
   on a known answer. Exit-code tests alone are not enough — a tool that
   returns confidently wrong numbers passes those.
4. Reference it from at least one skill, or nothing will ever invoke it.

## Touching the studio

`studio/engine.js` is a second implementation of statistics that already
exist in `tools/`, and two implementations drift silently. The parity test
freezes what `tools/` computes (`parity_expected.py` → `parity_expected.json`)
and checks `engine.js` against it. Comments in `engine.js` like *"Python
indexes the midpoint here rather than averaging the pair"* are the contract,
not style notes. Change the arithmetic on one side and you must change it on
both, regenerate the expected values, and rebuild.

## Conventions

- Deterministic output. No `Math.random`, no unseeded ordering — `kg.py` sorts
  everywhere so two runs of `clusters` agree. Demo fixtures use seeded
  `random.uniform` (stable across interpreter versions) and avoid
  `random.choice`, whose strategy is an implementation detail — CI diffs the
  output across 3.9 and 3.12.
- Atomic writes for anything persistent (`kg.py` writes to `.tmp` then
  `os.replace`), so a crash mid-write never truncates the store.
- `utf-8-sig` on every CSV read. A BOM silently corrupts the first column name
  otherwise, and platform exports frequently carry one.
- `.claude/settings.json` allowlists read-only git and the repo's own Python;
  it denies `curl`/`wget`, force pushes, and reads of `.env`/secrets. Work
  within that, not around it.
