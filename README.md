# Newton QA

Newton is an agent-native QA harness that turns sprint context into executable web/iOS scenarios and evidence-backed QA reports.

## Install

```bash
python -m pip install -e '.[dev]'
```

For web execution:

```bash
python -m pip install -e '.[dev,web]'
python -m playwright install chromium
```

## Plan a QA Bundle

Generate a minimal PRD-style planning bundle from markdown product/ticket context:

```bash
newton qa plan-bundle qa/inputs/login-ticket.md \
  --source qa/inputs/login-policy.md \
  --source qa/inputs/staging-notes.md \
  --out qa/plans
```

Use `--source` to merge extra markdown sources such as policy notes, staging notes, or design annotations into the same checklist/test-case bundle.

Outputs:

```text
qa/plans/login/qa-scope.md
qa/plans/login/checklist.md
qa/plans/login/test-cases.csv
qa/plans/login/risk-map.md
qa/plans/login/qa-estimate.md
qa/plans/login/automation-candidates.md
qa/plans/login/qa-run-tracker.md
qa/plans/login/manifest.json
```

After updating the tracker with a checklist result, generate a bug ticket draft from the first failed item:

```bash
newton qa tracker-update qa/plans/login/qa-run-tracker.md \
  --item 5 \
  --env stg \
  --status failed \
  --notes "Dashboard never appears after submit"
newton qa tracker-update-from-run qa/plans/login/qa-run-tracker.md \
  --item 1 \
  --env stg \
  --run qa/runs/run_123
newton qa bug-draft qa/plans/login/qa-run-tracker.md
```

Output:

```text
qa/plans/login/bug-ticket-draft.md
```

The bundle is deterministic and does not call an external agent.

## Plan a Scenario

Generate a scenario draft from markdown product/ticket context. The default `template` agent is deterministic; `codex` and `claude` use the same external-agent YAML contract:

```bash
newton qa plan qa/inputs/login-ticket.md --agent template --target web --out qa/scenarios
newton qa plan qa/inputs/login-ticket.md --agent codex --target web --out qa/scenarios
```

Outputs:

```text
qa/scenarios/login-smoke.generated.yaml
qa/scenarios/login_ticket.template.plan.json
```

Agent-backed planning also records the exact prompt and raw stdout:

```text
qa/scenarios/login_ticket.codex.prompt.txt
qa/scenarios/login_ticket.codex.raw.txt
qa/scenarios/login_ticket.codex.plan.json
```

For a cross-platform draft:

```bash
newton qa plan qa/inputs/login-ticket.md --target web,ios --out qa/scenarios
```

`qa plan` validates the generated scenario before returning successfully.

## Validate a Scenario

```bash
newton qa validate qa/scenarios/web-login-smoke.yaml
```

Expected:

```text
valid: web-login-smoke
```

## Dry Run

```bash
newton qa run qa/scenarios/web-login-smoke.yaml --target web --backend dry-run --out qa/runs
```

To link a generated scenario back to its planning provenance, pass the accepted plan JSON:

```bash
newton qa run qa/scenarios/login-smoke.generated.yaml \
  --target web \
  --backend dry-run \
  --plan-provenance qa/scenarios/login_ticket.codex.plan.json \
  --out qa/runs
```

The run `result.json` and `qa-report.md` include a small `planning`/Planning Provenance section with the provenance path, agent, source input, accepted scenario path, and validation status.

Outputs:

```text
qa/runs/index.jsonl
qa/runs/run_*/result.json
qa/runs/run_*/qa-report.md
```

List local run history:

```bash
newton qa runs --out qa/runs
```

Expected:

```text
run_e213334d75db  passed  login-smoke  web
```

## Web Run

Install Chromium once, then run a web scenario with Playwright:

```bash
python -m pip install -e '.[web]'
python -m playwright install chromium
newton qa run qa/scenarios/web-login-smoke.yaml \
  --target web \
  --backend playwright \
  --base-url https://staging.example.com \
  --out qa/runs
```

On failure, Newton writes debuggable evidence into the run directory:

```text
qa/runs/run_*/result.json
qa/runs/run_*/qa-report.md
qa/runs/run_*/failure-step-*.png
qa/runs/run_*/playwright-trace.zip
```

Open traces with:

```bash
python -m playwright show-trace qa/runs/<run_id>/playwright-trace.zip
```

## Current Backends

- `dry-run`: validates the full Newton pipeline without opening a browser or simulator
- `playwright`: executes web scenarios
- `maestro`: compiles Newton iOS bindings to Maestro flow YAML and saves it as an artifact
