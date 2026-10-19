---
paths:
  - "backend/app/api/**"
  - "backend/app/main.py"
  - "backend/tests/integration/**"
  - "frontend/src/lib/api/**"
---
# API contract

The REST contract between `backend/` and `frontend/`. Change both sides in the same PR, or neither.

- Resources are nouns under `/api/v1`: `/auth/...`, `/tasks`, `/tasks/{id}`. Standard methods: `GET` reads, `POST` creates, `PATCH` updates part of a resource, `DELETE` removes. A move is `PUT /tasks/{id}/position` with `{"afterId": ...}`: the task goes right after that task, or to the top when it is null. JSON in and out.
- Status codes:

| Case | Code |
|---|---|
| Read or update succeeded | 200 |
| Created; the response carries the resource and a `Location` header | 201 |
| Deleted | 204, no body |
| Body, query or `If-Match` header fails validation, or a move's `afterId` is not one of the user's other tasks | **400** (FastAPI's default is 422; the app maps `RequestValidationError` to 400 in one handler) |
| No token, bad token, expired token, wrong password | 401 |
| Authenticated but not allowed to do this action | 403 |
| Resource missing, **or owned by another user** (so ids of other users' tasks are never confirmed) | 404 |
| Conflict with current state, such as an email already registered | 409 |
| `If-Match` names an old version of the task | 412 |
| Overloaded (in-flight limit, no free database connection) or database unreachable | 503 |
| Any other HTTP-level error the framework raises (for example 415): the envelope with code `http_error` and the original status | as raised |

- JSON field names are camelCase on the wire (`dueDate`, `createdAt`). Pydantic models use `alias_generator=to_camel` with `populate_by_name=True`; Python code keeps snake_case.
- Tasks carry an integer `version`, returned as the `ETag` header as a quoted number (`"3"`). `PATCH` honours `If-Match` (412 on mismatch) and changes only the fields sent; without `If-Match` it always applies. Every edit bumps the version; a move does not.
- Every error body has one shape, a typed model: `{"error": {"code": "...", "message": "...", "details": [...]}}`. `code` is a stable machine string the frontend switches on; `message` is safe to show a user.
- List endpoints return a typed envelope, not a bare array, so paging can be added without breaking clients.
- The frontend parses every response with a Zod schema that mirrors the backend's Pydantic model. When a model changes, the schema changes in the same PR, and the integration test for that endpoint asserts the new shape.
- Every endpoint has an integration test for its success code and each error code it can return.
