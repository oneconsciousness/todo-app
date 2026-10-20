---
paths:
  - "**/Dockerfile"
  - "docker-compose*.yml"
  - "frontend/nginx.conf"
  - "deploy/**"
  - ".github/workflows/**"
---
# Deployment

## Stages, in order
1. **Containers**: each service builds its own image; `docker compose up` runs the stack (database, backend, frontend). The whole test pyramid passes here first.
2. **Local Kubernetes**: a k3d cluster runs the same images from the same manifests, with more than one backend replica. Development continues here once stage 1 is proven.
3. **AKS**: an Azure Kubernetes Service cluster, deployed by GitHub Actions, only after stage 2 works end to end and the human signs off.

Do not start a stage before the previous one is proven and the human says go.

## The human reviews every deployment artifact
- Dockerfiles, compose files, Kubernetes manifests, overlays and workflows are shown to the human and approved before they are applied or merged. Show the file and say what it will create or change.
- The agent never applies anything to AKS or any shared cloud resource. It prepares the change and the exact command; the human runs it (`CONTRIBUTING.md` § 11). `kubectl apply`, `kubectl delete`, `helm` and `az` always ask, even against k3d. In a session, run each `kubectl apply` on its own so each one asks; never `deploy.py up`, which applies everything without asking.

## Built for more than one replica
- One uvicorn process per container; scale with replicas, never with in-container workers.
- The backend is stateless: auth is a signed token checked on every request, with no in-memory sessions or caches that requests write to. Any replica can serve any request.
- One set of manifests (Kustomize base) with one overlay per target (`k3d`, `aks`). No copy-pasted manifests per environment.
- Images are tagged with the git sha, never `latest`, and the same image moves from one stage to the next.
- Migrations run once per release as a Job before the backend rolls out, never from every pod at startup.
- Every backend pod has a liveness probe (`/livez`, process up, checks no dependencies) and a readiness probe (`/readyz`, database reachable). Neither is routed by nginx or the ingress. Shutdown is covered by a 20-second `preStop` sleep instead of a failing probe: Kubernetes drops a terminating pod from the Service at once, but nginx's DNS needs up to about 15 seconds to notice. uvicorn then drains within 20 seconds, inside a 45-second grace period. Requests and limits are set. Containers run as a non-root user with a read-only root filesystem where the runtime allows.
- Config comes from env vars through ConfigMaps; secrets come from Kubernetes Secrets. Neither is ever committed.

## The compose stack
- The `migrate` service runs the migrations once; the API starts only after it exits with 0. It gets the database URL alone, never the JWT secret.
- Two API replicas sit behind nginx. nginx publishes the only port, `127.0.0.1:8080`, and returns 404 for the probes.
- The app containers run read-only with every capability dropped. They set no CPU or memory limits yet.
- Images are tagged `todo-api:${GIT_SHA}` and `todo-web:${GIT_SHA}`, or `local` when `GIT_SHA` is unset. Set it on every compose command.
- Settings come from `.env`; compose stops before anything starts when one is missing.

## The k3d cluster
- `deploy/k3d/cluster.yaml` makes a cluster of one server and two agents. `python3 deploy/k3d/deploy.py up` creates it if missing, builds and imports both images for the current commit, creates the Secrets, and rolls out the release; `build`, `render`, `secrets` and `down` run one step alone. `down` deletes the cluster and its data.
- `render` writes the release to `deploy/.release/<sha>/` (gitignored): one kustomization per part on top of `deploy/overlays/k3d/`, with both images pinned to the commit and the migration Job named `migrate-<sha>`.
- The order is platform (the `todo` namespace and the Postgres StatefulSet), then the migration Job, waited on until complete, then the app. `rollout_steps` in `deploy.py` lists the exact commands.
- The app is three API pods, one per node, behind the headless Service `api`, and two nginx pods. nginx finds the API at `api.todo.svc.cluster.local`. Traefik ends TLS with the `todo-tls` certificate and sends everything to nginx. The app is at https://localhost:8443 with secure cookies.
- `deploy.py` creates the Secrets `todo-db` (key `password`), `todo-api` (key `jwt-secret`) and `todo-tls` (a mkcert certificate) only when they are missing, and keeps existing ones. Values reach kubectl on stdin and are never printed. Trusting mkcert's local authority (`mkcert -install`) is the human's step.
- A repeat `kubectl apply` of the same release still prints "configured" for the StatefulSet, Deployments and PDBs. If the objects' `resourceVersion` did not change, nothing changed.
- Not built yet, by the lead's choice: the restricted Pod Security level, network policies and a k3d job in CI (`FUTURE.md`).
