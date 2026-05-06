---
description: Generate a Newton QA plan bundle and scenario from markdown context
---

# Newton Plan

Generate a Newton QA planning bundle and scenario from markdown context.

Use the user-provided paths when present. For the default login dogfood input, run:

```bash
newton qa plan-bundle qa/dogfood/login/inputs/ticket.md \
  --source qa/dogfood/login/inputs/policy.md \
  --source qa/dogfood/login/inputs/design-notes.md \
  --out qa/dogfood/login \
  --bundle-dir-name plan
newton qa plan qa/dogfood/login/inputs/ticket.md \
  --agent template \
  --target web \
  --base-url http://127.0.0.1:8000 \
  --out qa/dogfood/login/scenario
```

Validate the outputs:

```bash
newton qa bundle-validate qa/dogfood/login/plan
newton qa validate qa/dogfood/login/scenario/login-smoke.generated.yaml
```
