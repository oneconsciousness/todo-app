"""Pipe hook payloads into transcript-backup.py and check the snapshots it leaves."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "transcript-backup.py"
SESSION = "11111111-2222-3333-4444-555555555555"


def run(payload: dict[str, str] | str, project: Path) -> subprocess.CompletedProcess[str]:
    """Run the hook with the payload on stdin and the project root in the environment."""
    body = payload if isinstance(payload, str) else json.dumps(payload)
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project)}
    return subprocess.run([sys.executable, str(HOOK)], input=body, capture_output=True, text=True, timeout=30, env=env)


class TranscriptBackup(unittest.TestCase):
    """transcript-backup.py snapshots, never overwrites, and flags rewrites."""

    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp(prefix="transcripts-"))
        self.project = Path(tempfile.mkdtemp(prefix="project-"))
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.addCleanup(shutil.rmtree, self.project, ignore_errors=True)
        self.transcript = self.home / f"{SESSION}.jsonl"
        self.transcript.write_text('{"n": 1}\n')
        (self.home / SESSION / "subagents").mkdir(parents=True)
        (self.home / SESSION / "subagents" / "agent-a.jsonl").write_text('{"sub": 1}\n')

    def payload(self, event: str, **extra: str) -> dict[str, str]:
        return {"session_id": SESSION, "transcript_path": str(self.transcript), "cwd": "/elsewhere", "hook_event_name": event, **extra}

    def snapshots(self) -> list[Path]:
        return sorted((self.project / ".ai-transcripts" / SESSION).iterdir())

    def test_copies_transcript_set_aside_copies_and_session_folder(self) -> None:
        (self.home / f"{SESSION}.jsonl.superseded-1").write_text('{"old": 1}\n')
        result = run(self.payload("PreCompact", trigger="auto"), self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        [snap] = self.snapshots()
        self.assertTrue(snap.name.endswith("-precompact-auto"))
        self.assertEqual((snap / self.transcript.name).read_text(), '{"n": 1}\n')
        self.assertTrue((snap / f"{SESSION}.jsonl.superseded-1").is_file())
        self.assertEqual((snap / "session" / "subagents" / "agent-a.jsonl").read_text(), '{"sub": 1}\n')

    def test_appended_transcript_adds_a_snapshot_and_keeps_the_first(self) -> None:
        run(self.payload("PreCompact", trigger="manual"), self.project)
        with self.transcript.open("a") as f:
            f.write('{"n": 2}\n')
        result = run(self.payload("PostCompact", trigger="manual"), self.project)
        self.assertEqual((result.returncode, result.stderr), (0, ""))
        first, second = self.snapshots()
        self.assertEqual((first / self.transcript.name).read_text(), '{"n": 1}\n')
        self.assertEqual((second / self.transcript.name).read_text(), '{"n": 1}\n{"n": 2}\n')

    def test_rewritten_transcript_is_reported_and_both_versions_kept(self) -> None:
        run(self.payload("PreCompact", trigger="auto"), self.project)
        self.transcript.write_text('{"summary": 1}\n')
        result = run(self.payload("PostCompact", trigger="auto"), self.project)
        self.assertEqual(result.returncode, 2)
        self.assertIn("rewritten", result.stderr)
        first, second = self.snapshots()
        self.assertEqual((first / self.transcript.name).read_text(), '{"n": 1}\n')
        self.assertEqual((second / self.transcript.name).read_text(), '{"summary": 1}\n')

    def test_rewrite_found_before_compaction_does_not_block_it(self) -> None:
        run(self.payload("SessionEnd", reason="other"), self.project)
        self.transcript.write_text('{"summary": 1}\n')
        result = run(self.payload("PreCompact", trigger="auto"), self.project)
        self.assertEqual(result.returncode, 0)
        self.assertIn("rewritten", result.stderr)
        self.assertEqual(len(self.snapshots()), 2)

    def test_missing_transcript_blocks_compaction(self) -> None:
        self.transcript.unlink()
        result = run(self.payload("PreCompact", trigger="auto"), self.project)
        self.assertEqual(result.returncode, 2)
        self.assertIn("not backed up", result.stderr)
        self.assertFalse((self.project / ".ai-transcripts").exists())

    def test_unreadable_payload_blocks_compaction(self) -> None:
        result = run("not json", self.project)
        self.assertEqual(result.returncode, 2)
        self.assertIn("not backed up", result.stderr)


if __name__ == "__main__":
    unittest.main()
