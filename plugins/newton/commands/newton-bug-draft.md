---
description: Update a Newton tracker from a run and draft a bug ticket
---

# Newton Bug Draft

Update a Newton QA run tracker from a run result and draft a bug ticket.

Use the user-provided tracker, run directory, item number, and environment when present. For the checked-in failing dogfood run:

```bash
newton qa tracker-update-from-run qa/dogfood/login/plan/qa-run-tracker.md \
  --item 5 \
  --env stg \
  --run qa/dogfood/login/runs/run_c96d5ae286d8
newton qa bug-draft qa/dogfood/login/plan/qa-run-tracker.md \
  --out qa/dogfood/login/bug-ticket-draft.md
```

Report the failed checklist item, linked run report, and generated bug draft path.
