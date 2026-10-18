---
paths:
  - "**/Dockerfile"
  - "docker-compose*.yml"
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
- The agent never applies anything to AKS or any shared cloud resource. It prepares the change and the exact command; the human runs it (`CONTRIBUTING.md` § 11). `kubectl apply`, `kubectl delete`, `helm` and `az` always ask, even against k3d.

## Built for more than one replica
- The backend is stateless: auth is a signed token checked on every request, with no in-memory sessions or caches that requests write to. Any replica can serve any request.
- One set of manifests (Kustomize base) with one overlay per target (`k3d`, `aks`). No copy-pasted manifests per environment.
- Images are tagged with the git sha, never `latest`, and the same image moves from one stage to the next.
- Migrations run once per release as a Job before the backend rolls out, never from every pod at startup.
- Every backend pod has a liveness probe (`/healthz`, process up) and a readiness probe (`/readyz`, database reachable). Requests and limits are set. Containers run as a non-root user with a read-only root filesystem where the runtime allows.
- Config comes from env vars through ConfigMaps; secrets come from Kubernetes Secrets the human creates. Neither is ever committed.
