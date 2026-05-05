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
```

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

## Supported Actions in MVP

- `navigate`: web navigation
- `tap`: click/tap an element
- `input_text`: fill an input
- `assert_visible`: wait until an element/text is visible

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
