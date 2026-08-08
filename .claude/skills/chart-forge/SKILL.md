---
name: chart-forge
description: Produce charts and graphs as dependency-free, theme-aware SVG using tools/chartkit.py — line, bar, horizontal bar, stacked, donut, heatmap, scatter, and sparkline. Use when the user asks to chart, graph, plot, or visualize data, wants a figure for a report, dashboard, README, or Artifact, or when a table of numbers would be clearer as a picture. Also use to pick the right chart type for a given question.
---

# Chart forge

Charts answer a question. Pick the chart from the question, never from the
data's shape or from what looks impressive.

`tools/chartkit.py` emits self-contained SVG — no CDN, no fonts, no fetch —
so output drops straight into an Artifact under a strict CSP, a README, or an
HTML dashboard, and adapts to the viewer's light or dark theme automatically.

## Choose by question

| The question | Chart | Why |
|---|---|---|
| How did this change over time? | `line` | position over time is the strongest encoding |
| …and how do the parts contribute? | `area`, `stacked` | only when the total is meaningful |
| Which is biggest? (labels are words) | `hbar` | horizontal — words read horizontally |
| Which is biggest? (few, short labels) | `bar` | fine up to ~8 categories |
| How is one whole divided? | `donut` | **≤ 6 slices, parts of one whole, or use hbar** |
| Does X relate to Y? | `scatter` | the only honest way to show a relationship |
| Where is the density? | `heatmap` | day × hour, week × weekday, correlations |
| What is the trend, in one line of a tile? | `sparkline` | context without a full chart |

If you cannot state the question in one sentence, do not draw the chart yet.

## Commands

```bash
python3 tools/chartkit.py --type line --csv data.csv --x date --y views \
    --title "Views" --subtitle "last 90 days" --out chart.svg

# Multiple series: repeat --y
python3 tools/chartkit.py --type line --csv d.csv --x date --y views --y clicks

# Or split one value column into series by a category column
python3 tools/chartkit.py --type line --csv d.csv --x date --y views \
    --series-col platform --out by_platform.svg

python3 tools/chartkit.py --type hbar --csv d.csv --x platform --y er --unit "%"
python3 tools/chartkit.py --type stacked --csv d.csv --x week --y organic \
    --y paid --percent
python3 tools/chartkit.py --type scatter --csv d.csv --x length_sec --y er_pct
```

Pipe from stdin with `--csv -`. Omit `--out` to write SVG to stdout.

As a library, every function returns an SVG string:

```python
import sys; sys.path.insert(0, "tools")
import chartkit
svg = chartkit.line(dates, {"views": v, "clicks": c}, title="Reach")
tile = chartkit.sparkline(v)          # for stat tiles
```

## Rules that keep charts honest

**Bar charts start at zero. Always.** A truncated bar axis misstates the ratio,
which is the entire thing a bar chart encodes. Line charts may truncate — they
encode change, not magnitude — but say so when the truncation is aggressive.

**Never chart two platforms' "views" on one axis.** A TikTok view counts at
zero seconds; a YouTube view needs roughly thirty. Same word, different
events, and putting them on shared axes produces a chart that is wrong rather
than merely misleading. Use small multiples or index each series to its own
baseline.

**Sort horizontal bars by value, not alphabetically.** `hbar` does this by
default. Alphabetical order encodes nothing and wastes the reader's best
perceptual channel.

**Show gaps as gaps.** `chartkit` breaks the line at missing values rather
than interpolating across them. Do not fill missing data to make a line
continuous — an unbroken line through a two-week outage is a false claim.

**Label the last point.** Readers look at where a series ended.

**Under 6 slices or it is not a donut.** Beyond that, angles become
unreadable and `hbar` is strictly better. `chartkit.donut` rejects negative
values outright because a negative slice is meaningless.

**One idea per chart.** Two series comparing is one idea. Six series is a
table wearing a costume.

## Color

The palette in `chartkit.PALETTE` is a brand-neutral placeholder — swap the
hex values, keep the roles. The first four categorical hues stay distinguishable
under common color vision deficiency and in grayscale.

- **Categorical** (`--c0`…`--c7`) for unordered things: platforms, formats
- **Sequential** (`--s0`…`--s6`) for magnitude: heatmap density
- **`--pos` / `--neg`** for good/bad only, never for arbitrary categories

Never encode a quantity with hue alone; use position or length, and let color
carry identity.

## Theme

Colors are emitted as CSS custom properties, with the dark palette under
`prefers-color-scheme: dark`. Nothing needs doing for this to work. Use
`--theme light` or `--theme dark` only when pinning one palette, e.g. before
rasterizing to PNG.

## Failure modes it will catch for you

`chartkit` raises `ChartError` rather than drawing something wrong: series
length mismatched to the x axis, all-empty data, negative values in a donut
or a stack, a canvas too small for its own margins. Read the message — each
one names a real problem with the data, not with the call.

## Related

- `dataviz` skill — broader visual design system guidance
- `social-analytics` — full dashboard assembly from platform exports
- `metrics-lab` — computing the numbers before charting them
