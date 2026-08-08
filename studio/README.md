# Reportcraft

A single HTML file that turns a CSV export into a report you can hand a client.
Open `index.html` in any browser. No install, no account, no server — the
analysis runs in the tab and files never leave the machine.

```bash
python3 studio/build.py            # rebuild index.html from source
python3 studio/build.py --check    # fail if index.html is stale
```

## Why this shape

Distribution is the constraint. There is no outreach in this plan, so
customers have to arrive on their own — which means **the output has to be the
advertisement**. Someone builds a report *in order to send it to someone else*:
a client, a board, a buyer. That recipient is a business that also needs
reports, and the footer tells them what made it.

Sharing isn't a favour to ask for. It's the reason the tool gets opened.

Full reasoning, confidence, and kill criteria:
[`../business/decisions/0002-pull-only-reportcraft.md`](../business/decisions/0002-pull-only-reportcraft.md).

## What it computes

The same four things as the CLI in `tools/`:

- **Concentration** — Gini, effective count, top-N shares, and leave-one-out
  fragility. "Remove the top item and you lose 20%" is usually the whole risk.
- **Decay** — value by publish cohort, and whether new work performs like old
  work did. Production rising while yield falls is the finding no total shows.
- **Trend reality** — Theil–Sen trend baseline, robust MAD scoring, and CUSUM
  changepoints on the residuals. A sustained shift is a different event from a
  spike.
- **What it cannot establish** — printed in the report, every time.

## Layout

| File | Role |
|---|---|
| `engine.js` | Statistics. Pure functions, no DOM — this is the parity-tested part |
| `charts.js` | SVG drawing, theme-aware, no external references |
| `app.js` | File intake, column detection, report assembly, download |
| `template.html` | Shell with `{{PLACEHOLDER}}` slots |
| `style.css` | Tool chrome |
| `report.css` | Report only — a downloaded file carries this and nothing else |
| `build.py` | Inlines everything into `index.html`; `--check` for drift |
| `index.html` | **The product.** Built artifact, committed |

Sources are kept separate because a 2,000-line single file is unreadable and
unreviewable. The build stitches them together and refuses to emit anything
containing `http://`, `fetch(`, `@import`, or `<link>` — a single file that
phones home is not a single file.

## Testing

Three layers, because a browser port of existing statistics can fail in three
different ways.

**1. Parity — is the arithmetic right?**

```bash
python3 studio/parity_expected.py    # freeze what tools/ computes
node studio/parity.mjs               # check engine.js against it
```

`engine.js` is a second implementation of statistics that already exist in
`tools/`. Two implementations drift, and the drift is silent — the browser
would quietly disagree with the CLI on the same file, and the first person to
notice would be a client. This compares **214 values** across concentration,
vintages, trend detection, changepoints, and the primitives. It is why
`engine.js` carries comments like "Python indexes the midpoint here rather
than averaging the pair": those are not style notes, they are the parity
contract.

**2. Browser — can a person actually use it?**

```bash
node studio/browsertest.mjs [--screenshot out.png]
```

Loads the real `index.html`, feeds it the committed sample exports, checks
column auto-detection, finding order, chart count, the disclaimer, the
attribution, and the download. It also **fails the run if the page attempts
any network request**. Skips cleanly when Playwright is absent — the product
has no dependencies, only the test does.

**3. Build freshness** — `build.py --check` fails if `index.html` no longer
matches its sources, so editing `engine.js` without rebuilding cannot ship a
tool that differs from its own source.

## The paid tier

There is exactly one switch, `ATTRIBUTION_REQUIRED` in `app.js`. A licensed
build flips it and reads the branding field instead of stamping the credit.

**There is no billing in this build**, so the branding input is disabled with
a note saying why rather than pretending to be a feature that does nothing.
Building fake checkout would be the first dishonest thing in this repository.

## Data handling

Files are read with `FileReader` and held in memory for the life of the tab.
There is no upload because there is no server. The browser test enforces this
rather than the README merely claiming it.

Say this plainly to anyone who asks — the people most likely to use this are
handling a client's data and are right to be careful.
