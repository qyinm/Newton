---
name: newton-qa-workflow
description: Route natural-language QA planning, execution, tracker, and bug-draft requests through the Newton QA CLI artifact contract.
---

# Newton QA Workflow

Use this skill when the user asks for QA planning, sprint QA, ticket QA, test scope, executable QA scenarios, web QA runs, QA evidence, tracker updates, or bug ticket drafts in a repository that can use Newton.

Newton is file-first. Prefer the `newton qa ...` CLI over ad-hoc prompts or one-off test notes. Preserve artifact paths in your response so another agent or CI job can replay the work.

## Preconditions

1. Check the current repo and worktree status.
2. Verify the CLI is installed:

```bash
newton version
```

3. If unavailable, run the project installer when this repository is checked out:

```bash
bash scripts/install.sh
```

If the repository is not checked out, use the official installer:

```bash
curl -fsSL https://raw.githubusercontent.com/qyinm/Newton/main/scripts/install.sh | bash
```

## QA Planning

When the user asks for a QA plan, sprint QA, test scope, risk map, QA estimate, checklist, test cases, or automation candidates:

```bash
newton qa plan-bundle <ticket-or-context.md> \
  --source <policy-or-design.md> \
  --out <qa-plan-root>
newton qa bundle-validate <bundle-dir>
```

Use every relevant source file the user provided. Report the input files and generated artifacts:

- `qa-scope.md`
- `qa-estimate.md`
- `checklist.md`
- `test-cases.csv`
- `risk-map.md`
- `automation-candidates.md`
- `qa-run-tracker.md`
- `manifest.json`

## Scenario Planning

When the user asks for an executable scenario, smoke test, or agent-runnable QA flow:

```bash
newton qa plan <ticket-or-context.md> \
  --agent template \
  --target web \
  --out <scenario-dir>
newton qa validate <scenario.yaml>
```

If the user requests an external planning agent, use `--agent codex` or `--agent claude`, then preserve the prompt, raw output, accepted scenario, and provenance paths in the summary.

## Execution

When the user asks to run QA, verify a scenario, test a local fixture, or collect evidence:

```bash
newton qa validate <scenario.yaml>
newton qa run <scenario.yaml> \
  --target <target-id> \
  --backend playwright \
  --base-url <url> \
  --out <runs-dir>
newton qa report <runs-dir>/<run-id>
```

Report the run id, status, result path, report path, and evidence paths. For failures, call out screenshot and trace artifacts when present.

## Tracker And Bug Drafts

When the user asks to update QA status from a run or create a bug ticket:

```bash
newton qa tracker-update-from-run <qa-run-tracker.md> \
  --item <number> \
  --env <dev|stg|prod> \
  --run <run-dir>
newton qa bug-draft <qa-run-tracker.md>
```

If the user provides a manual failure instead of a run directory, use:

```bash
newton qa tracker-update <qa-run-tracker.md> \
  --item <number> \
  --env <dev|stg|prod> \
  --status failed \
  --notes "<actual result and evidence>"
newton qa bug-draft <qa-run-tracker.md>
```

## Reporting Contract

Every final response after using Newton should include:

- input files
- generated artifacts
- validation commands
- run id
- evidence paths
- tracker update status
- bug draft path
- remaining risk

Do not claim that QA passed unless `newton qa run` or the relevant validation command actually passed in the current turn. If you only generated a plan, say that execution remains unverified.
