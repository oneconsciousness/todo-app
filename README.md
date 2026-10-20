# todo-app

A full-stack To Do list: a React and TypeScript web client and a Python REST API. A user signs up or signs in, then creates, views, edits, completes, reorders, searches and deletes their own tasks, with a detail screen per task. The layout works from phone to desktop.

The stack runs as containers: Postgres, a one-shot migration step, two API replicas and nginx in front. It is built in rounds: containers (round 1, this one), then a local Kubernetes cluster, then a cloud cluster. The requirements and the decisions behind them are in [`docs/kickoff.md`](docs/kickoff.md); how we work is in [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Run it on a Mac

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

## Capacity

On an Apple M4 Max laptop, the stack served **at least 1,000 concurrent users** with every budget met: no failed request, p95 under 50 ms, and every user's tasks intact afterwards. 1,000 was the highest step tested; the API's CPU is what runs out first. The runs and how to read them are in [`tests/load/results/round-1.md`](tests/load/results/round-1.md).

## Status

This README covers round 1. The full write-up the brief asks for (approach, features, what more time would bring, and how to make it more robust) comes once the later rounds are done.
