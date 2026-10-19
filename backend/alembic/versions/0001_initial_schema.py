"""Create users and tasks, with their extensions, constraints and indexes.

Revision ID: 0001
Revises:
Create Date: 2026-10-19
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE = (
    "CREATE EXTENSION IF NOT EXISTS citext",
    "CREATE EXTENSION IF NOT EXISTS pg_trgm",
    # The email check is the basic shape only (one @, a dot in the domain, no spaces);
    # the API validates full email syntax before a row gets here.
    r"""
    CREATE TABLE users (
      id            uuid PRIMARY KEY,
      email         citext NOT NULL,
      password_hash text NOT NULL,
      created_at    timestamptz NOT NULL DEFAULT now(),
      CONSTRAINT ck_users_email_length CHECK (char_length(email) <= 254),
      CONSTRAINT ck_users_email_shape  CHECK (email ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$')
    )
    """,
    "CREATE UNIQUE INDEX uq_users_email ON users (email)",
    # COLLATE "C" sorts rank byte by byte, the same order Python gives the keys.
    """
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
      CONSTRAINT ck_tasks_title_not_blank  CHECK (char_length(btrim(title)) >= 1),
      CONSTRAINT ck_tasks_notes_length     CHECK (char_length(notes) <= 5000),
      CONSTRAINT ck_tasks_version_positive CHECK (version >= 1),
      CONSTRAINT ck_tasks_rank_not_empty   CHECK (rank <> '')
    )
    """,
    # Serves the owner filter, the rank order and the neighbour reads, and keeps ranks unique per user.
    "CREATE UNIQUE INDEX uq_tasks_owner_rank ON tasks (owner_id, rank)",
    # One trigram index answers `title ILIKE :p OR notes ILIKE :p` through a bitmap OR
    # (https://www.postgresql.org/docs/18/pgtrgm.html#PGTRGM-INDEX).
    "CREATE INDEX ix_tasks_search_trgm ON tasks USING gin (title gin_trgm_ops, notes gin_trgm_ops)",
)

DOWNGRADE = (
    "DROP TABLE tasks",
    "DROP TABLE users",
    "DROP EXTENSION IF EXISTS pg_trgm",
    "DROP EXTENSION IF EXISTS citext",
)


def upgrade() -> None:
    """Create the extensions, both tables and their indexes."""
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    """Drop both tables, then both extensions."""
    for statement in DOWNGRADE:
        op.execute(statement)
