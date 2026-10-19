"""Pipe payloads into env-protection.py and secrets-protection.py and check that only `.env.example` is open."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent
BASH_HOOKS = ("env-protection.py", "secrets-protection.py")

BASH_DENIED = (
    "cat .env", "cat ./.env", "cat backend/.env", "cat $HOME/.env", "cat .env.local", "source .env", ". ./.env",
    "export $(cat .env | xargs)", "cat .ENV", "cat .Env.Local",
    "cat .env.example .env", "cat .env.example; cat .env", "cat .env.example && cat .env", "cat .env.example|cat .env",
    "cp .env.example .env", "mv .env.example .env", "ln -s .env notes.txt",
    "cat .env.example.bak", "cat .env.examples", "cat .env.example*", "cat .env.exampl?", "cat .env.exam{ple,}",
    "cat {.env,.env.example}", "cat .e*", "cat .en?", "cat .[e]nv", "cat .*", "head */.e*",
    'cat .e""nv', "cat .e\\nv", "cat '.env'", 'cat ".env"', "cat $'.env'",
    "git show HEAD:.env", "cat <.env", "while read l; do echo $l; done < .env",
    "python3 -c \"print(open('.env').read())\"", "find . -name .env -exec cat {} \\;", "find . -name '.e*' -exec cat {} +",
    "grep -r SECRET .", "grep -rn JWT backend", "grep -Rin token .", "grep --recursive x .", "egrep -r x .",
    "rg --hidden JWT", "rg -uu JWT", "rg --no-ignore JWT",
    "docker compose config", "docker compose -f docker-compose.yml config", "docker inspect todo-api-1",
    "docker compose exec api env", "docker compose exec api printenv JWT_SECRET",
    "cat server.pem", "head -n 5 ~/.aws/credentials",
)

BASH_ALLOWED = (
    "cat .env.example", "cat ./.env.example", "cat frontend/.env.example", "sed -n 1,5p .env.example",
    "grep JWT .env.example", "cat '.env.example'", "cat .ENV.EXAMPLE", "diff .env.example backend/.env.example",
    "git diff -- .env.example", "git add .env.example", "cp .env.example /tmp/example-copy", "ls -la .env.example",
    "rg JWT", "rg -n JWT backend", "git grep -n JWT", "grep -n x README.md", "grep -c x file.txt | sort -r",
    "docker compose config --no-interpolate", "docker compose ps", "docker compose logs api",
    "cat environment.md", "ls src", "python3 scripts/check_hygiene.py", "uv run pytest",
)

PATH_DENIED = ("/repo/.env", "/repo/.env.local", "/repo/backend/.env", "/repo/.ENV", "/repo/.env.example.bak", "/repo/.env.examples", "/repo/server.key")
PATH_ALLOWED = ("/repo/.env.example", "/repo/frontend/.env.example", "/repo/.ENV.EXAMPLE", "/repo/README.md")

GREP_DENIED = ({"path": "/repo/.env"}, {"path": "/repo/.env.local"}, {"glob": ".env*"}, {"glob": ".e*"}, {"glob": "*env*"}, {"glob": "**/.env"})
GREP_ALLOWED = ({"path": "/repo/.env.example"}, {"glob": ".env.example"}, {"glob": "*.py"}, {"glob": "*"}, {"path": "/repo/backend"}, {"glob": "*environment*.md"})


def run(hook: str, tool: str, tool_input: dict[str, str]) -> bool:
    """Run one hook with a PreToolUse payload and return True when it denies."""
    payload = {"session_id": "t", "cwd": "/tmp", "hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input}
    result = subprocess.run(["python3", str(HOOKS / hook)], input=json.dumps(payload), capture_output=True, text=True, timeout=30, cwd="/tmp")
    return bool(result.stdout.strip()) and json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def bash_denied(command: str) -> bool:
    """True when any of the Bash hooks denies the command, as Claude Code would."""
    return any(run(hook, "Bash", {"command": command}) for hook in BASH_HOOKS)


class EnvExampleIsTheOnlyOpening(unittest.TestCase):
    """Agents may read and write `.env.example` by its exact name, and nothing else in the `.env` family."""

    def test_bash_commands_that_reach_a_secret_are_denied(self) -> None:
        for command in BASH_DENIED:
            with self.subTest(command=command):
                self.assertTrue(bash_denied(command))

    def test_bash_commands_on_the_example_or_no_secret_are_allowed(self) -> None:
        for command in BASH_ALLOWED:
            with self.subTest(command=command):
                self.assertFalse(bash_denied(command))

    def test_file_tools_deny_secret_paths(self) -> None:
        for tool in ("Read", "Write", "Edit", "MultiEdit"):
            for path in PATH_DENIED:
                with self.subTest(tool=tool, path=path):
                    self.assertTrue(run("secrets-protection.py", tool, {"file_path": path}))

    def test_file_tools_allow_the_example_and_ordinary_files(self) -> None:
        for tool in ("Read", "Write", "Edit", "MultiEdit"):
            for path in PATH_ALLOWED:
                with self.subTest(tool=tool, path=path):
                    self.assertFalse(run("secrets-protection.py", tool, {"file_path": path}))

    def test_grep_tool_denies_secret_paths_and_env_globs(self) -> None:
        for tool_input in GREP_DENIED:
            with self.subTest(tool_input=tool_input):
                self.assertTrue(run("secrets-protection.py", "Grep", {"pattern": "x", **tool_input}))

    def test_grep_tool_allows_the_example_and_ordinary_searches(self) -> None:
        for tool_input in GREP_ALLOWED:
            with self.subTest(tool_input=tool_input):
                self.assertFalse(run("secrets-protection.py", "Grep", {"pattern": "x", **tool_input}))


class SymlinkedExample(unittest.TestCase):
    """A `.env.example` that is a symlink to a real secret is treated as that secret."""

    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="env-guard-"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        (self.dir / ".env").write_text("SECRET=1\n")
        self.link = self.dir / "linked" / ".env.example"
        self.link.parent.mkdir()
        os.symlink(self.dir / ".env", self.link)
        self.real = self.dir / ".env.example"
        self.real.write_text("SECRET=change-me\n")

    def test_a_symlink_to_a_secret_is_denied_for_every_tool(self) -> None:
        for tool in ("Read", "Write", "Edit"):
            with self.subTest(tool=tool):
                self.assertTrue(run("secrets-protection.py", tool, {"file_path": str(self.link)}))
        self.assertTrue(bash_denied(f"cat {self.link}"))

    def test_a_real_example_file_is_allowed(self) -> None:
        for tool in ("Read", "Write", "Edit"):
            with self.subTest(tool=tool):
                self.assertFalse(run("secrets-protection.py", tool, {"file_path": str(self.real)}))
        self.assertFalse(bash_denied(f"cat {self.real}"))


if __name__ == "__main__":
    unittest.main()
