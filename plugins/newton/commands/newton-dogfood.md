---
description: Validate the checked-in Newton login dogfood QA loop
---

# Newton Dogfood

Validate the checked-in Newton login dogfood loop.

Run:

```bash
bash scripts/demo-web-release.sh
newton qa bundle-validate qa/dogfood/login/plan
newton qa validate qa/dogfood/login/scenario/login-smoke.generated.yaml
newton qa runs --out qa/dogfood/login/runs
```

Then inspect:

```bash
cat qa/dogfood/login/plan/qa-estimate.md
cat qa/dogfood/login/agent-handoff.md
cat qa/dogfood/login/bug-ticket-draft.md
```

Report whether the dogfood package contains a passing run, a failing run, screenshot evidence, trace evidence, a tracker update, and a bug draft.
