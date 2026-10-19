# backend

The REST API: FastAPI on Python 3.14, async SQLAlchemy with asyncpg, alembic migrations, Postgres 18. Today it serves the health probes and sign-up, sign-in, sign-out and the current user.

## Commands

Run from `backend/` unless noted.

```bash
uv sync                                    # Python 3.14.8 and the locked dependencies
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest   # the gate; every commit passes it
HYPOTHESIS_PROFILE=ci uv run pytest        # 1,000 examples per property, as CI runs them (200 by default)
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
- Migrations read only `DatabaseSettings` (the database URL), so the migrate step never sees the JWT secret.
- The app refuses to start when `JWT_SECRET` is still the value in `.env.example` and `COOKIE_SECURE` is true. `EXAMPLE_JWT_SECRET` in `config.py` and `.env.example` change together.
- Unknown variables are ignored, so a misspelt name silently falls back to its default.

## Where things are

- `app/domain/`: the pure core, with no I/O. Rank keys, the search pattern, patch-to-changes, session tokens, domain errors and the values they pass around.
- `app/api/`: routers, request dependencies, wire models (camelCase) and the error handlers. `STATUS_BY_ERROR` is the one table from domain error to status, code and message.
- `app/services/`: use cases. Each opens its own transaction.
- `app/db/`: the engine and session factory, table mappings and repository functions. Rows leave as Pydantic records.
- `app/security/`: argon2id password hashing on worker threads, at most four at a time.
- `app/log.py`: JSON lines through a queue, carrying the request and user ids from context variables.
- `app/middleware.py`: the request id, `X-Served-By`, `Cache-Control: no-store` on `/api/`, and one access line per request.
- `app/main.py`: `create_app(settings)` and the lifespan; uvicorn runs it with `--factory`.
- `alembic/versions/`: migrations, numbered. Never edit one that has been applied.

## Gotchas

- The access line's route is rebuilt from the request's `path` and `path_params`. FastAPI includes routers by reference, so `scope["route"].path` is relative to the innermost router (`/auth/me`, not `/api/v1/auth/me`).
- `decode_session` turns off PyJWT's own time checks (`verify_exp`, `verify_iat`), which read the wall clock. Expiry is checked against the `now` argument, so tests set the time without mocking.
- `SessionClaims` reads JWT times with `val_temporal_unit="seconds"`. Pydantic's default reads an integer above 2e10 as milliseconds.
- The loop guard (`tests/support/loop_guard.py`) yields once after turning on asyncio debug mode. The loop times only callbacks that started after debug was on. Its own tests carry the `loop_guard_off` marker.
- `get_session` is declared with `Depends(..., scope="function")`, so the session closes before the response is sent. Services open the transaction themselves with `async with session.begin()`, and hash passwords outside it so no pooled connection waits on a hash.
- Every query on `tasks` filters on the owner. A query without it is a bug, even in an admin path.
- A duplicate email is caught as the unique-index violation on `uq_users_email` and becomes 409. Any other `IntegrityError` stays a 500.
- The alpine Postgres image includes ICU, which one collation test relies on. The `rank` column is `COLLATE "C"` so Postgres sorts keys byte by byte, as Python does.
- If `uv` comes from a pyenv shim, it fails inside `backend/`. pyenv reads `backend/.python-version` (3.14.8), which it may not have installed. Install uv on its own, outside pyenv, or run `pyenv install 3.14.8`.
- Dependencies are pinned to exact versions. Change them with `uv add 'pkg==x.y.z'` and commit `uv.lock`.
