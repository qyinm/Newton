---
name: newton-qa-workflow
description: Route natural-language QA planning, execution, tracker, and bug-draft requests through the Newton QA CLI artifact contract.
---

# Newton QA Workflow

Use this skill when the user asks for QA planning, sprint QA, ticket QA, test scope, executable QA scenarios, web QA runs, QA evidence, tracker updates, or bug ticket drafts in a repository that can use Newton.

Newton is file-first. Prefer the `newton qa ...` CLI over ad-hoc prompts or one-off test notes. Preserve artifact paths in your response so another agent or CI job can replay the work.

Newton's release-quality web flow is web-first:

1. create a source-backed QA plan bundle
2. generate a `--target web` executable scenario
3. validate and run it with the Playwright backend
4. report evidence paths
5. update tracker state
6. draft a bug ticket when there is a failure

Use `--target web` for generated scenarios and `--backend playwright` for execution unless the user explicitly asks for planning-only output. Mobile execution is not release-ready. If a user asks for mobile QA, keep the response to planning/risk analysis or explain that Newton's release-quality execution path is currently web-first.

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

## Natural-Language Routing

Map natural-language requests to the narrowest Newton CLI flow:

- planning only: create and validate the QA planning bundle; do not imply execution happened.
- scenario generation: create a web scenario with `newton qa plan --target web`, then validate the scenario.
- web run: validate the scenario, run it with `--backend playwright`, then generate a report.
- tracker update: update `qa-run-tracker.md` from a run directory or from a manual failure note.
- bug draft: draft a bug ticket from the tracker after the failed item contains evidence.

## Planning Only

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

Example user request:

> "Plan QA for this ticket, but do not run anything yet."

Example commands:

```bash
newton qa plan-bundle docs/tickets/login.md \
  --source docs/policies/auth.md \
  --out qa/login \
  --bundle-dir-name plan
newton qa bundle-validate qa/login/plan
```

Final response emphasis: list the input files, planning artifacts, commands run, and say execution remains unverified.

## Scenario Generation

When the user asks for an executable scenario, smoke test, or agent-runnable QA flow:

```bash
newton qa plan <ticket-or-context.md> \
  --agent template \
  --target web \
  --out <scenario-dir>
newton qa validate <scenario.yaml>
```

If the user requests an external planning agent, use `--agent codex` or `--agent claude`, then preserve the prompt, raw output, accepted scenario, and provenance paths in the summary.

Example user request:

> "Turn this ticket into a web smoke scenario."

Example commands:

```bash
newton qa plan docs/tickets/login.md \
  --agent template \
  --target web \
  --base-url http://127.0.0.1:8000 \
  --out qa/login/scenario
newton qa validate qa/login/scenario/login-smoke.generated.yaml
```

Final response emphasis: list the scenario path, validation command, provenance files when available, and remaining scenario risk.

## Web Run

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

Example user request:

> "Run the generated login scenario against staging and collect evidence."

Example commands:

```bash
newton qa validate qa/login/scenario/login-smoke.generated.yaml
newton qa run qa/login/scenario/login-smoke.generated.yaml \
  --target web \
  --backend playwright \
  --base-url https://staging.example.com \
  --out qa/login/runs
newton qa report qa/login/runs/<run-id>
```

Final response emphasis: list the run id, result path, report path, screenshot or trace evidence paths, commands run, and remaining risk.

## Tracker Update

When the user asks to update QA status from a run:

```bash
newton qa tracker-update-from-run <qa-run-tracker.md> \
  --item <number> \
  --env <dev|stg|prod> \
  --run <run-dir>
```

If the user provides a manual failure instead of a run directory, use:

```bash
newton qa tracker-update <qa-run-tracker.md> \
  --item <number> \
  --env <dev|stg|prod> \
  --status failed \
  --notes "<actual result and evidence>"
```

Example user request:

> "Update the tracker from the failed staging run."

Example commands:

```bash
newton qa tracker-update-from-run qa/login/plan/qa-run-tracker.md \
  --item 5 \
  --env stg \
  --run qa/login/runs/<run-id>
```

Final response emphasis: list the tracker path, updated item, linked run report, evidence paths, and commands run.

## Bug Draft

When the user asks to create a bug ticket draft from QA state:

```bash
newton qa bug-draft <qa-run-tracker.md> \
  --out <bug-ticket-draft.md>
```

Example user request:

> "Draft the bug ticket from that failed checklist item."

Example commands:

```bash
newton qa bug-draft qa/login/plan/qa-run-tracker.md \
  --out qa/login/bug-ticket-draft.md
```

Final response emphasis: list the bug draft path, failed checklist item, linked evidence, commands run, and remaining risk.

## Reporting Contract

Every final response after using Newton should include this checklist:

- input files
- generated artifacts
- commands run
- run id
- evidence paths
- tracker update status
- bug draft path
- remaining risk
- whether the work stayed within the release-quality web flow

Do not claim that QA passed unless `newton qa run` or the relevant validation command actually passed in the current turn. If you only generated a plan, say that execution remains unverified.
