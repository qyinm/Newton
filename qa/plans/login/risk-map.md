# Risk Map: Login

| Area | Priority | Rationale |
| --- | --- | --- |
| functional | P0 | Login flow blocks core user access |
| edge case | P1 | Boundary, empty, duplicate, and invalid inputs can break the flow outside the happy path |
| network failure | P1 | Slow, offline, timeout, and retry states can hide incomplete error handling |
| permission/role | P1 | Role or session differences can expose unauthorized access or blocked valid users |
| policy conflict | P1 | Source policy or copy requirements may conflict with visible product behavior |
| regression | P1 | Existing login and navigation paths can regress when this feature changes |

Source: generated PRD baseline risks
