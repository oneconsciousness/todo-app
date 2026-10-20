# todo-app

A full-stack To Do list: a React and TypeScript web client and a Python REST API. A user signs up or signs in, then creates, views, edits, completes, reorders, searches and deletes their own tasks, with a detail screen per task. The layout works from phone to desktop.

It is built in rounds. Round 1 runs it as containers with Docker Compose: Postgres, a one-shot migration step, two API replicas and nginx in front. Round 2 runs the same images on a local Kubernetes cluster (k3d) with three nodes, behind HTTPS, starting with one replica of everything, where the API adds a second under load. Round 3, a cloud cluster on Azure, is next. The requirements and the decisions behind them are in [`docs/kickoff.md`](docs/kickoff.md) and the specs in [`docs/specs/`](docs/specs/); how we work is in [`CONTRIBUTING.md`](CONTRIBUTING.md).

There are two ways to run it on a Mac. Docker Compose is the quickest. k3d shows the app spread over a cluster.

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

Each layer catches what the others cannot; [`.claude/rules/testing.md`](.claude/rules/testing.md) says which owns what. The backend and live suites need [uv](https://docs.astral.sh/uv/), which installs the right Python itself; the frontend and browser suites need Node 24.

| Layer | Where | Command, from the repo root |
|---|---|---|
| Backend unit and integration | `backend/tests/` | `docker compose --profile test up -d --wait test-db`, then `cd backend && uv run pytest` |
| Frontend unit and component | next to the code in `frontend/src/` | `cd frontend && npm ci && npm run test` |
| Live API, through nginx | `tests/e2e/live/` | with the stack up: `cd tests/e2e/live && uv run pytest` |
| Browser journeys (Playwright) | `tests/e2e/browser/` | with the stack up: `cd tests/e2e/browser && npm ci && npx playwright install chromium && npm test` |
| Load (k6) | `tests/load/` | with the stack up: `docker compose --profile load run --rm k6 run /scripts/journey.js` |

CI runs every layer but load on each pull request.

The live, browser and load suites also run against the k3d cluster. Point them at it like this:

```bash
cd tests/e2e/live && BASE_URL=https://localhost:8443 API_REPLICAS=1 SSL_CERT_FILE="$(mkcert -CAROOT)/rootCA.pem" uv run pytest
cd tests/e2e/browser && BASE_URL=https://localhost:8443 npm test
docker compose --profile load-k3d run --rm k6-k3d run /scripts/journey.js
```

The browser journeys need `mkcert -install` first; until then, add `IGNORE_HTTPS_ERRORS=1`.

## Capacity

Both figures are from an Apple M4 Max laptop, with every budget met: no failed request, p95 under 50 ms, and every user's tasks intact afterwards. Each is the highest step tested, so a floor, not the limit.

| Where | Capacity | Notes |
|---|---|---|
| Docker Compose, two API replicas | **at least 1,000 concurrent users** | The API's CPU runs out first. [`round-1.md`](tests/load/results/round-1.md) |
| k3d as shipped, the API autoscaled from one pod to two | **at least 1,000 concurrent users** | Releases, scaling and losing one of two pods lost no request; losing the only pod cost about 13 seconds of errors. [`round-2.md`](tests/load/results/round-2.md) |
| k3d with the API's ceiling raised to five pods | **at least 1,500 concurrent users** | Same runs, same budgets. [`round-2.md`](tests/load/results/round-2.md) |

## Status

This README covers rounds 1 and 2. The full write-up the brief asks for (approach, features, what more time would bring, and how to make it more robust) comes once the later rounds are done.
