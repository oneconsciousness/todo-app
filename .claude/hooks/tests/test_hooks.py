"""Pipe Claude Code hook payloads into the git, PR-title, docs and lint hooks and check each decision."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent


def run_hook(hook: str, payload: dict[str, object] | str, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    """Run one hook with the payload on stdin, under the interpreter running the tests."""
    body = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run([sys.executable, str(HOOKS / hook)], input=body, capture_output=True, text=True, timeout=120, cwd=cwd)


def denied(result: subprocess.CompletedProcess[str]) -> bool:
    """True when the hook returned the PreToolUse deny shape."""
    if not result.stdout.strip():
        return False
    return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def bash(command: str, cwd: str) -> dict[str, object]:
    """Build a PreToolUse payload for the Bash tool."""
    return {"session_id": "t", "cwd": cwd, "hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": command}}


def git(cwd: str, *args: str) -> str:
    """Run git in cwd and return stdout."""
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, check=True).stdout


def make_repo() -> str:
    """Create a temporary repo on `main` with one commit and a v1.0.0 tag."""
    cwd = tempfile.mkdtemp(prefix="hooks-")
    git(cwd, "init", "-q", "-b", "main")
    git(cwd, "config", "user.email", "t@example.com")
    git(cwd, "config", "user.name", "t")
    Path(cwd, "README.md").write_text("x\n")
    git(cwd, "add", ".")
    git(cwd, "commit", "-q", "-m", "init")
    git(cwd, "tag", "v1.0.0")
    return cwd


class BranchProtection(unittest.TestCase):
    """branch-protection.py keeps commits and pushes off `main` and round branches."""

    def setUp(self) -> None:
        self.repo = make_repo()
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)

    def decide(self, command: str) -> bool:
        return denied(run_hook("branch-protection.py", bash(command, self.repo)))

    def assert_decisions(self, denied_commands: tuple[str, ...], allowed_commands: tuple[str, ...]) -> None:
        for command in denied_commands:
            with self.subTest(denied=command):
                self.assertTrue(self.decide(command))
        for command in allowed_commands:
            with self.subTest(allowed=command):
                self.assertFalse(self.decide(command))

    def test_on_main(self) -> None:
        self.assert_decisions(
            ("git commit -m x", "git push", "git add . && git commit -m x", "git -C . commit -m x", "git -c user.name=x commit -m x"),
            ("git status", "ls -la"),
        )

    def test_on_a_feature_branch(self) -> None:
        git(self.repo, "checkout", "-q", "-b", "feature/x")
        self.assert_decisions(
            (
                "git push --no-verify origin feature/x", "git commit -n -m x", "git commit -nm x", "git commit --no-verify -m x",
                "git -c a=b commit --no-verify -m x",
                "git push origin HEAD:main", "git push origin feature/x:main", "git push origin 'HEAD:main'", 'git push origin "main"',
                "git push origin feature/x:refs/heads/main", "git push origin refs/heads/main", "git push origin +HEAD:main",
                "git push origin feature/x main", "git push origin --all", "git push --mirror origin",
                "git push --force origin main", "git push -f origin main", "git checkout main && git commit -m x",
                "sudo git push origin main", "env git push origin main", "command git push origin main", "FOO=1 git push origin main",
                "{ git push origin main; }", "if true; then git push origin main; fi", "echo `git push origin main`",
                "git -c remote.origin.push=HEAD:main push origin", "git -c alias.p=push p origin main",
                "git push origin 'refs/heads/*'", "git push -f origin 'refs/tags/*'", "git commit -u -n -m x", "git commit --no-verif -m x",
                "git update-ref refs/heads/main HEAD", "git update-ref -d refs/tags/v1.0.0",
            ),
            (
                "git commit -m x", "git commit -m 'handle the -n flag'", "git commit -am 'tidy -n output'",
                "git push -u origin feature/x", "git push -n origin feature/x", "git push origin feature/x:feature/x",
                "git checkout main && git pull", "git -c core.editor=true commit -m x", "env GIT_TRACE=1 git status",
                "git update-ref refs/heads/feature/y HEAD",
            ),
        )

    def test_a_commit_through_a_worktree_on_main_is_refused(self) -> None:
        git(self.repo, "checkout", "-q", "-b", "feature/x")
        worktree = Path(tempfile.mkdtemp(prefix="hooks-wt-")) / "wt"
        self.addCleanup(shutil.rmtree, worktree.parent, ignore_errors=True)
        git(self.repo, "worktree", "add", "-q", str(worktree), "main")
        self.assert_decisions((f"git -C {worktree} commit -m x", f"cd {worktree} && git commit -m x"), (f"git -C {worktree} status",))

    def test_round_branches_are_protected_like_main(self) -> None:
        git(self.repo, "checkout", "-q", "-b", "feature/x")
        self.assert_decisions(
            (
                "git push origin HEAD:round/1-containers", "git push origin feature/x:refs/heads/round/1-containers",
                "git push --force origin round/1-containers", "git checkout round/1-containers && git commit -m x",
            ),
            ("git push -u origin feature/x", "git push -u origin feature/round-1-notes"),
        )
        git(self.repo, "checkout", "-q", "-b", "round/1-containers")
        self.assert_decisions(("git commit -m x", "git push"), ("git pull",))

    def test_release_tags_are_never_moved(self) -> None:
        git(self.repo, "checkout", "-q", "-b", "feature/x")
        self.assert_decisions(
            (
                "git tag -d v1.0.0", "git tag -f v1.0.0", "git tag -fa v1.0.0 -m x", "git tag v1.0.0",
                "git push origin :refs/tags/v1.0.0", "git push --delete origin v1.0.0", "git push origin +v1.0.0",
                "git push --force origin v1.0.0",
            ),
            ("git tag -a v1.0.1 -m 'release 1.0.1'", "git push origin v1.0.1"),
        )

    def test_an_unreadable_payload_is_refused(self) -> None:
        self.assertTrue(denied(run_hook("branch-protection.py", "not json")))


class PrTitle(unittest.TestCase):
    """pr-title.py enforces Conventional Commits on gh pr create and edit."""

    def decide(self, command: str) -> bool:
        return denied(run_hook("pr-title.py", bash(command, "/tmp")))

    def test_decisions(self) -> None:
        for command in ('gh pr create --title "fix(api): handle null body" --body x', "gh pr create --title='docs: explain the hooks'", "gh pr list", "gh pr create --fill", 'gh pr create --title "feat(round-1): run the to do app in containers"'):
            with self.subTest(allowed=command):
                self.assertFalse(self.decide(command))
        for command in ('gh pr create --title "Fix bug"', 'gh pr create --title "feat: Add thing"', 'gh pr create --title "docs: update readme."', 'gh pr edit 12 --title "promote: dev to qa"', 'gh pr create -t "feat(API): bad scope"'):
            with self.subTest(denied=command):
                self.assertTrue(self.decide(command))


class DocsCheck(unittest.TestCase):
    """docs-check.py blocks gh pr create until the branch carries a docs decision."""

    def setUp(self) -> None:
        self.repo = make_repo()
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        spec = {
            "bases": ["main", "round/*"],
            "artifact_prefixes": [".claude/rules/", "CLAUDE.md"],
            "triggers": [{"paths": ["config.py"], "artifacts": ["CLAUDE.md (Config)"]}],
        }
        d = Path(self.repo, ".claude", "skills", "claude-docs-check")
        d.mkdir(parents=True)
        (d / "map.json").write_text(json.dumps(spec))
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "chore: add docs map")
        git(self.repo, "checkout", "-q", "-b", "feature/x")

    def decide(self, command: str) -> bool:
        return denied(run_hook("docs-check.py", bash(command, self.repo)))

    def commit_file(self, name: str, message: str) -> None:
        path = Path(self.repo, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("y\n")
        git(self.repo, "add", name)
        git(self.repo, "commit", "-q", "-m", message)

    def test_blocks_without_decision(self) -> None:
        self.commit_file("config.py", "feat: add setting")
        self.assertTrue(self.decide('gh pr create --title "feat: add setting"'))
        self.assertFalse(self.decide('gh pr create --base release/1 --title "feat: add setting"'))
        self.assertFalse(self.decide("gh pr list"))

    def test_trailer_allows(self) -> None:
        self.commit_file("config.py", "feat: add setting")
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "chore(claude): docs check, no change needed\n\nClaude-Docs: no change: setting is internal")
        self.assertFalse(self.decide('gh pr create --title "feat: add setting"'))

    def test_artifact_change_allows(self) -> None:
        self.commit_file("config.py", "feat: add setting")
        self.commit_file("CLAUDE.md", "docs: describe the setting")
        self.assertFalse(self.decide('gh pr create --title "feat: add setting"'))

    def test_an_unrelated_claude_file_is_not_a_docs_decision(self) -> None:
        self.commit_file("config.py", "feat: add setting")
        self.commit_file(".claude/hooks/tests/test_x.py", "test: add a hook test")
        self.assertTrue(self.decide('gh pr create --title "feat: add setting"'))

    def test_child_prs_into_a_round_branch_are_checked(self) -> None:
        git(self.repo, "branch", "round/1-containers", "main")
        self.commit_file("config.py", "feat: add setting")
        self.assertTrue(self.decide('gh pr create --base round/1-containers --title "feat: add setting"'))

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

    def edit_payload(self, path: Path) -> dict[str, object]:
        return {"session_id": "t", "cwd": self.repo, "hook_event_name": "PostToolUse", "tool_name": "Write", "tool_input": {"file_path": str(path)}}

    @unittest.skipUnless(shutil.which("uvx"), "uvx not on PATH")
    def test_python_findings(self) -> None:
        path = Path(self.repo, "app.py")
        path.write_text("import os\n\ndef f(a):\n    return a\n")
        r = run_hook("lint.py", self.edit_payload(path))
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("F401", r.stderr)
        self.assertIn("ANN", r.stderr)

    @unittest.skipUnless(shutil.which("uvx"), "uvx not on PATH")
    def test_python_clean_file_is_quiet(self) -> None:
        path = Path(self.repo, "clean.py")
        path.write_text('"""Clean."""\n\n\ndef f(a: int) -> int:\n    """Return a."""\n    return a\n')
        self.assertEqual(run_hook("lint.py", self.edit_payload(path)).returncode, 0)

    def test_typescript_without_eslint_is_quiet(self) -> None:
        pkg = Path(self.repo, "frontend")
        pkg.mkdir()
        (pkg / "package.json").write_text("{}")
        path = pkg / "probe.ts"
        path.write_text("const unused = 1;\n")
        self.assertEqual(run_hook("lint.py", self.edit_payload(path)).returncode, 0)

    def test_skipped_paths_and_other_extensions_are_quiet(self) -> None:
        nested = Path(self.repo, "frontend", "node_modules", "x")
        nested.mkdir(parents=True)
        (nested / "a.py").write_text("import os\n")
        other = Path(self.repo, "notes.md")
        other.write_text("# x\n")
        for path in (nested / "a.py", other):
            with self.subTest(path=path.name):
                self.assertEqual(run_hook("lint.py", self.edit_payload(path)).returncode, 0)


if __name__ == "__main__":
    unittest.main()
