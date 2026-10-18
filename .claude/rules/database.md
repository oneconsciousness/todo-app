---
paths:
  - "backend/alembic/**"
  - "backend/app/db/**"
  - "backend/**/models.py"
  - "backend/**/repository.py"
---
# Database

- Schema changes go through a new alembic migration, numbered after the last one. Never edit a migration that has been applied anywhere. Never change the database by hand.
- Run migrations with `uv run alembic upgrade head` from `backend/`. Deployed environments run them as a one-shot step (a Kubernetes Job or init step) before the new pods take traffic, never from app startup, because several replicas would race.
- Every migration has a working `downgrade`. CI runs upgrade, downgrade and upgrade again.
- Every query is parameterized through SQLAlchemy. No string-built SQL. Index every column used in WHERE, JOIN or ORDER BY, starting with `tasks(owner_id, position)`.
- Every query against `tasks` filters on the owner. A query without the owner filter is a bug, even in an admin path.
- Writes that must stay consistent (reorder, delete with a position gap) run in one transaction.
