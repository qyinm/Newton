# Risk Map: Login

| Area | Priority | Rationale | Source |
| --- | --- | --- | --- |
| functional | P0 | Login flow blocks core user access | generated PRD baseline risks |
| edge case | P1 | Boundary, empty, duplicate, and invalid inputs can break the flow outside the happy path | generated PRD baseline risks |
| network failure | P1 | Slow, offline, timeout, and retry states can hide incomplete error handling | generated PRD baseline risks |
| permission/role | P1 | Role or session differences can expose unauthorized access or blocked valid users | generated PRD baseline risks |
| policy conflict | P1 | Source policy or copy requirements may conflict with visible product behavior | generated PRD baseline risks |
| regression | P1 | Existing login and navigation paths can regress when this feature changes | generated PRD baseline risks |
| data state | P1 | Data setup and state-specific records require coverage: Locked users see account recovery guidance | `login-policy.md#Acceptance criteria` |
| localization/copy | P1 | Visible copy or localization rules can drift from source expectations: Error message does not expose whether email exists; Locked users see account recovery guidance | `login-policy.md#Acceptance criteria` |

Source: generated PRD baseline risks
