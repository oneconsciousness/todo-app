#!/usr/bin/env python3
"""PreToolUse hook for Bash. Blocks `gh pr create` to a checked base branch when the branch touched a path in the docs map and carries no docs decision.

A decision is either a change to a Claude artifact on the branch, or a commit whose message carries a `Claude-Docs:` trailer.
`/claude-docs-check` produces both. The map's `bases` (fnmatch patterns) name the checked bases: `main` and each round's
integration branch, so child PRs are checked too. PRs to any other base are not checked.
"""
import fnmatch
import json
import os
import re
import shlex
import subprocess
import sys

# --- config ---------------------------------------------------------------
MAP = ".claude/skills/claude-docs-check/map.json"  # carries the checked bases and the triggers
DEFAULT_BASE = "main"  # gh's own default when --base is left out; also the fallback when map.json names no bases
# --------------------------------------------------------------------------


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}}))
    sys.exit(0)


def git(root: str, *args: str) -> str:
    try:
        return subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, timeout=15).stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""


def base_of(command: str, default: str) -> str:
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return default
    for i, tok in enumerate(tokens):
        if tok in ("--base", "-B") and i + 1 < len(tokens):
            return tokens[i + 1]
        if tok.startswith("--base="):
            return tok[len("--base="):]
    return default


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        sys.exit(0)
    command = ((payload.get("tool_input") or {}).get("command") or "").strip()
    if not re.search(r"\bgh\s+pr\s+create\b", command):
        sys.exit(0)
    root = payload.get("cwd") or os.getcwd()
    try:
        spec = json.load(open(os.path.join(root, MAP)))
    except (OSError, json.JSONDecodeError):
        sys.exit(0)
    base = base_of(command, DEFAULT_BASE)
    if not any(fnmatch.fnmatchcase(base, pattern) for pattern in spec.get("bases", [DEFAULT_BASE])):
        sys.exit(0)
    ref = next((r for r in (f"origin/{base}", base) if git(root, "rev-parse", "--verify", "-q", r).strip()), None)
    if ref is None:
        deny(f"The PR base `{base}` is not known locally, so the docs check cannot see what this branch changed. Run `git fetch --all --prune` and try again.")
    changed = [f for f in git(root, "diff", "--name-only", f"{ref}...HEAD").splitlines() if f]
    if not changed:
        sys.exit(0)
    hits = [(f, t["artifacts"]) for t in spec["triggers"] for f in changed if any(fnmatch.fnmatch(f, g) for g in t["paths"])]
    if not hits:
        sys.exit(0)
    prefixes = tuple(spec.get("artifact_prefixes", []))
    if any(f.startswith(prefixes) for f in changed):
        sys.exit(0)
    if re.search(r"^Claude-Docs: ", git(root, "log", "--format=%B", f"{ref}..HEAD"), re.M):
        sys.exit(0)
    lines = "\n".join(f"  {f} -> {', '.join(a)}" for f, a in hits[:12])
    deny(
        "This branch touched paths the Claude Code instructions describe, and carries no docs decision:\n"
        f"{lines}\n"
        "Run /claude-docs-check first. It updates the mapped files on Opus, or records why nothing changes, as a `Claude-Docs:` commit trailer."
    )


if __name__ == "__main__":
    main()
