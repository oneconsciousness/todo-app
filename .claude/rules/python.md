---
paths:
  - "backend/**/*.py"
---
# Python

## Boundaries and types
- Pydantic models at every boundary: request and response bodies, database rows leaving the repository layer, token claims. `Model.model_validate(raw)` right after deserializing; field access happens on the model.
- Request and response models are separate types (`TaskCreate`, `TaskUpdate`, `TaskRead`). A response never exposes a column the client should not see, such as a password hash.
- Settings are one pydantic-settings class. With `extra="ignore"` a typo in an env var name fails silently, so check the name when a value is missing.
- `X | None` and `dict[str, X]`. `Mapping` and `Sequence` for parameters you only read. A frozen dataclass or TypedDict for a value that stays inside the service; a Pydantic model for anything that crosses a boundary.
- `uv run mypy` runs in strict mode and passes.

## Docstrings
- Google style: a summary line in the imperative, a blank line, then `Args:`, `Returns:`, `Raises:` as needed. Types stay in the hints, never repeated in the docstring. Private helpers and tests need only the summary line, and only when the name does not already say it.

## FastAPI
- Routers stay thin: parse, call the service or core, map the result to a response model. No SQL and no business rules in a router.
- Dependencies (`Depends`) compose the request: settings, session, current user. Ownership is enforced in the query (`WHERE owner_id = :user_id`), not by loading a row and checking it afterwards.
- Domain errors are exceptions raised by the service and turned into HTTP responses by one set of exception handlers in the app factory. Handlers never build error bodies by hand. The status code contract is in `api-contract.md`.
- Build the app in a factory (`create_app(settings)`) so tests build their own app with their own settings.

## Failure handling and logging
- On a validation error at a boundary: log at WARNING with the function name, the error, and a sanitized snippet, then take the documented fail-soft path. Never silent.
- `log = logging.getLogger(__name__)`. No `print`. The root logger is configured once, in the app factory, before any request is served.
- WARNING and ERROR lines say where (`module.function`), why, and what happens next, with ids as key=value. Never log secrets.

## Async and boot
- asyncio throughout. Do not block the event loop: no sync database driver, no blocking hashing on the loop.
- Never add a network call at import time; put it in the lifespan. A database the app cannot reach makes `/readyz` fail, not the import.
