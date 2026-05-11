# Newton Scenario Schema

Newton scenarios are QA artifacts, not just automation scripts. A scenario must explain what product behavior is being tested and how each target should execute it.

## Required Top-Level Fields

- `scenario`: QA metadata
- `targets`: one or more execution targets
- `steps`: ordered executable steps

## Scenario Metadata

```yaml
scenario:
  id: login-smoke
  title: Login smoke
  source_refs:
    - qa/inputs/tickets.md#login
  risk_category: functional
  priority: P0
  environments: [staging]
```

## Targets

Web target:

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

`web` is the preferred production-like runtime configuration for Playwright targets.
For compatibility with device-shaped scenario drafts, Newton also reads the same
runtime keys from `targets[].device` when `targets[].web` does not override them.

iOS target:

```yaml
targets:
  - id: ios
    platform: ios
    backend: maestro
    bundle_id: com.example.app
    device:
      model: iPhone 15
```

## Steps

Each step has a shared action and target-specific bindings.

```yaml
steps:
  - id: submit
    action: tap
    target:
      web:
        role: button
        name: Log in
      ios:
        accessibility_id: loginButton
```

Step timeout defaults to `10000` ms. Override a single slow or intentionally
short assertion with `timeout_ms` on that step:

```yaml
steps:
  - id: wait-for-dashboard
    action: assert_visible
    timeout_ms: 30000
    target:
      web:
        role: heading
        name: Dashboard
```

Sensitive input values should set `secure: true`. Newton redacts secure step
values from generated `result.json` and `qa-report.md` if browser or backend
errors echo those values.

## Supported Actions in MVP

Newton keeps the action vocabulary intentionally small for the first executable web backend.

Canonical cross-platform actions:

- `navigate`: web navigation
- `tap`: click/tap an element
- `input_text`: fill an input
- `assert_visible`: wait until an element/text is visible

Playwright web aliases accepted by the web backend:

- `goto`: alias for `navigate`
- `click`: alias for `tap`
- `fill`: alias for `input_text`
- `wait_for_selector` / `expect_visible`: aliases for `assert_visible`
- `assert_text`: waits for `step.value` or `target.web.text` to be visible
- `assert_url`: waits for the current URL to match `target.web.url` or `step.value`

Unsupported actions fail explicitly with `unsupported web action: <action>`.

## Selector Priority

Prefer stable selectors:

1. Web `role` + `name` or `test_id`
2. iOS `accessibility_id`
3. Visible `text`
4. CSS selector for web only
5. Coordinates only as a future last resort

## Evidence Policy

```yaml
evidence:
  screenshots: on_failure
  video: true
  logs: true
  traces: true
```

Evidence is normalized into `qa/runs/<run_id>/result.json` and summarized in `qa-report.md`.
For Playwright failures, screenshot and trace artifact paths are stored relative to the run directory, for example:

```text
failure-step-005-assert-dashboard.png
playwright-trace.zip
```
