---
name: data-clean
description: Profile and clean messy CSV or spreadsheet exports before analysis — encodings, mixed date formats, duplicates, silent type coercion, and the specific ways platform exports lie. Use when the user hands over a raw export, when analysis produces suspicious numbers, when a file will not parse, or before any charting or metrics work on unfamiliar data. Also use when totals do not match a platform's own dashboard.
---

# Data clean

Analysis on unprofiled data produces confident wrong answers. Profile first,
always — it takes two minutes and catches the problems that would otherwise
be discovered after the conclusion has been presented.

## Profile before anything else

```bash
head -3 file.csv                       # real headers, real delimiter
file file.csv                          # encoding
wc -l file.csv                         # rows vs what the platform claimed
python3 tools/social_ingest.py --inspect file.csv   # column mapping + samples
```

For a quick column-level profile:

```python
import csv, collections
rows = list(csv.DictReader(open("file.csv", encoding="utf-8-sig")))
print(len(rows), "rows")
for col in rows[0]:
    vals = [r[col] for r in rows]
    blank = sum(1 for v in vals if not str(v).strip())
    uniq = len(set(vals))
    print(f"{col:<32} blank={blank:<6} unique={uniq:<7} sample={vals[0]!r}")
```

Look for: a column that is 90% blank (the export has it but does not populate
it), a "unique" count of 1 (constant, useless), and a unique count equal to
the row count on something that should repeat (an id where you expected a
category).

## The problems that actually occur

**BOM at the start of the file.** A UTF-8 BOM makes the first column name
`﻿Date` instead of `Date`, so every lookup on it fails with a confusing
"column not found". Always open with `encoding="utf-8-sig"`. Every tool in
`tools/` already does.

**Mixed date formats in one column.** Platform exports change format across
locale or across an export version boundary. `03/04/2026` is March 4th or
April 3rd depending on the exporter, and nothing in the file tells you which.
Check for any day value above 12 to disambiguate; if none exists in the whole
column, say so rather than guessing.

**Numbers stored as text.** `1,234`, `12%`, `$1.2k`, `(300)` for negative,
`1.2K`, and `—` for zero all appear in real exports. Naive `float()` throws
on every one. `chartkit._num` and `social_ingest.to_num` handle these; do not
re-implement.

**Excel has already corrupted it.** If the file passed through a spreadsheet:
leading zeros gone from IDs and postcodes, long IDs converted to scientific
notation (`1.23457E+15` — the original digits are *destroyed*, not hidden),
and anything resembling a date silently converted. If IDs look like floats,
go get the original export; this is not repairable.

**Duplicate rows.** Exports frequently repeat rows across pagination
boundaries. Deduplicate on a genuine key before counting anything:

```python
seen, clean = set(), []
for r in rows:
    k = (r["post_id"], r["date"])
    if k not in seen:
        seen.add(k); clean.append(r)
print(f"{len(rows) - len(clean)} duplicate rows removed")
```

**Timezone drift.** A platform exporting in UTC while the user thinks in
local time smears every daily boundary. Symptom: a weekly pattern that looks
shifted by one day, or activity appearing at implausible hours.

**Blank vs zero.** These mean different things and conflating them is the
most damaging silent error here. A blank impressions field means *not
reported*; zero means *reported as none*. Averaging blanks as zeros drags
every rate down. The tools in this repo keep blank as `""` deliberately —
preserve that distinction through your own transforms.

**Aggregate rows mixed into detail rows.** Some exports append a "Total" row.
It will be counted as a post, inflate every sum by exactly 2x, and look
plausible. Check whether the last row's values equal the sum of the others.

## Reconcile before you analyze

Take one number the platform's own dashboard displays and reproduce it from
the file. If total impressions in the CSV do not match the dashboard, stop —
the export is filtered, paginated, deduplicated, or windowed differently than
you assume, and every downstream number will be wrong in a way that is
invisible.

This single check catches more errors than all the others combined.

## Cleaning order

1. Fix encoding, delimiter, and header row
2. Drop aggregate/total rows
3. Deduplicate on a real key
4. Parse dates into ISO, flagging ambiguity rather than guessing
5. Coerce numerics, keeping blank distinct from zero
6. Reconcile a known total against the source dashboard
7. Only then analyze

## Document what you changed

Every cleaning step is a judgment call that affects the result. Record them
with the output — rows dropped, rows deduplicated, values coerced, and the
assumption made on any ambiguous date. An analysis whose cleaning steps are
undocumented cannot be reproduced or audited, including by you next month.

## Related

- `social-analytics` — normalizing platform exports specifically
- `metrics-lab` — the data-quality checklist for behavioral event data
- `xlsx` skill — when the deliverable is itself a spreadsheet
