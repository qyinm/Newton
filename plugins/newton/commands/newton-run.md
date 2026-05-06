---
description: Run a Newton scenario with the Playwright backend
---

# Newton Run

Run a Newton scenario with the Playwright backend.

Use the user-provided scenario, target, and base URL when present. For the checked-in login dogfood scenario:

```bash
newton qa run qa/dogfood/login/scenario/login-smoke.generated.yaml \
  --target web \
  --backend playwright \
  --base-url http://127.0.0.1:8123 \
  --plan-provenance qa/dogfood/login/scenario/login_ticket.template.plan.json \
  --out qa/dogfood/login/runs
```

After the run, inspect the emitted `result.json` and `qa-report.md`, and summarize evidence artifacts.
