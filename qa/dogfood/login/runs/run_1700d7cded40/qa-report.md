# QA Report: login-smoke

**Run ID:** run_1700d7cded40
**Target:** web
**Platform:** web
**Status:** passed

## Run Summary

| Total | Passed | Failed | Skipped | Artifacts | Duration |
| --- | --- | --- | --- | --- | --- |
| 5 | 5 | 0 | 0 | 0 | 931 ms |

## Step Results

| Step | Action | Status | Error |
| --- | --- | --- | --- |
| open-login | navigate | passed | - |
| enter-email | input_text | passed | - |
| enter-password | input_text | passed | - |
| submit | tap | passed | - |
| assert-dashboard | assert_visible | passed | - |

## Planning Provenance

**Provenance:** `qa/dogfood/login/scenario/ticket.template.plan.json`
**Agent:** template
**Input:** `qa/dogfood/login/inputs/ticket.md`
**Accepted Scenario:** `qa/dogfood/login/scenario/login-smoke.generated.yaml`
**Validation Status:** accepted
