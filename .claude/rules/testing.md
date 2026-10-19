# Testing

Robust testing is a hard requirement, and so is test-driven development. Applies to every change.

## Test first
- Red, green, refactor. Write the test, run it and watch it fail for the expected reason, write the least code that makes it pass, then clean up with the test still green. Run the red step in the session so the transcript shows it.
- Every commit is green. All suites that the change touches pass before `git commit`; a failing test is never committed. A commit holds the test and the code that passes it together.
- New behaviour gets a test in the same commit. A bug fix starts with a test that reproduces the bug.

## Each layer earns its place
Test a behaviour once, at the lowest layer that can catch it. A higher layer covers only what the lower layers cannot see. Before adding a test, name the failure it catches that no existing test catches; if there is none, do not add it.

| Layer | Tool | Owns | Does not re-test |
|---|---|---|---|
| Backend unit | pytest | pure functions in the core: ordering, search filters, validation, token and password helpers | anything HTTP or SQL |
| Backend integration | pytest, httpx `ASGITransport`, a real database | each endpoint's contract: status codes, response shape, auth, ownership, persistence | the pure rules already unit-tested, beyond one case that proves the wiring |
| Frontend unit and component | Vitest (its API matches Jest's), React Testing Library, MSW at the `fetch` boundary | pure helpers, hooks, and each screen's states: loading, empty, error, success, validation | backend rules |
| Live-server e2e | pytest against the running stack (compose, then k3d) | what only a deployed stack shows: migrations ran, the proxy and cookie path, ingress and routing, a session issued by one replica accepted by another | endpoint contracts |
| Browser e2e | Playwright against the running stack | a few complete user journeys: sign in, create, reorder, search, edit, delete, sign out; and the small-screen layout | screen states and endpoint contracts |
| Load | k6 from its container against the running stack | latency and error budgets at 200 concurrent users, data consistency afterwards, and the round's capacity figure from a stepped run | correctness of single requests |

## Concurrency
- Each race in the spec has an integration test named after it that fires the requests together with `asyncio.TaskGroup` against a real Postgres. Each one must fail when its guard is removed; show that once, in the session.
- A fixture runs the backend suite in asyncio debug mode with a 50 ms slow-callback threshold and fails any test during which the event loop was blocked.
- The race tests and the load tests are run with the lead present: show the scripts and budgets first, then walk through the results.

## Mechanics
- Mock at the boundary (the HTTP client, `fetch`, the clock), never inside the code under test. Nothing in a unit suite opens a socket.
- Tests are independent and order-free. Each builds its own data through factories or fixtures; none relies on another's leftovers.
- Assert on behaviour a user or caller can see: status, body, rendered text and roles. Never on private attributes or CSS class names.
- One reason to fail per test. The name says the behaviour: `test_reorder_rejects_task_owned_by_another_user`, `it("shows the empty state when the user has no tasks")`.
- Coverage is a floor, not a target: CI fails below the threshold set in `pyproject.toml` and `vitest.config.ts`. A line covered by a test that asserts nothing is not covered.
- Report results as they are. "128 passed" means you saw it. Name the suite and the stack it ran against.
