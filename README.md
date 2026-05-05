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

```bash
newton qa run qa/scenarios/web-login-smoke.yaml --target web --backend playwright --out qa/runs
```

## Current Backends

- `dry-run`: validates the full Newton pipeline without opening a browser or simulator
- `playwright`: executes web scenarios
- `maestro`: compiles Newton iOS bindings to Maestro flow YAML and saves it as an artifact
