#!/usr/bin/env python3
"""PreToolUse hook for Bash. Blocks commits and pushes to protected branches, `--no-verify`, and moves of release tags.

Edit the config block; every pattern and message is derived from it.

Behaviour:
  - `git commit` while on a protected branch                        -> DENY
  - `git push <remote> <protected>` / `git push <ref>:<protected>`  -> DENY
  - `git push --force` to a protected branch                        -> DENY
  - `git push` with no refspec while on a protected branch          -> DENY
  - `git checkout <protected> && git commit ...` in one command     -> DENY
  - `git commit --no-verify` / `git push --no-verify`               -> DENY
  - delete, force-move or re-create an existing release tag         -> DENY
  - everything else                                                 -> ALLOW

Returns Claude Code's PreToolUse deny shape on stdout with exit 0:
  {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                          "permissionDecision": "deny",
                          "permissionDecisionReason": "..."}}
"""
import json
import os
import re
import subprocess
import sys

# --- config ---------------------------------------------------------------
PROTECTED = ("main",)  # branches nobody commits on or pushes to directly
BASE = "main"  # where feature branches start and where PRs go
SECTION_REF = "CONTRIBUTING.md § 8 (the kind-stop protocol)"
TAG_RE = r"v\d+\.\d+\.\d+"  # release tags are never moved; set to "" to skip the guard
# --------------------------------------------------------------------------

PROTECTED_ALT = "|".join(re.escape(b) for b in PROTECTED)
PROTECTED_LIST = ", ".join(f"`{b}`" for b in PROTECTED)


def deny(reason: str) -> None:
    """Print the deny decision and exit."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def allow() -> None:
    """Exit without a decision."""
    sys.exit(0)


def current_branch(cwd: str) -> str | None:
    """Return the checked-out branch name, or None outside a repo."""
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def split_chain(command: str) -> list[str]:
    """Split a shell line on &&, || and ; into its commands."""
    parts = re.split(r"(?:&&|\|\||;)", command)
    return [p.strip() for p in parts if p.strip()]


def is_git_commit(part: str) -> bool:
    """True for `git [global opts] commit ...`."""
    return bool(re.match(r"^\s*git\s+(?:--?[A-Za-z][A-Za-z0-9=._/-]*\s+)*commit\b", part))


def is_git_push(part: str) -> bool:
    """True for `git push ...`."""
    return bool(re.match(r"^\s*git\s+push\b", part))


def is_no_verify(part: str) -> bool:
    """True when a commit or push skips git hooks. `-n` means --no-verify on commit but dry-run on push."""
    if re.match(r"^\s*git\s+commit\b", part):
        return bool(re.search(r"(?:^|\s)(?:--no-verify|-n)(?:\s|$)", part))
    if is_git_push(part):
        return bool(re.search(r"(?:^|\s)--no-verify(?:\s|$)", part))
    return False


def is_force_push(part: str) -> bool:
    """True for --force, --force-with-lease or -f."""
    return bool(re.search(r"(?:^|\s)(?:--force(?:-with-lease)?|-f)(?:\s|$)", part))


def push_targets_protected_explicit(part: str) -> bool:
    """True when the push names a protected branch as remote branch or refspec target."""
    if re.search(rf"\b(?:origin|upstream)\s+(?:{PROTECTED_ALT})(?:\s|$)", part):
        return True
    if re.search(rf":(?:{PROTECTED_ALT})(?:\s|$)", part):
        return True
    return False


def push_is_implicit(part: str) -> bool:
    """True when the push names no remote branch, so it goes to the current branch's upstream."""
    if re.search(r"\b(?:origin|upstream)\s+\S+", part):
        return False
    if re.search(r":\S+", part):
        return False
    return True


def is_checkout_protected(part: str) -> bool:
    """True for `git checkout|switch <protected>`."""
    return bool(re.search(rf"\bgit\s+(?:checkout|switch)\s+(?:{PROTECTED_ALT})(?:\s|$)", part))


def tag_violation(part: str, cwd: str) -> str | None:
    """Return a reason when the command deletes, moves or re-creates a release tag."""
    if not TAG_RE:
        return None
    if re.search(r"\bgit\s+tag\b.*(?:\s-d\b|\s--delete\b|\s-D\b)", part) and re.search(TAG_RE, part):
        return "deleting a release tag"
    if re.search(r"\bgit\s+tag\b.*(?:\s-f\b|\s--force\b)", part) and re.search(TAG_RE, part):
        return "moving a release tag with --force"
    if re.search(r"\bgit\s+push\b.*(?:--delete|\s:(?:refs/tags/)?" + TAG_RE + r")", part) and re.search(TAG_RE, part):
        return "deleting a release tag on the remote"
    if re.search(r"\bgit\s+push\b.*(?:--force(?:-with-lease)?|\s-f\b)", part) and re.search(r"--tags|refs/tags/|\s" + TAG_RE, part):
        return "force-pushing a release tag"
    m = re.search(r"\bgit\s+tag\s+(?:-a\s+|-s\s+|-m\s+\S+\s+)*(" + TAG_RE + r")\b", part)
    if m:
        exists = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "-q", "--verify", f"refs/tags/{m.group(1)}"],
            capture_output=True, text=True,
        ).returncode == 0
        if exists:
            return f"re-tagging {m.group(1)}, which already exists"
    return None


def main() -> None:
    """Read the hook payload and decide."""
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        allow()

    tool_input = payload.get("tool_input") or {}
    command = (tool_input.get("command") or "").strip()
    cwd = payload.get("cwd") or tool_input.get("cwd") or os.getcwd()

    if not command or "git" not in command:
        allow()

    branch = current_branch(cwd)
    if branch is None:
        allow()

    parts = split_chain(command)

    for part in parts:
        if is_no_verify(part):
            deny(
                "`--no-verify` skips the repo's git hooks. That is blocked here; fix what the "
                f"hook reports instead. See {SECTION_REF}."
            )

    for part in parts:
        reason = tag_violation(part, cwd)
        if reason:
            deny(
                f"Blocked: {reason}. A release tag is never moved or deleted; a wrong tag is fixed "
                f"by cutting the next version. Ask the human. See {SECTION_REF}."
            )

    for part in parts:
        if is_git_commit(part) and branch in PROTECTED:
            deny(
                f"Heads up — this would commit directly on `{branch}`. "
                f"Our flow: branch off `{BASE}`, commit there, open a PR. "
                f"Try: `git checkout -b <type>/<descriptive-name>` then "
                f"re-run your commit. If there's a reason to override, "
                f"see {SECTION_REF}."
            )

    if any(is_checkout_protected(p) for p in parts) and any(is_git_commit(p) for p in parts):
        deny(
            f"Heads up — this chains a checkout to a protected branch ({PROTECTED_LIST}) with a "
            "commit, which would land the commit on a shared branch. Try: "
            f"`git checkout -b <type>/<descriptive-name> {BASE}` and commit there. "
            f"See {SECTION_REF}."
        )

    for part in parts:
        if not is_git_push(part):
            continue

        force = is_force_push(part)
        explicit = push_targets_protected_explicit(part)
        implicit = push_is_implicit(part) and branch in PROTECTED

        if not (explicit or implicit):
            continue

        if force:
            deny(
                f"Force-pushing to a protected branch ({PROTECTED_LIST}) is blocked unconditionally — "
                "these are shared branches and force-push rewrites history "
                "everyone else has based work on. If you have an authorized "
                "exception (incident response, security rotation), do this "
                f"manually outside Claude Code with full awareness. See {SECTION_REF}."
            )

        target = (
            f"a protected branch ({PROTECTED_LIST})" if explicit
            else f"`{branch}` (your current branch is shared)"
        )
        deny(
            f"Heads up — this would push directly to {target}. "
            f"Our flow: push your feature branch, then open a PR via "
            f"`gh pr create --base {BASE}`. Try: "
            f"`git push -u origin <your-feature-branch>` then "
            f"`gh pr create --base {BASE}`. If there's a reason to override, "
            f"see {SECTION_REF}."
        )

    allow()


if __name__ == "__main__":
    main()
