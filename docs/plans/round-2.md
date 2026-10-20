# Round 2 plan: the same app on a local Kubernetes cluster

| | |
|---|---|
| Status | **As built.** Written after the work, at the lead's request, from what was built and tested on `feature/k3d-cluster` (#12) and `feature/k3d-scale-from-one`, which starts everything at one replica at the lead's call after #12 merged. |
| Builds on | `docs/specs/round-2.html` (revision 4, D21 to D34, the source of truth), then `docs/kickoff.md` §§ 5j, 5k and 5l |
| Out of scope | Round 3 (AKS), and the items deferred to `FUTURE.md`: restricted Pod Security, network policies, a k3d job in CI |
| Written | 2026-10-20 |

How to read it. § 1 maps each spec decision to the files that build it. §§ 2 to 5 say what was built. § 6 is the test plan with the results. § 7 lists the commits in order. § 8 lists what the work decided that the spec did not spell out, § 9 where it departed from the spec or the agreed process, and § 10 the risks and follow-ups. How to run it is in the README; the load results are in `tests/load/results/round-2.md`.

## 1. Traceability

| Spec | What | Where |
|---|---|---|
| D21 | Three-node k3d cluster, port 8443 on the Mac's loopback | `deploy/k3d/cluster.yaml` |
| D22 | One Kustomize base, one overlay per target | `deploy/base/{platform,migrate,app}/`, `deploy/overlays/k3d/{platform,migrate,app}/` |
| D23 | Commit-tagged images, imported into the nodes | `deploy/k3d/deploy.py` (`build`, `release_files`) |
| D24 | Postgres as a one-pod StatefulSet with a volume | `deploy/base/platform/db.yaml` |
| D25 | Migration Job per release, before the API rolls | `deploy/base/migrate/job.yaml`, `deploy.py` (`rollout_steps`) |
| D26 | API Deployment: rolling update, disruption budget, probes, requests and limits | `deploy/base/app/api.yaml` |
| D27 | nginx stays the front of the app; Traefik ends TLS; headless Service | `frontend/nginx-upstream.conf.template`, `frontend/nginx.conf`, `frontend/Dockerfile`, `deploy/base/app/{web,ingress}.yaml`, `deploy/overlays/k3d/app/` |
| D28 | TLS with a mkcert certificate; Secure cookie | `deploy.py` (`certificate`), overlay ConfigMap (`COOKIE_SECURE=true`) |
| D29 | 20-second `preStop` sleep, 45-second grace period | `deploy/base/app/api.yaml`, `.claude/rules/deployment.md` |
| D30 | Settings in a ConfigMap; Secrets made when missing | `deploy/base/app/kustomization.yaml`, `deploy.py` (`ensure_secrets`, `create_secret`) |
| D31 | Kubernetes's defaults for Pod Security and the network (deferred) | `FUTURE.md` |
| D32 | One deploy script; in a session each apply runs on its own | `deploy/k3d/deploy.py`, `.claude/rules/deployment.md` |
| D33 | k3d on the Mac only (deferred CI job) | `FUTURE.md` |
| D34 | API autoscaler, 1 to 2 pods on CPU (3 to 5 before revision 4) | `deploy/base/app/hpa.yaml` |

## 2. Repo layout

```
deploy/
  k3d/cluster.yaml             the cluster: 1 server, 2 agents, k3s v1.36.4, 127.0.0.1:8443 → 443, load balancer at 8,192 connections
  k3d/deploy.py                up | build | render | secrets | down (Python standard library, 3.9+)
  k3d/tests/test_deploy.py     unit tests for its pure parts (CI hygiene job, Python 3.9 and 3.13)
  base/platform/               namespace todo, Service db (headless), StatefulSet db
  base/migrate/                Job migrate (renamed migrate-<sha> per release)
  base/app/                    Deployment and headless Service api, Deployment and Service web, PDBs, Ingress, HPA, ConfigMap todo-config
  overlays/k3d/{platform,migrate,app}/   k3d's settings: origin, Secure cookie, Traefik class, TLS secret
  .release/<sha>/              written by deploy.py, gitignored: one kustomization per part, images pinned to the commit
```

## 3. The cluster and the deploy script

- **Cluster.** `k3d cluster create --config deploy/k3d/cluster.yaml`. k3d's load balancer is nginx with 1,024 connections by default; each connection it passes on holds two, so it dropped connections past about 500 users. The config raises it to 8,192.
- **Release.** `release_files(sha)` returns three kustomizations, each on top of its k3d overlay, pinning `todo-api` and `todo-web` to the commit. Only the migrate part adds `nameSuffix: -<sha>`, so each release runs its migration once and a repeat deploy of the same commit changes nothing. A sha that is not short lowercase hex is refused, because it lands in YAML.
- **Order.** `rollout_steps(sha)`: apply platform, wait for `statefulset/db`, apply migrate, wait for `job/migrate-<sha>` to complete, apply app, wait for `deployment/api` and `deployment/web`.
- **Secrets.** `ensure_secrets()` creates the namespace (`--save-config`, so the later apply takes it over quietly) and each missing Secret: `todo-db` (`password`, 24 random bytes as hex), `todo-api` (`jwt-secret`, 32 bytes as hex), `todo-tls` (mkcert for `localhost`, `127.0.0.1`, `::1`, written to a temporary folder that is deleted at once). Values go to `kubectl create -f -` on stdin as `stringData`, never as arguments. Existence is checked with `-o name`, which prints no data.
- **Output.** Each command is logged before it runs (`logging`, not `print`, because the hygiene check scans `deploy/`).
- **In a session.** The agent runs `build`, `secrets` and `render`, then each `rollout_steps` command by hand, so every `kubectl apply` asks. `up` is for the README.

## 4. Manifests

- **Postgres** (`db.yaml`): `postgres:18.6-alpine3.24`, the image compose runs, as uid 70 with a read-only root filesystem; writable `emptyDir`s for `/var/run/postgresql` and `/tmp`; 1 GiB volume from k3s's local-path storage at `/var/lib/postgresql`. Readiness `pg_isready`, liveness TCP. Requests 250m CPU and 256 MiB, limits 2 CPUs and 1 GiB.
- **Migration Job** (`job.yaml`): the API image runs `alembic upgrade head`; it gets the password and `DATABASE_URL` only. `backoffLimit` 2, a 300-second deadline, kept a week.
- **API** (`api.yaml`): starts at 1 replica, rolling update with surge 1 and none unavailable, spread one per node (`DoNotSchedule`, counted per release with `matchLabelKeys: [pod-template-hash]`). `DATABASE_URL` is built from `$(POSTGRES_PASSWORD)`, so the password is stored once. Startup and liveness on `/livez`, readiness on `/readyz`. `preStop` sleep 20 s, grace 45 s. Requests 500m and 256 MiB, limits 1 CPU and 512 MiB. Runs as uid 10001, read-only, no capabilities, no service account token. Headless Service `api`; PDB: at most one pod down at a time.
- **Autoscaler** (`hpa.yaml`): 1 to 2 pods at 70% of the CPU request (the database allows up to 5), scale up at once, scale down after 120 s. The Deployment keeps `replicas: 1`: a client-side apply patches only fields that changed in the manifest, so it leaves a scaled count alone.
- **web** (`web.yaml`): 1 replica, `API_HOST=api.todo.svc.cluster.local`, `/tmp` writable, `preStop` 5 s, uid 101. Service `web`; PDB: at most one pod down at a time, since "at least one" would block every node drain.
- **Ingress** (`ingress.yaml` and the k3d overlay): everything to `web`; the overlay adds `ingressClassName: traefik` and TLS with `todo-tls` for `localhost`.
- **Settings**: `todo-config` from a generator (`LOG_LEVEL` in the base; `APP_ORIGIN=https://localhost:8443` and `COOKIE_SECURE=true` merged in the overlay). Its name carries a content hash, so a changed setting rolls the API.

## 5. nginx

- **Resolver and upstream from the environment.** `nginx-upstream.conf.template` holds `resolver ${NGINX_LOCAL_RESOLVERS}` and `server ${API_HOST}:8000 resolve`. The image's entrypoint fills it in at start, into `/tmp/upstream.conf` (`NGINX_ENVSUBST_OUTPUT_DIR=/tmp`), because `/tmp` is the only folder the read-only container can write; `nginx.conf` includes it. `NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1` reads the DNS server from `/etc/resolv.conf`: Docker's in compose, the cluster's in Kubernetes. `API_HOST` defaults to `api`, so compose is unchanged.
- **No gzip on `/api/`.** nginx's gzip turns a strong ETag weak, and `If-Match` never matches a weak one. Behind Traefik, which asks nginx for gzip itself, every scripted edit that sent back its ETag got 400. The app's screens were not affected, since they build `If-Match` from the version in the body. The bug dates from round 1, where no test sent back the ETag through the proxy.

## 6. Test plan and results

| Layer | Round 2 change | Result |
|---|---|---|
| Backend unit and integration | None | Unchanged; CI |
| Frontend unit and component | None | Unchanged; CI |
| Deploy script (unit) | New: release files, step order, secrets on stdin, sha check (7 tests) | 7 passed on Python 3.9 and 3.13; red shown first |
| Live API | `BASE_URL` and `API_REPLICAS` from the environment. The session test now checks that every replica sees the same task. New: an ETag sent back as `If-Match` works for a client that accepts gzip | k3d: 12 passed (fresh cluster too). Compose: 12 passed. Red shown first for the replica count (3 ≠ 2) and the ETag (`W/"1"`, 400 on k3d and compose) |
| Browser journeys | `BASE_URL`; `IGNORE_HTTPS_ERRORS=1` only before `mkcert -install` | k3d: 5 passed, over HTTPS with the Secure cookie, CPU throttled 6×. Compose: 5 passed |
| Load (k6) | `k6-k3d` compose service, through `host.docker.internal:8443`, certificate checks skipped | See below |

Red before green for the nginx change: with the round 1 image on k3d, the SPA answered 200 and `/api` answered 502, with nginx logging that it could not reach `127.0.0.11`.

Load, 2026-10-20, same journey and budgets as round 1 (`tests/load/results/round-2.md`):

| Run | Users | Requests | Failed | Notes |
|---|---|---|---|---|
| Baseline | 200 | 44,059 | 0% | p95 26 ms read |
| Pod deleted at full load | 200 | 55,917 | 0% | Replacement on the same node |
| Rolling restart at full load | 200 | 55,931 | 0% | All three API pods replaced; users stayed signed in |
| Hand scale 3 → 5 → 3 at full load | 200 | 55,791 | 0% | |
| Autoscaler (failed) | 800 | 166,455 | 27% | EOF at k3d's load balancer (1,024 connections); fixed in the cluster config |
| Autoscaler | 800 | 176,656 | 0% | 3 → 4 → 5 pods, back to 3 two minutes after the load |
| Capacity | 1,000 | 220,904 | 0% | 3 → 5 pods |
| Capacity | 1,500 | 331,356 | 0% | 5 pods; about 0.74 of a core per API pod, Postgres about 0.68 |

As shipped, one replica of everything and the API autoscaled to two:

| Run | Users | Requests | Failed | Notes |
|---|---|---|---|---|
| Autoscaler stays at 1 | 200 | 43,779 | 0% | One pod at up to 64% of its CPU request, under the target |
| **The only API pod deleted** | 200 | 43,936 | **5.0%** | **2,200 5xx, about 13 s** until the replacement was ready and found |
| Rolling restart of the one pod | 200 | 43,877 | 0% | New pod ready before the old one left |
| Autoscaler | 500 | 110,067 | 0% | 1 → 2 pods and back to 1 |
| One of two pods deleted | 500 | 110,193 | 0% | |
| Capacity | 1,000 | 221,170 | 0% | 2 pods at up to 0.84 of a core each |

Load testing stopped at 1,000 users at the lead's call.

Every passing run met every budget and its data check: each account held exactly its five tasks with unique ranks. **Capacity on k3d: at least 1,000 concurrent users as shipped (two API pods), at least 1,500 with the ceiling raised to five.**

End to end from nothing: the cluster was deleted and recreated through `deploy.py`'s own `ensure_cluster`, then `build`, `secrets`, `render` and each rollout step, with no warning; the live and browser suites passed on it.

## 7. Delivery: one child PR, commit by commit

Each commit was green when made.

| Commit | What |
|---|---|
| `49e978c` docs(round-2): add the k3d spec with the lead's calls | Spec revision 2, kickoff § 5j, `FUTURE.md`, time log |
| `5472d25` feat(web): let nginx find its DNS server and the API from its environment | The upstream template; compose live 11, browser 5 |
| `071fdb2` fix(web): keep the API's ETags strong behind the proxy | `gzip off` on `/api/` and its live test |
| `c9b1915` feat(deploy): run the app on a three-node k3d cluster | `deploy/`, the script and its tests, the CI hygiene step |
| `efab894` test: run the live, browser and load suites against k3d | Suite settings, the replica test, `k6-k3d` |
| `46837c2` docs(claude): describe the k3d cluster and how sessions work with it | `CLAUDE.md`, the deployment rule, the verify skill, `frontend/CLAUDE.md` |
| `b690bac` feat(deploy): scale the API between three and five pods with the load | The autoscaler and the load balancer limit |
| `de3515b` docs: add the k3d run steps and round 2's load results | README and `tests/load/results/` |
| `fbe2df7` docs(round-2): record the autoscaler, the outcome and the as-built plan | Spec revision 3, kickoff § 5k, this plan |
| (child PR 2) feat(deploy): start every part of the app at one replica | Manifests at one replica, autoscaler 1 to 2, disruption budgets, spec revision 4, kickoff § 5l, the shipped runs, README, the rule and this plan |

## 8. Decisions the work made that the spec did not spell out

1. Three kustomizations per release (platform, migrate, app) instead of one, so each part can wait for the one before and only the Job's name carries the commit.
2. The ConfigMap lives in the app part with a content hash; Postgres and the Job take the user and database name as literals (`todo`), so they need no shared ConfigMap.
3. `DATABASE_URL` is built in the pod from `$(POSTGRES_PASSWORD)`, so the password is stored in one Secret key.
4. Images are built with `docker build` from the same folders compose builds, so `deploy.py` needs no `.env`.
5. nginx writes its filled-in config to `/tmp`, not `conf.d`: a compose tmpfs on `conf.d` was not writable by nginx's user, and the container failed to start.
6. The load test skips certificate checks; the live and browser suites make them.
7. The Deployment keeps `replicas: 1` alongside the autoscaler (§ 4).
8. Load runs on k3d do not wipe the database between runs, unlike round 1's stepped runner.
9. The certificate covers `localhost`, `127.0.0.1` and `::1`.

## 9. Departures from the spec and the agreed process

The lead should confirm or reverse each of these.

1. **Secrets.** The spec's revision 1 had the lead type the Secret commands. Because the lead was away, `deploy.py` creates any missing Secret itself, from random values that are never shown (spec D30, "Changed").
2. **Manifests applied before the lead reviewed them.** The deployment rule says the human reviews every deployment artifact before it is applied. The lead asked for setup and local testing to be finished while away, so the manifests were applied to the local k3d cluster, each apply on its own, and are reviewed in the PR. Nothing touched a shared or cloud resource.
3. **Load runs without the lead.** The testing rule runs load tests with the lead present. They ran while the lead was away, at the lead's request; the results are written up for a walk-through.
4. **One child PR** for the whole round, at the lead's request (kickoff § 5j), and this plan written after the work, at the lead's request.
5. **A round 1 bug fixed in round 2:** the weak ETag (§ 5). It was found by the k3d load test and is in scope because the round cannot pass its load test without it.

## 10. Risks and follow-ups

- **One pod of everything at rest.** Losing the only API or nginx pod fails requests for about 15 seconds; raising the floor to two removes that (README).
- **One Postgres pod.** Losing its node stops the app until the pod returns; the data survives on the volume. Round 3 uses Azure's managed Postgres.
- **The autoscaler's ceiling is two pods** for a laptop, and at most five while each pod may open 15 connections. A connection pooler (Azure's built-in PgBouncer in round 3) lifts it.
- **`kubectl apply` prints "configured"** for the StatefulSet, Deployments and PDBs on a repeat apply of the same release, though no object's `resourceVersion` changes.
- **`deploy.py secrets` runs `kubectl create`**, which no ask rule covers. It only creates missing Secrets.
- **The hygiene check's roots** still name `e2e` and `load`, which moved under `tests/` in round 1, so it does not scan the stack-wide suites.
- **`CLAUDE.md` and the deployment rule** do not mention that `kubectl rollout` is on the ask list.
- **The Mac slept** for about seven hours during the build; the session's timestamps show the gap.
