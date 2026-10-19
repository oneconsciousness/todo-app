"""Run check_hygiene.py against small throwaway repos and check what it flags."""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "check_hygiene.py"


class CheckHygiene(unittest.TestCase):
    """check_hygiene.py flags debug leftovers in shipped code and nothing else."""

    def setUp(self) -> None:
        self.repo = Path(tempfile.mkdtemp(prefix="hygiene-"))
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)

    def findings(self, files: dict[str, str]) -> list[str]:
        """Write the files, run the script and return its finding lines."""
        for name, text in files.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        result = subprocess.run([sys.executable, str(SCRIPT)], cwd=self.repo, capture_output=True, text=True, timeout=30)
        return [line for line in result.stdout.splitlines() if line and not line.startswith("hygiene check")]

    def assert_flagged(self, name: str, text: str) -> None:
        self.assertTrue(self.findings({name: text}), f"{name}: {text!r} was not flagged")

    def assert_clean(self, name: str, text: str) -> None:
        self.assertEqual(self.findings({name: text}), [], f"{name}: {text!r} was flagged")

    def test_task_markers_in_comments_are_flagged(self) -> None:
        cases = {
            "backend/app/a.py": "x = 1  # TODO: tidy\n",
            "frontend/src/a.ts": "const x = 1; // FIXME later\n",
            "frontend/src/b.css": "/* XXX */ a { color: red }\n",
            "deploy/Dockerfile": "# HACK pin\nFROM python:3.14\n",
        }
        for name, text in cases.items():
            with self.subTest(name=name):
                self.assert_flagged(name, text)

    def test_task_markers_in_code_and_strings_are_not_flagged(self) -> None:
        cases = {
            "backend/app/status.py": "class Status:\n    TODO = 'todo'\n\nstate = Status.TODO\n",
            "frontend/src/labels.ts": 'export const label = "TODO";\n',
            "backend/tests/test_x.py": "assert parse('XXX') is None\n",
        }
        for name, text in cases.items():
            with self.subTest(name=name):
                self.assert_clean(name, text)

    def test_print_in_backend_code_is_flagged_in_any_position(self) -> None:
        for text in ('print("x")\n', 'print ("x")\n', "x = 1; print(x)\n"):
            with self.subTest(text=text):
                self.assert_flagged("backend/app/a.py", text)

    def test_print_in_backend_tests_and_blueprint_names_are_not_flagged(self) -> None:
        self.assert_clean("backend/tests/test_a.py", 'print("debug output in a test")\n')
        self.assert_clean("backend/app/b.py", "blueprint(x)\n")

    def test_debug_only_console_calls_and_focused_tests_are_flagged(self) -> None:
        for name, text in (
            ("frontend/src/a.ts", "console.log(x);\n"), ("frontend/src/b.ts", "console.table(rows);\n"),
            ("frontend/src/c.ts", "console.debug(x);\n"), ("frontend/src/d.test.ts", "it.only ('x', () => {});\n"),
            ("frontend/src/e.ts", "debugger;\n"), ("backend/app/f.py", "breakpoint()\n"),
        ):
            with self.subTest(name=name):
                self.assert_flagged(name, text)

    def test_monitoring_logs_are_allowed(self) -> None:
        self.assert_clean("frontend/src/a.ts", 'console.error("[api] failed", e);\nconsole.info("[app] started");\nconsole.warn("x");\n')
        self.assert_clean("backend/app/a.py", 'log.warning("db unreachable, then=503")\n')


if __name__ == "__main__":
    unittest.main()
