# Kickoff — requirements, feedback and decisions

The spec for this repo. Written 2026-10-18 at the start of the first session, after the challenge brief was read and reviewed with the human lead. Plans in `docs/plans/` build on it; when a plan and this file disagree, stop and ask.

## 1. What we are building

A full-stack To Do list: a web client and our own backend API. A user signs in and does full CRUD on their own tasks, and only their own.

| Area | Requirement |
|---|---|
| Backend | A REST-style API: resource URLs, standard methods, JSON. Status codes: 200/201 success, 400 validation, 401/403 auth, 404 missing. |
| Frontend | Connects to our API. Sign-in landing page, task list after sign-in, reorder, search, a task detail screen to view and edit, full CRUD. Responsive. |
| README | Running on a Mac; deployment to distributed cloud infrastructure; overall approach; features completed; what we would add with more time and how long it would take; what we would do to make it more robust. |
| Code | In a shareable git repo, runnable by the reviewers, community-standard style, no debug-only logging, no `TODO` or `FIXME`, tested. |
| Style and practice | Clean code, concise but descriptive. Test-driven. Functional and declarative (higher-order functions, composition, `map`/`filter`/`reduce`, the right data structures). Async through high-level abstractions. |

Missing the minimum criteria ends the interview, so "the reviewers can run it" comes first, and every design choice must be one we can explain in a live deep-dive.

## 2. The human lead's feedback (verbatim) and what it means for the work

> 1. TBH, one thing to keep in mind is that the Bonus note on `TDD. Functional, declarative style (higher-order functions, composition, map/filter/reduce, correct data structures). Async through high-level abstractions.` is not a Bonus. Consider it an ALL IN Hard req.

TDD, functional style and high-level async are hard requirements, written into `coding-standards.md`, `testing.md` and the reviewer agent.

> 2. Great catch on the vald status code.

FastAPI's default 422 for validation errors is mapped to 400 in one handler (`api-contract.md`).

> 3. On the debug logging note: Logs are fine, just ensure we don't have any logs that you added just to debug errors that popped up along the way and ensure every print/console adds value to monitoring for bugs. So for example, printing exception errors, etc is absolutely needed, printing status ready for components/app is needed. I just don't want you to assume that absolutely no logging is allowed. That is not the case here.

Logging stays where it helps monitoring: lifecycle (startup, ready, shutdown), caught exceptions with context, warnings on auth or validation failures and degraded paths. Lines added only to chase a bug are removed before the commit. Backend uses `logging`; frontend uses `console.info`, `warn` and `error`, never `log` or `debug` (`coding-standards.md`, enforced by ESLint and `scripts/check_hygiene.py`).

> 4. On testing frameworks, lets use Vitest and note down that the API matches JEST. also it feels like a general guidance to me that robust testing is an absolute requirement. All tests should be passing before we commit. Every test (unit, integration, live server e2e tests, and playwright tests) should all add unique value. I don't want redundancy across tests just for the sake of bloating our test scene.

Vitest on the frontend (its API matches Jest's; the README says so), pytest on the backend. Every commit is green. Five layers, each owning failures the others cannot see; a test that repeats another layer's job is not added (`testing.md`, "Each layer earns its place"). Red-then-green happens inside the session, so the shared transcript shows each failing run before the passing one, and each commit holds the test and the code together.

> 5. We'll deploy towards the end, but i think we should definitely deploy. We'll initially build and test with sep docker container. once proven that the app works and all functonality works as expected, code is reviewed and tests are run -> then, we'll test and run locally using kubernetes (we'll setup a k3d cluster since the task mentions a bonus for distributed deployment efforts...do you agree on this note?). and we'll deploy on an azure subscription where we'll have a AKS cluster setup. We could use github actions then for deployment. I want to review each of the deployment artifacts before we deploy. Additionally, we'll focus on development on a local k3d cluster. Once everything is proven and working seamlessly and meeting my expectations, we'll proceed with AKS later if time permits.

Agreed on k3d. It runs k3s, a certified Kubernetes, so the same manifests carry over to AKS with only an overlay per target, and it lets us prove the distributed parts on a laptop: several backend replicas behind a Service, a migration Job, probes, rolling updates. That forces the right design early: a stateless backend (signed tokens, no in-memory sessions) and a shared Postgres, never in-memory or file storage. Stages: separate containers with `docker compose` → local k3d → AKS through GitHub Actions if time permits. The human reviews every deployment artifact before it is applied (`deployment.md`, `CONTRIBUTING.md` § 11).

> 6. I also want to review all the coding instructions before we begin. Not now, after we write out the detailed coding plan, you'll walk me through the instruction in chat along with code samples, commenting style samples, type checking samples, etc.

A gate before any app code: after the detailed coding plan, a walkthrough in chat of every coding instruction, with code, comment-style and type-checking samples. Coding starts only after the human signs off.

> 7. I also want to save this chat's transcript. It possible to find the json file. I've done this in the past for another interview. We saved the file with transcript, timestamps and all other info. If we can share this with the interviewing team, that would resolve all their questions on my AI usage for completing this assessment.

Claude Code writes each session as JSONL, one event per line with a timestamp, under `~/.claude/projects/<encoded project path>/<session id>.jsonl`, with subagent runs in a folder of the same name. At the end we export the session files into `docs/ai-usage/`, scan them for secrets and personal details before they are committed, and derive the human-versus-agent time split from the timestamps (see decision 4).

> 8. Skeleton setup - OK

## 3. Locked decisions

| # | Decision |
|---|---|
| 1 | The repository is `todo-app`, local for now, public on GitHub later. Creating the remote waits for the human's go. |
| 2 | The frontend uses Node and npm (no Bun), so the reviewers need nothing beyond Node, plus `docker compose up` as a one-command run. ESLint and Prettier for style. |
| 3 | ~~The env and secrets hooks stay as they are, `.env.example` included.~~ Changed by the lead on 2026-10-19: "I would like you to carefully update the hook such that you can create and edit only the .env.example. Ensure to test to ensure there are no loopholes." Agents now create and edit `.env.example` by its exact name; every other env file stays closed, and `.claude/hooks/tests/test_secret_guards.py` pins the boundary (`CONTRIBUTING.md` § 12.2). |
| 4 | The final report makes the split between human and agent work easy to see, derived from the transcript timestamps, alongside the agent-pair estimates the workspace rule asks for. |
| 5 | PRs carry one label taken from the branch prefix (`CONTRIBUTING.md` § 2). |
| 6 | One monorepo: `backend/`, `frontend/`, and later `e2e/` and `deploy/`, with one root `.claude/`. |
| 7 | The challenge brief (`TASK.md`) is committed at the repo root, unchanged. |
| 8 | Every change reaches `main` through a branch and a PR. The agent shows the PR card and waits for a yes; the human reviews and merges each PR. |
| 9 | Three rounds: round 1 runs in containers (`docker compose`), round 2 on a local k3d cluster, round 3 live on AKS. Each round starts after the previous one is proven and signed off. |
| 10 | The session transcript is snapshotted before every compaction, so no compaction can lose its contents (`.claude/hooks/transcript-backup.py`). |
| 11 | High-level choices and a solution diagram are specced and signed off (a Claude artifact) before the detailed coding plan is written. |

## 4. Sequence and gates

1. Repo skeleton: the Claude Code setup adapted from the template repo and upgraded with the rules above. Pause for review.
2. Spec of the high-level choices with a solution diagram, published as a Claude artifact and kept in `docs/specs/`. The human signs off.
3. Detailed coding plan in `docs/plans/`: data model, endpoints, screens, test plan per layer.
4. **Gate:** walkthrough of the coding instructions with samples; the human signs off.
5. Build, test-first: backend, then frontend, then containers, with the human reviewing at regular points.
6. **Gate:** round 1 (containers) proven, code reviewed, every suite green → round 2, local k3d.
7. **Gate:** round 2 (k3d) proven and the human satisfied → round 3, AKS through GitHub Actions, if time permits. Every deployment artifact reviewed before it is applied.
8. README, the transcript export and the human-versus-agent time report.

## 5. Open for the spec phase

- Auth: how accounts exist (sign-up screen or seeded users), token format and lifetime, where the frontend keeps the token.
- Ordering: how positions are stored so a reorder is one cheap, consistent write.
- Search: server-side or client-side, which fields, and whether it combines with ordering.
- Task fields beyond title and done state (description, due date, priority).
- Deployment target details: ingress, the managed Postgres choice for AKS, and how images reach the cluster registry.
