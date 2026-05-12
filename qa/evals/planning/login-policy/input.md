# Login Policy Regression

## Scope

- Improve the login flow so users can submit email and password and land on the dashboard.
- Keep the existing dashboard navigation working after authentication.

## Acceptance Criteria

- User can open the login page.
- User can enter email.
- User can enter password.
- User can submit valid credentials.
- User sees Dashboard after successful submit.
- Locked users see account recovery guidance before retrying.
- Expired sessions return the user to login before protected dashboard access.

## Regression Notes

- Existing dashboard navigation must continue to work after login.
- The smoke scenario should remain stable enough to automate across dev and staging.
