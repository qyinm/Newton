# Login

The login flow is being hardened for the next sprint so that users can reach the dashboard reliably while security-sensitive states stay clear and recoverable.

Acceptance Criteria:
- User can open login page from a direct `/login.html` route
- User can enter email
- User can enter password
- User can submit valid credentials
- User sees Dashboard after successful submit
- Locked users see account recovery guidance before retrying
- Expired sessions return the user to login before protected dashboard access

Regression Notes:
- Existing dashboard navigation must continue to work after login.
- The smoke scenario should remain stable enough to automate across dev and staging.
