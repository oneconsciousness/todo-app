#!/usr/bin/env python3
"""PreCompact, PostCompact and SessionEnd hook. Snapshots the session transcript so no compaction can lose it.

Each run copies the session's `.jsonl`, any set-aside copies of it (`<session>.jsonl.superseded-*`, `<session>.orphaned-*`)
and the session folder (subagent transcripts, tool results) into a new timestamped folder under `BACKUP_DIR`. A snapshot
is never overwritten. Each run also checks that the previous snapshot is a byte prefix of the current transcript, and
warns on stderr when it is not, because that would mean the file was rewritten rather than appended to.

Exit 0 on success. Exit 2 on any failure: for PreCompact that blocks the compaction, so it never runs without a backup.
Exit 2 also after PostCompact or SessionEnd when a rewrite is found, which shows the warning to the user without blocking anything.
"""
import json
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import NoReturn

# --- config ---------------------------------------------------------------
BACKUP_DIR = ".ai-transcripts"  # under the project root; gitignored, scanned before any export
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Snapshot:
    """Where one run's copies go, and what the run was."""

    session_id: str
    event: str
    transcript: Path
    folder: Path
    label: str


def fail(reason: str) -> NoReturn:
    """Report the failure on stderr and exit 2."""
    print(f"transcript-backup: {reason}", file=sys.stderr)
    sys.exit(2)


def plan(payload: dict[str, str | None], root: Path, now: datetime) -> Snapshot:
    """Build the snapshot target from the hook payload."""
    session_id = payload.get("session_id") or ""
    transcript = Path(payload.get("transcript_path") or "")
    if not session_id or not transcript.is_file():
        raise FileNotFoundError(f"no transcript at {transcript!s} for session {session_id!r}")
    event = (payload.get("hook_event_name") or "manual").lower()
    detail = payload.get("trigger") or payload.get("reason") or ""
    label = "-".join(filter(None, (now.strftime("%Y%m%dT%H%M%S%fZ"), event, detail)))
    return Snapshot(session_id, event, transcript, root / BACKUP_DIR / session_id / label, label)


def previous_copy(snapshot: Snapshot) -> Path | None:
    """Return the main transcript copy from the latest earlier snapshot, if any."""
    earlier = sorted(p for p in snapshot.folder.parent.glob("*") if p.is_dir() and p.name < snapshot.label)
    copies = [p / snapshot.transcript.name for p in earlier if (p / snapshot.transcript.name).is_file()]
    return copies[-1] if copies else None


def is_prefix(older: Path, newer: Path) -> bool:
    """True when `older`'s bytes are the start of `newer`'s."""
    size = older.stat().st_size
    if size > newer.stat().st_size:
        return False
    with older.open("rb") as a, newer.open("rb") as b:
        return a.read() == b.read(size)


def take(snapshot: Snapshot) -> list[Path]:
    """Copy the transcript, its set-aside copies and the session folder; return what was written."""
    snapshot.folder.mkdir(parents=True, exist_ok=False)
    source_dir = snapshot.transcript.parent
    files = sorted(p for p in source_dir.glob(f"{snapshot.session_id}*") if p.is_file())
    written = [Path(shutil.copy2(p, snapshot.folder / p.name)) for p in files]
    session_dir = source_dir / snapshot.session_id
    if session_dir.is_dir():
        written.append(Path(shutil.copytree(session_dir, snapshot.folder / "session")))
    return written


def main() -> None:
    """Read the hook payload and take one snapshot."""
    try:
        payload = json.loads(sys.stdin.read())
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd())
        snapshot = plan(payload, root, datetime.now(timezone.utc))
        before = previous_copy(snapshot)
        take(snapshot)
    except (json.JSONDecodeError, AttributeError, OSError) as exc:
        fail(f"snapshot not taken, so the transcript is not backed up: {exc}")
    rewritten = before is not None and not is_prefix(before, snapshot.transcript)
    if rewritten:
        print(
            f"transcript-backup: {snapshot.transcript.name} no longer starts with the snapshot in {before.parent.name}; "
            f"the file was rewritten. Both versions are kept under {snapshot.folder.parent}.",
            file=sys.stderr,
        )
    sys.exit(2 if rewritten and snapshot.event != "precompact" else 0)


if __name__ == "__main__":
    main()
