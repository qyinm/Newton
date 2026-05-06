# Login Policy

Authentication copy and error states must avoid account enumeration and give recoverable users a next step.

Acceptance Criteria:
- Error message does not expose whether email exists
- Password failures keep the user on the login page with retry guidance
- Locked accounts show account recovery guidance instead of generic failure copy
- Session timeout requires a fresh login before opening protected dashboard content

Policy References:
- Security copy must not confirm account existence.
- Recovery guidance is required for locked accounts.
