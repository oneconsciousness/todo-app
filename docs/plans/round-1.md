# Round 1 coding plan: the app, running in containers

| | |
|---|---|
| Status | Draft for the lead's review. Nothing here is locked until the lead signs it off. |
| Builds on | `docs/specs/round-1.html` (revision 3, D1 to D20, the source of truth), then `docs/kickoff.md` |
| Out of scope | `FUTURE.md`, and rounds 2 and 3 |
| Written | 2026-10-19, in parallel with the design artifact on `feature/web-design-system` |

How to read it. § 1 maps every spec decision to the section that builds it. §§ 2 to 7 say what gets built. § 8 says in what order, commit by commit. §§ 9 to 12 list what this plan decided on its own, the risks, the open questions and the contradictions it found. A line marked **(Q-n)** follows the recommendation for open question *n*. That question stays open until the lead locks it (`CONTRIBUTING.md` § 9.1), and the line changes if the answer does.

Code here is limited to signatures, short DDL, config fragments and pseudo-steps.

---

## 1. Traceability

| Spec id | What it locks | Plan section(s) |
|---|---|---|
| D1 | Stack | 2, 3, 4.1, 5 |
| D2 | Postgres 17 from day one | 3.5, 5.4, 6.1 |
| D3 | Open sign-up and sign-in, 12 to 128 character passwords, argon2id; OpenAPI at `/api/docs` | 3.6, 3.9.1, 3.10, 5.3 |
| D4 | JWT HS256, 8 h, cookie `session` (HttpOnly, SameSite=Strict, Path=/api); Origin check on writes | 3.3, 3.10, 5.3 |
| D5 | UUID ids minted by the API | 3.5, 3.9 |
| D6 | Fractional ranks, new tasks at the top, reorder off while searching, `PUT …/position` | 3.7.1, 3.9.2, 4.4, 4.7 |
| D7 | Server-side search, trigram index, 250 ms debounce, previous results stay on screen | 3.5, 3.7.2, 3.8, 4.4 |
| D8 | Task fields | 3.5, 3.6 |
| D9 | HTTP contract and the error envelope | 3.4, 3.6, 6.3 |
| D10 | Two API replicas, `X-Served-By` | 3.3, 5.4, 6.6 |
| D11 | JSON logs, access line, `X-Request-ID`, SPA console usage | 3.3, 3.11.4, 4.6 |
| D12 | Coverage floors 90 / 85 | 6.9, 7 |
| D13 | One uvicorn process per container, async only, `--limit-concurrency 200`, graceful shutdown 20 s, nginx keep-alive, 64 KB bodies | 3.11.1, 5.1, 5.3 |
| D14 | argon2id OWASP parameters, `to_thread`, `Semaphore(4)` | 3.10.2, 6.2 |
| D15 | Pool 10 + 5, 5 s wait, `pool_pre_ping`, statement and idle-in-transaction timeouts, one session and one transaction per request | 3.5.1, 3.9, 3.11.2 |
| D16 | Per-user advisory lock for create and move, READ COMMITTED, unique `(owner_id, rank)` | 3.5.3, 3.9.2, 6.4 |
| D17 | Refetch on focus, "Changed elsewhere", `version`, `ETag`, `If-Match`, 412 | 3.9.2, 4.3, 4.5, 6.4 |
| D18 | k6 load test, budgets, consistency check, stepped capacity run | 5.4, 6.8, 8 (PR E) |
| D19 | `/livez` and `/readyz`, not routed by nginx | 3.11.3, 5.3, 6.3, 6.6 |
| D20 | Views from the design branch, containers in the frontend PR | 4.7, 8 (PR D) |
| Race table | One named test per race | 6.4 |
| Endpoints table | Every endpoint, success and error codes | 3.9, 6.3 |
| Two tables | `users`, `tasks` | 3.5.3 |
| Screens table | Routes, states, optimistic rules, 401 handling | 4.6, 4.7 |
| Tests table | Five layers plus load | 6 |
| Order of work | Design before frontend code, gates | 8 |
| Done means | Exit criteria | 8 (gate G5) |

---

## 2. Repo layout

Files this plan adds. The design branch owns everything marked *(design)*.

### 2.1 Backend (`backend/`)

| Path | Owns |
|---|---|
| `pyproject.toml`, `uv.lock` | Dependencies, ruff, mypy strict, pytest, coverage config |
| `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako` | Async alembic setup. `env.py` reads `DatabaseSettings` only, so the migrate container needs no JWT secret. |
| `alembic/versions/0001_initial_schema.py` | Extensions, `users`, `tasks`, constraints and indexes (§ 3.5.3) |
| `Dockerfile`, `.dockerignore` | Image for `api` and `migrate` (§ 5.1) |
| `CLAUDE.md` | The backend's commands, config and layout. `CLAUDE.md` at the root already points to it. |
| `app/main.py` | `create_app(settings)`, lifespan, router and handler wiring |
| `app/config.py` | `DatabaseSettings`, `Settings` (§ 3.1) |
| `app/log.py` | JSON formatter, `configure_logging`, the request-id and user-id context variables |
| `app/middleware.py` | `RequestContextMiddleware`, a pure ASGI middleware: request id, `X-Served-By`, `Cache-Control`, access line |
| `app/api/router.py` | `api_router` under `/api/v1`, with the Origin guard on every route |
| `app/api/deps.py` | `Depends` providers: settings, session, hasher, current user, Origin guard |
| `app/api/schemas.py` | Wire models (camelCase) and the error envelope |
| `app/api/errors.py` | Exception handlers and `STATUS_BY_ERROR`, the one map from domain errors to HTTP |
| `app/api/auth.py` | `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/me` |
| `app/api/tasks.py` | `/tasks` routes |
| `app/api/health.py` | `/livez`, `/readyz` at the root |
| `app/domain/errors.py` | Domain exceptions |
| `app/domain/types.py` | `UserRecord`, `TaskRecord`, `TaskPatch`, `TaskChanges`, `SessionClaims` |
| `app/domain/ranks.py` | `rank_between`, `validate_rank` (pure) |
| `app/domain/search.py` | `normalize_query`, `search_pattern` (pure) |
| `app/domain/patch.py` | `apply_patch` (pure) |
| `app/domain/tokens.py` | `encode_session`, `decode_session` (pure; the clock is a parameter) |
| `app/security/passwords.py` | `Hasher`: argon2id behind `to_thread` and a semaphore (shell) |
| `app/db/engine.py` | `create_engine(settings)`, `create_sessionmaker(engine)` |
| `app/db/models.py` | SQLAlchemy `User`, `Task` |
| `app/db/users.py`, `app/db/tasks.py` | Repository functions. Every task query filters on `owner_id`. |
| `app/services/auth.py`, `app/services/tasks.py` | Use cases, transaction boundaries, advisory lock |
| `tests/conftest.py` | Settings, test database, truncation, app and client, loop guard, Hypothesis profile |
| `tests/support/loop_guard.py`, `database.py`, `factories.py` | Fixture helpers |
| `tests/unit/`, `tests/integration/` | § 6.2, § 6.3, § 6.4 |

### 2.2 Frontend (`frontend/`)

| Path | Owns |
|---|---|
| `src/styles/tokens.css`, `src/components/ui/`, `src/components/app-shell.tsx`, `src/views/*`, `design/` | *(design)* tokens, primitives, `AppShell`, the five views, the gallery |
| `src/lib/schema/task.ts`, `src/lib/schema/auth.ts` | *(design)* `taskSchema`, `Task`, `taskListSchema`, `credentialsSchema`, `userSchema`, `User` |
| `src/test/fixtures.ts` | *(design)* shared fixtures; this plan's tests reuse them |
| `src/lib/schema/error.ts` | `errorEnvelopeSchema` |
| `src/lib/schema/task-input.ts` | `taskDraftSchema` (the detail form), `taskCreateSchema` (quick add), `taskPatchSchema`, `moveSchema` |
| `src/lib/schema/route.ts` | `returnToSchema`, `taskIdParamSchema` (URL params are a boundary) |
| `src/lib/api/client.ts` | `apiRequest`, `ApiError` |
| `src/lib/api/auth.ts`, `src/lib/api/tasks.ts` | One function per endpoint |
| `src/lib/query/keys.ts` | `taskKeys`, `authKeys` |
| `src/lib/query/client.ts` | `createQueryClient`, global error handling |
| `src/lib/query/auth.ts`, `src/lib/query/tasks.ts` | Query and mutation hooks |
| `src/lib/tasks/order.ts` | `moveAfter` (pure, for the optimistic reorder) |
| `src/lib/tasks/draft.ts` | `draftFromTask`, `diffDraft`, `isChangedElsewhere` (pure) |
| `src/hooks/use-debounced-value.ts` | `useDebouncedValue(value, ms)` |
| `src/lib/auth/auth-context.tsx` | `AuthProvider`, `useAuth` |
| `src/app/router.tsx` | `createAppRouter()` |
| `src/app/require-auth.tsx` | Route guard and the signed-in layout (`AppShell` plus `Outlet`) |
| `src/app/route-error.tsx` | Route error boundary |
| `src/pages/*-page.tsx` | One container per route (§ 4.7). In `src/pages/` so `react.md` applies. |
| `src/main.tsx` | Boot: providers, router, `console.info` |
| `src/test/server.ts`, `src/test/handlers.ts` | MSW server and default handlers built from `fixtures.ts` |
| `Dockerfile`, `.dockerignore`, `nginx.conf` | § 5.2, § 5.3 |

### 2.3 End to end, load, compose

| Path | Owns |
|---|---|
| `e2e/live/pyproject.toml`, `e2e/live/test_*.py` | Live API tests (pytest and httpx against :8080) |
| `e2e/browser/package.json`, `playwright.config.ts`, `*.spec.ts` | Playwright journeys **(Q-10)** |
| `load/k6/journey.js` | The k6 script |
| `load/run_stepped.py` | Host-side stepped capacity run (Python standard library) |
| `load/results/` | Saved summaries and machine specs |
| `docker-compose.yml` | `db`, `migrate`, `api` ×2, `web`, plus `k6` (profile `load`) and `test-db` (profile `test`) |
| `.github/workflows/ci.yml` | Adds `backend`, `frontend` and `e2e` jobs |

---

## 3. Backend

### 3.1 Settings

`app/config.py` holds two pydantic-settings classes. `DatabaseSettings` has only `database_url`, so alembic can run without the other secrets. `Settings(DatabaseSettings)` adds the rest. Both use `extra="ignore"`, `frozen=True` and `case_sensitive=False`.

| Env var | Type | Default | Required | Notes |
|---|---|---|---|---|
| `DATABASE_URL` | `PostgresDsn`, scheme `postgresql+asyncpg` | none | yes | Compose builds it from the `POSTGRES_*` values |
| `JWT_SECRET` | `SecretStr`, at least 32 characters | none | yes | HS256 key |
| `APP_ORIGIN` | `str` (scheme, host and port, no trailing slash) | `http://localhost:8080` | no | The one trusted `Origin` for writes |
| `COOKIE_SECURE` | `bool` | `false` | no | `true` once TLS exists (rounds 2 and 3) |
| `LOG_LEVEL` | `Literal["DEBUG","INFO","WARNING","ERROR"]` | `INFO` | no | |
| `DB_POOL_SIZE` | `int` | `10` | no | D15. A setting so tests can shrink it and round 3 can retune it behind PgBouncer. |
| `DB_MAX_OVERFLOW` | `int` | `5` | no | D15 |
| `DB_POOL_TIMEOUT_SECONDS` | `float` | `5.0` | no | D15 |

Constants that are not settings, because the spec fixes them and nothing varies them per environment: JWT lifetime 8 h, cookie name `session`, hash concurrency 4, `statement_timeout` 5 s, `idle_in_transaction_session_timeout` 10 s, readiness timeout 1 s.

Compose also reads `POSTGRES_USER`, `POSTGRES_PASSWORD` and `POSTGRES_DB` for the `db` service. Missing required values fail fast through `${VAR:?message}` in `docker-compose.yml`.

**`.env.example` lines, for the human to create** (agents never write this file). Working local values, so `cp .env.example .env` then `docker compose up --build` works on a clean Mac **(Q-6)**:

```dotenv
# Local development only. Copy to .env. Replace both secrets for anything beyond a laptop:
#   POSTGRES_PASSWORD: openssl rand -hex 24  (letters and digits keep it safe inside DATABASE_URL)
#   JWT_SECRET:        openssl rand -hex 32
POSTGRES_USER=todo
POSTGRES_PASSWORD=local-dev-password-change-me
POSTGRES_DB=todo
JWT_SECRET=local-dev-jwt-secret-change-me-0123456789abcdef
APP_ORIGIN=http://localhost:8080
COOKIE_SECURE=false
LOG_LEVEL=INFO
```

### 3.2 App factory and lifespan

```python
def create_app(settings: Settings | None = None) -> FastAPI: ...
```

- uvicorn runs it as `app.main:create_app --factory`, so nothing is built at import time and tests build their own app with their own settings.
- Order inside the factory: `configure_logging(settings)`, then `FastAPI(title="todo-app API", docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None, lifespan=lifespan)`, then store `settings` on `app.state`, then add `RequestContextMiddleware`, register the handlers (§ 3.4), and include `health_router` (root) and `api_router` (`/api/v1`).
- `lifespan(app)`:
  - Startup: `engine = create_engine(settings)` (no connection is opened yet, so an unreachable database never fails startup), `sessionmaker = create_sessionmaker(engine)`, `hasher = Hasher.owasp(concurrency=4)`. All three go on `app.state`. Then log `api ready` at INFO with `served_by=<hostname>`.
  - Shutdown: log `api shutting down`, `await engine.dispose()`, then stop the log listener last, so the shutdown lines are flushed.
- uvicorn runs with `--lifespan on`, so a lifespan error stops the process instead of being swallowed.

### 3.3 Middleware and the Origin guard

**`RequestContextMiddleware`**, a pure ASGI middleware. A pure one, not `BaseHTTPMiddleware`, so it runs in the request's own task and context variables flow both ways ([Starlette: pure ASGI middleware](https://www.starlette.io/middleware/#pure-asgi-middleware)). For each HTTP request it:

1. Takes `X-Request-ID` from the request when it matches `^[A-Za-z0-9._-]{1,64}$`, and otherwise makes one (`uuid4().hex`). It sets the `request_id` context variable.
2. Wraps `send` so that `http.response.start` gets `X-Request-ID`, `X-Served-By: <socket.gethostname()>` and, for `/api/` paths, `Cache-Control: no-store`.
3. Times the request with `time.perf_counter()`. After the app returns, or raises, it logs one access line on logger `app.access`: `method`, `route` (the route template from `scope["route"].path`, or the raw path when nothing matched), `status`, `duration_ms`, plus `request_id` and `user_id` from the context. A successful `/livez` or `/readyz` is not logged, because probes every 5 s would drown the useful lines. A failed probe is logged.
4. On an exception escaping the app, it logs the access line with status 500 and re-raises. Starlette's outer `ServerErrorMiddleware` then calls the 500 handler (§ 3.4).

`user_id` reaches the access line because `get_current_user` (an async dependency, so it runs in the same task) sets the `user_id` context variable. An integration test pins this (§ 6.3).

**Origin guard**, `require_trusted_origin`. A dependency on `api_router`, so it covers every `/api/v1` route and raises a domain error that the handlers turn into the envelope (handlers never build bodies by hand).

| Method | `Origin` header | Result |
|---|---|---|
| `GET`, `HEAD`, `OPTIONS` | any | pass |
| `POST`, `PUT`, `PATCH`, `DELETE` | equals `APP_ORIGIN` | pass |
| same | present and different, including the literal `null` | `ForbiddenOrigin` → 403 `forbidden_origin` |
| same | absent | pass **(Q-3)** |

Browsers always attach `Origin` to a non-GET request, and send `null` rather than leaving it out when a policy hides it ([Fetch: append a request Origin header](https://fetch.spec.whatwg.org/#append-a-request-origin-header)). So a missing header means a non-browser client (curl, k6, a reviewer's script), which cannot ride the user's cookie in a CSRF attack. Router-level dependencies run before the body is parsed, so a cross-origin write with a bad body still gets 403.

### 3.4 Errors: one envelope, one map

Wire shape (`app/api/schemas.py`):

```python
class ErrorDetail(WireModel):  field: str | None; message: str
class ErrorBody(WireModel):    code: str; message: str; details: list[ErrorDetail] = []
class ErrorEnvelope(WireModel): error: ErrorBody
```

Domain errors (`app/domain/errors.py`) carry no HTTP knowledge. `app/api/errors.py` maps them with one dict, `STATUS_BY_ERROR: Mapping[type[DomainError], tuple[int, str]]`:

| Raised by | Domain error | Status | `code` | `message` (safe to show) |
|---|---|---|---|---|
| Request validation (FastAPI) | `RequestValidationError` | 400 | `validation_failed` | "Some fields are not valid." `details` gives one entry per field, using the last string in `loc` (the camelCase alias) |
| Empty `PATCH` body | `EmptyPatch` | 400 | `validation_failed` | "Send at least one field to change." |
| Bad `If-Match` | `InvalidPrecondition` | 400 | `invalid_if_match` | |
| `afterId` unknown, someone else's, or the task itself | `InvalidPosition` | 400 | `invalid_position` | One message for all three |
| No, bad or expired session | `NotAuthenticated` | 401 | `not_authenticated` | |
| Wrong email or password | `InvalidCredentials` | 401 | `invalid_credentials` | One message for unknown email and wrong password |
| Origin mismatch | `ForbiddenOrigin` | 403 | `forbidden_origin` | |
| Task missing or not yours | `TaskNotFound` | 404 | `not_found` | |
| No route (Starlette `HTTPException` 404 or 405) | n/a | 404 or 405 | `not_found`, `method_not_allowed` | |
| Email registered | `EmailTaken` | 409 | `email_taken` | `details` names `email` |
| Version mismatch | `VersionMismatch` | 412 | `version_mismatch` | |
| Pool wait, statement timeout, database down | `sqlalchemy.exc.TimeoutError`, `OperationalError`, `InterfaceError`, `ConnectionError` | 503 | `service_unavailable` | WARNING with `where=`, `why=`, `then=503` |
| Anything else | `Exception` | 500 | `internal_error` | ERROR with the traceback |

Handlers: `RequestValidationError` → 400 (logged at WARNING with the field names, never the values). `DomainError` → the map. `StarletteHTTPException` → the envelope. The database errors → 503. `Exception` → 500. A unit test walks every `DomainError` subclass and asserts it has an entry in the map.

Two 503s cannot carry the envelope: uvicorn's own `--limit-concurrency` reply (plain text `Service Unavailable`, [uvicorn `flow_control.py`](https://github.com/encode/uvicorn/blob/master/uvicorn/protocols/http/flow_control.py)), and nginx's 502 and 504. The frontend's fetch wrapper turns any non-envelope 502, 503 or 504 into `ApiError` with code `service_unavailable` (§ 4.2) **(Q-2)**.

### 3.5 Database

#### 3.5.1 Engine and sessions (`app/db/engine.py`)

```python
def create_engine(settings: Settings) -> AsyncEngine
def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]
```

- `create_async_engine(url, pool_size=10, max_overflow=5, pool_timeout=5.0, pool_pre_ping=True, connect_args={"server_settings": {"statement_timeout": "5000", "idle_in_transaction_session_timeout": "10000"}})`. asyncpg applies `server_settings` to every new connection ([asyncpg `connect`](https://magicstack.github.io/asyncpg/current/api/index.html#connection)), so the timeouts hold on any Postgres, Azure's included, without server flags.
- `async_sessionmaker(engine, expire_on_commit=False)`. Records leave the repository as Pydantic models, so nothing lazy-loads after commit.
- One `AsyncSession` per request, from `get_session`, declared with `Depends(get_session, scope="function")`. That closes the session and returns its connection before the response is sent. FastAPI's default `scope="request"` runs the exit code after the response is sent ([FastAPI: dependencies with yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/); `scope` is new in 0.121.0, so `fastapi>=0.121`).
- Sessions are never shared between coroutines ([SQLAlchemy asyncio: concurrency](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#using-asyncsession-with-concurrent-tasks)).

#### 3.5.2 SQLAlchemy models (`app/db/models.py`)

`User`: `id: Mapped[UUID]`, `email: Mapped[str]` (`CITEXT` type from `sqlalchemy.dialects.postgresql`), `password_hash: Mapped[str]`, `created_at: Mapped[datetime]`.

`Task`: `id`, `owner_id` (FK, cascade), `title: Mapped[str]` (`String(200)`), `notes: Mapped[str]`, `completed: Mapped[bool]`, `due_date: Mapped[date | None]`, `rank: Mapped[str]` (`Text(collation="C")`), `version: Mapped[int]`, `created_at`, `updated_at`. No relationships: queries are explicit and owner-scoped.

#### 3.5.3 Migration `0001_initial_schema`

```sql
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE users (
  id            uuid PRIMARY KEY,
  email         citext NOT NULL,
  password_hash text NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_users_email_length CHECK (char_length(email) <= 254)
);
CREATE UNIQUE INDEX uq_users_email ON users (email);

CREATE TABLE tasks (
  id         uuid PRIMARY KEY,
  owner_id   uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  title      varchar(200) NOT NULL,
  notes      text NOT NULL DEFAULT '',
  completed  boolean NOT NULL DEFAULT false,
  due_date   date,
  rank       text COLLATE "C" NOT NULL,
  version    integer NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_tasks_title_not_blank CHECK (char_length(btrim(title)) >= 1),
  CONSTRAINT ck_tasks_notes_length    CHECK (char_length(notes) <= 5000),
  CONSTRAINT ck_tasks_version_positive CHECK (version >= 1),
  CONSTRAINT ck_tasks_rank_not_empty   CHECK (rank <> '')
);
CREATE UNIQUE INDEX uq_tasks_owner_rank ON tasks (owner_id, rank);
CREATE INDEX ix_tasks_search_trgm ON tasks USING gin (title gin_trgm_ops, notes gin_trgm_ops);
```

- `uq_tasks_owner_rank` is also the `tasks(owner_id, rank)` index `database.md` asks for. It serves the owner filter, the rank order and the neighbour reads.
- One multicolumn trigram GIN index serves `title ILIKE :p OR notes ILIKE :p` through a bitmap OR ([pg_trgm: index support](https://www.postgresql.org/docs/17/pgtrgm.html#PGTRGM-INDEX)).
- `downgrade()` drops both tables, then both extensions. CI runs upgrade, downgrade, upgrade (§ 7).

### 3.6 Wire models (`app/api/schemas.py`)

```python
class WireModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)
class RequestModel(WireModel):
    model_config = ConfigDict(extra="forbid", strict=True)  # unknown keys and type coercion → 400
```

`strict=True` stops `"yes"` or `1` from passing as a boolean. JSON strings still parse into `date` and `UUID` in strict mode.

| Model | Fields (wire name: type) | Rules |
|---|---|---|
| `Credentials` | `email: EmailStr`, `password: str` | email ≤ 254 characters; password 12 to 128, not stripped. Used by register **and** login. |
| `UserRead` | `id: UUID`, `email: str`, `createdAt: datetime` | No `password_hash`, ever |
| `TaskCreate` | `title: Title`, `notes: Notes = ""`, `dueDate: date \| None = None` | `Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]`, `Notes = Annotated[str, StringConstraints(max_length=5000)]` |
| `TaskUpdate` | `title: Title`, `notes: Notes`, `completed: bool`, `dueDate: date \| None`, every one optional | Explicit `null` is allowed only for `dueDate` (it clears it). Null on the others → 400. Absent fields stay as they are. `to_patch() -> TaskPatch` builds the domain value from `model_fields_set`. |
| `TaskMove` | `afterId: UUID \| None` | Required key; `null` means the top **(Q-1)** |
| `TaskRead` | `id`, `title`, `notes`, `completed`, `dueDate`, `rank`, `version`, `createdAt`, `updatedAt` | Matches the design branch's `taskSchema` |
| `TaskList` | `items: list[TaskRead]` | The envelope leaves room for a cursor |
| `SearchQuery` | `q: str \| None` (query param) | Up to 200 characters, otherwise 400 |

Headers: `ETag: "<version>"` on `POST /tasks`, `GET /tasks/{id}`, `PATCH /tasks/{id}` and `PUT /tasks/{id}/position`. `If-Match` accepts exactly `"<positive int>"`; anything else → 400 `invalid_if_match`. `Location` is relative (`/api/v1/tasks/{id}`, and `/api/v1/auth/me` after register), which RFC 9110 allows and which needs no host or scheme behind a proxy.

### 3.7 Domain core (`app/domain/`, pure, no I/O)

#### 3.7.1 `rank_between`

```python
DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"  # base 62, in byte order
def rank_between(lower: str | None, upper: str | None) -> str: ...
def validate_rank(rank: str) -> str: ...  # returns rank or raises InvalidRank
```

**Contract.** For valid keys with `lower < upper` (byte order, which is Python `str` order for ASCII and Postgres `COLLATE "C"` order), the result is a valid key with `lower < result < upper`. `None` means open-ended on that side. `rank_between(None, None) == "a0"`. It raises `InvalidRankOrder` when `lower >= upper`, and `InvalidRank` for a malformed key. It never mutates and never touches I/O.

**Key format.** It follows David Greenspan's fractional indexing ([article](https://observablehq.com/@dgreensp/implementing-fractional-indexing), [reference code](https://github.com/rocicorp/fractional-indexing)). A key is an *integer part* followed by an optional *fraction*.

- The integer part is a head letter plus digits. Heads `a` to `z` mean 1 to 26 digits (`a0`, `a1`, … `az`, then `b00`). Heads `Z` down to `A` mean 1 to 26 digits below zero (`Zz` sorts just before `a0`).
- The fraction is base-62 digits that never end in `0`.
- So appending and prepending step the integer part and keep keys short (`a0`, `Zz`, `Zy`, …). Only inserts between two neighbours grow the fraction.

**Algorithm, as pseudo-steps.**

```
midpoint(lo, hi):                  # fractions, lo < hi, hi may be None, neither ends in "0"
  1. If hi is not None: n = length of the common prefix of lo (padded with "0") and hi.
     If n > 0: return hi[:n] + midpoint(lo[n:], hi[n:])
  2. dlo = value(lo[0]) or 0 if lo is empty;  dhi = value(hi[0]) or 62 if hi is None
  3. If dhi - dlo > 1: return DIGITS[(dlo + dhi) // 2]      # floor, see the note below
  4. If hi has more than one digit: return hi[0]
  5. Return DIGITS[dlo] + midpoint(lo[1:], None)

rank_between(lower, upper):
  1. Validate each key given. If both are given and lower >= upper: raise InvalidRankOrder.
  2. Neither given: return "a0".
  3. Only upper (insert at the top): (i, f) = split(upper)
       if i is the smallest integer ("A" + 26 zeros): return i + midpoint("", f)
       if f != "": return i                    # the bare integer sorts before upper
       return decrement(i)                     # "a0" → "Zz"
  4. Only lower (append): (i, f) = split(lower); j = increment(i)
       return j if j is not None else i + midpoint(f, None)
  5. Both: (il, fl) = split(lower); (iu, fu) = split(upper)
       if il == iu: return il + midpoint(fl, fu)
       j = increment(il)
       return j if j < upper else il + midpoint(fl, None)
```

`increment` and `decrement` add or subtract one in base 62 with carry. A carry out of the head moves to the next head letter, which adds or drops a digit (`az` + 1 = `b00`, `a0` − 1 = `Zz`). They return `None` past `zzz…` or `A000…`.

**Worked examples.**

| Call | Path | Result |
|---|---|---|
| `rank_between(None, None)` | step 2 | `"a0"` |
| `rank_between("a0", "a1")` | step 5: integer parts differ; `increment("a0") = "a1"` is not `< "a1"`, so `"a0" + midpoint("", None)`, which takes step 3 with `(0 + 62) // 2 = 31` → `V` | `"a0V"` |
| `rank_between("a0", "a0V")` | step 5: same integer `a0`, so `"a0" + midpoint("", "V")`: no common prefix, `(0 + 31) // 2 = 15` → `F` | `"a0F"` |
| `rank_between(None, "a0")` | step 3: no fraction, `decrement("a0")` | `"Zz"` |

**Note on rounding.** The reference code rounds the midpoint digit with `Math.round`, which would give `a0G` for the third row. The spec's worked example pins floor division, and any digit strictly between the two is correct, so floor it is.

#### 3.7.2 Search

```python
def normalize_query(q: str | None) -> str | None      # strip; empty or None → None (no search)
def search_pattern(q: str) -> str                     # "%" + escaped + "%"
```

`search_pattern` escapes `\` first, then `%` and `_`, each with a leading `\`. So `50%_off\x` becomes `%50\%\_off\\x%`. The repository passes it to `ILIKE … ESCAPE '\'` as a bound parameter, so user input never builds SQL.

#### 3.7.3 Patch

```python
class Unset(Enum): UNSET = auto()
@dataclass(frozen=True)
class TaskPatch:
    title: str | Unset = Unset.UNSET
    notes: str | Unset = Unset.UNSET
    completed: bool | Unset = Unset.UNSET
    due_date: date | None | Unset = Unset.UNSET

class TaskChanges(TypedDict, total=False):
    title: str; notes: str; completed: bool; due_date: date | None

def apply_patch(patch: TaskPatch) -> TaskChanges
```

**Contract.** `apply_patch` returns only the fields that were sent, keyed by column name, built with a comprehension over `dataclasses.fields`. `due_date=None` is kept, because it means "clear". It raises `EmptyPatch` when nothing was sent. The service adds `version = version + 1` and `updated_at = now()` itself. The spec's single conditional `UPDATE` (D17) means the core never holds the current row, so `apply_patch` turns a patch into changes rather than applying it to a task **(Q-8)**.

#### 3.7.4 Session tokens

```python
@dataclass(frozen=True)
class SessionClaims: user_id: UUID; issued_at: datetime; expires_at: datetime
def encode_session(user_id: UUID, *, now: datetime, secret: str) -> str
def decode_session(token: str, *, now: datetime, secret: str) -> SessionClaims  # raises NotAuthenticated
```

- Claims: `sub` (user id as a string), `iat`, `exp = iat + 8 h`. HS256 through PyJWT.
- `decode_session` calls `jwt.decode(token, secret, algorithms=["HS256"], options={"verify_exp": False, "require": ["sub", "iat", "exp"]})`, then checks `exp > now` itself. That keeps the clock a parameter, so the function stays pure and expiry is unit-testable. Any `jwt.InvalidTokenError`, a non-UUID `sub` or an expired token raises `NotAuthenticated`.

### 3.8 Repositories (`app/db/users.py`, `app/db/tasks.py`)

Each function takes the session first and returns a Pydantic record (`model_validate(row, from_attributes=True)`) or a primitive. Every task query has `owner_id = :owner_id` in its `WHERE`.

| Function | SQL shape |
|---|---|
| `insert_user(session, id, email, password_hash) -> UserRecord` | `INSERT … RETURNING *`. `IntegrityError` on `uq_users_email` → `EmailTaken` (no check-then-insert) |
| `find_user_by_email(session, email) -> UserRecord \| None` | `WHERE email = :email` (citext compares case-insensitively) |
| `get_user(session, user_id) -> UserRecord \| None` | by id |
| `lock_task_order(session, owner_id) -> None` | `SELECT pg_advisory_xact_lock(hashtextextended(CAST(:owner_id AS text), 0))` ([advisory locks](https://www.postgresql.org/docs/17/functions-admin.html#FUNCTIONS-ADVISORY-LOCKS)) |
| `first_rank(session, owner_id) -> str \| None` | `ORDER BY rank LIMIT 1` |
| `rank_of(session, owner_id, task_id) -> str \| None` | the rank of one task |
| `next_rank_after(session, owner_id, rank, excluding) -> str \| None` | `rank > :rank AND id <> :excluding ORDER BY rank LIMIT 1` |
| `first_rank_excluding(session, owner_id, excluding) -> str \| None` | `id <> :excluding ORDER BY rank LIMIT 1` |
| `insert_task(session, owner_id, id, title, notes, due_date, rank) -> TaskRecord` | `INSERT … RETURNING *` |
| `list_tasks(session, owner_id, pattern: str \| None) -> list[TaskRecord]` | `ORDER BY rank`, plus `(title ILIKE :p ESCAPE '\' OR notes ILIKE :p ESCAPE '\')` when searching |
| `get_task(session, owner_id, task_id) -> TaskRecord \| None` | |
| `update_task(session, owner_id, task_id, changes, expected_version: int \| None) -> TaskRecord \| None` | `UPDATE … SET <changes>, version = version + 1, updated_at = now() WHERE id AND owner_id [AND version = :v] RETURNING *` |
| `set_rank(session, owner_id, task_id, rank) -> TaskRecord \| None` | `UPDATE … SET rank WHERE id AND owner_id RETURNING *`. `version` and `updated_at` stay as they are. |
| `delete_task(session, owner_id, task_id) -> bool` | `DELETE … WHERE id AND owner_id RETURNING id` |

### 3.9 Services and transaction boundaries

The session comes from a dependency (§ 3.5.1). **Each service opens its one transaction explicitly with `async with session.begin():`** **(Q-4)**. Commit happens on a clean exit and rollback on any exception, both before the router builds the response. Explicit boundaries matter in two places:

- **Sign-in hashes outside the transaction.** If the connection stayed checked out during a hash, a burst of sign-ins queued on the semaphore would hold pool connections idle in a transaction, starving every other request and tripping the 10 s idle timeout.
- **The advisory lock is visibly the first statement** of the create and move transactions (D16).

READ COMMITTED throughout. Nothing raises the isolation level.

#### 3.9.1 `app/services/auth.py`

| Function | Steps |
|---|---|
| `register(session, hasher, creds) -> UserRecord` | 1. `hash = await hasher.hash(creds.password)` (no connection held). 2. `async with session.begin()`: `insert_user(uuid4(), …)`. `EmailTaken` propagates as 409. |
| `authenticate(session, hasher, creds) -> UserRecord` | 1. `async with session.begin()`: `find_user_by_email`. The connection goes back to the pool. 2. Unknown email: `await hasher.verify(DUMMY_HASH, password)`, so timing does not reveal which emails exist, then raise `InvalidCredentials`. 3. `await hasher.verify(user.password_hash, password)`, or raise `InvalidCredentials`. |
| `current_user(session, user_id) -> UserRecord` | `get_user`, or `NotAuthenticated` if it is gone |

#### 3.9.2 `app/services/tasks.py`

| Function | Transaction body, in order | Errors |
|---|---|---|
| `list_tasks(session, owner_id, q)` | `p = search_pattern(nq) if (nq := normalize_query(q)) else None`; `list_tasks` | none |
| `get_task(session, owner_id, task_id)` | `get_task` | `TaskNotFound` |
| `create_task(session, owner_id, data)` | **`lock_task_order`**; `top = first_rank`; `rank = rank_between(None, top)`; `insert_task(uuid4(), …)` | none |
| `update_task(session, owner_id, task_id, patch, if_match: int \| None)` | `changes = apply_patch(patch)`; `row = update_task(…, expected_version=if_match)`. If `row is None`: `get_task` decides `TaskNotFound` (gone or not yours) or `VersionMismatch` (exists, so the version was stale) | 400, 404, 412 |
| `move_task(session, owner_id, task_id, after_id)` | **`lock_task_order`**; `rank_of(task_id)` or `TaskNotFound`. If `after_id is None`: `lower = None`, `upper = first_rank_excluding(task_id)`. Otherwise: `after_id == task_id` → `InvalidPosition`; `lower = rank_of(after_id)` or `InvalidPosition`; `upper = next_rank_after(lower, excluding=task_id)`. Then `set_rank(task_id, rank_between(lower, upper))` | 400, 404 |
| `delete_task(session, owner_id, task_id)` | `delete_task` or `TaskNotFound` | 404 |

Why this order is correct under concurrency. The lock makes one user's creates and moves take turns. Under READ COMMITTED each neighbour read after the lock is granted sees the previous holder's commit ([Postgres: read committed](https://www.postgresql.org/docs/17/transaction-iso.html#XACT-READ-COMMITTED)). Edits and deletes do not take the lock (D16). A move does not bump `version`, so reordering in one tab never shows "Changed elsewhere" in another (decision 9.6).

Routers (`app/api/tasks.py`) stay thin. They parse with the wire models, take `owner_id` from `get_current_user`, call the service, then map the record to `TaskRead` and set `ETag` and `Location`.

### 3.10 Auth

#### 3.10.1 Cookie and current user

- Login and register set `session=<jwt>; Max-Age=28800; Path=/api; HttpOnly; SameSite=Strict`, plus `Secure` when `COOKIE_SECURE`. Logout sends the same cookie with `Max-Age=0`, returns 204, and needs no session.
- `get_current_user(request, settings) -> SessionClaims` reads the cookie and calls `decode_session(token, now=datetime.now(UTC), secret=…)`. It sets the `user_id` log context and raises `NotAuthenticated`. It does no database lookup, so task routes stay stateless. `/auth/me` loads the row through `current_user`.

#### 3.10.2 Password hashing (`app/security/passwords.py`)

```python
@dataclass(frozen=True)
class Hasher:
    hasher: argon2.PasswordHasher          # time_cost=2, memory_cost=19456 (19 MiB), parallelism=1
    gate: asyncio.Semaphore                # 4 per process
    @classmethod
    def owasp(cls, concurrency: int) -> "Hasher": ...
    async def hash(self, password: str) -> str: ...            # async with gate: await asyncio.to_thread(...)
    async def verify(self, password_hash: str, password: str) -> bool: ...  # VerifyMismatchError → False
```

The parameters are OWASP's argon2id minimum (m = 19 MiB, t = 2, p = 1; [OWASP password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html#argon2id)). argon2-cffi releases the GIL while hashing ([argon2-cffi](https://argon2-cffi.readthedocs.io/)). The semaphore is created in the lifespan, on the running loop, and kept on `app.state`, not at module level.

### 3.11 Concurrency configuration

#### 3.11.1 uvicorn (D13)

```text
uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
  --loop uvloop --http httptools --lifespan on
  --limit-concurrency 200 --timeout-graceful-shutdown 20 --timeout-keep-alive 75
  --no-access-log --no-server-header
```

- `--limit-concurrency` counts open **connections** as well as tasks ([uvicorn settings](https://www.uvicorn.org/settings/)). So nginx's idle keep-alive connections count toward the 200, and the nginx keep-alive pool stays small (§ 5.3).
- `--timeout-keep-alive 75` is longer than nginx's upstream `keepalive_timeout` of 60 s. Otherwise uvicorn could close a connection just as nginx reuses it, and the user would get a 502.
- `--no-access-log`, because `RequestContextMiddleware` writes the access line.
- Compose gives the container `stop_grace_period: 25s`, longer than the 20 s drain.

#### 3.11.2 Pool and timeouts (D15)

These are the values in § 3.5.1. Budget: 2 replicas × 15 = 30 connections, under 80% of Postgres's default 100.

#### 3.11.3 Probes (D19), `app/api/health.py`

| Path | Does | Success | Failure |
|---|---|---|---|
| `GET /livez` | Returns `{"status": "alive"}` from the event loop. Touches nothing else. | 200 | none (no answer means not alive) |
| `GET /readyz` | `async with asyncio.timeout(1): SELECT 1` on its own engine connection, not a request session | 200 `{"status": "ready"}` | 503 envelope, code `not_ready` |

"Fails once shutdown starts" comes from uvicorn itself. On SIGTERM it closes its listening sockets before draining requests ([`Server.shutdown`](https://github.com/encode/uvicorn/blob/master/uvicorn/server.py)), so every probe connection after that point is refused. No extra flag in the app (decision 9.10).

#### 3.11.4 Logging (D11), `app/log.py`

- `configure_logging(settings) -> QueueListener`, idempotent, called first in `create_app`.
- The root logger gets one `QueueHandler(SimpleQueue())` that carries the `JsonFormatter`. A `QueueListener` thread writes the already-formatted lines to stdout through a `StreamHandler` with `Formatter("%(message)s")`. The formatter sits on the `QueueHandler` because `QueueHandler.prepare` formats the record on the calling thread ([logging.handlers.QueueHandler](https://docs.python.org/3/library/logging.handlers.html#queuehandler)). That keeps the request's context variables and the traceback inside one JSON line. A slow stdout never blocks the loop.
- `uvicorn`, `uvicorn.error` and `uvicorn.access` lose their own handlers and propagate to root, so their lines are JSON too.
- The JSON keys: `ts` (UTC ISO 8601), `level`, `logger`, `msg`, `request_id`, `user_id`, plus whatever `extra` the call passed (`method`, `route`, `status`, `duration_ms`, `served_by`), and `exc` when there is a traceback.
- Lines that exist: `api ready`, `api shutting down`, one access line per request, WARNING for validation failures (field names only), auth failures (`reason=`), 503s (`where=`, `why=`, `then=`), ERROR for 500s. No bodies, cookies, tokens or passwords.

---

## 4. Frontend data layer

**To reconcile with the views' final props.** The design engineer defines the view interfaces. § 4.7 lists what each container must be able to supply.

### 4.1 What this plan adds on top of the design branch's scaffold

| Package | Use |
|---|---|
| `react-router` (v7, data router) | `createBrowserRouter`, `RouterProvider` |
| `@tanstack/react-query` (v5) | All server state |
| `msw` (dev) | `fetch` mocked at the boundary in Vitest |
| `@playwright/test` (in `e2e/browser/`) | Browser journeys |

`dnd-kit` belongs to the views (D1). No frontend env vars are needed: the app and the API share one origin, so every request uses a relative `/api/v1/...` path. The Vite dev server proxies `/api` to `http://localhost:8080` and rewrites `Origin` to `APP_ORIGIN`, so `npm run dev` works against the compose stack (decision 9.13).

### 4.2 Fetch wrapper and `ApiError` (`src/lib/api/client.ts`)

```ts
export class ApiError extends Error {            // (Q-9)
  readonly status: number;                       // 0 for a network failure
  readonly code: ApiErrorCode;                   // from the envelope, or derived below
  readonly details: readonly FieldError[];
}
export const apiRequest = <S extends z.ZodType>(path: string, options: {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown; schema: S; signal?: AbortSignal; ifMatch?: number;
}): Promise<z.infer<S>>;
export const apiRequestNoContent = (path: string, options: Omit<…, "schema">): Promise<void>; // 204
```

- It sends `credentials: "same-origin"`, `Accept: application/json`, `Content-Type: application/json` when there is a body, and `If-Match: "<n>"` when `ifMatch` is given. `path` is relative to `/api/v1`.
- A success body is parsed with `schema.parse`. A parse failure is a contract bug: `console.error("[api] response did not match schema", { path, issues })`, then `ApiError(code: "invalid_response")`.
- An error body is parsed with `errorEnvelopeSchema.safeParse`. On success the `ApiError` takes its `code`, `message` and `details`. On failure it is derived from the status: 502, 503 or 504 → `service_unavailable`, 413 → `payload_too_large`, anything else → `unexpected`.
- A thrown `TypeError` from `fetch` → `ApiError(status 0, code "network_error")`. An `AbortError` is rethrown untouched, so TanStack Query treats it as a cancellation.
- `ApiErrorCode` is an `as const` object with every code from § 3.4 plus the four derived ones.
- `declare module "@tanstack/react-query" { interface Register { defaultError: ApiError } }`, so every hook's `error` is typed ([TanStack: registering a global error](https://tanstack.com/query/v5/docs/framework/react/typescript#registering-a-global-error)).

`src/lib/api/tasks.ts`: `listTasks(q, signal)`, `getTask(id, signal)`, `createTask(input)`, `updateTask(id, patch, ifMatch?)`, `moveTask(id, afterId)`, `deleteTask(id)`. `src/lib/api/auth.ts`: `register(creds)`, `login(creds)`, `logout()`, `me(signal)`. `me` returns `User | null`: a 401 becomes `null`, so the global handler never fires for "not signed in yet".

### 4.3 Query keys and the query client

```ts
export const taskKeys = {
  all: ["tasks"] as const,
  lists: () => [...taskKeys.all, "list"] as const,
  list: (q: string) => [...taskKeys.lists(), { q }] as const,
  details: () => [...taskKeys.all, "detail"] as const,
  detail: (id: string) => [...taskKeys.details(), id] as const,
  mutations: { toggle: ["tasks", "toggle"], move: ["tasks", "move"], remove: ["tasks", "remove"], update: ["tasks", "update"], create: ["tasks", "create"] } as const,
};
export const authKeys = { me: ["auth", "me"] as const };
```

`createQueryClient({ onUnauthenticated }: { onUnauthenticated: () => void }): QueryClient`:

| Default | Value | Why |
|---|---|---|
| `queries.staleTime` | `0` | Every focus or reconnect refetches what is on screen (D17, first layer) |
| `queries.refetchOnWindowFocus`, `refetchOnReconnect` | `true` (set explicitly) | D17. Also the TanStack default; stating it keeps the decision visible. |
| `queries.retry` | Up to 2 retries, only for `network_error` and `service_unavailable` | A 4xx will not change on retry |
| `mutations.retry` | `0` | Writes are not blindly repeated |
| `QueryCache.onError`, `MutationCache.onError` | `not_authenticated` → `queryClient.clear()` then `onUnauthenticated()`. Anything else → `console.error("[query] failed", { key: <resource name only>, status, code })` | Spec: a 401 is handled once, in the query client. Search terms and task text are never logged. `invalid_credentials` is not a session expiry and never redirects. |

`onUnauthenticated`, wired in `main.tsx`, calls `router.navigate("/sign-in?returnTo=" + encodeURIComponent(current path + search), { replace: true })`.

### 4.4 Hooks (`src/lib/query/tasks.ts`, `src/lib/query/auth.ts`)

| Hook | Behaviour |
|---|---|
| `useTasks(q: string)` | `queryKey: taskKeys.list(q)`, `queryFn: ({ signal }) => listTasks(q, signal)`, `placeholderData: keepPreviousData`. Each term is cached under its own key. Consuming `signal` means a superseded search is aborted once its query goes inactive ([query cancellation](https://tanstack.com/query/v5/docs/framework/react/guides/query-cancellation)). The previous results stay on screen while the next ones load (D7). |
| `useTask(id)` | `taskKeys.detail(id)`. A 404 is not retried, and the page shows `NotFoundView`. |
| `useCreateTask()` | Not optimistic (spec). `onSuccess`: invalidate `taskKeys.lists()`. |
| `useUpdateTask(id)` | Detail save. Sends `ifMatch: baseVersion`. `onSuccess`: `setQueryData(detail)` and invalidate the lists. `onError` 412: invalidate the detail, so the newer version arrives and "Changed elsewhere" shows (§ 4.5). |
| `useToggleTask()` | Optimistic. **`onMutate`**: `await cancelQueries({ queryKey: taskKeys.all })`; snapshot with `getQueriesData`; `setQueriesData` flips `completed` in every list and the detail; return the snapshot. **`onError`**: 404 → remove the task from every cache entry and report "That task was deleted elsewhere." Anything else → restore the snapshot and report the failure. **`onSettled`**: invalidate the lists. No `If-Match`, because a toggle sets an absolute value (decision 9.7). |
| `useMoveTask()` | Optimistic, **`scope: { id: "task-order" }`**, so moves run one at a time, in order ([mutations: scopes](https://tanstack.com/query/v5/docs/framework/react/guides/mutations)). `onMutate`: `cancelQueries(taskKeys.lists())`, snapshot, then `setQueryData(taskKeys.list(""), items => moveAfter(items, id, afterId))`. `onError`: restore and report (404 → remove, as above). `onSettled`: invalidate the lists **only when `isMutating({ mutationKey: move }) === 1`**, so a refetch never lands between queued moves ([concurrent optimistic updates](https://tkdodo.eu/blog/concurrent-optimistic-updates-in-react-query)). |
| `useDeleteTask()` | Optimistic. `onMutate`: cancel, snapshot, remove from the lists, `removeQueries(detail)`. `onError`: 404 → keep it removed (it is gone either way); anything else → restore and report. `onSettled`: invalidate the lists. |
| `useTaskNotices()` | Derives the newest failed toggle, move or delete from `useMutationState({ filters: { mutationKey: ["tasks"], status: "error" } })`. Dismissal is local state (a set of dismissed `submittedAt` values). The list page shows notices from mutations started on the detail page, with no extra store. |
| `useMe()`, `useSignIn()`, `useSignUp()`, `useSignOut()` | `useMe` is `authKeys.me` with `staleTime: Infinity` (it changes only through these mutations). Sign-in and sign-up `setQueryData(authKeys.me, user)`. Sign-out clears the whole cache. |
| `useDebouncedValue(value, 250)` | A timer in `useEffect`, cleared on change. A timer is something outside React, so this is a legitimate effect. |

Pure helpers: `moveAfter(items: readonly Task[], id: string, afterId: string | null): readonly Task[]` uses `toSpliced` and `findIndex`, and returns a new array.

### 4.5 "Changed elsewhere" (D17)

The detail page keeps one piece of local state, `draft: { values: TaskDraft; baseVersion: number } | null`. `null` means not editing. Everything else is derived during render:

```ts
const isDirty = draft !== null && !isEqual(draft.values, draftFromTask(task));
const changedElsewhere = isChangedElsewhere(task, draft); // draft !== null && task.version > draft.baseVersion
```

- Editing starts on the first change, with `baseVersion = task.version` at that moment.
- A focus refetch that brings a newer version under a draft makes `changedElsewhere` true straight away. The draft is never overwritten.
- "Reload" sets `draft` to `null`. "Review" shows the newer values next to the draft, and from there "Keep mine" moves `baseVersion` to the current version **(Q-11)**.
- Save validates `draft.values` with `taskDraftSchema`, sends `diffDraft(task, draft)` (only the changed fields) with `If-Match: baseVersion`, and on success clears the draft. A 412 refetches, which turns the notice on.

### 4.6 Auth context, router, guard, error boundary, console

- **`AuthProvider`** exposes `{ status: "loading" | "signed-in" | "signed-out", user: User | null }`, derived from `useMe()` (never copied into state), plus `signIn`, `signUp` and `signOut` from the mutation hooks. `useAuth()` reads it.
- **Router** (`createAppRouter()`):

| Path | Element | Notes |
|---|---|---|
| `/` | `<Navigate to="/tasks" replace />` | |
| `/sign-in` | `SignInPage` | Signed in already → `/tasks` |
| `/sign-up` | `SignUpPage` | Signed in already → `/tasks` |
| layout | `RequireAuth` | `loading` → the shell's loading state; `signed-out` → `<Navigate to={"/sign-in?returnTo=" + path} replace />`; `signed-in` → `AppShell` around `<Outlet />` |
| `/tasks` | `TaskListPage` | |
| `/tasks/:taskId` | `TaskDetailPage` | A `taskId` that is not a UUID → `NotFoundView`, no request |
| `*` | `NotFoundPage` | |
| root `errorElement` | `RouteErrorPage` | **(Q-12)** for which view it renders |

- **`returnTo`** is parsed with `returnToSchema`: it must start with `/` and not with `//`, otherwise `/tasks`. That blocks open redirects.
- **Console.** `main.tsx` logs `console.info("[app] started", { mode })` once. `RouteErrorPage` logs `console.error("[app] route error", error)`. The query caches log as in § 4.3. Nothing else logs.

### 4.7 Route containers and the props they supply

Each container is one file in `src/pages/`. It calls hooks and passes plain data and callbacks into one view. It renders no markup of its own beyond the view. Prop names below describe *what must be supplied*; the final names follow the views.

| Container | View | Must supply |
|---|---|---|
| `SignInPage` | `SignInView` | `onSubmit(credentials)`; `status: "idle" \| "submitting"`; `fieldErrors` (from `credentialsSchema`, or server `details`); `formError` for `invalid_credentials` and for network or 503 failures; the link to sign-up (keeping `returnTo`). On success → navigate to `returnTo`. |
| `SignUpPage` | `SignUpView` | As sign-in. `email_taken` (409) → field error on `email`. |
| `TaskListPage` | `TaskListView` | `state`: `loading` \| `error` (with `onRetry`) \| `ready` with `tasks`. `ready` with no tasks and no search is the **empty** state; with a search it is **no matches**. `searchTerm`, `onSearchChange`, `isSearching` (fetching while showing previous results). **`reorderEnabled = searchTerm.trim() === ""`**. `onMove(taskId, afterId \| null)`. `onToggle(taskId, completed)`. Quick add: `onCreate(title)`, `createStatus: "idle" \| "saving"`, `createFieldError`. The task link (href builder or `onOpen`). `notice` and `onDismissNotice` from `useTaskNotices`. |
| `TaskDetailPage` | `TaskDetailView` | `state`: `loading` \| `error` (with `onRetry`) \| `not-found` (renders `NotFoundView`) \| `ready`. `task` (server values), `draft` values and `onFieldChange(field, value)`, `fieldErrors`, `isDirty`, `saveStatus: "idle" \| "saving"`, `saveError`, `onSave`, `onCancel`. `changedElsewhere` with `onReview`, `onReload`, `onKeepMine` and the newer values for review. Delete: `onDelete` (the confirm step lives in the view per the spec, or as two callbacks if the view prefers). After delete → navigate to `/tasks`. |
| `NotFoundPage` | `NotFoundView` | The link back to `/tasks` |
| `RequireAuth` layout | `AppShell` | `user.email`, `onSignOut`, `signingOut` |

---

## 5. Containers (round 1)

Every file here is a deployment artifact. The lead reviews each one before it is applied or merged (`deployment.md`). Base images are pinned to an exact version in the file when the PR is written. The `api` and `web` images are tagged `${GIT_SHA:-local}`, never `latest`.

### 5.1 Backend `Dockerfile` (multi-stage, uv, non-root)

Following [uv's Docker guide](https://docs.astral.sh/uv/guides/integration/docker/):

```dockerfile
FROM python:3.13-slim AS build
COPY --from=ghcr.io/astral-sh/uv:<pinned> /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev          # dependency layer, cached
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-editable

FROM python:3.13-slim
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --no-create-home app
WORKDIR /app
COPY --from=build --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app app ./app
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app alembic.ini ./
ENV PATH="/app/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 10001
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", …the flags in § 3.11.1]
```

`.dockerignore`: `.venv`, `tests`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.coverage`, `htmlcov`, `__pycache__`.

### 5.2 Frontend `Dockerfile` (build, then unprivileged nginx)

```dockerfile
FROM node:<the major the design branch pins>-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:<1.28.x>-alpine     # listens on 8080, runs as uid 101
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
```

nginx 1.28 is needed for `server … resolve` in open-source nginx (available since 1.27.3). `.dockerignore`: `node_modules`, `dist`, `coverage`, `design`, `*.test.*`, `src/test`.

### 5.3 `frontend/nginx.conf`

```nginx
resolver 127.0.0.11 valid=10s ipv6=off;               # Docker's DNS; replicas can change IPs
map $http_x_request_id $req_id { default $http_x_request_id; "" $request_id; }

upstream api {
  zone api 64k;
  server api:8000 resolve;                             # both replicas, round-robin
  keepalive 16;                                        # idle connections count toward uvicorn's 200
  keepalive_timeout 60s;                               # shorter than uvicorn's 75 s
}

server {
  listen 8080;
  server_tokens off;
  client_max_body_size 64k;                            # D13
  root /usr/share/nginx/html;

  # Security headers. Repeated in each location that sets its own, because add_header does not inherit.
  set $csp "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'";
  add_header Content-Security-Policy $csp always;
  add_header X-Content-Type-Options nosniff always;
  add_header Referrer-Policy strict-origin-when-cross-origin always;
  add_header X-Frame-Options DENY always;
  add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
  add_header Cross-Origin-Opener-Policy same-origin always;

  location = /livez  { return 404; }                   # D19: probes are not routed
  location = /readyz { return 404; }

  location /api/ {
    proxy_pass http://api;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_set_header Host $host;
    proxy_set_header X-Request-ID $req_id;
    proxy_read_timeout 30s;
    # + the security headers
  }
  location = /api/docs { proxy_pass http://api; …; add_header Content-Security-Policy "<docs CSP>" always; … }   # (Q-13)
  location /assets/ { add_header Cache-Control "public, max-age=31536000, immutable"; … }
  location / { try_files $uri /index.html; add_header Cache-Control "no-cache"; … }   # SPA fallback
}
```

- `resolve` with a shared `zone` re-resolves `api` as replicas come and go ([nginx upstream](https://nginx.org/en/docs/http/ngx_http_upstream_module.html)).
- `proxy_next_upstream` keeps its default. nginx does not retry non-idempotent requests on another replica.
- The `/api/docs` CSP allows the Swagger UI's CDN script and style and its inline start-up script. It applies to that one path only.
- gzip is on for JS, CSS and JSON.

### 5.4 `docker-compose.yml`

| Service | Image or build | Depends on | Healthcheck | Notes |
|---|---|---|---|---|
| `db` | `postgres:17.x-alpine` | | `pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB`, every 5 s, 10 retries, start period 10 s | Volume `pgdata`. No published port. |
| `migrate` | build `./backend`, image `todo-api:${GIT_SHA:-local}` | `db: service_healthy` | none (one-shot; its exit code is the signal) | `command: ["alembic", "upgrade", "head"]`, `restart: "no"`, only `DATABASE_URL` |
| `api` | same build and image | `migrate: service_completed_successfully`, `db: service_healthy` ([depends_on conditions](https://docs.docker.com/reference/compose-file/services/#depends_on)) | `python -c "urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=2)"`, every 5 s | `deploy.replicas: 2`, `expose: ["8000"]`, `stop_grace_period: 25s`, the five app env vars |
| `web` | build `./frontend`, image `todo-web:${GIT_SHA:-local}` | `api: service_healthy` | `wget -q --spider http://127.0.0.1:8080/` | `ports: ["127.0.0.1:8080:8080"]`, the only published port |
| `k6` | `grafana/k6:<pinned>` | `web: service_healthy` | none (one-shot) | `profiles: ["load"]`. Mounts `./load/k6:/scripts:ro` and `./load/results:/results`. `BASE_URL=http://web:8080`, `APP_ORIGIN`, `VUS`, `HOLD`. |
| `test-db` | `postgres:17.x-alpine` | | `pg_isready` | `profiles: ["test"]`. `127.0.0.1:55432:5432`, `tmpfs` data, `-c fsync=off -c synchronous_commit=off -c full_page_writes=off`, throwaway credentials. For local backend test runs only **(Q-5)**. |

Hardening on `api`, `migrate` and `web`: `read_only: true`, `tmpfs: [/tmp]`, `cap_drop: [ALL]`, `security_opt: ["no-new-privileges:true"]`. `DATABASE_URL` is built in the file: `postgresql+asyncpg://${POSTGRES_USER:?}:${POSTGRES_PASSWORD:?}@db:5432/${POSTGRES_DB:?}`. `migrate` and `api` declare the same build; BuildKit's cache makes the second build a no-op.

Commands: `docker compose up --build --wait` (the stack); `docker compose --profile test up -d test-db` (backend tests); `docker compose --profile load run --rm k6 run /scripts/journey.js` (load).

---

## 6. Test plan

Each layer owns failures the others cannot see (`testing.md`). Names say the behaviour.

### 6.1 Backend fixtures and database strategy

- **Database.** The race tests need real commits on separate connections, so there is no wrap-in-a-rolled-back-transaction trick. Instead:
  1. A session-scoped, synchronous fixture connects to the server's maintenance database, drops and recreates `todo_test`, then runs `alembic upgrade head` as a subprocess with `DATABASE_URL` pointing at it. A subprocess, because alembic's async `env.py` calls `asyncio.run`, and because it tests the real migration path.
  2. An autouse async fixture runs `TRUNCATE users, tasks CASCADE` **before** each test, so a crashed run leaves nothing behind for the next.
  3. Tests run serially (no xdist in round 1).
  - `TEST_DATABASE_URL`, read only by `conftest.py`, names the server and its maintenance database. The fixture derives the `todo_test` URL from it. The default is `postgresql+asyncpg://todo_test:todo_test@127.0.0.1:55432/postgres` (the `test-db` profile). CI points it at the service container.
- **App and client.** `app = create_app(test_settings)`, entered with `asgi_lifespan.LifespanManager` (httpx's `ASGITransport` does not run the lifespan), then `httpx.AsyncClient(transport=ASGITransport(app), base_url="http://test", headers={"Origin": APP_ORIGIN})`. Each request gets its own session and pooled connection, so concurrent requests in one test really are concurrent in Postgres.
- **Factories** (`tests/support/factories.py`): `signed_in_client(app, email=None) -> AsyncClient` registers a fresh user and keeps the cookie. `create_tasks(client, titles) -> list[TaskRead]`.
- **Loop guard** (`tests/support/loop_guard.py`): `blocked_loop_guard(threshold=0.05)` is an async context manager. It turns on `loop.set_debug(True)` and sets `loop.slow_callback_duration = 0.05`, captures records from the `asyncio` logger, and on exit raises `AssertionError` listing each "Executing … took N seconds" record ([asyncio debug mode](https://docs.python.org/3/library/asyncio-dev.html#debug-mode)). An autouse fixture wraps every backend test with it.
- **pytest config:** `asyncio_mode = "auto"`, session loop scope, `--strict-markers`. Hypothesis profiles `dev` (200 examples) and `ci` (1,000), chosen by `HYPOTHESIS_PROFILE`.

### 6.2 Backend unit (`tests/unit/`)

| File | Tests |
|---|---|
| `test_ranks.py` | `test_rank_between_with_no_neighbours_is_a0`, `test_rank_between_a0_and_a1_is_a0V`, `test_rank_between_a0_and_a0V_is_a0F`, `test_rank_before_a0_is_Zz`, `test_rank_between_rejects_unordered_bounds`, `test_rank_between_rejects_a_malformed_key`, `test_thousand_prepends_keep_ranks_at_most_three_characters`, `test_thousand_appends_keep_ranks_at_most_three_characters`. **Hypothesis:** `test_rank_is_strictly_between_its_bounds` (pairs drawn from a generated sorted list), `test_rank_before_first_sorts_first`, `test_rank_after_last_sorts_last`, `test_any_insertion_sequence_keeps_ranks_sorted_and_unique` (a list of slot indexes drives inserts into a growing list; after each insert the list equals its sorted, de-duplicated self), `test_generated_ranks_are_valid_keys` (no trailing `0` in the fraction, the head letter matches the integer length) |
| `test_search.py` | `test_blank_query_means_no_search`, `test_search_pattern_wraps_the_term_in_wildcards`, `test_search_pattern_escapes_backslash_before_percent_and_underscore`, Hypothesis `test_search_pattern_leaves_no_unescaped_wildcard_inside` |
| `test_patch.py` | `test_apply_patch_keeps_only_sent_fields`, `test_apply_patch_keeps_a_null_due_date_to_clear_it`, `test_apply_patch_rejects_an_empty_patch` |
| `test_tokens.py` | `test_session_token_round_trips_the_user_id`, `test_expired_token_is_rejected`, `test_token_signed_with_another_secret_is_rejected`, `test_unsigned_alg_none_token_is_rejected`, `test_token_without_sub_is_rejected` |
| `test_passwords.py` | `test_hash_verifies_the_same_password`, `test_hash_rejects_another_password`, `test_hasher_uses_owasp_parameters` (`m=19456,t=2,p=1` in the hash string), `test_hashing_runs_off_the_event_loop_thread`, `test_hashing_never_runs_more_than_four_at_once` (a fake argon2 hasher at the library boundary blocks on a `threading.Event` and records peak concurrency while 10 hashes are requested) |
| `test_log.py` | `test_json_line_carries_request_and_user_ids`, `test_exception_and_traceback_stay_in_one_json_line` |
| `test_errors_map.py` | `test_every_domain_error_has_a_status_and_code` |
| `test_loop_guard.py` | `test_loop_guard_flags_a_callback_that_blocks_for_100_ms`, `test_loop_guard_passes_code_that_awaits` |

### 6.3 Backend integration (`tests/integration/`, real Postgres)

Every endpoint has a test for its success code and each error code it can return (`api-contract.md`). Validation rules are proven once in unit tests or Pydantic; here, one case per endpoint proves the wiring.

| File | Tests |
|---|---|
| `test_auth_api.py` | `test_register_creates_account_and_signs_in` (201, `Location`, cookie attributes, no hash in the body), `test_register_rejects_a_short_password_with_400_envelope` (also pins the 422 → 400 mapping and `details[0].field == "password"`), `test_register_rejects_an_email_taken_in_another_case_with_409`, `test_login_sets_the_session_cookie`, `test_login_rejects_a_wrong_password_with_401`, `test_login_gives_unknown_email_the_same_401_as_a_wrong_password`, `test_login_rejects_a_malformed_body_with_400`, `test_logout_clears_the_session_cookie`, `test_me_returns_the_signed_in_user`, `test_me_without_a_session_returns_401`, `test_me_with_an_expired_token_returns_401`, `test_me_with_a_tampered_token_returns_401` |
| `test_origin_guard.py` | `test_write_from_another_origin_is_forbidden`, `test_write_with_null_origin_is_forbidden`, `test_write_without_origin_is_allowed` **(Q-3)**, `test_read_from_another_origin_is_allowed`, `test_text_plain_body_is_rejected_with_400` |
| `test_tasks_api.py` | `test_list_returns_only_own_tasks_in_rank_order`, `test_list_without_a_session_returns_401`, `test_create_puts_the_task_at_the_top_with_location_and_etag`, `test_create_rejects_a_blank_title_with_400`, `test_create_rejects_an_unknown_field_with_400`, `test_get_returns_the_task_with_its_etag`, `test_get_another_users_task_returns_404`, `test_get_an_unknown_task_returns_404`, `test_get_with_a_malformed_id_returns_400`, `test_patch_changes_only_sent_fields_and_bumps_version`, `test_patch_with_null_due_date_clears_it`, `test_patch_with_the_current_if_match_succeeds`, `test_patch_with_a_stale_if_match_returns_412`, `test_patch_with_a_malformed_if_match_returns_400`, `test_patch_rejects_a_null_title_with_400`, `test_patch_rejects_an_empty_body_with_400`, `test_patch_another_users_task_returns_404`, `test_patch_after_delete_returns_404`, `test_delete_returns_204_and_the_task_is_gone`, `test_delete_another_users_task_returns_404` |
| `test_tasks_position.py` | `test_move_to_the_top`, `test_move_after_another_task`, `test_move_keeps_version_and_updated_at`, `test_move_after_an_unknown_task_returns_400`, `test_move_after_another_users_task_returns_the_same_400`, `test_move_after_itself_returns_400`, `test_move_another_users_task_returns_404` |
| `test_tasks_search.py` | `test_search_matches_title_or_notes_ignoring_case_in_rank_order`, `test_search_treats_percent_and_underscore_literally`, `test_search_over_200_characters_returns_400`, `test_search_query_can_use_the_trigram_index` (`EXPLAIN` with `enable_seqscan = off` names `ix_tasks_search_trgm`; this catches a wrong operator class) |
| `test_rank_collation.py` | `test_postgres_sorts_ranks_like_python` (500 keys from a seeded insertion sequence, inserted as one user's tasks, then `ORDER BY rank` == `sorted(keys)`), `test_a_locale_collation_would_misorder_ranks` (the same keys under `COLLATE "und-x-icu"` disagree, which is why the column is `"C"`) |
| `test_health.py` | `test_livez_answers_without_a_database`, `test_readyz_is_200_when_the_database_answers`, `test_readyz_is_503_when_the_database_is_unreachable`, `test_task_request_is_503_envelope_when_the_database_is_unreachable`, `test_request_is_503_when_no_connection_frees_up_in_time` (pool 1 + 0 with a 0.2 s wait, one connection held by the test), `test_pooled_connections_carry_both_timeouts` (`SHOW statement_timeout`, `SHOW idle_in_transaction_session_timeout`) |
| `test_middleware.py` | `test_a_valid_request_id_is_echoed`, `test_a_missing_or_invalid_request_id_is_replaced`, `test_responses_name_the_replica`, `test_api_responses_are_not_cached`, `test_access_line_has_route_status_duration_and_user_id`, `test_unhandled_error_returns_500_envelope_and_logs_the_traceback` (a test-only route added to the test's own app), `test_unknown_route_returns_404_envelope` |
| `test_docs.py` | `test_openapi_document_and_docs_page_are_served` |

### 6.4 Race tests (`tests/integration/test_races.py`), one per row of the spec's race table

How they fire requests: each test builds N coroutines and starts them together inside one `asyncio.TaskGroup`. Every request goes through its own `AsyncSession` and pooled connection (`ASGITransport` calls the app once per request), so Postgres sees N separate transactions. The pool's 5 s wait absorbs N > 15.

| Race | Test | Fires | Asserts | Shown failing without its guard by |
|---|---|---|---|---|
| Two sign-ups, one email | `test_race_twenty_signups_with_one_email_yield_one_201` | 20 `POST /auth/register`, same email in mixed case | exactly one 201 and nineteen 409s; one row | Removing `unique` from the index in the local migration (the test database is rebuilt from migrations): two or more 201s |
| Moves and creates in one list | `test_race_fifty_concurrent_moves_keep_ranks_unique` | 50 `PUT …/position` over 10 tasks, random `afterId` (never the task itself) | all 200; same id set as before; ranks unique; the list sorted by rank | Built **test-first**: the lock is added in this commit, after the test fails without it (§ 8, CP1). Without the lock, colliding moves violate `uq_tasks_owner_rank` → 500s |
| | `test_race_creates_and_moves_together_keep_ranks_unique` | 20 creates and 30 moves | all 2xx; 30 tasks; ranks unique | same |
| | `test_race_other_users_are_never_blocked_by_the_order_lock` | user A holds the lock in a test transaction; user B creates | B's create returns before A releases | Swapping the lock key from `owner_id` to a constant: B times out |
| Two tabs edit one task | `test_race_two_patches_on_one_version_yield_one_412` | 2 `PATCH` with `If-Match: "1"` | one 200, one 412; version is 2 | Removing `AND version = :v` from the `UPDATE`: two 200s |
| Edit or toggle after delete | `test_patch_after_delete_returns_404` (§ 6.3); the frontend half is in § 6.5 | | | |
| A blocked event loop | Every test, through the loop guard | | | `test_loop_guard_flags_a_callback_that_blocks_for_100_ms`, plus the two `Hasher` tests in § 6.2 |
| Load beyond the limits | k6 (§ 6.8) | | | |

The removals in the last column are temporary, uncommitted edits made in the session with the lead watching. Each is reverted with `git checkout -- <file>` and the suite rerun green. The isolation note in D16 can be shown the same way: setting `REPEATABLE READ` on the move transaction makes the 50-move test fail.

### 6.5 Frontend unit and component (Vitest, React Testing Library, MSW)

MSW's `setupServer` runs in `src/test/setup.ts` with `onUnhandledRequest: "error"`. Handlers and data come from `src/test/fixtures.ts`. Container tests assert on roles and text, not on how the view renders. Rendering states belong to the design branch's view tests.

| File | Tests |
|---|---|
| `src/lib/api/client.test.ts` | `parses a success body with the schema`, `turns the error envelope into an ApiError with its code`, `turns a plain-text 503 into service_unavailable`, `returns nothing for 204`, `sends If-Match as a quoted version`, `reports a schema mismatch as invalid_response` |
| `src/lib/query/client.test.tsx` | `clears the cache and goes to sign-in with a return path on not_authenticated`, `does not redirect on invalid_credentials` |
| `src/lib/tasks/order.test.ts` | `moves a task after another without mutating the input`, `moves a task to the top` |
| `src/lib/tasks/draft.test.ts` | `diffs only changed fields`, `detects a newer version under a draft` |
| `src/hooks/use-debounced-value.test.ts` | `waits 250 ms after the last change` (fake timers) |
| `src/lib/query/tasks.test.tsx` | **Race:** `keeps abc on screen when the late ab response arrives` (MSW delays `q=ab` past `q=abc`), `aborts the superseded search request` |
| `src/pages/task-list-page.test.tsx` | `shows the server's tasks after loading`, `disables reorder while a search is typed`, **race:** `three quick moves end in the order the user made` (MSW holds each `PUT` briefly and a refetch is triggered between them), `rolls back an optimistic toggle and says what failed`, **race:** `removes the row and says why when a toggle gets 404`, `keeps quick add saving until the server answers` |
| `src/pages/task-detail-page.test.tsx` | `sends If-Match with the draft's base version`, **race:** `shows changed elsewhere when a newer version arrives under a draft`, `shows changed elsewhere after a 412`, `reload discards the draft`, `shows server field errors next to the field`, `deletes optimistically and returns to the list`, `restores the task when delete fails` |
| `src/pages/sign-in-page.test.tsx` | `returns to the page that asked after sign-in`, `ignores an external returnTo`, `says the email or password is wrong on 401` |
| `src/pages/sign-up-page.test.tsx` | `shows email taken next to the email field on 409` |
| `src/app/router.test.tsx` | `sends a signed-out visitor to sign-in with a return path`, `shows not found for an unknown route`, `shows not found for another user's task id` |

### 6.6 Live API e2e (`e2e/live/`, pytest and httpx against :8080)

| Test | Catches what only the stack shows |
|---|---|
| `test_migrations_ran_and_signup_works_through_the_proxy` | The migrate gate and the proxy path |
| `test_session_from_one_replica_is_accepted_by_the_other` | Loops `GET /auth/me` with one cookie until two distinct `X-Served-By` values are seen; every answer is 200 (D10) |
| `test_session_cookie_survives_the_proxy_with_its_attributes` | nginx did not alter `Set-Cookie` |
| `test_concurrent_moves_through_both_replicas_keep_ranks_unique` | The race-table live row: the advisory lock works across processes |
| `test_deep_link_serves_the_spa` | `GET /tasks/<uuid>` → 200 `text/html` |
| `test_security_headers_are_set_on_the_spa` | CSP and the other headers |
| `test_probes_are_not_reachable_through_the_front_door` | `/livez`, `/readyz` → 404 |
| `test_body_over_64_kb_is_rejected_at_the_proxy` | 413 from nginx |
| `test_api_docs_are_served_through_the_proxy` | `/api/docs`, `/api/openapi.json` |

### 6.7 Browser e2e (Playwright, `e2e/browser/`)

A shared fixture fails a test on any `console.error`, `pageerror` or CSP violation report. Each test signs up a fresh user.

| Spec file | Journey |
|---|---|
| `sign-up-and-sign-in.spec.ts` | `signs up, signs out, signs back in, and a second account sees none of the first account's tasks` |
| `create-edit-complete.spec.ts` | `creates a task, edits every field on the detail screen and completes it` |
| `reorder-and-search.spec.ts` | `reorders by keyboard and by mouse, then finds a task by search with reorder turned off` |
| `delete-and-sign-out.spec.ts` | `deletes a task after confirming and signs out` |
| `phone.spec.ts` | `runs create, reorder by touch and delete at 375 px with no horizontal scroll` (`hasTouch`) |

These journeys check behaviour that already exists when they are written, so their red step is the stack not running yet. Commit bodies say so.

### 6.8 Load (k6, D18)

**Script outline, `load/k6/journey.js`.** Shown to the lead before the first run (CP2).

- `options.scenarios.journey`: `ramping-vus`, stages `[{ duration: "1m", target: VUS }, { duration: HOLD, target: VUS }]`, `gracefulRampDown: "30s"`. `VUS` defaults to 200 and `HOLD` to `3m`.
- `setup()`: `RUN_ID = Date.now()`. Registers `VUS` accounts `load-<RUN_ID>-<n>@example.test` with one generated password, and returns their emails.
- Each VU on its first iteration (keyed by `exec.vu.idInTest`) signs in (tag `kind:auth`) and seeds 5 tasks.
- Each iteration: list (`read`), search a random seeded word (`read`), create (`write`), toggle it (`write`), move it after a random task (`write`), edit with `If-Match` (`write`), delete it (`write`), with `sleep(1)` between steps. Every request sends `Origin: APP_ORIGIN`. A `server_errors` counter counts 5xx.
- `teardown(data)`: signs in as each account and lists its tasks. It calls `exec.test.fail()` ([k6 execution API](https://grafana.com/docs/k6/latest/javascript-api/k6-execution/)) unless every list has exactly 5 tasks, unique ranks and rank order.
- `handleSummary` writes `/results/summary-<VUS>.json` and the text summary.

**Budgets as thresholds** ([k6 thresholds](https://grafana.com/docs/k6/latest/using-k6/thresholds/)):

```js
thresholds: {
  http_req_failed: ["rate<0.001"],
  server_errors: ["count==0"],
  "http_req_duration{kind:read}":  ["p(95)<250"],
  "http_req_duration{kind:write}": ["p(95)<400"],
  "http_req_duration{kind:auth}":  ["p(95)<1500"],
  checks: ["rate>0.999"],
}
```

**Stepped capacity run, `load/run_stepped.py`** (host side, standard library):

1. Record the machine: `sysctl -n hw.model machdep.cpu.brand_string hw.ncpu hw.memsize`, and Docker's CPU and memory from `docker info`. No serial numbers.
2. For each step in `--steps 200,400,600,800,1000` with `HOLD=2m`, run `docker compose --profile load run --rm -e VUS=<n> -e HOLD=2m k6 run /scripts/journey.js`. k6 exits non-zero when a threshold fails.
3. Stop at the first failing step. The capacity figure is the last step that passed (D15). Write `load/results/<UTC>-<sha>/` with `machine.json`, every summary and `capacity.json`.

Each run starts from a fresh stack (`docker compose down -v`, then `up --build --wait`), so earlier runs' accounts do not skew results.

### 6.9 Coverage (D12)

- Backend `pyproject.toml`: `[tool.coverage.run] branch = true, source = ["app"]`; `[tool.coverage.report] fail_under = 90, show_missing = true, skip_covered = true`; pytest runs with `--cov --cov-report=term-missing`. coverage.py's figure with `branch = true` combines lines and branches.
- Frontend `vitest.config.ts`: `coverage: { provider: "v8", include: ["src/**"], exclude: ["src/**/*.test.*", "src/test/**", "src/main.tsx"], thresholds: { lines: 85, branches: 85, functions: 85, statements: 85 } }`.
- e2e and load are not measured. They do not exist to raise a number.

---

## 7. CI (`.github/workflows/ci.yml`)

`hygiene` stays as it is.

| Job | Lands in | Steps |
|---|---|---|
| `backend` | PR C | Service container `postgres:17.x-alpine` (user and password `todo_test`, health command `pg_isready`, port 5432). `actions/checkout`, `astral-sh/setup-uv` (pinned), `uv sync --locked`, `ruff check .`, `ruff format --check .`, `mypy`. **Migration round trip** against a scratch database: `alembic upgrade head`, `alembic downgrade base`, `alembic upgrade head`. Then `pytest` with coverage and `HYPOTHESIS_PROFILE=ci`, `TEST_DATABASE_URL=postgresql+asyncpg://todo_test:todo_test@localhost:5432/postgres`. |
| `frontend` | PR D (or extended there, if the design PR already added it) | `actions/setup-node` with npm cache, `npm ci`, `npm run check`, `npm run test -- --coverage`, `npm run build` |
| `e2e` | PR E; `needs: [backend, frontend]` | `cp .env.example .env`, then replace both secrets with `openssl rand -hex` values. `GIT_SHA=${{ github.sha }} docker compose up --build --wait`. `uv run pytest e2e/live`. `npx playwright install --with-deps chromium`, `npx playwright test`. On failure: upload `playwright-report` and `docker compose logs`. Always: `docker compose down -v`. |

The load test does not run in CI. It runs on a Mac with the lead (D18).

---

## 8. Delivery sequence

### 8.1 PRs in order

| PR | Branch | Contents | Depends on | Size (bounded work) |
|---|---|---|---|---|
| A | `docs/round-1-plan` | The spec commits plus this plan. The branch is stacked on `docs/round-1-spec`, which is not on `main` yet. | | 1 file, 1 PR round |
| B | `feature/web-design-system` | *(design)* tokens, primitives, views, gallery | Gate G2 | Designer's estimate |
| C | `feature/backend-api` | All of § 3, § 6.1 to § 6.4, CI `backend`, the `db` and `test-db` services, `backend/CLAUDE.md` | G1 | About 45 files, 1 migration, 14 commits, 2 to 3 PR rounds **(Q-7)** |
| D | `feature/web-data-layer` | All of § 4, § 6.5, CI `frontend` | B merged (or stacked on B), C's contract | About 30 files, 11 commits, 2 PR rounds |
| E | `feature/containers` | § 5, § 6.6 to § 6.8, CI `e2e` | C and D merged | About 20 files, 8 commits, 2 PR rounds, plus 2 load sessions with the lead |
| F | `docs/readme-round-1` | README: running on a Mac, the load results and the capacity figure | E | 1 to 2 files, 1 PR round |

**External waits** (not agent time): about 2 minutes of CI per push; the lead's review of each PR, of the design and of every deployment artifact; first-time Docker image pulls and builds; Playwright's browser download in CI; the load runs themselves (about 5 minutes for the 200-user run and about 15 for the stepped run).

### 8.2 Gates and checkpoints

| Id | When | Who | What |
|---|---|---|---|
| G0 | Now | Lead | Sign off this plan and lock the open questions (§ 11) |
| G1 | Before PR C's first commit | Lead | The coding-instructions walkthrough with code, comment-style and type-checking samples (kickoff § 4, step 4) |
| G2 | Before PR D | Lead | Design tokens and screens (designer's gate) |
| G3 | In PR C (compose `db` and `test-db`, CI job), PR D (CI job), PR E (Dockerfiles, `nginx.conf`, compose, CI `e2e`) | Lead | Each deployment artifact shown and approved before it is applied or merged |
| **CP1** | PR C, commit C13 | **Lead present** | The race tests: watch them fail without their guards, then pass |
| **CP2** | PR E, commit E7, before any load run | **Lead present** | Review `journey.js`, the thresholds and the stepped plan |
| **CP3** | PR E, after E7 | **Lead present** | Run the 200-user test, then the stepped run, and walk through the results together |
| G4 | Every PR | Reviewer agent, then the lead | Reviewer agent, `/verify`, `/claude-docs-check`, the PR card, then the lead's line-by-line review and green CI |
| G5 | After PR F | Lead | Round 1 exit criteria (spec, "Round 1 is done when") |

### 8.3 Commit sequences (test first; every commit green)

Each row: the test that goes red, then what turns it green. Subjects follow Conventional Commits.

**PR C, `feature/backend-api`**

| # | Commit | Red | Green |
|---|---|---|---|
| C1 | `feat(api): add rank_between with property tests` | `test_rank_between_a0_and_a1_is_a0V` and the other examples (import fails) | `pyproject.toml`, `uv.lock`, `app/domain/ranks.py`, the loop guard and its two tests, the Hypothesis properties. CI `backend` job (unit tests only). |
| C2 | `feat(api): add the search pattern and patch helpers` | `test_search_pattern_escapes_…`, `test_apply_patch_…` | `search.py`, `patch.py`, `types.py`, `errors.py` |
| C3 | `feat(auth): add pure session token helpers` | `test_expired_token_is_rejected` and the rest | `tokens.py` |
| C4 | `feat(auth): hash passwords off the loop, four at a time` | `test_hashing_never_runs_more_than_four_at_once` | `security/passwords.py` |
| C5 | `feat(api): add settings and queue-backed JSON logging` | `test_json_line_carries_request_and_user_ids` | `config.py`, `log.py` |
| C6 | `feat(db): add the initial schema` (**G3**: compose `db` and `test-db`) | `test_postgres_sorts_ranks_like_python` (no table yet), `test_pooled_connections_carry_both_timeouts` | Compose services, alembic, migration `0001`, models, engine with `server_settings`, DB fixtures, the CI Postgres service and migration round trip. `test_a_locale_collation_would_misorder_ranks`. |
| C7 | `feat(api): add the app factory, error envelope and probes` | `test_readyz_is_503_when_the_database_is_unreachable`, `test_request_is_503_when_no_connection_frees_up_in_time`, `test_unknown_route_returns_404_envelope`, `test_openapi_document_and_docs_page_are_served`, middleware tests | `main.py`, `middleware.py`, `api/errors.py`, `api/health.py`, `test_errors_map.py` |
| C8 | `feat(auth): add register, login, logout and me` | `test_register_creates_account_and_signs_in` and the rest of `test_auth_api.py`, `test_origin_guard.py` | `api/auth.py`, `api/deps.py`, `api/schemas.py` (auth), `db/users.py`, `services/auth.py` |
| C9 | `feat(api): add task create, read and list` | `test_create_puts_the_task_at_the_top_…`, `test_list_returns_only_own_tasks_…` | `api/tasks.py`, `db/tasks.py`, `services/tasks.py` (create without the lock for now) |
| C10 | `feat(api): add task search` | `test_tasks_search.py` | Search wiring |
| C11 | `feat(api): add partial updates guarded by If-Match` | `test_patch_with_a_stale_if_match_returns_412` and the rest | `update_task` |
| C12 | `feat(api): add task moves and deletes` | `test_tasks_position.py`, delete tests | `move_task` (no lock yet), `delete_task` |
| C13 | `fix(db): serialize order changes per user with an advisory lock` **(CP1)** | `test_race_fifty_concurrent_moves_keep_ranks_unique` and `test_race_creates_and_moves_together_…` fail with the lead watching | `lock_task_order` as the first statement of create and move. All the race tests in § 6.4 land here. The guard-removal demos for the email, version and loop-guard rows run in the session and are reverted. |
| C14 | `docs(api): add the backend guide` | n/a | `backend/CLAUDE.md`; the `/claude-docs-check` decision commit |

**PR D, `feature/web-data-layer`**

| # | Commit | Red | Green |
|---|---|---|---|
| D1 | `feat(web): add the fetch wrapper and typed api errors` | `client.test.ts` | MSW setup, `client.ts`, `schema/error.ts`, the CI `frontend` job |
| D2 | `feat(web): add the query client with one 401 handler` | `client.test.tsx` | `keys.ts`, `query/client.ts`, `api/auth.ts`, `api/tasks.ts` |
| D3 | `feat(web): add the router, auth context and route guard` | `sends a signed-out visitor to sign-in with a return path`, `sign-in-page.test.tsx`, `sign-up-page.test.tsx` | `router.tsx`, `require-auth.tsx`, `auth-context.tsx`, sign-in and sign-up pages, `schema/route.ts` |
| D4 | `feat(web): add the task list with debounced search` | `keeps abc on screen when the late ab response arrives`, `waits 250 ms…`, `disables reorder while a search is typed` | `use-debounced-value.ts`, `useTasks`, `TaskListPage` |
| D5 | `feat(web): add optimistic toggle with rollback` | toggle rollback and 404 tests | `useToggleTask`, `useTaskNotices` |
| D6 | `feat(web): run reorders in order, optimistically` | `three quick moves end in the order the user made` | `order.ts`, `useMoveTask` |
| D7 | `feat(web): add quick add` | `keeps quick add saving until the server answers` | `useCreateTask`, `schema/task-input.ts` |
| D8 | `feat(web): add the task detail with If-Match and changed elsewhere` | `task-detail-page.test.tsx` (draft, 412, notice), `shows not found for another user's task id` | `draft.ts`, `useTask`, `useUpdateTask`, `TaskDetailPage` |
| D9 | `feat(web): delete tasks optimistically` | delete tests | `useDeleteTask` |
| D10 | `feat(web): add not found, the route error boundary and boot logging` | `shows not found for an unknown route` | `NotFoundPage`, `route-error.tsx`, `main.tsx` |
| D11 | `docs(web): update the frontend guide` | n/a | `frontend/CLAUDE.md` and the docs-check decision |

**PR E, `feature/containers`** (every file is **G3**)

| # | Commit | Red | Green |
|---|---|---|---|
| E1 | `build(deploy): run the stack in containers` | `test_migrations_ran_and_signup_works_through_the_proxy` (nothing on :8080) | Both Dockerfiles, `.dockerignore`s, minimal `nginx.conf` (proxy and SPA), full compose file, `e2e/live` scaffold |
| E2 | `feat(deploy): keep both replicas in rotation with upstream keep-alive` | `test_session_from_one_replica_…`. It may pass against E1's plain upstream, so its failure is shown with `docker compose up --scale api=1` (one `X-Served-By` value only) | `resolve`, `zone` and keep-alive in the upstream |
| E3 | `feat(deploy): add security headers, body limit and closed probes` | headers, 413 and probe tests | The rest of `nginx.conf` |
| E4 | `test(deploy): prove concurrent moves through both replicas` | None expected: the guard exists and its failure was shown in CP1. The commit body says so. | The live race test |
| E5 | `test(web): add the browser journeys` | The stack's absence (see § 6.7) | `e2e/browser` |
| E6 | `ci: run the live and browser suites against compose` | n/a | CI `e2e` job |
| E7 | `test(load): add the k6 journey and stepped capacity run` **(CP2, then CP3)** | A first 20-user smoke run in the session | `journey.js`, `run_stepped.py`, the `k6` service |
| E8 | `docs(load): record round 1 load results` | n/a | `load/results/…` |

---

## 9. Decisions this plan makes that the spec did not spell out

| # | Decision | Reason |
|---|---|---|
| 9.1 | `rank_between` uses floor division for the midpoint digit | The spec's `a0F` example requires it; the reference implementation's rounding would give `a0G` |
| 9.2 | The fractional-indexing key format (integer part plus fraction) | The spec's `a0` keys match it. New tasks go to the top, so prepending is the commonest insert, and the integer part keeps prepends to 2 or 3 characters instead of growing the key every few inserts. |
| 9.3 | `notes` is `NOT NULL DEFAULT ''` | One empty value, not two (`null` and `""`) |
| 9.4 | The API strips the title's surrounding whitespace, and a check stops a blank title | A title of spaces is not a title. The design branch's `taskSchema` must `trim()` to match (sent to the designer). |
| 9.5 | One `Credentials` model (12 to 128 characters) for login and register | It mirrors the single `credentialsSchema`. A short password at sign-in gets 400 rather than 401, which reveals only the public policy. |
| 9.6 | A move changes only `rank`; `version` and `updatedAt` stay | The version guards the fields a person edits. Otherwise a reorder in one tab would trip "Changed elsewhere" in another. |
| 9.7 | The list's toggle sends no `If-Match`; it bumps `version` | A toggle sets an absolute value, so last-write-wins is correct for it. The bump still warns a stale detail draft. |
| 9.8 | An empty `PATCH` is 400 | Nothing to change is a client mistake, not a silent no-op that bumps the version |
| 9.9 | Request models use `extra="forbid"` and `strict=True` | Typos (`after_id`) and coercions (`"yes"` as true) fail loudly as 400 |
| 9.10 | Readiness relies on uvicorn closing its sockets at shutdown | uvicorn already refuses new connections before draining; a second flag would duplicate it |
| 9.11 | Successful probes are left out of the access log | Two probes every 5 s per replica would bury the lines worth reading |
| 9.12 | Sign-in with an unknown email still runs one dummy verify | Equal timing, so response time does not reveal which emails exist |
| 9.13 | The Vite dev proxy rewrites `Origin` to `APP_ORIGIN` | `npm run dev` against the compose stack would otherwise get 403 on every write |
| 9.14 | Pool numbers are settings with the locked defaults; timeouts and the JWT lifetime are constants | Tests need a tiny pool and round 3 may retune behind PgBouncer. Nothing varies the rest. |
| 9.15 | Compose publishes `127.0.0.1:8080`, not every interface | The app is for this Mac, not the local network |
| 9.16 | `Location` headers are relative | Correct behind any proxy without trusting forwarded headers |
| 9.17 | `/api/` responses carry `Cache-Control: no-store` | Private data never sits in a shared or browser cache |
| 9.18 | Search terms over 200 characters → 400 | No title is longer, and it bounds the trigram work |
| 9.19 | Session tokens hold only `sub`, `iat` and `exp`; task routes never load the user | Stateless across replicas (D4); `/auth/me` is the one route that reads the row |
| 9.20 | List notices come from `useMutationState`, not a new store | Server-side outcomes stay in TanStack Query, and the list sees failures from the detail page |
| 9.21 | No `asyncio.TaskGroup` in app code in round 1 | No request has independent awaits to run together (sign-in's read and verify are sequential). `TaskGroup` drives the race tests. Adding one without a real need would be speculative. |

---

## 10. Risks

| Risk | Effect | Mitigation |
|---|---|---|
| uvicorn's own 503 and nginx's 502 and 504 carry no envelope | A client that only reads the envelope crashes | The fetch wrapper's fallback (§ 4.2) and a unit test; Q-2 |
| Idle nginx keep-alive connections count toward `--limit-concurrency` | Spurious 503s under load | `keepalive 16` per nginx worker; the load test watches for 503s |
| Load results depend on Docker Desktop's CPU and memory, and k6 shares the Mac | The capacity figure is not comparable across machines | Record Docker's resources with the results; quote them in the README |
| Zod's `.max()` counts UTF-16 units, Python and Postgres count code points | A 200-emoji title passes the API but not the form | The form is stricter, never looser; documented, no fix in round 1 |
| Swagger UI loads its files from a CDN | `/api/docs` breaks offline or under a strict CSP | A scoped CSP for that path; Q-13 |
| `citext` and `pg_trgm` must be allowed on Azure Postgres | The round 3 migration fails | Note for round 3: allow-list both extensions in the server parameters |
| Debug-mode asyncio slows the backend suite | A longer CI step | Accepted. The guard is the point. |
| `hashtextextended` can collide between two users | Two users' order writes occasionally queue together | Harmless (64-bit hash, a few milliseconds at worst) |
| Rank length grows when many moves land in one gap | Longer keys | Bounded in tests; rebalancing is in `FUTURE.md` |
| Browser fonts or styles from a CDN in the design branch | CSP blocks them | Sent to the designer: bundle fonts, no inline `<style>` |

---

## 11. Open questions (each with a recommendation)

| # | Question | Recommendation |
|---|---|---|
| Q-1 | The spec writes the move body as `{"after_id": …}`, but `api-contract.md` and the kickoff lock camelCase on the wire | **`afterId`**, per the later and more specific rule. Fix the spec's caption and prose in its next revision. |
| Q-2 | The spec says a 503 always carries the envelope, but uvicorn's `--limit-concurrency` reply is plain text and cannot | Keep the locked flag. The fetch wrapper maps any non-envelope 502, 503 or 504 to `service_unavailable`. Correct the spec's wording. (Intercepting in nginx would not carry over to round 2's ingress.) |
| Q-3 | A write with **no** `Origin` header: allow or 403? | **Allow.** Browsers always send `Origin` on writes, so its absence means a script, which cannot carry a victim's cookie. Reject a mismatch and the literal `null`. Reviewers' bulk scripts then work without extra headers. |
| Q-4 | `python.md` says the transaction comes from a dependency. This plan has the dependency give the session and the service open the transaction. | **Service-owned `session.begin()`.** Sign-in must not hold a pooled connection while it waits for a hash slot, and the advisory lock should sit visibly at the top of its transaction. Update `python.md` in PR C's docs check. |
| Q-5 | Local backend tests need a Postgres the host can reach, but the spec says only :8080 is published | A `test-db` service under the `test` profile on `127.0.0.1:55432`, on tmpfs, off by default. The main stack still publishes only :8080. |
| Q-6 | Should `.env.example` hold working local values, so a clean Mac needs only `cp .env.example .env`? | **Yes**, labelled local-only, with the `openssl` lines for real use |
| Q-7 | The spec plans one backend PR. At about 45 files it is a long line-by-line read. | Split into `feature/api-foundation` (C1 to C8) and `feature/api-tasks` (C9 to C14, including CP1). The commit sequence is the same either way. |
| Q-8 | The spec names `apply_patch` in the core. With D17's single conditional `UPDATE` it turns a patch into column changes; it does not apply one to a task. | Keep the spec's name for traceability, with the contract in § 3.7.3. Alternative: rename it `changes_from_patch` and update the spec diagram. |
| Q-9 | `typescript.md` says "no classes"; `ApiError extends Error` is a class | Allow it as the one exception. `instanceof` narrowing and TanStack's typed `defaultError` rely on it. Clarify the rule as "no class components or class-based services". |
| Q-10 | Playwright's home: the brief says `e2e/`, `map.json` lists `frontend/playwright.config.ts` | **`e2e/browser/`**, next to the live tests. Update `map.json` in PR E's docs check. |
| Q-11 | "Changed elsewhere … offers to review or reload". What does review lead to? | Review shows the newer values next to the draft, with **Use theirs** (reload) and **Keep mine** (rebase the draft on the new version; the next save sends the new `If-Match`). |
| Q-12 | The agreed views have no crash screen for the route error boundary | Ask the designer for a small `ErrorView` (message plus "Try again" and "Go to tasks"). Already raised with the designer. Fallback: `NotFoundView` with different copy. |
| Q-13 | `/api/docs` (Swagger UI) needs a CDN and an inline script | A CSP scoped to that path (§ 5.3). Alternative: serve Swagger UI's files from the API image, which adds a dependency. |

---

## 12. Spec and rule contradictions found

1. **Wire naming.** The spec's D6 figure caption and the endpoints prose say `after_id`; `api-contract.md` and kickoff § 5a say camelCase. → Q-1.
2. **503 envelope.** The spec's concurrency caption ("past that wait the client gets a 503 with the error envelope") and D9 cannot hold for uvicorn's own `--limit-concurrency` reply. → Q-2.
3. **Transaction placement.** `python.md` ("one transaction per request, from a dependency") conflicts with keeping the hash outside the transaction. Also, FastAPI's default `scope="request"` would commit *after* the response is sent. → Q-4.
4. **Reachable test database.** `testing.md` and the spec's tests table run integration tests against "the compose db", but the topology publishes only :8080. → Q-5.
5. **Playwright location.** `.claude/skills/claude-docs-check/map.json` expects `frontend/playwright.config.ts`; the brief puts Playwright in `e2e/`. → Q-10.
6. **Classes.** `typescript.md` "no classes" against an `Error` subclass. → Q-9.
7. **Docs the root `CLAUDE.md` points to.** `backend/CLAUDE.md` and `frontend/CLAUDE.md` do not exist yet. PR C (C14) and PR D (D11) create them.
8. **Branch base.** `main` does not contain the spec yet (`docs/round-1-spec` is unmerged), so this branch is stacked on it.

---

## 13. References

- FastAPI, dependencies with `yield` and `scope`: <https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/>, <https://fastapi.tiangolo.com/advanced/advanced-dependencies/>
- uvicorn settings: <https://www.uvicorn.org/settings/>; shutdown order: <https://github.com/encode/uvicorn/blob/master/uvicorn/server.py>
- Starlette pure ASGI middleware: <https://www.starlette.io/middleware/#pure-asgi-middleware>
- SQLAlchemy asyncio and pooling: <https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html>, <https://docs.sqlalchemy.org/en/20/core/pooling.html>
- asyncpg connection `server_settings`: <https://magicstack.github.io/asyncpg/current/api/index.html#connection>
- PostgreSQL 17: advisory locks, transaction isolation, pg_trgm, collation: <https://www.postgresql.org/docs/17/functions-admin.html#FUNCTIONS-ADVISORY-LOCKS>, <https://www.postgresql.org/docs/17/transaction-iso.html>, <https://www.postgresql.org/docs/17/pgtrgm.html>, <https://www.postgresql.org/docs/17/collation.html>
- Fractional indexing: <https://observablehq.com/@dgreensp/implementing-fractional-indexing>, <https://github.com/rocicorp/fractional-indexing>
- OWASP password storage and CSRF: <https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html>, <https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html>
- Fetch Standard, the `Origin` header: <https://fetch.spec.whatwg.org/#append-a-request-origin-header>
- Python asyncio debug mode and `QueueHandler`: <https://docs.python.org/3/library/asyncio-dev.html#debug-mode>, <https://docs.python.org/3/library/logging.handlers.html#queuehandler>
- TanStack Query v5: mutations and scopes, query cancellation, typed errors: <https://tanstack.com/query/v5/docs/framework/react/guides/mutations>, <https://tanstack.com/query/v5/docs/framework/react/guides/query-cancellation>, <https://tanstack.com/query/v5/docs/framework/react/typescript#registering-a-global-error>; concurrent optimistic updates: <https://tkdodo.eu/blog/concurrent-optimistic-updates-in-react-query>
- nginx upstream (`resolve`, `keepalive`): <https://nginx.org/en/docs/http/ngx_http_upstream_module.html>
- Docker Compose `depends_on` conditions: <https://docs.docker.com/reference/compose-file/services/#depends_on>; uv in Docker: <https://docs.astral.sh/uv/guides/integration/docker/>
- k6 thresholds and the execution API: <https://grafana.com/docs/k6/latest/using-k6/thresholds/>, <https://grafana.com/docs/k6/latest/javascript-api/k6-execution/>
