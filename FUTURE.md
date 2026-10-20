# Future work

Ideas we chose not to build in rounds 1 to 3, and why each is worth doing. The README's "given more time" section draws from this list.

## Identity
- **Sign-in with Microsoft, Google or Apple.** OpenID Connect through the provider each client already uses (Microsoft Entra ID for a Microsoft shop, Google or Apple for consumers). Email and password stay as the fallback.
- **Refresh-token rotation and revocation.** Short-lived access tokens, a rotating refresh token, and a deny list, so a stolen or signed-out session can be ended before it expires.
- **Email verification and password reset.** Both need an outbound email service.

## AI features (after everything else works)
- **Create and update tasks by describing them.** The user types or speaks ("move the dentist to Friday and add a note to bring the form") and the app turns that into task creates and updates. The model's output is untrusted: it is parsed into the same typed models the API already validates, and the user confirms the changes before they are applied.
- **An AI summary home page.** A home screen that summarises what is due, overdue and done, streamed to the client, possibly built on the AG-UI protocol for agent-to-UI events.

## Data and scale
- **Rank rebalancing.** A background job that rewrites long ranks in a list to short ones, run when a rank passes a length limit.
- **Paging for long lists.** A cursor on `GET /api/v1/tasks`; the `{"items": [...]}` envelope already leaves room for it.
- **Sign-in rate limiting.** It needs a store shared by every replica (Redis, or the ingress), so it waits for round 2 or 3.

## Security
- **Self-host the API docs page, or turn it off in production.** `/api/docs` loads Swagger UI from jsDelivr under a floating major version, with no integrity check, and its CSP allows one inline script by hash. Serving pinned Swagger UI files from the API, or disabling the page where cookies are secure, removes the third-party script before the app is public.
