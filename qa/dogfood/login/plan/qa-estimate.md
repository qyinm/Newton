# QA Estimate: Login

## Summary

Estimated QA effort: M (2-4 hours)

## Basis

- Checklist items: 21
- Risk level: P0 functional
- Source input: `qa/dogfood/login/inputs/ticket.md`
- Total score: 5
- Score band: 5-9 points

## Evidence Factors

| Factor | Value | Evidence | Source | Score | Rule |
| --- | --- | --- | --- | ---: | --- |
| screens | 0 extracted | No screens called out in source context. | `qa/dogfood/login/inputs/ticket.md` | 0 | 0-1 screens => +0 |
| roles | 0 extracted | No distinct user roles called out in source context. | `qa/dogfood/login/inputs/ticket.md` | 0 | 0-1 roles => +0 |
| states | 15 extracted | User can open login page from a direct `/login.html` route; User can enter email; User can enter password; +12 more | `ticket.md#Acceptance Criteria`, `policy.md#Acceptance Criteria`, `design-notes.md#Acceptance Criteria` | 2 | 9+ states => +2 |
| policy_rules | 2 extracted | Security copy must not confirm account existence.; Recovery guidance is required for locked accounts. | `policy.md#Policy References` | 1 | 1-2 policy rules => +1 |
| integrations | 0 extracted | No integrations or dependencies called out in source context. | `qa/dogfood/login/inputs/ticket.md` | 0 | 0 integrations/dependencies => +0 |
| environments | 0 extracted | No explicit environment matrix called out in source context. | `qa/dogfood/login/inputs/ticket.md` | 0 | 0-1 environments => +0 |
| regression | 2 extracted | Existing dashboard navigation must continue to work after login.; The smoke scenario should remain stable enough to automate across dev and staging. | `ticket.md#Regression Notes` | 1 | 1-2 regression risks => +1 |
| data_setup | 0 signals | No explicit data setup called out in source context. | `qa/dogfood/login/inputs/ticket.md` | 0 | 0 data setup signals => +0 |
| retest_count | 3 passes | 1 environment pass(es) plus 2 regression retest pass(es). | `ticket.md#Regression Notes` | 1 | 2-3 retest passes => +1 |

## Suggested Manual QA Time

- Primary flow, role/state, and dependency pass: 2-3 hours
- Regression and evidence review: 30-60 min

## Assumptions

- Local or staging environment is available.
- No cross-platform mobile validation included.
