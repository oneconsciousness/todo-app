# todo-app

A full-stack To Do list for an engineering challenge. A user signs in and manages only their own tasks: create, read, update, delete, reorder and search, with a detail screen per task and a responsive UI. `backend/` is a REST API in Python (FastAPI, async SQLAlchemy, alembic, Postgres). `frontend/` is a React SPA in TypeScript (Vite, TanStack Query, Zod, Tailwind). The app is built to run as more than one backend replica: containers first, then a local k3d cluster, then AKS.

## Read first
- `docs/kickoff.md`: the requirements, the human's feedback and the locked decisions. It is the spec; plans in `docs/plans/` build on it.
- `CONTRIBUTING.md`: branches and deploy stages (§1), branch names and PR labels (§2), test gates (§5), the kind-stop protocol (§8), human-runs-it for ops and deploys (§11), secrets (§12).
- `.claude/rules/`: working agreement, coding standards, testing and git rules load every session. Python, database, API contract, TypeScript, React and deployment rules load when you touch matching files.
- `backend/CLAUDE.md` and `frontend/CLAUDE.md`: each app's commands, config and layout.
- Skills: `/repo-sync` at the start of a session, `/verify` before saying done or committing, `/claude-docs-check` then `/raise-pr` to open a PR.

## Hard requirements that shape every change
- Test-driven: red, green, refactor, and every commit is green. Each test layer owns different failures; no test repeats another layer's job (`testing.md`).
- Functional and declarative: a pure core with an I/O shell, no mutated inputs, composition and higher-order functions, `map`/`filter`/`reduce` and comprehensions, the right data structure (`coding-standards.md`).
- Async through high-level abstractions: async FastAPI and SQLAlchemy with `TaskGroup` on the backend, TanStack Query on the frontend.
- Logs that help monitoring stay (startup, ready, caught errors with context); logs added only to debug go before the commit. No `TODO` or `FIXME` in code.
- HTTP semantics as in `api-contract.md`, including 400 (not FastAPI's default 422) for validation errors and 404 for another user's task.

## Commands
```bash
python3 scripts/check_hygiene.py      # task markers, debuggers, focused tests, debug-only logs; CI runs it
GIT_SHA=$(git rev-parse --short HEAD) docker compose up --build --wait   # the stack, on http://localhost:8080
docker compose down                   # stop it; `down -v` also deletes the database
```
Each app's own commands are in its `CLAUDE.md`; `CONTRIBUTING.md` § 5 lists every gate.

The stack is Postgres, a one-shot `migrate` service, two API replicas and nginx. It needs a `.env` in the repo root, which the human creates once with `cp .env.example .env`. Three suites run against it:
- Live-server e2e, `e2e/live/` (pytest, Python 3.14.8): `cd e2e/live && uv run pytest`. CI also runs ruff and mypy there.
- Browser journeys, `e2e/browser/` (Playwright, Chromium): from that folder, `npm ci && npx playwright install chromium` once, then `npm run check && npm test`. The HTML report goes to `playwright-report/`.
- Load, `load/` (k6 in a compose container): `GIT_SHA=$(git rev-parse --short HEAD) docker compose --profile load run --rm k6 run /scripts/journey.js`. `VUS` and `HOLD` set the users and the hold time (200 and 3m by default). `python3 load/run_stepped.py` steps up the users to find the capacity. Results go to `load/results/`. Run load tests with the lead present.

## Config and secrets
- `.env.example` is the only env file an agent may read or edit, by that exact name; it holds safe local values and never a real secret. Never read or edit `.env` or any other `.env.*` file, or key material. Hooks and the deny list block them, and a Bash command that only names such a file is blocked too. When a setting is needed, add it to `.env.example` with a safe local value; the human copies it into `.env` and sets real values there.
- `.mcp.json` configures Claude Code's own MCP servers. It is not the app's config.

## Workspace rules
This repo sits inside a larger workspace whose `.claude/rules/` also load. The general rules there apply (PR card, assignee, no auto-reviewers, typed boundaries, failure handling). The product-specific protocols do not: seed compile and migrate, planner templates, ThinkingBlock, user cleanup scripts, turbo logs, and sibling contract repos. There are no sibling repos here.

## Gotchas
- `transcript-backup.py` snapshots the session transcript into `.ai-transcripts/` before and after every compaction and at session end, and blocks a compaction it could not back up. The snapshots are the record of AI use; never delete them.
- macOS ships bash 3.2 and Python 3.9. Repo scripts and hooks are Python standard library and start with `from __future__ import annotations`, so they run on a reviewer's Mac; CI tests them on 3.9 and 3.13. The guard hooks fail closed: a crash denies the call.
- The Bash guards read every word of a command, heredoc bodies included. Text that names an env file or a reader program trips them: write prose with the Write tool, and commit such messages with `git commit -F <file>`.
- The three Bash guards share `.claude/hooks/shell_words.py`. A change there changes all three; run `python3 -m unittest discover -s .claude/hooks/tests` under `/usr/bin/python3` as well as 3.13.
- The branch-protection hook blocks every commit on `main`. Branch first.
- FastAPI answers validation errors with 422 unless the app's handler maps them. Keep the handler; the contract says 400.
- Set `GIT_SHA` on every compose command that builds or runs, `docker compose run` included. Images are tagged with it and fall back to `local`; a command under another tag makes compose recreate the running stack.
- `load/run_stepped.py` runs `docker compose down -v` before each step. That deletes the local database and every account in it.
- The browser journeys fail on any `console.error`, uncaught exception or CSP violation in the page, except a 401 from `/api/` (`e2e/browser/fixtures.ts`).

## Branches and deploy
- Each round has an integration branch, `round/<n>-<name>`, and one parent PR into `main` that merges only when the round is done and tested. Work on a branch off the round branch and open a child PR into it; the human lead reviews every PR. Child PRs are squash-merged, the parent is rebase-merged (`CONTRIBUTING.md` § 1). Releases are `vX.Y.Z` tags; a tag is never moved.
- CI runs on every PR: hygiene, the backend and frontend gates, and an `e2e` job that builds the stack and runs the live and browser suites against it.
- Deploy stages are in `.claude/rules/deployment.md`. The human reviews every deployment artifact before it is applied, and runs anything against AKS.
- Guards: a hook blocks commits and pushes on `main` and on round branches, force pushes, `--no-verify` and tag moves. `git push`, `gh pr create`, `kubectl apply`/`delete`, `helm` and `az` always ask. PR titles must be Conventional Commits. A PR also needs a docs decision from `/claude-docs-check`.

## Scope
Change only what the task names. Do not fix nearby code or add tests the change does not need. Unrelated problems go in a one-line follow-up note.
