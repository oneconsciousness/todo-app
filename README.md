# todo-app

A full-stack To Do list: a React and TypeScript web app and a Python REST API, with a Postgres database. You sign up, then manage your own tasks. It runs on a Mac with Docker Compose, or on a local Kubernetes cluster.

**Quick start:** `cp .env.example .env`, then `docker compose up --build --wait`, then open http://localhost:8080.

| Section | What's in it |
|---|---|
| [What it does](#what-it-does) | The features |
| [How it's built](#how-its-built) | The approach, the stack and the main choices |
| [Run it with Docker Compose](#run-it-with-docker-compose) | The quickest way to run it |
| [Run it on Kubernetes with k3d](#run-it-on-kubernetes-with-k3d) | The app on a three-node cluster, over HTTPS |
| [Run the tests](#run-the-tests) | Six test layers, and how test-first showed up |
| [The code style](#the-code-style) | Where to see the functional style and the async tools |
| [Capacity](#capacity) | How many users it held |
| [Given more time](#given-more-time) | What we would build next, and how long it would take |
| [Making it more robust](#making-it-more-robust) | What we would harden |
| [How it was made](#how-it-was-made) | How AI was used, and the time it took |

## What it does

- **Accounts.** Sign up and sign in with email and password; sign out. Each user sees only their own tasks: asking for someone else's task gets "not found", as if it did not exist.
- **The task list.** Your tasks in your own order. Add a task at the top, tick it done, or delete it after a confirm.
- **Reorder.** Drag with a mouse or a finger, or move with the keyboard. The order is saved on the server.
- **Search.** Type to search titles and notes; results update as you type. Reordering is turned off while you search, so the order stays clear.
- **Task detail.** Open a task to see and edit its title, notes, due date and done state.
- **Edits are never lost silently.** If a task changed somewhere else since you opened it (another tab, another device), saving tells you instead of overwriting it.
- **Any screen size.** The layout works from a phone (375 px) to a desktop.
- **An open API.** REST with standard HTTP answers: 200 and 201 for success, 400 for bad input, 401 when you are not signed in, 404 for a missing task. Its docs are at `/api/docs`, so the API can be scripted directly.

## How it's built

**Approach.** We agreed the requirements first, wrote a short spec of the main choices, and planned the code before writing it. Then we built it test-first, in small pull requests, each one reviewed and merged by the lead. The work came in rounds: round 1 ran it as containers, and round 2 ran the same images on a local Kubernetes cluster. A third round, on a cloud cluster, was left for later for lack of time. The assessment was used to show full-stack skills, so AI features were kept out of the product on purpose (see [Given more time](#given-more-time)).

**The stack.**

| Part | Built with |
|---|---|
| Backend | Python 3.14, FastAPI, Pydantic 2, SQLAlchemy 2 (async, with asyncpg), Alembic, uvicorn |
| Database | PostgreSQL 18 |
| Frontend | React 19, TypeScript, Vite, React Router, TanStack Query 5, Zod 4, Tailwind 4, dnd-kit |
| Front door | nginx: serves the app, proxies `/api/`, sets the security headers |
| Running it | Docker Compose; k3d (k3s) with Kustomize, Traefik and an autoscaler |
| Tests | pytest, Vitest, React Testing Library, MSW, Playwright, k6 |

**How a request flows.** The browser only talks to nginx, which serves the app and passes `/api/` on to the API. App and API share one address, so there is no CORS and the session cookie stays first-party. The API is stateless, so any copy of it can answer any request: two copies run in Compose, and one to two on k3d.

**Main choices.** Each one, with what it beat and what it costs, is in the specs.

- **Postgres from day one,** so every API copy shares one store, with real transactions.
- **The session is a signed token in a cookie** that page scripts cannot read (`HttpOnly`, `SameSite=Strict`). Any API copy can check it, with no session store. Passwords are hashed with argon2id, off the main event loop.
- **Reordering writes one row.** Each task has a sortable text rank; a move gives the task a rank between its new neighbours. A per-user database lock keeps two moves at once from colliding; tests fire them together to prove it.
- **Edits carry a version.** The API sends a task's version as its ETag, and a save sends it back. If the task changed in the meantime, the API answers 412 and the app shows that, instead of losing either edit.
- **Search runs on the server,** over titles and notes, with a trigram index, a quarter of a second after you stop typing.
- **Locked-down containers.** Each runs as a non-root user with a read-only file system and no extra Linux capabilities. nginx sets a strict Content Security Policy and caps request bodies at 64 KB.

**Read more.**

| Document | What it holds |
|---|---|
| [`docs/kickoff.md`](docs/kickoff.md) | The requirements, the lead's words and every decision |
| [`docs/specs/round-1.html`](docs/specs/round-1.html), [`docs/specs/round-2.html`](docs/specs/round-2.html) | The main choices with diagrams, per round. GitHub shows HTML as source, so open them in a browser from a clone |
| [`frontend/design/screenshots/`](frontend/design/screenshots/) | Every screen of the design, light and dark; `npm run design:dev` in `frontend/` opens the live gallery |
| [`docs/plans/round-1.md`](docs/plans/round-1.md), [`docs/plans/round-2.md`](docs/plans/round-2.md) | The coding plans; round 2's is written as built |
| [`tests/load/results/`](tests/load/results/) | Every load run, with how to read it |
| [`FUTURE.md`](FUTURE.md) | Ideas for later, in priority order |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | How we work: branches, PRs, test gates |

## Run it with Docker Compose

You need [Docker Desktop](https://www.docker.com/products/docker-desktop/) running. From the repo root:

```bash
cp .env.example .env                 # once; the example values are fine on a laptop
docker compose up --build --wait     # builds the images and waits until every service is healthy
```

Open http://localhost:8080 and sign up. The API's own docs are at http://localhost:8080/api/docs.

```bash
docker compose down                  # stop the stack; your data stays
docker compose down -v               # stop it and delete the database
```

To run anything beyond a laptop, replace `POSTGRES_PASSWORD` and `JWT_SECRET` in `.env` first; the comments in `.env.example` show how to generate them. Only port 8080 is published, and only on `127.0.0.1`.

## Run it on Kubernetes with k3d

[k3d](https://k3d.io) runs a real Kubernetes cluster ([k3s](https://k3s.io)) inside Docker. The cluster has one server and two agent nodes. The app runs on it as Postgres with its own volume, a migration Job, one API pod (an autoscaler adds a second under load), one nginx pod and an HTTPS front door.

### Once per Mac

1. Docker Desktop must be running, with at least 6 GB of memory (Settings → Resources).
2. Install the tools:
   ```bash
   brew install k3d kubectl mkcert
   ```
3. Let your Mac trust the certificates mkcert makes, so the browser shows `https://localhost:8443` as secure:
   ```bash
   mkcert -install          # asks for your Mac password; adds a local certificate authority
   ```
   Restart the browser afterwards. Firefox also needs `brew install nss` before `mkcert -install`.

### Start it

From the repo root:

```bash
python3 deploy/k3d/deploy.py up
```

The first run takes a few minutes. It creates the cluster `todo`, builds the images for the checked-out commit and loads them into the cluster, creates the secrets, then starts Postgres, runs the migrations and rolls out the app. Every command it runs is printed first. When it finishes, it prints the address.

Open **https://localhost:8443** and sign up. The API's docs are at https://localhost:8443/api/docs.

The secrets are made for you on the first run: a random database password, a random signing key for sessions, and a certificate for `localhost` from mkcert. Their values are never printed or saved to a file. To use your own instead, create them before the first `up`:

```bash
kubectl create namespace todo
kubectl create secret generic todo-db -n todo --from-literal=password="$(openssl rand -hex 24)"
kubectl create secret generic todo-api -n todo --from-literal=jwt-secret="$(openssl rand -hex 32)"
kubectl create secret tls todo-tls -n todo --cert=<your-cert.pem> --key=<your-key.pem>
```

### See it spread over the cluster

```bash
kubectl get pods -n todo -o wide                                   # one pod of each at rest; under load a second api pod, on another node
curl -s --cacert "$(mkcert -CAROOT)/rootCA.pem" -D - -o /dev/null https://localhost:8443/api/v1/auth/me   # run it a few times: X-Served-By names the pod that answered
kubectl get hpa -n todo --watch                                    # the autoscaler: CPU against its 70% target, and the pod count
```

The autoscaler adds an API pod when the pods average over 70% of their CPU, up to two, and removes the extra pod after two quiet minutes. To see it work, put some load on the app (see the load test below) and watch `kubectl get hpa`. Postgres stays one pod with its data on a volume; it is not scaled.

**Sized for a laptop.** Everything starts at one replica and the API stops at two, because we don't know the Mac it runs on. Releases and scaling lose no request at that size, but if the only API pod dies, requests fail for about 15 seconds until its replacement is up. For a heavy load test, or to keep a spare pod, raise the limits to suit your machine: `kubectl patch hpa api -n todo -p '{"spec":{"minReplicas":2,"maxReplicas":5}}'`, or change `deploy/base/app/hpa.yaml` and run `up` again. Five API pods is the most the database's connections allow.

### Update, stop and remove it

```bash
python3 deploy/k3d/deploy.py up      # after a new commit: rolls the app out to it, one pod at a time
k3d cluster stop todo                # stop the cluster; your data stays
k3d cluster start todo               # start it again
python3 deploy/k3d/deploy.py down    # delete the cluster and its data
```

Images are tagged with the commit, so `up` rolls out committed code only; commit a change before running it again. Compose (port 8080) and k3d (port 8443) can run at the same time, but together they need more memory.

### If something goes wrong

| What you see | What to do |
|---|---|
| The browser warns that the connection is not private | Run `mkcert -install` and restart the browser. A Mac that never ran it does not trust the certificate. |
| `missing k3d` (or another tool) | `brew install` the tool it names. |
| `port 8443 is already allocated` | Another program uses the port. Stop it, or delete the cluster and start again. |
| Pods stay `Pending` | Docker Desktop needs more memory. |
| Anything else | `kubectl get pods -n todo` shows what is not running; `kubectl logs -n todo <pod>` shows why. |

## Run the tests

There are six layers. Each one catches what the others cannot, and no test repeats another layer's job; [`.claude/rules/testing.md`](.claude/rules/testing.md) says which layer owns what. The backend and live suites need [uv](https://docs.astral.sh/uv/), which installs the right Python itself; the frontend and browser suites need Node 24.

| Layer | Where | Tests | Command, from the repo root |
|---|---|---|---|
| Backend unit and integration | `backend/tests/` | 182; 99.7% coverage of lines and branches | `docker compose --profile test up -d --wait test-db`, then `cd backend && uv run pytest` |
| Frontend unit and component | next to the code in `frontend/src/` | 228; 96% of statements, 97% of lines | `cd frontend && npm ci && npm run test` |
| Live API, through nginx | `tests/e2e/live/` | 12 | with the stack up: `cd tests/e2e/live && uv run pytest` |
| Browser journeys (Playwright) | `tests/e2e/browser/` | 5 | with the stack up: `cd tests/e2e/browser && npm ci && npx playwright install chromium && npm test` |
| Load (k6) | `tests/load/` | 1 journey with budgets | with the stack up: `docker compose --profile load run --rm k6 run /scripts/journey.js` |
| Deploy script | `deploy/k3d/tests/` | 7 | `python3 -m unittest discover -s deploy/k3d/tests` |

CI runs every layer but load on each pull request. It fails if backend coverage drops below 90% or frontend coverage below 85%.

The live, browser and load suites also run against the k3d cluster. Point them at it like this:

```bash
cd tests/e2e/live && BASE_URL=https://localhost:8443 API_REPLICAS=1 SSL_CERT_FILE="$(mkcert -CAROOT)/rootCA.pem" uv run pytest
cd tests/e2e/browser && BASE_URL=https://localhost:8443 npm test
docker compose --profile load-k3d run --rm k6-k3d run /scripts/journey.js
```

The browser journeys need `mkcert -install` first; until then, add `IGNORE_HTTPS_ERRORS=1`.

**Frameworks.** The frontend uses [Vitest](https://vitest.dev), whose API matches Jest's (`describe`, `it`, `expect`, `vi.fn` in place of `jest.fn`), with React Testing Library and MSW. The backend uses pytest.

**Test-first.** Each change started with a test that failed for the right reason, and the code came after. The session transcript shows each failing run before the passing one. Some examples:
- **Races.** Five tests fire requests at the same moment, for example two moves of the same list. Each was shown failing once with its guard removed.
- **A bug found on the cluster.** Behind nginx, an ETag sent back as `If-Match` was refused (`W/"1"`, then 400), because nginx's compression had weakened it. The test failed on k3d and on Compose before the fix.
- **A blocked event loop fails the test.** The backend suite runs in asyncio debug mode and fails any test during which the event loop was blocked for more than 50 ms.

**The browser journeys are strict.** They fail on any console error, page error or Content Security Policy violation, and they run on a CPU slowed down six times, so timing bugs that a fast laptop hides show up.

## The code style

**Functional and declarative.** The domain logic is pure functions with no I/O, in [`backend/app/domain/`](backend/app/domain/); the routes, the database code and the React components are a thin layer around it. Inputs are never changed in place.
- **Small rules, combined.** A rank is valid when every rule in a tuple of small checks passes: `all(rule(rank) for rule in RANK_RULES)` ([`ranks.py`](backend/app/domain/ranks.py)). Stepping a rank's digits is a `reduce` over them, carrying the overflow.
- **Functions that build functions.** `optimisticListUpdate` ([`tasks.ts`](frontend/src/lib/query/tasks.ts)) takes a pure list change, such as "move this task" or "tick this task", and returns the first step of an optimistic update: stop list fetches, keep a snapshot for rollback, apply the change to every cached list. Toggle, move and delete all use it.
- **New values, not edited ones.** Frozen dataclasses and frozen Pydantic models in Python; `readonly`, spread and `toSpliced` in TypeScript.
- **Dependencies as data.** FastAPI `Depends` types (`SessionDep`, `CurrentUserDep`) give each route its database session and signed-in user ([`deps.py`](backend/app/api/deps.py)).

**Async through high-level tools.**
- **Backend.** Async FastAPI and async SQLAlchemy, one session per request. Password hashing is slow on purpose, so it runs in a thread with `asyncio.to_thread`, at most four at once behind an `asyncio.Semaphore` ([`passwords.py`](backend/app/security/passwords.py)). The race tests fire their requests together with `asyncio.TaskGroup`.
- **Frontend.** All server data goes through TanStack Query: caching, retries, cancelling, and optimistic updates that roll back on failure. Moves share one mutation scope, so they reach the server in the order you made them.

## Capacity

Both figures are from an Apple M4 Max laptop, with every budget met: no failed request, p95 under 50 ms, and every user's tasks intact afterwards. Each is the highest step tested, so a floor, not the limit.

| Where | Capacity | Notes |
|---|---|---|
| Docker Compose, two API replicas | **at least 1,000 concurrent users** | The API's CPU runs out first. [`round-1.md`](tests/load/results/round-1.md) |
| k3d as shipped, the API autoscaled from one pod to two | **at least 1,000 concurrent users** | Releases, scaling and losing one of two pods lost no request; losing the only pod cost about 13 seconds of errors. [`round-2.md`](tests/load/results/round-2.md) |
| k3d with the API's ceiling raised to five pods | **at least 1,500 concurrent users** | Same runs, same budgets. [`round-2.md`](tests/load/results/round-2.md) |

## Given more time

In priority order. [`FUTURE.md`](FUTURE.md) has the detail.

**How long.** These estimates are for the way this app was built: an AI agent writes the code and the tests, and the lead plans, decides and reviews. A *session* is one or two hours of that pair working together. On top of each estimate, every pull request needs about 30 minutes of the lead's review, the figure from this build. Waits we don't control, such as cloud setup or user testing, are named separately.

| # | What | Why | How long |
|---|---|---|---|
| 1 | **Create tasks by describing them**, in text or by voice | The user says what they need, and the app writes the task; one simple way in | About 2 sessions: an AI layer over the existing task service, one endpoint, a voice and text box on the list; 2 to 3 PRs |
| 2 | **Update tasks by voice**: a button, then "mark the report done and move the dentist to Monday" | The same agent, with tools to edit, complete and move tasks | 1 to 2 sessions on top of #1; 1 to 2 PRs |
| 3 | **Ask about your work, with memory**: "summarise my backlog", "what does my week look like?"; the AI remembers what you tell it about yourself | A to-do manager that knows its user | About 2 sessions: a memory table and migration, 1 to 2 endpoints, a summary screen; 2 to 3 PRs |
| 4 | **Tools behind an MCP server, open to subscribers**: anyone with a subscription connects the AI agent they already use every day, such as ChatGPT, and it manages their list; the web or mobile app is there to look at it | Few people will build an agent just for their to-dos; they will use the one they have. The MCP server makes this app the place where the list lives. It also lets the tools scale apart from the model | About 2 to 3 sessions: an MCP server over the task service, sign-in for outside agents, 2 to 3 PRs. Waits: listing with each agent platform |
| 5 | **API management in front of the models** (Azure API Management or the same on another cloud) | It picks a working model, retries and rate-limits, so the backend doesn't | About 1 session to wire up, plus the cloud setup |
| 6 | **CI/CD with dev, UAT and prod environments**, and the app on a cloud cluster with **Terraform** and the existing Kubernetes manifests (AKS, EKS or GKE) | Versioned releases that move from dev to UAT to prod; start with dev, add UAT when there are users to test with | 2 to 3 sessions: Terraform modules, a cloud overlay, a deploy workflow; 3 to 4 PRs. Waits: cloud setup and approvals |
| 7 | **Decide where the database lives**: in the cluster or managed (Azure Database for PostgreSQL, Cosmos DB, or the same elsewhere) | Managed brings replicas, backups and a connection pooler; in the cluster is portable and cheap | A team discussion first; then about 1 session |
| 8 | **More designs** (three or four next to the vintage one), and **mobile, web or both**, with notifications on mobile | Find out with users what fits a to-do app best | About 1 session per design in the existing design gallery; a mobile app on the same API, a few sessions |
| 9 | **A paid plan**: token-based or a subscription | Only if it launches as a paid MVP, chosen with users in UAT | 2 to 3 sessions, after UAT |
| 10 | **Sign-in with Microsoft, Google or Apple** | Only once external users test it in UAT | 1 to 2 sessions; 2 PRs. Waits: registering the app with each provider |

**Above all, test with real users (UAT).** What they say decides what makes this app worth choosing. The list above should change with it.

## Making it more robust

| What | Why | How long |
|---|---|---|
| **Monitoring with Grafana** | Dashboards and alerts for errors, response times, pods and the database, from metrics and the JSON logs the app already writes | 1 to 2 sessions: a metrics endpoint, Prometheus and Grafana in the cluster; 2 PRs |
| **Pod Security and network policies** | Only nginx may reach the API, and only the API and the migration Job may reach Postgres | Within a session; 1 PR, checked on k3d |
| **Two API pods at rest** | Losing the only pod costs about 15 seconds of errors; two pods remove that | One setting; 1 PR |
| **A k3d job in CI** | A change that breaks only the cluster fails its own PR | Within a session; 1 PR; adds 6 to 8 minutes to CI |
| **Sign-in rate limiting** | Slows down password guessing; belongs in the ingress or API management, shared by every pod | Within a session once #5 or the ingress is in place |
| **Self-host the API docs page**, or turn it off in production | Removes an outside script from the page | Within a session; 1 PR |
| **Cleaner logs** | uvicorn's colour codes end up in the JSON logs; domain-error 400s are not logged yet | Within a session; 1 PR |
| **Fix the hygiene check's folder list** | It skips `tests/`, which was checked by hand | A few minutes; 1 PR |
| **Clean up merged branches** on GitHub | Twelve finished branches are still there | A few minutes |
| Later: **split the frontend bundle by route** | The app ships as one 524 kB file; not urgent | Within a session |

## How it was made

**How AI was used.** The code, tests, configuration and docs were written by an AI agent: Claude Code with Claude Opus. The agent planned, wrote the tests first and then the code, ran every suite, deployed to the local cluster and opened the pull requests. It also sent focused helper agents to review branches and keep the docs in step with the code. The lead set the direction, made every decision, signed off the specs and design, approved the guarded steps (pushing, opening PRs, applying to the cluster), and reviewed and merged every pull request. The lead wrote no code. Guard hooks kept the agent away from secrets and from the `main` and round branches.

The session transcript is the full record of this work, every message and every step. It is on the [`transcripts`](https://github.com/oneconsciousness/todo-app/tree/transcripts) branch, scanned for secrets first. The lead's own words and decisions are in [`docs/kickoff.md`](docs/kickoff.md); breaks are in [`docs/ai-usage/time-log.md`](docs/ai-usage/time-log.md).

**Time taken.** Approximate hours of the lead's own time.

| Day | The lead | The agent |
|---|---|---|
| **Sunday 18 Oct** | **About 2 hours**, hands-on: the requirements, the repo setup, the round 1 spec review | Set up the repo, wrote the spec |
| **Monday 19 Oct** | **About 5 to 6 hours**, in breaks from a full-time job: about 30 minutes to review each of 11 PRs, and each sign-off and checkpoint (the coding walkthrough, the design, the race tests, the load tests) | Built the backend, the frontend, the containers and every test suite, alone between reviews |
| **Tuesday 20 Oct** | **About 4 hours**: the round 2 calls, reviewing and merging #12 to #15, choosing the replica sizes, planning the future work and this write-up | Built and tested round 2 alone while the lead was away; the Mac slept for about 7 hours of that time |

**In total, about 11 to 12 hours of the lead's time, over about two days.** The rest of the time the lead was at work or asleep, and the agent was building or waiting for a review.
