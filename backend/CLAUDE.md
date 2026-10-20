# backend

The REST API: FastAPI on Python 3.14, async SQLAlchemy with asyncpg, alembic migrations, Postgres 18. Today it serves the health probes, sign-up, sign-in, sign-out and the current user, and the signed-in user's tasks: create, read, list, search, edit, move and delete.

## Commands

Run from `backend/` unless noted.

```bash
uv sync                                    # Python 3.14.8 and the locked dependencies
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest   # the gate; every commit passes it
HYPOTHESIS_PROFILE=ci uv run pytest        # 1,000 examples per property, as CI runs them (200 by default)
uv run pytest tests/integration/test_races.py --no-cov   # one file alone; without --no-cov the 90% floor fails it
DATABASE_URL=postgresql+asyncpg://... uv run alembic upgrade head   # apply migrations; `downgrade base` undoes them
```

The integration tests need a Postgres. From the repo root:

```bash
docker compose --profile test up -d --wait test-db    # throwaway server on 127.0.0.1:55432, data in memory
docker compose --profile test down                    # stop and remove it
```

Compose reads every service's variables, so even `test-db` needs a `.env` in the repo root. The human creates it once with `cp .env.example .env`. The suite drops and rebuilds its own `todo_test` database from the migrations on each run, and empties both tables before each test. Set `TEST_DATABASE_URL` to point it at another server's maintenance database (CI does).

Coverage below 90% fails the run. Unit tests never open a socket; integration tests run against the real database.

## Config

`app/config.py` reads environment variables into `Settings`, once, inside `create_app`.
- Required: `DATABASE_URL` (a `postgresql+asyncpg://` URL) and `JWT_SECRET` (32 characters or more).
- Optional, with defaults: `APP_ORIGIN` (`http://localhost:8080`), `COOKIE_SECURE` (`false`), `LOG_LEVEL` (`INFO`), `DB_POOL_SIZE` (10), `DB_MAX_OVERFLOW` (5), `DB_POOL_TIMEOUT_SECONDS` (5).
- `APP_ORIGIN` must be `http(s)://host[:port]`, exactly what browsers send in `Origin`. A trailing slash is dropped; a path, query, credentials or bad port stops start-up. Writes whose `Origin` differs get 403.
- Migrations read only `DatabaseSettings` (the database URL), so the migrate step never sees the JWT secret.
- The app refuses to start when `JWT_SECRET` is still the value in `.env.example` and `COOKIE_SECURE` is true. `EXAMPLE_JWT_SECRET` in `config.py` and `.env.example` change together.
- Unknown variables are ignored, so a misspelt name silently falls back to its default.

## Where things are

- `app/domain/`: the pure core, with no I/O. Rank keys, the search pattern, patch-to-changes, session tokens, domain errors and the values they pass around.
- `app/api/`: routers, request dependencies, wire models (camelCase) and the error handlers. `STATUS_BY_ERROR` is the one table from domain error to status, code and message.
- `app/services/`: use cases. Each opens its own transaction.
- `app/db/`: the engine and session factory, table mappings and repository functions. Rows leave as Pydantic records.
- `app/security/`: argon2id password hashing on worker threads, at most four at a time. At start-up the hasher makes a dummy hash with its own parameters; sign-in checks an unknown email's password against it, so it costs the same as a wrong password.
- `app/log.py`: JSON lines through a queue, carrying the request and user ids from context variables. uvicorn's own lines join them, but its access lines are dropped.
- `app/middleware.py`: the request id, `X-Served-By`, `Cache-Control: no-store` on `/api/`, one access line per request, and the 500 envelope for any error nothing else handled.
- `app/main.py`: `create_app(settings)` and the lifespan; uvicorn runs it with `--factory`.
- `alembic/versions/`: migrations, numbered. Never edit one that has been applied.
- `Dockerfile`: one image for the API and the compose `migrate` service. It runs as a non-root user on a read-only filesystem, and starts one uvicorn process with `--factory`, uvloop, httptools and `--no-access-log`.

## Gotchas

- `RequestContextMiddleware` writes the one access line per request, and none for a probe that succeeded. `configure_logging` stops `uvicorn.access` from reaching the JSON log, so running uvicorn without `--no-access-log` still writes no second line.
- The access line's route is rebuilt from the request's `path` and `path_params`. FastAPI includes routers by reference, so `scope["route"].path` is relative to the innermost router (`/auth/me`, not `/api/v1/auth/me`).
- `decode_session` turns off PyJWT's own time checks (`verify_exp`, `verify_iat`), which read the wall clock. Expiry is checked against the `now` argument, so tests set the time without mocking.
- `SessionClaims` reads JWT times with `val_temporal_unit="seconds"`. Pydantic's default reads an integer above 2e10 as milliseconds.
- The loop guard (`tests/support/loop_guard.py`) yields once after turning on asyncio debug mode. The loop times only callbacks that started after debug was on. It pauses the garbage collector while it times, since a full pass over the suite's heap can outlast the threshold. Its own tests and the OpenAPI test (FastAPI builds that document synchronously, once) carry the `loop_guard_off` marker.
- `get_session` is declared with `Depends(..., scope="function")`, so the session closes before the response is sent. Services open the transaction themselves with `async with session.begin()`, and hash passwords outside it so no pooled connection waits on a hash.
- Every query on `tasks` filters on the owner. A query without it is a bug, even in an admin path.
- Creates and moves call `lock_task_order` first in their transaction, then read the neighbouring ranks. The lock is per user, so other users never wait. Edits and deletes do not take it, since neither picks a rank.
- The order lock relies on READ COMMITTED, Postgres's default. Each statement after the lock reads a fresh snapshot, so it sees the rank the last holder wrote. At REPEATABLE READ the snapshot would predate the wait, and two creates would pick the same rank.
- A task's `version` is its ETag, sent as a quoted number (`"3"`). A `PATCH` with `If-Match` checks the version in the `UPDATE`'s `WHERE` and answers 412 when it moved on; without `If-Match` the edit always lands. Every edit bumps the version. A move does not, so reordering never makes an open edit fail with 412.
- `tests/integration/test_races.py` fires its requests together with `asyncio.TaskGroup`. Each request gets its own session and pooled connection, so Postgres sees separate, concurrent transactions.
- A duplicate email is caught as the unique-index violation on `uq_users_email` and becomes 409. Any other `IntegrityError` stays a 500.
- Unhandled errors become a 500 inside `RequestContextMiddleware`, not in a FastAPI exception handler. Starlette runs its `Exception` handler outside every middleware, so that 500 would lack the request id and the other headers, and the server would log the traceback a second time.
- A database that is slow, full or unreachable answers 503 (`/readyz` answers 503 `not_ready`). Opening a connection gives up after 5 s; asyncpg's own default is 60 s. `OSError` counts as unreachable, which covers refused connections and host names that do not resolve.
- `app/db/models.py` and the migrations are kept in step by hand; nothing generates one from the other. A schema change edits both, in a new migration.
- The alpine Postgres image includes ICU, which one collation test relies on. The `rank` column is `COLLATE "C"` so Postgres sorts keys byte by byte, as Python does.
- If `uv` comes from a pyenv shim, it fails inside `backend/`. pyenv reads `backend/.python-version` (3.14.8), which it may not have installed. Install uv on its own, outside pyenv, or run `pyenv install 3.14.8`.
- Dependencies are pinned to exact versions. Change them with `uv add 'pkg==x.y.z'` and commit `uv.lock`.
