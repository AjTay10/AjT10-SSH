# Demo — a full pipeline run, end to end

A worked example of the analytics tools on three raw platform exports.
The finished page is [`report.html`](report.html).

```bash
python3 demo/build.py            # regenerate report.html from a real run
python3 demo/build.py --check    # fail if the committed page is stale
```

## What it demonstrates

Three synthetic exports are generated in each platform's **native** format —
different column vocabularies, different date formats, different encodings —
and put through `social_ingest → anomaly → abtest`, with `chartkit` drawing
the figures.

| File | Format quirks it carries |
|---|---|
| `youtube_studio_export.csv` | utf-8 **with BOM**, watch time in **hours**, `Video publish time` |
| `tiktok_export.csv` | utf-8, US date format, video views and **no impressions column** |
| `instagram_export.csv` | **cp1252** (a spreadsheet round-trip), reach *and* impressions |

One story is embedded so the tools have something real to find: YouTube reach
collapses on 12 May and never recovers, engagement rate holds flat across the
same boundary, and TikTok keeps growing through it. That combination —
collapsed reach, flat rate, one platform only — is a distribution failure
rather than a content failure, and the two need opposite investigations.

TikTok has its own unrelated changepoints in March and April. They are left in
deliberately: a demo where every detector agrees with the narrative is not
demonstrating detection.

## Why it is built rather than written

Every number and every terminal block on the page is captured from a live
subprocess run and substituted into `report.template.html`. There is no path by
which a figure in the copy can disagree with what the tools output, because no
figure is typed into the copy.

`--check` rebuilds into a temp directory and diffs against the committed page,
so CI fails if a change to any tool alters the output without the report being
regenerated.

## Reproducibility

`make_fixtures.py` is seeded. It uses `random.uniform` (arithmetic over
`random()`, stable across interpreter versions) and avoids `random.choice`,
whose selection strategy is an implementation detail — CI diffs this output
across Python 3.9 and 3.12, so anything version-sensitive would surface as a
false "stale report" failure.

Two consecutive builds are byte-identical.

## On the data

Synthetic and labeled as such on the page itself. It does not describe any real
account, brand, or organization, and the numbers should not be quoted as
benchmarks — they were chosen to exercise the tools, not to represent typical
performance.

The one figure that is *not* generated is the A/B result (`41/1180` vs
`58/1205`), which is a fixed illustrative input chosen because it looks like a
+38% win and does not survive a significance test.
