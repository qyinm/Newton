# Authentication Policy

## Summary

- Authentication copy and error states must avoid account enumeration and give recoverable users a next step.

## Policy References

- Error message does not expose whether email exists.
- Recovery guidance is required for locked accounts.

## Acceptance Criteria

- Invalid credentials show generic guidance.
- Locked users see recovery guidance.
- Suspended users cannot reach the dashboard.
