---
description: Verify and install the Newton QA CLI for this project
---

# Newton Setup

Verify that the Newton QA CLI is installed and ready for this project.

Run:

```bash
newton version
newton qa bundle-validate qa/dogfood/login/plan
newton qa validate qa/dogfood/login/scenario/login-smoke.generated.yaml
```

If `newton` is not available, install it from the repository root:

```bash
bash scripts/install.sh
```

If this plugin was installed without the repository checkout, use the official installer:

```bash
curl -fsSL https://raw.githubusercontent.com/qyinm/Newton/main/scripts/install.sh | bash
```
