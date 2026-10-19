"""Pipe Claude Code hook payloads into every hook and check the decision. Ported from the claude-ag template suite."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TEMPLATES = (".",)


def run_hook(template: str, hook: str, payload: dict, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    """Run one hook script with the payload on stdin."""
    script = ROOT / template / ".claude" / "hooks" / hook
    return subprocess.run(
        ["python3", str(script)], input=json.dumps(payload), capture_output=True, text=True, timeout=120, cwd=cwd,
    )


def denied(result: subprocess.CompletedProcess[str]) -> bool:
    """True when the hook returned the PreToolUse deny shape."""
    if not result.stdout.strip():
        return False
    return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def bash(command: str, cwd: str) -> dict:
    """Build a PreToolUse payload for the Bash tool."""
    return {"session_id": "t", "cwd": cwd, "hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": command}}


def git(cwd: str, *args: str) -> str:
    """Run git in cwd and return stdout."""
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, check=True).stdout


def make_repo() -> str:
    """Create a temporary repo on `main` with one commit and a v1.0.0 tag."""
    cwd = tempfile.mkdtemp(prefix="claude-ag-")
    git(cwd, "init", "-q", "-b", "main")
    git(cwd, "config", "user.email", "t@example.com")
    git(cwd, "config", "user.name", "t")
    Path(cwd, "README.md").write_text("x\n")
    git(cwd, "add", ".")
    git(cwd, "commit", "-q", "-m", "init")
    git(cwd, "tag", "v1.0.0")
    return cwd


class BranchProtection(unittest.TestCase):
    """branch-protection.py decisions, identical in both templates."""

    def setUp(self) -> None:
        self.repo = make_repo()
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)

    def decide(self, command: str) -> bool:
        results = [denied(run_hook(t, "branch-protection.py", bash(command, self.repo))) for t in TEMPLATES]
        self.assertEqual(len(set(results)), 1, f"templates disagree on {command!r}")
        return results[0]

    def test_on_main(self) -> None:
        self.assertTrue(self.decide("git commit -m x"))
        self.assertTrue(self.decide("git push"))
        self.assertTrue(self.decide("git add . && git commit -m x"))
        self.assertFalse(self.decide("git status"))
        self.assertFalse(self.decide("ls -la"))

    def test_on_feature_branch(self) -> None:
        git(self.repo, "checkout", "-q", "-b", "feature/x")
        self.assertFalse(self.decide("git commit -m x"))
        self.assertFalse(self.decide("git push -u origin feature/x"))
        self.assertFalse(self.decide("git push -n origin feature/x"))
        self.assertTrue(self.decide("git push --no-verify origin feature/x"))
        self.assertTrue(self.decide("git commit -n -m x"))
        self.assertTrue(self.decide("git commit --no-verify -m x"))
        self.assertTrue(self.decide("git push origin HEAD:main"))
        self.assertTrue(self.decide("git push origin feature/x:main"))
        self.assertTrue(self.decide("git push --force origin main"))
        self.assertTrue(self.decide("git push -f origin main"))
        self.assertTrue(self.decide("git checkout main && git commit -m x"))
        self.assertFalse(self.decide("git checkout main && git pull"))
        self.assertTrue(self.decide("git push origin feature/x:refs/heads/main"))
        self.assertTrue(self.decide("git push origin refs/heads/main"))
        self.assertTrue(self.decide("git push origin +HEAD:main"))

    def test_round_branches_are_protected_like_main(self) -> None:
        git(self.repo, "checkout", "-q", "-b", "feature/x")
        self.assertTrue(self.decide("git push origin HEAD:round/1-containers"))
        self.assertTrue(self.decide("git push origin feature/x:refs/heads/round/1-containers"))
        self.assertTrue(self.decide("git push --force origin round/1-containers"))
        self.assertTrue(self.decide("git checkout round/1-containers && git commit -m x"))
        self.assertFalse(self.decide("git push -u origin feature/x"))
        self.assertFalse(self.decide("git push -u origin feature/round-1-notes"))
        git(self.repo, "checkout", "-q", "-b", "round/1-containers")
        self.assertTrue(self.decide("git commit -m x"))
        self.assertTrue(self.decide("git push"))
        self.assertFalse(self.decide("git pull"))

    def test_tags(self) -> None:
        git(self.repo, "checkout", "-q", "-b", "feature/x")
        self.assertTrue(self.decide("git tag -d v1.0.0"))
        self.assertTrue(self.decide("git tag -f v1.0.0"))
        self.assertTrue(self.decide("git tag v1.0.0"))
        self.assertTrue(self.decide("git push origin :refs/tags/v1.0.0"))
        self.assertTrue(self.decide("git push --delete origin v1.0.0"))
        self.assertFalse(self.decide("git tag -a v1.0.1 -m 'release 1.0.1'"))
        self.assertFalse(self.decide("git push origin v1.0.1"))

    def test_bad_payload_allows(self) -> None:
        for t in TEMPLATES:
            script = ROOT / t / ".claude" / "hooks" / "branch-protection.py"
            r = subprocess.run(["python3", str(script)], input="not json", capture_output=True, text=True)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout, "")


class EnvProtection(unittest.TestCase):
    """env-protection.py blocks any command naming a .env path."""

    def decide(self, command: str) -> bool:
        results = [denied(run_hook(t, "env-protection.py", bash(command, "/tmp"))) for t in TEMPLATES]
        self.assertEqual(len(set(results)), 1)
        return results[0]

    def test_decisions(self) -> None:
        self.assertTrue(self.decide("cat .env"))
        self.assertTrue(self.decide("source backend/.env.local"))
        self.assertFalse(self.decide("cat .env.example"))
        self.assertFalse(self.decide("ls src"))
        self.assertFalse(self.decide("cat environment.md"))


class SecretsProtection(unittest.TestCase):
    """secrets-protection.py covers key material and printing readers."""

    def decide(self, payload: dict) -> bool:
        results = [denied(run_hook(t, "secrets-protection.py", payload)) for t in TEMPLATES]
        self.assertEqual(len(set(results)), 1)
        return results[0]

    def edit(self, tool: str, path: str) -> dict:
        key = "notebook_path" if tool == "NotebookEdit" else "file_path"
        return {"session_id": "t", "cwd": "/tmp", "hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": {key: path}}

    def test_bash(self) -> None:
        self.assertTrue(self.decide(bash("cat server.pem", "/tmp")))
        self.assertTrue(self.decide(bash("head -n 5 ~/.aws/credentials", "/tmp")))
        self.assertTrue(self.decide(bash("grep TOKEN secrets.json", "/tmp")))
        self.assertTrue(self.decide(bash("awk '{print}' id_rsa", "/tmp")))
        self.assertFalse(self.decide(bash("grep -l TOKEN secrets.json", "/tmp")))
        self.assertFalse(self.decide(bash("ls -la server.pem", "/tmp")))
        self.assertFalse(self.decide(bash("cat README.md", "/tmp")))

    def test_writes(self) -> None:
        self.assertTrue(self.decide(self.edit("Write", "/repo/.env")))
        self.assertTrue(self.decide(self.edit("Edit", "/repo/config/credentials.json")))
        self.assertTrue(self.decide(self.edit("NotebookEdit", "/repo/.ssh/notes.ipynb")))
        self.assertFalse(self.decide(self.edit("Write", "/repo/src/app.py")))
        self.assertFalse(self.decide(self.edit("Edit", "/repo/docs/environment.md")))


class PrTitle(unittest.TestCase):
    """pr-title.py enforces Conventional Commits on gh pr create and edit."""

    def decide(self, command: str) -> bool:
        results = [denied(run_hook(t, "pr-title.py", bash(command, "/tmp"))) for t in TEMPLATES]
        self.assertEqual(len(set(results)), 1)
        return results[0]

    def test_decisions(self) -> None:
        self.assertFalse(self.decide('gh pr create --title "fix(api): handle null body" --body x'))
        self.assertFalse(self.decide("gh pr create --title='docs: explain the hooks'"))
        self.assertFalse(self.decide("gh pr list"))
        self.assertFalse(self.decide("gh pr create --fill"))
        self.assertTrue(self.decide('gh pr create --title "Fix bug"'))
        self.assertTrue(self.decide('gh pr create --title "feat: Add thing"'))
        self.assertTrue(self.decide('gh pr create --title "docs: update readme."'))
        self.assertTrue(self.decide('gh pr edit 12 --title "promote: dev to qa"'))
        self.assertTrue(self.decide('gh pr create -t "feat(API): bad scope"'))


class DocsCheck(unittest.TestCase):
    """docs-check.py blocks gh pr create until the branch carries a docs decision."""

    def setUp(self) -> None:
        self.repo = make_repo()
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        spec = {
            "bases": ["main", "round/*"],
            "artifact_prefixes": [".claude/", "CLAUDE.md"],
            "triggers": [{"paths": ["config.py"], "artifacts": ["CLAUDE.md (Config)"]}],
        }
        d = Path(self.repo, ".claude", "skills", "claude-docs-check")
        d.mkdir(parents=True)
        (d / "map.json").write_text(json.dumps(spec))
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "chore: add docs map")
        git(self.repo, "checkout", "-q", "-b", "feature/x")

    def decide(self, command: str) -> bool:
        results = [denied(run_hook(t, "docs-check.py", bash(command, self.repo))) for t in TEMPLATES]
        self.assertEqual(len(set(results)), 1)
        return results[0]

    def commit_file(self, name: str, message: str) -> None:
        Path(self.repo, name).write_text("y\n")
        git(self.repo, "add", name)
        git(self.repo, "commit", "-q", "-m", message)

    def test_blocks_without_decision(self) -> None:
        self.commit_file("config.py", "feat: add setting")
        self.assertTrue(self.decide('gh pr create --title "feat: add setting"'))
        self.assertFalse(self.decide('gh pr create --base release/1 --title "feat: add setting"'))
        self.assertFalse(self.decide("gh pr list"))

    def test_trailer_or_artifact_change_allows(self) -> None:
        self.commit_file("config.py", "feat: add setting")
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "chore(claude): docs check, no change needed\n\nClaude-Docs: no change: setting is internal")
        self.assertFalse(self.decide('gh pr create --title "feat: add setting"'))

    def test_artifact_change_allows(self) -> None:
        self.commit_file("config.py", "feat: add setting")
        self.commit_file("CLAUDE.md", "docs: describe the setting")
        self.assertFalse(self.decide('gh pr create --title "feat: add setting"'))

    def test_child_prs_into_a_round_branch_are_checked(self) -> None:
        git(self.repo, "branch", "round/1-containers", "main")
        self.commit_file("config.py", "feat: add setting")
        self.assertTrue(self.decide('gh pr create --base round/1-containers --title "feat: add setting"'))
        self.assertFalse(self.decide('gh pr create --base release/1 --title "feat: add setting"'))

    def test_a_base_missing_locally_is_refused_rather_than_skipped(self) -> None:
        self.commit_file("config.py", "feat: add setting")
        self.assertTrue(self.decide('gh pr create --base round/9-unfetched --title "feat: add setting"'))

    def test_unmapped_change_allows(self) -> None:
        self.commit_file("notes.txt", "docs: notes")
        self.assertFalse(self.decide('gh pr create --title "docs: notes"'))


class Lint(unittest.TestCase):
    """lint.py reports findings on stderr with exit 2 and stays quiet otherwise."""

    def setUp(self) -> None:
        self.repo = make_repo()
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)

    def edit_payload(self, path: str) -> dict:
        return {"session_id": "t", "cwd": self.repo, "hook_event_name": "PostToolUse", "tool_name": "Write", "tool_input": {"file_path": path}}

    @unittest.skipUnless(shutil.which("uvx"), "uvx not on PATH")
    def test_python_findings(self) -> None:
        path = Path(self.repo, "app.py")
        path.write_text("import os\n\ndef f(a):\n    return a\n")
        for t in TEMPLATES:
            r = run_hook(t, "lint.py", self.edit_payload(str(path)))
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("F401", r.stderr)
            self.assertIn("ANN", r.stderr)

    @unittest.skipUnless(shutil.which("uvx"), "uvx not on PATH")
    def test_python_clean_file_is_quiet(self) -> None:
        path = Path(self.repo, "clean.py")
        path.write_text('"""Clean."""\n\n\ndef f(a: int) -> int:\n    """Return a."""\n    return a\n')
        for t in TEMPLATES:
            r = run_hook(t, "lint.py", self.edit_payload(str(path)))
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_typescript_without_eslint_is_quiet(self) -> None:
        pkg = Path(self.repo, "frontend")
        pkg.mkdir()
        (pkg / "package.json").write_text("{}")
        path = pkg / "probe.ts"
        path.write_text("const unused = 1;\n")
        r = run_hook(".", "lint.py", self.edit_payload(str(path)))
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_nested_node_modules_skipped(self) -> None:
        nm = Path(self.repo, "frontend", "node_modules", "x")
        nm.mkdir(parents=True)
        path = nm / "a.py"
        path.write_text("import os\n")
        self.assertEqual(run_hook(".", "lint.py", self.edit_payload(str(path))).returncode, 0)

    def test_skipped_paths_and_other_extensions(self) -> None:
        nm = Path(self.repo, "node_modules", "x")
        nm.mkdir(parents=True)
        skipped = nm / "a.ts"
        skipped.write_text("const unused = 1;\n")
        other = Path(self.repo, "notes.md")
        other.write_text("# x\n")
        for t in TEMPLATES:
            self.assertEqual(run_hook(t, "lint.py", self.edit_payload(str(skipped))).returncode, 0)
            self.assertEqual(run_hook(t, "lint.py", self.edit_payload(str(other))).returncode, 0)


if __name__ == "__main__":
    unittest.main()
