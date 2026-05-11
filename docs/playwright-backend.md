# Playwright Backend

The Playwright backend executes Newton web scenarios in Chromium.

## Setup

```bash
python -m pip install -e '.[web]'
python -m playwright install chromium
```

In GitHub Actions or fresh Linux runners, prefer:

```bash
python -m playwright install --with-deps chromium
```

## Run

```bash
newton qa validate qa/scenarios/web-login-smoke.yaml
newton qa run qa/scenarios/web-login-smoke.yaml \
  --target web \
  --backend playwright \
  --base-url http://127.0.0.1:8000 \
  --out qa/runs
newton qa report qa/runs/<run_id>
```

`--base-url` overrides the scenario target's `base_url`, which lets the same scenario run against local fixtures, preview deployments, staging, or production.

## CI release gate

For release gates, call `newton qa run` without `--allow-failure`:

```bash
newton qa validate qa/scenarios/web-login-smoke.yaml
newton qa run qa/scenarios/web-login-smoke.yaml \
  --target web \
  --backend playwright \
  --base-url "$PREVIEW_URL" \
  --out qa/runs
```

Newton writes `result.json`, `qa-report.md`, and `index.jsonl` before the command exits. Passing runs exit `0`; non-passing runs exit non-zero so CI can block the release. Reserve `--allow-failure` for dogfood or diagnostic runs that intentionally capture failing evidence without failing the shell command.

## Supported web actions

- `navigate` / `goto`
- `tap` / `click`
- `input_text` / `fill`
- `assert_visible` / `wait_for_selector` / `expect_visible`
- `assert_text`
- `assert_url`

Selectors support:

- `role` + optional `name`
- `test_id`
- `text`
- `css`

## Failure evidence

When a step fails and `evidence.screenshots` is `on_failure`, Newton stores:

```text
failure-step-<index>-<step-id>.png
```

When `evidence.traces: true`, Newton stores a Playwright trace for failed runs:

```text
playwright-trace.zip
```

Both `result.json` and `qa-report.md` reference evidence paths relative to the run directory.

Open a trace with:

```bash
python -m playwright show-trace qa/runs/<run_id>/playwright-trace.zip
```
