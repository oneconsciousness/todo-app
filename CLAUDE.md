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
```
Each app's own commands are in its `CLAUDE.md`; `CONTRIBUTING.md` § 5 lists every gate.

## Config and secrets
- Never read or edit `.env` files, `.env.example` or key material. Hooks and the deny list block it, and a Bash command that only names such a file is blocked too. When a setting is needed, post the exact lines in chat and the human adds them.
- `.mcp.json` configures Claude Code's own MCP servers. It is not the app's config.

## Workspace rules
This repo sits inside a larger workspace whose `.claude/rules/` also load. The general rules there apply (PR card, assignee, no auto-reviewers, typed boundaries, failure handling). The product-specific protocols do not: seed compile and migrate, planner templates, ThinkingBlock, user cleanup scripts, turbo logs, and sibling contract repos. There are no sibling repos here.

## Gotchas
- `transcript-backup.py` snapshots the session transcript into `.ai-transcripts/` before and after every compaction and at session end, and blocks a compaction it could not back up. The snapshots are the record of AI use; never delete them.
- macOS ships bash 3.2. Repo scripts are Python 3 standard library, like the hooks, so they run on a reviewer's Mac and in CI.
- The branch-protection hook blocks every commit on `main`. Branch first.
- FastAPI answers validation errors with 422 unless the app's handler maps them. Keep the handler; the contract says 400.

## Branches and deploy
- Work on a branch off `main`. PR to `main`, squash-merge. Releases are `vX.Y.Z` tags; a tag is never moved.
- CI runs on every PR: hygiene, plus the backend and frontend gates as those apps land.
- Deploy stages are in `.claude/rules/deployment.md`. The human reviews every deployment artifact before it is applied, and runs anything against AKS.
- Guards: a hook blocks commits and pushes on `main`, force pushes, `--no-verify` and tag moves. `git push`, `gh pr create`, `kubectl apply`/`delete`, `helm` and `az` always ask. PR titles must be Conventional Commits. A PR also needs a docs decision from `/claude-docs-check`.

## Scope
Change only what the task names. Do not fix nearby code or add tests the change does not need. Unrelated problems go in a one-line follow-up note.
