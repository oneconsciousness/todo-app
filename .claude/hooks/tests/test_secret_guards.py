"""Pipe payloads into env-protection.py and secrets-protection.py and check that only `.env.example` is open."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
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
    "cat .{e,}nv", "cat {.,}env", "cat .{env,x}", "cat .e{n,}v",
    'cat .e""nv', "cat .e\\nv", "cat '.env'", 'cat ".env"', "cat $'.env'",
    "git show HEAD:.env", "cat <.env", "while read l; do echo $l; done < .env",
    "python3 -c \"print(open('.env').read())\"", "find . -name .env -exec cat {} \\;", "find . -name '.e*' -exec cat {} +",
    "find . -type f -exec cat {} +", "find . -type f -execdir head {} \\;", "find . -type f | xargs cat", "find . -print0 | xargs -0 grep SECRET",
    "grep -r SECRET .", "grep -rn JWT backend", "grep -Rin token .", "grep --recursive x .", "egrep -r x .",
    "grep -d recurse SECRET .", "grep --directories=recurse SECRET .", "grep --directories recurse x .",
    "git grep --no-index SECRET", "git grep --untracked --no-exclude-standard SECRET",
    "rg --hidden JWT", "rg -uu JWT", "rg -u -u JWT", "rg --unrestricted --unrestricted JWT", "rg -uuu JWT", "rg --no-ignore JWT",
    "docker compose config", "docker compose -f docker-compose.yml config", "docker inspect todo-api-1",
    "docker compose exec api env", "docker compose exec api printenv JWT_SECRET",
    "cat server.pem", "head -n 5 ~/.aws/credentials", "grep TOKEN secrets.json", "awk '{print}' id_rsa",
    'cat "server.key"', "/bin/cat id_rsa", "sed -n p server.key", "base64 id_rsa", "cat config/credentials.yaml",
    "grep --recur SECRET .", "grep --dir=recurse SECRET .", "find . -type f -exec sh -c 'cat \"$0\"' {} \\;",
    "find . -exec env cat {} +", "find . -type f -exec perl -pe1 {} +", "cat .e{m..o}v", "cat .(env|x)",
    "env grep -r SECRET .", "command -p grep -r x .", "sudo -u x grep -r x .", "{ grep -r x .; }",
    "if true; then grep -r x .; fi", "echo `grep -r x .`", "git grep --no-inde x", "ugrep -r x .", "ug -. x",
    "git add -f . && git diff --cached", "git add --force .", "git stash -a", "git stash push --all",
    "tar -cf - . | tar -xOf -", "docker compose convert", "docker compose exec api cat /proc/1/environ",
    "docker compose exec api sh -c 'printenv'",
    "paste server.key", "tr -d x < server.key", "openssl rsa -in server.key", "dd if=server.key",
    "perl -pe1 server.key", "ln -s server.key x.txt", "sudo -u x cat server.key", "{ cat server.key; }",
    "echo `cat server.key`", "git diff --no-index /dev/null server.key",
)

BASH_ALLOWED = (
    "cat .env.example", "cat ./.env.example", "cat frontend/.env.example", "sed -n 1,5p .env.example",
    "grep JWT .env.example", "cat '.env.example'", "cat .ENV.EXAMPLE", "diff .env.example backend/.env.example",
    "git diff -- .env.example", "git add .env.example", "cp .env.example /tmp/example-copy", "ls -la .env.example",
    "rg JWT", "rg -n JWT backend", "rg 'import\\.meta\\.env' frontend/src", "git grep -n JWT", "git grep --untracked JWT",
    "grep -n x README.md", "grep -c x file.txt | sort -r", "grep -l TOKEN secrets.json",
    "find . -name '*.pyc' -delete", "find src -type f -name '*.ts'", "find . -name '*.pyc' -exec rm {} +",
    "docker compose config --no-interpolate", "docker compose ps", "docker compose logs api",
    "cat environment.md", "ls src", "python3 scripts/check_hygiene.py", "uv run pytest", "ls -la server.pem",
    "sed -i 's/a/b/' server.key", "cat backend/app/auth/credentials.py", "cat frontend/src/lib/secrets.ts", "cat README.md",
    "find backend -name '*.py' -exec grep -l create_app {} +", "git ls-files '*.py' | xargs grep -n x",
    "rg -l old | xargs sed -i '' 's/old/new/g'", "find . -name '*.pyc' -exec rm -f {} +", "git add -A", "git add backend/app/main.py",
    "git stash push -m wip", "git diff", "git diff --stat HEAD~1", "tar -czf backup.tgz backend", "docker compose exec api alembic upgrade head",
    "env FOO=1 uv run pytest", "if true; then echo ok; fi", "{ echo a; echo b; }",
)

BRACE_BOMB = "cat " + "{a,b}" * 30

PATH_DENIED = (
    "/repo/.env", "/repo/.env.local", "/repo/backend/.env", "/repo/.ENV", "/repo/.env.example.bak", "/repo/.env.examples",
    "/repo/server.key", "/repo/credentials.json", "/repo/config/secrets.yaml", "/repo/.ssh/notes.ipynb",
)
PATH_ALLOWED = (
    "/repo/.env.example", "/repo/frontend/.env.example", "/repo/.ENV.EXAMPLE", "/repo/README.md",
    "/repo/backend/app/auth/credentials.py", "/repo/frontend/src/lib/secrets.ts", "/repo/docs/environment.md",
)

GREP_DENIED = ({"path": "/repo/.env"}, {"path": "/repo/.env.local"}, {"glob": ".env*"}, {"glob": ".e*"}, {"glob": "*env*"}, {"glob": "**/.env"})
GREP_ALLOWED = ({"path": "/repo/.env.example"}, {"glob": ".env.example"}, {"glob": "*.py"}, {"glob": "*"}, {"path": "/repo/backend"}, {"glob": "*environment*.md"})


def run(hook: str, tool: str, tool_input: dict[str, str]) -> bool:
    """Run one hook with a PreToolUse payload and return True when it denies."""
    payload = {"session_id": "t", "cwd": "/tmp", "hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input}
    return decision(subprocess.run([sys.executable, str(HOOKS / hook)], input=json.dumps(payload), capture_output=True, text=True, timeout=30, cwd="/tmp"))


def decision(result: subprocess.CompletedProcess[str]) -> bool:
    """True when the hook printed the deny shape."""
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
        self.assertTrue(run("secrets-protection.py", "NotebookEdit", {"notebook_path": "/repo/.ssh/notes.ipynb"}))

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

    def test_a_brace_expansion_too_large_to_check_is_refused_quickly(self) -> None:
        started = time.monotonic()
        self.assertTrue(run("env-protection.py", "Bash", {"command": BRACE_BOMB}))
        self.assertLess(time.monotonic() - started, 5)

    def test_an_unreadable_payload_is_refused(self) -> None:
        for hook in BASH_HOOKS:
            with self.subTest(hook=hook):
                result = subprocess.run([sys.executable, str(HOOKS / hook)], input="not json", capture_output=True, text=True, timeout=30)
                self.assertTrue(decision(result))


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
