# QA Estimate: Login

## Summary

Estimated QA effort: S

## Basis

- Checklist items: 21
- Risk level: P0 functional
- Source input: `qa/dogfood/login/inputs/ticket.md`

## Evidence Factors

| Factor | Value | Evidence | Source |
| --- | --- | --- | --- |
| checklist_items | 21 items | Extracted acceptance criteria count | `qa/dogfood/login/inputs/ticket.md` |
| risk_level | P0 functional | Primary flow blocks core user access | `qa/dogfood/login/inputs/ticket.md` |
| source_1 | `ticket.md` | Provided planning context included in bundle generation | `qa/dogfood/login/inputs/ticket.md` |
| source_2 | `policy.md` | Provided planning context included in bundle generation | `qa/dogfood/login/inputs/policy.md` |
| source_3 | `design-notes.md` | Provided planning context included in bundle generation | `qa/dogfood/login/inputs/design-notes.md` |

## Suggested Manual QA Time

- Happy path smoke: 15 min
- Negative/error cases: 15 min
- Evidence/report review: 10 min

## Assumptions

- Local or staging environment is available.
- No cross-platform mobile validation included.
