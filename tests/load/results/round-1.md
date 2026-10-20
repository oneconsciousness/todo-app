# Round 1 load results

**Capacity: at least 1,000 concurrent users** on the compose stack (two API replicas), with every budget met. 1,000 was the highest step tested, so this is a floor, not the limit.

Measured on 2026-10-19 with `tests/load/k6/journey.js` and `tests/load/run_stepped.py`, on an Apple M4 Max (16 cores, 48 GiB) whose Docker VM had 16 CPUs and 7.7 GiB. k6 ran inside the same VM as the stack, so it competed with the app for CPU; the figures are conservative.

## Stepped run (`20261019T230758Z-1c1aded/`)

Each step started from a fresh stack, ramped for 1 minute and held for 2.

| Users | Requests/s | p95 read | p95 write | p95 sign-in | Failed | 5xx | Checks | Peak CPU per API replica | Peak Postgres CPU |
|---|---|---|---|---|---|---|---|---|---|
| 200 | 170 | 38.6 ms | 41.3 ms | 28.9 ms | 0% | 0 | 100% | 30% | 11% |
| 400 | 339 | 41.5 ms | 44.0 ms | 20.8 ms | 0% | 0 | 100% | 43% | 19% |
| 600 | 506 | 43.4 ms | 46.7 ms | 18.0 ms | 0% | 0 | 100% | 44% | 23% |
| 800 | 675 | 17.7 ms | 19.4 ms | 16.3 ms | 0% | 0 | 100% | 67% | 18% |
| 1,000 | 839 | 7.4 ms | 8.4 ms | 14.7 ms | 0% | 0 | 100% | 79% | 25% |

Budgets: under 0.1% failed requests, no 5xx, p95 under 250 ms for reads, 400 ms for writes and 1,500 ms for sign-in, over 99.9% of checks. CPU is the peak of the `docker stats` samples in each folder's `docker-stats.txt`, taken every 20 seconds; 100% is one core, the most a single uvicorn process can use.

## 200 users, 3-minute hold (`20261019T230058Z-09ae1d8-200/`)

43,912 requests at 177/s; p95 30.2 ms read, 32.5 ms write, 28.7 ms sign-in; no failed request, no 5xx, every check passed.

## What the numbers say

- **Correct under load.** After every run, each account was signed back into and held exactly its five tasks, with unique ranks in order. 527,368 requests across six fresh stacks produced no failure.
- **The API's CPU is what runs out first.** At 1,000 users each single-process replica used 79% of a core while Postgres used a quarter and nginx under a tenth. More replicas raise the figure without code changes.
- **Latency fell as load rose.** The likely reason is the host, not the app: under light load macOS keeps the VM's threads on efficiency cores at lower clock speeds. Not verified.

Each folder holds `machine.json` and the k6 summary for every step; the stepped run also holds `capacity.json`. The summaries carry no account details.
