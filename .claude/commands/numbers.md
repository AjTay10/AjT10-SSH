---
description: Turn platform analytics exports into a normalized dataset, a dashboard, and an honest read.
---

Take the export file(s) the user names in $ARGUMENTS (or find recent CSVs in
the working directory if they named none) and run the full analytics pipeline.

1. **Inspect first.** For each file:
   `python3 tools/social_ingest.py --inspect <file>`
   Confirm the platform and the column mapping before proceeding. Do not guess
   the platform silently — if the guess is ambiguous, ask.

2. **Reconcile.** Ask the user for one number from the platform's own
   dashboard and check it against the file. If they disagree, stop and say so
   — every downstream number would be wrong.

3. **Normalize.**
   `python3 tools/social_ingest.py --csv <f> --platform <p> [...] --out norm.csv --summary`

4. **Dashboard.**
   `python3 tools/dashboard.py --csv norm.csv --out dashboard.html --title "<period>"`

5. **Check for breaks.**
   `python3 tools/anomaly.py --csv norm.csv --date date --value impressions --seasonal weekly`

6. **Read it**, following the `social-analytics` skill. Lead with what changed
   and what to do about it. Never open with a wall of totals.

Hold to the rule that cross-platform engagement rates are not comparable —
say it once, plainly, if the user asks which platform is "winning".

$ARGUMENTS
