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

Check a workstation or CI runner before executing scenarios:

```bash
newton qa doctor web
```

The doctor checks the Playwright Python import, Chromium availability, and a basic headless Chromium launch. If setup is incomplete, it exits non-zero and prints the same remediation commands Newton writes into failed run artifacts:

- Missing Playwright package: `python -m pip install -e '.[web]'`
- Missing Chromium browser binary: `python -m playwright install chromium`
- Missing Linux OS dependencies: `python -m playwright install --with-deps chromium`

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

## Production-like runtime config

Configure browser launch and context settings in the web target:

```yaml
targets:
  - id: web
    platform: web
    backend: playwright
    base_url: https://staging.example.com
    web:
      headless: true
      browser_channel: chrome
      viewport:
        width: 1440
        height: 900
      locale: en-US
      timezone: America/Los_Angeles
      permissions:
        - clipboard-read
      storage_state_path: qa/state/staging.json
      extra_http_headers:
        X-QA-Run: release-gate
      retries: 1
      timeout_ms: 10000
```

Newton maps these settings to Playwright as follows:

- `headless` and `browser_channel` become Chromium launch options.
- `viewport`, `locale`, `timezone`, `permissions`, `storage_state_path`, and `extra_http_headers` become browser context options.
- `retries` retries each failing step before the run is marked failed.
- `timeout_ms` sets Playwright's default timeout and navigation timeout for the page.

Newton also accepts these same runtime keys under `targets[].device` for older or
agent-generated scenario drafts. Values in `targets[].web` take precedence.

Every step defaults to `timeout_ms: 10000`. Add `timeout_ms` to an individual
step to override that action's Playwright timeout:

```yaml
steps:
  - id: assert-dashboard
    action: assert_visible
    timeout_ms: 30000
    target:
      web:
        role: heading
        name: Dashboard
```

For passwords, tokens, or other sensitive input, set `secure: true` on the step.
Generated `result.json` and `qa-report.md` redact secure step values if backend
errors or evidence descriptions echo them.

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

If Playwright setup or web preflight fails during `newton qa run`, Newton still writes `result.json` and `qa-report.md`. Setup failures use a `setup` step and base URL reachability failures use a `preflight-base-url` step so CI and agents can read the failure without parsing a Playwright stack trace.

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

When `evidence.screenshots` is `after_each_step`, Newton stores a screenshot for every completed step and the failing step when applicable:

```text
step-<index>-<step-id>.png
failure-step-<index>-<step-id>.png
```

When `evidence.traces: true`, Newton stores a Playwright trace for failed runs:

```text
playwright-trace.zip
```

When `evidence.video: true`, Newton records the Playwright session video and attaches the relative `.webm` path to both `result.json` and `qa-report.md`.

When `evidence.logs: true`, Newton captures browser console errors and failed network requests when they occur:

```text
console-errors.jsonl
network-failures.jsonl
```

`result.json` includes a compact `summary` object with step totals, artifact count, total duration when available, and the first failure error. Both `result.json` and `qa-report.md` reference evidence paths relative to the run directory. The markdown report also includes a run summary and failure diagnosis section for failed runs.

Open a trace with:

```bash
python -m playwright show-trace qa/runs/<run_id>/playwright-trace.zip
```
