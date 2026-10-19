# Coding standards

Applies to `backend/` (Python) and `frontend/` (TypeScript). The path-scoped rules add the language detail.

## General
- Minimal code. No speculative abstractions. No options nobody asked for.
- Concise but descriptive. A name says what a thing is or does; a reader should not need the comment to follow the code.
- Prefer editing an existing file to adding one. Delete what is unused. No dead branches.
- Every public function, class, component and type carries a one-line summary in the language's doc format (Google-style docstrings in Python, JSDoc in TypeScript). Sections (`Args:`, `@param`) only when they add something the signature does not say. Other comments are single line and only where the code cannot say it. No comment blocks. No commented-out code.
- Comments are written for someone new to the codebase. A hard-to-follow part gets a single-line comment above it saying concisely what happens there. Never cite the spec, the plan, decision or question ids (`D14`, `Q-4`), review rounds or the history of a choice. Where a library's behaviour is the reason, link that library's docs; where a module has its own page under `docs/`, link that page.
- Every change is verifiable. If you cannot test it, say so before shipping it.
- Match the surrounding code's style, not its gaps.

## Functional and declarative style (a hard requirement)
- Functional core, imperative shell. Domain logic (validation, ordering, search filters, mapping rows to responses) is pure functions with no I/O. Routers, repositories and React components are the thin shell that does I/O and calls the core.
- Never mutate an input. Return a new value. Python: frozen dataclasses, Pydantic models with `frozen=True` where they flow through the core, tuples over lists for fixed data. TypeScript: `const`, `readonly`, spread, `toSorted`/`toSpliced`/`with` over `sort`/`splice`.
- Prefer expressions to statements: `map`, `filter`, `reduce`, comprehensions and generator expressions over loops that append into an accumulator. Use a loop only when it reads more clearly, and never just to mutate an outer variable.
- Compose small functions instead of writing one long one. Higher-order functions where they remove repetition: FastAPI `Depends` factories, decorators, hooks that take a query function, comparator builders. Do not add one for a single caller.
- Pick the data structure for the access pattern: a dict or `Map` for lookup by id, a set for membership, a list or tuple for order. Say why in review when it is not obvious.
- No hidden shared mutable state: no module-level caches that requests write to, no singletons holding request data.

## Async and concurrency (a hard requirement)
- Use the high-level abstraction, never hand-rolled threads or callbacks. Backend: `async def` handlers, the async SQLAlchemy session, `asyncio.TaskGroup` (or `gather`) when independent awaits can run together. Frontend: TanStack Query for all server state (caching, retries, cancellation, optimistic updates with rollback), never `useEffect` plus `fetch`.
- Never block the event loop. CPU-heavy work (password hashing) runs through `asyncio.to_thread` or the library's async API.

## Boundaries and types
- Every value that crosses a boundary (HTTP body, database row, token claims, storage, URL params) is a typed model, validated right after it is read: Pydantic in Python, Zod in TypeScript. Field access happens on the validated value. No `dict[str, Any]`, `any` or `Record<string, unknown>` for a known shape.
- Type hints on every parameter and return value, tests included. TypeScript is `strict`; no `any`, no `as unknown as`, no `@ts-ignore`.

## Logging
- Logs exist to monitor the running app and find bugs. Keep every line that does that: startup and ready, shutdown, a caught exception with its context, a request that failed auth or validation at WARNING, a degraded path taken.
- Remove every line added only to chase a bug during development before the commit. A log line that would not help someone on call is noise.
- Backend: `log = logging.getLogger(__name__)`, never `print`. Frontend: `console.info` for lifecycle, `console.warn` and `console.error` for failures; never `console.log` or `console.debug`. ESLint enforces the frontend list.
- WARNING and ERROR lines say where, why and what happens next, with ids as key=value (`user_id=`, `task_id=`, `request_id=`). Never log secrets, passwords, tokens or full request bodies.

## Hygiene
- No `TODO`, `FIXME`, `XXX` or `HACK` in code. A follow-up goes in the PR description or an issue.
- No `debugger`, `breakpoint()`, `pdb`, or focused tests (`.only`). `python3 scripts/check_hygiene.py` checks all of this and runs in CI and in `/verify`.
- Secrets never appear in code, logs, tests, or chat. `.env` files and key material are off limits; a hook enforces this. Anything bundled into the frontend is public.
