# Reportcraft

A single HTML file that turns a CSV export into a readable report. Open
`index.html` in any browser — no install, no account, no server. The analysis
runs in the tab and files never leave the machine.

```bash
python3 studio/build.py --artifact   # rebuild index.html, artifact.html, docs/
python3 studio/build.py --check      # fail if any built copy is stale
```

## What it computes

The same four things as the CLI in `tools/`, because it is the same
arithmetic:

- **Concentration** — Gini, effective count, top-N shares, and leave-one-out
  fragility. "Remove the top item and you lose 20%" is usually the whole risk
  in one line.
- **Decay** — value by publish cohort, and whether new work performs like old
  work did. Production rising while yield falls is the finding no total shows.
- **Trend reality** — Theil–Sen trend baseline, robust MAD scoring, and CUSUM
  changepoints on the residuals. A sustained level shift is a different event
  from a spike.
- **What it cannot establish** — printed in the report, every time.

## Layout

| File | Role |
|---|---|
| `engine.js` | Statistics. Pure functions, no DOM — this is the parity-tested part |
| `charts.js` | SVG drawing, theme-aware, no external references |
| `app.js` | File intake, column detection, report assembly, export |
| `template.html` | Shell with `{{PLACEHOLDER}}` slots |
| `style.css` | Tool chrome |
| `report.css` | Report only — a downloaded file carries this and nothing else |
| `fixtures.py` | Seeded sample CSVs for the tests and for trying it out |
| `build.py` | Inlines everything; `--check` for drift |
| `index.html` | **The tool.** Built artifact, committed |
| `artifact.html` | Same page without the outer document tags, for embedding |

Sources are kept separate because a 2,000-line single file is unreadable and
unreviewable. The build stitches them together and refuses to emit anything
containing `http://`, `fetch(`, `@import`, or `<link>` — a single file that
phones home is not a single file.

## Testing

Three layers, because a browser port of existing statistics can fail in three
different ways.

**1. Parity — is the arithmetic right?**

```bash
python3 studio/fixtures.py           # seeded sample data
python3 studio/parity_expected.py    # freeze what tools/ computes
node studio/parity.mjs               # check engine.js against it
```

`engine.js` is a second implementation of statistics that already exist in
`tools/`. Two implementations drift, and the drift is silent — the browser
would quietly disagree with the CLI on the same file, and you would not find
out from either of them. This compares **214 values** across concentration,
vintages, trend detection, changepoints, and the primitives. It is why
`engine.js` carries comments like *"Python indexes the midpoint here rather
than averaging the pair"*: those are not style notes, they are the contract.

**2. Browser — can a person actually use it?**

```bash
node studio/browsertest.mjs [--screenshot out.png]
```

Loads the real `index.html`, feeds it the fixtures, checks column
auto-detection, finding order, chart count, the disclaimer, and the export. It
also **fails the run if the page attempts any network request**. Skips cleanly
when Playwright is absent — the tool has no dependencies, only the test does.

**3. Build freshness** — `build.py --check` fails if any built copy no longer
matches its sources, so editing `engine.js` without rebuilding cannot ship a
tool that differs from its own source.

## Hosting

`docs/index.html` is a byte-identical copy served by GitHub Pages. Enable it
once — *Settings → Pages → Source: GitHub Actions* — and every push
republishes. The deploy workflow refuses to publish a stale build or one that
could reach the network.

You do not need any of that to use it. Downloading `index.html` and opening it
works identically, including offline.

## Data handling

Files are read with `FileReader` and held in memory for the life of the tab.
There is no upload because there is no server. The browser test enforces this
rather than the README merely claiming it.

## Honest limits

The report states these itself, and they are worth repeating here:

- It computes descriptive statistics. It is not a valuation, an audit, or
  investment advice.
- It cannot tell you whether the numbers you feed it are true — only what they
  imply if they are.
- Sections are omitted rather than faked when their input is missing, and the
  omission is declared. A gap you can see is worth more than a section that
  was invented.
