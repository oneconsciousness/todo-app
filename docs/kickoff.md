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
| 8 | Every change reaches `main` through a PR, and since 2026-10-19 through a round: child PRs into the round branch (squash-merged), one parent PR per round into `main` (rebase-merged). The agent shows the PR card and waits for a yes; the human lead reviews and merges every PR. |
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

## 5. Spec review, round 1 (verbatim) and what it settled

The round 1 spec is `docs/specs/round-1.html`, published as a Claude artifact. The lead's first review:

> 1. Remind me before we submit to make the artifact public and also we'll include in the final report.
> 2. Well done, on the presentation. It neat and easy to skim and understand.
> 3. I understand you want to prove memory isn't saved in the backend api and its isolated with the replica. I think, let's save that for round 2.
> 4. Good on postgresql for storage and all replicas must share one store, true.
> 5. I want to hear your thoughts on the following topics within the spec itself `Async and concurrency`, `Races and consistency` and Testing and Explainability against those topics too from a FastAPI/Uvicorn pov keeping mind that many users would use the application at the same time. Its important we take this into account during our spec and planning stages itself so the expectation is set straight.
> 6. For the frontend, I'd like you to create a design artifact first of every screen. I'll review the design tokens before we proceed to build frontend. note this down as the order in the spec. This will be run in parallel while writing the plan. Build the design artifact such that you can directly reuse those components for the actual frontend too. Reduce the redundancy of your work.

> DECISIONS:
> 1. Agreed. It also allows for the reviewer to script the testing in bulk if required. we should also test this before we submit, i.e., load testing.
> 2. Agreed. It secure enough for this demo. Note down as something we would implement in the future (i recommend a FUTURE.md doc) that we would use msft or google login or apple login depending on client needs.
> 3. Agreed! Appreciate the well thought of walkthrough of D6 in spec. helped me understand your thought process!
> 4. This is well thought off. I like the 250ms touch. its great!
> 5. I agree. Note down here that. After all functionality is working fine, we may change the create/update new task to essentially an AI operation if time exists. where the user describes in text or voice what they want to create/update and we update. For now, put it in FUTURE.md. We could also have a TASK summary home page driven by AI in the future, potentially using a framework like AGUI.
> 6. Yeah tbh, that's fine with me! I understand the intent. scratch my guidance in the thoughts/feedback point 3.
> 7. Agreed.

> Additional notes: agreed on endpoints, check on whether (health vs healthz; what is expected and the best practice).

What it settled:

| Spec id | Locked |
|---|---|
| D3 | Open sign-up and sign-in by email and password. Reviewers can script bulk tests against the API (OpenAPI docs at `/api/docs`). A load test runs before submission. |
| D4 | JWT in an httpOnly `SameSite=Strict` cookie, 8 hours. Sign-in with Microsoft, Google or Apple goes in `FUTURE.md`. |
| D6 | Fractional ranks; new tasks at the top; reordering off while searching. |
| D7 | Server-side search over title and notes, trigram index, 250 ms debounce. |
| D8 | Fields: title, notes, completed, due date. AI task entry (text or voice) and an AI summary home page (possibly AG-UI) go in `FUTURE.md`. |
| D10 | Two API replicas from round 1, with `X-Served-By`. Feedback point 3 is withdrawn by decision 6. |
| D12 | Coverage floors: 90% backend, 85% frontend. |
| Order | The frontend starts with a design artifact of every screen, built from the real components, made while the plan is written; the lead reviews the design tokens before the frontend is built. |
| Endpoints | Agreed, with the health check naming researched in revision 2 (D19). |

Revision 2 of the spec answers points 5 and 6 and the health check question with D13 to D20, signed off below.

## 5a. Spec review, round 2 (verbatim) and what it settled

> D13 - Understood well and agreed.
> D14 - Understood well and agreed. It will make a difference on high app load.
> D15 - Understood well and agreed. It would also be good to showcase realistic numbers in our final report on how many concurrent users we could end up handling at the end of each round.
> D16 - Understood and agreed. I would like to actively involved when we test this.
> D17 - Is this specifically to overcome cases where two tabs update the same todo item one after the other and tab 2 doesn't have the tab 1 update loaded? validate my understanding. I also believe, that a good todo app's tab when in focus by the user should refresh and update every time the user comes back to focus on that tab. that way we won't run into edit mismatches.
> D18 - a load test is an amazing idea. Agreed! Keep me actively in the loop.
> D19 - agreed.
> D20 - agreed.
>
> 1/ Agreed on endpoints. 2/ Agreed on tables. neat and concise. 3/ Screens. Agreed! 4/ Tests. Agreed! 5/ For the design - tips: stellar look and premium feel + vintage colors + 0 redundancy.

What it settled: D1 to D20 are locked (spec revision 3), and the rules carry them (`api-contract.md`, `testing.md`, `deployment.md`, `python.md`, `database.md`).

| Spec id | Note |
|---|---|
| D15 | The final report gives a measured concurrent-user capacity for each round. |
| D16, D18 | The lead takes part in the race tests and the load tests. |
| D17 | The lead's understanding is right. Refetch on focus is the first layer, a "Changed elsewhere" notice covers unsaved drafts, and `If-Match`/412 is the guarantee. |
| Design | A stellar look, a premium feel, vintage colours, zero redundancy. |
| Wire format | JSON field names are camelCase, so the frontend uses the API's shapes without a mapping layer (agent decision, recorded in `api-contract.md`). |

## 5b. Plan review (verbatim) and what it settled

> 1. On the sdk/library versions - did the sub-agent planner ensure to research the web for official docs, find the latest+stable version before proceeding? also ensuring to review the community for any known bugs. If not, please send the same sub-agent back to do this step.
> 2. While reviewing `3.5.3 Migration 0001_initial_schema`, i had a question. I hope we're also planning to verify if its an actual email address, i.e., does it have '@' and other basic tests.
> 3. White reviewing `3.7.1 rank_between`, did you check to ensure ask per the TASK.md (`● Bonus points: Code in a functional, concise, declarative way. Things we will look for:higher-order functions, function composition, correct use of basic data structures and manipulations (map, reduce, apply, etc.)`) has been taken into consideration, researched and well planned?
> 4. I've reviewed the plan in detail. On the open questions, I agree with your (tech lead) decision making.
>
> What's left/next? List out the todo list in chat, I'll review and give you the go ahead. Note: We should wait for design to be approved as well before we begin coding.

What it settled:

| Item | Outcome |
|---|---|
| Plan Q-1 to Q-13 | Locked as the tech lead recommended. Spec revision 3.1 carries the errata (Q-1 `afterId`, Q-2 plain-text 503); `python.md` (Q-4), `typescript.md` (Q-9) and the docs map (Q-10) are updated. |
| Versions | The planner had not researched current stable versions or known bugs. Sent back to pin every dependency from official sources with known issues and mitigations. |
| Email | Three layers: Zod in the form, Pydantic `EmailStr` in the API, a basic-shape `CHECK` in the database, each tested. |
| Functional style | `rank_between` redesigned declaratively, and a "Functional style map" section ties each `TASK.md` item to concrete code. |
| Order | Coding starts only after the design is approved and the instructions walkthrough is done. |

## 5c. Design sign-off (gate G2)

> Design looks good to me! Nice vintage color choice and nice touch on the notepad style edit looks.

Signed off 2026-10-19 10:52 EDT, on the design artifact built from `feature/web-design-system` (the bookkeeper's ledger direction). One polish fix (a balanced cover subtitle) follows before its PR.

## 6. Before submission

- [ ] Share the spec artifact, and the design artifact, so the reviewers can open them; put the links in the final report.
- [ ] Run the load test (D18) with the lead, and quote its results and each round's capacity figure in the README.
- [ ] Export the session transcripts from `.ai-transcripts/` into `docs/ai-usage/` after a secrets and personal-data scan; write the human-versus-agent time split.
- [ ] Make the GitHub repository public.
