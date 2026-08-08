---
description: Map a niche or competitor set from public sources and find the structural gap nobody can fill.
---

Analyze the niche, competitor, or space named in $ARGUMENTS.

1. **Sourcing discipline first.** Public, accessible material only — published
   posts, public pricing, public filings, archived pages. No scraping against
   terms, no fake accounts, no private analytics. If the question genuinely
   needs non-public data, say so and stop.

2. **Record into the graph** as you go, so this compounds across sessions:
   ```bash
   python3 tools/kg.py add --id <slug> --type brand --name "<name>" --attr platform=<p>
   python3 tools/kg.py link --from <a> --to <b> --rel <verb> --note "<why>"
   python3 tools/kg.py clusters
   python3 tools/kg.py central --top 20
   ```

3. **Per competitor**, follow `competitor-recon`: format and cadence, top and
   bottom performers by engagement rate, what they **abandoned** (scroll back
   12–18 months — this is the most valuable and least-performed step), what
   they repeat despite poor results, and what their monetization forbids them
   from saying.

4. **Then run `contrarian-scan`** on the niche as a whole: what does every
   account here do identically without ever explaining why, and is that belief
   true-then-false-now, true-for-them-not-you, or never tested at all?

5. **Output the gap and the move.** A teardown that stops at description is a
   report. Name the specific thing to do and why they structurally cannot
   follow.

Benchmark against accounts 2–5x the user's size, not 50x — different weight
classes operate under different mechanics and the lessons do not transfer.

$ARGUMENTS
