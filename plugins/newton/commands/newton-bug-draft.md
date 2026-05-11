---
description: Update a Newton tracker from a run and draft a bug ticket
---

# Newton Bug Draft

Update a Newton QA run tracker from a run result and draft a bug ticket.

This command closes Newton's release-quality web flow: use web-first run evidence to update the tracker and create a bug draft without bypassing `newton qa ...`.

Use the user-provided tracker, run directory, item number, and environment when present. For the checked-in failing dogfood run:

```bash
bash scripts/demo-web-release.sh
newton qa tracker-update-from-run qa/dogfood/login/plan/qa-run-tracker.md \
  --item 5 \
  --env stg \
  --run <failed-run-dir>
newton qa bug-draft qa/dogfood/login/plan/qa-run-tracker.md \
  --out qa/dogfood/login/bug-ticket-draft.md
```

Report the failed checklist item, linked run report, and generated bug draft path.
