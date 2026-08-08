---
description: Validate every skill, tool, hook, and config file in this repo and report what is broken.
---

Run the full configuration QA gate and report the result.

```bash
python3 qa/validate.py
python3 qa/selftest.py
```

Then:

1. If either command reports errors, fix them. Do not report success while
   `validate.py` exits non-zero.
2. Report warnings only if they are actionable — a warning that is a
   deliberate choice should be left alone and not narrated every run.
3. If both pass, say so in one line with the skill and test counts. Do not
   summarize what the repo contains; the user knows.

$ARGUMENTS
