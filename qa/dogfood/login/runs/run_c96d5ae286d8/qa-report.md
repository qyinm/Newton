# QA Report: login-smoke

**Run ID:** run_c96d5ae286d8
**Target:** web
**Platform:** web
**Status:** failed

## Step Results

| Step | Action | Status | Error |
| --- | --- | --- | --- |
| open-login | navigate | passed | - |
| enter-email | input_text | passed | - |
| enter-password | input_text | passed | - |
| submit | tap | passed | - |
| assert-dashboard | assert_visible | failed | Locator.wait_for: Timeout 10000ms exceeded.
Call log:
  - waiting for get_by_text("Dashboard") to be visible
 |

## Evidence

- `screenshot`: `failure-step-005-assert-dashboard.png` — Failure screenshot for step assert-dashboard
- `trace`: `playwright-trace.zip` — Playwright trace for failed run

## Step Evidence

### assert-dashboard
- `screenshot`: `failure-step-005-assert-dashboard.png` — Failure screenshot for step assert-dashboard

## Planning Provenance

**Provenance:** `qa/dogfood/login/scenario/login_ticket.template.plan.json`
**Agent:** template
**Input:** `qa/dogfood/login/inputs/ticket.md`
**Accepted Scenario:** `qa/dogfood/login/scenario/login-smoke.generated.yaml`
**Validation Status:** accepted

## Bug Draft

**Title:** login-smoke failed on web
**Environment:** web
**Severity:** TBD by QA
**Priority:** TBD by QA

### Reproduction Steps
1. navigate: `open-login`
2. input_text: `enter-email`
3. input_text: `enter-password`
4. tap: `submit`
5. assert_visible: `assert-dashboard`

### Actual Result
Locator.wait_for: Timeout 10000ms exceeded.
Call log:
  - waiting for get_by_text("Dashboard") to be visible


### Expected Result
Scenario should complete all steps successfully.
