---
description: Report which skills, commands, and tools have actually been used, and bank this session so the history survives.
---

Run the usage report and bank this session's tally.

```bash
python3 tools/usage.py --archive
```

Then:

1. **Report what fired and what did not.** Lead with the counts, not with a
   recommendation.
2. **Do not propose dropping anything unless the tool says there is enough
   history.** It refuses a verdict below 5 sessions and 14 days, and that
   refusal is the point — a skill absent from three sessions has not been
   rejected, it simply had no occasion to fire.
3. **When it does have enough history**, check each drop candidate's
   `description` before agreeing to remove it. A good skill with a description
   that never says *when* to use it looks identical, from the report, to a
   useless one. Fixing the description is usually the better move.
4. **If new tally files were written**, remind the user to commit
   `.claude/data/usage/` — that is what makes the history accumulate. The
   files hold counts and dates only, never conversation text.

If the report shows one session every time, say so plainly: transcripts are
not persisting, and without `--archive` plus a commit, this report can never
say anything useful.

$ARGUMENTS
