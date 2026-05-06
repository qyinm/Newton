# Login Design Notes

The web login screen uses semantic labels and stable test IDs so Newton can execute the flow without visual inference.

Acceptance Criteria:
- Email field is exposed as a textbox named Email
- Password field exposes `data-testid="password-input"`
- Primary action is a button named Log in
- Successful submit reveals visible Dashboard text

Design References:
- Use role/name selectors for visible controls.
- Use the password test ID because password fields can be inconsistently named by browsers.
