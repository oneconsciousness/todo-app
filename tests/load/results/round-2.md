# Round 2 load results

**Capacity: at least 1,500 concurrent users** on the k3d cluster, with every budget met and the API autoscaled to its ceiling of five pods. 1,500 was the highest step tested, so this is a floor, not the limit. Round 1's compose stack, with two fixed replicas, held at least 1,000 ([`round-1.md`](round-1.md)).

**No request failed while pods were deleted, restarted, added or removed under load,** and every account's tasks were intact after every run.

Measured on 2026-10-20 with the same `tests/load/k6/journey.js` and budgets as round 1, through the `k6-k3d` compose service, on the same Apple M4 Max (16 cores, 48 GiB; Docker VM with 16 CPUs and 7.7 GiB). The cluster was k3d with one server and two agent nodes, running k3s v1.36.4. k6 ran in the same VM as the cluster and reached it through the Mac at `https://host.docker.internal:8443`, so it competed with the app for CPU, and every request went through k3d's load balancer, Traefik and nginx. The figures are conservative.

Budgets: under 0.1% failed requests, no 5xx, p95 under 250 ms for reads, 400 ms for writes and 1,500 ms for sign-in, over 99.9% of checks. Each run ends with a data check that signs back into every account and fails the run unless each holds exactly its five tasks with unique ranks. Unlike round 1's stepped run, the database was not wiped between runs.

## Disruption under load: 200 users, 3 API pods

Each run ramped to 200 users over a minute and held for four; the disruption came at full load. The times are in each folder's `events.txt`.

| Run | What happened at full load | Requests | p95 read / write / sign-in | Failed | 5xx | Data check |
|---|---|---|---|---|---|---|
| `…115056Z-071fdb2-k3d-baseline-200` (3-minute hold) | Nothing | 44,059 | 26.1 / 28.8 / 23.4 ms | 0% | 0 | passed |
| `…115514Z-071fdb2-k3d-pod-kill-200` | One API pod deleted; its replacement started on the same node | 55,917 | 23.6 / 27.3 / 24.7 ms | 0% | 0 | passed |
| `…120041Z-071fdb2-k3d-rolling-restart-200` | `kubectl rollout restart`: all three API pods replaced, one at a time, while users stayed signed in | 55,931 | 27.3 / 30.3 / 22.9 ms | 0% | 0 | passed |
| `…122016Z-071fdb2-k3d-scale-3-5-3-200` | Scaled by hand from 3 to 5 pods, then back to 3 | 55,791 | 29.9 / 33.4 / 23.1 ms | 0% | 0 | passed |

The restarted and removed pods kept serving for 20 seconds after Kubernetes told them to stop, while nginx's view of the pods caught up, and then finished their requests in flight. That is why none of these runs lost a request. Signed-in users stayed signed in across the full restart because a session is a signed cookie any pod can check; no pod holds it.

## The autoscaler: 800 users

The API's autoscaler keeps 3 to 5 pods and adds one when the pods average over 70% of their CPU request.

`…124016Z-46837c2-k3d-autoscale-800`: 176,656 requests at 696/s; p95 11.9 ms read, 14.3 ms write, 17.0 ms sign-in; no failed request, no 5xx; data check passed. From `pods-top.txt`:

| Time (UTC) | Autoscaler CPU / target | API pods |
|---|---|---|
| 12:41:37 | 82% / 70% | 3 |
| 12:41:57 | 89% / 70% | 4 |
| 12:43:58 | 75% / 70% | 5 |
| 12:45:19 | 6% / 70% (load over) | 5 |
| 12:46:59 | 0% / 70% | 3 |

It added a pod by the next sample after crossing the target, and removed them after its two-minute quiet window.

## Capacity: 1,000 and 1,500 users

| Run | Users | Requests/s | p95 read | p95 write | p95 sign-in | Failed | 5xx | Checks | API pods | Peak CPU per API pod | Peak Postgres CPU |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `…124809Z-46837c2-k3d-capacity-1000` | 1,000 | 866 | 17.9 ms | 20.5 ms | 17.7 ms | 0% | 0 | 100% | 3 → 5 | 60% | 43% |
| `…125236Z-46837c2-k3d-capacity-1500` | 1,500 | 1,290 | 13.1 ms | 15.4 ms | 20.4 ms | 0% | 0 | 100% | 5 | 74% | 68% |

CPU is the peak of the `kubectl top` samples in each folder's `pods-top.txt`, taken every 20 seconds; 100% is one core, which is each API pod's limit and the most one uvicorn process can use. The 1,500 run started with five pods because the 1,000 run had just ended.

## A failed run, and what it fixed

`…122838Z-071fdb2-k3d-autoscale-800` failed: 27% of requests got no answer (EOF), with no 5xx, and the autoscaler never moved. The app was healthy; k3d's own load balancer, an nginx in front of the cluster, was out of connections. It allows 1,024 by default and each connection it passes on holds two, so it dropped connections past about 500 users, and `kubectl` with them. `deploy/k3d/cluster.yaml` now raises it to 8,192, and every run after that passed. The folder is kept as the record; its `k6.txt` is trimmed of the 5,992 per-request warnings.

## What the numbers say

- **Correct under load and under disruption.** 940,614 requests across the seven passing runs produced no failure, and every account held exactly its five tasks afterwards.
- **The API scales with the load.** Five autoscaled pods carried 1,500 users with p95 under 21 ms. At that point each pod used about three quarters of a core and Postgres about two thirds, so Postgres would be the next limit to watch.
- **Five pods is a deliberate ceiling.** Each pod opens up to 15 database connections, and 5 × 15 = 75 stays under 80% of Postgres's 100. More pods need a connection pooler in front of Postgres, which Azure's managed Postgres brings in round 3.

Each folder holds `machine.json`, the k6 summary (`summary-<users>.json`), the k6 output (`k6.txt`) and the samples (`pods-top.txt`); the disruption runs also hold `events.txt`. The summaries carry no account details.

To rerun one, with the cluster up: `GIT_SHA=$(git rev-parse --short HEAD) VUS=200 HOLD=4m docker compose --profile load-k3d run --rm k6-k3d run /scripts/journey.js`, then disrupt it with `kubectl delete pod`, `kubectl rollout restart deployment/api -n todo` or `kubectl scale deployment/api -n todo --replicas=5` at full load, and watch `kubectl get hpa -n todo`.
