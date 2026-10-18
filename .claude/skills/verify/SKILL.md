---
name: verify
description: Run the checks that make "done" true before reporting a task complete or committing. No side effects beyond running checks and tests.
---
# Verify before saying done

1. Gates. Run what CI runs for every part the change touched, from the repo root. Skip a part only when it does not exist yet, and say so.
   - Hygiene: `python3 scripts/check_hygiene.py`
   - Hooks, when `.claude/hooks/` changed: `python3 -m unittest discover -s .claude/hooks/tests`
   - Backend: `cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest`
   - Frontend: `cd frontend && npm run check && npm run test && npm run build`
   - When the change touches the running stack (Dockerfiles, compose, manifests, config, CORS, routing): bring the stack up and run the live-server e2e and Playwright suites against it, following `CONTRIBUTING.md` § 14 for restarts.
   Report the exact counts per suite and the stack each ran against. A failure is reported as a failure, with the output.
2. Read back. Read `git diff` for every file you changed. Check each hunk does what the task asked and nothing more.
3. Logs. For every log line in the diff, say what it helps someone monitor. Delete any line added only to debug.
4. Tests. For every test in the diff, name the failure it catches that no other test catches. Delete a test that has none.
5. Side effects. For every function, component, model, field or constant you changed or removed, grep the repo for other users. Fix or list them.
6. Secrets. Scan the diff for keys, tokens, passwords, connection strings. None may be in it.
7. Contract check, when the change sends data across a boundary: read the receiving side's type first (the Pydantic model, the Zod schema, the migration), not the docs, and convert explicitly. A change to an API model changes the Zod schema in the same PR.
8. Plan adherence, when working from a written plan: diff your output against the plan's fields, endpoints and names. Anything missing or extra is a bug until the human says otherwise.

Then report: what was verified, what was not, and why.
