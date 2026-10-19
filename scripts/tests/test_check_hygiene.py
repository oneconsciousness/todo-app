"""Run check_hygiene.py against a fresh throwaway repo per case and check what it flags."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "check_hygiene.py"


def findings(name: str, text: str) -> list[str]:
    """Write one file into a new repo, run the script there and return the findings that name that file."""
    repo = Path(tempfile.mkdtemp(prefix="hygiene-"))
    try:
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        result = subprocess.run([sys.executable, str(SCRIPT)], cwd=repo, capture_output=True, text=True, timeout=30)
        return [line for line in result.stdout.splitlines() if line.startswith(f"{name}:")]
    finally:
        shutil.rmtree(repo, ignore_errors=True)


class CheckHygiene(unittest.TestCase):
    """check_hygiene.py flags debug leftovers in shipped code and nothing else."""

    def assert_flagged(self, cases: dict[str, str]) -> None:
        for name, text in cases.items():
            with self.subTest(name=name, text=text):
                self.assertTrue(findings(name, text), f"{name}: {text!r} was not flagged")

    def assert_clean(self, cases: dict[str, str]) -> None:
        for name, text in cases.items():
            with self.subTest(name=name, text=text):
                self.assertEqual(findings(name, text), [], f"{name}: {text!r} was flagged")

    def test_task_markers_in_comments_are_flagged(self) -> None:
        self.assert_flagged({
            "backend/app/a.py": "x = 1  # TODO: tidy\n",
            "frontend/src/a.ts": "const x = 1; // FIXME later\n",
            "frontend/src/b.css": "/* XXX */ a { color: red }\n",
            "frontend/src/c.ts": "/**\n * HACK around the parser\n */\n",
            "frontend/src/d.ts": "/*\n  FIXME before release\n*/\nconst a = 1;\n",
            "backend/app/b.py": 'def f() -> None:\n    """Load tasks.\n\n    TODO: page them.\n    """\n',
            "deploy/Dockerfile": "# HACK pin\nFROM python:3.14\n",
        })

    def test_task_markers_in_code_and_strings_are_not_flagged(self) -> None:
        self.assert_clean({
            "backend/app/status.py": "class Status:\n    TODO = 'todo'\n\nstate = Status.TODO\n",
            "frontend/src/labels.ts": 'export const label = "TODO";\n',
            "backend/tests/test_x.py": "assert parse('XXX') is None\n",
        })

    def test_print_in_backend_code_is_flagged_in_any_position(self) -> None:
        self.assert_flagged({"backend/app/a.py": 'print("x")\n', "backend/app/b.py": 'print ("x")\n', "backend/app/c.py": "x = 1; print(x)\n"})

    def test_print_in_backend_tests_and_blueprint_names_are_not_flagged(self) -> None:
        self.assert_clean({"backend/tests/test_a.py": 'print("debug output in a test")\n', "backend/app/b.py": "blueprint(x)\n"})

    def test_debuggers_debug_only_console_calls_and_focused_tests_are_flagged(self) -> None:
        self.assert_flagged({
            "frontend/src/a.ts": "console.log(x);\n", "frontend/src/b.ts": "console.table(rows);\n",
            "frontend/src/c.ts": "console.debug(x);\n", "frontend/src/d.test.ts": "it.only ('x', () => {});\n",
            "frontend/src/e.ts": "debugger;\n", "backend/app/f.py": "breakpoint()\n",
        })

    def test_monitoring_logs_are_allowed(self) -> None:
        self.assert_clean({
            "frontend/src/a.ts": 'console.error("[api] failed", e);\nconsole.info("[app] started");\nconsole.warn("x");\n',
            "backend/app/a.py": 'log.warning("db unreachable, then=503")\n',
        })


if __name__ == "__main__":
    unittest.main()
