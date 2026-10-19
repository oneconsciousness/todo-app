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
- Every query is parameterized through SQLAlchemy. No string-built SQL. Index every column used in WHERE, JOIN or ORDER BY, starting with `tasks(owner_id, rank)`.
- Transactions run at READ COMMITTED, Postgres's default. Do not raise it: the ordering lock below depends on each statement reading a fresh snapshot.
- Creating or moving a task takes `pg_advisory_xact_lock(hashtextextended(owner_id::text, 0))` as the first statement of its transaction, then reads the neighbours. A unique index on `(owner_id, rank)` backs it up. Edits and deletes do not take the lock.
- `rank` is `text COLLATE "C"` so Postgres sorts it byte by byte, like Python. Edits check `version` in the `UPDATE`'s `WHERE` and bump it.
- Unique facts are enforced by unique indexes, and the insert's `IntegrityError` becomes 409. Never check-then-insert.
- Pool: 10 connections plus 5 overflow per process, 5 s wait, `pool_pre_ping`; `statement_timeout` 5 s and `idle_in_transaction_session_timeout` 10 s on every connection.
- Every query against `tasks` filters on the owner. A query without the owner filter is a bug, even in an admin path.
- Writes that must stay consistent (create at the top, move) run in one transaction.
