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

Outputs:

```text
qa/runs/run_*/result.json
qa/runs/run_*/qa-report.md
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
