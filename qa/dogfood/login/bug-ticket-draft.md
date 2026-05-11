# Bug Ticket Draft: [stg] login-smoke failed on web

## Issue Fields

- Title: [stg] login-smoke failed on web
- Severity: S2 - Major
- Priority: P1
- Environment: stg
- Failed Step: assert-dashboard (assert_visible)
- Suspected Owner/Area: Web / login-smoke

## Failed Checklist Item

- Item: User sees Dashboard after successful submit
- Environment: stg
- Status: failed
- Notes: Run run_c96d5ae286d8 failed; report: qa/dogfood/login/runs/run_c96d5ae286d8/qa-report.md

## Reproduction Steps

1. navigate: `open-login`
2. input_text: `enter-email`
3. input_text: `enter-password`
4. tap: `submit`
5. assert_visible: `assert-dashboard`

## Expected Result

Scenario should complete all steps successfully.

## Actual Result

Locator.wait_for: Timeout 10000ms exceeded.
Call log:
  - waiting for get_by_text("Dashboard") to be visible

## Source References

- Tracker: `qa/dogfood/login/plan/qa-run-tracker.md`
- Run result: `qa/dogfood/login/runs/run_c96d5ae286d8/result.json`
- Run report: `qa/dogfood/login/runs/run_c96d5ae286d8/qa-report.md`
- Planning input: `qa/dogfood/login/inputs/ticket.md`
- Accepted scenario: `qa/dogfood/login/scenario/login-smoke.generated.yaml`
- Plan provenance: `qa/dogfood/login/scenario/login_ticket.template.plan.json`

## Evidence Paths

- `qa/dogfood/login/runs/run_c96d5ae286d8/failure-step-005-assert-dashboard.png`
- `qa/dogfood/login/runs/run_c96d5ae286d8/playwright-trace.zip`
