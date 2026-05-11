# QA Scope: Login

## Sources

- `qa/dogfood/login/inputs/ticket.md`
- `qa/dogfood/login/inputs/policy.md`
- `qa/dogfood/login/inputs/design-notes.md`

## Goal

The login flow is being hardened for the next sprint so that users can reach the dashboard reliably while security-sensitive states stay clear and recoverable.

## Extracted Source Facts

| Fact Type | Fact | Source |
| --- | --- | --- |
| Feature Goal | The login flow is being hardened for the next sprint so that users can reach the dashboard reliably while security-sensitive states stay clear and recoverable. | `ticket.md#Summary` |
| Feature Goal | Authentication copy and error states must avoid account enumeration and give recoverable users a next step. | `policy.md#Summary` |
| Feature Goal | The web login screen uses semantic labels and stable test IDs so Newton can execute the flow without visual inference. | `design-notes.md#Summary` |
| States | User can open login page from a direct `/login.html` route | `ticket.md#Acceptance Criteria` |
| States | User can enter email | `ticket.md#Acceptance Criteria` |
| States | User can enter password | `ticket.md#Acceptance Criteria` |
| States | User can submit valid credentials | `ticket.md#Acceptance Criteria` |
| States | User sees Dashboard after successful submit | `ticket.md#Acceptance Criteria` |
| States | Locked users see account recovery guidance before retrying | `ticket.md#Acceptance Criteria` |
| States | Expired sessions return the user to login before protected dashboard access | `ticket.md#Acceptance Criteria` |
| States | Error message does not expose whether email exists | `policy.md#Acceptance Criteria` |
| States | Password failures keep the user on the login page with retry guidance | `policy.md#Acceptance Criteria` |
| States | Locked accounts show account recovery guidance instead of generic failure copy | `policy.md#Acceptance Criteria` |
| States | Session timeout requires a fresh login before opening protected dashboard content | `policy.md#Acceptance Criteria` |
| States | Email field is exposed as a textbox named Email | `design-notes.md#Acceptance Criteria` |
| States | Password field exposes `data-testid="password-input"` | `design-notes.md#Acceptance Criteria` |
| States | Primary action is a button named Log in | `design-notes.md#Acceptance Criteria` |
| States | Successful submit reveals visible Dashboard text | `design-notes.md#Acceptance Criteria` |
| Policies | Security copy must not confirm account existence. | `policy.md#Policy References` |
| Policies | Recovery guidance is required for locked accounts. | `policy.md#Policy References` |
| Regression Areas | Existing dashboard navigation must continue to work after login. | `ticket.md#Regression Notes` |
| Regression Areas | The smoke scenario should remain stable enough to automate across dev and staging. | `ticket.md#Regression Notes` |

## In Scope

- Validate the primary user flow described in the source context.
- Cover the listed acceptance criteria as manual checklist items.

## Out of Scope

- Cross-browser matrix expansion.
- Performance, security, and accessibility deep dives unless explicitly listed in the source context.
